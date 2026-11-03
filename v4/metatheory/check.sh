#!/bin/sh
# Check the Lean metatheory: Scope.lean (a model of Reality v3's design, not of v4; see its header) and Exact.lean (v4's exact decision procedure, see its header). Needs elan with Lean 4.35.0 (no Mathlib).
# Checks every file, prints the axioms each main theorem uses, and fails if
#   - any file does not check (Lean error),
#   - any proof uses `sorry` (Lean's "declaration uses 'sorry'" or sorryAx in #print axioms),
#   - any file declares its own axiom or uses unsafe/extern/implemented_by escape hatches,
#   - any main theorem depends on an axiom other than propext, Classical.choice, Quot.sound.
# Files are checked one after another in a fixed order; the output depends only on the sources.
set -u
cd "$(dirname "$0")" || exit 1
LEAN="${ELAN:-$HOME/.elan/bin/elan} run leanprover/lean4:v4.35.0 lean"
FILES="Scope.lean Exact.lean"
fail=0
if grep -nE '^[[:space:]]*(axiom|unsafe|@\[(extern|implemented_by))' $FILES; then
  echo "FAIL: a file declares an axiom or uses an unsafe/extern escape hatch"; fail=1
fi
for f in $FILES; do
  echo "== $f"
  out=$($LEAN "$f" 2>&1); rc=$?
  printf '%s\n' "$out" | grep "depends on axioms\|does not depend on any axioms"
  if [ $rc -ne 0 ] || printf '%s\n' "$out" | grep -q "error"; then
    printf '%s\n' "$out"; echo "FAIL: $f does not check"; fail=1
  fi
  if printf '%s\n' "$out" | grep -q "sorry"; then
    echo "FAIL: $f uses sorry"; fail=1
  fi
  if printf '%s\n' "$out" | grep "depends on axioms" | sed 's/.*axioms: \[//; s/\]//' | tr ',' '\n' | tr -d ' ' \
      | grep -v '^$' | grep -qvE '^(propext|Classical\.choice|Quot\.sound)$'; then
    echo "FAIL: $f has a theorem depending on a non-standard axiom"; fail=1
  fi
  n=$(printf '%s\n' "$out" | grep -c "depends on axioms\|does not depend on any axioms")
  [ "$n" -gt 0 ] || { echo "FAIL: $f printed no axioms"; fail=1; }
done
if [ $fail -eq 0 ]; then echo "OK: all files check, no sorry, only Lean's standard axioms"; else echo "FAILED"; fi
exit $fail
