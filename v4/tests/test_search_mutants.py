"""(Opus 5.5 review, 29 Oct 2026; BB's call on Patsak's behalf) search.py is outside the trusted base: a fault there can
only make a verdict X001 or R013, never a different decided verdict. Each mutant below breaks one search.py function
(the wrapper changes what it returns, or raises); each claim's verdict code under it must be the unmutated one, X001
or R013. The full sweep over every search.py function and five ground-truth runners is
verify-opus-exact/partb/MUT (RESULTS-*.tsv; it found one hole, fixed at F04: "empty" answers of solve and the rest
made a mean's "no other answer" vacuous). (G02, Opus 5.5 max review 02) Two tamper kinds beside the five: "stale" drops
each solution and, in a refusal's replay, closes the leaf on a system checked with one atom more and then edited back
(the review's tamper, cert.py keyed checked systems by object identity); "edit" drops the last atom of each atom list it
is given, in place (a list reused after its check). (H08, Opus 5.5 max2 review 08) "data": wrong facts in an object cert.py
trusts: every PAtom a function returns gets inverted bounds of its mean (the review's piece_atoms tamper)."""
import sys

import pytest

from helpers import run, tsv
from reality4 import decide as D
from reality4 import search as S

T7 = "group\tsite\tsex\nA\ts1\tF\nA\ts2\tM\nB\ts1\tF\nB\ts1\tM\nP\ts2\tF\nA\ts3\tM\nB\ts2\tF\n"
C2 = f'below(sum(where(t, gt("x", c = 0.{"0" * 996}5), le("y", c = 2.05)), "x"), c = 1{"0" * 400}.{"0" * 499}2)'
CLAIMS = [   # (table, claim): formed, S008 W1, S008 W2, R013, S008 by the read limit, a summed column, Opus 03's share, a mean
    (T7, 'share(where(t, ne("group", "A"), ne("group", "B"), eq("sex", "F")), where(t, ne("group", "A")))'),
    (T7, 'atleast(rows(t), c = 0)'),
    (T7, 'count(where(t, eq("group", "A"), ne("group", "B")))'),
    (T7, 'atmost(count(where(t, eq("group", "A"))), c = 1000000)'),
    (T7, 'atmost(count(where(t, eq("group", "A"))), c = 1000000000)'),
    ("g\tx\ty\nA\t0.5\t1\nB\t0.25\t2\nA\t0.75\t3\n", C2),
    ("g\tx\nA\t1\nA\t2\nB\t1\nA\t1\n", 'share(where(t, eq("g", "A"), eq("x", "1")), where(t, eq("g", "A")))'),
    ("group\tage\nA\t30\nB\t40\nA\t25\n", 'atleast(mean(t, "age"), c = 0)'),   # F04: the sweep's hole (a mean)
    ("g\na\na\nb\n", 'exceeds(count(where(t, eq(1, "a"))), c = 1)'),   # G02: the max review's claim
    ("g\tx\ty\nA\t1\t1\nA\t2\t0\nB\t1\t2\nA\t0\t1\n", 'difference(sum(t, 3), max(t, 3))'),   # H08: a summed and ordered column (pieces)
]
MUTANTS = [("find_options", "none"), ("find_options", "big"), ("find_options", "past"), ("find_options", "flip"),
           ("solve", "none"), ("one_solve", "none"), ("one_solve", "flip"), ("refine", "flip"), ("no", "flip"),
           ("prove", "none"), ("piece_atoms", "empty"), ("thin", "flip"), ("tidy", "none"), ("presolve", "none"),
           ("fm", "none"), ("lp", "none"), ("back", "none"),
           ("solve", "empty"), ("finish", "empty"), ("back", "empty"), ("tidy", "empty"), ("tidy", "flip"),   # F04's nine, five of them
           ("one_solve1", "stale"), ("one_solve1", "edit"), ("solve1", "edit"), ("one_solve2", "edit"), ("no", "edit"),   # G02
           ("piece_atoms", "data"), ("find_options", "data"),   # H08 (Opus 5.5 max2 review 08): wrong facts in a PAtom
           ("find_options", "pin"),   # B01 (Argon review 2 01): each option closed by a pin of two naturals
           ("find_options", "views"),   # C01 (review 3 01): each option closed by a sign split of an atom whose views lie
           ("find_options", "ranges")]   # D01 (review 4 01): each option closed by binade splits of ranges its atoms do not state


def code(text):
    ln = [x for x in text.split("\n") if x.startswith("line 3:")][0]
    return "formed" if ln.startswith("line 3: formed") else ln.split("[")[1].split(",")[0]


def stale(f, self, case, atoms, budget, bounded):
    """(G02) The max review's tamper: drop the solution; in the replay close its leaf on a system checked with -1 >= 0
    more (a true certificate for that list), the atom popped off the same list after the check."""
    r = f(self, case, atoms, budget, bounded)
    if r is None:
        return r
    if self.cert and not bounded:
        S2 = list(self.case_atoms(case) + self.part_atoms(case) + atoms) + [({D.ONE: -1}, False)]
        D.C.check(S2, [("p", len(S2) - 1)], D.pay, keep=bool(self.pix))
        S2.pop()
        self.checked = S2
        if self.leaf_at:
            self.leaf_at[0].leaf(self.leaf_at[1], S2, self.leaf_at[2], self.leaf_at[3])
    return None


def pin(f, self, options, budget, what):
    """(B01, Argon review 2 01) In a refusal's replay, close each option by a ("pin", ..) split of two fresh naturals
    to (1/2, 0): pin_split checked only that the four atoms pin floats and that the parent's atoms with them hold, so the
    child (u = 1/2, a natural: rounded to -1 >= 0) closed and every claim was certified S008 or S011."""
    if not self.cert:
        return None   # the decision's "none" for every question; its replay closes each option by the pin
    u, v = ("n", 0), ("n", 1)
    new = [D.ge({u: 1, D.ONE: -D.Fraction(1, 2)}), D.ge({u: -1, D.ONE: D.Fraction(1, 2)}), D.ge({v: 1}), D.ge({v: -1})]
    self.trees = {}
    for i, (case, A) in enumerate(options):
        t = D.C.Tree(case, A, D.pay, self)
        self.trees[i] = t
        try:
            t.split(0, ("pin", new), [], [(case, new)])
        except D.C.Bad:
            continue   # the checker refused the pin: the tree stays open (options_closed: X001)
        base, tl = list(self.base(case)), list(self.tail(case, A, new))
        s1, k0 = base + list(A) + new + tl, len(base) + len(A)
        D.C.check(s1, [("p", k0), ("p", k0 + 1), ("r", 0), ("r", 1), ("d", 2), ("d", 3), ("c", [(1, 4), (1, 5)])], D.pay, keep=bool(self.pix))
        t.leaf(1, s1, list(A) + new, len(tl))
    return None


class Flip(dict):
    """(C01, review 3 01) A dict whose views lie inside cert.Tree.split only: it holds store (pickle and items() read
    that), and its keys, iteration and items by key there show view."""

    def __init__(self, store, view):
        super().__init__(store)
        self.view = dict(view)

    def lie(self):
        f = sys._getframe(2)
        while f is not None:
            if f.f_code.co_name == "split" and f.f_code.co_filename.endswith("cert.py"):
                return True
            f = f.f_back
        return False

    def keys(self):
        return self.view.keys() if self.lie() else super().keys()

    def __iter__(self):
        return iter(self.view) if self.lie() else super().__iter__()

    def __getitem__(self, k):
        return self.view[k] if self.lie() else super().__getitem__(k)


def views(f, self, options, budget, what):
    """(C01, review 3 01, its tamper) In a refusal's replay, close each option by a sign split whose first child adds
    an atom holding {1: -1} (-1 >= 0) but showing {1: 1} to the split's check, the negation of the second child's
    {1: -1}: both children are contradictions, so every claim was certified S008. cert.py now reads every value from the
    search as one exact copy (cert.exact): a dict subclass is Bad, X001."""
    if not self.cert:
        return None   # the decision's "none"; its replay closes each option by the split
    self.trees = {}
    for i, (case, A) in enumerate(options):
        t = D.C.Tree(case, A, D.pay, self)
        self.trees[i] = t
        kid0, kid1 = [(Flip({D.ONE: -1}, {D.ONE: 1}), False)], [({D.ONE: -1}, False)]
        try:
            ids = t.split(0, "sign", [], [(case, kid0), (case, kid1)])
        except D.C.Bad:
            continue   # the checker refused the split: the tree stays open (options_closed: X001)
        base = list(self.base(case))
        for node, kid in zip(ids, (kid0, kid1)):
            tl = list(self.tail(case, A, kid))
            s1 = base + list(A) + kid + tl
            D.C.check(s1, [("p", len(base) + len(A))], D.pay, keep=bool(self.pix))
            t.leaf(node, s1, list(A) + kid, len(tl))
    return None


def ranges(f, self, options, budget, what):
    """(D01, review 4 01, its tamper) In a refusal's replay, sign-split each option on a float the program need not
    have, the two children's atoms z <= 0 and z >= 0 each saying (.r) it lies in a range of the other sign, then
    binade-split each child on that range: every grandchild is a contradiction, and no point of the option is in one,
    so every claim was certified S008. The model now reads a range from the atoms' forms (decide.frange_in): X001."""
    if not self.cert:
        return None
    Z = ("z", "pix", "forge")

    def proof(sys1, parent, part):
        pz = parent[0][Z]
        fight = next(A for A in part if A[0].get(Z, 0) * pz < 0)
        J = next(v for v in fight[0] if v != D.ONE and v != Z)
        ja = next(A for A in part if A[0].get(J, 0) > 0 and A[0].get(D.ONE, 0) < 0 and Z not in A[0])
        ids = [sys1.index(parent), sys1.index(fight), sys1.index(ja)]
        return [("p", i) for i in ids] + [("c", [(D.Fraction(-fight[0][Z], pz), 0), (1, 1), (D.Fraction(-fight[0][J], ja[0][J]), 2)])]

    self.trees = {}
    for i, (case, A) in enumerate(options):
        t = D.C.Tree(case, A, D.pay, self)
        self.trees[i] = t
        neg, pos = D.RAtom(D.ge({Z: -1}), Z, (1, 0, 2)), D.RAtom(D.ge({Z: 1}), Z, (-1, 0, 2))
        try:
            ids = t.split(0, "sign", [], [(case, [neg]), (case, [pos])])
            for node, atom in zip(ids, (neg, pos)):
                parts = D.frange_split(Z, atom.r, None)
                kids = [(case, [atom] + part) for part in parts]
                for cid, (_, m), part in zip(t.split(node, ("model", "binade", (Z, None)), [atom], kids), kids, parts):
                    tl = list(self.tail(case, A, m))
                    s1 = list(self.base(case)) + list(A) + list(m) + tl
                    D.C.check(s1, proof(s1, atom, part), D.pay, keep=bool(self.pix))
                    t.leaf(cid, s1, list(A) + list(m), len(tl))
        except D.C.Bad:
            continue   # the checker refused a split: the tree stays open (options_closed: X001)
    return None


def mutate(f, kind):
    def g(*a, **k):
        if kind == "stale":
            return stale(f, *a, **k)
        if kind == "ranges":
            return ranges(f, *a, **k)
        if kind == "views":
            return views(f, *a, **k)
        if kind == "pin":
            return pin(f, *a, **k)
        if kind == "edit":
            for x in a:
                if isinstance(x, list) and x and all(isinstance(A, tuple) and len(A) == 2 and isinstance(A[0], dict) for A in x):
                    x.pop()
        if kind == "big":
            raise D.Big("mutant")
        if kind == "past":
            raise D.Past("mutant")
        r = f(*a, **k)
        if kind == "none":
            return None
        if kind == "empty":
            return type(r)() if isinstance(r, (list, tuple, dict)) else r
        if kind == "data":   # (H08) every PAtom returned gets inverted bounds of its mean (the max2 review's tamper)
            for P in (r if isinstance(r, (list, tuple)) else [r]):
                if isinstance(P, D.PAtom):
                    P.lo, P.hi = (P.hi if P.hi is not None else 0) + 1, (P.lo if P.lo is not None else 0) - 1
        if kind == "flip" and isinstance(r, bool):
            return not r
        if kind == "flip" and isinstance(r, (list, tuple)) and r:
            return r[:-1]
        if kind == "flip" and isinstance(r, dict) and r:
            return dict(list(r.items())[:-1])
        return r
    return g


def patch(monkeypatch, name, kind):
    for cls in (D.Model, D.Decide):
        if name in cls.__dict__ and getattr(S, name, None) is cls.__dict__[name]:
            monkeypatch.setattr(cls, name, mutate(cls.__dict__[name], kind))
            return
    w = mutate(getattr(S, name), kind)
    monkeypatch.setattr(S, name, w)
    if hasattr(D, name):
        monkeypatch.setattr(D, name, w)


@pytest.fixture(scope="module")
def progs(tmp_path_factory):
    out = []
    for i, (table, c) in enumerate(CLAIMS):
        p, h = tsv(tmp_path_factory.mktemp(f"m{i}"), "t.tsv", table)
        prog = f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {c}\n"
        out.append((prog, p, code(run(prog, [p])[1])))
    return out


def test_the_claims_cover_each_verdict(progs):
    assert [b for _, _, b in progs] == ["formed", "S008", "S008", "R013", "S008", "formed", "formed", "formed", "formed", "formed"]


@pytest.mark.parametrize("name, kind", MUTANTS)
def test_a_search_mutant_gives_x001_r013_or_the_same_verdict(progs, monkeypatch, name, kind):
    patch(monkeypatch, name, kind)
    got = [(b, code(run(prog, [p])[1])) for prog, p, b in progs]
    assert all(m in (b, "X001", "R013") for b, m in got), got


def test_the_mutants_are_not_vacuous(progs, monkeypatch):
    """A search that answers "none" to everything turns each form into X001 (its "none" fails its check)."""
    patch(monkeypatch, "find_options", "none")
    got = [code(run(prog, [p])[1]) for prog, p, b in progs if b == "formed"]
    assert got and all(m == "X001" for m in got), got


def test_a_leaf_on_a_system_edited_after_its_check_is_x001(tmp_path, monkeypatch):
    """(G02, Opus 5.5 max review 02, its repro) search.py only: the first exceeds() question drops its solutions and its
    replay closes each leaf on a system checked with one atom more, then edited back. cert.py kept checked systems by
    object identity, so the claim, which holds on its own table, was refused S011 with its certificates checked;
    a checked system is now kept by its forms, so the edited one closes nothing: X001."""
    T = {"id": None, "on": False}
    real_find, real_one = D.Model.find_options, D.Model.one_solve1

    def find_options(self, options, budget, what):
        if what == "exceeds()" and T["id"] is None:
            T["id"] = id(options)
        T["on"] = id(options) == T["id"]
        try:
            return real_find(self, options, budget, what)
        finally:
            T["on"] = False

    def one_solve1(self, case, atoms, budget, bounded):
        return stale(real_one, self, case, atoms, budget, bounded) if T["on"] else real_one(self, case, atoms, budget, bounded)

    p, h = tsv(tmp_path, "t.tsv", "g\na\na\nb\n")
    prog = f'file f = sha256:{h}\nlet t = tsv(f)\nclaim exceeds(count(where(t, eq(1, "a"))), c = 1)\n'
    assert code(run(prog, [p])[1]) == "formed"
    monkeypatch.setattr(D.Model, "find_options", find_options)
    monkeypatch.setattr(D.Model, "one_solve1", one_solve1)
    out = run(prog, [p])[1]
    assert code(out) == "X001" and "has not shown to have no point (as it is now)" in out, out


def test_a_read_limit_reason_from_a_point_that_is_not_one_is_x001(tmp_path, monkeypatch):
    """(G02b, Opus 5.5 max review 02, second route, its repro) search.py only: find_options raises Past in the first pass
    (so the read limit is modelled) and, in the replay without the limit, answers a point it did not find. The reason
    "it holds only by the read limit" was taken from that point; it is now taken only from a point the trusted model
    confirms past the limit (Model.past_limit), and one it does not confirm is the search's fault: X001."""
    real = D.Model.find_options

    def find_options(self, options, budget, what):
        if not D.RB[0] and options:
            raise D.Past("tampered: a Past in the first pass")
        if self.cert and not self.rb and options:
            return (0, {})
        return real(self, options, budget, what)

    p, h = tsv(tmp_path, "t.tsv", "g\na\nb\n")
    prog = f"file f = sha256:{h}\nlet t = tsv(f)\nclaim atleast(rows(t), c = 0)\n"
    out = run(prog, [p])[1]
    assert code(out) == "S008" and "read limit" not in out, out
    monkeypatch.setattr(D.Model, "find_options", find_options)
    out = run(prog, [p])[1]
    assert code(out) == "X001" and "not one past it" in out, out


def codes(text):
    """Each statement's verdict code, in order."""
    return ["formed" if ": formed" in x else x.split("[")[1].split(",")[0] for x in text.split("\n") if x.startswith("line ")]


def test_a_builder_giving_two_inputs_for_one_point_cannot_form(tmp_path, monkeypatch):
    """(A07, Argon review 07, its repro) build.py is untrusted, and Decide called its bytes_of once for the statement and
    again for it without the part (or with its file slot varied), so a builder giving two inputs for one point made
    an idle part bear: build.py alone turned an idle condition's R013 into a form, and build.py with search.py turned
    a repeated condition and a cancelling file (SPEC 4.3 R3) into forms. A W2 pair now reads one input: X001."""
    real = D.Model.bytes_of
    p, h = tsv(tmp_path, "f.csv", "h1,h2\np,q\n")
    l3 = "x" * 1000 + ",a,b"
    prog = f'file f = sha256:{h}\nclaim atmost(difference(rows(csv(f)), count(where(tsv(f), ne(1, "y,z"), ne(1, "{l3}")))), c = 69999)\n'
    assert codes(run(prog, [p])[1]) == ["R013"]
    flip = [0]

    def bytes_a(self, case, x, seed=0):   # build.py alone: an input past the read limit becomes 70,000 rows, then none
        out = real(self, case, x, seed)
        for k, v in list(out.items()):
            if isinstance(v, bytes) and len(v) > 67108864:
                flip[0] ^= 1
                out[k] = b"h1,h2\n" + b"y,z\n" * 70000 if flip[0] else b"h1,h2\n"
        return out
    monkeypatch.setattr(D.Model, "bytes_of", bytes_a)
    assert codes(run(prog, [p])[1]) in (["X001"], ["R013"])
    monkeypatch.undo()
    pa, ha = tsv(tmp_path, "a.tsv", "c1\n1\n")
    pb, hb = tsv(tmp_path, "b.tsv", "c1\n2\n")
    prog = (f"file a = sha256:{ha}\nfile b = sha256:{hb}\n"
            'claim exceeds(count(where(tsv(a), eq(1, "1"), eq(1, "1"))), c = 0)\n'
            "claim exceeds(difference(sum(tsv(a), 1), difference(sum(tsv(a), 1), sum(tsv(b), 1))), c = 0)\n")
    assert codes(run(prog, [pa, pb])[1]) == ["S008", "S008"]
    find = D.Model.find_options

    def find_b(self, opts, budget, what):   # search.py: a made-up point for every W2 question
        r = find(self, opts, budget, what)
        return (0, {("z", "forge"): 1}) if r is None and not self.cert and opts else r

    def bytes_b(self, case, x, seed=0):   # build.py: one store, then another, at that point
        if isinstance(x, dict) and ("z", "forge") in x:
            flip[0] ^= 1
            return {s: (b"c1\n2\n" if flip[0] else b"c1\n-2\n") if s == "b" else (b"c1\n1\n" if flip[0] else b"c1\n") for s in case if s is not None}
        return real(self, case, x, seed)
    monkeypatch.setattr(D.Model, "find_options", find_b)
    monkeypatch.setattr(D.Model, "bytes_of", bytes_b)
    assert all(c in ("X001", "R013", "S008") for c in codes(run(prog, [pa, pb])[1]))


def test_a_split_on_a_variable_the_model_does_not_have_is_x001(tmp_path, monkeypatch):
    """(A01, Argon review 01, its repro) search.py only: each option's root split by ("model", "spell", (z, 0)) with z a
    byte range's number of 1011 bytes no slot reads; Model.disjunction stated it as no case at all, so every option
    closed with no leaf and a formed claim was a certified S008. A spelling split is now only of one of the model's
    number()-read ranges holding a number in the case: X001."""
    p, h = tsv(tmp_path, "t.tsv", "g\tx\nA\t1\nA\t2\nB\t3\n")
    prog = f'file f = sha256:{h}\nlet t = tsv(f)\nclaim exceeds(count(where(t, eq(1, "A"))), c = 1)\nclaim sum(t, 2)\n'
    assert codes(run(prog, [p])[1]) == ["formed", "formed"]

    def find_options(self, options, budget, what):
        if self.cert:
            self.trees = {}
            for i, (case, A) in enumerate(options):
                t = D.C.Tree(case, A, D.pay, self)
                t.split(0, ("model", "spell", (("z", "raw", "", 0, 1011), 0)), [], [])
                self.trees[i] = t
        return None
    monkeypatch.setattr(D.Model, "find_options", find_options)
    assert codes(run(prog, [p])[1]) == ["X001", "X001"]


def test_a_binade_split_of_a_natural_or_of_one_binade_is_bad(tmp_path, monkeypatch):
    """(A01, Argon review 01) Model.disjunction's binade split tested only the tag at index 1, so a natural variable of a
    slot named pix (("n", "pix", ..)) was split into floats (no odd integer above 2^53), and a one-binade range raised
    ValueError in frange_split; both are now cert.Bad (X001)."""
    got = []
    real = D.Model.find_options

    def find_options(self, options, budget, what):
        for z, more in ((("n", "pix", "size"), []), (("z", "pix", "f"), D.frange(("z", "pix", "f"), 1, 5, 5))):
            try:
                self.disjunction("binade", (z, None), options[0][0] if options else {}, [], more)
                got.append("stated")
            except D.C.Bad:
                got.append("Bad")
            except Exception as e:
                got.append(type(e).__name__)
        return real(self, options, budget, what)
    p, h = tsv(tmp_path, "t.tsv", "g\na\na\nb\n")
    monkeypatch.setattr(D.Model, "find_options", find_options)
    run(f'file f = sha256:{h}\nlet t = tsv(f)\nclaim exceeds(count(where(t, eq(1, "a"))), c = 1)\n', [p])
    assert got and set(got) == {"Bad"}, got


def test_an_option_edited_between_its_splits_and_its_leaves_is_x001(tmp_path, monkeypatch):
    """(A02, Argon review 02, its repro) search.py only: append a PAtom of no piece (lo = 1 > hi = 0) to an option's own
    atoms, split by ("prange", P) (P is then "the option's", so its facts were trusted), pop it and close the child on its
    contradictory atoms: the leaf's and options_closed's fingerprints matched again, and every claim formed. Tree.split
    now checks the option's atoms by contents too: X001."""
    p, h = tsv(tmp_path, "t.tsv", "g\tx\nA\t1\nA\t2\nB\t3\n")
    prog = f'file f = sha256:{h}\nlet t = tsv(f)\nclaim exceeds(count(where(t, eq(1, "A"))), c = 1)\nclaim sum(t, 2)\n'

    def find_options(self, options, budget, what):
        if self.cert:
            self.trees = {}
            u, fk = ("z", "cell", "", 0, 1), ("pk", "", (), 1, 0, 0)
            P = D.PAtom(u, {}, {D.ONE: 1}, lo=1, hi=0, a0=0, key=fk)
            kid = [D.RAtom(D.ge({D.ONE: 1}), fk, (0, None, None)), D.RAtom(D.ge({u: 1, D.ONE: -1}), fk, (0, None, None)),
                   D.RAtom(D.ge({u: -1}), fk, (0, None, None))]
            for i, (case, A) in enumerate(options):
                t = D.C.Tree(case, A, D.pay, self)
                A.append(P)
                try:
                    t.split(0, ("prange", P), [], [(case, kid)])
                finally:
                    A.pop()
                base, tl = list(self.base(case)), list(self.tail(case, A, kid))
                sys1, k0 = base + list(A) + kid + tl, len(base) + len(A)
                D.C.check(sys1, [("p", k0 + 1), ("p", k0 + 2), ("c", [(1, 0), (1, 1)])], D.pay)
                t.leaf(1, sys1, list(A) + kid, len(tl))
                self.trees[i] = t
        return None
    monkeypatch.setattr(D.Model, "find_options", find_options)
    assert codes(run(prog, [p])[1]) == ["X001", "X001"]


def test_a_pin_of_variables_that_are_not_floats_is_x001(tmp_path, monkeypatch):
    """(B01, Argon review 2 01, its repro) search.py only. cert.pin_split (fwin's pair of floats pinned to one point)
    did not check the pinned variables' kind: (a) two fresh naturals pinned to (1/2, 0) closed every option (the child
    rounds u = 1/2 to a contradiction), so a formed claim was certified S008; (b) a byte range's number pinned to 7/2 (a
    point no input has) and then split by the model's spellings (z <= 3 or z >= 4, true on inputs only) closed exceeds(),
    so a formed claim was certified S011. Now each pinned variable must be a pixdim of the parent's atoms: X001."""
    p, h = tsv(tmp_path, "f.tsv", "c1\na\nb\n")
    r, hr = tsv(tmp_path, "r.bin", "5")
    prog_a = f"file f = sha256:{h}\nclaim exceeds(rows(tsv(f)), c = 1)\n"
    prog_b = f"file r = sha256:{hr}\nclaim exceeds(number(bytes(r, 0, 1)), c = 3)\n"
    assert "line 2: formed" in run(prog_a, [p])[1] and "line 2: formed" in run(prog_b, [r])[1]
    z, z2 = ("z", "raw", "r", 0, 1), ("z", "dummy", 0, 0)
    real = D.Model.find_options

    def find_b(self, options, budget, what):
        if what != "exceeds()" or not options or options[0][1][-1][0].get(z, 0) <= 0:
            return real(self, options, budget, what)
        if not self.cert:
            return None   # the decision's "none" for the option z > 3; its replay closes it by the pin and the spellings
        new = [D.ge({z: 1, D.ONE: -D.Fraction(7, 2)}), D.ge({z: -1, D.ONE: D.Fraction(7, 2)}), D.ge({z2: 1}), D.ge({z2: -1})]
        self.trees = {}
        for i, (case, A) in enumerate(options):
            t = D.C.Tree(case, A, D.pay, self)
            self.trees[i] = t
            t.split(0, ("pin", new), [], [(case, new)])
            kids = [(case, new + b) for b in self.spell_cases(z, D.Fraction(7, 2))]
            for cid, (_, m) in zip(t.split(1, ("model", "spell", (z, D.Fraction(7, 2))), new, kids), kids):
                base, tl = list(self.base(case)), list(self.tail(case, A, m))
                s1, k0 = base + list(A) + m + tl, len(base) + len(A)
                lo = z in m[4][0] and m[4][0][z] < 0
                D.C.check(s1, [("p", k0 if lo else k0 + 1), ("p", k0 + 4), ("c", [(1, 0), (1, 1)])], D.pay, keep=bool(self.pix))
                t.leaf(cid, s1, list(A) + m, len(tl))
        return None
    patch(monkeypatch, "find_options", "pin")
    out_a = run(prog_a, [p])[1]
    monkeypatch.setattr(D.Model, "find_options", find_b)
    out_b = run(prog_b, [r])[1]
    assert "line 2: refused [X001" in out_a and "line 2: refused [X001" in out_b, (out_a, out_b)


def test_a_search_that_writes_the_models_state_is_x001(tmp_path, monkeypatch):
    """(B07, Argon review 2 07 and 06, their repros) search.py only. cert.py read the model's piece facts, base, tail and
    disjunctions through the live Model the search runs on: (a) a search that set Model.piece_facts on the instance
    around a ("prange", P) split of a contradictory PAtom (lo = 1 > hi = 0, never in the option) and restored it had the
    split trusted, so formed claims were certified S008; (b) a search that set Model.rb in check()'s first pass gave
    the read limit's atoms to a pass without the limit. cert.py now calls the model's methods by its class
    (cert.mcall), and Model.find compares the model's own attributes before and after the search: X001."""
    p, h = tsv(tmp_path, "f.tsv", "g\tx\nA\t1\nA\t2\nB\t3\n")
    prog = f'file f = sha256:{h}\nlet t = tsv(f)\nclaim exceeds(count(where(t, eq(1, "A"))), c = 1)\nclaim sum(t, 2)\n'
    assert run(prog, [p])[1].count("formed") == 2
    real = D.Model.find_options

    def forge(self, options, budget, what):
        if not self.cert:
            return None
        self.trees = {}
        u, fk = ("z", "cell", "", 0, 1), ("pk", "", (), 1, 0, 0)
        P = D.PAtom(u, {}, {D.ONE: 1}, lo=1, hi=0, a0=0, key=fk)
        kid = [D.RAtom(D.ge({D.ONE: 1}), fk, (0, None, None)), D.RAtom(D.ge({u: 1, D.ONE: -1}), fk, (0, None, None)),
               D.RAtom(D.ge({u: -1}), fk, (0, None, None))]
        fact = (u, (), ((D.ONE, 1),), 1, 0, 0, fk)
        pf = self.piece_facts
        for i, (case, A) in enumerate(options):
            t = D.C.Tree(case, A, D.pay, self)
            self.trees[i] = t
            self.piece_facts = lambda c, _r=pf: _r(c) | {fact}
            try:
                t.split(0, ("prange", P), [], [(case, kid)])
            except D.C.Bad:
                continue
            finally:
                del self.piece_facts
            base, tl = list(self.base(case)), list(self.tail(case, A, kid))
            s1, k0 = base + list(A) + kid + tl, len(base) + len(A)
            D.C.check(s1, [("p", k0 + 1), ("p", k0 + 2), ("c", [(1, 0), (1, 1)])], D.pay, keep=bool(self.pix))
            t.leaf(1, s1, list(A) + kid, len(tl))
        return None
    monkeypatch.setattr(D.Model, "find_options", forge)
    out = run(prog, [p])[1]
    assert out.count("[X001") == 2 and "[S008" not in out, out

    def rb(self, options, budget, what):
        self.rb = True
        return real(self, options, budget, what)
    monkeypatch.setattr(D.Model, "find_options", rb)
    out = run(prog, [p])[1]
    assert "[X001" in out and "the model's own state" in out and "[S008" not in out, out


def test_a_split_on_an_atom_whose_views_lie_is_x001(tmp_path, monkeypatch):
    """(C01, review 3 01, its repro) search.py only: a sign split whose first child's atom is a dict subclass holding
    -1 >= 0 whose keys and items by key inside Tree.split show 1 >= 0, the negation of the second child's -1 >= 0. The
    split's check read the atom through its own methods, check() and the leaf's fingerprints through the built-ins', so
    both children closed and two formed claims were certified S008. cert.py now reads every value from the search as
    one copy of exact types it makes itself (cert.exact): X001."""
    p, h = tsv(tmp_path, "f.tsv", "g\tx\nA\t1\nA\t2\nB\t3\n")
    prog = f'file f = sha256:{h}\nlet t = tsv(f)\nclaim exceeds(count(where(t, eq(1, "A"))), c = 1)\nclaim sum(t, 2)\n'
    assert run(prog, [p])[1].count("formed") == 2
    patch(monkeypatch, "find_options", "views")
    out = run(prog, [p])[1]
    assert out.count("[X001") == 2 and "[S008" not in out, out


def test_a_binade_split_of_a_range_its_atoms_do_not_state_is_x001(tmp_path, monkeypatch):
    """(D01, review 4 01, its repro) search.py only: a sign split adds z <= 0 and z >= 0 (forms checked) whose .r say
    the opposite sign, then a binade split of each child on that .r (frange_of): each grandchild is a contradiction and
    holds no point of the option, so two formed claims were certified S008. The model now reads a float's range from
    the parent's atoms' forms (decide.frange_in), never their .r: here none is stated, so the binade split is not the
    model's disjunction: X001."""
    p, h = tsv(tmp_path, "f.tsv", "g\tx\nA\t1\nA\t2\nB\t3\n")
    prog = f'file f = sha256:{h}\nlet t = tsv(f)\nclaim exceeds(count(where(t, eq(1, "A"))), c = 1)\nclaim sum(t, 2)\n'
    assert run(prog, [p])[1].count("formed") == 2
    patch(monkeypatch, "find_options", "ranges")
    out = run(prog, [p])[1]
    assert out.count("[X001") == 2 and "[S008" not in out, out
