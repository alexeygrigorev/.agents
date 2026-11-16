"""PreToolUse hook: block destructive Bash commands.

Rules match at command position (start of the command, or after a separator,
`do`/`then`, optionally via sudo) on a copy of the command with quoted strings
and heredoc bodies removed, so commit messages, echo labels and SQL in quotes
do not cause false positives.

Output contract: print {"decision": "block", "reason": ...} to block; print
nothing to allow. Fail-open: any internal error allows the command.
"""

import json
import re
import sys

# Command actually being run: at the start, or right after a separator / do / then.
_CMD = r"(?:^|[\n;&|]|\bdo\b|\bthen\b)\s*(?:sudo\s+)?"
# Stay inside one simple command.
_ARG = r"[^|;&\n]*?"
_BND = r"[^|;&\n]*"
_ROOT_END = r"(?=\s|$|[;&|])"
_CRITICAL_ROOTS = (
    r"(?:/|/\*|~|\$\{?HOME\}?|/home|/root|/etc|/usr|/var|/bin|/boot|/lib|/sys|/proc)"
)

# (compiled pattern, human-readable description)
DESTRUCTIVE_RULES = [
    (re.compile(_CMD + r"gh\s+repo\s+delete\b"), "GitHub repo deletion"),
    (
        re.compile(
            _CMD + r"rm\s+(?:-\S*[rR]\S*|--recursive)\b" + _ARG + r"\s"
            + _CRITICAL_ROOTS + _ROOT_END
        ),
        "recursive delete of a critical root (/ ~ /home /etc ...)",
    ),
    (re.compile(r"\bDROP\s+(?:DATABASE|TABLE)\b", re.IGNORECASE), "database/table deletion"),
    (
        re.compile(_CMD + r"git\s+push\b" + _ARG + r"\s(?:--force|-f)(?=\s|$)"),
        "force push (use --force-with-lease, and never on main)",
    ),
    (
        re.compile(
            _CMD + r"git\s+clean\b(?=" + _BND + r"\s-[a-zA-Z]*f)(?=" + _BND
            + r"\s-[a-zA-Z]*d)(?=" + _BND + r"\s-[a-zA-Z]*x)"
        ),
        "git clean -fdx removes ignored and untracked files",
    ),
    (re.compile(_CMD + r"mkfs\b"), "mkfs formats a filesystem"),
    (re.compile(r"\bdd\b" + _ARG + r"\sof=/dev/"), "dd writing to a raw device"),
    (re.compile(r">\s*/dev/sd[a-z]"), "redirect to a raw disk device"),
    (re.compile(_CMD + r"chmod\s+-R\b" + _ARG + r"\s/" + _ROOT_END), "chmod -R on /"),
    (re.compile(_CMD + r"chown\s+-R\b" + _ARG + r"\s/" + _ROOT_END), "chown -R on /"),
    (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"), "fork bomb"),
]


def strip_quotes(command: str) -> str:
    """Remove heredoc bodies and quoted strings to avoid false positives from
    commit messages, echo statements, etc."""
    command = re.sub(
        r"<<-?\s*['\"]?(\w+)['\"]?.*?\n\s*\1\b",
        "",
        command,
        flags=re.DOTALL,
    )
    command = re.sub(r"'[^']*'", '""', command)
    command = re.sub(r'"(?:[^"\\]|\\.)*"', '""', command)
    return command


def check(command: str):
    """Return a description of the first matching rule, or None."""
    cleaned = strip_quotes(command)
    for pattern, description in DESTRUCTIVE_RULES:
        if pattern.search(cleaned):
            return description
    return None


def main():
    try:
        data = json.load(sys.stdin)
        command = (data.get("tool_input") or {}).get("command") or ""
        if not isinstance(command, str):
            return
        description = check(command)
    except Exception:
        return  # fail open

    if description:
        json.dump(
            {
                "decision": "block",
                "reason": f"Blocked: {description}. If you really want to do this, explicitly confirm.",
            },
            sys.stdout,
        )


if __name__ == "__main__":
    main()
