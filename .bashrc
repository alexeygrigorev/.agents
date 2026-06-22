# Shared AI assistant aliases and functions

export AI_DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AGENTS_DOTFILES_DIR="$AI_DOTFILES_DIR"

alias c="claude"
alias cc="claude -c"
alias csp="claude --dangerously-skip-permissions"
alias ccsp="claude -c --dangerously-skip-permissions"
alias cy="codex --dangerously-bypass-approvals-and-sandbox"

# zlaude: Claude Code routed to Z.AI via the ~/.zlaude profile
# (configure with: ./configure.sh zlaude).
# Runs claude with a clean env: any ambient ANTHROPIC_* vars (e.g. a project
# .env's ANTHROPIC_MODEL/API_KEY) override ~/.zlaude/settings.json, so strip
# them (env -u) and let the profile's settings.json take full control.
_zlaude_run() {
  local env_file="$AGENTS_DOTFILES_DIR/config/claude/zlaude_env_unset.txt"
  local unset_args=()

  if [[ -f "$env_file" ]]; then
    while IFS= read -r var; do
      [[ -n "$var" && "$var" != \#* ]] && unset_args+=(-u "$var")
    done < "$env_file"
  fi

  env "${unset_args[@]}" CLAUDE_CONFIG_DIR="$HOME/.zlaude" claude "$@"
}

zlaude() { _zlaude_run "$@"; }
z()      { _zlaude_run "$@"; }
zc()     { _zlaude_run -c "$@"; }
zsp()    { _zlaude_run --dangerously-skip-permissions "$@"; }

# zodex: Codex routed to Z.AI via the ~/.zodex profile
# (configure with: ./configure.sh zodex).
_zodex_run() {
  local env_file="$AGENTS_DOTFILES_DIR/config/codex/zodex_env_unset.txt"
  local profile_env="$HOME/.zodex/zai.env"
  local unset_args=()

  if [[ -f "$env_file" ]]; then
    while IFS= read -r var; do
      [[ -n "$var" && "$var" != \#* ]] && unset_args+=(-u "$var")
    done < "$env_file"
  fi

  if [[ ! -f "$profile_env" ]]; then
    echo "zodex is not configured. Run: $AGENTS_DOTFILES_DIR/configure.sh zodex" >&2
    return 1
  fi

  "$AGENTS_DOTFILES_DIR/scripts/zodex_start_proxy.sh" || return

  env "${unset_args[@]}" CODEX_HOME="$HOME/.zodex" codex "$@"
}

zodex() { _zodex_run "$@"; }
zy()    { _zodex_run --dangerously-bypass-approvals-and-sandbox "$@"; }

codex_sync_config() {
  local script="$AGENTS_DOTFILES_DIR/scripts/setup_codex_config.py"

  if command -v python3 >/dev/null 2>&1; then
    python3 "$script" >/dev/null 2>&1 || true
    return
  fi

  if command -v uv >/dev/null 2>&1; then
    uv run --no-project python "$script" >/dev/null 2>&1 || true
  fi
}

codex_sync_skills() {
  local script="$AGENTS_DOTFILES_DIR/scripts/setup_codex_skills.py"

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
  local src="$AGENTS_DOTFILES_DIR/CLAUDE.md"
  local dest="$PWD/CLAUDE.md"

  if [[ -e "$dest" ]]; then
    echo "CLAUDE.md already exists in this directory. Nothing done."
    return 0
  fi

  cp "$src" "$dest" || return 1
  echo "Init successful: CLAUDE.md created."
}
