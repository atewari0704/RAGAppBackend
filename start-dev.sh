#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/.venv/bin/activate"

if [[ ! -f "$VENV_PATH" ]]; then
  echo "Virtual environment not found at: $VENV_PATH"
  echo "Create it first, then re-run this script."
  exit 1
fi

source "$VENV_PATH"

cleanup() {
  if [[ -n "${UVICORN_PID:-}" ]] && kill -0 "$UVICORN_PID" 2>/dev/null; then
    kill "$UVICORN_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "Starting FastAPI app with uvicorn..."
uvicorn main:app &
UVICORN_PID=$!

# Give uvicorn a moment to boot before starting Inngest dev server
sleep 5

echo "Starting Inngest dev server..."
npx -y inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest
