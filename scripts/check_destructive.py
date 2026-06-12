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
    ("terraform apply", "Terraform apply"),
]

# tmux server-wide kills wipe EVERY session on the targeted socket. A bare
# `tmux kill-server` (no -L/-S) hits the DEFAULT socket = all of the
# maintainer's live sessions. This destroyed hours of agent work on
# 2026-06-12. Block the unscoped server-wide kills; allow socket-scoped
# (`tmux -L foo kill-server` / `tmux -S /path ...`) and targeted
# (`tmux kill-session -t <name>`) variants.
TMUX_GUIDANCE = (
    "wipes ALL sessions on the default tmux socket (destroyed hours of work "
    "on 2026-06-12). Kill ONE session by name: `tmux kill-session -t <name>`. "
    "To clear an isolated test server, scope it: `tmux -L <name> kill-server`."
)


def tmux_danger(cleaned: str) -> str | None:
    """Return a block reason if the command does a server-wide tmux kill on
    the default socket, else None."""
    # `tmux ... kill-server` within one command segment (no ; && || pipe
    # between) that has NO -L/-S socket selector before kill-server.
    if re.search(r"\btmux\b(?:(?![;&|]|-L\b|-S\b).)*\bkill-server\b", cleaned):
        return f"`tmux kill-server` on the default socket {TMUX_GUIDANCE}"
    # pkill / killall targeting tmux nukes the server process directly.
    if re.search(r"\b(?:pkill|killall)\b[^;&|]*\btmux\b", cleaned):
        return f"`pkill/killall tmux` {TMUX_GUIDANCE}"
    return None


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

    tmux_reason = tmux_danger(cleaned)
    if tmux_reason:
        json.dump(
            {
                "decision": "block",
                "reason": f"Blocked: {tmux_reason}",
            },
            sys.stdout,
        )
        return

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
