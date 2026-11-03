"""The integer step of the exact decision (SPEC-EXACT 4): does a list of atoms have a common solution
in the naturals?

A linear form is (coefficients, constant), the coefficients a tuple of (variable, nonzero int) sorted
by variable; variables are ints. An atom is ("ge", f): f >= 0, or ("dvd", m, f): m divides f.
Each function below is the definition of the same name in metatheory/Exact.lean, step by step and in
the same order; Exact.decide_correct proves the procedure exact whichever variable pick() chooses.
Exact.lean does not build a witness: the one built here is checked by holds() and, for statements, by
the real readers (SPEC-EXACT 6). Used by decide.py, the exact decision of part T (phase 3)."""
from math import gcd


class TooBig(Exception):
    """More than the allowed number of calls (SPEC-EXACT 8): the statement refuses R013."""


def form(coeffs, k):
    return tuple(sorted((v, c) for v, c in coeffs.items() if c != 0)), k


def coef(f, j):
    return dict(f[0]).get(j, 0)


def value(f, x):
    return sum(c * x.get(v, 0) for v, c in f[0]) + f[1]


def holds(a, x):
    v = value(a[-1], x)
    return v >= 0 if a[0] == "ge" else (v == 0 if a[1] == 0 else v % a[1] == 0)


def lin(*terms):
    """sum of n * f over (n, f) pairs"""
    d, k = {}, 0
    for n, f in terms:
        for v, c in f[0]:
            d[v] = d.get(v, 0) + n * c
        k += n * f[1]
    return form(d, k)


def rest(f, j):
    return form({v: c for v, c in f[0] if v != j}, f[1])


def tighten(a):
    """Exact.tighten: the atom's normal form, a list of atoms."""
    cs, k = a[-1]
    if a[0] == "ge":
        g = 0
        for _, c in cs:
            g = gcd(g, c)
        return [a] if g <= 1 else [("ge", (tuple((v, c // g) for v, c in cs), k // g))]
    m = a[1]
    if m == 0:
        return [("ge", a[-1]), ("ge", lin((-1, a[-1])))]
    d, c0 = {v: c % m for v, c in cs}, k % m
    g = gcd(m, c0, *d.values())
    if m // g == 1:
        return [("ge", ((), 0))]
    return [("dvd", m // g, form({v: c // g for v, c in d.items()}, c0 // g))]


def normalize(atoms):
    """Exact.normalize: every atom tightened, repeats dropped (first occurrences kept)."""
    out = []
    for a in atoms:
        for b in tighten(a):
            if b not in out:
                out.append(b)
    return out


def ground_ok(a):
    return a[-1][1] >= 0 if a[0] == "ge" else a[-1][1] % a[1] == 0


def hopeless(a):
    return a[0] == "ge" and a[-1][1] < 0 and all(c <= 0 for _, c in a[-1][0])


def lower_rule(atoms, j):
    """not (Exact.noDvdAt and (allNonneg or allNonpos))"""
    if any(a[0] == "dvd" and coef(a[-1], j) for a in atoms):
        return True
    cs = [coef(a[-1], j) for a in atoms]
    return not (all(c >= 0 for c in cs) or all(c <= 0 for c in cs))


def delta(atoms, j):
    """Exact.delta: lcm of the moduli of the dvd atoms in which j occurs."""
    d = 1
    for a in atoms:
        if a[0] == "dvd" and coef(a[-1], j):
            d = d * a[1] // gcd(d, a[1])
    return d


def is_lower(a, j):
    return a[0] == "ge" and coef(a[-1], j) > 0


def branches(atoms, j):
    return delta(atoms, j) * (1 + sum(coef(a[-1], j) for a in atoms if is_lower(a, j)))


def ub(atoms, j):
    """Exact.ub: the least explicit bound on j, from a ge atom with j's coefficient < 0 and no coefficient > 0
    (j <= k / -c in the naturals), or None."""
    b = None
    for a in atoms:
        c = coef(a[-1], j)
        if a[0] == "ge" and c < 0 and all(e <= 0 for _, e in a[-1][0]):
            v = max(0, a[-1][1] // -c)
            b = v if b is None else min(b, v)
    return b


def cost(atoms, j):
    """Exact.cost: the branches of j, or its explicit range when that is fewer (the enumeration rule)."""
    b, n = ub(atoms, j), branches(atoms, j)
    return n if b is None else min(b + 1, n)


def pick(atoms):
    """Exact.pickStd: among the variables present, one a one-signed rule applies to if any, then the
    fewest branches (cost), then the smallest variable."""
    present = sorted({v for a in atoms for v, _ in a[-1][0]})
    return min(present, key=lambda j: (lower_rule(atoms, j), cost(atoms, j), j))


def subst(a, j, v):
    """Exact.subst: j := v."""
    return a[:-1] + (lin((1, rest(a[-1], j)), (coef(a[-1], j) * v, ((), 1))),)


def pin_atom(b, j, a, t):
    """Exact.pinA: b multiplied by a, with a*y replaced by t."""
    g = lin((coef(b[-1], j), t), (a, rest(b[-1], j)))
    return ("ge", g) if b[0] == "ge" else ("dvd", b[1] * a, g)


def pin(atoms, j, a, t):
    """Exact.pin, with t = tOf (k minus the lower atom without j)."""
    return [("dvd", a, t), ("ge", t)] + [pin_atom(b, j, a, t) for b in atoms]


class Search:
    def __init__(self, limit):
        self.calls, self.limit = 0, limit

    def decide(self, atoms):
        """Exact.decideN: a solution {variable: natural} (variables not named are 0), or None."""
        self.calls += 1
        if self.calls > self.limit:
            raise TooBig(self.calls)
        atoms = normalize(atoms)
        if not all(ground_ok(a) for a in atoms if not a[-1][0]):
            return None
        atoms = [a for a in atoms if a[-1][0]]
        if not atoms:
            return {}
        if any(hopeless(a) for a in atoms):
            return None
        j = pick(atoms)
        if not lower_rule(atoms, j) and all(coef(a[-1], j) >= 0 for a in atoms):
            # pos: drop the atoms with j; j := large enough for each of them
            x = self.decide([subst(a, j, 0) for a in atoms if not coef(a[-1], j)])
            if x is not None:
                x[j] = sum(max(0, -value(rest(a[-1], j), x)) for a in atoms if coef(a[-1], j))
            return x
        if not lower_rule(atoms, j):
            # neg: j := 0
            return self.decide([subst(a, j, 0) for a in atoms])
        b = ub(atoms, j)
        if b is not None and b + 1 <= branches(atoms, j):
            # enum: j has an explicit range 0..b no larger than Cooper's branches; try each value
            for v in range(b + 1):
                x = self.decide([subst(a, j, v) for a in atoms])
                if x is not None:
                    x[j] = v
                    return x
            return None
        d = delta(atoms, j)
        for v in range(d):
            x = self.decide([subst(a, j, v) for a in atoms])
            if x is not None:
                x[j] = v
                return x
        for low in atoms:
            if not is_lower(low, j):
                continue
            a = coef(low[-1], j)
            for k in range(a * d):
                t = lin((1, ((), k)), (-1, rest(low[-1], j)))
                x = self.decide(pin(atoms, j, a, t))
                if x is not None:
                    x[j] = value(t, x) // a
                    return x
        return None


def solve(atoms, limit):
    """(a solution or None, calls used). Raises TooBig past limit calls."""
    s = Search(limit)
    x = s.decide(atoms)
    return x, s.calls
