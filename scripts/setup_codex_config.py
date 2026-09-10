"""Sync repo-managed Codex settings into $CODEX_HOME/config.toml.

Also removes legacy repo-managed skill symlinks from $CODEX_HOME/skills:
Codex now discovers shared skills in ~/.agents/skills, so the per-skill
symlinks this repo used to maintain are obsolete. Only symlinks pointing
into this repo's skills/ directory (and the state files tracking them) are
removed; anything else is left untouched.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path


BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")

STATE_FILES = (".managed-skills-state.json", ".claude-bridge-state.json")
OLD_COMMAND_PREFIX = "claude-command-"


def load_settings(path: Path) -> dict:
    return json.loads(path.read_text())


def load_state_skills(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return set()
    if isinstance(data, dict):
        return {str(item) for item in data.get("skills", [])}
    if isinstance(data, list):
        return {str(item) for item in data}
    return set()


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_junction():
        path.rmdir()
    elif path.is_dir():
        shutil.rmtree(path)


def remove_legacy_skills(codex_home: Path, repo_skills_dir: Path) -> None:
    skills_dir = codex_home / "skills"

    if skills_dir.is_symlink():
        resolved = skills_dir.resolve()
        if resolved == repo_skills_dir or repo_skills_dir in resolved.parents:
            skills_dir.unlink()
            print(f"  Removed {skills_dir} symlink; skills now load from {repo_skills_dir}")
        return

    if not skills_dir.is_dir():
        return

    managed: set[str] = set()
    for state_file in STATE_FILES:
        managed |= load_state_skills(skills_dir / state_file)

    for child in skills_dir.iterdir():
        if not child.is_symlink() and not child.is_junction():
            continue
        resolved = child.resolve()
        if resolved == repo_skills_dir or repo_skills_dir in resolved.parents:
            managed.add(child.name)

    for child in skills_dir.glob(f"{OLD_COMMAND_PREFIX}*"):
        if child.is_symlink() or child.is_junction():
            managed.add(child.name)

    removed = 0
    for name in sorted(managed):
        target = skills_dir / name
        if target.is_symlink() or target.is_junction():
            remove_path(target)
            removed += 1

    for state_file in STATE_FILES:
        state_path = skills_dir / state_file
        if state_path.exists():
            state_path.unlink()

    if removed:
        print(f"  Removed {removed} legacy skill symlinks from {skills_dir}")


def flatten_sections(node: dict, prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], dict]]:
    sections: list[tuple[tuple[str, ...], dict]] = []
    scalars: dict[str, object] = {}

    for key, value in node.items():
        if isinstance(value, dict):
            sections.extend(flatten_sections(value, prefix + (key,)))
        else:
            scalars[key] = value

    if scalars:
        if not prefix:
            raise ValueError("settings.json must not contain top-level scalar keys")
        sections.insert(0, (prefix, scalars))

    return sections


def format_header(parts: tuple[str, ...]) -> str:
    rendered = []
    for part in parts:
        if BARE_KEY_RE.fullmatch(part):
            rendered.append(part)
        else:
            rendered.append(json.dumps(part))
    return "[" + ".".join(rendered) + "]"


def format_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    raise TypeError(f"Unsupported value type: {type(value).__name__}")


def find_section(lines: list[str], header: str) -> tuple[int | None, int | None]:
    for index, line in enumerate(lines):
        if line.strip() != header:
            continue

        end = len(lines)
        for next_index in range(index + 1, len(lines)):
            stripped = lines[next_index].strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                end = next_index
                break
        return index, end

    return None, None


def upsert_section(lines: list[str], header: str, assignments: dict[str, object]) -> bool:
    start, end = find_section(lines, header)

    if start is None:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(header)
        for key, value in assignments.items():
            lines.append(f"{key} = {format_value(value)}")
        return True

    changed = False
    section_lines = lines[start + 1 : end]

    for key, value in assignments.items():
        wanted = f"{key} = {format_value(value)}"
        matcher = re.compile(rf"^\s*{re.escape(key)}\s*=")

        for index, line in enumerate(section_lines):
            if not matcher.match(line):
                continue
            if line.strip() != wanted:
                section_lines[index] = wanted
                changed = True
            break
        else:
            section_lines.append(wanted)
            changed = True

    if changed:
        lines[start + 1 : end] = section_lines

    return changed


def sync_config(config_path: Path, desired: dict) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    sections = flatten_sections(desired)

    original = config_path.read_text() if config_path.exists() else ""
    lines = original.splitlines()
    changed_sections = []

    for parts, assignments in sections:
        header = format_header(parts)
        if upsert_section(lines, header, assignments):
            changed_sections.append(header)

    updated = ("\n".join(lines).rstrip() + "\n") if lines else ""

    if updated != original:
        config_path.write_text(updated)
        for header in changed_sections:
            print(f"  Synced {header} in {config_path}")
        print(f"  Updated {config_path}")
    else:
        print(f"  No changes needed in {config_path}")


def main() -> None:
    repo_dir = Path(__file__).resolve().parent.parent
    repo_skills_dir = (repo_dir / "skills").resolve()
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))

    desired = load_settings(repo_dir / "config" / "codex" / "settings.json")
    sync_config(codex_home / "config.toml", desired)
    remove_legacy_skills(codex_home, repo_skills_dir)


if __name__ == "__main__":
    main()
