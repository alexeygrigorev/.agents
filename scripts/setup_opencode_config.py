"""Merge repo-managed OpenCode settings into ~/.config/opencode/opencode.json.

Deep-merges the desired config from config/opencode/settings.json into the
user's existing config, without overwriting keys the user has already set.
"""

import json
from pathlib import Path


def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2) + "\n")


def deep_merge(existing: dict, desired: dict) -> bool:
    """Recursively merge desired into existing. Existing keys are never overwritten."""
    changed = False
    for key, value in desired.items():
        if key not in existing:
            existing[key] = value
            changed = True
        elif isinstance(existing[key], dict) and isinstance(value, dict):
            if deep_merge(existing[key], value):
                changed = True
    return changed


def main():
    repo_dir = Path(__file__).resolve().parent.parent
    settings_path = Path.home() / ".config" / "opencode" / "opencode.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    existing = load_json(settings_path)
    desired = load_json(repo_dir / "config" / "opencode" / "settings.json")

    if deep_merge(existing, desired):
        save_json(settings_path, existing)
        print(f"  Merged OpenCode settings into {settings_path}")
    else:
        print(f"  OpenCode settings already up to date")


if __name__ == "__main__":
    main()
