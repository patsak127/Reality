"""Reality v3 gauntlet (adapted from v2/tools/gauntlet): deterministic probes for the failure patterns the reviews keep finding.

Usage (from v3/):
    python3 tools/gauntlet/run.py                 # all probes, text report
    python3 tools/gauntlet/run.py --only env,codes
    python3 tools/gauntlet/run.py --json          # machine-readable report on stdout
    python3 tools/gauntlet/run.py --python PATH   # interpreter for the subprocess probes

The probes REPORT. They do not decide what is right and they gate nothing, with one exception:
`env` checks clause 4 of the principle (a verdict depends on nothing but the text and the bytes),
which is an invariant, so a difference there sets exit code 1. Every other probe's findings are
observations and leave the exit code at 0. Exit 3 means a probe itself broke.

Standard library only. Nothing in v3/ is written; scratch files go to a temporary directory.
See README.md next to this file for what each probe verifies and what it does not.
"""
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True  # importing reality4 and the tests must not write into v3/

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(V2, "src")
TESTS = os.path.join(V2, "tests")
HARNESS_PY = os.path.expanduser("~/reality-harness/venv/bin/python")

CODE_RE = re.compile(r"\b(B[0-9]{2}|[CFIJKMNPRSTUVX][0-9]{3})\b")
RANGE_RE = re.compile(r"\b([A-Z])([0-9]{2,3})\s*[–-]\s*([A-Z])([0-9]{2,3})\b")


def read(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8")


class Report:
    def __init__(self):
        self.probes = []

    def probe(self, pid, title, invariant=False):
        p = {"id": pid, "title": title, "invariant": invariant, "notes": [], "findings": [], "error": None}
        self.probes.append(p)
        return p


def finding(p, what, detail=""):
    p["findings"].append({"what": what, "detail": detail})


def note(p, text):
    p["notes"].append(text)


# ---- probe: env (clause 4 invariant) -------------------------------------------------------

def env_base():
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "PYTHONPATH": SRC,
        "PYTHONHASHSEED": "0",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


ENV_VARIANTS = [
    ("hashseed=1", {"PYTHONHASHSEED": "1"}, []),
    ("hashseed=random", {"PYTHONHASHSEED": "random"}, []),
    ("int_max_str_digits=640", {"PYTHONINTMAXSTRDIGITS": "640"}, []),
    ("int_max_str_digits=0 (unlimited)", {"PYTHONINTMAXSTRDIGITS": "0"}, []),
    ("io encoding ascii, UTF-8 mode off", {"PYTHONIOENCODING": "ascii", "PYTHONUTF8": "0"}, []),
    ("io encoding latin-1, UTF-8 mode off", {"PYTHONIOENCODING": "latin-1", "PYTHONUTF8": "0"}, []),
    ("locale C, no io encoding, UTF-8 mode off", {"LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONIOENCODING": None}, []),
    ("TZ=Pacific/Kiritimati", {"TZ": "Pacific/Kiritimati"}, []),
    ("cwd=/", {}, ["cwd"]),
]


def corpus(tmp):
    """Fixed programs and files. Every byte is written here, so the corpus is the same everywhere."""
    files = {}

    def put(name, data):
        p = os.path.join(tmp, "files", name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
        files[name] = (p, hashlib.sha256(data).hexdigest())

    part = os.path.join(TESTS, "data", "ds001734-box", "participants.tsv")
    if os.path.exists(part):
        with open(part, "rb") as f:
            put("participants.tsv", f.read())
    put("long.tsv", b"n\tm\n" + b"9" * 5000 + b"\t1\n" + b"1\t2\n")
    put("nonascii.tsv", "name\tv\n\u00e9t\u00e9\t1\nabc\t2\n".encode("utf-8"))
    put("plain.tsv", b"id\tgroup\tage\ns1\tA\t30\ns2\tB\t41\ns3\tA\t25\n")
    progs = {}

    def prog(name, text):
        p = os.path.join(tmp, "progs", name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(text.encode("ascii"))
        progs[name] = p

    if "participants.tsv" in files:
        h = files["participants.tsv"][1]
        prog("demo.rl", f"file p = sha256:{h}\nlet t = tsv(p)\nclaim rows(t) is 108\n"
             "claim count(where(t, eq(\"group\", \"equalRange\")))\nclaim exceeds(max(t, \"age\"), c = 30)\n"
             "claim significant(t)\nclaim count(where(t, eq(\"group\", \"equaIRange\")))\n")
    h = files["long.tsv"][1]
    prog("long.rl", f"file f = sha256:{h}\nlet t = tsv(f)\nclaim number(cell(t, 1, 1))\nclaim sum(t, 1)\n"
         "claim exceeds(number(cell(t, 1, 1)), c = 3)\n")
    h = files["nonascii.tsv"][1]
    prog("nonascii.rl", f"file f = sha256:{h}\nlet t = tsv(f)\nclaim cell(t, 1, 1)\nclaim count(where(t, eq(1, \"abc\")))\n")
    h = files["plain.tsv"][1]
    prog("plain.rl", f"file f = sha256:{h}\nlet t = tsv(f)\nclaim share(where(t, eq(\"group\", \"A\")))\n"
         "claim difference(number(cell(t, 1, 3)), number(cell(t, 2, 3)))\nclaim size(f)\nclaim bytes(f, 0, 2)\n"
         "claim undeclared(t)\nlet u = tsv(g)\nclaim rows(u)\n")
    old = sorted(os.listdir(os.path.join(TESTS, "old"))) if os.path.isdir(os.path.join(TESTS, "old")) else []
    old = [os.path.join(TESTS, "old", n) for n in old if n.endswith(".rl")]
    return files, progs, old


def run_cli(py, args, env, cwd):
    r = subprocess.run([py, "-m", "reality4", "check"] + args, env=env, cwd=cwd, capture_output=True, timeout=600)
    return r.returncode, r.stdout, r.stderr


def sections(stdout):
    """Split multi-program output into {program path: bytes}; the '== path' header is the key."""
    out, cur, buf = {}, None, []
    for line in stdout.split(b"\n"):
        if line.startswith(b"== "):
            if cur is not None:
                out[cur] = b"\n".join(buf).rstrip(b"\n")
            cur, buf = line[3:].decode("utf-8", "replace"), []
        else:
            buf.append(line)
    if cur is not None:
        out[cur] = b"\n".join(buf).rstrip(b"\n")
    return out


def first_diff(a, b):
    la, lb = a.split(b"\n"), b.split(b"\n")
    for i in range(max(len(la), len(lb))):
        x = la[i] if i < len(la) else b"<missing>"
        y = lb[i] if i < len(lb) else b"<missing>"
        if x != y:
            j = next((k for k in range(min(len(x), len(y))) if x[k] != y[k]), min(len(x), len(y)))
            lo = max(0, j - 60)
            return f"line {i + 1}, byte {j}: base ...{x[lo:j + 60]!r} / variant ...{y[lo:j + 60]!r}"
    return "identical lines"


def compare(p, label, base, var):
    (c0, o0, e0), (c1, o1, e1) = base, var
    if (c0, o0) == (c1, o1) and bool(e0) == bool(e1):
        return
    s0, s1 = sections(o0), sections(o1)
    if s0 and s1:
        for k in s0:
            if s0[k] != s1.get(k):
                finding(p, f"{label}: output of {os.path.basename(k)} differs", first_diff(s0[k], s1.get(k, b"<absent>")))
    else:
        finding(p, f"{label}: output differs", first_diff(o0, o1))
    if c0 != c1:
        finding(p, f"{label}: exit code {c0} -> {c1}", (e1.decode("utf-8", "replace").strip().splitlines() or [""])[-1][:200])
    elif bool(e0) != bool(e1):
        finding(p, f"{label}: stderr {'appears' if e1 else 'disappears'}", (e1 or e0).decode("utf-8", "replace").strip()[-200:])


def probe_env(rep, py):
    p = rep.probe("env", "A verdict depends on nothing but the text and the file bytes (principle clause 4)", invariant=True)
    note(p, f"interpreter: {py}")
    with tempfile.TemporaryDirectory() as tmp:
        files, progs, old = corpus(tmp)
        fpaths = [files[k][0] for k in sorted(files)]
        groups = {
            "file programs": [progs[k] for k in sorted(progs)] + ["--files"] + fpaths,
            "tests/old programs": old,
        }
        note(p, f"corpus: {len(progs)} file programs over {len(files)} files, {len(old)} programs from tests/old")
        for gname, args in groups.items():
            if not args:
                continue
            base = run_cli(py, args, env_base(), V2)
            if base[2]:
                finding(p, f"{gname}: the baseline run writes to stderr", base[2].decode("utf-8", "replace")[-200:])
            for label, delta, flags in ENV_VARIANTS:
                env = env_base()
                for k, v in delta.items():
                    if v is None:
                        env.pop(k, None)
                    else:
                        env[k] = v
                compare(p, f"{gname} / {label}", base, run_cli(py, args, env, "/" if "cwd" in flags else V2))
            if gname == "file programs":
                n = len(progs)
                pa, fa = args[:n], args[n + 1:]
                compare(p, f"{gname} / --files in reverse order", base, run_cli(py, pa + ["--files"] + fa[::-1], env_base(), V2))
                compare(p, f"{gname} / --files as one folder", base,
                        run_cli(py, pa + ["--files", os.path.join(tmp, "files")], env_base(), V2))
            progs_only = [a for a in args if a.endswith(".rl")]
            rest = args[len(progs_only):]
            compare(p, f"{gname} / programs in reverse order", base, run_cli(py, progs_only[::-1] + rest, env_base(), V2))
            for one in progs_only[:12] if gname == "file programs" else []:
                alone = run_cli(py, [one] + rest, env_base(), V2)
                together = sections(base[1]).get(one)
                if together is not None and alone[1].rstrip(b"\n") != together.rstrip(b"\n"):
                    finding(p, f"{gname}: {os.path.basename(one)} alone vs with the other programs differs",
                            first_diff(together, alone[1]))
    note(p, "Not varied: memory limits, recursion limits, the machine (the harness's xrun does 4 machines), the clock across days.")


# ---- probe: neighbours (one standard of accuracy, spec §10.2) ------------------------------

SEP_LIKE = [  # class: bytes that some reader could read as structure or as nothing (two readings)
    ("CR (U+000D)", b"\r"), ("BOM (U+FEFF)", "\ufeff".encode()), ("LINE SEPARATOR U+2028", "\u2028".encode()),
    ("PARAGRAPH SEPARATOR U+2029", "\u2029".encode()), ("NEL U+0085", "\u0085".encode()), ("FF U+000C", b"\x0c"),
    ("VT U+000B", b"\x0b"), ("NUL U+0000", b"\x00"), ("double quote", b'"'), ("NBSP U+00A0", "\u00a0".encode()),
    ("ZERO WIDTH SPACE U+200B", "\u200b".encode()), ("SOFT HYPHEN U+00AD", "\u00ad".encode()),
    ("trailing space", None), ("non-UTF-8 byte 0xFF", b"\xff"),
]
LOOKALIKES = [  # class: (label, target as written in the claim, variant present in the file)
    ("1 / l (ASCII)", b"s1", b"sl"), ("0 / O (ASCII)", b"s0", b"sO"), ("rn / m (ASCII)", b"rnx", b"mx"),
    ("case S / s (ASCII)", b"s1", b"S1"),
    ("Cyrillic dze U+0455 / s", b"s1", "\u04551".encode()), ("Cyrillic DZE U+0405 / S", b"S1", "\u04051".encode()),
    ("Cyrillic a U+0430 / a", b"a1", "\u04301".encode()), ("Greek omicron U+03BF / o", b"o1", "\u03bf1".encode()),
    ("fullwidth digit one U+FF11 / 1", b"s1", "s\uff11".encode()),
    ("NFD e+U+0301 / NFC U+00E9", "\u00e9".encode(), "e\u0301".encode()),
    ("non-breaking hyphen U+2011 / -", b"a-b", "a\u2011b".encode()),
]


def _verdict(check, store_cls, prog, paths):
    ok, out = check(prog.encode("ascii"), store_cls(paths, []))
    codes = [m.group(1) for line in out for m in [re.match(r"line \d+: refused \[(\w+)", line)] if m]
    return "formed" if not codes else "refused " + ",".join(sorted(set(codes)))


def probe_neighbours(rep):
    p = rep.probe("neighbours", "The same hazard gets the same treatment in neighbouring places (spec §10.2, one standard)")
    sys.path.insert(0, SRC)
    from reality4 import readers as R
    from reality4.kernel import check, esc
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        n = [0]

        def tsv(data):
            n[0] += 1
            path = os.path.join(tmp, f"t{n[0]}.tsv")
            with open(path, "wb") as f:
                f.write(data)
            return path, hashlib.sha256(data).hexdigest()

        def v(data, claim):
            path, h = tsv(data)
            return _verdict(check, R.Store, f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {claim}\n", [path])

        # class 1: separator-like bytes, in a data cell, in a header, at a cell's start.
        for label, hz in SEP_LIKE:
            if hz is None:  # trailing space
                cell, head, start = b"x \t1\n", b"id \tv\n", None
                r = {"hazard": label, "in a data cell": v(b"id\tv\n" + cell, "rows(t)"),
                     "in a header": v(head + b"x\t1\n", "rows(t)"), "at file start": "-"}
            else:
                r = {"hazard": label,
                     "in a data cell": v(b"id\tv\nx" + hz + b"y\t1\n", "rows(t)"),
                     "in a header": v(b"i" + hz + b"d\tv\nx\t1\n", "rows(t)"),
                     "at file start": v(hz + b"id\tv\nx\t1\n", "rows(t)")}
            rows.append(("sep", r))
        # class 2: lookalikes, where the claim writes the target and the file holds the variant.
        for label, tgt, var in LOOKALIKES:
            lt = esc(tgt)
            r = {"hazard": label,
                 "key() over a column holding both": v(b"id\tv\n" + tgt + b"\t1\n" + var + b"\t2\n", f"cell(t, key(1, {lt}), 2)"),
                 "eq() over a column holding both": v(b"id\tv\n" + tgt + b"\t1\n" + var + b"\t2\n", f"count(where(t, eq(1, {lt})))"),
                 "eq() literal vs the other cell only": v(b"id\tv\n" + var + b"\t2\nzz\t3\n", f"count(where(t, eq(1, {lt})))"),
                 "two headers, select by name": v(tgt + b"\t" + var + b"\nq\tr\n", f"cell(t, 1, {lt})")}
            rows.append(("look", r))
    # Report: within class 1, a hazard refused in one place and accepted in another; and the class
    # split (some refused, some accepted) in each place. Same for class 2.
    for cls, cname in (("sep", "separator-like bytes"), ("look", "lookalikes")):
        rs = [r for c, r in rows if c == cls]
        cols = [k for k in rs[0] if k != "hazard"]
        for r in rs:
            vals = {r[k] for k in cols if r[k] != "-"}
            kinds = {x.split()[0] for x in vals}
            if len(kinds) > 1:
                finding(p, f"{cname}: {r['hazard']} is refused in some places and forms in others",
                        "; ".join(f"{k}: {r[k]}" for k in cols))
        for k in cols:
            ref = [r["hazard"] for r in rs if r[k].startswith("refused")]
            acc = [r["hazard"] for r in rs if r[k] == "formed"]
            if ref and acc:
                finding(p, f"{cname}, {k}: {len(ref)} refused, {len(acc)} form",
                        "refused: " + ", ".join(ref) + " | form: " + ", ".join(acc))
    p["table"] = [r for _, r in rows]
    note(p, "The two classes are this tool's grouping. A difference inside a class may be legitimate; "
            "the probe says where the treatment differs, not which treatment is right.")
    note(p, "Not covered: JSON keys and values, the BIDS TSV reader, NIfTI headers, the manifest reader.")


# ---- probe: codes (docs and model name only codes the checker has) -------------------------

def expand(text):
    codes = set(CODE_RE.findall(text))
    for a, x, b, y in RANGE_RE.findall(text):
        if a == b and len(x) == len(y):
            for i in range(int(x), int(y) + 1):
                codes.add(f"{a}{i:0{len(x)}d}")
    return {c for c in codes if CODE_RE.fullmatch(c)}


def probe_codes(rep):
    p = rep.probe("codes", "Refusal codes: the code, the SPEC, the README, the model and the tests name the same set")
    src = set()
    for n in sorted(os.listdir(os.path.join(SRC, "reality4"))):
        if n.endswith(".py"):
            src |= set(re.findall(r"[\"'](B[0-9]{2}|[CFIJKMNPRSTUVX][0-9]{3})[\"']", read(os.path.join(SRC, "reality4", n))))
    spec = read(os.path.join(V2, "SPEC.md"))
    m = re.search(r"## 3\. Refusal codes(.*?)\n## ", spec, re.S)
    spec_codes = expand(m.group(1)) if m else set()
    if not m:
        note(p, "SPEC.md has no '## 3. Refusal codes' section; skipped that comparison")
    docs = {"README.md": read(os.path.join(V2, "README.md"))}
    rules = os.path.join(V2, "bids", "RULES-1.0.1.md")
    if os.path.exists(rules):
        docs["bids/RULES-1.0.1.md"] = read(rules)
    docs["SPEC.md (outside §3)"] = spec.replace(m.group(1), "") if m else spec
    lean = ""
    md = os.path.join(V2, "metatheory")
    for n in sorted(os.listdir(md)) if os.path.isdir(md) else []:
        if n.endswith(".lean"):
            lean += read(os.path.join(md, n))
    tests = ""
    for n in sorted(os.listdir(TESTS)):
        if n.endswith(".py"):
            tests += read(os.path.join(TESTS, n))
    note(p, f"{len(src)} codes raised in src/reality4; {len(spec_codes)} in SPEC §3 after expanding ranges")
    for c in sorted(spec_codes - src):
        finding(p, f"SPEC §3 covers {c}, which src/reality4 never raises")
    for c in sorted(src - spec_codes):
        finding(p, f"src/reality4 raises {c}, which SPEC §3 does not list")
    acc_ids = re.compile(r"^F[0-9]{1,2}$")
    for name, text in docs.items():
        for c in sorted(set(CODE_RE.findall(text)) - src):
            finding(p, f"{name} names {c}, which src/reality4 never raises")
    for c in sorted(set(CODE_RE.findall(lean)) - src):
        finding(p, f"metatheory names {c}, which src/reality4 never raises",
                "the model's codes are meant to be the checker's codes")
    tested = set(CODE_RE.findall(tests))
    for c in sorted(src - tested):
        finding(p, f"{c} is raised in src/reality4 but no file in tests/ mentions it")
    note(p, "A mention is not a test, and a code in a doc is matched as text, so a code quoted in prose counts.")


# ---- probe: surface (the README's list of computations is the checker's list) --------------

def probe_surface(rep):
    p = rep.probe("surface", "The README's computations are the checker's computations")
    k = read(os.path.join(SRC, "reality4", "kernel.py"))
    code = set(re.findall(r"def c_(\w+)\(", k))
    code |= set(re.findall(r"\.fn\s*==\s*\"(\w+)\"", k))
    for grp in re.findall(r"\.fn\s+(?:not\s+)?in\s+\(([^)]*)\)", k):
        code |= set(re.findall(r"\"(\w+)\"", grp))
    readme = read(os.path.join(V2, "README.md"))
    m = re.search(r"\*\*Computations\.\*\*(.*?)\n\n[^|]", readme, re.S)
    if not m:
        note(p, "README has no '**Computations.**' table; nothing to compare")
        return
    doc = set()
    for span in re.findall(r"`([^`]*)`", m.group(1)):
        for names in re.findall(r"([\w/]+)\(", span):
            doc |= set(names.split("/"))
    note(p, f"{len(code)} computations in kernel.py, {len(doc)} in the README table")
    for c in sorted(code - doc):
        finding(p, f"kernel.py has computation {c!r}, which the README table does not list")
    for c in sorted(doc - code):
        finding(p, f"the README table lists {c!r}, which kernel.py does not implement")


# ---- probe: numbers (numbers the README states that can be recomputed) ---------------------

def probe_numbers(rep, py):
    p = rep.probe("numbers", "Numbers the README states and a script can recompute")
    readme = read(os.path.join(V2, "README.md"))
    total = 0
    for name, n in re.findall(r"^\|\s*`([\w.]+\.py)`\s*\|\s*([0-9][0-9 ]*)\s*\|", readme, re.M):
        path = os.path.join(SRC, "reality4", name)
        if not os.path.exists(path):
            finding(p, f"README trusted-base table names {name}, which is not in src/reality4")
            continue
        lines = read(path).split("\n")
        actual = len(lines) - (1 if lines and lines[-1] == "" else 0)
        total += actual
        if int(n.replace(" ", "")) != actual:
            finding(p, f"README says {name} has {n} lines; it has {actual}")
    m = re.search(r"\*\*total\*\*\s*\|\s*\*\*([0-9 ]+)\*\*", readme)
    if m and int(m.group(1).replace(" ", "")) != total:
        finding(p, f"README says the trusted base totals {m.group(1)} lines; the listed files total {total}")
    elif m:
        note(p, f"trusted base: {total} lines, as stated")
    m = re.search(r"`__main__\.py` adds ([0-9]+) lines", readme)
    if m:
        lines = read(os.path.join(SRC, "reality4", "__main__.py")).split("\n")
        actual = len(lines) - (1 if lines[-1] == "" else 0)
        if int(m.group(1)) != actual:
            finding(p, f"README says __main__.py adds {m.group(1)} lines; it has {actual}")
    m = re.search(r"`tests/` \(([0-9]+) tests\)", readme)
    if m:
        r = subprocess.run([py, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "tests"],
                           cwd=V2, capture_output=True, text=True, timeout=600,
                           env=dict(env_base(), PATH=os.path.dirname(py) + ":/usr/bin:/bin"))
        got = re.search(r"([0-9]+) tests? collected", r.stdout)
        if not got:
            p["error"] = "pytest collection failed: " + (r.stdout + r.stderr).strip()[-300:]
        elif int(got.group(1)) != int(m.group(1)):
            finding(p, f"README says tests/ has {m.group(1)} tests; pytest collects {got.group(1)}")
        else:
            note(p, f"tests/: {got.group(1)} tests, as stated")
    note(p, "Only numbers written in the shapes above are checked; a claim reworded is not found, and that is "
            "reported here as nothing, not as a failure. Timings ('about 11 s') are not deterministic and are skipped.")


# ---- probe: independence (how separate the second implementation is) -----------------------

def probe_independence(rep):
    p = rep.probe("independence", "How independent the second implementation and the differential test are")
    refdir = os.path.join(SRC, "reality4_ref")
    for n in sorted(os.listdir(refdir)):
        if not n.endswith(".py"):
            continue
        tree = ast.parse(read(os.path.join(refdir, n)))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            for mname in mods:
                if mname.split(".")[0] == "reality4":
                    finding(p, f"reality4_ref/{n} imports {mname}", "the second implementation shares code with the first")
    td = os.path.join(TESTS, "test_differential.py")
    if not os.path.exists(td):
        note(p, "tests/test_differential.py not found")
        return
    t = read(td)
    if re.search(r"kv\.endswith\(", t):
        finding(p, "for a formed line the test compares only the printed value, not the printed sort",
                "so the sort text of formed claims is produced and checked by one implementation only")
    if re.search(r"ref\.evaluate\(\s*data\s*,\s*q\s*\)", t):
        finding(p, "the reference is given the test's query tuple, not the program text",
                "so the parser and the printed form are checked by one implementation only")
    for mname in ("Checker", "parse_line", "esc"):
        if re.search(rf"from reality4[.\w]* import [^\n]*\b{mname}\b", t):
            note(p, f"the differential test imports reality4's {mname} (it writes and parses the program text with the first implementation)")
    # Replay the generator with its own seed and loop shape, and record what it ever produces.
    sys.path[:0] = [SRC, TESTS]
    import importlib
    mod = importlib.import_module("test_differential")
    import random
    m = re.search(r"random\.Random\((\d+)\)", t)
    loops = re.search(r"for i in range\((\d+)\):.*?for _ in range\((\d+)\):", t, re.S)
    if not (m and loops):
        note(p, "could not read the generator's seed and loop counts; replay skipped")
        return
    rng = random.Random(int(m.group(1)))
    words, rowpos, colpos, n = set(), set(), set(), 0
    for _ in range(int(loops.group(1))):
        _data, nc = mod.table(rng)
        for _ in range(int(loops.group(2))):
            if hasattr(mod, "program"):   # v3: the generator writes program text
                txt = mod.program(rng, "0" * 64, nc)
            else:
                txt = mod.text(mod.query(rng, nc))
            n += 1
            words |= set(re.findall(r"\b([a-z_]+)\(", txt))
            rowpos |= {int(x) for x in re.findall(r"cell\(t, (-?\d+),", txt)}
            colpos |= {int(x) for x in re.findall(r"(?:eq|ne)\((-?\d+),", txt)}
            if " is " in f" {txt} ":
                words.add("is")
    k = read(os.path.join(SRC, "reality4", "kernel.py"))
    plain = {"tsv", "rows", "where", "eq", "ne", "count", "share", "cell", "key", "header", "number", "sum", "min",
             "max", "difference", "widen", "exceeds", "below", "size", "bytes"}
    plain &= set(re.findall(r"def c_(\w+)\(", k)) | {"eq", "ne", "key"}
    note(p, f"replayed {n} generated claims (seed {m.group(1)})")
    for w in sorted(plain - words - {"tsv"}):
        finding(p, f"the differential test never generates {w}()")
    if "is" not in words:
        finding(p, "the differential test never generates a claim with 'is'")
    if rowpos:
        note(p, f"row positions generated: {min(rowpos)}..{max(rowpos)}")
        if min(rowpos) > 0:
            finding(p, f"row positions below {min(rowpos)} are never generated", "row 0 and negative rows are untested")


# ---- probe: table (SPEC §4 is what tools/acceptance_table.py prints today) -----------------

def probe_table(rep, py):
    p = rep.probe("table", "SPEC §4's F/N table is what tools/acceptance_table.py prints now")
    tool = os.path.join(V2, "tools", "acceptance_table.py")
    if not os.path.exists(tool):
        note(p, "tools/acceptance_table.py not found")
        return
    r = subprocess.run([py, tool], cwd=V2, capture_output=True, timeout=900, env=env_base())
    if r.returncode != 0:
        p["error"] = "acceptance_table.py failed: " + r.stderr.decode("utf-8", "replace")[-300:]
        return
    now = [l for l in r.stdout.decode("utf-8").split("\n") if l.startswith("| ") and not l.startswith("| id ")]
    spec = read(os.path.join(V2, "SPEC.md"))
    m = re.search(r"## 4\..*?\n(\|.*?)\n\n", spec, re.S)
    doc = [l for l in (m.group(1).split("\n") if m else []) if l.startswith("| ") and not l.startswith("| id ")]
    key = lambda l: l.split("|")[1].strip()
    dn, nn = {key(l): l for l in doc}, {key(l): l for l in now}
    for k in sorted(set(dn) | set(nn)):
        if dn.get(k) != nn.get(k):
            finding(p, f"row {k} differs", f"SPEC: {(dn.get(k) or '<absent>')[:200]} || now: {(nn.get(k) or '<absent>')[:200]}")
    note(p, f"{len(nn)} rows printed, {len(dn)} rows in SPEC §4")


# ---- main ------------------------------------------------------------------------------------

PROBES = ["env", "neighbours", "codes", "surface", "numbers", "independence", "table"]


def main(argv):
    only, as_json, py = PROBES, False, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--only":
            only = argv[i + 1].split(",")
            i += 1
        elif a == "--json":
            as_json = True
        elif a == "--python":
            py = argv[i + 1]
            i += 1
        else:
            print(__doc__)
            return 2
        i += 1
    py = py or (HARNESS_PY if os.path.exists(HARNESS_PY) else sys.executable)
    rep = Report()
    fns = {"env": lambda: probe_env(rep, py), "neighbours": lambda: probe_neighbours(rep),
           "codes": lambda: probe_codes(rep), "surface": lambda: probe_surface(rep),
           "numbers": lambda: probe_numbers(rep, py), "independence": lambda: probe_independence(rep),
           "table": lambda: probe_table(rep, py)}
    for pid in only:
        if pid not in fns:
            print(f"unknown probe {pid!r}; probes: {', '.join(PROBES)}")
            return 2
        before = len(rep.probes)
        try:
            fns[pid]()
        except Exception as e:  # a broken probe is reported, never read as clean
            if len(rep.probes) == before:
                rep.probe(pid, "(probe crashed before it started)")
            rep.probes[-1]["error"] = f"{type(e).__name__}: {e}"
    code = 0
    for p in rep.probes:
        if p["error"]:
            code = 3
        elif p["invariant"] and p["findings"] and code == 0:
            code = 1
    if as_json:
        print(json.dumps({"v2": V2, "exit": code, "probes": rep.probes}, indent=1, ensure_ascii=False, sort_keys=True))
        return code
    for p in rep.probes:
        status = "ERROR" if p["error"] else ("clear" if not p["findings"] else
                 ("INVARIANT BROKEN" if p["invariant"] else "observations"))
        print(f"== {p['id']}: {p['title']}\n   {status}, {len(p['findings'])} finding(s)")
        if p["error"]:
            print(f"   error: {p['error']}")
        for f in p["findings"]:
            print(f"   - {f['what']}" + (f"\n       {f['detail']}" if f["detail"] else ""))
        for n in p["notes"]:
            print(f"   note: {n}")
        if p.get("table"):
            cols = list(p["table"][0].keys())
            print("   table:")
            for r in p["table"]:
                print("     " + " | ".join(f"{k}: {r.get(k, '')}" for k in r))
        print()
    print(f"exit {code} (0: nothing broke an invariant; 1: env found a difference; 3: a probe errored)")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
