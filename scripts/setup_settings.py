"""Ensure ~/.claude/settings.json has required configuration."""

import json
from pathlib import Path


def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2) + "\n")


def ensure_attribution(data: dict) -> bool:
    if data.get("attribution", {}).get("commit", "MISSING") == "MISSING":
        data.setdefault("attribution", {})["commit"] = ""
        return True
    return False


def resolve_repo_dir(obj, repo_dir: str):
    """Recursively replace {{REPO_DIR}} placeholders in strings."""
    if isinstance(obj, str):
        return obj.replace("{{REPO_DIR}}", repo_dir)
    if isinstance(obj, list):
        return [resolve_repo_dir(item, repo_dir) for item in obj]
    if isinstance(obj, dict):
        return {k: resolve_repo_dir(v, repo_dir) for k, v in obj.items()}
    return obj


def merge_hooks(data: dict, repo_hooks: dict, repo_dir: str) -> bool:
    """Merge repo hooks into user settings, without duplicating."""
    changed = False
    user_hooks = data.setdefault("hooks", {})

    for event, repo_matchers in repo_hooks.items():
        user_matchers = user_hooks.setdefault(event, [])

        for repo_entry in repo_matchers:
            repo_entry = resolve_repo_dir(repo_entry, repo_dir)
            repo_matcher = repo_entry.get("matcher")

            # Find existing entry with same matcher
            existing = None
            for entry in user_matchers:
                if entry.get("matcher") == repo_matcher:
                    existing = entry
                    break

            if existing is None:
                # No entry for this matcher — add it
                user_matchers.append(repo_entry)
                changed = True
            else:
                # Merge hook commands: add any that aren't already present
                existing_commands = {
                    h.get("command", h.get("prompt", ""))
                    for h in existing.get("hooks", [])
                }
                for hook in repo_entry.get("hooks", []):
                    hook_key = hook.get("command", hook.get("prompt", ""))
                    if hook_key not in existing_commands:
                        existing.setdefault("hooks", []).append(hook)
                        changed = True

    return changed


def main():
    repo_dir = Path(__file__).resolve().parent.parent
    settings_path = Path.home() / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    data = load_json(settings_path)
    repo_settings = load_json(repo_dir / "config" / "claude" / "settings.json")

    changed = False

    # Attribution
    if ensure_attribution(data):
        print(f"  Set attribution.commit in {settings_path}")
        changed = True
    else:
        print(f"  attribution.commit already set")

    # Hooks
    repo_hooks = repo_settings.get("hooks", {})
    if repo_hooks:
        if merge_hooks(data, repo_hooks, str(repo_dir)):
            print(f"  Merged hooks into {settings_path}")
            changed = True
        else:
            print(f"  Hooks already up to date")

    if changed:
        save_json(settings_path, data)
        print(f"  Updated {settings_path}")
    else:
        print(f"  No changes needed")


if __name__ == "__main__":
    main()
