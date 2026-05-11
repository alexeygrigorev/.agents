# Shared AI assistant aliases and functions

export AI_DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CLAUDE_DOTFILES_DIR="$AI_DOTFILES_DIR"
export CODEX_DOTFILES_DIR="$AI_DOTFILES_DIR"

alias c="claude"
alias cc="claude -c"
alias csp="claude --dangerously-skip-permissions"
alias ccsp="claude -c --dangerously-skip-permissions"
alias cy="codex --dangerously-bypass-approvals-and-sandbox"

codex_sync_config() {
  local script="$CODEX_DOTFILES_DIR/scripts/setup_codex_config.py"

  if command -v python3 >/dev/null 2>&1; then
    python3 "$script" >/dev/null 2>&1 || true
    return
  fi

  if command -v uv >/dev/null 2>&1; then
    uv run --no-project python "$script" >/dev/null 2>&1 || true
  fi
}

codex_sync_skills() {
  local script="$CODEX_DOTFILES_DIR/scripts/setup_codex_skills.py"

  if command -v python3 >/dev/null 2>&1; then
    python3 "$script" >/dev/null 2>&1 || true
    return
  fi

  if command -v uv >/dev/null 2>&1; then
    uv run --no-project python "$script" >/dev/null 2>&1 || true
  fi
}

oc() {
  local env_file="$AI_DOTFILES_DIR/config/opencode/env_unset.txt"
  local unset_args=()

  if [[ -f "$env_file" ]]; then
    while IFS= read -r var; do
      [[ -n "$var" && "$var" != \#* ]] && unset_args+=(-u "$var")
    done < "$env_file"
  fi

  env "${unset_args[@]}" opencode "$@"
}

claude_init() {
  local src="$CLAUDE_DOTFILES_DIR/CLAUDE.md"
  local dest="$PWD/CLAUDE.md"

  if [[ -e "$dest" ]]; then
    echo "CLAUDE.md already exists in this directory. Nothing done."
    return 0
  fi

  cp "$src" "$dest" || return 1
  echo "Init successful: CLAUDE.md created."
}
