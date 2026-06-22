#!/usr/bin/env bash
set -euo pipefail

HOST="${ZODEX_PROXY_HOST:-127.0.0.1}"
PORT="${ZODEX_PROXY_PORT:-18765}"
URL="http://${HOST}:${PORT}/api/config"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROXY_REPO="${ZODEX_PROXY_REPO:-alexeygrigorev/zai-codex-proxy}"
PROXY_BIN_DIR="${ZODEX_PROXY_BIN_DIR:-${HOME}/.zodex/bin}"
PROXY_BIN="${ZODEX_PROXY_BIN:-${PROXY_BIN_DIR}/zai-codex-proxy}"
ZODEX_DIR="${HOME}/.zodex"
ENV_FILE="${ZODEX_DIR}/zai.env"
CONFIG_FILE="${ZODEX_DIR}/codex-proxy/config.json"
LOG_DIR="${ZODEX_DIR}/log"
LOG_FILE="${LOG_DIR}/codex-proxy.log"

if curl -fsS "http://${HOST}:${PORT}/ui" >/dev/null 2>&1; then
  exit 0
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "zodex profile is missing $ENV_FILE. Run: ${REPO_DIR}/configure.sh zodex" >&2
  exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "zodex proxy config is missing $CONFIG_FILE. Run: ${REPO_DIR}/configure.sh zodex" >&2
  exit 1
fi

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

install_proxy_binary() {
  local asset url tmp
  asset="$(asset_name)"
  url="https://github.com/${PROXY_REPO}/releases/latest/download/${asset}"
  tmp="${PROXY_BIN}.download"

  mkdir -p "$PROXY_BIN_DIR"
  echo "Installing zodex proxy from $url" >&2
  curl -fL "$url" -o "$tmp"
  chmod +x "$tmp"
  mv "$tmp" "$PROXY_BIN"
}

if [[ ! -x "$PROXY_BIN" ]]; then
  install_proxy_binary
fi

# shellcheck disable=SC1090
source "$ENV_FILE"
if [[ -z "${ZAI_API_KEY:-}" ]]; then
  echo "zodex profile is missing ZAI_API_KEY in $ENV_FILE" >&2
  exit 1
fi

mkdir -p "$LOG_DIR"
(
  exec nohup env CODEX_PROXY_ZAI_API_KEY="$ZAI_API_KEY" "$PROXY_BIN" --config "$CONFIG_FILE"
) >"$LOG_FILE" 2>&1 &

for _ in {1..50}; do
  if curl -fsS "http://${HOST}:${PORT}/ui" >/dev/null 2>&1; then
    exit 0
  fi
  sleep 0.1
done

echo "zodex proxy did not become ready on ${HOST}:${PORT}. Log: $LOG_FILE" >&2
tail -n 40 "$LOG_FILE" >&2 || true
exit 1
