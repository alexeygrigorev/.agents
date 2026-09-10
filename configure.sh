#!/bin/bash
# Install AI assistant dotfiles

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SETUP_BASHRC_ARGS=()
TARGETS=()

usage() {
    cat <<'EOF'
Usage: ./configure.sh [--yes] [all|claude|codex|opencode|zlaude|zodex|godex ...]

Targets:
  all       Configure every target except zlaude (default)
  claude    Symlink skills into ~/.claude and sync Claude settings
  codex     Sync Codex config into ~/.codex and remove legacy skill
            symlinks (Codex loads shared skills from ~/.agents/skills)
  opencode  Sync OpenCode config into ~/.config/opencode (skills load
            from ~/.agents/skills)
  zlaude    Configure a Z.AI-routed Claude profile under ~/.zlaude
            (prompts for a Z.AI API key; not included in 'all')
  zodex     Configure a Z.AI-routed Codex profile under ~/.zodex
            (prompts for a Z.AI API key; not included in 'all')
  godex     Configure an OpenCode Go-routed Codex profile under ~/.godex
            (prompts for an OpenCode Go API key; not included in 'all')
  zcodex    Configure the zcodex Codex variant under ~/.zcodex
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
    all|claude|codex|opencode|zlaude|zodex|godex|zcodex)
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
# requested by name (e.g. zlaude/zodex, which prompt for an API key).
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

# Codex and OpenCode (and most other agents) load shared skills from
# ~/.agents/skills, so ~/.agents must point at this repo.
ensure_agents_dir() {
    local link="$HOME/.agents"

    if [[ -L "$link" ]]; then
        if [[ "$(readlink -f "$link")" == "$REPO_DIR" ]]; then
            return
        fi
        echo "WARNING: $link is a symlink to $(readlink -f "$link"), not $REPO_DIR; leaving it unchanged."
        return
    fi

    if [[ -e "$link" ]]; then
        echo "WARNING: $link exists and is not a symlink; leaving it unchanged."
        return
    fi

    ln -s "$REPO_DIR" "$link"
    echo "Linked $link -> $REPO_DIR"
}

# Remove a skills symlink that points into this repo; the agents that used
# to need it now read ~/.agents/skills directly.
remove_repo_skills_link() {
    local target_dir="$1"
    local target="$target_dir/skills"

    if [[ -L "$target" && "$(readlink -f "$target")" == "$REPO_DIR/skills" ]]; then
        rm "$target"
        echo "Removed $target (skills now load from ~/.agents/skills)"
    fi
}

ensure_agents_dir

if has_target claude; then
    link_shared_dirs "$HOME/.claude"
    run_python "$REPO_DIR/scripts/setup_settings.py"
fi

if has_target opencode; then
    mkdir -p "$HOME/.config/opencode"
    remove_repo_skills_link "$HOME/.config/opencode"
    remove_managed_commands "$HOME/.config/opencode"
    run_python "$REPO_DIR/scripts/setup_opencode_config.py"
fi

if has_target codex; then
    mkdir -p "$HOME/.codex"
    run_python "$REPO_DIR/scripts/setup_codex_config.py"
fi

if has_explicit_target zlaude; then
    # Prompt for / validate the Z.AI key first. With set -e, a blank prompt
    # aborts here before the skills symlink is created, so nothing is left behind.
    run_python "$REPO_DIR/scripts/setup_zlaude.py"
    link_shared_dirs "$HOME/.zlaude"
fi

if has_explicit_target zodex; then
    # Prompt for / validate the Z.AI key first. With set -e, a blank prompt
    # aborts here before the skills symlink is created, so nothing is left behind.
    run_python "$REPO_DIR/scripts/setup_zodex.py"
    chmod +x "$REPO_DIR/scripts/zodex_start_proxy.sh"
    CODEX_HOME="$HOME/.zodex" run_python "$REPO_DIR/scripts/setup_codex_config.py"
fi

if has_explicit_target godex; then
    # Prompt for / validate the OpenCode Go key first. With set -e, a blank
    # prompt aborts here before the skills symlink is created, so nothing is
    # left behind.
    run_python "$REPO_DIR/scripts/setup_godex.py"
    chmod +x "$REPO_DIR/scripts/godex_start_proxy.sh"
    CODEX_HOME="$HOME/.godex" run_python "$REPO_DIR/scripts/setup_codex_config.py"
fi

if has_explicit_target zcodex; then
    # zcodex uses ZCode's own credentials, so no API-key prompt is needed.
    mkdir -p "$HOME/.zcodex"
    if [[ ! -f "$HOME/.zcodex/config.toml" ]]; then
        cat > "$HOME/.zcodex/config.toml" <<'EOF'
model = "glm-5.3-flash"
model_reasoning_effort = "max"
model_provider = "zcode"

[model_providers.zcode]
name = "ZCode"
base_url = ""
wire_api = "zcode"
EOF
    fi
    CODEX_HOME="$HOME/.zcodex" run_python "$REPO_DIR/scripts/setup_codex_config.py"
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
