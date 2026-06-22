#!/bin/bash
# One-line installer for AI assistant dotfiles
# Usage: curl -sSL https://raw.githubusercontent.com/alexeygrigorev/.agents/main/installer.sh | bash

set -euo pipefail

REPO_URL="https://github.com/alexeygrigorev/.agents.git"
INSTALL_DIR="$HOME/git/.agents"
CONFIGURE_ARGS=()

for arg in "$@"; do
    CONFIGURE_ARGS+=("$arg")
done

# Check for git
if ! command -v git &>/dev/null; then
    echo "Error: git is required but not installed."
    exit 1
fi

# Check for Python runner
if ! command -v python3 &>/dev/null && ! command -v uv &>/dev/null; then
    echo "Error: python3 or uv is required."
    exit 1
fi

# Clone or update
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating existing installation..."
    git -C "$INSTALL_DIR" pull --rebase
else
    echo "Cloning AI assistant dotfiles..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# Run configure
cd "$INSTALL_DIR"
./configure.sh "${CONFIGURE_ARGS[@]}"

echo ""
echo "Run 'source ~/.bashrc' or restart your shell to apply changes."
