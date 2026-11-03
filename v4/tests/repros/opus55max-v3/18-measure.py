"""Finding 18: work that the cost model (SPEC 9.8) does not charge.
Writes inputs under /tmp/reality-review-18/ and runs reality3's own check() in-process, printing
wall time and the steps the statement was charged (store.steps.n; the bound is 200 000 000).
  A. composite key(): P columns, every key part needed, M filler rows. Work ~ P*P*rows.
  B. BIDS inheritance: N subjects, each with a BOLD image and a sidecar JSON (one shared copy of
     each, named N times by a hand-written manifest). Work ~ N*N.
Usage: .venv/bin/python findings/18-measure.py key P M | inherit N"""
import hashlib, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import _lib as L
from reality3 import readers as R
from reality3.kernel import check
D = "/tmp/reality-review-18"; os.makedirs(D, exist_ok=True)

def key(P, M):
    rows = [["a"] * P]                       # the row the key picks
    for j in range(P):                       # row j differs from it in column j only
        r = ["a"] * P; r[j] = "b"; rows.append(r)
    rows += [["a"] * (P - 1) + ["c"]] * M    # filler rows differ in the last column only
    data = ("\t".join(f"c{j}" for j in range(1, P + 1)) + "\n" + "\n".join("\t".join(r) for r in rows) + "\n").encode()
    p = os.path.join(D, f"key-{P}-{M}.tsv"); open(p, "wb").write(data)
    pairs = ", ".join(f'{j}, "a"' for j in range(1, P + 1))
    prog = f"file f = sha256:{hashlib.sha256(data).hexdigest()}\nclaim cell(tsv(f), key({pairs}), 1)\n"
    return prog, [p], f"{len(data)} bytes, {len(rows)} rows, {P} columns"

def inherit(N):
    d = os.path.join(D, f"inherit-{N}"); os.makedirs(d, exist_ok=True)
    blobs = {"desc": b'{"Name": "inheritance load", "BIDSVersion": "1.0.1"}',
             "task": b'{"TaskName": "x", "RepetitionTime": 1}', "side": b'{"EchoTime": 0.03}',
             "img": L.nifti1((2, 2, 2, 5), pixdim4=1.0)}
    hs = {}
    for k, b in blobs.items():
        open(os.path.join(d, k), "wb").write(b); hs[k] = (hashlib.sha256(b).hexdigest(), len(b))
    ents = [("dataset_description.json", "desc"), ("task-x_bold.json", "task")]
    for i in range(N):
        s = f"sub-{i:05d}"
        ents += [(f"{s}/func/{s}_task-x_bold.json", "side"), (f"{s}/func/{s}_task-x_bold.nii", "img")]
    ents.sort(key=lambda e: e[0].encode())
    man = ("reality-manifest 1\n" + "".join(f"{hs[k][0]}\t{hs[k][1]}\t{p}\n" for p, k in ents)).encode()
    open(os.path.join(d, "manifest"), "wb").write(man)
    prog = f'dataset d = sha256:{hashlib.sha256(man).hexdigest()}\nclaim tr(recording(bids(d), "00000", "x"))\n'
    return prog, [d], f"{N} subjects, manifest {len(man)} bytes"

prog, files, what = key(int(sys.argv[2]), int(sys.argv[3])) if sys.argv[1] == "key" else inherit(int(sys.argv[2]))
# Keep the program next to the finding: 18-uncharged-quadratic-work.rl is the key() program,
# 18b-inheritance.rl the BIDS one (of the last size run; the files it names are in /tmp).
out_name = "18-uncharged-quadratic-work.rl" if sys.argv[1] == "key" else "18b-inheritance.rl"
open(os.path.join(HERE, out_name), "w").write(prog)
store = R.Store(files)
t = time.time(); ok, out = check(prog.encode(), store); dt = time.time() - t
print(f"{sys.argv[1]} {' '.join(sys.argv[2:])}: {what}; {dt:.1f} s; steps charged to the claim: {store.steps.n:,}; {out[0][:90]}")
