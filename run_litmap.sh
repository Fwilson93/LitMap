#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
APP_MODULE="app.main:app"

HOST="${LITMAP_HOST:-127.0.0.1}"
PREFERRED_PORT="${LITMAP_PORT:-8000}"
OPEN_BROWSER="${LITMAP_OPEN_BROWSER:-1}"

log() {
  printf '[LitMap] %s\n' "$*"
}

fail() {
  printf '[LitMap] ERROR: %s\n' "$*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

find_python() {
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "$(command -v python3)"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    printf '%s' "$(command -v python)"
    return 0
  fi
  return 1
}

find_free_port() {
  python_bin="$1"
  preferred="$2"

  "$python_bin" - "$preferred" <<'PY'
import socket
import sys

preferred = int(sys.argv[1])

for port in [preferred, *range(preferred + 1, preferred + 100)]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            continue

    print(port)
    raise SystemExit(0)

raise SystemExit("No free port found")
PY
}

package_check() {
  "$1" - <<'PY'
mods = ["fastapi", "uvicorn", "jinja2", "pydantic", "multipart", "httpx"]
for mod in mods:
    __import__(mod)
PY
}

open_url() {
  url="$1"

  if [[ "$OPEN_BROWSER" != "1" ]]; then
    return 0
  fi

  if command -v open >/dev/null 2>&1; then
    (sleep 1; open "$url" >/dev/null 2>&1 || true) &
  elif command -v xdg-open >/dev/null 2>&1; then
    (sleep 1; xdg-open "$url" >/dev/null 2>&1 || true) &
  fi
}

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    if kill -0 "$SERVER_PID" >/dev/null 2>&1; then
      log "Stopping LitMap server..."
      kill "$SERVER_PID" >/dev/null 2>&1 || true
      wait "$SERVER_PID" 2>/dev/null || true
    fi
  fi
}

trap cleanup EXIT INT TERM

cd "$REPO_ROOT"

[[ -f "pyproject.toml" ]] || fail "pyproject.toml not found"
[[ -f "app/main.py" ]] || fail "app/main.py not found"

PYTHON_BIN="$(find_python)" || fail "Python 3.9+ required"
need_cmd "$PYTHON_BIN"

# -------------------------------
# ✅ NEW: clear cache (safe + robust)
# -------------------------------
log "Clearing Python cache (__pycache__ directories)..."
find "$REPO_ROOT" -name "__pycache__" -type d -exec rm -r {} + || true
# -------------------------------


if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  log "Creating virtual environment"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

VENV_PY="${VENV_DIR}/bin/python"

if ! "$VENV_PY" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 9) else 1)
PY
then
  fail "Virtual env must use Python >=3.9"
fi

log "Ensuring dependencies are installed"

if ! package_check "$VENV_PY" >/dev/null 2>&1; then
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -e '.[dev]'
fi

PORT="$(find_free_port "$VENV_PY" "$PREFERRED_PORT")" || fail "No free port found"
URL="http://${HOST}:${PORT}"

if [[ "$PORT" != "$PREFERRED_PORT" ]]; then
  log "Port ${PREFERRED_PORT} is in use; using ${PORT}"
fi

log "Starting LitMap at ${URL}"
log "Press Ctrl+C to stop cleanly"

open_url "$URL"

"$VENV_PY" -m uvicorn "$APP_MODULE" --reload --host "$HOST" --port "$PORT" &
SERVER_PID=$!

wait "$SERVER_PID"
