#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
BACKEND_PORT="${BACKEND_PORT:-9000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
DRY_RUN=0

if [ "${1:-}" = "--dry-run" ] || [ "${1:-}" = "-n" ]; then
  DRY_RUN=1
fi

info() {
  printf "\033[1;34m[finance]\033[0m %s\n" "$1"
}

warn() {
  printf "\033[1;33m[finance]\033[0m %s\n" "$1"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

pid_running() {
  local pid="$1"
  [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1
}

command_line() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null || true
}

process_cwd() {
  local pid="$1"

  if command_exists lsof; then
    lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | awk '/^n/ { sub(/^n/, ""); print; exit }' || true
  fi
}

matches_expected() {
  local pid="$1"
  local pattern="$2"
  local cmd
  local cwd

  cmd="$(command_line "$pid")"
  cwd="$(process_cwd "$pid")"

  [ -n "$cmd" ] &&
    [[ "$cmd" =~ $pattern ]] &&
    { [[ "$cwd" == "$ROOT_DIR"* ]] || [[ "$cmd" == *"$ROOT_DIR"* ]]; }
}

stop_pid() {
  local name="$1"
  local pid="$2"

  if ! pid_running "$pid"; then
    warn "$name PID $pid is not running"
    return 1
  fi

  if [ "$DRY_RUN" = "1" ]; then
    info "Would stop $name PID $pid: $(command_line "$pid")"
    return 0
  fi

  info "Stopping $name PID $pid"
  kill "$pid" >/dev/null 2>&1 || true

  for _ in {1..30}; do
    if ! pid_running "$pid"; then
      info "$name stopped"
      return 0
    fi
    sleep 0.2
  done

  warn "$name PID $pid is still running. You may need to stop it manually."
  return 1
}

remove_pid_file() {
  local pid_file="$1"

  if [ "$DRY_RUN" = "0" ] && [ -f "$pid_file" ]; then
    rm -f "$pid_file"
  fi
}

stop_from_pid_file() {
  local name="$1"
  local pid_file="$2"
  local pattern="$3"
  local pid

  [ -f "$pid_file" ] || return 1

  pid="$(tr -cd '0-9' <"$pid_file")"
  if [ -z "$pid" ]; then
    warn "$name PID file is empty: $pid_file"
    remove_pid_file "$pid_file"
    return 1
  fi

  if ! pid_running "$pid"; then
    warn "$name PID file is stale: $pid"
    remove_pid_file "$pid_file"
    return 1
  fi

  if ! matches_expected "$pid" "$pattern"; then
    warn "$name PID $pid does not look like this project: $(command_line "$pid")"
    return 1
  fi

  stop_pid "$name" "$pid"
  remove_pid_file "$pid_file"
}

stop_from_port() {
  local name="$1"
  local port="$2"
  local pattern="$3"
  local pids
  local stopped=1
  local pid

  if ! command_exists lsof; then
    warn "Cannot inspect port $port because lsof is not available"
    return 1
  fi

  pids="$(lsof -ti "tcp:$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -z "$pids" ]; then
    info "$name is not listening on port $port"
    return 1
  fi

  for pid in $pids; do
    if matches_expected "$pid" "$pattern"; then
      stop_pid "$name" "$pid" && stopped=0
    else
      warn "Skipping PID $pid on port $port; command does not match $name: $(command_line "$pid")"
    fi
  done

  return "$stopped"
}

main() {
  local stopped_any=1

  mkdir -p "$RUNTIME_DIR"

  stop_from_pid_file "Backend" "$RUNTIME_DIR/backend.pid" "uvicorn|app\.main:app" && stopped_any=0 || true
  stop_from_pid_file "Frontend" "$RUNTIME_DIR/frontend.pid" "vite|node_modules/vite" && stopped_any=0 || true

  stop_from_port "Backend" "$BACKEND_PORT" "uvicorn|app\.main:app" && stopped_any=0 || true
  stop_from_port "Frontend" "$FRONTEND_PORT" "vite|node_modules/vite" && stopped_any=0 || true

  if [ "$DRY_RUN" = "1" ]; then
    info "Dry run complete. No process was stopped."
  elif [ "$stopped_any" = "0" ]; then
    info "Shutdown complete."
  else
    info "No matching service process was found."
  fi
}

main "$@"
