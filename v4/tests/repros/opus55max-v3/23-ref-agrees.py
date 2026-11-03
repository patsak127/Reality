"""Finding 23: run reality3 and reality3_ref (the second implementation) on the plain-TSV
programs of findings 01, 02, 13 and 19, and on two valid programs outside the differential
generator's line format. Usage: .venv/bin/python findings/23-ref-agrees.py"""
import hashlib, os, signal, sys
sys.path.insert(0, "src")
from reality3 import readers as R
from reality3.kernel import check
from reality3_ref import ref
F = "findings"
tabs = {n: open(os.path.join(F, n), "rb").read() for n in ("01-small.tsv", "13-trials.tsv")}
files = {hashlib.sha256(b).hexdigest(): b for b in tabs.values()}
store = R.Store([os.path.join(F, n) for n in tabs])
def alarm(*a):
    raise TimeoutError("no answer within 5 s")
signal.signal(signal.SIGALRM, alarm)
def both(name, prog):
    ok, out = check(prog, store)
    k = [l.split(":")[0] + ": " + (l.split("]")[0].split("[")[1] if "refused [" in l else "formed") for l in out if l.startswith("line")]
    signal.alarm(5)
    try:
        r = [f"line {ln}: {code if st == 'refused' else 'formed'}" for ln, st, code in ref.run(prog, files)]
    except Exception as e:
        r = f"{type(e).__name__}: {e}"
    signal.alarm(0)
    print(f"{name}\n  reality3:      {k}\n  reality3_ref:  {r}")
for n in ("01-idle-difference", "02-quote-literal", "13-key-vs-where", "19-tolerance-aliasing"):
    both(n + ".rl", open(os.path.join(F, n + ".rl"), "rb").read())
h = hashlib.sha256(tabs["01-small.tsv"]).hexdigest()
both("a comment after a statement", f"file f = sha256:{h}\nlet t = tsv(f)  # the table\nclaim rows(t)\n".encode())
both("no spaces around '='", f"file f = sha256:{h}\nlet t=tsv(f)\nclaim rows(t)\n".encode())
