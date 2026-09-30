#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"
HOST="${LABROW_HOST:-0.0.0.0}"
PORT="${LABROW_PORT:-8000}"
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required"
  exit 1
fi
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" || {
  echo "python 3.11 or newer is required"
  exit 1
}
echo "starting the application server on ${HOST}:${PORT}"
exec python3 -m api.server --host "$HOST" --port "$PORT" --repo "$REPO_ROOT"
