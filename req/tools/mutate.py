"""Mutation sweep over req/'s trusted files (gate E). Untrusted tool; not part of Reality.

Each mutant changes one operator on one line of one trusted file. The req tests that cover that
file run against it (in a copy of the source tree). A mutant 'survives' if they all still pass.
Usage: python mutate.py [--jobs N] [--out FILE]
"""
import argparse, concurrent.futures as cf, json, os, pathlib, re, shutil, subprocess, sys, tempfile

REQ = pathlib.Path(__file__).resolve().parents[1]
ROOT = REQ.parent
PY = sys.executable
OPS = [
    (r"(?<![=!<>])==(?!=)", "!="), (r"!=", "=="), (r"\bis not None\b", "is None"), (r"\bis None\b", "is not None"),
    (r"\bnot (?!in\b)", ""), (r"\bTrue\b", "False"), (r"\bFalse\b", "True"), (r" <= ", " < "), (r" >= ", " > "),
    (r" < ", " <= "), (r" > ", " >= "), (r" not in ", " in "), (r"(?<!not) in \(", " not in ("),
    (r"\braise (Refusal|SyntaxRefusal)\(", r"\1("), (r"\band\b", "or"), (r"\bor\b", "and"),
    (r"\+= 1\b", "+= 0"), (r"\bn - 2\b", "n - 1"), (r'"(G0\d\d|T001|E004|N00\d|S0\d\d)"', '"X999"'),
]
CAT = "tests/test_gate_e_catalogue.py"
TESTS = {   # fastest killers first (pytest -x); the byte-for-byte demo transcript (gate F) last
    "syntax.py": [CAT, "tests/test_gate_b.py", "tests/test_gate_d.py"],
    "form.py": [CAT, "tests/test_gate_b.py", "tests/test_gate_d.py", "tests/test_gate_c.py", "tests/test_gate_f.py"],
    "say.py": [CAT, "tests/test_gate_b.py", "tests/test_gate_d.py", "tests/test_wording.py", "tests/test_gate_f.py"],
    "run.py": [CAT, "tests/test_gate_c.py", "tests/test_gate_f.py"],
    "bind.py": [CAT, "tests/test_gate_d.py"],
}


def mutants():
    for f in TESTS:
        lines = (REQ / "src" / "reality_req" / f).read_text().split("\n")
        in_doc = False
        for i, ln in enumerate(lines):
            s = ln.strip()
            if '"""' in s:
                if s.count('"""') == 1:
                    in_doc = not in_doc
                continue
            if in_doc or s.startswith("#") or not s:
                continue
            for pat, rep in OPS:
                for m in re.finditer(pat, ln):
                    new = ln[:m.start()] + m.expand(rep) + ln[m.end():]
                    if new != ln:
                        yield f, i, ln, new


def run(job):
    f, i, old, new = job
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="reqmut-"))
    try:
        shutil.copytree(REQ / "src", tmp / "src")
        p = tmp / "src" / "reality_req" / f
        lines = p.read_text().split("\n"); lines[i] = new; p.write_text("\n".join(lines))
        try:
            compile(p.read_text(), str(p), "exec")
        except SyntaxError:
            return dict(file=f, line=i + 1, new=new.strip(), result="invalid")
        env = dict(os.environ, PYTHONPATH=f"{tmp / 'src'}:{ROOT / 'v4' / 'src'}", PYTHONDONTWRITEBYTECODE="1",
                   REALITY_REQ_SRC=str(tmp / "src"))
        r = subprocess.run([PY, "-m", "pytest", "-p", "no:cacheprovider", "-q", "-x", f"--basetemp={tmp / 'pt'}",
                            *[str(REQ / t) for t in TESTS[f]]], cwd=ROOT, env=env, capture_output=True, timeout=900)
        return dict(file=f, line=i + 1, old=old.strip(), new=new.strip(), result="killed" if r.returncode else "SURVIVED")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--jobs", type=int, default=4); ap.add_argument("--out", default="mutation.json")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    jobs = list(mutants())
    if a.list:
        from collections import Counter
        print(len(jobs), Counter(j[0] for j in jobs)); sys.exit(0)
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(run, jobs))
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1))
    from collections import Counter
    print(Counter(r["result"] for r in res))
    for r in res:
        if r["result"] == "SURVIVED":
            print(f"{r['file']}:{r['line']}: {r['old']}  ->  {r['new']}")
