"""Ensure ~/.bashrc sources the repo's .bashrc file."""

import argparse
from pathlib import Path


def ensure_source_line(repo_dir: Path, *, yes: bool = False):
    bashrc = Path.home() / ".bashrc"
    bashrc_source = repo_dir / ".bashrc"

    # Use ${HOME} prefix if repo is under home directory
    home = str(Path.home())
    source_str = str(bashrc_source)
    if source_str.startswith(home):
        source_path = '${HOME}' + source_str[len(home):]
    else:
        source_path = source_str

    # Normalize to forward slashes for bash
    source_path = source_path.replace("\\", "/")

    source_line = f'source "{source_path}"'

    # Check if already present (match on the repo .bashrc path, either form)
    if bashrc.exists():
        content = bashrc.read_text()
        repo_bashrc_str = str(bashrc_source).replace("\\", "/")
        if repo_bashrc_str in content or source_path in content:
            print("Source line already present in ~/.bashrc")
            return

    if not yes:
        answer = input(f"Add '{source_line}' to ~/.bashrc? [y/N] ").strip().lower()
        if answer != "y":
            print("Skipped.")
            return

    with open(bashrc, "a") as f:
        f.write(f"\n# AI assistant dotfiles\n{source_line}\n")
    print("Added source line to ~/.bashrc")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="Update ~/.bashrc without prompting")
    args = parser.parse_args()
    repo_dir = Path(__file__).resolve().parent.parent
    ensure_source_line(repo_dir, yes=args.yes)
