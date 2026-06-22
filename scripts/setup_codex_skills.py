"""Sync repo-managed skills into ~/.codex/skills."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


STATE_FILE = ".managed-skills-state.json"
OLD_BRIDGE_STATE_FILE = ".claude-bridge-state.json"
OLD_COMMAND_PREFIX = "claude-command-"


def load_state(path: Path) -> set[str]:
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


def save_state(path: Path, skills: set[str]) -> None:
    path.write_text(json.dumps({"skills": sorted(skills)}, indent=2) + "\n")


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def ensure_symlink(target: Path, source: Path) -> bool:
    if target.is_symlink():
        current = Path(target.readlink())
        if not current.is_absolute():
            current = (target.parent / current).resolve()
        else:
            current = current.resolve()
        if current == source.resolve():
            return False
        target.unlink()
    elif target.exists():
        return False

    target.symlink_to(source)
    return True


def sync_skills(codex_skills_dir: Path, repo_skills_dir: Path, old_skills: set[str]) -> set[str]:
    desired: set[str] = set()
    if not repo_skills_dir.is_dir():
        return desired

    for child in sorted(repo_skills_dir.iterdir()):
        if child.name.startswith(".") or not child.is_dir():
            continue
        if not (child / "SKILL.md").is_file():
            continue

        target = codex_skills_dir / child.name
        ensure_symlink(target, child.resolve())
        if target.is_symlink():
            desired.add(child.name)

    for name in old_skills - desired:
        target = codex_skills_dir / name
        if target.is_symlink():
            target.unlink()

    return desired


def cleanup_old_bridge_state(codex_skills_dir: Path) -> set[str]:
    old_state_path = codex_skills_dir / OLD_BRIDGE_STATE_FILE
    old_skills = load_state(old_state_path)
    old_commands = set()
    if old_state_path.exists():
        try:
            data = json.loads(old_state_path.read_text())
        except json.JSONDecodeError:
            data = {}
        old_commands = {str(item) for item in data.get("commands", [])}

    stale_commands = old_commands | {path.name for path in codex_skills_dir.glob(f"{OLD_COMMAND_PREFIX}*")}
    for name in stale_commands:
        target = codex_skills_dir / name
        if target.exists() or target.is_symlink():
            remove_path(target)

    if old_state_path.exists():
        old_state_path.unlink()

    return old_skills


def main() -> None:
    repo_dir = Path(__file__).resolve().parent.parent
    repo_skills_dir = repo_dir / "skills"
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    codex_skills_dir = codex_home / "skills"
    if codex_skills_dir.is_symlink():
        codex_skills_dir.unlink()
    codex_skills_dir.mkdir(parents=True, exist_ok=True)

    state_path = codex_skills_dir / STATE_FILE
    old_skills = load_state(state_path) | cleanup_old_bridge_state(codex_skills_dir)
    skills = sync_skills(codex_skills_dir, repo_skills_dir, old_skills)
    save_state(state_path, skills)

    print(f"  Synced shared skills into {codex_skills_dir}")


if __name__ == "__main__":
    main()
