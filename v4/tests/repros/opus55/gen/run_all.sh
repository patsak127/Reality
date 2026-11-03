#!/bin/sh
# Re-run every finding from the review folder; writes findings/NN-*.out. Usage: sh findings/gen/run_all.sh
# Needs scratch/cmp (the fabricated complete copy): python -c "import sys; sys.path[:0]=['tests','src']; import bidsfix; bidsfix.complete_copy('scratch/cmp')"
cd "$(dirname "$0")/../.." || exit 1
export PYTHONPATH=src PYTHONIOENCODING=utf-8
PY=.venv/Scripts/python.exe
R="$PY -m reality2 check"
BOX=tests/data/ds001734-box
$R findings/01-subset-manifest-conforms.rl --files findings/01-subset.manifest findings/01-box.manifest --root $BOX > findings/01.out
$R findings/02-hash-in-literal-prints-as-file.rl --files findings/02-t.tsv > findings/02.out
$R findings/03-manifest-sizes-and-extra-hashes-unchecked.rl --files findings/03-false-sizes.manifest $BOX/participants.tsv --root $BOX > findings/03.out
{ $PY findings/gen/memlimit_run.py 0 check findings/04-let-doubling-19.rl --files findings/04-n.tsv | grep -v '^  #'; echo "== same, 120 MB limit"; $PY findings/gen/memlimit_run.py 120 check findings/04-let-doubling-19.rl --files findings/04-n.tsv | grep -v '^  #'; } > findings/04.out
{ $R findings/05-int-max-str-digits.rl --files findings/05-long.tsv; echo "== PYTHONINTMAXSTRDIGITS=0"; PYTHONINTMAXSTRDIGITS=0 $R findings/05-int-max-str-digits.rl --files findings/05-long.tsv; } > findings/05.out
( unset PYTHONIOENCODING; $R findings/06-output-encoding.rl | sha256sum; PYTHONIOENCODING=utf-8 $R findings/06-output-encoding.rl | sha256sum; PYTHONIOENCODING=ascii $R findings/06-output-encoding.rl 2>&1 | tail -1; ) > findings/06.out
$PY findings/gen/time_check.py findings/07-quadratic-lookalike-scan.rl findings/07-distinct.tsv > findings/07.out
{ $R findings/08-rename-a.rl --files $BOX/participants.tsv; echo "== renamed"; $R findings/08-rename-b.rl --files $BOX/participants.tsv; } > findings/08.out
$R findings/09-onsets-from-two-frames.rl --files findings/09-fabricated-complete.manifest --root scratch/cmp > findings/09.out
$R findings/10-refused-statement-changes-later-verdict.rl --files findings/01-box.manifest --root $BOX > findings/10.out
$R findings/11-non-ascii-lookalikes-pass.rl --files findings/11-lookalikes.tsv > findings/11.out
$R findings/12-nifti2-tr-never-consistent.rl --files findings/12-nifti2.manifest --root findings/12-nifti2 > findings/12.out
$R findings/13-deep-json-internal-error.rl --files findings/13-deep-json.manifest --root findings/13-deep-json > findings/13.out
$R findings/14-idle-parts-form.rl --files $BOX/participants.tsv > findings/14.out
$R findings/15-tsv-second-readings-not-refused.rl --files findings/15-tsv.tsv > findings/15.out
$R findings/16-unchecked-machine-checkable-rules.rl --files findings/16-dangling-intendedfor.manifest --root scratch/cmp > findings/16.out
$PY findings/gen/no_touch.py > findings/17.out
{ $R findings/18-ref-disagrees.rl --files findings/18-t.tsv; echo "== reality2 vs reality2_ref"; $PY findings/gen/ref_vs_kernel.py; } > findings/18.out
