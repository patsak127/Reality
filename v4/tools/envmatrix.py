"""Run one fixed corpus of programs under many interpreter settings and compare the output bytes.

python3 tools/envmatrix.py [--python PATH]

Corpus: every reproducer program in tests/repros (with all of tests/repros and the box copy
supplied), and the acceptance programs (tests/acceptance.py) on the box copy, the decisions
table and the FABRICATED complete copy. One CLI call per setting checks the whole corpus.

Settings varied, one at a time from a UTF-8 baseline:
  memory (RLIMIT_AS)        at or above the 2 GiB floor (SPEC 9.4): 2 GiB, 4 GiB, unlimited, which
                            must equal the baseline; below it: 128 MB, 512 MB, 1 GB, 2 GiB - 1 MB,
                            which must each give X002: exit 3, exactly the floor line of SPEC 9.4
                            on stdout, nothing on stderr (nothing checked, by design)
  PYTHONIOENCODING          utf-8, ascii, cp437, cp1252, latin-1 (PYTHONUTF8=0)
  PYTHONINTMAXSTRDIGITS     640, 4300, 0
  recursion limit at start  300, 1000, 100000 (set before reality4 is imported)
  PYTHONHASHSEED            0, 1, random
Every output (stdout bytes, stderr bytes, exit code) must equal the baseline's. Prints a table
and exits 1 on any difference. Report only; nothing in v3/ is written."""
import hashlib
import os
import resource
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [os.path.join(V3, "src"), os.path.join(V3, "tests"), HERE]
import acceptance as A  # noqa: E402
import bidsfix  # noqa: E402
import helpers  # noqa: E402
import run_repros  # noqa: E402

WRAP = ("import sys, runpy; sys.setrecursionlimit(int(sys.argv.pop(1))); "
        "sys.argv[0] = 'reality4'; runpy.run_module('reality4', run_name='__main__')")


def corpus(tmp):
    progs = []
    for d in run_repros.default_dirs():
        progs += list(run_repros.programs(d))
    box = bidsfix.box_copy()
    md = os.path.join(tmp, "m")
    os.makedirs(md)
    cmp_root = bidsfix.complete_copy(os.path.join(tmp, "complete"))
    subs = {"P": A.P, "EV": A.EV, "BOX": helpers.manifest(box, md), "CMP": helpers.manifest(cmp_root, md)}
    p, subs["DEC"] = helpers.tsv(tmp, "decisions.tsv", A.DECISIONS)
    for cid, fixture, prog, expect, _ in A.CASES:
        if prog is None or fixture.startswith("mini"):
            continue
        path = os.path.join(tmp, f"acc-{cid}.rl")
        with open(path, "w", encoding="ascii") as f:
            f.write(prog.format(**subs))
        progs.append(path)
    # stress: doubling lets (sort bound R006), an 80 000-row lookalike scan, a 5 000-digit cell
    big, hb = helpers.tsv(tmp, "big.tsv", "id\tv\n" + "".join(f"k{i}\t{i}\n" for i in range(80000)))
    nt, hn = helpers.tsv(tmp, "n.tsv", "x\ty\n1\t2\n" + "9" * 5000 + "\t3\n")
    lets = "let a0 = number(cell(tsv(g), 1, 1))\nlet b0 = number(cell(tsv(g), 1, 2))\n"
    lets += "".join(f"let a{i + 1} = difference(a{i}, b{i})\nlet b{i + 1} = difference(b{i}, a{i})\n" for i in range(40))
    stress = {"stress-doubling.rl": f"file g = sha256:{hn}\n" + lets + "claim a40\nclaim number(cell(tsv(g), 2, 1))\n",
              "stress-scan.rl": f"file f = sha256:{hb}\nclaim count(where(tsv(f), eq(1, \"zz\")))\nclaim mean(tsv(f), 2)\n"}
    for name, text in stress.items():
        path = os.path.join(tmp, name)
        with open(path, "w", encoding="ascii") as f:
            f.write(text)
        progs.append(path)
    files = run_repros.default_dirs() + [box, md, p, cmp_root, big, nt]
    roots = []
    for d in run_repros.default_dirs():
        roots += run_repros.roots_in(d)
    roots = sorted(set(roots + [cmp_root]))
    return progs, files, roots


def run(py, args, env_over, mem=None, rec=None):
    env = {"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "/tmp"), "PYTHONPATH": os.path.join(V3, "src"),
           "PYTHONHASHSEED": "0", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "LC_ALL": "C.UTF-8",
           "PYTHONDONTWRITEBYTECODE": "1"}
    for k, v in env_over.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v

    def limit():
        if mem:
            resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    # cwd is "/", so a relative --python path is made absolute here (it is resolved against the caller's cwd)
    cmd = [os.path.abspath(py) if os.sep in py else py, "-c", WRAP, str(rec or 1000)] + ["check"] + args
    r = subprocess.run(cmd, env=env, capture_output=True, timeout=3600, preexec_fn=limit, cwd="/")
    return r.returncode, r.stdout, r.stderr


SETTINGS = [("baseline", {}, None, None)]
SETTINGS += [(f"memory {m // 2**20} MB", {}, m, None) for m in (2048 * 2**20, 4096 * 2**20)]
BELOW_FLOOR = [128 * 2**20, 512 * 2**20, 1024 * 2**20, 2047 * 2**20]


def x002_ok(rc, out, err, mem):
    """SPEC 9.4: below the floor nothing is checked: exit 3 and exactly the X002 line naming the limit."""
    line = f"no verdict: this machine's memory limit ({mem} bytes) is below Reality's floor (2147483648 bytes); nothing was checked\n"
    return rc == 3 and out == line.encode() and err == b""
SETTINGS += [(f"io {e}", {"PYTHONIOENCODING": e, "PYTHONUTF8": "0"}, None, None) for e in ("ascii", "cp437", "cp1252", "latin-1")]
SETTINGS += [("io unset, locale C", {"PYTHONIOENCODING": None, "PYTHONUTF8": "0", "LC_ALL": "C"}, None, None)]
SETTINGS += [(f"int digits {d}", {"PYTHONINTMAXSTRDIGITS": d}, None, None) for d in ("640", "4300", "0")]
SETTINGS += [(f"recursion {r}", {}, None, r) for r in (300, 100000)]
SETTINGS += [(f"hashseed {s}", {"PYTHONHASHSEED": s}, None, None) for s in ("1", "random")]


def main(argv):
    py = argv[argv.index("--python") + 1] if "--python" in argv else sys.executable
    with tempfile.TemporaryDirectory() as tmp:
        progs, files, roots = corpus(tmp)
        args = progs + ["--files"] + files + ["--root"] + roots
        base = None
        bad = 0
        print(f"corpus: {len(progs)} programs; interpreter {py}")
        for name, env, mem, rec in SETTINGS:
            rc, out, err = run(py, args, env, mem, rec)
            sig = (rc, hashlib.sha256(out).hexdigest()[:16], hashlib.sha256(err).hexdigest()[:16])
            if base is None:
                base = (rc, out, err)
                same = "baseline"
            else:
                same = "identical" if (rc, out, err) == base else "DIFFERENT"
                bad += same != "identical"
            print(f"{name:28s} exit {rc}  stdout {sig[1]} ({len(out)} B)  stderr {sig[2]} ({len(err)} B)  {same}")
            if same == "DIFFERENT":
                a, b = base[1].split(b"\n"), out.split(b"\n")
                for i, (x, y) in enumerate(zip(a, b)):
                    if x != y:
                        print(f"    first difference at output line {i + 1}:\n      base: {x[:160]!r}\n      this: {y[:160]!r}")
                        break
                if err:
                    print(f"    stderr: {err[-300:]!r}")
        for mem in BELOW_FLOOR:
            rc, out, err = run(py, args, {}, mem, None)
            ok = x002_ok(rc, out, err, mem)
            bad += not ok
            print(f"{'memory ' + str(mem // 2**20) + ' MB (below floor)':28s} exit {rc}  stdout {len(out)} B  {'X002 as specified' if ok else 'NOT X002'}")
            if not ok:
                print(f"    stdout: {out[-300:]!r}\n    stderr: {err[-300:]!r}")
        print(f"{bad} difference(s) from the baseline over {len(SETTINGS) - 1} settings and {len(BELOW_FLOOR)} below-floor settings")
        return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
