"""Sync repo-managed Codex settings into ~/.codex/config.toml."""

from __future__ import annotations

import json
import re
from pathlib import Path


BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def load_settings(path: Path) -> dict:
    return json.loads(path.read_text())


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


def main() -> None:
    repo_dir = Path(__file__).resolve().parent.parent
    settings_path = repo_dir / "config" / "codex" / "settings.json"
    config_path = Path.home() / ".codex" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    desired = load_settings(settings_path)
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


if __name__ == "__main__":
    main()
