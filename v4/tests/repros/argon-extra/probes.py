"""Extra box probes for Argon's v2 findings: sub-claims build_repros.py did not run.
Runs against /tmp/rv2-e46b604/v2 (git worktree of e46b6046). Writes fixtures under ./fx/."""
import hashlib, json, os, shutil, subprocess, sys, time, resource
sys.path.insert(0, "/workspace/reality/review-argon-v2/box-repro/work/scratch")
HERE = os.path.dirname(os.path.abspath(__file__)); FX = os.path.join(HERE, "fx")
SRC = "/tmp/rv2-e46b604/v2/src"; PY = "/tmp/rv2venv/bin/python"
def sha(b): return hashlib.sha256(b).hexdigest()
def wb(rel, b):
    p = os.path.join(FX, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(b); return sha(b)
def wt(rel, s): return wb(rel, s.encode())
import struct
def nifti1(dims=(2,2,2,4), tr=2.0, units=10):
    h = bytearray(352); struct.pack_into("<i", h, 0, 348); nd = len(dims)
    struct.pack_into("<8h", h, 40, *([nd] + list(dims) + [1]*(7-nd))); struct.pack_into("<hh", h, 70, 2, 8)
    struct.pack_into("<8f", h, 76, 1.0,1.0,1.0,1.0,float(tr),0,0,0); struct.pack_into("<f", h, 108, 352.0)
    h[123] = units; h[344:348] = b"n+1\x00"; n = 1
    for d in dims: n *= d
    return bytes(h) + b"\0"*n
def manifest(root, out):
    R = os.path.join(FX, root); ents = []
    for dp, dn, fn in os.walk(R):
        for f in fn:
            p = os.path.join(dp, f); b = open(p, "rb").read(); ents.append((os.path.relpath(p, R), sha(b), len(b)))
    ents.sort(key=lambda e: e[0].encode())
    return wt(out, "reality-manifest 1\n" + "".join(f"{h}\t{s}\t{r}\n" for r, h, s in ents))
def run(prog_rel, files, root=None, env=None, memcap_mb=None, timeout=120):
    e = dict(os.environ, PYTHONPATH=SRC, PYTHONIOENCODING="utf-8"); e.update(env or {})
    args = [PY, "-m", "reality2", "check", os.path.join(FX, prog_rel), "--files"] + [os.path.join(FX, f) for f in files]
    if root: args += ["--root", os.path.join(FX, root)]
    pre = (lambda: resource.setrlimit(resource.RLIMIT_AS, (memcap_mb << 20, memcap_mb << 20))) if memcap_mb else None
    t = time.time()
    try:
        r = subprocess.run(args, capture_output=True, env=e, timeout=timeout, preexec_fn=pre)
        out = (r.stdout + r.stderr).decode("utf-8", "replace"); rc = r.returncode
    except subprocess.TimeoutExpired:
        out, rc = f"KILLED after {timeout} s", None
    lines = [l if len(l) < 400 else l[:200] + f" ...[{len(l)} chars]" for l in out.splitlines()]
    return rc, round(time.time() - t, 1), "\n".join(lines[-12:])
def show(tag, res): print(f"===== {tag}: rc={res[0]} wall={res[1]}s\n{res[2]}\n", flush=True)
DD = '{"Name": "p", "BIDSVersion": "1.0.1"}\n'
which = sys.argv[1:] or ["e1","e2","e3","e4","e5","e6","e8","e9","e10"]
# E1 (04 part 4): participants.tsv rows sub-01 and folderless sub-O1 (lookalike labels)
if "e1" in which:
    shutil.rmtree(os.path.join(FX, "e1"), ignore_errors=True)
    wt("e1/dataset_description.json", DD); wt("e1/participants.tsv", "participant_id\tgroup\nsub-01\ta\nsub-O1\tb\n")
    wt("e1/sub-01/func/sub-01_task-x_bold.json", '{"TaskName": "x", "RepetitionTime": 2}\n'); wb("e1/sub-01/func/sub-01_task-x_bold.nii", nifti1())
    m = manifest("e1", "e1.manifest")
    wt("e1.rl", f'dataset d = sha256:{m}\nlet b = bids(d)\nclaim volumes(recording(b, "01", "x")) is 4\nclaim rows(participants(b))\nclaim count(where(participants(b), eq("group", "a")))\n')
    show("E1 folderless lookalike participant sub-O1 next to sub-01", run("e1.rl", ["e1.manifest"], "e1"))
# E2 (04 part 5): acq-01 and acq-O1 lookalike labels in one subject/task
if "e2" in which:
    shutil.rmtree(os.path.join(FX, "e2"), ignore_errors=True)
    wt("e2/dataset_description.json", DD); wt("e2/task-x_bold.json", '{"TaskName": "x", "RepetitionTime": 2}\n')
    wb("e2/sub-01/func/sub-01_task-x_acq-01_bold.nii", nifti1()); wb("e2/sub-01/func/sub-01_task-x_acq-O1_bold.nii", nifti1())
    wt("e2/participants.tsv", "participant_id\nsub-01\n")
    m = manifest("e2", "e2.manifest")
    wt("e2.rl", f'dataset d = sha256:{m}\nlet b = bids(d)\nclaim rows(participants(b))\nclaim volumes(recording(b, "01", "x"))\n')
    show("E2 acq-01 vs acq-O1", run("e2.rl", ["e2.manifest"], "e2"))
# E3 (06): equal-rank sidecars (sub-01/, 2 entities each) that DISAGREE on RepetitionTime
if "e3" in which:
    shutil.rmtree(os.path.join(FX, "e3"), ignore_errors=True)
    wt("e3/dataset_description.json", DD)
    wt("e3/sub-01/sub-01_acq-a_bold.json", '{"TaskName": "x", "RepetitionTime": 3}\n')
    wt("e3/sub-01/sub-01_task-x_bold.json", '{"TaskName": "x", "RepetitionTime": 2}\n')
    wb("e3/sub-01/func/sub-01_task-x_acq-a_bold.nii", nifti1(tr=2.0))
    m = manifest("e3", "e3.manifest")
    wt("e3.rl", f'dataset d = sha256:{m}\nclaim tr(recording(bids(d), "01", "x"))\n')
    show("E3 equal-rank sidecars, TR 3 vs 2", run("e3.rl", ["e3.manifest"], "e3"))
# E4 (10 part 4): deeply nested JSON in dataset_description.json; vary depth and the claim's nesting
if "e4" in which:
    for depth in (900, 960, 975, 985, 995):
        r = f"e4-{depth}"; shutil.rmtree(os.path.join(FX, r), ignore_errors=True)
        wt(f"{r}/dataset_description.json", '{"Name": "p", "BIDSVersion": "1.0.1", "X": ' + "[" * depth + "]" * depth + "}\n")
        wt(f"{r}/participants.tsv", "participant_id\nsub-01\n")
        wt(f"{r}/sub-01/func/sub-01_task-x_bold.json", '{"TaskName": "x", "RepetitionTime": 2}\n'); wb(f"{r}/sub-01/func/sub-01_task-x_bold.nii", nifti1())
        m = manifest(r, f"{r}.manifest")
        wt(f"{r}-shallow.rl", f"dataset d = sha256:{m}\nclaim rows(participants(bids(d)))\n")
        wt(f"{r}-nested.rl", f"dataset d = sha256:{m}\nclaim difference(difference(difference(difference(difference(volumes(recording(bids(d), \"01\", \"x\")), 1), 1), 1), 1), 1)\nclaim rows(participants(bids(d)))\n")
        show(f"E4 depth {depth} shallow", run(f"{r}-shallow.rl", [f"{r}.manifest"], r))
        show(f"E4 depth {depth} nested", run(f"{r}-nested.rl", [f"{r}.manifest"], r))
# E5 (10 part 3b): {"a": 1e99999999} in a sidecar: stall?
if "e5" in which:
    r = "e5"; shutil.rmtree(os.path.join(FX, r), ignore_errors=True)
    wt(f"{r}/dataset_description.json", '{"Name": "p", "BIDSVersion": "1.0.1", "a": 1e99999999}\n')
    wt(f"{r}/participants.tsv", "participant_id\nsub-01\n")
    wt(f"{r}/sub-01/func/sub-01_task-x_bold.json", '{"TaskName": "x", "RepetitionTime": 2}\n'); wb(f"{r}/sub-01/func/sub-01_task-x_bold.nii", nifti1())
    m = manifest(r, f"{r}.manifest"); wt(f"{r}.rl", f"dataset d = sha256:{m}\nclaim rows(participants(bids(d)))\n")
    show("E5 1e99999999 in dataset_description.json (60 s limit)", run(f"{r}.rl", [f"{r}.manifest"], r, timeout=60))
# E6 (11): cp437 and ascii stdout
if "e6" in which:
    W = "/workspace/reality/review-argon-v2/box-repro/work/findings"
    for enc in ("cp437", "ascii", "cp1252", "utf-8"):
        e = dict(os.environ, PYTHONPATH=SRC, PYTHONIOENCODING=enc)
        r = subprocess.run([PY, "-m", "reality2", "check", f"{W}/11-locale-encoding-dependence-and-crash.rl", "--files", f"{W}/11-bad.tsv", f"{W}/11-good.tsv"], capture_output=True, env=e)
        print(f"===== E6 PYTHONIOENCODING={enc}: rc={r.returncode} stdout sha256={sha(r.stdout)[:16]} bytes={len(r.stdout)}\n{r.stdout.decode('latin-1')[-260:]}\n{r.stderr.decode()[-160:]}\n", flush=True)
# E8 (09): RLIMIT_AS sweep on the let chain
if "e8" in which:
    W = "/workspace/reality/review-argon-v2/box-repro/work/findings"
    for cap in (60, 100, 150, 200, 300, None):
        e = dict(os.environ, PYTHONPATH=SRC, PYTHONIOENCODING="utf-8")
        pre = (lambda c=cap: resource.setrlimit(resource.RLIMIT_AS, (c << 20, c << 20))) if cap else None
        t = time.time(); r = subprocess.run([PY, "-m", "reality2", "check", f"{W}/09-let-call-by-name-exponential-blowup.rl", "--files", f"{W}/09-val.tsv"], capture_output=True, env=e, preexec_fn=pre)
        o = (r.stdout + r.stderr).decode("utf-8", "replace").splitlines()
        print(f"===== E8 RLIMIT_AS={cap} MB: rc={r.returncode} wall={time.time()-t:.1f}s stdout={len(r.stdout)} bytes\n" + "\n".join(l[:200] for l in o[-4:]) + "\n", flush=True)
# E9 (12): sum over a non-empty prose selection; and `is 0/-5` on its own
if "e9" in which:
    h = wt("e9.tsv", "id\tprose\nx\thello\ny\tworld\n")
    wt("e9.rl", f'file f = sha256:{h}\nclaim sum(where(tsv(f), eq(1, "x")), 2)\nclaim sum(where(tsv(f), eq(1, "x"), ne(1, "x")), 2)\nclaim count(where(tsv(f), eq(1, "x"), ne(1, "x")))\nclaim share(where(tsv(f), eq(1, "x"))) is 1/-2\nclaim share(where(tsv(f), eq(1, "x"))) is 54/108\n')
    show("E9 sum on prose; empty selection; written ratios", run("e9.rl", ["e9.tsv"]))
# E10 (12 b): manifest size wrong, whole-dataset claim; and extra file with no bytes anywhere
if "e10" in which:
    W = "/workspace/reality/review-argon-v2/box-repro/work/findings"
    print("===== E10 12-manifest.txt sizes vs real sizes"); print(open(f"{W}/12-manifest.txt").read())
    for f in ("dataset_description.json", "participants.tsv"): print(f, os.path.getsize(f"{W}/12-root/{f}"))
