"""Exact-decision Phase 0 (plans/exact-decision-procedure.md section 7): the old-vs-new differential
harness. Report only; nothing in the trusted base is changed or imported differently.

python3 tools/exact_diff.py A B [--corpus NAMES] [--out FILE]

Deciders (the module the kernel calls for W1/W2, `kernel.witness`):
  live   src/reality4/witness.py (the trusted one; decides every verdict until the switch-over)
  old    tests/old_witness.py (the frozen, untrusted copy of witness.py at 6f21606)
  exact  src/reality4/exact_decide.py, once a later phase builds it (absent in Phase 0)
Corpora (default all), each run in full under A and then under B, each with fresh stores:
  repros        every tests/repros program, one store over all of them (as the snapshot's first part)
  acceptance    the acceptance programs and the two stress programs of tools/envmatrix.py's corpus
  differential  the 24 000 programs of tests/test_differential.py (rng 1025), one store per table;
                lines are tagged with their class in tests/differential-carve-outs.tsv
  bruteforce    the 86 statements of tests/test_v4_bruteforce.py on its REAL table
Every statement line ('line N: formed' or 'line N: refused [CODE') is compared. A difference is
classed refuse/form, form/refuse, code (both refuse, other codes), text (same verdict, other bytes).
Exit 1 on any difference."""
import contextlib
import importlib
import importlib.util
import os
import random
import re
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
V4 = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [os.path.join(V4, "src"), os.path.join(V4, "tests"), HERE]
from reality4 import kernel, readers as R  # noqa: E402
from reality4.kernel import check  # noqa: E402

CORPORA = ("repros", "acceptance", "differential", "bruteforce")
LINE = re.compile(r"line (\d+): (formed|refused)(?: \[(\w+),)?")


def decider(name):
    if name == "live":
        return importlib.import_module("reality4.witness")
    if name == "old":
        return importlib.import_module("old_witness")
    if name == "exact":
        return importlib.import_module("reality4.exact_decide")
    raise SystemExit(f"unknown decider {name!r}")


class Recorder:
    """Wraps a decider: records, per W1/W2 call, the statement's line, its expression as judged and
    the outcome (None, or the refusal code). The decider's behaviour is unchanged."""

    def __init__(self, mod):
        self.mod, self.records, self.line = mod, [], None

    def check(self, checker, expr):
        rec = {"line": self.line, "expr": expr, "checker": checker, "code": None}
        try:
            rec["judged"] = self.mod._as_judged(expr, checker)
        except Exception:   # measurement only
            rec["judged"] = expr
        self.records.append(rec)
        t0 = time.perf_counter()
        try:
            return self.mod.check(checker, expr)
        except R.Refusal as e:
            rec["code"] = e.code
            raise
        finally:
            rec["secs"] = time.perf_counter() - t0

    def __getattr__(self, k):
        return getattr(self.mod, k)


@contextlib.contextmanager
def using(mod):
    """kernel.witness is the module the kernel calls (kernel.py: witness.check after check 2)."""
    rec = Recorder(mod)
    saved_w, saved_p = kernel.witness, kernel.parse_line

    def parse_line(text, ln):
        rec.line = ln
        return saved_p(text, ln)
    kernel.witness, kernel.parse_line = rec, parse_line
    try:
        yield rec
    finally:
        kernel.witness, kernel.parse_line = saved_w, saved_p


def statement_lines(out):
    res = {}
    for ln in out:
        m = LINE.match(ln)
        if m:
            res[int(m.group(1))] = (m.group(2), m.group(3), ln)
    return res


def programs(corpus, tmp):
    """Yield (id, program bytes, store) in a fixed order."""
    if corpus == "repros":
        import run_repros
        roots = []
        for d in run_repros.default_dirs():
            roots += run_repros.roots_in(d)
        store = R.Store(list(run_repros.default_dirs()) + [run_repros.BOX], sorted(set(roots)))
        for d in run_repros.default_dirs():
            for p in run_repros.programs(d):
                with open(p, "rb") as f:
                    yield os.path.basename(d) + "/" + os.path.relpath(p, d).replace(os.sep, "/"), f.read(), store
    elif corpus == "acceptance":
        import envmatrix
        import run_repros
        progs, files, roots = envmatrix.corpus(tmp)
        store = R.Store(files, roots)
        repro = {os.path.abspath(p) for d in run_repros.default_dirs() for p in run_repros.programs(d)}
        for p in progs:
            if os.path.abspath(p) not in repro:
                with open(p, "rb") as f:
                    yield os.path.basename(p), f.read(), store
    elif corpus == "differential":
        import helpers
        import test_differential as TD
        rng = random.Random(1025)
        for i in range(6000):
            data, nc = TD.table(rng)
            p, h = helpers.tsv(tmp, f"t{i}.tsv", data)
            store = R.Store([p])
            for j in range(4):
                yield f"{i}.{j}", TD.program(rng, h, nc).encode("ascii"), store
    elif corpus == "bruteforce":
        import helpers
        import test_v4_bruteforce as BF
        p, h = helpers.tsv(tmp, "f.tsv", BF.REAL)
        store = R.Store([p])
        for k, stmt in enumerate(BF.family()):
            yield f"bf{k:02d}", f"file f = sha256:{h}\nclaim {stmt}\n".encode("ascii"), store
    elif corpus == "partT":
        import helpers
        p, h = helpers.tsv(tmp, "g.tsv", PART_T_TABLE)
        store = R.Store([p])
        for k, stmt in enumerate(part_t_family()):
            yield f"pt{k:03d}", f"file f = sha256:{h}\nclaim {stmt}\n".encode("ascii"), store
    elif corpus == "partT2":
        import helpers
        p, h = helpers.tsv(tmp, "g2.tsv", PART_T2_TABLE)
        store = R.Store([p])
        for k, stmt in enumerate(part_t2_family()):
            yield f"pu{k:03d}", f"file f = sha256:{h}\nclaim {stmt}\n".encode("ascii"), store
    elif corpus == "partN":
        import helpers
        p, h = helpers.tsv(tmp, "gn.tsv", PART_N_TABLE)
        store = R.Store([p])
        for k, stmt in enumerate(part_n_family()):
            yield f"pn{k:03d}", f"file f = sha256:{h}\nclaim {stmt}\n".encode("ascii"), store
    elif corpus == "partV":
        import helpers
        p, h = helpers.tsv(tmp, "gn.tsv", PART_N_TABLE)
        store = R.Store([p])
        for k, stmt in enumerate(part_v_family()):
            yield f"pv{k:03d}", f"file f = sha256:{h}\nclaim {stmt}\n".encode("ascii"), store
    elif corpus == "partH":
        import bidsfix
        import helpers
        files = part_h_files(tmp)
        store = R.Store([f for f, _ in files.values()])
        head = "".join(f"file {n} = sha256:{h}\n" for n, (_, h) in sorted(files.items()))
        for k, stmt in enumerate(part_h_family()):
            yield f"ph{k:03d}", (head + f"claim {stmt}\n").encode("ascii"), store
    else:
        raise SystemExit(f"unknown corpus {corpus!r}")


PART_H_JSON = '{"a": [10, 20, 30], "b": 4, "c": {"d": "x", "e": 2.5}, "f": null}'


def part_h_files(tmp):
    """The part-H family's files: a JSON text g, a NIfTI-1 header n (64 x 64 x 30 x 10), raw bytes r."""
    import bidsfix
    import helpers
    return {"g": helpers.tsv(tmp, "j.json", PART_H_JSON), "n": helpers.tsv(tmp, "img.nii", bidsfix.nifti1((64, 64, 30, 10), tr=2.0)),
            "r": helpers.tsv(tmp, "r.bin", "hello world")}


def part_h_family(n=400, seed=1029):
    """Generated family for part H (phase 5): member/item chains of a JSON file (numbers, strings, objects,
    missing keys, null), dim() of a NIfTI header, size() and bytes() of a raw file; differences (also of a
    value with itself), widen, comparisons, cutoffs near and past the int16 range."""
    rng = random.Random(seed)

    def jnum():
        return rng.choice(['member(json(g), "b")', 'item(member(json(g), "a"), {})'.format(rng.randint(1, 4)),
                           'member(member(json(g), "c"), "e")', 'member(json(g), "{}")'.format(rng.choice("bfz"))])

    def num(d=0):
        r = rng.random()
        if r < 0.55 or d > 1:
            return rng.choice([jnum(), f"dim(nifti(n), {rng.randint(1, 5)})", "size(r)"])
        if r < 0.75:
            return f"widen({num(d + 1)}, tolerance = {rng.choice(['1', '1/2'])})"
        a = num(d + 1)
        return f"difference({a}, {a if rng.random() < 0.25 else num(d + 1)})"

    out = []
    for _ in range(n):
        r = rng.random()
        if r < 0.1:
            out.append(rng.choice(['member(member(json(g), "c"), "d")', f"bytes(r, {rng.randint(0, 12)}, {rng.randint(1, 4)})"]))
        elif r < 0.5:
            out.append(num())
        else:
            out.append(f"{rng.choice(['exceeds', 'below', 'atleast', 'atmost'])}({num()}, c = {rng.choice(['0', '3', '11', '30', '64', '32767', '40000', '1/2'])})")
    return out


PART_N_TABLE = b"group\tsite\tage\tscore\nA\ts1\t30\t2\nB\ts2\t41\t5\nP\ts1\t-4.5\t2\nB\ts1\t7\t0.5\nZ\ts2\t12\t9\n"


def part_n_family(n=600, seed=1028):
    """Generated family for part N (phase 4): sum, mean, max, min, order, median over selections with
    eq/ne and number conditions, differences (also of a value with itself), widen (one or two
    tolerances, differences of widened values), and comparisons with integer, decimal and fractional cutoffs."""
    rng = random.Random(seed)
    lits = {"group": ["A", "B", "P", "Z"], "site": ["s1", "s2", "s9"]}
    cuts = ["0", "2", "7", "10", "12.5", "1/3", "-5"]

    def cond():
        if rng.random() < 0.4:
            return f'{rng.choice(["ge", "gt", "le", "lt"])}("{rng.choice(["age", "score"])}", c = {rng.choice(cuts)})'
        c = rng.choice(sorted(lits))
        return f'{rng.choice(["eq", "ne"])}("{c}", "{rng.choice(lits[c])}")'

    def src():
        return "t" if rng.random() < 0.3 else "where(t, " + ", ".join(cond() for _ in range(rng.randint(1, 2))) + ")"

    def agg():
        f = rng.choice(["sum", "mean", "max", "min", "order", "median"])
        col = '"age"' if rng.random() < 0.6 else '"score"'
        return f"order({src()}, {col}, {rng.randint(1, 3)})" if f == "order" else f"{f}({src()}, {col})"

    def num(d=0):
        r = rng.random()
        if r < 0.5 or d > 1:
            return agg()
        if r < 0.75:
            return f"widen({num(d + 1)}, tolerance = {rng.choice(['1', '1/2', '2.5'])})"
        a = num(d + 1)
        return f"difference({a}, {a if rng.random() < 0.25 else num(d + 1)})"

    out = []
    for _ in range(n):
        if rng.random() < 0.45:
            out.append(num())
        else:
            out.append(f"{rng.choice(['exceeds', 'below', 'atleast', 'atmost'])}({num()}, c = {rng.choice(cuts)})")
    return [re.sub(r"\bt\b", "tsv(f)", s) for s in out]


def part_v_family(n=300, seed=1030):
    """Generated family for the variance phase: sample/population variances and SDs over selections with eq/ne and
    number conditions, alone or compared with cutoffs (negative, zero, small, at the bounds of 3.7)."""
    rng = random.Random(seed)
    lits = {"group": ["A", "B", "P", "Z"], "site": ["s1", "s2", "s9"]}
    cuts = ["0", "2", "7", "10", "12.5", "-5", "30"]

    def cond():
        if rng.random() < 0.5:
            return f'{rng.choice(["ge", "gt", "le", "lt"])}("{rng.choice(["age", "score"])}", c = {rng.choice(cuts)})'
        c = rng.choice(sorted(lits))
        return f'{rng.choice(["eq", "ne"])}("{c}", "{rng.choice(lits[c])}")'

    out = []
    for _ in range(n):
        src = "t" if rng.random() < 0.25 else "where(t, " + ", ".join(cond() for _ in range(rng.randint(1, 3))) + ")"
        v = f'{rng.choice(["sample_variance", "population_variance", "sample_sd", "population_sd"])}({src}, "{rng.choice(["age", "score"])}")'
        out.append(v if rng.random() < 0.35 else f"{rng.choice(['exceeds', 'below', 'atleast', 'atmost'])}({v}, c = {rng.choice(['-1', '0', '1/2', '2', '25', '72', '144', '1000'])})")
    return [re.sub(r"\bt\b", "tsv(f)", s) for s in out]


PART_T2_TABLE = b"group\tsite\tage\nA\ts1\t30\nB\ts2\t41\nP\ts1\t-4.5\nB\ts1\t7\nZ\ts2\t12\n"


def part_t2_family(n=600, seed=1027):
    """Generated family for the part-T additions of the phase 3 checkpoint (BB's ruling 3): number
    conditions (ge/gt/le/lt), cell() by position and by key (one or two pairs), header(), number() of
    cells and headers, differences of numbers (also of a value with itself), mixed with counts and
    shares, and comparisons with integer, decimal and fractional cutoffs."""
    rng = random.Random(seed)
    lits = {"group": ["A", "B", "P", "Z"], "site": ["s1", "s2", "s9"]}
    cuts = ["0", "7", "10", "12.5", "30", "1/3", "-5"]

    def cond():
        if rng.random() < 0.45:
            return f'{rng.choice(["ge", "gt", "le", "lt"])}("age", c = {rng.choice(cuts)})'
        c = rng.choice(sorted(lits))
        return f'{rng.choice(["eq", "ne"])}("{c}", "{rng.choice(lits[c])}")'

    def sel():
        return "where(t, " + ", ".join(cond() for _ in range(rng.randint(1, 3))) + ")"

    def row():
        if rng.random() < 0.5:
            return str(rng.randint(1, 3))
        pairs = [f'"group", "{rng.choice(lits["group"])}"'] + ([f'"site", "{rng.choice(lits["site"])}"'] if rng.random() < 0.4 else [])
        return "key(" + ", ".join(pairs) + ")"

    def cell():
        return f'cell(t, {row()}, {rng.choice(["1", "2", "3", chr(34) + "age" + chr(34)])})'

    def num(d=0):
        r = rng.random()
        if r < 0.45 or d > 1:
            return f"number(cell(t, {row()}, 3))" if rng.random() < 0.9 else f"number(header(t, {rng.randint(1, 3)}))"
        if r < 0.7:
            a = num(d + 1)
            return f"difference({a}, {a if rng.random() < 0.2 else num(d + 1)})"
        return f"difference(difference(count({sel()}), rows(t)), {num(d + 1)})"

    out = []
    for _ in range(n):
        r = rng.random()
        op = rng.choice(["exceeds", "below", "atleast", "atmost"])
        if r < 0.15:
            out.append(cell())
        elif r < 0.2:
            out.append(f"header(t, {rng.randint(1, 3)})")
        elif r < 0.4:
            out.append(num())
        elif r < 0.6:
            out.append(f"{op}({num()}, c = {rng.choice(cuts)})")
        elif r < 0.75:
            out.append(f"count({sel()})")
        elif r < 0.85:
            base = cond()
            out.append(f"share(where(t, {base}, {cond()}), where(t, {base}))" if rng.random() < 0.5 else f"share({sel()})")
        else:
            out.append(f"{op}(count({sel()}), c = {rng.choice(['0', '1', '2', '1/2'])})")
    return [re.sub(r"\bt\b", "tsv(f)", s) for s in out]


PART_T_TABLE = b"group\tsite\tsex\nA\ts1\tF\nA\ts2\tM\nB\ts1\tF\nB\ts1\tM\nP\ts2\tF\nA\ts3\tM\nB\ts2\tF\n"


def part_t_family(n=600, seed=1026):
    """Generated part-T family (Phase 1 checkpoint): counts, rows, nested differences, shares with and
    without a base, comparisons with small, large and fractional cutoffs; eq/ne on 1-3 columns."""
    rng = random.Random(seed)
    lits = {"group": ["A", "B", "P", "Z"], "site": ["s1", "s2", "s3", "s9"], "sex": ["F", "M", "X"]}

    def cond():
        c = rng.choice(sorted(lits))
        col = rng.choice([f'"{c}"', str(sorted(lits).index(c) + 1)]) if False else f'"{c}"'
        return f'{rng.choice(["eq", "ne"])}({col}, "{rng.choice(lits[c])}")'

    def sel(k=None):
        k = rng.randint(1, 3) if k is None else k
        return "where(t, " + ", ".join(cond() for _ in range(k)) + ")"

    def cnt(d):
        r = rng.random()
        if d > 0 and r < 0.3:
            return f"difference({cnt(d - 1)}, {cnt(d - 1)})"
        return rng.choice(["count(t)", "rows(t)"]) if r < 0.4 else f"count({sel()})"

    def shr():
        if rng.random() < 0.4:
            return f"share({sel()})"
        base = [cond() for _ in range(rng.randint(1, 2))]
        extra = [cond() for _ in range(rng.randint(1, 2))]
        return f"share(where(t, {', '.join(base + extra)}), where(t, {', '.join(base)}))"

    cuts = ["0", "1", "2", "7", "1000", "1000000", "1000000000"]
    fr = ["1/2", "1/3", "333/1000", "2/7", "99/100", "1/1000000", "0", "1"]
    out = []
    for _ in range(n):
        r = rng.random()
        op = rng.choice(["exceeds", "below", "atleast", "atmost"])
        if r < 0.25:
            out.append(cnt(2))
        elif r < 0.45:
            out.append(shr())
        elif r < 0.7:
            out.append(f"{op}({cnt(2)}, c = {rng.choice(cuts)})")
        else:
            out.append(f"{op}({shr()}, c = {rng.choice(fr)})")
    return [re.sub(r"\bt\b", "tsv(f)", s) for s in out]


def run(mod, corpus, keep=False):
    """{program id: (statement lines, W1/W2 records or None)} for one decider over one corpus."""
    out = {}
    tmp = tempfile.mkdtemp(prefix="exactdiff-")
    try:
        with using(mod) as rec:
            for pid, prog, store in programs(corpus, tmp):
                rec.records = []
                ok, lines = check(prog, store)
                out[pid] = (statement_lines(lines), rec.records if keep else None, prog)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def carve_classes():
    cls = {}
    with open(os.path.join(V4, "tests", "differential-carve-outs.tsv"), encoding="utf-8") as f:
        for ln in f:
            c = ln.rstrip("\n").split("\t")
            cls[(c[1], c[2])] = c[0]
    return cls


def compare(a, b, corpus, carve=None):
    """List of (corpus, program id, line, class, carve-out class, A line, B line)."""
    diffs = []
    for pid in a:
        la, lb = a[pid][0], b[pid][0]
        for n in sorted(set(la) | set(lb)):
            x, y = la.get(n), lb.get(n)
            if x == y:
                continue
            if x is None or y is None:
                kind = "missing"
            elif x[0] == "refused" and y[0] == "formed":
                kind = "refuse/form"
            elif x[0] == "formed" and y[0] == "refused":
                kind = "form/refuse"
            elif x[1] != y[1]:
                kind = "code"
            else:
                kind = "text"
            cc = (carve or {}).get((pid, str(n))) or (carve or {}).get((pid, "-")) or ""
            diffs.append((corpus, pid, n, kind, cc, x[2] if x else "", y[2] if y else ""))
    return diffs


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    A, B = argv[0], argv[1]
    corpora = argv[argv.index("--corpus") + 1].split(",") if "--corpus" in argv else list(CORPORA)
    outp = argv[argv.index("--out") + 1] if "--out" in argv else None
    carve = carve_classes()
    allx = []
    print(f"deciders: A = {A}, B = {B}")
    for c in corpora:
        ra, rb = run(decider(A), c), run(decider(B), c)
        n = sum(len(v[0]) for v in ra.values())
        d = compare(ra, rb, c, carve if c == "differential" else None)
        kinds = {}
        for x in d:
            kinds[x[3]] = kinds.get(x[3], 0) + 1
        print(f"{c:13s} programs {len(ra):6d}  statement lines {n:6d}  differences {len(d):5d}  " + " ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
        allx += d
    if outp:
        with open(outp, "w", encoding="utf-8") as f:
            f.write("corpus\tprogram\tline\tclass\tcarve-out\tA\tB\n")
            for x in allx:
                f.write("\t".join(str(v).replace("\t", "\\t") for v in x) + "\n")
    print(f"total differences: {len(allx)}")
    return 1 if allx else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
