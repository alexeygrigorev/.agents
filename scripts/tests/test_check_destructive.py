import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_destructive  # noqa: E402

SCRIPT = Path(__file__).resolve().parent.parent / "check_destructive.py"

BLOCK = [
    "gh repo delete foo/bar --yes",
    "rm -rf /",
    "rm -rf ~",
    "sudo rm -rf /etc",
    "cd x && rm -r /home",
    'psql -c "x"; DROP DATABASE prod',
    "drop table users;",
    "git push --force origin main",
    "git push -f",
    "git clean -fdx",
    "mkfs.ext4 /dev/sda1",
    "dd if=/dev/zero of=/dev/sda",
    "echo hi > /dev/sda",
    "chmod -R 777 /",
    "chown -R me /",
    ":(){ :|: & };:",
]

ALLOW = [
    "terraform apply",
    "tmux kill-server",
    "git push --force-with-lease",
    "rm -rf ./build",
    "rm -rf /tmp/x",
    'echo "DROP TABLE"',
    "git clean -fd",
    "git commit -m \"$(cat <<'EOF'\nfix: stop rm -rf / and git push --force\nEOF\n)\"",
    "",
]


@pytest.mark.parametrize("command", BLOCK)
def test_blocks(command):
    assert check_destructive.check(command) is not None


@pytest.mark.parametrize("command", ALLOW)
def test_allows(command):
    assert check_destructive.check(command) is None


def _run(stdin: str) -> str:
    return subprocess.run(
        [sys.executable, str(SCRIPT)], input=stdin, capture_output=True, text=True
    ).stdout


def test_json_block_contract():
    out = json.loads(_run(json.dumps({"tool_input": {"command": "git push -f"}})))
    assert out["decision"] == "block" and out["reason"]


def test_allow_prints_nothing():
    assert _run(json.dumps({"tool_input": {"command": "ls"}})) == ""


@pytest.mark.parametrize(
    "stdin", ["not json", "", '{"tool_input": null}', '{"tool_input":{"command":5}}']
)
def test_fail_open(stdin):
    assert _run(stdin) == ""
