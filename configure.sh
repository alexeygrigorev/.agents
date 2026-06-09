#!/bin/bash
# Install AI assistant dotfiles

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SETUP_BASHRC_ARGS=()
TARGETS=()

usage() {
    cat <<'EOF'
Usage: ./configure.sh [--yes] [all|claude|codex|opencode|zlaude ...]

Targets:
  claude    Symlink skills into ~/.claude and sync Claude settings
  codex     Sync Codex config and shared skills into ~/.codex
  opencode  Symlink skills into ~/.config/opencode
  zlaude    Configure a Z.AI-routed Claude profile under ~/.zlaude
            (prompts for a Z.AI API key; not included in 'all')
  all       Configure every target except zlaude (default)
EOF
}

for arg in "$@"; do
    case "$arg" in
        --yes|-y)
            SETUP_BASHRC_ARGS+=("--yes")
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        all|claude|codex|opencode|zlaude)
            TARGETS+=("$arg")
            ;;
        *)
            echo "Error: unknown argument: $arg"
            usage
            exit 1
            ;;
    esac
done

if [[ ${#TARGETS[@]} -eq 0 ]]; then
    TARGETS=(all)
fi

has_target() {
    local wanted="$1"
    local target
    for target in "${TARGETS[@]}"; do
        if [[ "$target" == "all" || "$target" == "$wanted" ]]; then
            return 0
        fi
    done
    return 1
}

# Like has_target but does NOT match "all" — for opt-in targets that must be
# requested by name (e.g. zlaude, which prompts for an API key).
has_explicit_target() {
    local wanted="$1"
    local target
    for target in "${TARGETS[@]}"; do
        if [[ "$target" == "$wanted" ]]; then
            return 0
        fi
    done
    return 1
}

run_python() {
    if command -v python3 >/dev/null 2>&1; then
        python3 "$@"
        return
    fi

    if command -v uv >/dev/null 2>&1; then
        uv run --no-project python "$@"
        return
    fi

    echo "Error: python3 or uv is required."
    exit 1
}

link_shared_dirs() {
    local target_dir="$1"
    mkdir -p "$target_dir"

    if [[ "${OS:-}" == "Windows_NT" ]]; then
        echo "Creating directory junctions in $target_dir on Windows..."
        local win_repo win_target
        win_repo=$(cygpath -w "$REPO_DIR")
        win_target=$(cygpath -w "$target_dir")

        rm -rf "$target_dir/skills"
        remove_managed_commands "$target_dir"

        cmd.exe //c "mklink /J ${win_target}\\skills ${win_repo}\\skills" 2>/dev/null
    else
        echo "Creating symlinks in $target_dir..."
        ensure_symlink "$REPO_DIR/skills" "$target_dir/skills"
        remove_managed_commands "$target_dir"
    fi
}

ensure_symlink() {
    local source="$1"
    local target="$2"
    local current

    if [[ -L "$target" ]]; then
        current="$(readlink -f "$target")"
        if [[ "$current" == "$source" ]]; then
            return
        fi
        rm "$target"
    elif [[ -e "$target" ]]; then
        echo "WARNING: $target exists and is not a symlink; leaving it unchanged."
        return
    fi

    ln -s "$source" "$target"
}

remove_managed_commands() {
    local target_dir="$1"
    local target="$target_dir/commands"

    if [[ -L "$target" ]]; then
        local current
        current="$(readlink -f "$target")"
        if [[ "$current" == "$REPO_DIR/commands" || ! -e "$current" ]]; then
            rm "$target"
            echo "Removed legacy commands symlink: $target"
        fi
    fi
}

if has_target claude; then
    link_shared_dirs "$HOME/.claude"
    run_python "$REPO_DIR/scripts/setup_settings.py"
fi

if has_target opencode; then
    link_shared_dirs "$HOME/.config/opencode"
    run_python "$REPO_DIR/scripts/setup_opencode_config.py"
fi

if has_target codex; then
    mkdir -p "$HOME/.codex"
    run_python "$REPO_DIR/scripts/setup_codex_config.py"
    run_python "$REPO_DIR/scripts/setup_codex_skills.py"
fi

if has_explicit_target zlaude; then
    # Prompt for / validate the Z.AI key first. With set -e, a blank prompt
    # aborts here before the skills symlink is created, so nothing is left behind.
    run_python "$REPO_DIR/scripts/setup_zlaude.py"
    link_shared_dirs "$HOME/.zlaude"
fi

# Install CLI wrappers to ~/bin
mkdir -p "$HOME/bin"
for wrapper in "$REPO_DIR/bin/"*; do
    name="$(basename "$wrapper")"
    cp "$wrapper" "$HOME/bin/$name"
    chmod +x "$HOME/bin/$name"
    echo "Installed wrapper: ~/bin/$name"
done

# Ensure ~/bin is early in PATH (before /usr/bin)
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$HOME/bin"; then
    echo "WARNING: ~/bin is not in your PATH."
    echo "Add this to your ~/.bashrc or ~/.profile:"
    echo '  export PATH="$HOME/bin:$PATH"'
elif [[ "$(command -v gh)" != "$HOME/bin/gh" ]]; then
    echo "WARNING: ~/bin/gh is not taking priority. Another gh comes first in PATH."
    echo "Make sure ~/bin is early in PATH:"
    echo '  export PATH="$HOME/bin:$PATH"'
fi

# Setup bashrc source line
run_python "$REPO_DIR/scripts/setup_bashrc.py" "${SETUP_BASHRC_ARGS[@]}"

echo "Installation complete. Run 'source ~/.bashrc' to apply changes."
