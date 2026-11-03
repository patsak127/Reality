"""Byte snapshot of v4 outputs: repro corpus (full), differential programs, envmatrix corpus CLI run.
Copy of /tmp/snapshot.py (v4-fixes) with paths taken from this file's location. python3 tools/snapshot.py OUT"""
import io, os, sys, shutil, random, hashlib, tempfile
V4 = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [V4 + "/src", V4 + "/tests", V4 + "/tools"]
os.chdir(V4)
out = open(sys.argv[1], "wb")
import run_repros
s = io.StringIO(); run_repros.run_all(run_repros.default_dirs(), s, full=True)
out.write(b"== repros\n" + s.getvalue().encode("utf-8", "surrogateescape"))
import test_differential as TD, helpers
from reality4 import readers as R
from reality4.kernel import check
tmp = tempfile.mkdtemp(prefix="snapdiff-"); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
rng = random.Random(1025)
out.write(b"== differential\n")
for i in range(6000):
    data, nc = TD.table(rng)
    p, h = helpers.tsv(tmp, f"t{i}.tsv", data)
    store = R.Store([p])
    for _ in range(4):
        prog = TD.program(rng, h, nc)
        ok, o = check(prog.encode("ascii"), store)
        out.write(prog.encode() + b"--\n" + "\n".join(o).encode("utf-8", "surrogateescape") + b"\n")
import envmatrix as E
ct = tempfile.mkdtemp(prefix="snapcorpus-"); shutil.rmtree(ct, ignore_errors=True); os.makedirs(ct)
progs, files, roots = E.corpus(ct)
rc, so, se = E.run(sys.executable, progs + ["--files"] + files + ["--root"] + roots, {})
out.write(b"== envmatrix corpus rc=%d\n" % rc + so + b"\n== stderr\n" + se)
out.close()
raw = open(sys.argv[1], "rb").read()
import re
# the same bytes as /tmp/snapshot.py run in /workspace/reality/v4 (paths are the only difference)
norm = re.sub(rb"/tmp/snapcorpus-[a-z0-9_]+", b"/tmp/snapcorpus", re.sub(rb"/tmp/snapdiff-[a-z0-9_]+", b"/tmp/snapdiff", raw.replace(os.path.dirname(V4).encode(), b"/workspace/reality")))
print(hashlib.sha256(raw).hexdigest(), len(raw), "normalised:", hashlib.sha256(norm).hexdigest(), len(norm))
