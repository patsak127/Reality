#!/usr/bin/env bash
# In-repo startup (uses checkout sources via paths.py). For standalone, use the pack's start.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8765}"
HOST="${HOST:-127.0.0.1}"
exec "${PYTHON:-python3}" "$ROOT/serve.py" --host "$HOST" --port "$PORT" --root "$ROOT"
