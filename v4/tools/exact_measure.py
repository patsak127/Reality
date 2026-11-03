"""Exact-decision Phase 0 measurements (plans/exact-decision-procedure.md section 9, phase 0). Report only.

python3 tools/exact_measure.py [--corpus NAMES] [--out FILE]

For every claim of the corpora of tools/exact_diff.py, under the live decider:
  1. by kind, the claims that mention it (after following let names, all claims) and those that reach
     W1/W2 (the witness is called), with their verdicts. Kinds: variance/SD, max/min/order/median, BIDS,
     JSON, NIfTI, size/bytes, CSV, two or more file slots.
  2. for the claims that reach W1/W2, the plan's row-type estimate (section 4.1), per table slot:
     classes of a column = its literals + 1 ("other"), and for a column read as a number its literals
     + 2p + 2 (the 2p + 1 regions that p cutoff points cut the rationals into, and "not a decimal");
     raw types = the product over the columns the statement reads; grouped types = the distinct
     signatures of the raw types (membership in every where() of that slot, and the region of every
     column an aggregate reads), enumerated when there are at most 200 000 raw types. Cutoff points of
     a column: its ge/gt/le/lt cutoffs, the decimal literals compared with it, and the c of every
     comparison over a max/min/order/median of it. This is an estimate of the plan's normal form, not
     the normal form: it is not built yet."""
import itertools
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import exact_diff as X  # noqa: E402
from reality4 import witness as W  # noqa: E402
import old_witness as OW  # noqa: E402  (the deleted search's Plan, colkey, NUMERIC_FNS: phase 7)
from reality4.readers import Refusal  # noqa: E402
from reality4.syntax import Call, Dec, Int, Name, Ratio, SyntaxRefusal, parse_line, split_program  # noqa: E402

KINDS = {
    "variance/SD": {"sample_variance", "population_variance", "sample_sd", "population_sd", "variance", "pvariance", "sd", "psd"},
    "max/min/order/median": {"max", "min", "order", "median"},
    "BIDS": {"bids"},
    "JSON": {"json"},
    "NIfTI": {"nifti"},
    "size/bytes": {"size", "bytes"},
    "CSV": {"csv"},
    "sum/mean": {"sum", "mean"},
    "number()": {"number"},
    "number conditions": {"ge", "gt", "le", "lt"},
    "widen": {"widen"},
    "share": {"share"},
    "cell/header": {"cell", "header"},
}
# the plan's phase 3 part T alone: no number work, no file-level or BIDS reader, no variance
NOT_T = {"variance/SD", "max/min/order/median", "BIDS", "JSON", "NIfTI", "size/bytes", "sum/mean", "number()", "number conditions", "widen"}
EXTREME = {"max", "min", "order", "median"}
COMPARE = {"exceeds", "below", "atleast", "atmost"}
ENUM_LIMIT = 200_000


def fns(e):
    return {x.fn for x in W.walk(e) if isinstance(x, Call)}


def names(e):
    return {x.id for x in W.walk(e) if isinstance(x, Name)}


def claim_kinds(prog):
    """{line: set of kinds} for every claim line of the program, following let names (text only)."""
    out, env = {}, {}
    try:
        lines = split_program(prog)
    except SyntaxRefusal:
        return out
    for ln, text in lines:
        try:
            st = parse_line(text, ln)
        except SyntaxRefusal:
            continue
        if st is None or st.expr is None:
            continue
        f, seen, todo = set(fns(st.expr)), set(), list(names(st.expr))
        nslot = set()
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            if n in env:
                f |= env[n][0]
                todo += list(env[n][1])
        if st.kind == "let":
            env[st.name] = (fns(st.expr), names(st.expr))
        elif st.kind == "claim":
            out[ln] = {k for k, s in KINDS.items() if f & s}
    return out


def num(v):
    if isinstance(v, Int):
        return Fraction(v.v)
    if isinstance(v, Dec):
        return v.v
    if isinstance(v, Ratio):
        return Fraction(v.n, v.d)
    return None


def as_decimal(b):
    try:
        s = b.decode("ascii")
        return Fraction(s) if s and s.lstrip("-").replace(".", "", 1).isdigit() else None
    except (UnicodeDecodeError, ValueError, ZeroDivisionError):
        return None


def where_nodes(expr):
    """[(slot, [conditions])] for every where(), conditions collected through nested where()."""
    out = []
    for x in W.walk(expr):
        if isinstance(x, Call) and x.fn == "where" and x.args:
            conds, b = list(x.args[1:]), x.args[0]
            while isinstance(b, Call) and b.fn == "where" and b.args:
                conds += list(b.args[1:])
                b = b.args[0]
            s = W.slot_of(x)
            if s is not None:
                out.append((s, conds))
    return out


def estimate(expr):
    """Per slot: (columns, raw types, grouped types or None, rows named by position)."""
    plan = OW.Plan(expr)
    points, aggcols = {}, {}
    for x in W.walk(expr):
        if not isinstance(x, Call):
            continue
        if x.fn == "where":
            s = W.slot_of(x)
            for c in x.args[1:]:
                if isinstance(c, Call) and c.fn in ("ge", "gt", "le", "lt") and c.args and c.params:
                    k, q = OW.colkey(c.args[0]), num(c.params[0].value)
                    if s is not None and k is not None and q is not None:
                        points.setdefault((s, k), set()).add(q)
        if x.fn in OW.NUMERIC_FNS and len(x.args) >= 2:
            s, k = W.slot_of(x.args[0]) if x.args else None, OW.colkey(x.args[1])
            if s is not None and k is not None:
                aggcols.setdefault(s, set()).add(k)
        if x.fn in COMPARE and x.args and x.params:
            q = num(x.params[0].value)
            for y in W.walk(x.args[0]):
                if isinstance(y, Call) and y.fn in EXTREME and len(y.args) >= 2 and q is not None:
                    s, k = W.slot_of(y.args[0]), OW.colkey(y.args[1])
                    if s is not None and k is not None:
                        points.setdefault((s, k), set()).add(q)
    wn = where_nodes(expr)
    res = {}
    for s, cols in plan.cols.items():
        numeric = plan.numeric.get(s, set())
        classes = {}
        for k, lits in cols.items():
            cl = [("lit", l) for l in lits]
            if k in numeric:
                pts = sorted(points.get((s, k), set()) | {v for v in map(as_decimal, lits) if v is not None})
                regs = [("pt", p) for p in pts] + [("iv", a, b) for a, b in zip([None] + pts, pts + [None])]
                cl += [("other", r) for r in regs] + [("other", ("nd",))]
            else:
                cl.append(("other", None))
            classes[k] = cl
        raw = 1
        for c in classes.values():
            raw *= len(c)
        grouped = None
        if raw <= ENUM_LIMIT:
            keys = list(classes)
            mine = [conds for sl, conds in wn if sl == s]
            sig = set()
            for combo in itertools.product(*(classes[k] for k in keys)):
                t = dict(zip(keys, combo))
                sig.add(tuple(tuple(cond_value(c, t) for c in conds) for conds in mine) + tuple(region(t.get(k)) for k in sorted(aggcols.get(s, set()), key=repr)))
            grouped = len(sig)
        res[s] = (len(cols), raw, grouped, len(plan.rows.get(s, ())))
    return res


def value_of(cl):
    if cl is None:
        return None
    if cl[0] == "lit":
        return as_decimal(cl[1])
    r = cl[1]
    if r is None or r[0] == "nd":
        return None
    if r[0] == "pt":
        return r[1]
    a, b = r[1], r[2]
    return (a + b) / 2 if a is not None and b is not None else (b - 1 if a is None and b is not None else (a + 1 if a is not None else Fraction(0)))


def region(cl):
    if cl is None:
        return None
    v = value_of(cl)
    return ("lit", cl[1]) if cl[0] == "lit" else cl[1] if v is None else cl[1]


def cond_value(c, t):
    if not isinstance(c, Call) or not c.args:
        return "?"
    k = OW.colkey(c.args[0])
    cl = t.get(k)
    if c.fn in ("eq", "ne") and len(c.args) == 2:
        lit = getattr(c.args[1], "v", None)
        hit = cl is not None and cl[0] == "lit" and cl[1] == lit
        return hit if c.fn == "eq" else not hit
    if c.fn in ("ge", "gt", "le", "lt") and c.params:
        v, q = value_of(cl), num(c.params[0].value)
        if v is None or q is None:
            return "?"
        return {"ge": v >= q, "gt": v > q, "le": v <= q, "lt": v < q}[c.fn]
    return "?"


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else 0


def main(argv):
    corpora = argv[argv.index("--corpus") + 1].split(",") if "--corpus" in argv else list(X.CORPORA)
    outp = argv[argv.index("--out") + 1] if "--out" in argv else None
    rows = []
    carve = X.carve_classes()
    for c in corpora:
        res = X.run(X.decider("live"), c, keep=True)
        for pid, (lines, recs, prog) in res.items():
            kinds = claim_kinds(prog)
            reached = {r["line"]: r for r in recs}
            for ln, ks in sorted(kinds.items()):
                st = lines.get(ln)
                verdict = "none" if st is None else ("formed" if st[0] == "formed" else st[1])
                r = reached.get(ln)
                est = estimate(r["judged"]) if r is not None else {}
                nslots = len({x for x in names(r["judged"])}) if r is not None else 0
                cc = carve.get((pid, str(ln)), "") if c == "differential" else ""
                rows.append((c, pid, ln, sorted(ks) + (["2+ slots"] if nslots >= 2 else []), r is not None, verdict, est, cc, r["code"] if r is not None else None))
    report(rows)
    if outp:
        with open(outp, "w", encoding="utf-8") as f:
            f.write("corpus\tprogram\tline\tkinds\treaches W1/W2\tW1/W2 code\tverdict\tcarve-out\tslots (slot:cols/raw/grouped/posrows)\n")
            for c, pid, ln, ks, reach, v, est, cc, wc in rows:
                f.write(f"{c}\t{pid}\t{ln}\t{','.join(ks)}\t{int(reach)}\t{wc or '-'}\t{v}\t{cc}\t" + " ".join(f"{s}:{a}/{b}/{g}/{p}" for s, (a, b, g, p) in sorted(est.items())) + "\n")


def report(rows):
    print("1. Claims by kind (all = every claim line; W = reaching W1/W2; pass = W1/W2 held; S008/S011/R013 = refused by W1/W2; formed = the line formed)")
    corp = sorted({r[0] for r in rows}, key=lambda c: (list(X.CORPORA) + [c]).index(c))
    allk = list(KINDS) + ["2+ slots", "(part T only)"]
    print(f"{'corpus':13s} {'kind':22s} {'all':>7s} {'W':>7s} {'pass':>7s} {'formed':>7s} {'S008':>6s} {'S011':>6s} {'R013':>6s}")
    for c in corp + ["TOTAL"]:
        sel = [r for r in rows if c == "TOTAL" or r[0] == c]
        for k in ["(any)"] + allk:
            s = [r for r in sel if k == "(any)" or k in r[3] or (k == "(part T only)" and not set(r[3]) & NOT_T)]
            if not s:
                continue
            w = [r for r in s if r[4]]
            cnt = lambda v: sum(1 for r in w if r[8] == v)  # noqa: E731
            print(f"{c:13s} {k:22s} {len(s):7d} {len(w):7d} {cnt(None):7d} {sum(1 for r in s if r[5] == 'formed'):7d} {cnt('S008'):6d} {cnt('S011'):6d} {cnt('R013'):6d}")
    print("\n2. Row types per table slot, claims reaching W1/W2 (estimate, see the docstring)")
    print(f"{'corpus':13s} {'slots':>6s} {'raw max':>9s} {'raw p50':>8s} {'raw p99':>8s} {'>64 raw':>8s} {'>1000':>6s} {'grp max':>8s} {'grp p50':>8s} {'grp p99':>8s} {'>64 grp':>8s} {'not enum':>9s}")
    for c in corp + ["TOTAL", "carve w1-w2-s012"]:
        if c == "carve w1-w2-s012":
            sel = [r for r in rows if r[7] == "w1-w2-s012"]
        else:
            sel = [r for r in rows if c == "TOTAL" or r[0] == c]
        ests = [e for r in sel for e in r[6].values()]
        raw = [e[1] for e in ests]
        grp = [e[2] for e in ests if e[2] is not None]
        if not ests:
            continue
        print(f"{c:13s} {len(ests):6d} {max(raw):9d} {pct(raw, .5):8d} {pct(raw, .99):8d} {sum(x > 64 for x in raw):8d} {sum(x > 1000 for x in raw):6d} {max(grp or [0]):8d} {pct(grp, .5):8d} {pct(grp, .99):8d} {sum(x > 64 for x in grp):8d} {sum(e[2] is None for e in ests):9d}")


if __name__ == "__main__":
    main(sys.argv[1:])
