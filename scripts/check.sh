#!/usr/bin/env bash
# 本地质量门禁：backend ruff → pytest → frontend lint → type-check → test → build
# 用法：在仓库根执行  ./scripts/check.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

info() { printf "\033[1;34m[check]\033[0m %s\n" "$1"; }
fail() { printf "\033[1;31m[check]\033[0m %s\n" "$1" >&2; exit 1; }

resolve_python() {
  if [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
    echo "$BACKEND_DIR/.venv/bin/python"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return
  fi
  fail "未找到 Python（期望 backend/.venv 或 python3）"
}

ensure_node() {
  if command -v node >/dev/null 2>&1; then
    return
  fi
  if [[ -x /opt/homebrew/opt/node@22/bin/node ]]; then
    export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
    return
  fi
  if [[ -x /opt/homebrew/opt/node/bin/node ]]; then
    export PATH="/opt/homebrew/opt/node/bin:$PATH"
    return
  fi
  fail "未找到 node。请安装 Node.js 18+（推荐: brew install node@22 && brew link node@22）"
}

run_frontend() {
  local script="$1"
  cd "$FRONTEND_DIR"
  if command -v bun >/dev/null 2>&1 && [[ -f bun.lockb || -f bun.lock ]]; then
    bun run "$script"
  elif command -v npm >/dev/null 2>&1; then
    npm run "$script"
  else
    fail "未找到 bun 或 npm"
  fi
}

info "1/6 backend ruff"
PY="$(resolve_python)"
info "python: $PY"
(
  cd "$BACKEND_DIR"
  if [[ -x "$BACKEND_DIR/.venv/bin/ruff" ]]; then
    "$BACKEND_DIR/.venv/bin/ruff" check app tests
  elif command -v ruff >/dev/null 2>&1; then
    ruff check app tests
  else
    fail "未找到 ruff。请: cd backend && .venv/bin/pip install -r requirements-dev.txt"
  fi
)

info "2/6 backend pytest"
(
  cd "$BACKEND_DIR"
  "$PY" -m pytest -q
)

info "3/6 frontend lint"
ensure_node
info "node: $(command -v node) ($(node -v))"
run_frontend lint

info "4/6 frontend type-check"
run_frontend type-check

info "5/6 frontend unit tests"
run_frontend test

info "6/6 frontend build"
run_frontend build

info "全部通过 ✓"
