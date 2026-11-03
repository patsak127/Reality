"""Exact-decision Phase 1: a MEASUREMENT PROTOTYPE, untrusted, not part of the checker.

It builds the part-T systems of plans/exact-decision-procedure.md (counts, rows, shares, differences of
counts, comparisons; eq/ne conditions) from statements as judged, and decides their integer step with
src/reality4/intstep.py (SPEC-EXACT 4; its own phase 1 copy of the solver is gone). It exists to measure, on the corpora, whether bounded enumeration
would do instead, and what elimination costs. Realisability of row types is not modelled here (every type
counts as realisable), so its verdicts are not the checker's; phase 3 builds the real model.

python3 tools/exact_proto.py [--corpus NAMES] [--suite-dump FILE] [--out FILE]"""
import math
import os
import pickle
import sys
import time
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import exact_diff as X  # noqa: E402
from reality4 import intstep as I  # noqa: E402
from reality4 import witness as W  # noqa: E402
import old_witness as OW  # noqa: E402  (the deleted search's Plan, colkey, NUMERIC_FNS: phase 7)
from reality4.syntax import Call, Dec, Int, Name, Ratio, Str  # noqa: E402

# ---- linear atoms over the naturals --------------------------------------------------------------
# A form is (coeffs: tuple of (var, int) sorted, const: int). Atoms: ("ge", form): form >= 0;
# ("dvd", m, form): m divides form (m >= 1).


def form(coeffs, const=0):
    return (tuple(sorted((v, c) for v, c in coeffs.items() if c != 0)), const)


def fval(f, x):
    return sum(c * x[v] for v, c in f[0]) + f[1]


def coef(f, y):
    for v, c in f[0]:
        if v == y:
            return c
    return 0


class Stats:
    def __init__(self):
        self.nodes, self.max_delta, self.max_mod, self.max_coef = 0, 1, 1, 0


def vars_of(atoms):
    return sorted({v for a in atoms for v, _ in a[-1][0]}, key=repr)


def papadimitriou(atoms):
    """n (m a)^(2m+1) for the initial system (ge atoms only): log10 of the box it gives for enumeration."""
    vs = vars_of(atoms)
    m = len(atoms)
    a = max([1] + [abs(c) for at in atoms for _, c in at[-1][0]] + [abs(at[-1][1]) for at in atoms])
    n = max(1, len(vs))
    b = math.log10(n) + (2 * m + 1) * math.log10(max(1, m) * a)
    return b, len(vs) * max(b, math.log10(2))

# ---- part T: statements as judged -> forms over row types -----------------------------------------


class NotT(Exception):
    pass


def num(v):
    if isinstance(v, Int):
        return Fraction(v.v)
    if isinstance(v, Dec):
        return Fraction(v.v)
    if isinstance(v, Ratio):
        return Fraction(v.n, v.d)
    raise NotT("cutoff")


class Model:
    def __init__(self, expr):
        self.lits = {}    # (slot, colkey) -> [literal bytes]
        for x in W.walk(expr):
            if isinstance(x, Call) and x.fn in ("eq", "ne") and len(x.args) == 2 and isinstance(x.args[1], Str):
                pass
        self.expr = expr
        self._collect(expr)
        self.cols = {}
        for (s, k), ls in self.lits.items():
            self.cols.setdefault(s, []).append(k)
        self.types = {}
        for s, ks in self.cols.items():
            ks.sort(key=repr)
            ts = [()]
            for k in ks:
                ts = [t + (i,) for t in ts for i in range(len(self.lits[(s, k)]) + 1)]
            self.types[s] = ts

    def _collect(self, e):
        for x in W.walk(e):
            if isinstance(x, Call) and x.fn == "where":
                s = W.slot_of(x)
                for c in x.args[1:]:
                    if isinstance(c, Call) and c.fn in ("eq", "ne") and len(c.args) == 2 and isinstance(c.args[1], Str) and OW.colkey(c.args[0]):
                        lst = self.lits.setdefault((s, OW.colkey(c.args[0])), [])
                        if c.args[1].v not in lst:
                            lst.append(c.args[1].v)

    def all_types(self, slot):
        return self.types.get(slot, [()])

    def sat(self, slot, t, conds):
        ks = self.cols.get(slot, [])
        for c in conds:
            k = OW.colkey(c.args[0])
            i = self.lits[(slot, k)].index(c.args[1].v)
            hit = t[ks.index(k)] == i
            if (c.fn == "eq") != hit:
                return False
        return True

    def ev(self, e):
        if not isinstance(e, Call):
            raise NotT("leaf")
        f = e.fn
        if f in ("tsv", "csv") and len(e.args) == 1 and isinstance(e.args[0], Name):
            return ("table", e.args[0].id, ())
        if f == "where":
            b = self.ev(e.args[0])
            if b[0] not in ("table", "sel"):
                raise NotT("where base")
            for c in e.args[1:]:
                if not (isinstance(c, Call) and c.fn in ("eq", "ne") and len(c.args) == 2 and isinstance(c.args[1], Str) and OW.colkey(c.args[0])):
                    raise NotT("condition")
            return ("sel", b[1], b[2] + tuple(e.args[1:]))
        if f in ("rows", "count"):
            b = self.ev(e.args[0])
            if b[0] not in ("table", "sel") or len(e.args) != 1:
                raise NotT("count arg")
            return ("lin", self.count_form(b))
        if f == "share":
            s = self.ev(e.args[0])
            if s[0] != "sel":
                raise NotT("share arg")
            if len(e.args) == 1:
                base = ("table", s[1], ())
            else:
                base = self.ev(e.args[1])
                if base[0] not in ("table", "sel") or base[1] != s[1] or any(c not in s[2] for c in base[2]):
                    raise NotT("S006")
            return ("share", self.count_form(s), self.count_form(base))
        if f == "difference" and len(e.args) == 2:
            a, b = self.ev(e.args[0]), self.ev(e.args[1])
            if a[0] != "lin" or b[0] != "lin":
                raise NotT("difference of non-counts")
            return ("lin", sub(a[1], b[1]))
        if f in ("exceeds", "below", "atleast", "atmost") and len(e.args) == 1 and e.params:
            x = self.ev(e.args[0])
            if x[0] not in ("lin", "share"):
                raise NotT("comparison arg")
            return ("cmp", f, x, num(e.params[0].value))
        raise NotT(f)

    def count_form(self, s):
        return {(s[1], t): 1 for t in self.all_types(s[1]) if self.sat(s[1], t, s[2])}


def sub(a, b):
    d = dict(a)
    for k, v in b.items():
        d[k] = d.get(k, 0) - v
    return {k: v for k, v in d.items() if v}


def lin_atom(F, op, c):
    """Atom (as ge) for F op c, F an integer form (dict), c = p/q."""
    p, q = c.numerator, c.denominator
    if op in ("exceeds", "atleast"):
        return form({v: q * a for v, a in F.items()}, -p - (1 if op == "exceeds" else 0))
    return form({v: -q * a for v, a in F.items()}, p - (1 if op == "below" else 0))


def share_atom(S, B, op, c):
    """S/B op c with B >= 1: q*S - p*B op 0."""
    p, q = c.numerator, c.denominator
    G = sub({v: q * a for v, a in S.items()}, {v: p * a for v, a in B.items()})
    return lin_atom(G, op, Fraction(0))


def outcomes(val):
    """[(outcome label, [atoms])] partitioning the inputs by the value's outcome (for comparisons)."""
    kind = val[0]
    if kind == "cmp":
        _, op, x, c = val
        neg = {"exceeds": "atmost", "atmost": "exceeds", "below": "atleast", "atleast": "below"}[op]
        if x[0] == "lin":
            return [("holds", [("ge", lin_atom(x[1], op, c))]), ("fails", [("ge", lin_atom(x[1], neg, c))])]
        S, B = x[1], x[2]
        dom = ("ge", form(B, -1))
        return [("holds", [dom, ("ge", share_atom(S, B, op, c))]), ("fails", [dom, ("ge", share_atom(S, B, neg, c))]),
                ("V003", [("ge", form({v: -a for v, a in B.items()}, 0))])]
    raise ValueError(kind)


def rename(atoms, tag):
    return [a[:-1] + (form({(tag, v): c for v, c in a[-1][0]}, a[-1][1]),) for a in atoms]


def group(atoms):
    """Merge variables with the same coefficient column (SPEC-EXACT 3.3; Exact.lean merge lemma)."""
    vs = vars_of(atoms)
    col = {v: tuple(coef(a[-1], v) for a in atoms) for v in vs}
    rep = {}
    for v in vs:
        rep.setdefault(col[v], v)
    out = []
    for a in atoms:
        d = {}
        for v, c in a[-1][0]:
            if rep[col[v]] == v:
                d[v] = c
        out.append(a[:-1] + (form(d, a[-1][1]),))
    return out, len(vs), len(rep)


def questions(expr):
    """(kind, label, payload) for every W1/W2 question of a part-T statement: 'identity' needs no
    solver (a form or polynomial is checked for a nonzero coefficient); 'system' is a conjunction for the
    integer step."""
    m = Model(expr)
    out = []
    for e in W.subexprs(expr):
        v = m.ev(e)
        if v[0] == "lin":
            out.append(("identity", "W1 " + e.fn, v[1]))
        elif v[0] == "sel":
            out.append(("identity", "W1 where", m.count_form(v)))
        elif v[0] == "share":
            out.append(("system", "W1 share: an input with base > 0", [("ge", form(v[2], -1))]))
            out.append(("share-w1", "W1 share", v))
        elif v[0] == "cmp":
            for lab, atoms in outcomes(v):
                out.append(("system", f"W1 {e.fn} {lab}", atoms))
    for pi, (node, mod, desc) in enumerate(W.parts(expr)):
        desc = f"#{pi} {desc}"
        levels = [(x, W._subst(x, node, mod)) for x in W._path(expr, node)]
        for top, whole in levels:
            try:
                a, b = m.ev(top), m.ev(whole)
            except NotT:
                continue
            if a[0] == "lin":
                out.append(("identity", f"W2 {desc} at {top.fn}", sub(a[1], b[1])))
            elif a[0] == "sel":
                out.append(("identity", f"W2 {desc} at where", sub(m.count_form(a), m.count_form(b))))
            elif a[0] == "share":
                out.append(("share-w2", f"W2 {desc} at share", (a, b)))
            elif a[0] == "cmp":
                for la, xa in outcomes(a):
                    for lb, xb in outcomes(b):
                        if la != lb:
                            out.append(("system", f"W2 {desc} at {top.fn}: {la}/{lb}", xa + xb))
            break
    return out


def poly(S1, B2, S2, B1):
    """S1*B2 - S2*B1 as {(v, w) sorted: coefficient}, zero terms dropped."""
    d = {}
    for (X1, Y1, sg) in ((S1, B2, 1), (S2, B1, -1)):
        for v, a in X1.items():
            for w, b in Y1.items():
                k = tuple(sorted((v, w), key=repr))
                d[k] = d.get(k, 0) + sg * a * b
    return {k: c for k, c in d.items() if c}


def expand(kind, lab, pay):
    """Share questions as systems plus identity tests (SPEC-EXACT 5.2, 5.4)."""
    if kind == "share-w1":
        _, S, B = pay
        g0, names = to_ints([("ge", form(B, -1))])
        x0i, _ = I.solve(g0, 200000)
        x0 = None if x0i is None else {names[i]: v for i, v in x0i.items()}
        if x0 is None:
            return [("identity", lab + ": no input with base > 0", {})]
        x = {v: x0.get(v, 0) for v in B}
        x.update({v: x0.get(v, 0) for v in S})
        p, q = sum(S[v] * x[v] for v in S), sum(B[v] * x[v] for v in B)
        G = sub({v: q * a for v, a in S.items()}, {v: p * a for v, a in B.items()})
        dom = ("ge", form(B, -1))
        return [("system", lab + ": above x0", [dom, ("ge", form(G, -1))]),
                ("system", lab + ": below x0", [dom, ("ge", form({v: -a for v, a in G.items()}, -1))])]
    if kind == "share-w2":
        (_, S1, B1), (_, S2, B2) = pay
        out = [("system", lab + ": both bases > 0", [("ge", form(B1, -1)), ("ge", form(B2, -1))]),
               ("identity", lab + ": S1*B2 - S2*B1 not the zero polynomial", poly(S1, B2, S2, B1)),
               ("system", lab + ": V003 only without", [("ge", form(B1, -1)), ("ge", form({v: -a for v, a in B2.items()}))]),
               ("system", lab + ": V003 only with", [("ge", form(B2, -1)), ("ge", form({v: -a for v, a in B1.items()}))])]
        return out
    return [(kind, lab, pay)]


SYSTEMS = []


def to_ints(atoms):
    """Variables renamed 0, 1, ... in the order of their names (intstep's variables are ints)."""
    names = vars_of(atoms)
    ix = {v: i for i, v in enumerate(names)}
    return [a[:-1] + (I.form({ix[v]: c for v, c in a[-1][0]}, a[-1][1]),) for a in atoms], names


def measure(expr):
    """Per system: dict of measurements."""
    rows = []
    for kind, lab, pay in [q for q0 in questions(expr) for q in expand(*q0)]:
        if kind != "system":
            rows.append({"kind": kind, "label": lab})
            continue
        g, before, after = group(pay)
        g, names = to_ints(g)
        st = Stats()
        t0 = time.perf_counter()
        try:
            r, st.nodes = I.solve(g, 200000)
            over = False
        except I.TooBig:
            r, over = None, True
        dt = time.perf_counter() - t0
        SYSTEMS.append(g)
        ok = over or r is None or all(I.holds(a, r) for a in g)
        st.max_coef = max([0] + [abs(c) for a in g for _, c in a[-1][0]])
        pb, enum = papadimitriou(g)
        rows.append({"kind": kind, "label": lab, "vars": before, "grouped": after, "atoms": len(g), "sat": r is not None,
                     "witness_max": max(r.values()) if r else 0, "nodes": st.nodes, "max_delta": st.max_delta,
                     "max_mod": st.max_mod, "max_coef": st.max_coef, "secs": dt, "checked": ok,
                     "pap_log10": pb, "enum_log10": enum, "budget": over,
                     "system": g if over or dt > 0.05 else None})
    return rows


TIMES = {}


def main(argv):
    corpora = argv[argv.index("--corpus") + 1].split(",") if "--corpus" in argv else list(X.CORPORA)
    dump = argv[argv.index("--suite-dump") + 1] if "--suite-dump" in argv else None
    outp = argv[argv.index("--out") + 1] if "--out" in argv else None
    dumps = argv[argv.index("--dump-systems") + 1] if "--dump-systems" in argv else None
    stmts = []
    for c in corpora:
        res = X.run(X.decider("live"), c, keep=True)
        for pid, (lines, recs, prog) in res.items():
            for r in recs:
                stmts.append((c, pid, r["line"], r["judged"], r.get("secs")))
    if dump:
        with open(dump, "rb") as f:
            for row in pickle.load(f):
                stmts.append(("suite",) + tuple(row[:3]) + ((row[3] if len(row) > 3 else None),))
    seen, rows, notT = set(), [], {}
    t_model = t_live = 0.0
    for c, pid, ln, e, secs in stmts:
        if (c, e) in seen:
            continue
        seen.add((c, e))
        t0 = time.perf_counter()
        try:
            ms = measure(e)
        except NotT as x:
            notT[(c, str(x))] = notT.get((c, str(x)), 0) + 1
            continue
        t_model += time.perf_counter() - t0
        t_live += secs or 0.0
        TIMES.setdefault(c, [0.0, 0.0, 0.0, 0])
        TIMES[c][0] += secs or 0.0
        TIMES[c][1] += time.perf_counter() - t0
        TIMES[c][2] += sum(m.get("secs", 0.0) for m in ms)
        TIMES[c][3] += 1
        for mm in ms:
            rows.append((c, pid, ln, mm))
    report(rows, notT, len(seen))
    print("\ntime on the part-T statements (live W1/W2 search, as recorded in this run; exact path = prototype model + intstep):")
    for c, (lv, ex, sv, n) in sorted(TIMES.items()):
        print(f"  {c:12s} statements {n:6d}  live W1/W2 {lv:8.2f} s   exact path {ex:7.2f} s (intstep {sv:6.2f} s)")
    if dumps:
        with open(dumps, "wb") as f:
            pickle.dump(SYSTEMS, f)
    if outp:
        with open(outp, "w", encoding="utf-8") as f:
            for c, pid, ln, mm in rows:
                f.write(f"{c}\t{pid}\t{ln}\t" + "\t".join(f"{k}={v}" for k, v in mm.items()) + "\n")


def report(rows, notT, nstmts):
    print(f"distinct statements reaching W1/W2: {nstmts}; outside part T (by first reason): " + ", ".join(f"{c}:{k} {v}" for (c, k), v in sorted(notT.items())))
    for c in sorted({r[0] for r in rows}) + ["ALL"]:
        rs = [r[3] for r in rows if c == "ALL" or r[0] == c]
        sy = [m for m in rs if m["kind"] == "system"]
        idn = [m for m in rs if m["kind"] != "system"]
        if not sy:
            continue
        q = lambda k: sorted(m[k] for m in sy)  # noqa: E731
        p = lambda xs, f: xs[min(len(xs) - 1, int(f * len(xs)))]  # noqa: E731
        print(f"\n[{c}] questions: {len(rs)} ({len(idn)} without the integer step: identity tests and share checks; {len(sy)} systems)")
        print(f"  systems sat {sum(m['sat'] for m in sy)}, unsat {sum(not m['sat'] and not m['budget'] for m in sy)}, over the node budget {sum(m['budget'] for m in sy)}, witnesses checked {all(m['checked'] for m in sy)}")
        for k in ("vars", "grouped", "atoms", "max_coef", "witness_max", "nodes", "max_delta", "max_mod"):
            xs = q(k)
            print(f"  {k:12s} max {xs[-1]:>8}  p50 {p(xs, .5):>6}  p99 {p(xs, .99):>6}")
        ts = q("secs")
        print(f"  time         total {sum(ts):.3f} s  max {ts[-1] * 1000:.2f} ms  p99 {p(ts, .99) * 1000:.3f} ms")
        pa, en = q("pap_log10"), q("enum_log10")
        print(f"  generic bound n(ma)^(2m+1): log10 max {pa[-1]:.1f} p50 {p(pa, .5):.1f};  enumeration box (bound+1)^vars: log10 max {en[-1]:.1f} p50 {p(en, .5):.1f} min {en[0]:.1f}")
        print(f"  systems whose generic enumeration box is <= 10^6 points: {sum(1 for x in en if x <= 6)} of {len(en)}")


if __name__ == "__main__":
    main(sys.argv[1:])
