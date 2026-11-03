"""The exact decision's search (moved verbatim from decide.py, unit I3; BB's call 28 Oct 2026 18:05: decide.py's
search leaves the trusted base): presolve, tidy, empty_box, lp, fm, back, the integer step's wrapper and Model's
solve, solve1, half_cut, count_ints, implied, one_solve*, finish and find; since unit SRH (29 Oct 2026) also
the helpers only it calls: Log (the proof logs cert.check reads), Model.no, prove, rs_small, refine, thin, piece_atoms,
psign, unrealized, rows_of, and fpick, cap_ok, the float steps, form_bytes, spent_all; since unit HIT the variance
shapes' witness pickers Decide.d_hit, n_hit, d_domain, d_scale, two_vals, dvals and var_of (each None refuses only
through Decide.vnone's checked range certificate, or var_hit's checked vdeep/vrange record). Untrusted: every "none" it gives a
refusal is replayed with a certificate and checked by cert.py (Decide.certify); every solution it gives a form is
written as bytes and confirmed by the real readers and evaluator (Decide.run). A wrong search can make a refusal
X001 or R013, never a wrong answer. Its loops are still charged or named (tests/test_v4_loops.py scans it)."""
from . import decide as D   # the model's names, bounds and helpers, read through decide (so its bounds and patches hold here)

class MSearch(D.I.Search):
    """The integer step (intstep, unchanged) with each frame's atoms held while it runs, above what its system holds
    (SPEC-EXACT 8): its depth and its numbers' growth (pin multiplies coefficients) are bounded by nothing stated."""

    def __init__(self, limit, held):
        super().__init__(limit)
        self.held, self.base, self.now = held, held[0] * D.STEP_BYTES, 0

    def decide(self, atoms):
        b = sum(D.form_bytes(len(a[-1][0]) + 1, max([abs(c).bit_length() for _, c in a[-1][0]] + [abs(x).bit_length() for x in a[1:-1]] + [abs(a[-1][1]).bit_length(), 1])) for a in atoms)
        self.now += b
        D.hold(self.held, self.base + self.now)
        try:
            return super().decide(atoms)
        finally:
            self.now -= b


def presolve(atoms, log=None):
    """Each equality F = 0 (atoms F >= 0 and -F >= 0) over the counts with integer coefficients and a
    variable v of coefficient 1 or -1: v is replaced everywhere by what F gives, kept >= 0 (exact over the
    naturals; SPEC-EXACT 4.1). Returns the atoms and the replacements, in order. With a log (Log: its ids run beside
    the atoms), each new atom is written as the line it is: G + lam F from G's line and F's or -F's (cert.py)."""
    done = []
    while True:
        eqs = {frozenset(F.items()) for F, st in atoms if not st}
        hit = None
        for F, st in atoms:
            if not st and frozenset((u, -c) for u, c in F.items()) in eqs and all(D.Fraction(c).denominator == 1 for c in F.values()) \
                    and not any(v != D.ONE and v[0] == "z" for v in F):
                hit = min(((F, v) for v, c in F.items() if v != D.ONE and c in (1, -1)), key=lambda h: repr(h[1]), default=None)
                if hit:
                    break
        if hit is None:
            return atoms, done
        F, v = hit
        E = D.lin((-F[v], {u: c for u, c in F.items() if u != v}))   # v = E, as F[v] is 1 or -1
        if log:   # G with v := E is G - G[v] F[v] F; E = v - F[v] F
            i = {frozenset(G.items()): j for (G, st), j in zip(atoms, log.ids) if not st}   # as eqs above
            fp, fn = i[frozenset(F.items())], i[frozenset((u, -c) for u, c in F.items())]
            log.ids = [log.c([(1, j), (abs(G[v]), fp if -G[v] * F[v] > 0 else fn)]) if v in G else j for (G, st), j in zip(atoms, log.ids)]
            log.ids.append(log.c([(1, log.nat(v)), (1, fn if F[v] > 0 else fp)]))
        atoms = [(D.lin((1, {u: c for u, c in G.items() if u != v}), (G[v], E)), st) if v in G else (G, st) for G, st in atoms] + [D.ge(E)]
        done.append((v, E))


def tidy(ints, log=None):
    """Integer atoms (G, k) meaning G + k >= 0 over the naturals, made simpler without changing their
    solutions: an atom -(x1 + ... ) >= 0 sets its variables to 0 (they are dropped); an atom with no negative
    coefficient and k >= 0 always holds (dropped); two atoms G + k >= 0
    and -G + k2 >= 0 with k + k2 < 0 have no solution (None)."""
    while True:
        zero = {v for G, k in ints if k == 0 and all(c < 0 for c in G.values()) for v in G}
        if zero:
            if log:   # -x_v >= 0 from a zero atom Z and the others' x_w >= 0; then G without v: + c_v (-x_v) or |c_v| x_v
                zl = {}
                for (G, k), j in zip(ints, log.ids):
                    for v in G if k == 0 and all(c < 0 for c in G.values()) else ():
                        zl.setdefault(v, (G, j))
                zl = {v: log.c([(D.Fraction(1, -G[v]), j)] + [(D.Fraction(-c, -G[v]), log.nat(w)) for w, c in G.items() if w != v]) for v, (G, j) in zl.items()}
                log.ids = [log.c([(1, j)] + [(c, zl[v]) if c > 0 else (-c, log.nat(v)) for v, c in G.items() if v in zero]) if zero & G.keys() else j for (G, k), j in zip(ints, log.ids)]
                log.ids = [j for (G, k), j in zip(ints, log.ids) if any(v not in zero for v in G) or k < 0]
            ints = [(H, k) for H, k in (({v: c for v, c in G.items() if v not in zero}, k) for G, k in ints) if H or k < 0]
            if any(not H for H, _ in ints):
                if log:
                    log.end(next(j for (H, _), j in zip(ints, log.ids) if not H))
                return None
            continue
        if log:
            log.ids = [j for (G, k), j in zip(ints, log.ids) if k < 0 or any(c < 0 for c in G.values())]
        ints = [(G, k) for G, k in ints if k < 0 or any(c < 0 for c in G.values())]   # G + k >= 0 with G, k >= 0 always holds
        low, at = {}, {}
        for i, (G, k) in enumerate(ints):
            key = tuple(sorted(G.items(), key=lambda vc: repr(vc[0])))
            if k < low.get(key, k + 1):
                low[key], at[key] = k, i
        neg = lambda key: tuple(sorted(((v, -c) for v, c in key), key=lambda vc: repr(vc[0])))
        bad = next((key for key, k in low.items() if k + low.get(neg(key), -k) < 0), None)
        if bad is not None:
            if log:
                log.end(log.c([(1, log.ids[at[bad]]), (1, log.ids[at[neg(bad)]])]))
            return None
        return ints


def empty_box(ints, pay, rounds=32, log=None):
    """True when the integer atoms (G, k), G + k >= 0 over the naturals, have no solution by bounds alone: each atom
    bounds each of its variables by the others' bounds (rounded to integers), up to `rounds` times; crossed bounds mean
    no natural point. False says nothing ((f): spares the integer step systems on huge float-lattice coefficients).
    With a log, each bound is its line: the atom plus d times the others' bound lines, divided by |c| (cert.py "d")."""
    lo, hi, li, hj = {}, {}, {}, {}
    for _ in range(rounds):
        pay[0] += sum(len(G) for G, _ in ints)
        moved = False
        for i, (G, k) in enumerate(ints):
            for v, c in G.items():
                bs = [d * (hi.get(u) if d > 0 else lo.get(u, 0)) for u, d in G.items() if u != v and (d < 0 or u in hi)]
                if len(bs) < len(G) - 1:
                    continue   # c·x_v >= -k - (the most the others can give), unbounded here
                r = -k - sum(bs)
                new = c > 0 and -(-r // c) > lo.get(v, 0) or c < 0 and (v not in hi or -r // -c < hi[v])
                if new and log:
                    j = log.c([(1, log.ids[i])] + [(d, hj[u]) if d > 0 else (-d, li.get(u) if u in li else log.nat(u)) for u, d in G.items() if u != v])
                    (li if c > 0 else hj)[v] = log.add(("d", j))
                if c > 0 and -(-r // c) > lo.get(v, 0):
                    lo[v], moved = -(-r // c), True
                if c < 0 and (v not in hi or -r // -c < hi[v]):
                    hi[v], moved = -r // -c, True
                if v in hi and hi[v] < lo.get(v, 0):
                    if log:
                        log.end(log.c([(1, hj[v]), (1, li[v] if v in li else log.nat(v))]))
                    return True
        if not moved:
            return False
    return False


def lp(ints):
    """The rational relaxation of integer atoms (G, k), G + k >= 0, x >= 0, by phase one of the simplex
    method in exact arithmetic (Bland's rule, so it ends). Returns ("none", u) with a Farkas certificate
    (u >= 0, sum u G <= 0 in every variable, sum u k < 0: no rational point, so no natural one), ("point", x)
    for an integral vertex, or None (fractional vertex, or a certificate that does not check). The caller
    checks the point; the certificate is checked here (SPEC-EXACT 4.2). Its memory is held (hold) before it is built:
    the tableau, its cost row and the row a pivot builds, up to its largest, given back when lp returns; its numbers have
    B bits at the start and at most 4B + 1 after a pivot (a - f*b, the pivot row b = r/p of 2B bits, B the largest
    before it), held before each pivot."""
    held = [0]
    try:
        return lp1(ints, held)
    finally:
        D.MEM[0] -= held[0]


def lp1(ints, held):
    vs = sorted({v for G, _ in ints for v in G}, key=repr)
    m, n = len(ints), len(vs)
    cells, rows_ = (m + 2) * (n + 2 * m + 1), 64 * (m + 2)
    D.hold(held, cells * (D.num(D.bits(c for G, k in ints for c in [k, *G.values()])) + 8) + rows_)
    sg = [1 if k <= 0 else -1 for _, k in ints]
    T = [[D.Fraction(sg[i] * G.get(v, 0)) for v in vs] + [D.Fraction(-sg[i] if j == i else 0) for j in range(m)] + [D.Fraction(int(j == i)) for j in range(m)] + [D.Fraction(-sg[i] * k)] for i, (G, k) in enumerate(ints)]
    cost = [0] * (n + m) + [1] * m + [0]
    basis = [n + m + i for i in range(m)]
    rc = [cost[j] - sum(cost[basis[i]] * T[i][j] for i in range(m)) for j in range(n + 2 * m + 1)]   # reduced costs, kept
    while True:                                                                                      # as a row of T is
        enter = next((j for j in range(n + 2 * m) if rc[j] < 0), None)
        if enter is None:
            break
        D.hold(held, cells * (D.num(4 * D.bits(c for r in T + [rc] for c in r) + 1) + 8) + rows_)
        rows = [i for i in range(m) if T[i][enter] > 0]
        i0 = min(rows, key=lambda i: (T[i][-1] / T[i][enter], basis[i]))
        p = T[i0][enter]
        T[i0] = [c / p for c in T[i0]]
        for i in range(m):
            if i != i0 and T[i][enter]:
                f = T[i][enter]
                T[i] = [a - f * b for a, b in zip(T[i], T[i0])]
        f = rc[enter]
        rc = [a - f * b for a, b in zip(rc, T[i0])]
        basis[i0] = enter
    if sum(T[i][-1] for i in range(m) if basis[i] >= n + m) > 0:
        u = [sg[i] * (1 - rc[n + m + i]) for i in range(m)]
        ok = all(x >= 0 for x in u) and sum(x * k for x, (_, k) in zip(u, ints)) < 0 and all(sum(x * G.get(v, 0) for x, (G, _) in zip(u, ints)) <= 0 for v in vs)
        return ("none", u) if ok else None
    x = {vs[basis[i]]: T[i][-1] for i in range(m) if basis[i] < n}
    return ("point", {v: int(c) for v, c in x.items()}) if all(c.denominator == 1 for c in x.values()) else None


def fm(atoms, zs, left=None, held=None, log=None):
    """Fourier-Motzkin elimination of the rational variables zs, exactly, keeping strictness: the
    atoms over the other variables, and per eliminated variable the atoms that bound it. (e2) Big before an
    elimination would take the charge (stack and rest atoms) past left, the steps left (SPEC-EXACT 8). Each elimination's
    new atoms are held before they are made (hold): forms of len(p) + len(q) entries whose numbers have 4B + 1 bits
    (-q_z p + p_z q, B the largest in P and N), in held, which the caller gives back when its system is solved."""
    stack, paid, mem, held = [], 0, 0, [0] if held is None else held
    if log:   # (cert.py) an atom's line rides with it: (F, strict, line)
        atoms = [a + (j,) for a, j in zip(atoms, log.ids)]
    for z in zs:
        P = [a for a in atoms if a[0].get(z, 0) > 0]
        N = [a for a in atoms if a[0].get(z, 0) < 0]
        rest = [a for a in atoms if not a[0].get(z, 0)]
        paid += len(P) + len(N)
        if left is not None and paid + len(rest) + len(P) * len(N) > left:
            raise D.Big(f"deciding it needs more than {D.W.MAX_WITNESS_STEPS} counted steps (SPEC-EXACT 8)")
        if P and N:
            B = 4 * D.bits(c for a in P + N for c in a[0].values()) + 1
            e = len(N) * sum(len(a[0]) for a in P) + len(P) * sum(len(a[0]) for a in N)   # the entries of the P x N forms
            mem += D.form_bytes(0, B) * len(P) * len(N) + e * (64 + D.num(B))
            D.hold(held, mem)
        stack.append((z, [a[:2] for a in P + N]))
        for p in P:
            for q in N:
                f = D.lin((-q[0][z], p[0]), (p[0][z], q[0]))
                rest.append((f, p[1] or q[1]) + ((log.c([(-q[0][z], p[2]), (p[0][z], q[2])]),) if log else ()))
        atoms = rest
    if log:
        log.ids = [a[2] for a in atoms]
        atoms = [a[:2] for a in atoms]
    return atoms, stack


def rpick(n, lo, hi, pay):
    """(shape 3) A number of n bytes in the window (lo, hi: (end, strict) or None), 0 first, else the least above lo; or None."""
    pay[0] += 1
    ok = lambda v: v is not None and (lo is None or v > lo[0] or v == lo[0] and not lo[1]) and (hi is None or v < hi[0] or v == hi[0] and not hi[1])
    if ok(D.Fraction(0)) and D.rin(n, D.Fraction(0)):
        return D.Fraction(0)
    c = lo[0] if lo is not None and not lo[1] and D.rin(n, lo[0]) else D.rnext(n, None if lo is None else lo[0])
    return c if ok(c) else None


def back(stack, x, pay):
    """Values for the eliminated variables, last eliminated first, each strictly inside its bounds
    when they leave room (SPEC-EXACT 4.1), else at its one point."""
    for z, A in reversed(stack):
        lo = hi = None
        for F, strict in A:
            c = F[z]
            b = -D.value({u: k for u, k in F.items() if u != z}, x) / D.Fraction(c)
            if c > 0 and (lo is None or b > lo[0] or (b == lo[0] and strict)):
                lo = (b, strict)
            if c < 0 and (hi is None or b < hi[0] or (b == hi[0] and strict)):
                hi = (b, strict)
        if z[1] == "pix":   # (f) a float: the least above lo, or the point
            f = lo[0] if lo and hi and lo[0] == hi[0] else D.fpick(lo and lo[0], hi and hi[0], pay)
            x[z] = f if f is not None and D.is_float(f) else None
            if x[z] is None:
                raise D.Unreadable("a pixdim the system allows only between floats (SPEC-EXACT 3.6)", z, x, lo and lo[0])
            continue
        if z[1] == "raw":   # (shape 3) a number of z[4] bytes in its bounds; none: the point where its spellings are split
            x[z] = rpick(z[4], lo, hi, pay)
            if x[z] is None:
                l, h = lo and lo[0], hi and hi[0]
                v = (l + h) / 2 if lo and hi else l + 1 if lo else h - 1 if hi else D.Fraction(0)
                raise D.Unreadable("a byte range's number the system allows only between the numbers of its length (SPEC-EXACT 3.11)", z, x, v)
            continue
        if z[1] in ("mu", "pv"):   # (e) a mean's value (e2: a piece's mean): any rational (Model.solve checks S = mu·N)
            l, h = lo and lo[0], hi and hi[0]
            x[z] = l if l == h and l is not None else (l + h) / 2 if lo and hi else l + 1 if lo else h - 1 if hi else D.Fraction(0)
            continue
        x[z] = lo[0] if lo and hi and lo[0] == hi[0] else D.inside(lo and lo[0], hi and hi[0], pay)
        if x[z] is None and D.zkind(z) == "sum" and lo and hi:   # a sum need not be read: a point of R's finest step
            g = D.Fraction(D.floor(lo[0] * 10 ** -D.LOW) + 1, 10 ** -D.LOW)
            x[z] = g if g < hi[0] else None
        if x[z] is None or not (D.zkind(z) == "sum" or D.in_r(x[z])):
            raise D.Unreadable("a value the system allows only between ends closer than the numbers the reader reads (at most 1000 digits; P1, SPEC-EXACT 3.1)", z, x, lo and lo[0])
    return x


# Model's search methods (attached to Model by decide.py)

def solve(self, case, atoms, budget, bounded=True):
    """A solution of the case's system (one_solve) where each summed type of undecided presence has no rows and
    sum 0, or rows and a sum strictly inside (n lo, n hi), or None. The closed bounds of 3.5 are a relaxation:
    no solution, none at all; else the first type a solution breaks is decided both ways (no rows; rows) and each
    is solved, so only the types solutions touch are split (item 8), at most MAX_CASES systems."""
    held = [0]   # (memory) the cases waiting on its stack, held at their peak until it returns (SPEC-EXACT 8)
    self.tree = D.C.Tree(case, atoms, D.pay, self) if self.cert and not bounded else None   # (C4) in a refusal's check, a tree of checked leaves
    try:
        return self.solve1(case, atoms, budget, bounded, held)
    finally:
        D.MEM[0] -= held[0]
        self.leaf_at = None


def solve1(self, case, atoms, budget, bounded, held):
    todo, tried, Ps = [(case, [])], 0, [A for A in atoms if isinstance(A, D.PAtom)]
    nests = self.nests(Ps)   # (e) cases
    cps = D.caps(Ps)   # (pm) split only where a solution breaking S = mu·N admits no shared types' mean (cap_ok)
    budget[0] += 2 * len(Ps) ** 2
    Ms, Ps = Ps, Ps + self.piece_atoms(case)   # (e2) pieces' PAtoms: same N-range split, own range keys
    pc = self.pcuts(case, Ms)
    nests += pc
    budget[0] += len(Ps) - len(Ms) + sum(len(A) for _, B in pc for A in B)   # (e2) the pieces' PAtoms and cut cases
    tb, last, hmemo, tree, rule = 0, (case, [], 0, None), {}, self.tree, "root"   # hmemo: half cuts' conditions, decided once per case
    while todo:                                                                        # (count atoms only); rule: the last split's (cert.py)
        k = len(todo)
        while k and len(todo[k - 1]) == 2:   # the entries pushed since the last pop: a list, its new atoms, a new case
            k -= 1
        ids = {id(A) for A in last[1]}
        kids = [0] if rule == "root" else tree.split(last[3], rule, last[1], todo[k:]) if tree and rule else [None] * (len(todo) - k)
        for i, nd in zip(range(k, len(todo)), kids):
            c, more = todo[i]
            e = 64 + 8 * len(more) + sum(D.form_bytes(len(A[0]), D.bits(A[0].values())) for A in more if id(A) not in ids)
            e += 0 if c is last[0] else 256 + 128 * (len(c) + len(c[None].pres))
            todo[i], tb = (c, more, e, nd), tb + e
        D.hold(held, tb)
        c, more, eb, node = last = todo.pop()
        rule = None   # set by the split this node makes, if any
        tb -= eb
        tried += 1
        if tried > D.MAX_CASES:
            raise D.Big(f"deciding it needs more than {D.MAX_CASES} cases of which summed types have rows and which band of readable numbers a value is in{', or how many rows a mean inside a difference has' if Ps else ''} (SPEC-EXACT 3.1, 3.5)")
        lz = next((s for s in sorted(self.lay) if D.frange_of(("lay", s), more) is None), None)
        if lz is not None:   # (3.12b) a one-column table with an empty literal: from one column or from more (lay_cases)
            todo += [(c, more + A) for A in self.lay_cases(lz, c)]
            rule = ("model", "layout", lz)
            continue
        P = next((P for P in Ps if D.frange_of(P.key, more) is None), None)
        if P:   # (e) a mean's count of rows: from 1 to MAX_ROWS (unbounded: any), mu of either sign
            sg = self.psign(P, more) if P.a0 == 0 else "split"
            if sg == "mu":   # (e2) a piece's mu split by sign once, shared by the pieces it is the value or an end of
                todo += [(c, more + [D.RAtom(D.ge({P.mu: d}), ("sg", P.mu), d)]) for d in (-1, 1)]
                rule = "sign"
                continue
            todo += [(c, more + D.prange(P, P.a0, D.MAX_ROWS if bounded else None, g)) for g in ((-1, 1) if sg == "split" else (sg,))]
            rule = ("prange", P) if sg in ("split", None) or D.frange_of(("sg", P.mu), more) or (P.lo if sg == 1 else P.hi) is not None and sg * (P.lo if sg == 1 else P.hi) >= 0 else \
                ("prange", P, self.prove(c, atoms + more + [D.gt({P.mu: -sg})], budget)) if tree else "prange (a piece's sign by its end's, 3.5)"
            continue
        k = next((k for k, b in nests if D.frange_of(k, more) is None), None)
        if k:   # (e) a mean of a mean's rows and more: which side of the others' class ends the inner one is; a mean at
                # a point class's end or strictly inside
            todo += [(c, more + [D.RAtom(A, k, i) for A in B]) for i, B in enumerate(dict(nests)[k])]
            rule = ("model", "nest", k)
            continue
        X = c[None]
        und = [st for st in X.sums if st not in X.pres]
        try:
            sm = self.same_means(c, Ms, atoms + more, budget)
            self.leaf_at = tree and (tree, node, atoms + more, len(sm))
            x = self.one_solve(c, atoms + more + sm, budget, bounded)
        except D.Unreadable as e:   # a read value with no readable point at the solver's choices: split on its band
            z, lo = e.args[1], e.args[3]   # (call 2: in it as a whole step, below it, above it; SPEC-EXACT 3.1)
            if z[1] == "pix" and not any(isinstance(A, D.RAtom) and A.z[1] == "pix" for A in more):   # (f) two floats in one window: exact
                P = D.fwin(self.case_atoms(c) + self.part_atoms(c) + atoms + more, budget)
                if P is not None:
                    todo += [(c, more + P)] if P else []
                    rule = ("pin", P) if P else ("model", "fwin", None)   # (L5) a pair checked (cert.pin_split); none: the model's (fwin)
                    continue
            if z[1] == "pix":   # (f) a float: its range of binades halved down to one binade (frange)
                todo += [(c, [A for A in more if not (isinstance(A, D.RAtom) and A.z == z)] + fr) for fr in D.frange_split(z, D.frange_of(z, more), lo)]
                rule = ("model", "binade", (z, lo))
                continue
            if z[1] == "raw":   # (shape 3) a byte range's number: its spellings split at the point (spell_cases)
                todo += [(c, more + A) for A in self.spell_cases(z, lo)]
                rule = ("model", "spell", (z, lo))
                continue
            if D.zkind(z) != "sum":   # a read value (A04: a region's sum of RepetitionTimes is a sum, a multiple of R's finest step)
                todo += [(c, more + A) for A in self.band_cases(z, lo)]
                rule = ("model", "band", (z, lo))
                continue
            if z[1] != "rs" and self.refine(z[2:5], e.args[2]):   # a sum no readable value reached: its column is cut into parts (item 2)
                todo.append((c, more))
                rule = ("model", "refine", None)
                continue
            if lo is not None:   # else a sum, a multiple of R's finest step, is at or below the one under lo, or above
                todo += [(c, more + A) for A in self.step_cases(z, lo)]
                rule = ("model", "step", (z, lo))
                continue
            if not und:
                raise
            x, bad = None, und[0]   # else presence is split (item 8)
        else:
            if x is None:
                continue
            hcut = self.half_cut(c, Ms, atoms, x, budget, hmemo) if Ms and X.ordv else None
            if hcut:   # (item 1, 28 Oct) a half cut the solution breaks (SPEC-EXACT 3.5a): added, the case solved again
                todo.append((c, more + [hcut]))
                if tree:   # (cert.py) its condition shown, for the model's obligation
                    self.prove(c, self.half_need(c, atoms, hcut) or [], budget, raw=True)
                rule = ("model", "half", hcut)
                continue
            P = next((P for P in Ps if D.value(P.S, x) != x.get(P.mu, 0) * D.value(P.N, x)), None)
            bad = next((st for st in und if not self.inside_sum(st, x)), None)
            if P and bad is not None and any(v != D.ONE and v[2:4] == bad for v in P.S):
                P = None   # (e2) a type of P's rows breaks its presence (no rows, a sum not 0): presence is split first
            cg = next((g for v, g in cps if D.frange_of(g[0][0], more) is None and not D.cap_ok(v, g, x, budget)), None) if P else None
            if cg:   # (pm) the shared types' mean cuts the solution off: its nests' cases, each solved
                todo += [(c, more + [D.RAtom(a, k, i) for (k, _), (i, A) in zip(cg, ch) for a in A]) for ch in D.itertools.product(*[list(enumerate(B)) for _, B in cg])]
                rule = ("model", "cap", cg[0][0])
                continue
            if P:   # (e) S != mu·n at the solution's n: N's range split at n, the point (exact) solved first
                (a, b, sg), n, keep = D.frange_of(P.key, more), D.value(P.N, x), [A for A in more if not (isinstance(A, D.RAtom) and A.z == P.key)]
                todo += [(c, keep + D.prange(P, *r)) for r in [(n + 1, b, sg), (a, n - 1, sg), (n, n, 0)] if r[1] is None or r[0] <= r[1]]
                rule = ("prange", P)
                continue
            key = self.unrealized(x, X) if bad is None else None
            if key and self.refine(key, x):
                todo.append((c, more))
                rule = ("model", "refine", None)
                continue
            gap = self.thin(x, X) if bad is None else None
            if gap:   # rows in a piece with no readable number between its ends (call 3): split as call 2 does
                todo += [(c, more + A) for A in self.gap_cases(*gap)]
                rule = ("model", "gap", gap)
                continue
            if bad is None:
                return x
        todo += [(d, more) for d in self.presence(c, bad)]
        rule = ("model", "presence", bad)
    if tree and rule:
        tree.split(last[3], rule, last[1], [])   # the last node's split made no child (fwin: no pair in the window)
    return None


def half_cut(self, case, Ms, atoms, x, budget, memo):
    """(item 1, 28 Oct 2026; SPEC-EXACT 3.5a) For a mean M (no named rows) and an order statistic u of M's column in
    this case: a = M's rows not known to be at or below u (types of a higher region; in u's region, the pieces above
    u, and the types without pieces). Rows at or below u are <= u and the others <= h, M's classes' upper end, so
    S <= (N - a) u + a h. When the case's counts give 2a <= N on every solution (the counts' atoms with 2a >= N + 1
    have no rational point: lp's certificate), mu <= (u + h)/2: for u <= h, S <= N u + (N/2)(h - u); for u > h no
    row is above u and mu <= h < (u + h)/2. Mirrored with b, the rows not known to be at or above u, and l:
    mu >= (u + l)/2. When the counts give a = 0, mu <= u (no row of M above u; mirrored, b = 0: mu >= u). True on
    every solution of the case's system, so a relaxation; the cuts exclude no input. Lazy: the first cut the solution x
    breaks whose count condition holds (implied), or None; only a broken cut's condition is tested, once per case (memo:
    the condition reads the case's count atoms only, the same on every solution of the case; each test charged)."""
    for cut, cond in self.half_cands(case, Ms):
        if D.value(cut[0], x) >= 0:
            continue
        key = (id(case), tuple(sorted(cond.items(), key=repr)))
        if key not in memo:
            if (id(case), None) not in memo:
                memo[(id(case), None)] = self.count_ints(case, atoms)
            memo[key] = self.implied(memo[(id(case), None)], cond, budget)
        if memo[key]:
            return cut
    return None


def count_ints(self, case, atoms):
    """The case's count atoms (counts, pieces, means' N only) as integer atoms G + k >= 0."""
    ints = []
    for F, strict in [A for A in self.case_atoms(case) + atoms if all(v == D.ONE or v[0] in ("n", "p", "m") for v in A[0])]:
        m = D.lcm(*[D.Fraction(c).denominator for c in F.values()])
        G = {v: int(c * m) for v, c in F.items() if v != D.ONE}
        if G:
            ints.append((G, int(F.get(D.ONE, 0) * m) - strict))
    return ints


def implied(self, ints, F, budget):
    """Whether F >= 0 has no natural point with the integer atoms ints (G + k >= 0): tidy, or lp's checked Farkas
    certificate over the rationals (so none over the naturals); charged as a system, as side work (side; SPEC-EXACT 8)."""
    sys_ = tidy(ints + [({v: int(c) for v, c in F.items() if v != D.ONE}, int(F.get(D.ONE, 0)))])
    D.side(budget, len(ints) + 1)
    if sys_ is None:
        return True
    if D.spent_all(budget) + len(sys_) * (len(sys_) + 1) > D.W.MAX_WITNESS_STEPS:
        raise D.Big(f"deciding it needs more than {D.W.MAX_WITNESS_STEPS} counted steps (SPEC-EXACT 8)")
    D.side(budget, len(sys_) * (len(sys_) + 1))
    r = lp(sys_) if sys_ else None
    return bool(r and r[0] == "none")


def one_solve(self, case, atoms, budget, bounded=True):
    """A solution {variable: value} of the case's atoms and these, with at most MAX_ROWS rows per
    slot when bounded, or None. Named cell values are eliminated exactly (SPEC-EXACT 4.1); then
    variables with equal columns are merged [merge_columns] and the integer step decides. (f) With pixdims, a system
    solved before (find()'s rounds re-solve each option's float ranges) gives its answer again for one step."""
    if not self.pix:
        return self.one_solve1(case, atoms, budget, bounded)
    key = (id(case), bounded, tuple((tuple(sorted(F.items(), key=lambda vc: repr(vc[0]))), st) for F, st in atoms))
    if key in self.memo and self.memo[key][0] is case:
        budget[0] += 1
        if isinstance(self.memo[key][1], D.Unreadable):
            raise self.memo[key][1]
        if self.memo[key][1] is None and self.leaf_at and self.memo[key][2] is not None:   # (cert.py) its checked system
            try:
                self.leaf_at[0].leaf(self.leaf_at[1], self.memo[key][2], self.leaf_at[2], self.leaf_at[3])
            except D.C.Bad:
                pass   # an unchecked "none" leaves the node open: find's "none" is X001
        return self.memo[key][1] and dict(self.memo[key][1])
    try:
        self.checked = None
        r = self.one_solve1(case, atoms, budget, bounded)
    except D.Unreadable as e:
        self.memo[key] = (case, e, None)
        raise
    self.memo[key] = (case, r and dict(r), self.checked)
    return r


def one_solve1(self, case, atoms, budget, bounded):
    held, log = [0], None   # the system's memory (fm's atoms, the integer atoms and tidy's keys of them; a certificate's
    try:                    # steps), given back when it is solved
        atoms = self.case_atoms(case) + self.part_atoms(case) + atoms
        if self.cert and not bounded:   # (C4) a refusal's check: an unbounded system's "no" is certified (cert.py)
            log = D.Log(len(atoms))
        return self.one_solve2(atoms, case, budget, bounded, held, log)
    finally:
        D.MEM[0] -= held[0] + (log.held[0] if log else 0)


def one_solve2(self, atoms, case, budget, bounded, held, log):
    if bounded:
        atoms += [D.ge(D.lin((-1, self.size(s, case, self.types[s])), (1, D.const(D.MAX_ROWS)))) for s in self.tabs]
    sys0 = atoms
    atoms, subs = presolve(atoms, log)
    zs = sorted({v for F, _ in atoms for v in F if v != D.ONE and v[0] == "z"}, key=repr)
    rest, stack = fm(atoms, zs, D.W.MAX_WITNESS_STEPS - budget[0], held, log)
    budget[0] += sum(len(A) for _, A in stack) + len(rest)
    ints, mem, ids = [], held[0] * D.STEP_BYTES, []
    for i, (F, strict) in enumerate(rest):
        m = D.lcm(*[D.Fraction(c).denominator for c in F.values()])
        mem += 2 * D.form_bytes(len(F), D.bits(F.values()) + m.bit_length())   # G, and tidy's key of it
        D.hold(held, mem)
        G = {v: int(c * m) for v, c in F.items() if v != D.ONE}
        k = int(F.get(D.ONE, 0) * m) - strict
        if not G:
            if k < 0:
                return self.no(sys0, log, budget, held, "ground", log and log.r(log.ids[i]))
            continue
        ints.append((G, k))
        ids.append(log and log.r(log.ids[i]))
    if log:
        log.ids = ids
    ints = tidy(ints, log)
    if ints is None:
        return self.no(sys0, log, budget, held, "tidy")
    if self.pix and empty_box(ints, budget, log=log):   # (f) pixdim models only (others charged as before)
        return self.no(sys0, log, budget, held, "box")
    if budget[0] + len(ints) * (len(ints) + 1) > D.W.MAX_WITNESS_STEPS:   # (e2) lp's charge, before its tableau is built
        raise D.Big(f"deciding it needs more than {D.W.MAX_WITNESS_STEPS} counted steps (SPEC-EXACT 8)")
    r = lp(ints) if ints else None
    budget[0] += len(ints) * (len(ints) + 1)
    if r and r[0] == "none":
        vs = {v for G, _ in ints for v in G}
        s = {v: sum(u * G.get(v, 0) for u, (G, _) in zip(r[1], ints)) for v in vs}   # <= 0: + (-s_v) x_v >= 0
        return self.no(sys0, log, budget, held, "lp", log and log.c(list(zip(r[1], log.ids)) + [(-s[v], log.nat(v)) for v in sorted(vs, key=repr) if s[v]]))
    if r and all(sum(c * r[1].get(v, 0) for v, c in G.items()) + k >= 0 for G, k in ints):
        return self.finish(r[1], subs, stack)
    vs = sorted({v for G, _ in ints for v in G}, key=repr)
    rep = {}
    for v in vs:
        rep.setdefault(tuple(G.get(v, 0) for G, _ in ints), len(rep))
    ix = {v: rep[tuple(G.get(v, 0) for G, _ in ints)] for v in vs}
    first = {}
    for v in vs:
        first.setdefault(ix[v], v)
    sys_ = [("ge", D.I.form({j: G[v] for j, v in first.items() if v in G}, k)) for G, k in ints]
    w = max(1, -(-max((abs(c).bit_length() for G, k in ints for c in [k, *G.values()]), default=0) // 64))   # a call's cost in 64-bit words (call 2)
    try:
        S = MSearch(max(1, (D.W.MAX_WITNESS_STEPS - budget[0]) // w), held)
        x, calls = S.decide(sys_), S.calls
    except D.I.TooBig:
        raise D.Big(f"deciding it needs more than {D.W.MAX_WITNESS_STEPS} counted steps of the integer step (SPEC-EXACT 8)") from None
    budget[0] += calls * w + len(ints) + len(subs)
    if x is None:
        if log:
            log.add(("int", log.ids), 192 + 8 * len(log.ids))
        return self.no(sys0, log, budget, held, "int")
    return self.finish({first[j]: n for j, n in x.items() if n}, subs, stack)


def finish(self, x, subs, stack):
    """The full solution: the replaced counts from the rest, then the eliminated values (4.1)."""
    x = {v: n for v, n in x.items() if n}
    for v, E in reversed(subs):
        x[v] = int(D.value(E, x))
    return back(stack, x, self.pay)


def find_options(self, options, budget, what):
    """The first option (case, atoms) with a solution within MAX_ROWS rows per slot, as (its index,
    the solution); None when no option has any solution; Big when only larger inputs exist (D3).
    The unbounded system is solved first: its solution is used when it is small enough."""
    free, todo, cap, big, spent, trees = False, list(range(len(options))), 1 << 12, None, {}, {}
    while todo:   # (g) every open option within a step cap, the cap x4 each round: a costly option no longer
        left = []   # starves a cheap one; None for all still needs each solved in full; Big only when none answers
        for i in todo:
            case, A = options[i]
            budget[0] -= spent.get(i, 0)   # (e2) a round redoes the option's earlier rounds: their steps count once (the largest)
            start = max(budget[0], D.W.MAX_WITNESS_STEPS - cap)
            capped, b, base = start > budget[0], [start, start - budget[0]], budget[0]   # [the round's steps, side work's headroom] (side)
            try:
                x = self.solve(case, A, b, bounded=False)
                trees[i] = self.tree   # (cert.py) its tree when it has no solution
                n = 0 if x is None else max(self.rows_of(case, x).values(), default=0)
                for R in (2, 64) if n > 64 else ():   # #4: fewest rows first (a vertex at a large count
                    try:                              # can cost its check more than the step bound)
                        y = self.solve(case, A + [D.ge(D.lin((-1, self.size(s, case, self.types[s])), (1, D.const(R)))) for s in self.tabs], b)
                    except (D.Big, D.Unreadable):
                        y = None
                    if y is not None:
                        x, n = y, R
                        break
                vs = [v for v in x or () if v[0] == "n" and v[2:3] in (("vol",), ("ev",), ("tt",))]
                for R in (2, 64, D.MAX_VOL) if any(x[v] > 2 for v in vs) else ():   # (2c) the smallest BOLD image, as #4; item 3: events file
                    try:
                        y = self.solve(case, A + [D.ge(D.lin((-1, {v: 1}), (1, D.const(R if v[2] == "vol" else min(R, D.MAX_ROWS))))) for v in vs], b, False)
                    except (D.Big, D.Unreadable):
                        y = None
                    if y is not None:
                        x = y
                        break
                for R in (2, 64, D.MAX_ROWS) if x and self.rs else ():   # (R1) the fewest recordings, each within a certificate's file
                    try:
                        y = self.solve(case, A + self.rs_small(R), b, False)
                    except (D.Big, D.Unreadable):
                        y = None
                    if y is not None:
                        x = y
                        break
                if n > D.MAX_ROWS and not self.big_ok:   # (G02b) in Decide.limit_shown's replay the large point itself
                    free, x = True, self.solve(case, A, b)
            except D.Big as e:
                x = None
                if capped:
                    left.append(i)   # stopped by the cap, or by a bound the next rounds meet again
                else:
                    big = big or e
            spent[i] = max(D.spent_all(b) - base, spent.get(i, 0))   # its solves and its side work
            budget[0] += spent[i]
            if x is not None:
                return i, x
        if left and cap == 1 << 12:   # some option needs more: first each with at most two rows in all, fewest first
            for i, tot in ((i, tot) for tot in range(3) for i in left):   # (e2) one system per row total, not per count vector
                case, A = options[i]
                ns = sorted({v for F, _ in A + self.case_atoms(case) for v in F if v != D.ONE and v[0] == "n" and v[1] in self.tabs}, key=repr)
                start = max(budget[0], D.W.MAX_WITNESS_STEPS - cap)   # (e2) under the first round's cap
                b, base = [start + len(ns), start - budget[0]], budget[0]
                try:   # a solution with tot rows in all is one of the option's (more atoms)
                    x = self.solve(case, A + [D.ge({**{v: 1 for v in ns}, D.ONE: -tot}), D.ge({**{v: -1 for v in ns}, D.ONE: tot})], b, False)
                except (D.Big, D.Unreadable):
                    x = None
                budget[0] += D.spent_all(b) - base
                if x is not None:
                    return i, x
        todo, cap = left, cap * 4
    if big:
        raise big
    if free:
        raise D.Past(f"{what} needs a readable input with more than {D.MAX_ROWS} rows in one table (SPEC-EXACT 6; D3)")
    if self.cert:
        self.trees = trees   # (cert.py) checked by Decide.certify (cert.options_closed), not here
    return None   # (F03) kept for the question's check by Model.find (trusted), not here


SHORT = [D.Fraction(x) for x in (0, 1, -1, 2, -2, 3)] + [D.Fraction(1, 2)]   # (3.7b) values tried first in an interval class


def joint_rows(d, top, whole):
    """(3.7b) The finite-domain witness search for a part of a variance's selection (or a file slot) beside another
    variance result, where 3.7a stops: rows of the types the variances' answering cases select, each with readable
    values of its classes (Decide.dvals: a point, or an interval's two readable ends and a short number inside), as
    multisets by size, at most MAX_CASES (charged one per row). The first on which the real code gives top and whole
    different outcomes (each an answer or a V refusal, SPEC 4.4 10), or None. Untrusted: its rows are written as bytes
    and confirmed again by Decide.differ_on (X001 if they do not differ); None is never a refusal (R013)."""
    import itertools
    cols, types = {}, {}
    for e in (top, whole):
        for v in D.W.subexprs(e):
            if getattr(v, "fn", None) in D.VARF:
                for s, k, _, f, S, _ in d.var_cands(v, True):
                    d.budget[0] += len(f) + len(S)
                    cols.setdefault(s, set()).add(k)
                    types.setdefault(s, set()).update(f, S)
    items = []
    for s in sorted(types, key=repr):
        ks = tuple(sorted(cols[s]))
        for t in sorted(types[s], key=repr):
            vals = []
            for k in ks:
                c = d.m.cls(s, t, k)
                if c[0] == "iv":   # short numbers inside first (a witness rarely needs a class's 1,000-digit ends), then dvals'
                    lo, hi = c[1]
                    vals.append([x for x in SHORT if (lo is None or x > lo) and (hi is None or x < hi)] + [x for x in d.dvals(s, t, k) if x not in SHORT])
                else:
                    vals.append(d.dvals(s, t, k) if len(c) > 2 and c[2] is not None and c[0] not in ("lit", "oth") else [None])
            for xs in itertools.product(*vals):
                d.budget[0] += 1
                items.append((sum(len(str(x)) for x in xs), len(items), s, (ks, t, xs)))
    items = [(s, r) for *_, s, r in sorted(items)]   # the shortest rows first
    tried = 0
    for n in range(1, D.MAX_ROWS + 1):
        for ix in itertools.combinations_with_replacement(range(len(items)), n):
            tried += 1
            d.budget[0] += n
            if tried > D.MAX_CASES or d.budget[0] > D.W.MAX_WITNESS_STEPS:
                return None
            got = {}
            for i in ix:
                got.setdefault(items[i][0], []).append(items[i][1])
            a, b = d.d_out(top, got, True), d.d_out(whole, got, True)
            if a is not None and b is not None and a != b and all(t[0] != "V" or str(t[1] or "").startswith("V") for t in (a, b)):
                return got
        if not items:
            return None
    return None


def no(self, sys0, log, budget, held, how, last=None):
    """None (no point). In a refusal's check (C4: log given) its certificate is checked by cert.py first (BB's call
    28 Oct 18:05): one that does not check is X001; checking holds its lines (copies of the atoms the system held)
    and pays its steps in its own account (pay); past either bound, Unchecked (the refusal is R013)."""
    if log is None:
        return None
    if last is not None:
        log.end(last)
    try:
        D.hold(held, 2 * held[0] * D.STEP_BYTES + 128 * len(log.steps))
        D.pay(len(log.steps))
        steps = log.needed()
        D.C.check(sys0, steps, D.pay, keep=bool(self.pix))
        self.checked = sys0
        if self.leaf_at:
            self.leaf_at[0].leaf(self.leaf_at[1], sys0, self.leaf_at[2], self.leaf_at[3])
    except D.C.Bad as e:
        from .kernel import fail
        fail("X001", "bug", f"a system's certificate of no point does not check ({e}): nothing formed (a checker fault, please report; SPEC-EXACT 6)")
    except D.Big as b:   # the checking bound, or memory to hold its lines: not checked, so the refusal is R013 (certify)
        raise D.Unchecked(str(b)) from None
    D.CERTS[how] = D.CERTS.get(how, 0) + 1
    return None


def prove(self, case, atoms, budget, raw=False):
    """(cert.py) In a refusal's check: the system (the case's model atoms and these; raw: these only) shown to have
    no point by a checked certificate, kept by the option's tree for a split's obligation. A point, or a "none" not
    shown, means the split is not shown: cert.Bad (X001)."""
    la, self.leaf_at, self.checked, held, log = self.leaf_at, None, None, [0], None
    try:
        sys_ = list(atoms) if raw else self.base(case) + atoms
        log = Log(len(sys_))
        x = self.one_solve2(sys_, case, budget, False, held, log)
    except D.Unreadable:
        x = True
    finally:
        self.leaf_at = la
        D.MEM[0] -= held[0] + (log.held[0] if log else 0)
    if x is not None or self.checked is not sys_:
        raise D.C.Bad("a split's obligation has a point, or its none is not shown")
    self.tree.proved(sys_)
    return sys_


def rs_small(self, R):
    """(R1) at most R recordings of each kind per region, a sum or one value at most R, and within a certificate's
    (MAX_VOL volumes, MAX_ROWS events in all)."""
    out = []
    for (s, t), regs in self.rsreg.items():
        q = self.rsq.get(s, ("tr",))[0]
        if s in self.rsm:   # (3.9a)
            for r in range(len(regs)):
                out += [D.ge(D.lin((-1, self.rs_n(s, t, k, r)), (1, D.const(R)))) for k in self.rs_jk(s)]
                out += [D.ge(D.lin((-1, {self.rs_var(s, t, "y", r, i if q == "volumes" else (i, c)): 1}), (1, D.const(min(R, D.MAX_VOL if q == "volumes" else D.MAX_ROWS))))) for i, (q, _) in enumerate(self.rsm[s]) for c in ((None,) if q == "volumes" else self.rs_evc(s))]
            continue
        for r in range(len(regs)):
            out += [D.ge(D.lin((-1, self.rs_n(s, t, k, r)), (1, D.const(R)))) for k in ("ok",) + D.RSBAD[q]]
            if q != "tr" and s in self.rsq:
                out += [D.ge(D.lin((-1, {self.rs_var(s, t, w, r): 1}), (1, D.const(min(R, D.MAX_VOL if q == "volumes" else D.MAX_ROWS))))) for w in "ym"]
            if any(x.fn == "min" for x in self.rsagg if x.args[0].args[0].args[0].id == s and x.args[0].args[1].v.decode("ascii", "replace") == t) and (s, t) not in self.rs7:
                out += [D.ge(D.lin((-1, self.rs_n(s, t, "ok", r)), (1, D.const(1))))]   # a min's recordings all at its value: one (3.9e: of its task)
    return out


def refine(self, key, x):
    """Cuts in two the widest part of more than one band of a summed column that holds rows at x (at first: its
    class's bands in two halves, or its one band); False when there is none."""
    B, ps = self.cbands(key), self.parts.get(key)
    if ps is None:
        h = (len(B) - 1) // 2
        self.parts[key] = [(0, 0)] if len(B) == 1 else [(0, h), (h + 1, len(B) - 1)]
        return bool(B)
    held = [(i, j) for p, (i, j) in enumerate(ps) if i < j and x.get(("q",) + key + (p,), 0)]
    if not held:
        return False
    i, j = max(held, key=lambda r: r[1] - r[0])
    at, h = ps.index((i, j)), (i + j) // 2
    self.parts[key] = ps[:at] + [(i, h), (h + 1, j)] + ps[at + 1:]
    return True


def thin(self, x, X):
    """Call 3: the first piece of an ordered column strictly between two of its ends (type_rows' ws) that holds rows
    at x and no readable number: (its count, its lower end, its upper end), an end (variable or None, value)."""
    for (s, k, r), m in X.nw.items():
        for t in X.sel.get((s, k), ()):
            c = self.cls(s, t, k)
            if self.rindex(s, k, c) != r or not x.get(("n", s, t), 0):
                continue
            ws = [(None, c[1][0])] + [(("z", "w", s, k, r, i), x.get(("z", "w", s, k, r, i), D.inside(*c[1], self.pay))) for i in range(m)] + [(None, c[1][1])]
            for i in range(0, 2 * m + 1, 2):
                if x.get(("p", s, t, k, r, i), 0) and D.inside(ws[i // 2][1], ws[i // 2 + 1][1], self.pay) is None:
                    return ("p", s, t, k, r, i), ws[i // 2], ws[i // 2 + 1]
    return None


def piece_atoms(self, case):
    """(e2) PAtoms of pieces(): a piece of rows at w_j sums to w_j·P; one between two ends to its mean times P."""
    out = []   # the pieces at a w first, so that its sign is split before the pieces it is an end of (psign)
    for (s, t, k, r, m), _, _, _ in self.pieces(case):
        lo, hi = self.regs[(s, k)][r][1:]
        w = lambda j: ("z", "w", s, k, r, j) if 0 <= j < m else None   # noqa: E731
        for i in list(range(1, 2 * m + 1, 2)) + list(range(0, 2 * m + 1, 2)):
            mu = w(i // 2) if i % 2 else ("z", "pv", s, t, k, r, i // 2)
            P = D.PAtom(mu, {("z", "ps", s, t, k, r, i): 1}, {("p", s, t, k, r, i): 1}, lo, hi, a0=0, key=("pk", s, t, k, r, i))
            P.lw, P.hw = (None, None) if i % 2 else (w(i // 2 - 1), w(i // 2))
            out.append(P)
    return sorted(out, key=lambda P: not P.mu[1] == "w")


def psign(self, P, more):
    """(e2) A piece's mu: of sign 1 or -1 (its own sign split, or an end's: an end at or above 0 below it, at or
    below 0 above it), None between two finite bounds, else 'mu' (split its sign)."""
    d = D.frange_of(("sg", P.mu), more)
    lw, hw = (D.frange_of(("sg", w), more) if w else None for w in (P.lw, P.hw))
    if d or (P.lo is not None and P.lo >= 0) or lw == 1:
        return d or 1
    if (P.hi is not None and P.hi <= 0) or hw == -1:
        return -1
    return None if P.lo is not None and P.hi is not None else "mu"


def unrealized(self, x, X):
    """The first summed column at x whose sum no readable rows reach, or None."""
    for s, t in X.sums:
        n = x.get(("n", s, t), 0)
        for k in self.cols[s]:
            if n and self.agg.get((s, k)) in ("sum", "both") and self.cls(s, t, k)[0] == "iv" and self.inside_sum((s, t), x) and self.realize(s, t, k, x, n) is None:
                return (s, t, k)
    return None


def rows_of(self, case, x):
    return {s: len(case[s].types) + sum(n for v, n in x.items() if v[0] == "n" and v[1] == s) for s in self.tabs}


def fpick(lo, hi, pay):
    """A float strictly between lo and hi (None: unbounded), or None: 0 if it fits, else the one of fewest binary digits
    (a power of two above lo when hi is None), mirrored below 0; steps paid."""
    if (lo is None or lo < 0) and (hi is None or hi > 0):
        return D.Fraction(0)
    if lo is None or lo < 0:
        r = fpick(-hi, None if lo is None else -lo, pay)
        return None if r is None else -r
    if hi is None:
        c = D.Fraction(2) ** (lo.numerator.bit_length() - lo.denominator.bit_length())
        c = c if c > lo else 2 * c
        return c if is_float(c) else fnext(lo)
    k = (hi - lo).denominator.bit_length() - (hi - lo).numerator.bit_length() - 1
    while D.Fraction(2) ** -k >= fstep(lo):
        pay[0] += 1
        c = (D.floor(lo * D.Fraction(2) ** k) + 1) / D.Fraction(2) ** k
        if c < hi:
            return c if is_float(c) else fnext(lo) if fnext(lo) is not None and fnext(lo) < hi else None
        k += 1
    c = fnext(lo)
    return c if c is not None and c < hi else None


def cap_ok(v, g, x, pay):
    """Whether some value of the free mean v meets one of the cases of each nest in g at x (the rest of x fixed): the
    cases are linear in v, so the values meeting them are intervals with ends among the atoms' roots; the roots, the
    points between them and one beyond each side are tried (exact)."""
    ats = [a for _, B in g for A in B for a in A]
    rs = sorted({-D.value({u: c for u, c in a[0].items() if u != v}, x) / a[0][v] for a in ats if a[0].get(v)})
    ps = [D.Fraction(0)] if not rs else [rs[0] - 1, rs[-1] + 1] + rs + [(a + b) / 2 for a, b in zip(rs, rs[1:])]
    pay[0] += len(ats) * (len(ps) + 1)
    return any(all(any(all(D.holds(a, {**x, v: p}) for a in A) for A in B) for _, B in g) for p in ps)


def fup(a):
    """The least float above a >= 0, or None."""
    c = (D.floor(a / fstep(a)) + 1) * fstep(a)
    return c if c <= D.FMAX else None


def fdown(a):
    """The greatest float below a > 0 (at a binade's start the spacing below is half)."""
    if a > D.FMAX:
        return D.FMAX
    g = fstep(a)
    c = (-D.floor(-a / g) - 1) * g
    return a - fstep(c) if c and fstep(c) < g else c


def fstep(a):
    """The spacing of the floats at a >= 0 (the subnormals' below 2^-1022)."""
    e = a.numerator.bit_length() - a.denominator.bit_length() if a else -1022
    e -= bool(a) and D.Fraction(2) ** e > a   # floor(log2 a)
    return D.Fraction(2) ** (max(e, -1022) - 52)


def fnext(q):
    return fup(q) if q >= 0 else -fdown(-q)


def is_float(q):
    return abs(q) <= D.FMAX and (q / fstep(abs(q))).denominator == 1


def form_bytes(n, B):
    """Accounted bytes of a form (a dict) of n entries whose numbers have at most B bits, with its atom's tuple: 256 for
    the dict and tuple, 64 a slot and the number (CPython 3.13: 224 bytes for one entry, 632 for 12)."""
    return 256 + n * (64 + D.num(B))


def spent_all(budget):
    return budget[0] - (budget[1] if len(budget) > 1 else 0)   # the steps really spent (side)


class Log:
    """A leaf certificate being written (cert.py): its steps, and the line of each atom of the system now (ids)."""

    def __init__(self, n):
        self.steps, self.ids, self.nats, self.held, self.b = [("p", i) for i in range(n)], list(range(n)), {}, [0], 192 * n
        D.hold(self.held, self.b)

    def add(self, step, nb=192):
        """A step, held before it is kept (SPEC-EXACT 8; given back with the system's memory, one_solve1)."""
        self.b += nb
        D.hold(self.held, self.b)
        self.steps.append(step)
        return len(self.steps) - 1

    def c(self, terms):
        t = [(u, j) for u, j in terms if u]
        return self.add(("c", t), 192 + sum(200 + D.num(D.bits([D.Fraction(u)])) for u, _ in t))

    def r(self, j):
        return self.add(("r", j))

    def nat(self, v):
        if v not in self.nats:
            self.nats[v] = self.add(("nat", v))
        return self.nats[v]

    def end(self, j):
        if j != len(self.steps) - 1:
            self.c([(1, j)])

    def needed(self):
        """The steps the last one rests on, renumbered (the checker need not redo the rest)."""
        st, need = self.steps, {len(self.steps) - 1}
        for i in range(len(st) - 1, -1, -1):
            if i in need:
                need |= {j for _, j in st[i][1]} if st[i][0] == "c" else set(st[i][1]) if st[i][0] == "int" else {st[i][1]} if st[i][0] in ("r", "d") else set()
        new = {j: n for n, j in enumerate(sorted(need))}
        f = lambda s: (s[0], [(u, new[j]) for u, j in s[1]]) if s[0] == "c" else (s[0], [new[j] for j in s[1]]) if s[0] == "int" else (s[0], new[s[1]]) if s[0] in ("r", "d") else s
        return [f(st[j]) for j in sorted(need)]


def d_hit(self, dn, K):
    """Rows ({slot: [(column, type, value)]}) on which the difference dn = V1 − V2 lies in a piece of K, or None
    when no input's does (item 5b). V1 and V2 lie in [0, sup1] and [0, sup2] whatever the coupling (3.7), so a
    piece missing [−sup2, sup1] is met by no input. Two equal variances (one slot, column, selection and ddof)
    differ by 0 only. Uncoupled (other slots, or selections sharing no row type that can hold rows), a piece meets
    [0, sup1] with V2 = 0 or [−sup2, 0] with V1 = 0, and the ends' shifts (V1 = sup1, V2 = sup2) are tried;
    var_hit finds the other there. Then (and first when coupled) the finite domain is searched: multisets of rows,
    each of a type and readable values of the classes' ends and a short number inside, by size, at most
    MAX_CASES (BB's calls 2 and 4, 27 Oct 14:00); R013 past it."""
    v1, v2 = dn.args
    c1, c2 = self.var_cands(v1, True), self.var_cands(v2, True)
    meets = lambda p, lo, hi: (p[2] is None or p[2] > lo or p[3] and p[2] == lo) and (p[0] is None or p[0] < hi or p[1] and p[0] == hi)
    sups = {}
    for (s, k, d, f, S, Z) in c1 + c2:
        (L, _), (U, _) = self.ends(s, k, f)
        sups[(s, k, d, tuple(f))] = (U - L) ** 2 / (2 if d else 4)
    big, joint = False, []
    for deep, (s1, k1, d1, f1, S1, Z1), (s2, k2, d2, f2, S2, Z2) in D.itertools.product((False, True), c1, c2):
        self.budget[0] += 1
        sup1, sup2 = sups[(s1, k1, d1, tuple(f1))], sups[(s2, k2, d2, tuple(f2))]
        if not any(meets(p, -sup2, sup1) for p in K):
            continue
        Zs = Z1 | Z2   # (3.13g) an input both candidates' cases admit has no row of these types: the selections are compared without them
        if (s1, k1, d1, set(S1) - Zs) == (s2, k2, d2, set(S2) - Zs) and v1.fn == v2.fn:
            if any(meets(p, 0, 0) for p in K):   # V1 = V2 on every input: the difference is 0
                (L, t), _ = self.ends(s1, k1, f1)
                return {s1: [(k1, t, L)] * (d1 + 1)}
            continue
        if (s1, k1, set(S1) - Zs, set(f1) - Zs) == (s2, k2, set(S2) - Zs, set(f2) - Zs) and d1 != d2:
            # one selection, sample − population variance: n·Vp/(n − 1) − Vp = Vp/(n − 1), in [0, D²/4] with both
            # ends reached at n = 2, where it is the population variance of the two rows: var_hit (two rows)
            Q = [q for q in (D.pclip(p) if d1 else D.pclip(D.pneg(p)) for p in K) if q is not None]
            try:
                rows = self.var_hit(s1, k1, 0, f1, Q, False) if Q else None
            except D.Big:
                big = True
                if not deep:
                    joint.append(((s1, k1, d1, f1, S1, Z1), (s2, k2, d2, f2, S2, Z2)))
                continue
            if rows is None:
                continue
            return {s1: [(k1, t, x) for t, x in rows]}
        if not deep:
            joint.append(((s1, k1, d1, f1, S1, Z1), (s2, k2, d2, f2, S2, Z2)))
        if s1 == s2 and (set(f1) & (set(S2) | Z2) or set(f2) & (set(S1) | Z1)):   # coupled: rows of types only one reads
            f1, f2 = [t for t in f1 if t not in S2 and t not in Z2], [t for t in f2 if t not in S1 and t not in Z1]   # (Z: types a case rules out)
            if not (f1 and f2):
                continue
            sup1, sup2 = ((self.ends(s, k, f)[1][0] - self.ends(s, k, f)[0][0]) ** 2 / (2 if d else 4) for s, k, d, f in ((s1, k1, d1, f1), (s2, k2, d2, f2)))
        (L1, t1), (U1, u1) = self.ends(s1, k1, f1)
        (L2, t2), (U2, u2) = self.ends(s2, k2, f2)
        zero1, zero2, top1, top2 = ((t1, L1), (t1, L1)), ((t2, L2), (t2, L2)), ((t1, L1), (u1, U1)), ((t2, L2), (u2, U2))
        for p in K:
            for fixed, first, q in ((zero2, True, D.pclip(p)), (zero1, False, D.pclip(D.pneg(p))), (top1, False, D.pclip(D.pneg(p, sup1))), (top2, True, D.pclip(p, sup2))):
                if q is None:
                    continue
                try:
                    rows = self.var_hit(s1, k1, d1, f1, [q], deep) if first else self.var_hit(s2, k2, d2, f2, [q], deep)
                except D.Big:
                    big = True
                    continue
                if rows:
                    r1, r2 = (rows, fixed) if first else (fixed, rows)
                    out = {}
                    out.setdefault(s1, []).extend((k1, t, x) for t, x in r1)
                    out.setdefault(s2, []).extend((k2, t, x) for t, x in r2)
                    return out
    if joint:
        got = self.d_domain(dn, K, joint)
        if got is not None:
            return got
        big = True
    if big:
        raise D.Big(f"deciding whether a difference of two variances lies in a piece needs more than {D.MAX_CASES} multisets of rows of its classes' readable ends (item 5b, SPEC-EXACT 3.7)")
    return None


def n_hit(self, terms, K):
    """Rows ({slot: [(columns, type, values)]}) of the one table on which the sum of signed variances lies in a piece
    of K, or None when no input's does: each variance lies in [0, sup] (3.7), so a piece missing [-(sum of the
    negative terms' sups), sum of the positive terms'] is met by none. Else the finite domain of d_domain: rows of the
    types every variance reads as a decimal, readable values of their classes (ends and a short number inside), by
    multiset size, scaled as d_scale; Big past MAX_CASES multisets (a stopped search, R013)."""
    m, tried, co = self.m, 0, {}
    for g, v in terms:   # one variance (convention, table, column) twice: its signs add (V - V = 0 on every input)
        co[(v.fn, v.args[0].args[0].id, v.args[1].v)] = co.get((v.fn, v.args[0].args[0].id, v.args[1].v), 0) + g
    meets = lambda p, lo, hi: (p[2] is None or p[2] > lo or p[3] and p[2] == lo) and (p[0] is None or p[0] < hi or p[1] and p[0] == hi)
    inK = lambda y, p: (p[0] is None or y > p[0] or p[1] and y == p[0]) and (p[2] is None or y < p[2] or p[3] and y == p[2])
    cands = [self.var_cands(v, True) for _, v in terms]
    for cs in D.itertools.product(*cands):
        self.budget[0] += len(cs)
        sup = {}   # per column the population variance's sup; a·Vs + b·Vp = Vp·(a·n/(n - 1) + b), n >= 2, lies in
        for s, k, d, f, S, Z in cs:   # Vp's range times [min, max] of 0, a + b and 2a + b
            sup[k] = max(sup.get(k, 0), (self.ends(s, k, f)[1][0] - self.ends(s, k, f)[0][0]) ** 2 / 4)
        lo, hi = self.n_range(cs, co)
        if not any(meets(p, lo, hi) for p in K):
            continue
        s = cs[0][0]
        ts = sorted(set.intersection(*(set(f) for _, _, _, f, _, _ in cs)) - set().union(*(set(Z) for *_, Z in cs)), key=repr)
        ks = sorted({k for _, k, _, _, _, _ in cs})
        items = []
        for t in ts:
            for xs in D.itertools.product(*(self.dvals(s, t, k) for k in ks)):
                items.append((s, t, dict(zip(ks, xs))))
        for n in range(2, D.MAX_ROWS + 1):
            for ix in D.itertools.combinations_with_replacement(range(len(items)), n):
                tried += 1
                self.budget[0] += n
                if tried > D.MAX_CASES:
                    raise D.Big(f"deciding whether a sum of variances lies in a piece needs more than {D.MAX_CASES} multisets of rows of its classes' readable ends (SPEC-EXACT 3.7)")
                rs = [items[i] for i in ix]
                C = {k: sum(g * var_of([r[2][k] for r in rs], 1 if q[0].startswith("sample") else 0) for q, g in co.items() if g and q[2] == k) for k in ks}
                y = sum(C.values())
                if any(inK(y, p) for p in K):
                    return {s: [(tuple(ks), t, tuple(kv[k] for k in ks)) for _, t, kv in rs]}
                for cols, A in [(ks, y)] + [((k,), C[k]) for k in ks if len(ks) > 1]:   # (h) all columns scaled, or one alone
                    lam = self.d_scale(rs, A, y - A, K, cols)
                    if lam is not None:
                        return {s: [(tuple(ks), t, tuple(kv[k] * (lam if k in cols else 1) for k in ks)) for _, t, kv in rs]}
            if not items:
                break
        else:   # (L6) every size tried without meeting MAX_CASES: a stopped search, never a None
            raise D.Big(f"deciding whether a sum of variances lies in a piece needs inputs of more than {D.MAX_ROWS} rows (SPEC-EXACT 3.7)")
    return None


def d_domain(self, dn, K, pairs):
    """The finite-domain search of d_hit: rows, each a row type with readable values of its classes (ends, and a
    short number inside), as multisets by size; the first whose V1 − V2 lies in a piece of K, or None past
    MAX_CASES multisets (charged one per row)."""
    m, v1, v2, tried = self.m, dn.args[0], dn.args[1], 0
    inK = lambda y, p: (p[0] is None or y > p[0] or p[1] and y == p[0]) and (p[2] is None or y < p[2] or p[3] and y == p[2])
    vals = self.dvals
    for (s1, k1, d1, f1, S1, Z1), (s2, k2, d2, f2, S2, Z2) in pairs:
        items, seen = [], set()   # (slot, type, {column: value})
        for s, ts in ([(s1, set(f1) | set(f2))] if s1 == s2 else [(s1, set(f1)), (s2, set(f2))]):
            for t in sorted(ts, key=repr):
                if s1 == s2 and (t in S1 and t not in f1 or t in S2 and t not in f2 or t in Z1 | Z2):
                    continue   # a row of it would make a variance refuse (V005) or break the case
                ks = sorted({k for k, ok in ((k1, s == s1 and t in S1), (k2, s == s2 and t in S2)) if ok})
                for xs in D.itertools.product(*(vals(s, t, k) for k in ks)):
                    # item (h): two rows that both variances read alike are one item (V1 − V2 is the same)
                    sig = (s, s == s1 and t in S1, s == s2 and t in S2, tuple(zip(ks, xs)))
                    if sig not in seen:
                        seen.add(sig)
                        items.append((s, t, dict(zip(ks, xs))))
        n = 2
        while n <= D.MAX_ROWS:
            for ix in D.itertools.combinations_with_replacement(range(len(items)), n):
                tried += 1
                self.budget[0] += n
                if tried > D.MAX_CASES:
                    return None
                rs = [items[i] for i in ix]
                a = [r[2][k1] for r in rs if r[0] == s1 and r[1] in S1]
                b = [r[2][k2] for r in rs if r[0] == s2 and r[1] in S2]
                if len(a) <= d1 or len(b) <= d2:
                    continue
                V1, V2 = var_of(a, d1), var_of(b, d2)
                # (h) all values times λ: λ²(V1 − V2); two columns: one column's values times λ alone
                sc = [(None, None)] if any(inK(V1 - V2, p) for p in K) else [((k1, k2), self.d_scale(rs, V1 - V2, 0, K, (k1, k2)))]
                sc += [((k,), self.d_scale(rs, A, B, K, (k,))) for k, A, B in ((k1, V1, -V2), (k2, -V2, V1)) if k1 != k2 and sc[-1][1] is None]
                cols, lam = next(((c, l) for c, l in sc if c is None or l is not None), (None, None))
                if lam is not None or cols is None and any(inK(V1 - V2, p) for p in K):
                    out = {}
                    for s, t, kv in rs:
                        ks = tuple(sorted(kv))
                        out.setdefault(s, []).append((ks, t, tuple(kv[k] * (lam if lam and k in cols else 1) for k in ks)))
                    return out
            n += 1
    return None


def d_scale(self, rs, A, B, K, cols):
    """Item (h): each variance is homogeneous of degree 2 in its column's values, so the values of the columns cols
    times λ give λ²·A + B (all: A = V1 − V2, B = 0; one column of two: its variance's signed A, the other's B). A
    λ > 0 (t/X, X the largest |value| scaled, t a short readable number) with λ²·A + B in a piece of K and every
    scaled value readable and in its class, or None."""
    m = self.m
    if A == 0:
        return None
    for p in K:
        lo, hi = [None if v is None else (v - B) / A for v in ((p[0], p[2]) if A > 0 else (p[2], p[0]))]
        lo = D.Fraction(0) if lo is None or lo < 0 else lo
        if hi is not None and hi <= lo:
            continue
        self.budget[0] += len(rs) + 1
        X = max((abs(x) for _, _, kv in rs for k, x in kv.items() if k in cols), default=0)   # λ = t/X
        a = X * D.root(lo, 1) if lo > 0 else D.Fraction(0)
        t = D.inside(a, None if hi is None else X * D.root(hi, 0), self.budget)
        if t is None or t <= 0 or X == 0:
            continue
        lam = t / X
        ok = True
        for s, typ, kv in rs:
            for k, x in kv.items():
                c, z = m.cls(s, typ, k), x * lam
                ok = ok and (k not in cols or D.in_r(z) and (c[2] == z if c[0] != "iv" else (c[1][0] is None or z > c[1][0]) and (c[1][1] is None or z < c[1][1])))
        if not ok:
            continue
        z = lam * lam * A + B   # exact: each variance is homogeneous of degree 2
        if (p[0] is None or z > p[0] or p[1] and z == p[0]) and (p[2] is None or z < p[2] or p[3] and z == p[2]):
            return lam
    return None


def two_vals(self, s, k, d, free, K):
    """Item (h): rows of the classes' two readable ends L < U, j at U and n − j at L (2 <= n <= MAX_ROWS, and the
    table at most MAX_TEXT_FILE bytes, else it is no readable input), whose variance j(n − j)/(n(n − d))·(U − L)²
    lies in a piece of K: every n is tried, j solved exactly (isqrt, adjusted; j(n − j) grows up to n/2), the
    fewest rows first. None when none is (the multisets follow)."""
    (L, ta), (U, tb) = self.ends(s, k, free)
    D2, cap = (U - L) ** 2, self.two_cap(s, k, free)
    best = None   # (n, j)
    for p in K:   # in units of D²: j(n − j)/(n(n − d)) in (yl, yh), ends as p's
        yl, yh = p[0] / D2, None if p[2] is None else p[2] / D2
        a, b = yl.numerator, yl.denominator   # integers only in the loop
        A, Bh = (yh.numerator, yh.denominator) if yh is not None else (None, None)
        okl = lambda P, q: P * b > a * q or p[1] and P * b == a * q
        okh = lambda P, q: A is None or P * Bh < A * q or p[3] and P * Bh == A * q
        for n in range(2, min(cap, D.MAX_ROWS if best is None else best[0] - 1) + 1):
            self.budget[0] += 1
            q = n * (n - d)
            if 4 * a * q > n * n * b:
                continue
            j = max(1, (n - D.isqrt((n * n * b - 4 * a * q) // b + 1)) // 2 - 1)
            while j <= n // 2 and not okl(j * (n - j), q):
                j += 1
                self.budget[0] += 1
            if j <= n // 2 and okh(j * (n - j), q):
                best = (n, j)
                break
    return None if best is None else ((tb, U),) * best[1] + ((ta, L),) * (best[0] - best[1])


def dvals(self, s, t, k):
    """Readable values of the class of column k in type t: a point, or an interval's two readable ends and a short
    number inside (d_domain)."""
    c = self.m.cls(s, t, k)
    if c[0] != "iv":
        return [c[2]]
    return sorted({x for x in (D.nxt(c[1][0]), D.prv(c[1][1]), D.inside(*c[1], self.budget)) if x is not None})


def var_of(xs, d):
    """The variance of the numbers xs with ddof d (exact)."""
    mu = sum(xs) / len(xs)
    return sum((x - mu) ** 2 for x in xs) / (len(xs) - d)
