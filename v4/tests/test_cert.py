"""cert.py, the checker of the exact decision's certificates (BB's call 28 Oct 2026 18:05; partb/CERT/PLAN.md): a
valid certificate checks, a tampered one is rejected, and a refusal whose certificate does not check is X001."""
from fractions import Fraction

import pytest

from helpers import run, tsv
from reality4 import cert as C
from reality4 import decide as D

N, M, Z = ("n", "s", "a"), ("n", "s", "b"), ("z", "y", "s")


def pay(n):
    pay.spent += n
pay.spent, pay.left = 0, lambda: 10 ** 6


def ok(system, log):
    return C.check(system, log, pay) is None


def bad(system, log):
    with pytest.raises(C.Bad):
        C.check(system, log, pay)
    return True


def test_a_farkas_combination_checks_and_a_tampered_one_does_not():
    sys_ = [({N: 1, 1: -1}, False), ({N: -1}, False)]   # n >= 1, n <= 0
    assert ok(sys_, [("p", 0), ("p", 1), ("c", [(1, 0), (1, 1)])])
    assert bad(sys_, [("p", 0), ("p", 1), ("c", [(1, 0), (2, 1)])])    # multipliers changed: n - 1 left
    assert bad(sys_, [("p", 0), ("p", 1), ("c", [(-1, 0), (1, 1)])])   # a negative multiplier
    assert bad(sys_, [("p", 0), ("p", 2), ("c", [(1, 0), (1, 1)])])    # no such premise
    assert bad(sys_[:1] + [({N: -1, 1: 1}, False)], [("p", 0), ("p", 1), ("c", [(1, 0), (1, 1)])])   # a system with a point
    assert bad(sys_, [("p", 0), ("p", 1)])   # no contradiction at the end


def test_strictness_counts():
    sys_ = [({Z: 1}, True), ({Z: -1}, False)]   # z > 0, z <= 0
    assert ok(sys_, [("p", 0), ("p", 1), ("c", [(1, 0), (1, 1)])])
    assert bad([({Z: 1}, False), ({Z: -1}, False)], [("p", 0), ("p", 1), ("c", [(1, 0), (1, 1)])])   # z = 0 is a point


def test_rounding_needs_natural_variables():
    sys_ = [({N: 2, 1: -1}, True), ({N: -2, 1: 2}, True)]   # 1/2 < n < 1: no natural n
    log = [("p", 0), ("p", 1), ("r", 0), ("r", 1), ("c", [(1, 2), (1, 3)])]
    assert ok(sys_, log)
    zs = [({Z: 2, 1: -1}, True), ({Z: -2, 1: 2}, True)]   # z = 3/4 is a point
    assert bad(zs, log)
    assert bad([({N: 1}, False)], [("nat", Z)])   # z is not a natural


def test_division_needs_an_integral_line():
    sys_ = [({N: 3, 1: -1}, False), ({N: -3, 1: 2}, False)]   # 1/3 <= n <= 2/3
    assert ok(sys_, [("p", 0), ("p", 1), ("d", 0), ("d", 1), ("c", [(1, 2), (1, 3)])])   # n >= 0 + 1, n <= 0
    assert bad([({Z: 3, 1: -1}, False), ({Z: -3, 1: 2}, False)], [("p", 0), ("p", 1), ("d", 0), ("d", 1), ("c", [(1, 2), (1, 3)])])
    assert bad([({N: Fraction(3, 2), 1: -1}, False)], [("p", 0), ("d", 0)])


def test_the_integer_step_end():
    sys_ = [({N: 2, M: -2, 1: -1}, False), ({N: -2, M: 2, 1: 1}, False)]   # 2n = 2m + 1
    assert ok(sys_, [("p", 0), ("p", 1), ("int", [0, 1])])
    assert bad([({N: 1, M: -1, 1: -1}, False), ({N: -1, M: 1, 1: 1}, False)], [("p", 0), ("p", 1), ("int", [0, 1])])   # n = m + 1
    assert bad([({Z: 2, 1: -1}, False)], [("p", 0), ("int", [0])])   # a rational variable is not the integer step's


T = "g\tx\ty\nA\t1\t2\nB\t3\t0.5\nA\t-2\t4\n"
S008 = "atmost(difference(mean(where(t, le(2, c = 1)), 2), mean(where(t, ge(2, c = 1)), 2)), c = 0)"


def claim(tmp_path, c):
    p, h = tsv(tmp_path, "f.tsv", T)
    _, text = run(f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {c}\n", [p])
    return text


def test_a_refusal_carries_checked_certificates(tmp_path):
    before = sum(D.CERTS.values())
    out = claim(tmp_path, S008)
    assert "[S008" in out and "decided exactly" in out, out
    assert sum(D.CERTS.values()) > before


@pytest.mark.parametrize("how", ["multiplier", "premise"])
def test_a_tampered_certificate_is_x001(tmp_path, monkeypatch, how):
    needed = D.Log.needed

    def tampered(self):
        steps = needed(self)
        for i in range(len(steps) - 1, -1, -1):
            if how == "multiplier" and steps[i][0] == "c" and len(steps[i][1]) > 1:
                steps[i] = ("c", [(u * 2 if k == 0 else u, j) for k, (u, j) in enumerate(steps[i][1])])
                break
            if how == "premise" and steps[i][0] == "p":
                steps[i] = ("p", steps[i][1] + 1)
                break
        return steps
    monkeypatch.setattr(D.Log, "needed", tampered)
    out = claim(tmp_path, S008)
    assert "[X001" in out and "certificate" in out, out


def test_a_tree_needs_every_node_closed():
    t = C.Tree("case", [])
    a, b = t.split(0, "sign", [], [("case", [({Z: 1}, False)]), ("case", [({Z: -1}, False)])])
    s1 = [({Z: 1}, False), ({Z: -1, 1: -1}, False)]   # z >= 0, z <= -1
    with pytest.raises(C.Bad):
        t.leaf(a, s1, [({Z: 1}, False)], 1)   # not checked yet
    assert ok(s1, [("p", 0), ("p", 1), ("c", [(1, 0), (1, 1)])])
    t.leaf(a, s1, [({Z: 1}, False)], 1)
    with pytest.raises(C.Bad):
        t.done()   # b is open
    s2 = [({Z: -1}, False), ({Z: 1, 1: -1}, False)]   # z <= 0, z >= 1
    assert ok(s2, [("p", 0), ("p", 1), ("c", [(1, 0), (1, 1)])])
    t.leaf(b, s2, [({Z: -1}, False)], 1)
    t.done()
    with pytest.raises(C.Bad, match="does not know"):   # (L6) no named lemma: a rule the checker does not know is Bad
        C.Tree("case", []).split(0, "a named lemma", [], [("case", [])])
    with pytest.raises(C.Bad):
        t.split(a, "sign", [], [("case", [({Z: 1}, False)]), ("case", [({Z: 1}, False)])])   # not F and -F
    with pytest.raises(C.Bad):
        C.Tree("case", []).leaf(0, s1, [({Z: -1}, False)], 1)   # its system lacks the node's atom


def test_a_no_without_its_certificate_is_x001(tmp_path, monkeypatch):
    one = D.Model.one_solve2

    def skip(self, atoms, case, budget, bounded, held, log):   # a replay that answers "none" once without a checked leaf
        if self.cert and not bounded and not skip.done:
            skip.done = True
            return None
        return one(self, atoms, case, budget, bounded, held, log)
    skip.done = False
    monkeypatch.setattr(D.Model, "one_solve2", skip)
    out = claim(tmp_path, S008)
    assert "[X001" in out and "certificate of no input" in out, out


FORMS = "atmost(difference(mean(where(t, le(2, c = 1)), 2), mean(where(t, ge(2, c = 1)), 2)), c = -1)"


def test_a_form_never_checks_a_certificate(tmp_path, monkeypatch):
    """C4: certificates are built and checked only for a refusal, after its decision; a form's search builds none."""
    def never(*a, **k):
        raise AssertionError("a certificate checked for a form")
    monkeypatch.setattr(C, "check", never)
    monkeypatch.setattr(D.Decide, "certify", never)
    out = claim(tmp_path, FORMS)
    assert "formed" in out and "refused" not in out, out


def test_a_wrong_none_is_x001_on_its_replay(tmp_path, monkeypatch):
    """A search that wrongly finds no input (here: every unbounded system answered "none" in the decision) refuses; the
    replay with certificates finds the input, so the refusal is X001, not S008."""
    one = D.Model.one_solve2

    def wrong(self, atoms, case, budget, bounded, held, log):
        return None if not self.cert and not bounded else one(self, atoms, case, budget, bounded, held, log)
    monkeypatch.setattr(D.Model, "one_solve2", wrong)
    out = claim(tmp_path, FORMS)
    assert "[X001" in out and "replayed" in out, out


def test_a_refusal_past_the_checking_bound_is_r013(tmp_path, monkeypatch):
    check = C.check
    monkeypatch.setattr(C, "check", lambda system, log, pay, keep=False: (pay(D.W.MAX_WITNESS_STEPS + 1), check(system, log, pay, keep))[1])
    out = claim(tmp_path, S008)
    assert "[R013" in out and "checking the refusal's certificate exceeded the bound" in out, out


def test_a_refusal_whose_certificate_cannot_be_kept_is_r013(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "kept_bytes", lambda x: D.MEM_STEPS * D.STEP_BYTES)
    out = claim(tmp_path, S008)
    assert "[R013" in out and "could not be kept" in out, out


def test_an_option_without_its_tree_is_x001(tmp_path, monkeypatch):
    closed = C.options_closed
    monkeypatch.setattr(C, "options_closed", lambda options, trees, f0, pay: closed(options, dict(list(trees.items())[1:]), f0, pay))
    out = claim(tmp_path, S008)
    assert "[X001" in out and "certificate of no input" in out, out


def test_equal_shares_are_recomputed():
    A, B = ("n", "s", "A"), ("n", "s", "B")
    S1, B1 = {A: 1}, {A: 1, B: 1}                 # A / (A + B)
    assert C.shares_zero(S1, B1, {A: 2}, {A: 2, B: 2}, {A: 1}, [], pay) is None   # 2A / (2A + 2B): equal everywhere
    with pytest.raises(C.Bad):
        C.shares_zero(S1, B1, {A: 1}, {A: 1, B: 2}, {A: 1}, [], pay)   # equal at x0 (B = 0), not at B = 1
    assert C.shares_zero(S1, B1, {A: 1}, {A: 1, B: 2}, {A: 1}, [({B: -1}, False)], pay) is None   # B held at 0


SHARE = 'share(where(t, eq(1, "B"), ne(1, "007")))'


def test_a_share_refusal_carries_its_check(tmp_path, monkeypatch):
    before = D.CERTS.get("shares", 0)
    out = claim(tmp_path, SHARE)
    assert "[S008" in out and "W2" in out, out
    assert D.CERTS.get("shares", 0) > before
    sc = D.Decide.shares_cert
    monkeypatch.setattr(D.Decide, "shares_cert", lambda self, S1, B1, S2, B2, x0, atoms, ys, *ca: sc(self, S1, B1, {**S2, ("n", "s", "x"): 1}, B2, x0, atoms, ys, *ca))
    out = claim(tmp_path, SHARE)
    assert "[X001" in out and "equal shares" in out, out


def test_a_means_rows_split_is_checked():
    """prange (SPEC-EXACT 3.5): P's facts trusted (S = mu·N, lo <= mu <= hi); range atoms, McCormick products and the
    cover checked; a tampered product, a missing child or a wrong sign is rejected."""
    mu, n, s = ("z", "mu"), ("n", "s", "A"), ("z", "S")
    P = D.PAtom(mu, {s: 1}, {n: 1}, lo=Fraction(-1), hi=Fraction(3))
    root = [P]
    first = [D.prange(P, 1, None, g) for g in (-1, 1)]
    assert C.prange_split(P, [], root, first, pay) is None
    with pytest.raises(C.Bad):
        C.prange_split(P, [], root, first[1:], pay)   # mu's sign not covered
    par = first[1]   # N >= 1, mu >= 0; split at the solution's N = 4
    kids = [[A for A in par if getattr(A, "z", None) != P.key] + D.prange(P, *r) for r in [(5, None, 1), (1, 3, 1), (4, 4, 0)]]
    assert C.prange_split(P, par, root, kids, pay) is None
    with pytest.raises(C.Bad):
        C.prange_split(P, par, root, kids[:2], pay)   # N = 4 in no child
    with pytest.raises(C.Bad):
        C.prange_split(P, par, root, [kids[0], [A for A in par if getattr(A, "z", None) != P.key] + D.prange(P, 1, 3, -1), kids[2]], pay)   # sign changed
    t = [D.RAtom(({**F, ("z", "S"): F.get(("z", "S"), 0) + 1}, st), A.z, A.r) if i == len(kids[1]) - 1 else A for i, A in enumerate(kids[1]) for F, st in [A]]
    with pytest.raises(C.Bad):
        C.prange_split(P, par, root, [kids[0], t, kids[2]], pay)   # a McCormick atom tampered


def test_a_means_first_rows_split_starts_at_its_own_a0():
    """(B06, Argon review 2 06) The first rows split of the option's own PAtom took its a0 from the children: a split
    over [1000, ...) of a P with a0 = 1 was accepted, leaving N in [1, 999] uncovered (with the read limit's atoms the
    children closed and search.py alone certified a formed claim S008). Now a0 is at most P.a0; a lower one covers more."""
    mu, n, s = ("z", "mu"), ("n", "s", "A"), ("z", "S")
    P = D.PAtom(mu, {s: 1}, {n: 1}, lo=Fraction(-1), hi=Fraction(3))
    assert P.a0 == 1
    for a0 in (2, 1000):
        with pytest.raises(C.Bad):
            C.prange_split(P, [], [P], [D.prange(P, a0, None, g) for g in (-1, 1)], pay)
    assert C.prange_split(P, [], [P], [D.prange(P, 0, None, g) for g in (-1, 1)], pay) is None


def test_what_a_check_keeps_counts_each_object_once():
    """C4: find's options share their cases; what a refusal's check keeps is counted once per object (pn472: 7,190
    options counted per option were 1.35 GB and dropped its S008 W2 to R013; once, 16.8 MB)."""
    case, A = {None: {("n", "s", "a"): Fraction(1, 3)}}, [({("n", "s", "a"): 1, 1: -1}, False)]
    one = D.kept_bytes([(case, A)])
    assert D.kept_bytes([(case, A)] * 1000) <= one + 1000 * 80
    assert D.kept_bytes([({None: dict(case[None])}, [(dict(A[0][0]), False)]) for _ in range(10)]) > 5 * one   # distinct objects each count


GN = "group\tsite\tage\tscore\nA\ts1\t30\t2\nB\ts2\t41\t5\nP\ts1\t-4.5\t2\nB\ts1\t7\t0.5\nZ\ts2\t12\t9\n"
NEST = 'difference(mean(t, "age"), difference(mean(where(t, ne("site", "s1"), ge("age", c = 12.5)), "age"), mean(where(t, ne("site", "s1"), ge("age", c = 12.5)), "age")))'
PIECE = 'difference(min(where(t, eq("site", "s2"), ne("site", "s9")), "score"), sum(where(t, ne("group", "Z")), "score"))'


def gn(tmp_path, c):
    p, h = tsv(tmp_path, "gn.tsv", GN)
    _, text = run(f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {c}\n", [p])
    return text


def test_a_nest_split_is_the_models_disjunction(tmp_path, monkeypatch):
    """L1 (BB's call 18:05): a mean against its classes' ends (nest, 3.5) is no longer a named lemma: each child is the
    parent within one case of the model's own disjunction (Model.disjunction), checked by cert.cover; a child with an
    atom the model does not state, or a missing case, is X001."""
    D.CERTS.clear()
    out = gn(tmp_path, NEST)
    assert "[S008" in out and D.CERTS.get("split: nest") and not any(k.startswith("lemma") for k in D.CERTS), (out, D.CERTS)
    real = D.Model.disjunction

    def shifted(self, name, args, case, atoms, more):
        cs, need = real(self, name, args, case, atoms, more)
        if name == "nest":
            (c0, A0), *rest = cs
            cs = [(c0, [({**A0[0][0], 1: A0[0][0].get(1, 0) + 1}, A0[0][1])] + A0[1:])] + rest
        return cs, need
    monkeypatch.setattr(D.Model, "disjunction", shifted)
    out = gn(tmp_path, NEST)
    assert "[X001" in out and "nest split" in out, out
    monkeypatch.setattr(D.Model, "disjunction", lambda self, *a: (lambda cs, need: (cs[:-1], need) if a[0] == "nest" else (cs, need))(*real(self, *a)))
    out = gn(tmp_path, NEST)
    assert "[X001" in out and "children for the model's" in out, out


def test_a_pieces_sign_by_its_ends_is_shown(tmp_path, monkeypatch):
    """L1: a piece's sign taken from its end's sign (3.5) is shown: the parent with sg·mu < 0 has no point (a checked
    leaf, kept by the tree); a proof skipped, or of another atom, is X001."""
    D.CERTS.clear()
    out = gn(tmp_path, PIECE)
    assert "[S008" in out and D.CERTS.get("split: prange shown") and not any(k.startswith("lemma") for k in D.CERTS), (out, D.CERTS)
    monkeypatch.setattr(D.Model, "prove", lambda self, case, atoms, budget, raw=False: self.base(case) + atoms)   # not shown
    out = gn(tmp_path, PIECE)
    assert "[X001" in out and "not shown" in out, out
    real = D.Model.prove
    monkeypatch.setattr(D.Model, "prove", lambda self, case, atoms, budget, raw=False: real(self, case, atoms[:-1] + [D.gt({**atoms[-1][0], 1: -1})], budget, raw))
    out = gn(tmp_path, PIECE)
    assert "[X001" in out, out


class FakeModel:
    def __init__(self, D_, need=()):
        self.D, self.need = D_, list(need)

    def disjunction(self, name, args, case, atoms, more):
        return self.D, self.need

    def same_case(self, a, b):
        return a is b

    def base(self, case):
        return []

    def tail(self, case, atoms, more):
        return []


def test_a_model_split_covers_only_the_models_cases():
    """cert.cover: children one per case of the model's disjunction, each within its case (its atoms the parent's or the
    case's; dropping atoms is sound); a child in another case, with an atom of neither, or an obligation not shown, fails."""
    p = ({Z: 1}, False)
    A, B = ({N: -1}, False), ({N: 1, 1: -1}, False)   # n <= 0 | n >= 1
    t = C.Tree("c", [], pay, FakeModel([("c", [A]), ("c", [B])]))
    t.more[0] = (1, C.fp([p]))   # (F01) a node whose split gave it p (as Tree.split keeps a child's atoms: G02, by contents)
    t.split(0, ("model", "presence", None), [p], [("c", [p, ({N: -1}, False)]), ("c", [({N: 1, 1: -1}, False)])])   # the second drops p: sound
    for kids in ([("c", [p, A])], [("c", [p, A]), ("d", [p, B])], [("c", [p, A]), ("c", [p, ({N: 1}, False)])]):
        with pytest.raises(C.Bad):
            t2 = C.Tree("c", [], pay, FakeModel([("c", [A]), ("c", [B])]))
            t2.more[0] = (1, C.fp([p]))
            t2.split(0, ("model", "band", None), [p], kids)
    need = [({N: 1, 1: -1}, False), ({N: -1}, False)]
    t = C.Tree("c", [], pay, FakeModel([("c", [A])], [need]))
    t.more[0] = (1, C.fp([p]))
    with pytest.raises(C.Bad):
        t.split(0, ("model", "half", None), [p], [("c", [p, A])])   # its obligation is not shown
    assert ok(need, [("p", 0), ("p", 1), ("c", [(1, 0), (1, 1)])])
    t.proved(need)
    t.split(0, ("model", "half", None), [p], [("c", [p, A])])
    with pytest.raises(C.Bad):
        C.Tree("c", [], pay).split(0, "sign", [], [("d", [({Z: 1}, False)]), ("c", [({Z: -1}, False)])])   # a case changed outside the model


def test_a_leaf_is_the_models_atoms_of_its_case():
    """A leaf's system starts with the model's atoms of its node's case (Model.base): a system of another case fails."""
    s1 = [({N: -1, 1: -1}, False), ({Z: 1}, False)]   # base: n <= -1; the node's atom z >= 0
    assert ok(s1, [("p", 0), ("nat", N), ("c", [(1, 0), (1, 1)])])
    m = type("M", (FakeModel,), {})([])   # (B07) cert.py reads the model's methods by its class (cert.mcall), not the instance's
    type(m).base = lambda self, case: [({N: -1, 1: -1}, False)] if case == "c" else [({N: 1}, False)]
    root = [s1[1]]
    C.Tree("c", root, pay, m).leaf(0, s1, root, 0)
    with pytest.raises(C.Bad):
        C.Tree("d", root, pay, m).leaf(0, s1, root, 0)   # another case's model atoms
    with pytest.raises(C.Bad):
        C.Tree("c", [({Z: 1}, False)], pay, m).leaf(0, s1, root, 0)   # not its option's atoms
    type(m).tail = lambda self, case, atoms, more: [({N: 1}, False)]
    with pytest.raises(C.Bad):
        C.Tree("c", root, pay, m).leaf(0, s1, root, 0)   # the model's facts at its end are missing


def test_a_variances_verdict_is_recomputed_from_its_values():
    """cert.var_verdict (3.7): written from the comparison's meaning; values [0, M] both reached."""
    assert C.var_verdict("atleast", 0, 0, False, 4) == ("S008", False)   # never below 0: by its sign
    assert C.var_verdict("exceeds", -1, 0, True, 4) == ("S008", False)
    assert C.var_verdict("exceeds", 5, 0, False, 4) == ("S011", True)    # never above its sup
    assert C.var_verdict("atleast", 4, 0, False, 4) is None               # reached at the sup
    assert C.var_verdict("exceeds", 4, 0, False, 4) == ("S011", True)
    assert C.var_verdict("exceeds", 1, 0, True, 4) is None                # sd up to 2
    assert C.var_verdict("atmost", 2, 0, True, 4) == ("S008", True)        # sd never above 2
    assert C.var_verdict("below", Fraction(1, 2), 1, False, 4) == ("S011", False)   # v + 1 < 1/2 never: by its sign
    assert C.var_verdict("atmost", 3, 1, False, 4) == ("S008", True)   # fails only when v - 1 > 3: past the sup
    assert C.var_verdict("atmost", 2, 1, False, 4) is None


def test_a_variance_refusal_is_checked_and_one_resting_on_nothing_is_x001(tmp_path, monkeypatch):
    """L1: a variance's S008 (3.7) carries its facts (f, c, w, sd, sup); the checker recomputes the verdict: a verdict
    the facts do not give is X001. (F03: the check that a refusal kept something is gone; every "none" is kept by the
    trusted Model.find, never by the search, test_a_none_the_search_does_not_keep_is_still_checked.)"""
    D.CERTS.clear()
    out = gn(tmp_path, 'atleast(sample_variance(t, "score"), c = 0)')
    assert "[S008" in out and D.CERTS.get("var: by its sign") == 1, (out, D.CERTS)
    rest = D.Decide.rest
    monkeypatch.setattr(D.Decide, "rest", lambda self, kind, what, v: rest(self, kind, what, ("S011", "it holds")) and v if kind == "var" else rest(self, kind, what, v))
    out = gn(tmp_path, 'atleast(sample_variance(t, "score"), c = 0)')
    assert "[X001" in out and "do not give" in out, out


SUMS = 'mean(where(t, eq(1, "B"), ne(1, "007")), 2)'


def test_shares_with_sums_need_their_points_shown(tmp_path, monkeypatch):
    """L4 (5.4 with sums): two means equal on every input, their sums free: at each point of the counts both signs'
    systems must be among the replayed finds shown to have no input (Decide.sums_shown recomputes them); one left out
    of what is kept is X001."""
    D.CERTS.clear()
    out = claim(tmp_path, SUMS)
    assert "[S008" in out and D.CERTS.get("shares with sums") == 1 and not any(k.startswith("lemma") for k in D.CERTS), (out, D.CERTS)
    certify, seen = D.Decide.certify, []

    def drop_one(self):   # the points' systems not kept for the check (here S1 = S2, B1 = B2: P is 0, each system 0 > 0)
        if any(e[0] == "sums" for e in D.PEND):
            seen.extend(e for e in D.PEND if e[0] == "find" and len(e[1]) == 1)
            D.PEND[:] = [e for e in D.PEND if not (e[0] == "find" and len(e[1]) == 1)]
        return certify(self)
    monkeypatch.setattr(D.Decide, "certify", drop_one)
    out = claim(tmp_path, SUMS)
    assert seen and "[X001" in out and "shares with sums" in out, (out, seen)


def test_two_floats_pinned_are_checked_and_none_is_the_models(tmp_path, monkeypatch):
    """L5 (fwin, 3.6) is no longer a named lemma. A pair pinned (u = a, v = w) is checked by cert.pin_split: every atom
    with u or v has no other variable and holds at (a, w), and a, w are floats; a pin breaking an atom, beside another
    variable, or off the floats is Bad. No pair in the window is the model's own enumeration (fwin, trusted), recomputed
    by certify: a search claiming none where the model finds a pair is X001."""
    import sys
    from test_exact_decide import _p, E45
    u, v, one = ("z", "pix", "n"), ("z", "pix", "m"), D.ONE
    box = [D.ge({u: 1, one: D.FMAX}), D.ge({u: -1, one: D.FMAX}), D.ge({v: 1, one: D.FMAX}), D.ge({v: -1, one: D.FMAX})]
    w = Fraction(1, 10 ** 45)
    C0 = Fraction(1, 10) - Fraction(1, 1000) * Fraction(2.0 ** -1000) + w / 3
    win = [D.ge({u: 1, v: -Fraction(1, 1000), one: -(C0 - w)}), D.ge({u: -1, v: Fraction(1, 1000), one: C0 + w})]
    P = D.fwin(box + win, [0])
    assert P and C.pin_split(box + win, P, pay) is None
    x, a = next((k, -F[one] / F[k]) for F, _ in P[:1] for k in F if k != one)
    off = [D.ge({x: 1, one: -(a + 1)}), D.ge({x: -1, one: a + 1})] + P[2:]
    with pytest.raises(C.Bad, match="breaks"):
        C.pin_split(box + win, off, pay)
    with pytest.raises(C.Bad, match="another variable"):
        C.pin_split(box + win + [D.ge({u: 1, ("n", "t", "A"): 1})], P, pay)
    half = [D.ge({x: 1, one: -Fraction(1, 3)}), D.ge({x: -1, one: Fraction(1, 3)})] + P[2:]
    with pytest.raises(C.Bad, match="not a float"):
        C.pin_split([], half, pay)
    with pytest.raises(C.Bad, match="two variables"):
        C.pin_split([], P[:3], pay)
    D.CERTS.clear()
    c = f"exceeds(widen(difference(pixdim(nifti(n), 4), pixdim(nifti(m), 4)), tolerance = {E45} s), c = 0.4285714285714285714285714285714285 s)"
    out = _p(tmp_path, c)
    assert "[S008" in out and D.CERTS.get("split: fwin") and not any(k.startswith("lemma") for k in D.CERTS), (out, D.CERTS)
    real = D.fwin
    monkeypatch.setattr(D, "fwin", lambda atoms, pay: real(atoms, pay) if sys._getframe(1).f_code.co_name == "disjunction" else [])
    out = _p(tmp_path, c.replace("0.4285714285714285714285714285714285", "0.3"))
    assert "[X001" in out and "float window" in out, out


def test_a_variance_shapes_none_by_its_range_is_checked(monkeypatch):
    """L6 (3.7): a variance shape's "no input in K" (var_hit, d_hit, n_hit) is a "vrange" record when the model's ranges
    of its values (Decide.vranges: [0, sup]; a difference [-sup2, sup1], 0 for two equal variances, [0, sup] for sample
    minus population of one selection; a sum as n_hit) miss every piece: cert.vrange_none checks each range against
    each piece (open and closed ends); a range that meets a piece is X001."""
    from fractions import Fraction as F
    z, one, h = F(0), F(1), F(1, 2)
    assert C.vrange_none([(z, one)], [(one, False, None, False), (None, False, z, False)], pay) is None
    for ivs, K in [([(z, one)], [(one, True, None, False)]), ([(z, one)], [(None, False, z, True)]), ([(z, one)], [(h, False, h, True)]),
                   ([(one, z)], [])]:
        with pytest.raises(C.Bad):
            C.vrange_none(ivs, K, pay)
    from test_partB import tab, X5
    c = 'atleast(difference(sample_variance(t, 2), population_variance(t, 2)), c = 0)'
    D.CERTS.clear()
    out = tab(c, X5)
    assert out[0].startswith("line 3: refused [S008") and D.CERTS.get("var: by its range") and not any(k.startswith("lemma") for k in D.CERTS), (out, D.CERTS)
    real = D.Decide.rest
    monkeypatch.setattr(D.Decide, "rest", lambda self, kind, what, v: real(self, kind, ([(F(-1), one)] * len(what[0]), what[1]) if kind == "vrange" else what, v))
    out = tab(c, X5)
    assert "[X001" in out[0] and "range meets" in out[0], out


def test_a_variances_none_by_its_values_is_checked(monkeypatch):
    """L6 (5a's no-input sub-case): a widened variance that no readable input reaches keeps ("vdeep", K, ddof, the
    classes' readable values, the rows tried): cert.vdeep_none tries every multiset (two values: every j, by halving)
    up to those rows and checks every piece lies above the largest variance of more rows; a piece met, or rows too few,
    is Bad, and a tampered record X001."""
    from fractions import Fraction as F
    z, one = F(0), F(1)
    K = [(F(1, 3), False, F(1, 2), False)]   # sample variances of 0s and 1s: 1/2, 1/3, 1/4, 3/10, ... none inside
    assert C.vdeep_none(K, 1, [z, one], 3, pay) is None
    for k, vals, n in [([(F(1, 3), True, F(1, 2), False)], [z, one], 3), ([(F(3, 11), False, F(3, 10), True)], [z, one], 40),
                       ([(one, True, one, True)], [z, one, 2 * one], 3), (K, [z, one], 0)]:
        with pytest.raises(C.Bad):
            C.vdeep_none(k, 1, vals, n, pay)
    from test_partB import tab, B502, G2, DEC
    sel = f'where(t, gt("x", c = {B502}), lt("x", c = {G2(3)}))'
    c = f"exceeds(widen(sample_variance({sel}, 2), tolerance = {DEC(2500, 999)}), c = {DEC(42500, 999)})"
    data = f"g\tx\ty\nA\t{G2(1)}\t1\nB\t{G2(2)}\t2\n"
    D.CERTS.clear()
    out = tab(c, data)
    assert out[0].startswith("line 3: refused [S008") and D.CERTS.get("var: by its values") and not any(k.startswith("lemma") for k in D.CERTS), (out, D.CERTS)
    real = D.Decide.rest
    monkeypatch.setattr(D.Decide, "rest", lambda self, kind, what, v: real(self, kind, ([(F(0), False) + p[2:] for p in what[0]],) + what[1:] if kind == "vdeep" else what, v))
    out = tab(c, data)
    assert "[X001" in out[0] and "variance in a piece" in out[0], out


def test_a_certificate_input_that_is_not_its_store_is_x001(tmp_path, monkeypatch):
    """(BLD) the certificate inputs are built by build.py, outside the base; decide.plain (B02) copies each from exact types as the store
    its hashes name (a blob's sha256, a periodic file rebuilt from its rule), and Decide.run makes any other X001."""
    import hashlib
    from reality4 import witness as W
    blob = b"a\tb\n"
    h = hashlib.sha256(blob).hexdigest()
    assert D.plain(blob) is blob and D.plain(({h: blob}, h)) == ({h: blob}, h)
    assert D.plain(({h: blob + b"x"}, h)) is None and D.plain(({h: blob}, "0" * 64)) is None and D.plain(bytearray(blob)) is None
    p = W.Periodic(300, 1)
    assert D.plain(p).sha == p.sha and D.plain(({p.sha: p}, p.sha))[0][p.sha].sha == p.sha
    q = W.Periodic(300, 1)
    q.n = 299   # (B02) its rule is not read: plain rebuilds it from its arguments, so the file its sha names is used
    assert D.plain(q).n == 300 and D.plain(q) is not q and D.plain(({p.sha: W.Periodic(300, 2)}, p.sha)) is None
    real = D.Model.bytes_of

    def tampered(self, *a, **k):
        b = dict(real(self, *a, **k))
        n = sorted(b)[0]
        b[n] = bytearray(b[n]) if isinstance(b[n], bytes) else ({**b[n][0], b[n][1]: b"x"}, b[n][1]) if isinstance(b[n], tuple) else type("P", (W.Periodic,), {})(300, 1)
        return b
    monkeypatch.setattr(D.Model, "bytes_of", tampered)
    out = claim(tmp_path, S008)
    assert "[X001" in out and "not the store its hashes name" in out, out


def test_a_leaf_on_a_system_stronger_than_its_node_is_x001(tmp_path, monkeypatch):
    """(F01; Opus 5.5 review 01a) search.py's leaf solves its system with one atom its node does not have (-1 >= 0) and
    reports it in its path: cert.Tree compares a leaf's atoms with the node's (as its splits gave them), so the
    refusal's check fails (X001), never a wrong S008."""
    from reality4 import search as S
    p, h = tsv(tmp_path, "t.tsv", "g\tx\nA\t1\nB\t2\nA\t3\n")
    prog = f'file f = sha256:{h}\nlet t = tsv(f)\nclaim count(where(t, eq("g", "A")))\n'
    assert "formed:" in run(prog, [p])[1]
    bogus, orig = D.ge({D.ONE: -1}), S.one_solve

    def one_solve(self, case, atoms, budget, bounded=True):
        if self.leaf_at:
            tree, node, path, tail = self.leaf_at
            n = len(atoms) - tail
            atoms = atoms[:n] + [bogus] + atoms[n:]
            self.leaf_at = (tree, node, path + [bogus], tail)
        elif self.cert is False:
            atoms = atoms + [bogus]
        return orig(self, case, atoms, budget, bounded)
    monkeypatch.setattr(D.Model, "one_solve", one_solve)
    out = run(prog, [p])[1]
    assert "[X001" in out and "[S008" not in out, out


def test_parts_that_do_not_partition_a_summed_columns_bands_are_x001(tmp_path, monkeypatch):
    """(F01; Opus 5.5 review 01b) refine (search.py) writes the parts the model's sums are checked against; a refine
    that drops a band (the second half) is caught by the trusted check that the parts partition the bands: X001."""
    from reality4 import search as S
    c2 = f'below(sum(where(t, gt("x", c = 0.{"0" * 996}5), le("y", c = 2.05)), "x"), c = 1{"0" * 400}.{"0" * 499}2)'
    p, h = tsv(tmp_path, "t.tsv", "g\tx\ty\nA\t0.5\t1\nB\t0.25\t2\nA\t0.75\t3\n")
    prog = f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {c2}\n"
    assert "formed:" in run(prog, [p])[1]
    orig = S.refine

    def refine(self, key, x):
        r = orig(self, key, x)
        if len(self.parts.get(key, ())) > 1:
            self.parts[key] = self.parts[key][:1]   # a band dropped: the model would exclude real inputs
        return r
    monkeypatch.setattr(D.Model, "refine", refine)
    out = run(prog, [p])[1]
    assert "[X001" in out and "partition" in out, out


def test_a_none_the_search_does_not_keep_is_still_checked(tmp_path, monkeypatch):
    """(F03; Opus 5.5 review 03) search.py's find_options answers one W2 option "none" (it has a point) and keeps no
    record of it: the trusted Model.find keeps every "none" the question gets, so certify replays it, finds the point
    and the refusal is X001, never a wrong S008 W2."""
    from reality4 import search as S
    p, h = tsv(tmp_path, "t.tsv", "g\tx\nA\t1\nA\t2\nB\t1\nA\t1\n")
    prog = f'file f = sha256:{h}\nlet t = tsv(f)\nclaim share(where(t, eq("g", "A"), eq("x", "1")), where(t, eq("g", "A")))\n'
    assert "formed:" in run(prog, [p])[1]
    in_w2, orig_find, orig_w2 = [False], S.find_options, D.Decide.w2_input

    def find_options(self, options, budget, what):
        if in_w2[0] and len(options) == 1 and not self.cert:
            return None
        return orig_find(self, options, budget, what)

    def w2_input(self, *a, **k):
        in_w2[0] = True
        try:
            return orig_w2(self, *a, **k)
        finally:
            in_w2[0] = False
    monkeypatch.setattr(D.Model, "find_options", find_options)
    monkeypatch.setattr(D.Decide, "w2_input", w2_input)
    out = run(prog, [p])[1]
    assert "[X001" in out and "[S008" not in out, out


def test_a_search_point_where_a_mean_has_no_rows_is_x001(tmp_path, monkeypatch):
    """(F04; mutation sweep, partb/MUT) w1 asks for an input whose answer differs from the answer at the search's first
    point x0; for a ratio (a mean) that is den(x0)·num − num(x0)·den ≠ 0. A search answering an empty point ({}: no rows)
    made that form 0, so "no input differs" was vacuous and a mean that forms was refused S008 W1. Now X001."""
    p, h = tsv(tmp_path, "n.tsv", "group\tage\tscore\nA\t30\t1.5\nB\t40\t2\nA\t25\t-1\n")
    prog = f'file f = sha256:{h}\nclaim atleast(mean(tsv(f), "age"), c = 0)\n'
    assert "formed:" in run(prog, [p])[1]
    orig = D.Model.solve

    def solve(self, *a, **k):
        r = orig(self, *a, **k)
        return {} if isinstance(r, dict) else r
    monkeypatch.setattr(D.Model, "solve", solve)
    out = run(prog, [p])[1]
    assert "[X001" in out and "ratio over no rows" in out, out


def test_a_store_that_is_not_plain_is_x001(tmp_path, monkeypatch):
    """(B02, Argon review 2 02) Decide.run read build.py's store through its own methods: a dict subclass could show one
    store to the checks and another to the evaluator (Argon's case A: build.py alone, a wrong form), a dataset could be a
    tuple subclass (case B2), a Periodic's whole a bytes subclass equal to anything (other bytes under its sha), and a
    dataset blob's key a str subclass equal to anything (a blob under a hash it does not have). Decide.input copies the
    store from exact types (decide.plain, a Periodic rebuilt from its arguments) or gives X001."""
    import hashlib
    from reality4 import witness as W
    real = D.Model.bytes_of

    class Flip(dict):
        pass
    monkeypatch.setattr(D.Model, "bytes_of", lambda self, *a, **kw: Flip(real(self, *a, **kw)))
    out = claim(tmp_path, S008)
    assert "[X001" in out and "not the store its hashes name" in out, out
    monkeypatch.undo()

    class B(bytes):
        def __eq__(s, o):
            return True
        __hash__ = bytes.__hash__

    class S(str):
        def __eq__(s, o):
            return True
        __hash__ = str.__hash__
    q = W.Periodic(10, 0)
    q.whole = B(b"x" * 10)
    assert D.plain(q).whole == W.Periodic(10, 0).whole and type(D.plain(q).whole) is bytes   # the rebuilt file's bytes
    k = S("0" * 64)
    assert D.plain(({k: b"hello"}, k)) is None
    h = hashlib.sha256(b"hello").hexdigest()
    assert D.plain(type("T", (tuple,), {})(({h: b"hello"}, h))) is None and D.plain(({h: B(b"hello")}, h)) is None


def test_a_means_rows_range_is_read_only_as_its_atoms_state_it():
    """(D01, review 4 01's open lead) prange_split took the parent's range from its atoms' .r, which the search sets: a
    parent whose atoms state N >= 1, mu >= 0 but say (1, 3, 1) was split into one child over [1, 3], leaving N >= 4 in
    no child. The range is now read only as the parent's atoms state it (by form), and a range's ends are integers (a
    child ending at 7/2 and the next starting at 9/2 left N = 4 in neither)."""
    mu, n, s = ("z", "mu"), ("n", "s", "A"), ("z", "S")
    P = D.PAtom(mu, {s: 1}, {n: 1}, lo=Fraction(-1), hi=Fraction(3))
    root = [P]
    par = D.prange(P, 1, None, 1)
    liar = [D.RAtom(tuple(A), A.z, (1, 3, 1)) for A in par]
    with pytest.raises(C.Bad):
        C.prange_split(P, liar, root, [D.prange(P, 1, 3, 1)], pay)
    assert C.prange_split(P, par, root, [D.prange(P, 1, None, 1)], pay) is None
    with pytest.raises(C.Bad):
        C.prange_split(P, par, root, [D.prange(P, 1, Fraction(7, 2), 1), D.prange(P, Fraction(9, 2), None, 1)], pay)
    assert C.prange_split(P, par, root, [D.prange(P, 1, Fraction(3), 1), D.prange(P, 4, None, 1)], pay) is None


def test_a_copy_has_distinct_keys_and_a_failed_copy_is_not_kept():
    """(D01, review 4's open leads) cert.exact rebuilds a Fraction from its fields: two keys of a dict made one value
    (a Fraction's fields rewritten after it went in) merged silently. Such a dict is now Bad, and a copy that fails
    leaves nothing in the memo (a search that catches the Bad cannot have a partial list read as the whole)."""
    f1, f2 = Fraction(1, 2), Fraction(1, 3)
    d = {f1: "a", f2: "b"}
    f2._numerator, f2._denominator = 1, 2
    with pytest.raises(C.Bad):
        C.exact(d)
    L, memo = [{1: 2}, object()], {}
    with pytest.raises(C.Bad):
        C.exact(L, memo)
    assert id(L) not in memo
