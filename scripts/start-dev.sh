#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUNTIME_DIR="$ROOT_DIR/.runtime"
BACKEND_PORT="${BACKEND_PORT:-9000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"
FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}"
BUNDLED_BASE="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies"

mkdir -p "$RUNTIME_DIR"

info() {
  printf "\033[1;34m[finance]\033[0m %s\n" "$1"
}

warn() {
  printf "\033[1;33m[finance]\033[0m %s\n" "$1"
}

fail() {
  printf "\033[1;31m[finance]\033[0m %s\n" "$1" >&2
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

url_ok() {
  local url="$1"
  if command_exists curl; then
    curl -fsS "$url" >/dev/null 2>&1
  else
    return 1
  fi
}

wait_for_url() {
  local url="$1"
  local name="$2"
  local log_file="$3"

  for _ in {1..40}; do
    if url_ok "$url"; then
      info "$name ready: $url"
      return 0
    fi
    sleep 0.5
  done

  warn "$name did not respond in time. Last log lines:"
  tail -n 40 "$log_file" 2>/dev/null || true
  return 1
}

python_supports_project() {
  local python_bin="$1"
  "$python_bin" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1
}

find_python() {
  local candidate

  for candidate in \
    "$BACKEND_DIR/.venv312/bin/python3" \
    "$BACKEND_DIR/.venv312/bin/python" \
    "$BACKEND_DIR/.venv/bin/python3" \
    "$BACKEND_DIR/.venv/bin/python"; do
    if [ -x "$candidate" ] && python_supports_project "$candidate"; then
      printf "%s" "$candidate"
      return 0
    fi
  done

  for candidate in python3.12 python3.11 python3.10 python3; do
    if command_exists "$candidate" && python_supports_project "$candidate"; then
      printf "%s" "$(command -v "$candidate")"
      return 0
    fi
  done

  candidate="$BUNDLED_BASE/python/bin/python3"
  if [ -x "$candidate" ] && python_supports_project "$candidate"; then
    printf "%s" "$candidate"
    return 0
  fi

  return 1
}

ensure_backend_venv() {
  local python_bin
  python_bin="$(find_python)" || fail "Python 3.10+ is required. Install Python 3.12, then rerun this launcher."

  if [[ "$python_bin" != "$BACKEND_DIR/.venv"* ]]; then
    info "Creating backend virtual environment with $python_bin"
    "$python_bin" -m venv "$BACKEND_DIR/.venv312"
    python_bin="$BACKEND_DIR/.venv312/bin/python"
  fi

  if ! "$python_bin" -c 'import fastapi, uvicorn, sqlalchemy, pandas' >/dev/null 2>&1; then
    info "Installing backend dependencies"
    "$python_bin" -m pip install -r "$BACKEND_DIR/requirements.txt"
  fi

  printf "%s" "$python_bin"
}

find_node() {
  if command_exists node; then
    command -v node
    return 0
  fi

  local candidate="$BUNDLED_BASE/node/bin/node"
  if [ -x "$candidate" ]; then
    printf "%s" "$candidate"
    return 0
  fi

  return 1
}

find_pnpm() {
  if command_exists pnpm; then
    command -v pnpm
    return 0
  fi

  local candidate="$BUNDLED_BASE/bin/pnpm"
  if [ -x "$candidate" ]; then
    printf "%s" "$candidate"
    return 0
  fi

  return 1
}

ensure_frontend_deps() {
  local node_bin="$1"
  local node_dir
  local pnpm_bin

  node_dir="$(dirname "$node_bin")"

  if [ -x "$FRONTEND_DIR/node_modules/vite/bin/vite.js" ] &&
    (cd "$FRONTEND_DIR" && "$node_bin" node_modules/vite/bin/vite.js --version >/dev/null 2>&1); then
    return 0
  fi

  info "Installing frontend dependencies"
  if pnpm_bin="$(find_pnpm)"; then
    (cd "$FRONTEND_DIR" && PATH="$node_dir:$PATH" "$pnpm_bin" install --config.dangerouslyAllowAllBuilds=true)
  elif command_exists npm; then
    (cd "$FRONTEND_DIR" && npm install)
  else
    fail "Node package manager not found. Install npm or pnpm, then rerun this launcher."
  fi
}

start_backend() {
  local python_bin="$1"
  local log_file="$RUNTIME_DIR/backend.log"
  local pid_file="$RUNTIME_DIR/backend.pid"

  if url_ok "$BACKEND_URL/api/health"; then
    info "Backend already running: $BACKEND_URL"
    return 0
  fi

  info "Starting backend on $BACKEND_URL"
  (
    cd "$BACKEND_DIR"
    nohup "$python_bin" -m uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" >"$log_file" 2>&1 &
    echo $! >"$pid_file"
  )

  wait_for_url "$BACKEND_URL/api/health" "Backend" "$log_file"
}

start_frontend() {
  local node_bin="$1"
  local log_file="$RUNTIME_DIR/frontend.log"
  local pid_file="$RUNTIME_DIR/frontend.pid"

  if url_ok "$FRONTEND_URL/"; then
    info "Frontend already running: $FRONTEND_URL"
    return 0
  fi

  info "Starting frontend on $FRONTEND_URL"
  (
    cd "$FRONTEND_DIR"
    nohup "$node_bin" node_modules/vite/bin/vite.js --host 127.0.0.1 --port "$FRONTEND_PORT" >"$log_file" 2>&1 &
    echo $! >"$pid_file"
  )

  wait_for_url "$FRONTEND_URL/" "Frontend" "$log_file"
}

main() {
  local python_bin
  local node_bin

  python_bin="$(ensure_backend_venv)"
  node_bin="$(find_node)" || fail "Node.js is required. Install Node.js, then rerun this launcher."

  ensure_frontend_deps "$node_bin"
  start_backend "$python_bin"
  start_frontend "$node_bin"

  info "System is ready."
  info "Frontend: $FRONTEND_URL/dashboard"
  info "Backend docs: $BACKEND_URL/docs"
  info "Logs: $RUNTIME_DIR"

  if [ "${SKIP_OPEN:-0}" != "1" ] && command_exists open; then
    open "$FRONTEND_URL/dashboard" >/dev/null 2>&1 || true
  fi
}

main "$@"
