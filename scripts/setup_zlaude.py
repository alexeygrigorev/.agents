"""Configure the 'zlaude' profile: Claude Code routed to Z.AI under ~/.zlaude.

Writes ~/.zlaude/settings.json with the Z.AI env block (auth token, base URL,
earlier auto-compaction) and reuses the shared hook/permission merges from
setup_settings.py.

The key is always requested interactively at the terminal when you run
configure — it is never read from .env or the environment. Leaving the prompt
blank aborts before anything is created or modified, so a cancelled run leaves
no partial profile behind.
"""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_settings import (  # noqa: E402
    ensure_attribution,
    load_json,
    merge_hooks,
    merge_permissions,
    save_json,
)

ZAI_BASE_URL = "https://api.z.ai/api/anthropic"
ZAI_API_KEY_URL = "https://z.ai/manage-apikey/apikey-list"

# Z.AI routing + earlier compaction (compact at ~128k instead of full window).
ZLAUDE_ENV = {
    "ANTHROPIC_BASE_URL": ZAI_BASE_URL,
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "128000",
}


def prompt_api_key() -> str:
    """Prompt for the Z.AI key at the terminal; abort (exit 1) if left blank.

    The key is requested every run and never read from .env or the environment.
    """
    print(f"  Get a Z.AI API key at: {ZAI_API_KEY_URL}")
    key = getpass.getpass("  Enter your Z.AI API key: ").strip()
    if not key:
        print("Error: no Z.AI API key provided. Aborting; no changes made.")
        sys.exit(1)
    return key


def main():
    repo_dir = Path(__file__).resolve().parent.parent

    # Prompt first, before creating or modifying anything, so a blank/aborted
    # prompt leaves no partial ~/.zlaude profile behind.
    api_key = prompt_api_key()

    settings_path = Path.home() / ".zlaude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    data = load_json(settings_path)
    repo_settings = load_json(repo_dir / "config" / "claude" / "settings.json")

    # Z.AI env block
    env = data.setdefault("env", {})
    env["ANTHROPIC_AUTH_TOKEN"] = api_key
    for key, value in ZLAUDE_ENV.items():
        env[key] = value

    # Reuse the shared merges so zlaude gets the same hooks/permissions as claude
    ensure_attribution(data)
    repo_hooks = repo_settings.get("hooks", {})
    if repo_hooks:
        merge_hooks(data, repo_hooks, str(repo_dir))
    repo_permissions = repo_settings.get("permissions", {})
    if repo_permissions:
        merge_permissions(data, repo_permissions)

    save_json(settings_path, data)
    print(f"  Configured zlaude profile at {settings_path}")


if __name__ == "__main__":
    main()
