"""PreToolUse hook: block destructive commands unless explicitly confirmed."""

import json
import re
import shlex
import sys

# Each entry: (pattern to match, human-readable description)
DESTRUCTIVE_PATTERNS = [
    ("gh repo delete", "GitHub repo deletion"),
    ("rm -rf /", "recursive delete from root"),
    ("DROP DATABASE", "database deletion"),
    ("DROP TABLE", "table deletion"),
    ("git push --force", "force push"),
    ("git push -f", "force push"),
]

def strip_quotes(command: str) -> str:
    """Remove quoted strings and heredocs to avoid false positives from
    commit messages, echo statements, etc."""
    # Remove heredoc bodies: everything between <<'EOF' ... EOF (or <<EOF ... EOF)
    import re

    command = re.sub(
        r"<<-?\s*['\"]?(\w+)['\"]?.*?\n\1",
        "",
        command,
        flags=re.DOTALL,
    )
    # Remove single-quoted strings
    command = re.sub(r"'[^']*'", '""', command)
    # Remove double-quoted strings (handling escaped quotes)
    command = re.sub(r'"(?:[^"\\]|\\.)*"', '""', command)
    return command


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return

    command = data.get("tool_input", {}).get("command", "")
    cleaned = strip_quotes(command)

    for pattern, description in DESTRUCTIVE_PATTERNS:
        if pattern in cleaned:
            json.dump(
                {
                    "decision": "block",
                    "reason": f"Blocked: {description} detected (`{pattern}`). If you really want to do this, explicitly confirm.",
                },
                sys.stdout,
            )
            return


if __name__ == "__main__":
    main()
