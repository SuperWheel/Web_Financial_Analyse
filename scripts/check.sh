#!/usr/bin/env bash
# 本地质量门禁：后端 pytest → 前端 type-check → 前端 production build
# 用法：在仓库根执行  ./scripts/check.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

info() { printf "\033[1;34m[check]\033[0m %s\n" "$1"; }
fail() { printf "\033[1;31m[check]\033[0m %s\n" "$1" >&2; exit 1; }

# Prefer project venv, then PATH python
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

# Ensure node is available for vue-tsc shebang (bun alone is not enough)
ensure_node() {
  if command -v node >/dev/null 2>&1; then
    return
  fi
  # Common Homebrew keg-only path
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

info "1/3 backend pytest"
PY="$(resolve_python)"
info "python: $PY"
(
  cd "$BACKEND_DIR"
  "$PY" -m pytest -q
)

info "2/3 frontend type-check"
ensure_node
info "node: $(command -v node) ($(node -v))"
(
  cd "$FRONTEND_DIR"
  if command -v bun >/dev/null 2>&1 && [[ -f bun.lockb || -f bun.lock ]]; then
    bun run type-check
  elif command -v npm >/dev/null 2>&1; then
    npm run type-check
  else
    fail "未找到 bun 或 npm"
  fi
)

info "3/3 frontend build"
(
  cd "$FRONTEND_DIR"
  if command -v bun >/dev/null 2>&1 && [[ -f bun.lockb || -f bun.lock ]]; then
    bun run build
  elif command -v npm >/dev/null 2>&1; then
    npm run build
  else
    fail "未找到 bun 或 npm"
  fi
)

info "全部通过 ✓"
