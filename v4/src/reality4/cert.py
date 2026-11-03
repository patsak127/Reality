"""Certificates for the exact decision's refusals (BB's call, 28 Oct 2026 18:05; verify-opus-exact/partb/CERT/PLAN.md).

A system is a list of atoms (F, strict), F a dict variable -> number with the constant at key 1, meaning F >= 0
(F > 0 when strict). A variable whose first entry is "z" is rational; every other one is a natural number. A leaf
certificate is a proof log; each line it derives holds on every point of the system:
  ("p", i)            premise i;
  ("nat", v)          v >= 0, v natural;
  ("c", [(u, j), ..]) the sum of u times line j, each u >= 0 (strict when a strict line has u > 0);
  ("r", j)            line j over naturals only, scaled by the lcm of its denominators to integers G, k: G x + k >= 0
                      (strict: G x + k - 1 >= 0, as G x + k is an integer);
  ("d", j)            line j with integer coefficients over naturals, divided by the gcd g of its variables'
                      coefficients, its constant rounded down (G x / g is an integer at least -k / g);
  ("int", [j, ..])    the end: the lines (rounded, over naturals) have no natural point, by intstep (Lean-proved);
the last line has no variable and constant < 0, or constant 0 and strict: the system has no point. check() checks
it with exact Fractions and nothing from decide.py; pay(n) charges n steps of checking (the caller's R013 past its
bound) and pay.left() is the steps left.

Why a search.py fault can only give X001 or R013, never another verdict (Opus 5.5 review, units F01 F03 F02): every
"none" a refusal rests on is kept by the trusted Model.find, not the search (F03), and replayed here; a leaf closes
exactly its node's system (F01, Tree); a summed column's parts must partition its bands (decide.part_atoms); a
search's form is confirmed on bytes. (G02, Opus 5.5 max review 02) Nothing checked is trusted by object identity: a
checked system is kept by its forms, a node's atoms and case and the question's options by fingerprints of their
contents when checked (fp), so an object the search edits after a check closes nothing (X001). Tested by tests/test_search_mutants.py and the sweep verify-opus-exact/partb/MUT."""
from fractions import Fraction
import hashlib
import itertools
import pickle
from math import gcd, lcm
from . import intstep as I

ONE = 1
CHECKED = set()   # (G02) the systems check() has shown to have no point, by their forms then (key): Tree.leaf closes a node
# only on one, so a system edited after its check is no longer one (Opus 5.5 max review 02: not by object identity)


class Bad(Exception):
    """The certificate does not check: the refusal it stands for is not shown (X001)."""


ATOMS = {}   # (C01) the trusted atom classes (decide.RAtom, decide.PAtom) and their attributes, in order: set by decide.py


def exact(x, memo=None):
    """(C01, review 3 01; B02 part 2) The one copy of a value from the search that the checker reads: rebuilt from exact
    types only (None, bool, int, str, bytes, Fraction, tuple, list, dict and the trusted atom classes with their attributes),
    read through the built-ins' own methods, never the value's. A subclass of any of them (whose keys(), items() or
    __getitem__ could show the checker one thing and a pickle or the model another) is Bad. memo (id -> (value, copy))
    keeps one copy per object, so the identities a tree checks (an option's atoms, a node's) hold among the copies."""
    t = type(x)
    if t is int or t is str or t is bytes or t is bool or x is None:
        return x
    memo = {} if memo is None else memo
    got = memo.get(id(x))
    if got is not None and got[0] is x:   # the memo holds x, so its id is not another object's
        return got[1]
    if t is Fraction:
        n, d = x.numerator, x.denominator
        if type(n) is not int or type(d) is not int:
            raise Bad("a number from the search that is not an exact Fraction")
        y = Fraction(n, d)
    elif t is tuple:
        y = tuple([exact(u, memo) for u in tuple.__iter__(x)])
    elif t is list:
        y = []
        memo[id(x)] = (x, y)
        try:
            y.extend(exact(u, memo) for u in list.__iter__(x))
        except Exception:   # (D01, review 4) a copy that failed is no copy: a search that catches the Bad cannot reuse it
            memo.pop(id(x), None)
            raise
    elif t is dict:
        y = {}
        memo[id(x)] = (x, y)
        try:
            for k, v in dict.items(x):
                k = exact(k, memo)
                if type(k) in (list, dict):
                    raise Bad("a dict key from the search that is not hashable")
                y[k] = exact(v, memo)
            if len(y) != dict.__len__(x):   # (D01, review 4) two keys that are one value once copied (a Fraction's fields rewritten)
                raise Bad("a dict from the search whose keys are not distinct values")
        except Exception:
            memo.pop(id(x), None)
            raise
    elif t in ATOMS:
        y = tuple.__new__(t, [exact(u, memo) for u in tuple.__iter__(x)])
        d = object.__getattribute__(x, "__dict__")
        if type(d) is not dict or any(a not in d for a in ATOMS[t]):
            raise Bad("an atom from the search without its class's attributes")
        memo[id(x)] = (x, y)
        try:
            for a in ATOMS[t]:
                object.__setattr__(y, a, exact(dict.get(d, a), memo))
        except Exception:
            memo.pop(id(x), None)
            raise
    else:
        raise Bad(f"a value from the search of a type the checker does not copy ({t.__name__})")
    memo[id(x)] = (x, y)
    return y


def nat(v):
    return v != ONE and v[0] != "z"


def comb(terms, lines, pay):
    out, strict = {}, False
    for u, j in terms:
        u = Fraction(u)
        if u < 0 or not 0 <= j < len(lines):
            raise Bad(f"multiplier {u} or line {j}")
        F, st = lines[j]
        pay(len(F) + 1)
        for v, c in F.items():
            out[v] = out.get(v, 0) + u * c
        strict = strict or (st and u > 0)
    return {v: c for v, c in out.items() if c}, strict


def rnd(line):
    F, st = line
    if not all(v == ONE or nat(v) for v in F):
        raise Bad("rounding a line with a rational variable")
    m = lcm(*[Fraction(c).denominator for c in F.values()])
    G, k = {v: Fraction(c) * m for v, c in F.items() if v != ONE}, Fraction(F.get(ONE, 0)) * m - st
    return ({**G, ONE: k} if k else G), False


def check(system, log, pay, keep=False):
    """None when the log shows the system has no point; else Bad. The system is remembered (CHECKED): the last one
    only, or with keep every one until the statement ends (a float system's memo answers it again). (C01) Both are
    read as exact copies: the forms checked are the forms remembered."""
    if not keep:
        CHECKED.clear()
    memo = {}
    system, log = exact(system, memo), exact(log, memo)
    if type(system) is not list and type(system) is not tuple or type(log) is not list and type(log) is not tuple:
        raise Bad("a system or a log that is not a list")
    lines = []
    for step in log:
        pay(1)
        if step[0] == "p":
            if not 0 <= step[1] < len(system):
                raise Bad(f"premise {step[1]}")
            lines.append(system[step[1]])
        elif step[0] == "nat":
            if not nat(step[1]):
                raise Bad(f"{step[1]} is not natural")
            lines.append(({step[1]: 1}, False))
        elif step[0] == "c":
            lines.append(comb(step[1], lines, pay))
        elif step[0] in ("r", "d"):
            if not 0 <= step[1] < len(lines):
                raise Bad(f"line {step[1]}")
            lines.append(rnd(lines[step[1]]) if step[0] == "r" else div(lines[step[1]]))
        elif step[0] == "int" and step is log[-1]:
            intstep(step[1], lines, pay)
            CHECKED.add(key(system))
            return None
        else:
            raise Bad(f"step {step[0]}")
    if not lines:
        raise Bad("an empty log")
    F, st = lines[-1]
    k = F.get(ONE, 0)
    if any(v != ONE for v in F) or not (k < 0 or k == 0 and st):
        raise Bad("the last line is not a contradiction")
    CHECKED.add(key(system))
    return None


def fp(x, pay=None):
    """(G02) A fingerprint of x's contents now (its pickle: every value, attribute and type it holds): what a check saw,
    so that an edit made later is seen. Cases, atoms and their parts only; one that cannot be pickled is Bad."""
    try:
        s = pickle.dumps(x, 5)
    except Exception:
        raise Bad("a case or an atom that cannot be compared by its contents") from None
    if pay is not None:
        pay(len(s) // 64 + 1)
    return hashlib.sha256(s).digest()


def div(line):
    F, st = line
    G = {v: c for v, c in F.items() if v != ONE}
    if st or not G or not all(nat(v) and Fraction(c).denominator == 1 for v, c in G.items()) or Fraction(F.get(ONE, 0)).denominator != 1:
        raise Bad("dividing a line that is not integral over naturals")
    g = 0
    for c in G.values():
        g = gcd(g, int(c))
    k = Fraction(F.get(ONE, 0)) // g
    return ({**{v: Fraction(c) / g for v, c in G.items()}, ONE: k} if k else {v: Fraction(c) / g for v, c in G.items()}), False


def intstep(js, lines, pay):
    """The lines js, rounded, handed to the integer step with equal columns merged (a solution of the lines gives one
    of the merged system: each group's sum); its None shows no natural point (Exact.decide_correct)."""
    ints = []
    for j in js:
        if not 0 <= j < len(lines):
            raise Bad(f"line {j}")
        G, _ = rnd(lines[j])
        pay(len(G) + 1)
        ints.append(({v: int(c) for v, c in G.items() if v != ONE}, int(G.get(ONE, 0))))
    vs = sorted({v for G, _ in ints for v in G}, key=repr)
    col = {v: tuple(G.get(v, 0) for G, _ in ints) for v in vs}
    ix = {c: i for i, c in enumerate(dict.fromkeys(col[v] for v in vs))}
    one = {ix[col[v]]: v for v in vs}
    pay(len(vs) * (len(ints) + 1))
    S = I.Search(max(1, pay.left()))
    try:
        x = S.decide([("ge", I.form({j: G[v] for j, v in one.items() if v in G}, k)) for G, k in ints])
    except I.TooBig:
        x = None
    pay(S.calls)   # past the bound: the caller's R013 (a stated bound, not a failed certificate)
    if x is not None or S.calls > S.limit:
        raise Bad("the integer step finds a natural point" if x is not None else "the integer step did not end")
    return None


def form(*terms):
    """The form sum of k * F over (k, F) pairs, F a dict (the constant at key 1) or a variable."""
    out = {}
    for k, F in terms:
        for v, c in (F.items() if isinstance(F, dict) else [(F, 1)]):
            out[v] = out.get(v, 0) + k * c
    return {v: c for v, c in out.items() if c}


def same(F, G):
    return {v: Fraction(c) for v, c in F.items() if c} == {v: Fraction(c) for v, c in G.items() if c}


def has(atoms, F):
    return any(not st and same(A, F) for A, st in atoms)


def rng(r):
    """(D01, review 4) A mean's rows range (a, b, sg): a, b integers (int, or a Fraction of denominator 1; b None: no
    top), sg -1, 0, 1 or None. The cover below steps a range's top by 1: an end between two integers would leave the
    integer between two children's ends in neither."""
    whole = lambda v: type(v) is int or type(v) is Fraction and v.denominator == 1   # noqa: E731
    return type(r) is tuple and len(r) == 3 and whole(r[0]) and (r[1] is None or whole(r[1])) and (r[2] is None or type(r[2]) is int and r[2] in (-1, 0, 1))


def prange_split(P, parent, root, kids, pay, ob=None, tree=None, case=None):
    """A mean's rows split (decide.prange, SPEC-EXACT 3.5): P's facts are trusted (S = mu·N, lo <= mu <= hi: the mean of
    its rows, its classes' ends); the rest is checked. Each child keeps the parent's atoms or adds atoms of P's range
    (a, b, sg): N - a >= 0, b - N >= 0, sg·mu >= 0, each present, and every other added atom is the product of two of
    those (or of mu - lo, hi - mu) with mu·N read as S, linear (no mu·mu, N·N), or with an equality N = a any multiple
    of N - a by mu; the children's ranges cover the parent's: the integers of [a, b] (N integer-valued over naturals),
    each sign the parent's (0 only on one point), or a split of mu's sign; one child's sign is the parent's atom, or
    lo >= 0 (hi <= 0). None, or Bad."""
    mu, S, N = P.mu, P.S, P.N
    if not any(A is P for A in root) and (tree is None or (mu, tuple(S.items()), tuple(N.items()), P.lo, P.hi, P.a0, P.key) not in mcall(tree.model, "piece_facts", case)):
        raise Bad("a mean's rows split of a PAtom that is neither the option's nor one of the model's pieces (H08)")   # its facts are trusted below
    if not all(v == ONE or nat(v) and Fraction(c).denominator == 1 for v, c in N.items()) or Fraction(N.get(ONE, 0)).denominator != 1:
        raise Bad("a mean's rows N that is not integer-valued over naturals")
    pr = next((A.r for A in parent if getattr(A, "z", None) == P.key and hasattr(A, "r")), None)
    if pr is not None:   # (D01, review 4 01) a range the search names (.r) is read only as the parent's atoms state it
        if not rng(pr) or not (has(parent, form((1, N), (-pr[0], ONE))) and (pr[1] is None or has(parent, form((-1, N), (pr[1], ONE))))
                               and (not pr[2] or has(parent, {mu: pr[2]}))):
            raise Bad("a mean's rows split of a parent whose atoms do not state its range")
    ranges = []
    for k in kids:
        new = [A for A in k if not any(A is B for B in parent)]
        rs = [A.r for A in new if getattr(A, "z", None) == P.key]
        if not rs or any(not rng(r) or r != rs[0] for r in rs):
            raise Bad("a child of a mean's rows split without one range")
        a, b, sg = r = rs[0]   # (D01) its atoms are checked to state it below
        ranges.append(r)
        pay((len(new) + 1) * 29 * (len(N) + len(S) + 4))   # each atom against the range facts and their 28 products
        facts = [form((1, N), (-a, ONE))] + ([form((-1, N), (b, ONE))] if b is not None else [])
        if not all(has(new, F) for F in facts):
            raise Bad("a child's range atoms are not there")
        eq = b is not None and a == b
        if sg:
            if not has(new, {mu: sg}):
                raise Bad("a child's sign atom is not there")
            facts.append({mu: sg})
        facts += ([form((1, mu), (-P.lo, ONE))] if P.lo is not None else []) + ([form((-1, mu), (P.hi, ONE))] if P.hi is not None else []) + [{ONE: 1}]
        for F, st in new:
            if st or not (any(same(F, G) for G in facts) or any(same(F, prod(f, g, mu, N, S)) for i, f in enumerate(facts) for g in facts[i:] if prod(f, g, mu, N, S) is not None)
                    or eq and sg == 0 and any(same(F, form((t, S), (-t * a, mu))) for t in (1, -1))):
                raise Bad("an atom of a mean's rows split that is no product of its range")
    if pr is None:   # the first split: [a0, None) (N >= a0: P's own atom in the option, or N >= 0 when a0 <= 0) by mu's sign
        a0 = ranges[0][0]   # (B06, Argon review 2 06) at most P's own a0: a greater one leaves [P.a0, a0) uncovered
        if any(r[:2] != (a0, None) for r in ranges) or not (any(A is P for A in root) and a0 <= P.a0 or a0 <= 0 and all(c > 0 for v, c in N.items() if v != ONE) and N.get(ONE, 0) >= 0):
            raise Bad("a mean's first rows split not over [a0, ...)")
        sgs = sorted(r[2] for r in ranges if r[2] is not None)
        one = len(ranges) == 1 and (ranges[0][2] is None or has(parent, {mu: ranges[0][2]}) or ranges[0][2] == 1 and P.lo is not None and P.lo >= 0 or ranges[0][2] == -1 and P.hi is not None and P.hi <= 0
                                    or ob is not None and implied(tree, ob, case, parent, root, {mu: -ranges[0][2]}))
        if not (one or sgs == [-1, 1] and len(ranges) == 2):
            raise Bad("a mean's first rows split whose signs do not cover mu's")
        return None
    a, b, sg = pr
    if any(r[2] != sg and not (r[2] == 0 and r[0] == r[1]) for r in ranges):
        raise Bad("a child's sign is not its parent's")
    at = a
    for lo, hi, _ in sorted(ranges, key=lambda r: r[0]):
        if lo > at:
            raise Bad(f"the rows {at}..{lo - 1} of a mean are in no child")
        at = max(at, hi + 1) if hi is not None else None
        if at is None:
            break
    if at is not None and (b is None or at <= b):
        raise Bad("a mean's rows split leaves its top uncovered")
    return None


def implied(tree, ob, case, parent, root, F):
    """Whether ob, a system shown to have no point (tree.proved), is the model's atoms of the parent's case, the option's
    atoms, the parent's and F > 0: then -F >= 0 on every point of the parent."""
    base = mcall(tree.model, "base", case)
    want = list(base) + list(root) + list(parent) + [(F, True)]
    tree.pay(sum(len(A[0]) + 1 for A in want))
    if key(want) not in tree.shown or key(ob) != key(want):
        raise Bad("a piece's sign by its end's that is not shown")
    return True


def prod(f, g, mu, N, S):
    """The product f·g of two forms over mu, N's variables and 1, with mu·N read as S: None unless it is linear so."""
    fm, gm = f.get(mu, 0), g.get(mu, 0)
    fn, gn = ratio(f, N, mu), ratio(g, N, mu)
    if fn is None or gn is None or fm * gm or fn * gn:
        return None
    f1, g1 = f.get(ONE, 0) - fn * N.get(ONE, 0), g.get(ONE, 0) - gn * N.get(ONE, 0)
    return form((fm * gn + gm * fn, S), (fm * g1 + gm * f1, mu), (fn * g1 + gn * f1, N), (f1 * g1, ONE))


def ratio(f, N, mu):
    """t when f = t·N + c·mu + d (N's variables only through N), else None."""
    vs = {v: c for v, c in f.items() if v not in (ONE, mu)}
    nv = {v: c for v, c in N.items() if v != ONE}
    if not vs:
        return 0
    t = Fraction(next(iter(vs.values()))) / nv.get(next(iter(vs)), 0) if nv.get(next(iter(vs))) else None
    return t if t is not None and same(vs, {v: t * c for v, c in nv.items()}) else None


class Tree:
    """The case splits of one option (case, atoms) of find (Model.solve1). A node has a case and the atoms its splits
    added (more). A node is closed by a checked leaf whose system is the model's atoms of the node's case (model.base),
    then the option's atoms and exactly the node's (kept per node, F01), in order, before `tail` model facts (same_means). A split is checked: a sign split (two children add F >= 0 and -F >= 0); a mean's rows split
    (prange_split); or a model disjunction ("model", name, args): the model's own statement of cases that hold
    together on every input (model.disjunction, the trusted model's code, never the search's), each child the parent's case
    and atoms within one of them (cover); obligations of a disjunction (systems the model says must have no point)
    are met only by systems check() has shown (proved); two floats pinned (pin_split). Any other rule is Bad (L6: no
    named lemma is left).
    done(): every node is closed or split with every child done."""

    def __init__(self, case, atoms, pay=lambda n: None, model=None):   # model: the trusted model (base, tail, disjunction)
        self.root, self.kids, self.closed, self.pay = (case, atoms), {0: None}, set(), pay
        self.model, self.case, self.shown, self.splits = model, {0: case}, set(), {}
        self.more = {0: (0, fp([], pay))}   # (F01) each node's own atoms, as its split gave them: a leaf's and a split's are compared with these
        self.fcase, self.froot = {0: fp(case, pay)}, fp(atoms, pay)   # (G02) by their contents when given: an edit since is Bad
        # (C01, review 3 01) the tree reads every atom from the search as its one exact copy (memo: per object), the
        # option's atoms too (croot); a node's case as the search names it (case: compared by identity only) and as the
        # model made it (mcase: the only one the model's methods are given)
        self.memo, self.mcase = {}, {0: case}
        self.croot = exact(atoms, self.memo)
        self.fcroot = fp(self.croot, pay)

    def proved(self, system):
        """A system check() has just shown to have no point, kept (by its forms) for an obligation."""
        system = exact(system, self.memo)   # (C01)
        if key(system) not in CHECKED:
            raise Bad("an obligation's system that check() has not shown to have no point (as it is now)")
        self.pay(sum(len(F) + 1 for F, _ in system))
        self.shown.add(key(system))

    def split(self, node, rule, more, kids):
        """kids: the children as (case, more). (C01) Read as exact copies: the case of each by identity only."""
        if type(node) is not int or type(kids) is not list and type(kids) is not tuple or any(type(k) is not tuple or len(k) != 2 for k in kids):
            raise Bad("a split whose node or children are not exact")
        rule, more = exact(rule, self.memo), exact(more, self.memo)
        kids = [(c, exact(m, self.memo)) for c, m in kids]
        if node not in self.case or self.kids.get(node) is not None or not self.as_given(node, more) \
                or fp(self.root[1], self.pay) != self.froot:   # (A02, Argon review 02) the option's atoms as given, at each split too
            raise Bad("a split of a node that is not open, or whose atoms or case (or its option's) are not the ones given")
        pc, mc = self.case[node], self.mcase[node]
        ks = [m for _, m in kids]
        mcs = [mc] * len(kids)
        if isinstance(rule, tuple) and rule[0] == "model":
            D, need = mcall(self.model, "disjunction", rule[1], rule[2], mc, self.croot, more)
            for sys_ in need:
                self.pay(sum(len(F) + 1 for F, _ in sys_))
                if key(sys_) not in self.shown:
                    raise Bad(f"a {rule[1]} split whose obligation is not shown")
            cover(D, more, kids, self.model, self.pay, rule[1])
            mcs = [dc for dc, _ in D]   # (C01) each child's case for the model: the model's own, never the search's
        else:
            if any(c is not pc for c, _ in kids):
                raise Bad("a split that changes the case outside the model's disjunctions")
            if isinstance(rule, tuple) and rule[0] == "pin":   # ("pin", atoms): two floats pinned (fwin), checked
                if len(ks) != 1:
                    raise Bad("a pin split with other than one child")
                ids = {id(A) for A in more}
                new = [A for A in ks[0] if id(A) not in ids]
                sys_ = list(mcall(self.model, "base", mc)) + list(self.croot) + list(more)
                pin_split(sys_ + list(mcall(self.model, "tail", mc, self.croot, list(more) + new)), new, self.pay)
            elif isinstance(rule, tuple):   # ("prange", P[, obligation]): checked
                prange_split(rule[1], more, self.croot, ks, self.pay, rule[2] if len(rule) > 2 else None, self, mc)
            elif rule == "sign":
                new = [[A for A in k if not any(A is B for B in more)] for k in ks]
                if len(new) != 2 or any(len(a) != 1 or a[0][1] for a in new) or {**new[0][0][0]} != {v: -c for v, c in new[1][0][0].items()}:
                    raise Bad("a sign split whose children do not add F >= 0 and -F >= 0")
            else:
                raise Bad(f"a split by a rule the checker does not know ({rule})")
        k = rule if isinstance(rule, str) else rule[1] if rule[0] == "model" else "pin" if rule[0] == "pin" else "prange shown" if len(rule) > 2 else "prange"
        self.splits[k] = self.splits.get(k, 0) + 1
        ids = list(range(len(self.kids), len(self.kids) + len(kids)))
        self.kids[node] = ids
        self.kids.update({i: None for i in ids})
        self.case.update({i: c for i, (c, _) in zip(ids, kids)})
        self.mcase.update(zip(ids, mcs))
        self.more.update({i: (len(m), fp(m, self.pay)) for i, (_, m) in zip(ids, kids)})   # (G02) as checked now
        self.fcase.update({i: fp(c, self.pay) for i, (c, _) in zip(ids, kids)})
        return ids

    def as_given(self, node, more):
        """(G02) more is the node's atoms and its case is as the split that made it checked them (by contents)."""
        return len(more) == self.more[node][0] and fp(more, self.pay) == self.more[node][1] and fp(self.case[node], self.pay) == self.fcase[node]

    def leaf(self, node, system, path, tail):
        if type(node) is not int or type(tail) is not int:   # (C01) the rest as exact copies
            raise Bad("a leaf whose node or tail is not an exact int")
        system, path = exact(system, self.memo), exact(path, self.memo)
        if type(system) is not list and type(system) is not tuple or type(path) is not list and type(path) is not tuple:
            raise Bad("a leaf's system or atoms that are not a list")
        if key(system) not in CHECKED:
            raise Bad("a leaf closed on a system check() has not shown to have no point (as it is now)")
        n = len(system) - tail
        if n < len(path) or any(a != b for a, b in zip(system[n - len(path):n], path)):
            raise Bad("a leaf's system does not hold its node's atoms")
        k = len(path) - self.more[node][0] if node in self.more else -1
        if node not in self.case or self.kids.get(node) is not None or k != len(self.root[1]) or not self.as_given(node, path[k:]) \
                or fp(path[:k], self.pay) != self.fcroot:   # (F01) the option's atoms, then exactly the node's; (G02) as given
            raise Bad("a leaf's atoms are not its option's and then its node's (no atom its splits did not give it)")
        if self.model is not None:
            base = mcall(self.model, "base", self.mcase[node])
            self.pay(sum(len(F) + 1 for F, _ in base))
            if len(base) != n - len(path) or any(not (a is b or b[1] == a[1] and same(a[0], b[0])) for a, b in zip(system, base)):
                raise Bad("a leaf's system is not the model's atoms of its node's case")
            root = self.croot
            if len(path) < len(root) or any(a is not b for a, b in zip(path, root)):
                raise Bad("a leaf's atoms do not start with its option's")
            tl = mcall(self.model, "tail", self.mcase[node], root, path[len(root):])
            self.pay(sum(len(F) + 1 for F, _ in tl))
            if len(tl) != tail or any(not (b[1] == a[1] and same(a[0], b[0])) for a, b in zip(system[n:], tl)):
                raise Bad("a leaf's system ends with facts that are not the model's")
        self.closed.add(node)

    def done(self):
        todo = [0]
        while todo:
            n = todo.pop()
            if n not in self.closed:
                if self.kids.get(n) is None:
                    raise Bad(f"node {n} of an option's splits is neither closed nor split")
                todo += self.kids[n]


def mcall(model, name, *a):
    """(B07, Argon review 2 07) A trusted model method by its class: one the search set on the instance is never read."""
    return getattr(type(model), name)(model, *a)


def key(system):
    """A system by its forms (an obligation is met by a shown system with the same atoms in the same order)."""
    return tuple((tuple(sorted(((v, Fraction(c)) for v, c in F.items() if c), key=repr)), bool(st)) for F, st in system)


def cover(D, more, kids, model, pay, name):
    """A split by the model's disjunction D = [(case, atoms)]: one child per case, in order; a child's case is the
    case's (model.same_case) and each of its atoms is one of the parent's (the same object) or of the case's (the same
    form). So a child's points include the parent's points in its case, and the cases hold together on every input:
    every point of the parent is in a child (a child may drop atoms: more points, still sound for no point)."""
    if len(D) != len(kids):
        raise Bad(f"a {name} split with {len(kids)} children for the model's {len(D)} cases")
    ids = {id(A) for A in more}
    for (dc, dA), (kc, km) in zip(D, kids):
        pay(len(km) * (len(dA) + 1) + 1)
        if not mcall(model, "same_case", kc, dc):
            raise Bad(f"a {name} split whose child's case is not the model's")
        for A in km:
            if id(A) not in ids and not any(A[1] == B[1] and same(A[0], B[0]) for B in dA):
                raise Bad(f"a {name} split's child with an atom of neither its parent nor the model's case")


def options_closed(options, trees, f0, pay):
    """find()'s "none": every option (case, atoms) has its own done tree, and (G02) the options are as the question
    asked them (f0, their fingerprint before the search saw them) and each tree's root as it was given then."""
    if fp(options, pay) != f0:
        raise Bad("the question's options were changed after it asked them")
    if type(trees) is not dict:   # (C01) the search's trees: an exact dict of Trees, done() by the class
        raise Bad("the search's trees are not an exact dict")
    for i, (case, A) in enumerate(options):
        t = dict.get(trees, i)
        if type(t) is not Tree or t.root[0] is not case or t.root[1] is not A or t.fcase[0] != fp(case, pay) or t.froot != fp(A, pay):
            raise Bad(f"option {i} has no tree of its own, as asked")
        Tree.done(t)


def shares_zero(S1, B1, S2, B2, x0, atoms, pay):
    """SPEC-EXACT 5.4 for two shares S1/B1 and S2/B2 over counts: q = S1 B2 - S2 B1 is a polynomial of degree 2 in the
    counts; a variable that an atom -(n + ...) >= 0 (no constant, every coefficient < 0) holds at 0 is 0 on every
    solution. If q is 0 at x0, x0 + e_v, x0 + 2 e_v and x0 + e_v + e_w for the other variables v, w, its constant,
    linear and quadratic coefficients are 0 (q(x0 + t) = c + L t + t'Qt: L_v + Q_vv = 2 L_v + 4 Q_vv = 0, then Q_vw = 0):
    q is 0 wherever those variables are 0, so the shares are equal on every solution. Recomputed here: None, or Bad."""
    zero = {v for F, _ in atoms if not F.get(ONE) and F and all(c < 0 for c in F.values()) for v in F}
    pay(len(atoms))
    vs = sorted({v for F in (S1, B1, S2, B2) for v in F if v != ONE} - zero, key=repr)
    if any(not nat(v) for v in vs) or any(x0.get(v, 0) for v in zero):
        raise Bad("a share's form has a rational variable, or x0 is not 0 where an atom holds it at 0")
    val = lambda F, x: sum(Fraction(c) * (1 if v == ONE else x.get(v, 0)) for v, c in F.items())
    pts = [x0] + [{**x0, v: x0.get(v, 0) + k} for v in vs for k in (1, 2)] + [{**x0, v: x0.get(v, 0) + 1, w: x0.get(w, 0) + 1} for i, v in enumerate(vs) for w in vs[i + 1:]]
    for x in pts:
        pay(len(vs) + 4)
        if val(S1, x) * val(B2, x) != val(S2, x) * val(B1, x):
            raise Bad("two shares differ at a point the search did not report")
    return None


def var_verdict(f, c, w, sd, sup):
    """(3.7, w1_var) The verdict on a comparison f of a variance (sd: its square root) widened by w with cutoff c, whose
    values on the answering inputs are every number in [0, M], M = sup (sd: sqrt(sup)), both ends reached (lemma 3.7;
    a variance is >= 0 by the kernel's own formula, a sum of squares over n - ddof >= 1): written here from the
    comparison's meaning, not from decide's table. The widened value [v - w, v + w] holds when every point of it
    satisfies x f c, fails when none does. ("S011", by_sup) when no value holds, ("S008", by_sup) when none fails, else
    None; by_sup: whether the answer needs sup (False: the value's sign alone gives it)."""
    sat = {"exceeds": lambda x: x > c, "atleast": lambda x: x >= c, "below": lambda x: x < c, "atmost": lambda x: x <= c}[f]
    up = f in ("exceeds", "atleast")
    # holds: up, v - w satisfies (v >= t, strict when f is exceeds); else v + w satisfies (v <= t). fails: the other side.
    hold = (up, c + w if up else c - w, f in ("exceeds", "below"))   # (v above t?, t, strict)
    fail = (not up, c - w if up else c + w, f in ("atleast", "atmost"))
    assert sat(hold[1] + (1 if up else -1)) and not sat(fail[1] + (-1 if up else 1))   # the rays lie on the right sides

    def meets(r):   # some v in [0, M] on the ray; (meets, needed sup)
        above, t, strict = r
        if not above:
            return (0 < t or not strict and t == 0), False
        if sd:
            return (t < 0 or (sup > t * t or not strict and sup == t * t)), t >= 0
        return (sup > t or not strict and sup == t), True
    (h, hs), (g, gs) = meets(hold), meets(fail)
    if not h:
        return "S011", hs
    if not g:
        return "S008", gs
    return None


def pin_split(system, new, pay):
    """(L5; 3.6, fwin) Two variables u, v pinned to a point (a, w) in one child: sound for no point when every atom of the
    parent's system with u or v has no other variable and holds at (a, w): any point of the parent with (u, v) moved to
    (a, w) is a point of the child. new: the child's added atoms, u = a and v = w as four atoms. (B01, Argon review 2 01)
    That holds only for variables whose every value is a float: u and v are pixdims (fwin's pair), each in the system."""
    pay(len(new) + sum(len(F) + 1 for F, _ in system))
    pt = {}
    for F, st in new:
        vs = [v for v in F if v != ONE]
        if st or len(vs) != 1 or abs(F[vs[0]]) != 1:
            raise Bad("a pin atom that is not v >= a or v <= a")
        pt.setdefault(vs[0], set()).add(-Fraction(F.get(ONE, 0)) / F[vs[0]])
    if len(pt) != 2 or any(len(b) != 1 for b in pt.values()) or len(new) != 4 or \
            any(sum(1 for F, _ in new if v in F and F[v] == d) != 1 for v in pt for d in (1, -1)):
        raise Bad("a pin split that does not pin two variables to one point")
    x = {v: next(iter(b)) for v, b in pt.items()}
    for a in x.values():   # a point of floats: the child's point is an input's
        try:
            if Fraction(float(a)) != a or a != a or abs(float(a)) == float("inf"):
                raise Bad("a pinned value that is not a float")
        except OverflowError:
            raise Bad("a pinned value that is not a float") from None
    if any(not (isinstance(v, tuple) and v[:2] == ("z", "pix")) or not any(v in F for F, _ in system) for v in x):
        raise Bad("a pinned variable that is not a float of the parent's atoms (a pixdim, fwin's pair)")
    for F, st in system:
        if any(v in F for v in x):
            if any(v != ONE and v not in x for v in F):
                raise Bad("a pinned variable in an atom with another variable")
            val = sum(Fraction(c) * (1 if v == ONE else x[v]) for v, c in F.items())
            if val < 0 or st and val == 0:
                raise Bad("a pinned point that breaks the parent's atom")
    return None


def vrange_none(ivs, K, pay):
    """(L6; 3.7) No value in a piece of K: every value lies in one of the closed intervals ivs (the model's ranges of a
    variance shape: a variance lies in [0, sup]), and each interval misses each piece (lo, lo closed, hi, hi closed;
    None: no bound). None, or Bad."""
    pay(len(ivs) * len(K) + 1)
    for a, b in ivs:
        if a > b:
            raise Bad("a variance's range that is empty")
        for lo, lc, hi, hc in K:
            if not (hi is not None and (hi < a or hi == a and not hc) or lo is not None and (lo > b or lo == b and not lc)):
                raise Bad("a piece a variance's range meets")
    return None


def vdeep_none(K, d, vals, nmax, pay):
    """(L6; 3.7, 5a) No variance (ddof d) of rows whose values are among vals (the model's: every readable value of the
    classes) lies in a piece of K: 0 is in none; every multiset of 2..nmax values is tried (two values: j rows at the
    greater, the variance j(n - j)/(n(n - d))·D², the least j meeting a piece's lower end found by halving, as
    j(n - j) grows to n/2); and every piece lies above the greatest variance of more rows, the largest of
    (N//2)(N - N//2)·D²/(N(N - d)) at N = nmax + 1, nmax + 2 (no more rows give more: with ddof 1 it falls
    along each parity; with ddof 0 it is D²/4 at even N and below it at odd). None, or Bad."""
    vals = sorted(set(vals))
    pay(len(vals) + len(K) + 1)
    inK = lambda y, p: (p[0] is None or y > p[0] or p[1] and y == p[0]) and (p[2] is None or y < p[2] or p[3] and y == p[2])   # noqa: E731
    if nmax < 1 or not vals:
        raise Bad("values that do not rule out a variance in a piece")
    D2 = (vals[-1] - vals[0]) ** 2
    top = max(Fraction(N // 2 * (N - N // 2)) * D2 / (N * (N - d)) for N in (nmax + 1, nmax + 2))
    if any(inK(Fraction(0), p) for p in K) or any(p[0] is None or p[0] < top or p[0] == top and p[1] for p in K):
        raise Bad("values that do not rule out a variance in a piece")
    for n in range(2, nmax + 1):
        if len(vals) <= 2:
            for lo, lc, hi, hc in K:
                pay(n.bit_length() + 1)
                y = lambda j: Fraction(j * (n - j)) * D2 / (n * (n - d))   # noqa: E731
                a, b = 0, n // 2 + 1   # the least j in [0, n // 2] with y(j) past lo (b: none)
                while a < b:
                    j = (a + b) // 2
                    if y(j) > lo or lc and y(j) == lo:
                        b = j
                    else:
                        a = j + 1
                if a <= n // 2 and inK(y(a), (lo, lc, hi, hc)):
                    raise Bad("rows of two values whose variance lies in a piece")
            continue
        for xs in itertools.combinations_with_replacement(vals, n):
            pay(n + len(K))
            mu = sum(xs) / n
            y = sum((x - mu) ** 2 for x in xs) / (n - d)
            if any(inK(y, p) for p in K):
                raise Bad("rows whose variance lies in a piece")
    return None
