#!/usr/bin/env bash
# One-command MacBook demo of Reality's req layer (throwaway TEST key only).
# Needs: Python 3.13+ and OpenSSH (ssh-keygen). No pip packages. No GGUF judge.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
WORK="${REALITY_DEMO_WORK:-/tmp/reality-macbook-demo}"

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "missing: $1" >&2; exit 1; }
}

pick_py() {
  if [ -n "${PYTHON:-}" ]; then
    echo "$PYTHON"
    return
  fi
  for c in python3.13 python3; do
    command -v "$c" >/dev/null 2>&1 || continue
    ver="$("$c" -c 'import sys; print("%d.%d"%sys.version_info[:2])' 2>/dev/null || true)"
    maj="${ver%%.*}"; min="${ver#*.}"
    if [ -n "$ver" ] && [ "$maj" -gt 3 ] 2>/dev/null; then echo "$c"; return; fi
    if [ -n "$ver" ] && [ "$maj" -eq 3 ] && [ "$min" -ge 13 ] 2>/dev/null; then echo "$c"; return; fi
  done
  return 1
}

need ssh-keygen
PY="$(pick_py)" || { echo "need Python 3.13+ (set PYTHON=…)" >&2; exit 1; }
ver="$("$PY" -c 'import sys; print("%d.%d"%sys.version_info[:2])')"
echo "using $PY ($ver)"

export PYTHONPATH="$ROOT/req/src:$ROOT/v4/src"
rm -rf "$WORK"
mkdir -p "$WORK"

echo "=== 1/2  req demo (HOLDS / DOES NOT HOLD / refused bar-edit / composite Gate) ==="
echo "work: $WORK/demo"
echo "key:  REALITY-TEST-KEY-NOT-PATSAK (throwaway; not Patsak)"
"$PY" "$ROOT/req/demo/demo.py" --work "$WORK/demo"

echo
echo "=== 2/2  AI-eval composite CI gate (pass exit 0, fail exit 1) ==="
"$PY" "$ROOT/req/demo/ai_eval_gate.py" --work "$WORK/gate" --mode both

echo
echo "Done. Cue sheet: req/demo/macbook/CUE-SHEET.md"
echo "Live 1.8 GB Qwen judge is NOT part of this laptop demo."
