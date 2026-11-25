#!/usr/bin/env bash
# Reality: the Ptolemy demo. Runs run_demo.py (one demo, one source of truth). Needs python3 (3.10+) and ssh-keygen.
set -u
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null || { echo "reality.py needs python3 3.10 or newer (python3 --version: $(python3 --version 2>&1)). Install one, e.g. from python.org or: brew install python"; exit 4; }
HERE="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$HERE/run_demo.py" "$@"
