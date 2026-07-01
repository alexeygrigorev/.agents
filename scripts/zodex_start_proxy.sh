#!/usr/bin/env bash
set -euo pipefail

HOST="${ZODEX_PROXY_HOST:-127.0.0.1}"
PORT="${ZODEX_PROXY_PORT:-18765}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROXY_REPO="${ZODEX_PROXY_REPO:-alexeygrigorev/zai-codex-proxy}"
PROXY_BIN_DIR="${ZODEX_PROXY_BIN_DIR:-${HOME}/.zodex/bin}"
PROXY_BIN="${ZODEX_PROXY_BIN:-${PROXY_BIN_DIR}/zai-codex-proxy}"
PROXY_VERSION_FILE="${PROXY_BIN}.version"
ZODEX_DIR="${ZODEX_DIR:-${HOME}/.zodex}"
ENV_FILE="${ZODEX_ENV_FILE:-${ZODEX_DIR}/zai.env}"
CONFIG_FILE="${ZODEX_PROXY_CONFIG_FILE:-${ZODEX_DIR}/codex-proxy/config.json}"
PID_FILE="${ZODEX_PROXY_PID_FILE:-${ZODEX_DIR}/codex-proxy/proxy.pid}"
LOG_DIR="${ZODEX_PROXY_LOG_DIR:-${ZODEX_DIR}/log}"
LOG_FILE="${ZODEX_PROXY_LOG_FILE:-${LOG_DIR}/codex-proxy.log}"
RESTART_ON_UPDATE="${ZODEX_PROXY_RESTART_ON_UPDATE:-0}"
PROXY_UPDATED=0

asset_name() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"

  case "$os" in
    Linux) os="linux" ;;
    Darwin) os="darwin" ;;
    MINGW*|MSYS*|CYGWIN*) os="windows" ;;
    *)
      echo "unsupported OS for zodex proxy binary: $os" >&2
      return 1
      ;;
  esac

  case "$arch" in
    x86_64|amd64) arch="amd64" ;;
    aarch64|arm64) arch="arm64" ;;
    *)
      echo "unsupported architecture for zodex proxy binary: $arch" >&2
      return 1
      ;;
  esac

  if [[ "$os" == "windows" ]]; then
    printf 'zai-codex-proxy-%s-%s.exe\n' "$os" "$arch"
  else
    printf 'zai-codex-proxy-%s-%s\n' "$os" "$arch"
  fi
}

latest_proxy_tag() {
  # Prefer an authenticated request via `gh api` (5000 req/h token budget) to
  # avoid the 60 req/h unauthenticated limit that 403s and breaks the launch.
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh api "repos/${PROXY_REPO}/releases/latest" --jq '.tag_name' 2>/dev/null && return
  fi

  # Fall back to a plain unauthenticated request.
  curl -fsSL \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${PROXY_REPO}/releases/latest" \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])'
}

installed_proxy_tag() {
  if [[ -f "$PROXY_VERSION_FILE" ]]; then
    tr -d '[:space:]' <"$PROXY_VERSION_FILE"
    return
  fi

  if [[ -x "$PROXY_BIN" ]]; then
    local version
    version="$("$PROXY_BIN" --version 2>/dev/null | awk '{print $NF}')"
    if [[ -n "$version" ]]; then
      printf 'v%s\n' "$version"
    fi
  fi
}

# Return success (0) if version $1 is strictly newer than version $2, else
# failure (1). Tags may carry an optional leading 'v' (v0.2.3 or 0.2.3) and are
# compared with version sort. Equal or older is "not newer". Used so a newer
# local/dev build is never clobbered by an older published tag.
version_is_newer() {
  local a="${1#v}" b="${2#v}"
  [[ -z "$a" || -z "$b" ]] && return 1
  [[ "$a" == "$b" ]] && return 1
  local newest
  newest="$(printf '%s\n%s\n' "$a" "$b" | sort -V | tail -n1)"
  [[ "$a" == "$newest" ]]
}

install_proxy_binary() {
  local tag="${1:-}"
  local asset url tmp
  asset="$(asset_name)"
  if [[ -n "$tag" ]]; then
    url="https://github.com/${PROXY_REPO}/releases/download/${tag}/${asset}"
  else
    url="https://github.com/${PROXY_REPO}/releases/latest/download/${asset}"
  fi
  tmp="${PROXY_BIN}.download"

  mkdir -p "$PROXY_BIN_DIR"
  echo "Installing zodex proxy from $url" >&2
  curl -fsSL "$url" -o "$tmp"
  chmod +x "$tmp"
  mv "$tmp" "$PROXY_BIN"
  if [[ -n "$tag" ]]; then
    printf '%s\n' "$tag" >"$PROXY_VERSION_FILE"
  else
    "$PROXY_BIN" --version 2>/dev/null | awk '{print "v"$NF}' >"$PROXY_VERSION_FILE" || true
  fi
  PROXY_UPDATED=1
}

ensure_proxy_binary() {
  local latest_tag installed_tag
  latest_tag="$(latest_proxy_tag)"
  installed_tag="$(installed_proxy_tag || true)"

  if [[ ! -x "$PROXY_BIN" ]]; then
    install_proxy_binary "$latest_tag"
    return
  fi

  # Only update when the latest release is strictly newer than what is
  # installed (or the installed version is unknown). This avoids clobbering a
  # newer local/dev build — e.g. a binary built from source ahead of the latest
  # published release — and skips pointless reinstalls when they already match.
  if [[ -n "$latest_tag" ]] && { [[ -z "$installed_tag" ]] || version_is_newer "$latest_tag" "$installed_tag"; }; then
    echo "Updating zodex proxy from ${installed_tag:-unknown} to ${latest_tag}" >&2
    install_proxy_binary "$latest_tag"
  fi
}

listener_pids() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true
  elif command -v fuser >/dev/null 2>&1; then
    fuser -n tcp "$PORT" 2>/dev/null || true
  fi
}

stop_existing_proxy() {
  local pids pid
  pids="$(listener_pids | tr '\n' ' ')"

  if [[ -f "$PID_FILE" ]]; then
    pid="$(tr -d '[:space:]' <"$PID_FILE")"
    if [[ -n "$pid" && " $pids " != *" $pid "* ]] && kill -0 "$pid" 2>/dev/null; then
      pids="${pids} ${pid}"
    fi
  fi

  for pid in $pids; do
    if [[ "$pid" != "$$" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "Stopping existing zodex proxy process $pid" >&2
      kill "$pid" 2>/dev/null || true
    fi
  done

  for _ in {1..50}; do
    if ! curl -fsS "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
      rm -f "$PID_FILE"
      return
    fi
    sleep 0.1
  done

  for pid in $pids; do
    if [[ "$pid" != "$$" ]] && kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  done
  rm -f "$PID_FILE"
}

if curl -fsS "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
  if ensure_proxy_binary; then
    if [[ "$PROXY_UPDATED" == "0" ]]; then
      exit 0
    fi
    if [[ "$RESTART_ON_UPDATE" == "1" ]]; then
      stop_existing_proxy
    else
      echo "Installed latest zodex proxy binary; keeping already-running proxy on ${HOST}:${PORT}" >&2
      exit 0
    fi
  else
    echo "Could not check/install latest zodex proxy; using already-running proxy on ${HOST}:${PORT}" >&2
    exit 0
  fi
else
  # Proxy not running. If the update check fails (e.g. GitHub API rate limit),
  # fall back to an already-installed binary instead of aborting the launch.
  ensure_proxy_binary || {
    if [[ -x "$PROXY_BIN" ]]; then
      echo "Could not check for latest zodex proxy; using installed binary" >&2
    else
      echo "Could not install zodex proxy binary (GitHub API unavailable)" >&2
      exit 1
    fi
  }
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "zodex profile is missing $ENV_FILE. Run: ${REPO_DIR}/configure.sh zodex" >&2
  exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "zodex proxy config is missing $CONFIG_FILE. Run: ${REPO_DIR}/configure.sh zodex" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"
if [[ -z "${ZAI_API_KEY:-}" ]]; then
  echo "zodex profile is missing ZAI_API_KEY in $ENV_FILE" >&2
  exit 1
fi

mkdir -p "$LOG_DIR" "$(dirname "$PID_FILE")"
if command -v setsid >/dev/null 2>&1; then
  setsid env CODEX_PROXY_ZAI_API_KEY="$ZAI_API_KEY" "$PROXY_BIN" --config "$CONFIG_FILE" \
    >"$LOG_FILE" 2>&1 </dev/null &
else
  nohup env CODEX_PROXY_ZAI_API_KEY="$ZAI_API_KEY" "$PROXY_BIN" --config "$CONFIG_FILE" \
    >"$LOG_FILE" 2>&1 </dev/null &
fi
printf '%s\n' "$!" >"$PID_FILE"

for _ in {1..50}; do
  if curl -fsS "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
    exit 0
  fi
  sleep 0.1
done

echo "zodex proxy did not become ready on ${HOST}:${PORT}. Log: $LOG_FILE" >&2
tail -n 40 "$LOG_FILE" >&2 || true
exit 1
