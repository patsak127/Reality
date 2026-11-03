"""Finding 20: check 2 cannot see a BIDS reader that attaches the wrong file to a recording.

    python -I findings\\20-check2-not-independent.py

tests/test_findings.py::test_03_check2_refuses_an_unnamed_read shows check 2 catching a plain-TSV
computation that reads a file its sort does not name. Here the planted bug is in the BIDS reader
instead: bids101.read pairs sub-01 run 1's BOLD file with run 2's events file. The sort and the
trace are both built from the same variable (Recording.events), so they agree, check 2 passes,
and a wrong onset forms with a sort that names the wrong file as run 1's events."""
import os
import sys

F = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(F)
sys.path.insert(0, os.path.join(ROOT, "src"))
from reality2 import bids101, readers  # noqa: E402
from reality2.kernel import check  # noqa: E402

prog = open(os.path.join(F, "20-check2-not-independent.rl"), "rb").read()
files, roots = [os.path.join(F, "20-m")], [os.path.join(F, "20-ds")]

print("== unmodified reader")
print("\n".join(check(prog, readers.Store(files, roots))[1]))

orig = bids101.read


def planted(store, mh):
    ds = orig(store, mh)
    run1 = next(r for r in ds.recordings if dict(r.ents).get("run") == "1")
    run2 = next(r for r in ds.recordings if dict(r.ents).get("run") == "2")
    run1.events = run2.events          # the bug: run 1 gets run 2's events file
    return ds


bids101.read = planted
print("\n== reader with a planted bug (run 1 paired with run 2's events file)")
print("\n".join(check(prog, readers.Store(files, roots))[1]))
for p, (h, _) in readers.parse_manifest(open(os.path.join(F, "20-m", os.listdir(os.path.join(F, "20-m"))[0]), "rb").read(), "x").items():
    if p.endswith("_events.tsv"):
        print(f"  (manifest: {p} = sha256:{h})")
