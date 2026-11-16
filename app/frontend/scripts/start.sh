#!/usr/bin/env bash
set -euo pipefail

backend_pid=
frontend_pid=
backend_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../backend" && pwd)"
backend_venv="$backend_dir/.venv"

cleanup() {
  trap - EXIT INT TERM
  if [[ -n "$frontend_pid" ]]; then
    kill "$frontend_pid" 2>/dev/null || true
  fi
  if [[ -n "$backend_pid" ]]; then
    kill "$backend_pid" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

cleanup_stale_build_server() {
  command -v lsof >/dev/null 2>&1 || return 0

  while read -r pid; do
    [[ -n "$pid" ]] || continue
    command=$(ps -o args= -p "$pid" 2>/dev/null || true)
    if [[ "$command" == *"serve -s build"* ]]; then
      echo "Stopping stale production server on port 3000 (PID $pid)"
      kill "$pid" 2>/dev/null || true
    fi
  done < <(lsof -t -iTCP:3000 -sTCP:LISTEN 2>/dev/null)
}

cleanup_stale_build_server

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required to start the backend." >&2
  exit 1
fi

if [[ ! -x "$backend_venv/bin/python" ]]; then
  echo "Creating backend virtual environment at $backend_venv"
  python3 -m venv "$backend_venv"
fi

if ! "$backend_venv/bin/python" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  echo "Installing backend dependencies in the project virtual environment"
  "$backend_venv/bin/python" -m pip install -r "$backend_dir/requirements.txt"
fi

if ! "$backend_venv/bin/python" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  echo "Error: backend dependencies could not be installed in $backend_venv." >&2
  exit 1
fi

npm run start:backend &
backend_pid=$!

npm run start:frontend &
frontend_pid=$!

wait -n "$backend_pid" "$frontend_pid"
