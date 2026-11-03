#!/bin/sh
# usage: run.sh <file> [extra mutator args]   (from mutation-v4/; a git archive of v4 at 03c5c2f)
cd /workspace/reality/mutation-v4/v4
export PATH=/workspace/mutation-venv/bin:$PATH
f="$1"; shift
name=$(basename "$f" .py)
exec /workspace/tools-3p/mutator/mutator --max-workers 7 --verbose \
  --test-command 'REALITY4_SRC="$PWD/src" /workspace/mutation-venv/bin/python -m pytest -p no:cacheprovider -q -x tests --deselect tests/test_differential.py::test_differential' \
  "$@" "$f" > ../logs/$name.log 2>&1
