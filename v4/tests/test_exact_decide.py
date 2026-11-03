"""Exact-decision phase 3: part T is decided exactly (SPEC-EXACT, src/reality4/decide.py). Each test is a
behaviour the switch changed or must keep."""
import pytest

from helpers import run, tsv
from reality4 import decide as D
from reality4 import witness as W

T7 = "group\tsite\tsex\nA\ts1\tF\nA\ts2\tM\nB\ts1\tF\nB\ts1\tM\nP\ts2\tF\nA\ts3\tM\nB\ts2\tF\n"


def line(text, n):
    return [ln for ln in text.split("\n") if ln.startswith(f"line {n}:")][0]


def claim(tmp_path, c, data=T7, kind="tsv"):
    p, h = tsv(tmp_path, "f." + kind, data)
    ok, text = run(f"file f = sha256:{h}\nlet t = {kind}(f)\nclaim {c}\n", [p])
    return line(text, 3)


# ---- overcorrections of the search that now form (plan 7.3 refuse/form; partT pt136, pt254, pt484, pt556)

@pytest.mark.parametrize("c", [
    'share(where(t, ne("group", "A"), ne("group", "B"), eq("sex", "F")), where(t, ne("group", "A")))',
    'difference(difference(count(where(t, ne("group", "A"))), rows(t)), difference(count(where(t, ne("group", "P"), ne("group", "A"), ne("group", "B"))), rows(t)))',
    'below(share(where(t, ne("group", "B"), ne("site", "s3"), ne("group", "A"))), c = 1/2)',
])
def test_search_misses_now_form(tmp_path, c):
    assert "formed" in claim(tmp_path, c)


def test_eight_conditions_on_eight_columns_form(tmp_path):   # finding 14's kind, past any shell cap
    hdr = "\t".join(f"c{i}" for i in range(1, 9))
    data = hdr + "\n" + "\t".join("k" * 8) + "\n" + "\t".join("k" * 7 + "z") + "\n"
    c = "count(where(t, " + ", ".join(f'eq({i}, "k")' for i in range(1, 9)) + "))"
    assert "= 1 (Exact)" in claim(tmp_path, c, data)


def test_cross_file_difference_with_another_cutoff_forms(tmp_path):   # finding 15's kind
    p, hp = tsv(tmp_path, "f.tsv", "c\na\nb\nc\nd\ne\n")
    q, hq = tsv(tmp_path, "g.tsv", "c\ny\nb\n")
    ok, text = run(f"file f = sha256:{hp}\nfile g = sha256:{hq}\n"
                   'claim exceeds(difference(count(where(tsv(f), ne(1, "x"))), count(where(tsv(g), ne(1, "y")))), c = 3)\n', [p, q])
    assert "holds" in line(text, 3), text


# ---- refusals the exact path decides --------------------------------------------------------------

def test_idle_condition_refuses_decided(tmp_path):
    out = claim(tmp_path, 'count(where(t, eq("group", "A"), ne("group", "B")))')
    assert "[S008" in out and "decided exactly" in out and "ne(...)" in out


def test_selection_that_never_has_a_row_is_s011(tmp_path):
    out = claim(tmp_path, 'count(where(t, eq("group", "A"), eq("group", "B")))')
    assert "[S011" in out and "decided exactly" in out


def test_a_quote_cannot_be_in_a_tsv_cell_but_can_in_a_csv_cell(tmp_path):
    assert "[S011" in claim(tmp_path, 'count(where(t, eq(1, "\\"q\\"")))', "c\na\nb\n")
    assert "formed" in claim(tmp_path, 'count(where(t, eq(1, "\\"q\\"")))', 'c\na\n"""q"""\n', "csv")


def test_cutoff_past_the_bound_refuses_r013(tmp_path):   # D3: only inputs of more than MAX_ROWS rows differ
    out = claim(tmp_path, 'atmost(count(where(t, eq("group", "A"))), c = 1000000)')
    assert "[R013" in out and f"more than {D.MAX_ROWS} rows" in out
    out = claim(tmp_path, 'atmost(count(where(t, eq("group", "A"))), c = 1000000000)')   # (F02) past any readable table
    assert "[S008" in out and "it holds only by the read limit" in out


def test_small_witness_found_although_another_outcome_pair_needs_a_large_one(tmp_path):   # pt064
    assert "holds" in claim(tmp_path, 'atleast(share(where(t, eq("sex", "M"), ne("group", "Z")), where(t, eq("sex", "M"))), c = 1/1000000)')


@pytest.mark.parametrize("c, want", [(1000000, "R013, bounds"), (1000000000, "S008, item 1")])   # (F02) past the read limit: S008
def test_r013_is_the_same_under_renaming_and_reordering_of_slots(tmp_path, c, want):   # plan 7.8
    p, hp = tsv(tmp_path, "f.tsv", "c\na\nb\n")
    q, hq = tsv(tmp_path, "g.tsv", "c\ny\n")
    body = 'claim atmost(difference(count(where(tsv({0}), ne(1, "x"))), count(where(tsv({1}), ne(1, "y")))), c = %d)\n' % c
    outs = []
    for a, b, first in (("f", "g", True), ("g", "f", True), ("u", "v", False)):
        decl = f"file {a} = sha256:{hp}\nfile {b} = sha256:{hq}\n" if first else f"file {b} = sha256:{hq}\nfile {a} = sha256:{hp}\n"
        ok, text = run(decl + body.format(a, b), [p, q])
        outs.append(line(text, 3).split("]")[0])
    assert outs[0] == outs[1] == outs[2] == "line 3: refused [" + want, outs


def test_look_alike_literals_on_one_column_are_decided_exactly(tmp_path, monkeypatch):
    # item 2 (28 Oct 2026; went to the search before): a row holding "rn" makes the where() that reads "m" refuse K002, no
    # answer, and an "m" row the one that reads "rn"; on the inputs where both versions answer, ne(1, "rn") holds on every
    # row, so it never changes an answer (a refusal is no answer, SPEC 4.4 item 11): S008 W2
    out = claim(tmp_path, 'difference(count(where(t, eq(1, "m"))), count(where(t, ne(1, "rn"))))', "c\na\nb\n")
    assert "[S008" in out and "W2" in out and "decided exactly" in out, out


def test_outside_part_t_refuses_s013(tmp_path):
    # phase 7 (D5): one file whose size() is read beside its tsv() and csv() readings is outside part T (3.12, 3.13);
    # no search decides it. (Until shape 1, 29 Oct 2026, the canary was a where() of tsv() beside
    # rows(csv()): decided now, 3.13; then number() of a tsv() cell beside a csv() sum: decided now, 3.13b; then a variance
    # of the tsv() column beside a csv() variance: decided now, 3.13g.) Now: size() of the file beside both readers.
    out = claim(tmp_path, 'difference(difference(size(f), rows(csv(f))), number(cell(t, 1, 1)))', "c\n1\n2\n")
    assert "[S013" in out and "cannot decide this kind of statement" in out and "constant" not in out, out
    assert "[S008" in claim(tmp_path, 'difference(sample_variance(t, 1), sample_variance(csv(f), 1))', "c\n1\n2\n")   # 3.13g
    assert "[S008" in claim(tmp_path, 'difference(sum(t, 1), sum(csv(f), 1))', "c\n1\n2\n")   # 3.13c
    out = claim(tmp_path, 'difference(number(cell(t, 1, 1)), sum(csv(f), 1))', "c\n1\n2\n")
    assert "formed:" in out and "= -2" in out, out
    out = claim(tmp_path, 'difference(count(where(t, eq(1, "1"))), rows(csv(f)))', "c\n1\n2\n")
    assert "formed:" in out and "= -1" in out, out
    assert "[S013" not in claim(tmp_path, 'count(where(t, eq("group", "A")))')


def test_a_variance_part_hidden_by_another_variance_is_not_refused(tmp_path):
    """(3.7a; BB's call on Patsak's behalf 29 Oct 2026 04:10, reversible) "a part of a variance's selection bears
    through V003/V005 or not at all" holds for one variance alone, not beside another value refusing on the same
    inputs: in Vs(sel) - Vp(sel), sel = rows not -1, Vp's condition shows by V003 only where Vs(sel) is V003 too, yet
    on 1, 2, -1 dropping it turns True into False with both answering (ground truth, groundtruth.recheck_w2; found by
    the shape-1 runner, partb/S13/s1 VAR=1 seed 3). Such a found none is not decided: S013, never S008 W2. One variance
    alone keeps its W2 decided (a dropped condition bears there through V003), and so does a condition that only drops
    rows no variance reads as a number (equal good types answer alike wherever both answer: rows not "a" beside rows
    not -1 is S008 W2, ground truth: not contradicted on every csv of 1-4 rows over 1, 2, -1, 0, a, "", 3)."""
    d = "c\n1\n2\n"
    for c in ['exceeds(difference(sample_variance(where(t, ne(1, "-1")), 1), population_variance(where(t, ne(1, "-1")), 1)), c = 0)']:
        out = claim(tmp_path, c, d)
        assert "formed:" in out, out   # (3.7b) decided since: an input where both answer and the comparison flips
    out = claim(tmp_path, 'exceeds(sample_variance(where(t, ne(1, "-1")), 1), c = 0)', d)
    assert "formed:" in out, out
    out = claim(tmp_path, 'atmost(difference(population_variance(where(t, ne(1, "-1")), 1), population_variance(where(t, ne(1, "a")), 1)), c = 0)', d)
    assert "[S008" in out and "does not bear" in out, out



def test_a_variance_part_beside_another_variance_is_decided_by_a_checked_witness(tmp_path, monkeypatch):
    """(3.7b; BB's call on Patsak's behalf 29 Oct 2026 05:40, reversible) 3.7a's S013 decided: the joint witness
    search (search.joint_rows, untrusted) finds rows on which the real code gives the statement with and without the
    part different outcomes; Decide.differ_on confirms them on bytes. Before it, Decide.same_rows keeps the W2 refusal
    where each variance and its place without the part hold the same good types less the case's zero types (they read
    the same rows wherever both answer). Rows that do not tell the two apart are X001
    (a tampered search), and a search that finds nothing is R013 (a stopped search at MAX_CASES), never S008 W2: the
    part is not shown not to bear (ground truth: it bears, on 1, 2, -1)."""
    from reality4 import search as S
    d = "c\n1\n2\n"
    c = 'exceeds(difference(sample_variance(where(t, ne(1, "-1")), 1), population_variance(where(t, ne(1, "-1")), 1)), c = 0)'
    assert "formed:" in claim(tmp_path, c, d)
    assert "formed:" in claim(tmp_path, 'difference(sample_variance(where(t, ne(1, "1")), 1), population_variance(where(t, ne(1, "1")), 1))', "c\n0\n2\n3\n")
    tw = 'exceeds(difference(sample_variance(where(t, ne(1, "-1")), 1), population_variance(where(csv(f), ne(1, "-1")), 1)), c = 0)'
    assert "formed:" in claim(tmp_path, tw, d)   # the finding's tsv() form (bf1n VAR=1 seed 3)
    b = 'below(difference(sample_variance(csv(f), 1), population_variance(where(t, ne(1, "b")), 1)), c = 2)'
    out = claim(tmp_path, b, d)   # a "b" line makes sample_variance(csv(f)) refuse: same rows where both answer (same_rows)
    assert "[S008" in out and "W2" in out, out
    monkeypatch.setattr(D.Decide, "same_rows", lambda self, top, whole: True)   # mutant: every pair "the same rows"
    assert "[S008" in claim(tmp_path, c, d)   # a wrong W2 refusal (ground truth: it bears), which the first assert catches
    monkeypatch.undo()
    monkeypatch.setattr(S, "joint_rows", lambda dd, top, whole: {})   # no rows: both refuse alike
    out = claim(tmp_path, c, d)
    assert "[X001" in out, out
    monkeypatch.setattr(S, "joint_rows", lambda dd, top, whole: None)   # a bounded none is no proof
    out = claim(tmp_path, c, d)
    assert "[R013" in out and "3.7b" in out and "[S008" not in out, out

# ---- a certificate the real code does not confirm is no verdict ---------------------------------------

def test_unconfirmed_certificate_is_x001(tmp_path, monkeypatch):
    monkeypatch.setattr(D.Model, "bytes_of", lambda self, case, x, seed=0: {s: self.table(s, []) for s in self.names})
    out = claim(tmp_path, 'count(where(t, eq("group", "A")))')
    assert "[X001" in out and "do not confirm" in out


def test_unrealisable_class_is_not_a_variable(tmp_path):
    out = claim(tmp_path, 'count(where(t, ne(1, "\\"q\\"")))', "c\na\nb\n")   # a quote is in no TSV cell: ne() holds on every row
    assert "[S008" in out and "decided exactly" in out


# ---- the part-T additions of the phase 3 checkpoint (BB's ruling 3): number conditions, cell, key, header, number()

N5 = "group\tsite\tage\nA\ts1\t30\nQ\ts2\t41\nB\ts1\t-4.5\nC\ts1\t7\nP\ts2\t12\n"


@pytest.mark.parametrize("c, want", [
    ('count(where(t, ge("age", c = 10)))', "= 3 (Exact)"),
    ('count(where(t, ge("age", c = 10), gt("age", c = 5)))', "[S008"),     # implied: W2
    ('count(where(t, ge("age", c = 10), lt("age", c = 5)))', "[S011"),     # contradictory: W1
    ('count(where(t, ge("age", c = 1/3), le("age", c = 1/3)))', "[S011"),  # no decimal is 1/3
    ('count(where(t, eq("site", "s1"), ge("age", c = 0)))', "= 2 (Exact)"),
    ('share(where(t, ge("age", c = 0), eq(1, "A")), where(t, ge("age", c = 0)))', "= 1/4 (Exact)"),
])
def test_number_conditions_are_decided_exactly(tmp_path, c, want, monkeypatch):
    out = claim(tmp_path, c, N5)
    assert want in out and ("[S0" not in want or "decided exactly" in out), out


def test_a_point_needs_a_spelling_unlike_the_literals(tmp_path):
    # the decimal 10 is spelled 10.0: "10" looks like the literal "l0" (UTS #39), and a row holding it refuses K002
    out = claim(tmp_path, 'count(where(t, ne(1, "l0"), ge(1, c = 10), le(1, c = 10)))', "c\n10.0\n3\n")
    assert "= 1 (Exact)" in out, out


def test_v005_is_an_outcome_for_w2(tmp_path):
    # without eq(), a row whose col 2 is not a decimal refuses V005; with it the row is dropped
    assert "formed" in claim(tmp_path, 'count(where(t, eq(1, "a"), ge(2, c = 0)))', "c\td\na\t1\nb\t2\n")


@pytest.mark.parametrize("c, want", [
    ('cell(t, 1, 1)', '= "A"'),
    ('cell(t, key("group", "P"), 3)', '= "12"'),
    ('cell(t, key("group", "P"), 1)', "[S008"),                       # the key's own column: always "P"
    ('cell(t, key("group", "P", "group", "P"), 3)', "[S008"),         # a key pair said twice: W2
    ('number(cell(t, 2, 3))', "= 41 (Exact)"),
    ('difference(number(cell(t, 1, 3)), number(cell(t, 1, 3)))', "[S008"),
    ('difference(number(cell(t, 1, 3)), number(cell(t, key(1, "A"), 3)))', "= 0 (Exact)"),   # the key row need not be row 1
    ('header(t, 2)', '= "site"'),
    ('exceeds(number(cell(t, 1, 3)), c = 1/3)', "holds"),
    ('difference(difference(count(where(t, gt(3, c = 7))), rows(t)), number(cell(t, 4, 3)))', "= -9 (Exact)"),
])
def test_cells_keys_headers_numbers_are_decided_exactly(tmp_path, c, want, monkeypatch):
    out = claim(tmp_path, c, N5)
    assert want in out and ("[S0" not in want or "decided exactly" in out), out


def test_search_misses_with_keys_now_form(tmp_path):   # partT2 pu444: the search never moved a key row
    assert "= 11.5 (Exact)" in claim(tmp_path, 'difference(number(cell(t, key("group", "B", "site", "s1"), 3)), number(cell(t, 3, 3)))',
                                     "group\tsite\tage\nA\ts1\t30\nB\ts2\t41\nP\ts1\t-4.5\nB\ts1\t7\nZ\ts2\t12\n")


def test_number_of_a_header(tmp_path):
    assert "= 5 (Exact)" in claim(tmp_path, 'number(header(t, 1))', "5\tx\n1\t2\n")


def test_a_row_past_the_bound_refuses_r013(tmp_path):   # D3: only tables of more than MAX_ROWS rows have the row
    n = D.MAX_ROWS + 1
    out = claim(tmp_path, f'cell(t, {n}, 1)', "c\n" + "a\n" * n)
    assert "[R013" in out and f"more than {D.MAX_ROWS} rows" in out, out


def test_csv_number_condition(tmp_path):
    assert "= 1 (Exact)" in claim(tmp_path, 'count(where(t, gt(2, c = 1), eq(1, "a,b")))', 'c,d\n"a,b",2\nx,0\n', "csv")


# ---- part N (phase 4): sum, mean, max, min, order, median, widen ---------------------------------------

@pytest.mark.parametrize("c, want", [
    ('sum(t, 3)', "= 85.5 (Exact)"),
    ('mean(t, 3)', "= 17.1 (Exact)"),
    ('max(t, 3)', "= 41 (Exact)"),
    ('min(where(t, eq(2, "s1")), 3)', "= -4.5 (Exact)"),
    ('order(t, 3, 2)', "= 7 (Exact)"),
    ('median(t, 3)', "= 12 (Exact)"),
    ('exceeds(max(t, 3), c = 40)', "holds"),
    ('difference(max(t, 3), min(t, 3))', "= 45.5 (Exact)"),
    ('atleast(difference(max(t, 3), min(t, 3)), c = 0)', "[S008"),          # the maximum is never below the minimum: W1
    ('widen(sum(t, 3), tolerance = 1)', "lies within [84.5, 86.5]"),
    ('difference(widen(sum(t, 3), tolerance = 1), widen(sum(t, 3), tolerance = 1))', "[S008"),   # one symbol: always 0
    ('exceeds(widen(mean(t, 3), tolerance = 1), c = 10)', "holds"),
    ('mean(where(t, eq(2, "s1"), ne(1, "Z")), 3)', "= 65/6 (Exact)"),
    ('sum(where(t, ge(3, c = 10), gt(3, c = 5)), 3)', "[S008"),             # implied condition: W2
])
def test_part_n_is_decided_exactly(tmp_path, c, want, monkeypatch):
    out = claim(tmp_path, c, N5)
    assert want in out and ("[S0" not in want or "decided exactly" in out), out


def test_widened_values_are_one_symbol_only_when_their_rows_are_one(tmp_path):
    # on these bytes eq(2, "s1") and ne(2, "s2") select the same rows, so the two widened sums are one value (width 0);
    # on other inputs they are two (width 2): the answer varies, so it forms (SPEC 5.2)
    out = claim(tmp_path, 'difference(widen(sum(where(t, eq(2, "s1")), 3), tolerance = 1), widen(sum(where(t, ne(2, "s2")), 3), tolerance = 1))', N5)
    assert "= 0 (Exact)" in out, out


def test_search_misses_with_order_statistics_now_form(tmp_path):   # partN pn541
    p, h = tsv(tmp_path, "f.tsv", "group\tsite\tage\tscore\nA\ts1\t30\t2\nB\ts2\t41\t5\nP\ts1\t-4.5\t2\nB\ts1\t7\t0.5\nZ\ts2\t12\t9\n")
    ok, text = run(f"file f = sha256:{h}\n"
                   'claim atmost(widen(difference(median(where(tsv(f), ne("site", "s1"), eq("group", "Z")), "score"), median(where(tsv(f), ne("group", "B")), "age")), tolerance = 0.5), c = 1/3)\n', [p])
    assert "holds" in line(text, 2), text


@pytest.mark.parametrize("c", ['difference(max(t, 3), sum(t, 3))'])
def test_part_n_limits_are_decided_exactly(tmp_path, c, monkeypatch):
    # a column both summed and ordered: decided exactly since Part B (e2) (was to the search, CHECKPOINT-4)
    assert "formed" in claim(tmp_path, c, N5)


# ---- (e1) a mean inside a difference: S = mu·N, N's range split (SPEC-EXACT 3.5) ------------------------------

M3 = "g\tx\ty\nA\t1\t2\nB\t3\t0.5\nA\t-2\t4\n"


@pytest.mark.parametrize("c, want", [
    ('difference(mean(t, 2), mean(t, 2))', "[S008"),                                      # one mean: always 0
    ('difference(mean(t, 2), number(cell(t, 1, 2)))', "= -1/3 (Exact)"),
    ('atleast(difference(mean(where(t, gt(2, c = 0.4)), 2), mean(t, 2)), c = 0)', "[S008"),   # the rows above 0.4 and the rest below
    ('exceeds(difference(mean(where(t, gt(2, c = 0.4)), 2), mean(t, 2)), c = 0)', "holds"),
    ('atmost(difference(mean(where(t, le(2, c = 1)), 2), mean(where(t, ge(2, c = 1)), 2)), c = 0)', "[S008"),   # both 1 at most
    ('below(difference(mean(where(t, le(2, c = 1)), 2), mean(where(t, ge(2, c = 1)), 2)), c = 0)', "holds"),     # fails: all rows 1
    ('widen(difference(mean(t, 2), mean(t, 3)), tolerance = 0.5)', "lies within [-2, -1]"),
    ('atleast(difference(mean(where(t, ge(2, c = 1), le(2, c = 3)), 2), number(cell(t, 2, 2))), c = -2)', "holds"),
])
def test_mean_in_a_difference_is_decided_exactly(tmp_path, c, want, monkeypatch):
    out = claim(tmp_path, c, M3)
    assert want in out and ("[S0" not in want or "decided exactly" in out), out


def test_nested_means_cases_hold_on_every_input():
    # nest(): Q, the mean of P's rows and R's, lies between P and R's mean; each input meets one of the cases
    import itertools
    from fractions import Fraction as F
    P = D.PAtom(("z", "mu", "p"), {}, {("n", "s", 1): 1})
    Q = D.PAtom(("z", "mu", "q"), {}, {("n", "s", 1): 1, ("n", "s", 2): 1}, ty={("n", "s", 2): ("iv", (F(0), F(1)), F(1, 2))})
    cases = D.nest(P, Q)
    assert len(cases) == 3 and D.nest(Q, P) is None
    vals = [F(k, 4) for k in range(-8, 9)]
    for ps in itertools.product(vals, repeat=2):   # P's rows: any values; R's: inside (0, 1)
        for rs in itertools.product([F(1, 4), F(1, 2), F(3, 4)], repeat=2):
            for nr in (0, 1, 2):
                p, q = sum(ps) / 2, (sum(ps) + sum(rs[:nr])) / (2 + nr)
                x = {("z", "mu", "p"): p, ("z", "mu", "q"): q, D.ONE: 1}
                assert any(all((sum(c * x[v] for v, c in G.items()) > 0) if st else (sum(c * x[v] for v, c in G.items()) >= 0) for G, st in B) for B in cases), (ps, rs, nr)


# ---- (e2) a column both summed and ordered: each piece's sum S = mu·P (SPEC-EXACT 3.5) ----------------------------

M5 = "g\tx\ty\nA\t1\t1\nA\t2\t0\nB\t1\t2\nA\t0\t1\n"


@pytest.mark.parametrize("c, want", [
    # bfm seed 4: the old search said S008 'could not find' (false: the answer varies with the bytes)
    ('difference(median(where(t, eq("g", "A")), 3), mean(where(t, gt("x", c = 0.4)), 3))', "= 0 (Exact)"),
    ('difference(sum(t, 3), max(t, 3))', "= 2 (Exact)"),
    ('difference(median(where(t, eq("g", "A")), 3), mean(where(t, eq("g", "A")), 3))', "= 1/3 (Exact)"),
    ('atleast(difference(max(t, 3), mean(t, 3)), c = 0)', "[S008"),     # a mean is at most the max of its rows
    ('atmost(difference(min(t, 3), mean(t, 3)), c = 0)', "[S008"),
    ('exceeds(difference(max(t, 3), mean(t, 3)), c = 0)', "holds"),      # fails: all rows equal
    ('below(difference(mean(where(t, eq("g", "A")), 2), max(where(t, gt("x", c = 0.4)), 2)), c = 2)', "[S008"),   # rows <= 0.4 or <= the max
    ('below(difference(median(where(t, ge("x", c = 1)), 3), sum(where(t, eq("g", "A")), 3)), c = 2)', "holds"),
    ('atleast(difference(sum(t, 3), order(t, 3, 2)), c = -100)', "holds"),
])
def test_summed_and_ordered_column_is_decided_exactly(tmp_path, c, want, monkeypatch):
    out = claim(tmp_path, c, M5)
    assert want in out and ("[S0" not in want or "decided exactly" in out), out


def test_find_cap_is_not_a_refusal(tmp_path, monkeypatch):
    # (e2) bfe seed 4: with fm/lp charged before their work, find()'s rounds re-solving each option counted every
    # round (R013 at 564.6 s), and its two-row pass cost one system per count vector (494 options: 25M steps, R013).
    # An option's rounds count once (its largest); one system per row total: S008 W2, decided exactly.
    c = 'exceeds(difference(max(where(t, gt("x", c = 0.4)), 2), mean(where(t, eq("g", "B"), ge("x", c = 0.5)), 2)), c = 0)'
    out = claim(tmp_path, c, "g\tx\ty\nA\t0\t1\nA\t1\t1\nB\t2\t0\nB\t0.5\t2\n")
    assert "[S008" in out and "decided exactly" in out and "W2" in out, out


@pytest.mark.parametrize("c,rows", [
    ('atmost(difference(min(where(t, le("x", c = 1)), 2), mean(where(t, le("x", c = 1)), 2)), c = 2)', "B\t1\t1\nA\t2\t0\nB\t1\t1\nB\t2\t0\n"),
    ('atleast(difference(mean(where(t, le("x", c = 1)), 2), min(t, 2)), c = 0)', "A\t1\t1\nB\t0\t1\nA\t1\t1\nA\t1\t1\n")])
def test_presence_before_a_mean_count(tmp_path, c, rows, monkeypatch):
    # (e2) bfe seeds 3 and 2: a min is at most the mean of the same or fewer rows on every input, yet both refused R013
    # (10,000 cases, 24-27 s): a solution gave a type no rows and a sum of -3, and the mean's count split walked N one
    # by one; the broken presence of one of the mean's types is split first: S008 W1, decided exactly, in about 0.5 s
    out = claim(tmp_path, c, "g\tx\ty\n" + rows)
    assert "[S008" in out and "decided exactly" in out and "W1" in out, out

@pytest.mark.parametrize("c, want", [
    # (pm) never fails: the left mean is at least the mean of the rows in (0.4, 1], the right one at most it; refused
    # R013 at MAX_CASES (104.7 s on 8f646db) before the shared types' mean (caps); S008 W1 now
    ('atleast(difference(mean(where(t, gt("x", c = 0.4)), 2), mean(where(t, le("x", c = 1)), 2)), c = 0)', "W1"),
    ('exceeds(difference(mean(where(t, gt("x", c = 0.4)), 2), mean(where(t, le("x", c = 1)), 2)), c = 0)', "holds"),   # fails: all rows 1
    # nest() compared means of two columns over the same rows as one column's (S008 W1 on 627191a); the value is
    # -1 on these bytes and 1.5 on the one row B 2 0.5: it forms
    ('atmost(difference(mean(where(t, ge("y", c = 0.5)), 2), mean(where(t, ge("y", c = 0.5), gt("x", c = 0.4)), 3)), c = 0)', "holds"),
    # bfp seed 1: with the caps' cases split up front, R013 at MAX_CASES (228.8 s; 2.9 s and formed before); split only
    # where a solution admits no shared mean (cap_ok): formed again
    ('atleast(difference(mean(where(t, eq("g", "B"), ge("x", c = 0.5)), 2), mean(where(t, ge("y", c = 0.5), gt("x", c = 0.4)), 2)), c = 0)', "holds"),
])
def test_means_compared_through_their_shared_rows(tmp_path, c, want, monkeypatch):
    out = claim(tmp_path, c, "g\tx\ty\nA\t0\t1\nA\t1\t1\nB\t2\t0\nB\t0.5\t2\n")
    assert want in out and (want != "W1" or ("[S008" in out and "decided exactly" in out)), out


@pytest.mark.parametrize("c, want", [
    # item 2 (28 Oct 2026): look-alike literals on one column. A row holding "m" makes a where() reading "rn" refuse
    # K002 (no answer) and the other way round, so the inputs that answer hold neither: both counts are 0 (S008 W1).
    ('difference(count(where(t, eq("g", "m"))), count(where(t, eq("g", "rn"))))', "W1"),
    ('difference(count(where(t, ne("g", "m"))), count(where(t, ne("g", "rn"))))', "W1"),
    ('difference(count(where(t, eq("g", "e\\xcc\\x81"))), count(where(t, eq("g", "\\xc3\\xa9"))))', "W1"),
    ('difference(count(where(t, eq("g", "A"))), count(where(t, eq("g", "rn"))))', "= 1 (Exact)"),
    # ne("g", "m") is true on every row of an input that answers (an "m" row makes the other where() refuse): W2
    ('difference(count(where(t, eq("g", "A"), ne("g", "m"))), count(where(t, eq("g", "rn"))))', "W2"),
])
def test_look_alike_literals_are_decided_exactly(tmp_path, c, want, monkeypatch):
    out = claim(tmp_path, c, "g\tx\nA\t1\nB\t2\nC\t1\n")
    assert want in out and (want[0] != "W" or ("[S008" in out and "decided exactly" in out)), out


def pclaim(c, rows=(("A", "1"), ("B", "n/a"), ("A", "2.5"))):
    """c on a dataset (witness._dataset) whose participants.tsv has the columns g and x and these rows."""
    from reality4 import kernel as K
    pt = ("participant_id\tg\tx\n" + "".join(f"sub-p\t{g}\t{v}\n" for g, v in rows)).encode()
    blobs, mh = __import__("reality4.build").build._dataset({"subs": [], "recs": [], "ids": []}, pt, {})
    st = W.MemStore(blobs)
    st.begin_program()
    return [ln for ln in K._check(f"dataset d = sha256:{mh}\nlet b = bids(d)\nlet t = participants(b)\nclaim {c}\n".encode(), st)[1] if ln.startswith("line")][0]


@pytest.mark.parametrize("c, want", [
    # item 2b (28 Oct 2026; went to the search before): participants(bids(d)) is a table slot of kind "pt", read by
    # bids101.bids_tsv, its certificates datasets made by witness._dataset around the table
    ('count(where(t, eq("g", "A")))', "= 2 (Exact)"),
    ('mean(where(t, ne("x", "n/a")), "x")', "= 1.75 (Exact)"),
    ('share(where(t, eq("g", "A")))', "formed"),
    ('rows(t)', "= 3 (Exact)"),
    ('atleast(count(where(t, eq("g", "A"))), c = 0)', "W1"),
    ('difference(count(where(t, eq("g", "A"))), count(where(t, eq("g", "A"))))', "W1"),
    ('count(where(t, eq("g", "A"), ne("g", "B")))', "W2"),
])
def test_participants_are_decided_exactly(c, want, monkeypatch):
    out = pclaim(c)
    assert want in out and (want[0] != "W" or ("[S008" in out and "decided exactly" in out)), out


@pytest.mark.parametrize("c, want", [
    # item 4 (28 Oct 2026; went to the search before): participant_id (column 1) holds sub-<label>, distinct (B11); a
    # literal that is no label has no row. Regressions: the search refused the first S011 and the second S008 W2 (its
    # candidates relabel column 1, so no candidate held or lacked sub-w1); both form: a dataset without sub-w1 and one
    # with it (and another participant) give two answers
    ('count(where(t, ne(1, "sub-w1")))', "= 2 (Exact)"), ('count(where(t, eq(1, "sub-w1")))', "= 1 (Exact)"),
    ('atmost(count(where(t, eq(1, "sub-w1"))), c = 1)', "W1"), ('count(where(t, eq(1, "sub-1")))', "= 0 (Exact)"),
    ('exceeds(count(where(t, eq(1, "abc"))), c = -1)', "S011"),
    ('extra(participant(b, "w2"), 2)', "formed"), ('number(extra(participant(b, "w3"), 3))', "= 2.5 (Exact)"),
    ('number(extra(participant(b, "w2"), 3))', "V005"), ('extra(participant(b, "x9"), 2)', "V004"),
    ('difference(number(extra(participant(b, "w1"), 3)), number(extra(participant(b, "w1"), 3)))', "W1"),
    ('below(widen(number(extra(participant(b, "w1"), 3)), tolerance = 1), c = 30)', "formed"),
])
def test_participant_id_and_extra_are_decided_exactly(c, want, monkeypatch):
    out = pclaim(c)
    assert want in out and (want != "W1" or ("[S008" in out and "decided exactly" in out)), out


def rclaim(c, tr="1", v=2, ons=("1.5",)):
    """c on a dataset with one BOLD recording, sub-01 task-x (NIfTI-1, dims 1 x 1 x 1 x v), and its events."""
    import hashlib
    from reality4 import kernel as K, readers as R
    from fractions import Fraction
    files = {"dataset_description.json": b'{"Name": "g", "BIDSVersion": "1.0.1"}', "README": b"g\n", "sub-01/func/sub-01_task-x_bold.nii": W._nii((1, 1, 1, v), Fraction(tr)),
             "sub-01/func/sub-01_task-x_bold.json": ('{"TaskName": "x", "RepetitionTime": %s}' % tr).encode(),
             "sub-01/func/sub-01_task-x_events.tsv": ("onset\tduration\n" + "".join(f"{o}\t1\n" for o in ons)).encode()}
    blobs = {hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (R.MANIFEST_MAGIC + "\n" + "".join(f"{hashlib.sha256(files[p]).hexdigest()}\t{len(files[p])}\t{p}\n" for p in sorted(files))).encode()
    blobs[hashlib.sha256(man).hexdigest()] = man
    st = W.MemStore(blobs)
    st.begin_program()
    prog = f'dataset d = sha256:{hashlib.sha256(man).hexdigest()}\nlet b = bids(d)\nlet r = recording(b, "01", "x")\nclaim {c}\n'
    return [ln for ln in K._check(prog.encode(), st)[1] if ln.startswith("line")][0]


@pytest.mark.parametrize("c, want", [
    # item 2c (28 Oct 2026; went to the search before): tr, volumes and onset of one recording, the statement or a
    # comparison of it (SPEC-EXACT 3.8): TRLO < tr < TRHI, 1 <= volumes <= 2^63 - 1, onset < (2^63 - 1) TRHI
    ("tr(r)", "recorded as 1 s"), ("volumes(r)", "= 2 (Exact)"), ("onset(r, 1)", "recorded as 1.5 s"), ("onset(r, 2)", "V002"),
    ("atleast(tr(r), c = 0 s)", "W1"), ("atmost(volumes(r), c = 9223372036854775807)", "W1"), ("atleast(volumes(r), c = 1)", "W1"),
    ("below(tr(r), c = 17" + "0" * 307 + " s)", "W1"), ("below(tr(r), c = 16" + "0" * 307 + " s)", "formed"),
    ("exceeds(tr(r), c = 1/1" + "0" * 335 + " s)", "W1"), ("exceeds(tr(r), c = 1/1" + "0" * 329 + " s)", "formed"),
    ("below(onset(r, 1), c = 1" + "0" * 330 + " s)", "W1"), ("below(onset(r, 1), c = 1" + "0" * 300 + " s)", "formed"),
    ("exceeds(onset(r, 1), c = -1" + "0" * 50 + " s)", "formed"),
    # a certificate would need more than MAX_VOL volumes: R013 (KNOWN-OPEN), never a verdict
    ("below(volumes(r), c = 2000000)", "R013"), ("below(onset(r, 1), c = 1" + "0" * 320 + " s)", "R013"),
])
def test_recording_values_are_decided_exactly(c, want, monkeypatch):
    out = rclaim(c)
    assert want in out and (want != "W1" or ("[S008" in out and "decided exactly" in out)), out


@pytest.mark.parametrize("c, want", [
    # item 3 (28 Oct 2026; went to the search before): a named recording's tr, volumes, onset, duration, events, trials
    # anywhere in a statement (SPEC-EXACT 3.8): duration > 0 (B06), onset < volumes x tr (B30), events >= named rows
    ('widen(tr(recording(b, "01", "x")), tolerance = 1/2 s)', "formed"),
    ('exceeds(widen(onset(recording(b, "01", "x"), 1), tolerance = 1/4 s), c = 1 s)', "formed"),
    ('difference(onset(recording(b, "01", "x"), 3), onset(recording(b, "01", "x"), 1))', "recorded as 7.5 s"),
    ('duration(recording(b, "01", "x"), 3)', "recorded as 1 s"), ('exceeds(duration(recording(b, "01", "x"), 1), c = 0 s)', "W1"),
    ('exceeds(duration(recording(b, "01", "x"), 1), c = 1 s)', "formed"),
    ('events(recording(b, "01", "x"))', "= 3"), ('atleast(events(recording(b, "01", "x")), c = 0)', "W1"),
    ('atleast(events(recording(b, "01", "x")), c = 1)', "formed"),
    ('trials(recording(b, "01", "x"), "go")', "= 2"), ('atleast(trials(recording(b, "01", "x"), "stop"), c = 0)', "W1"),
    ('difference(events(recording(b, "01", "x")), trials(recording(b, "01", "x"), "go"))', "= 1"),
    ('difference(trials(recording(b, "01", "x"), "go"), trials(recording(b, "02", "x"), "go"))', "= 0"),
    ('difference(tr(recording(b, "01", "x")), tr(recording(b, "02", "x")))', "formed"),
    # onset with tr (onset < (2^63 - 1) x tr) or with volumes (onset < volumes x TRHI) of one recording: linear
    ('below(difference(onset(recording(b, "01", "x"), 1), tr(recording(b, "01", "x"))), c = 1 s)', "formed"),
    ('exceeds(difference(onset(recording(b, "01", "x"), 3), tr(recording(b, "01", "x"))), c = 1 s)', "formed"),
    ('below(onset(recording(b, "01", "x"), 3), c = 1' + "0" * 330 + ' s)', "W1"),   # with tr not read: below (2^63 - 1) TRHI
])
def test_recording_values_anywhere_are_decided_exactly(c, want, monkeypatch):
    out = sclaim(c)
    assert want in out and (want != "W1" or ("[S008" in out and "decided exactly" in out)), out


@pytest.mark.parametrize("c", ['trials(recording(b, "01", "x"), "a\\"b")', 'sum(recordings(b, "x"), "trials", "a\\"b")',
                               'trials(recording(b, "02", "x"), "\\"")', 'mean(recordings(b, "x"), "trials", "a\\"b")'])
def test_a_trial_type_no_events_file_holds_counts_zero(c):
    """(G06, Opus 5.5 max review 06) a trial type with a double quote (T005) or a break character (T006) is in no
    readable events file: its count is 0 on every readable dataset, S008 W1 (before G06, the certificate's events file
    was refused B04: X001)."""
    out = sclaim(c)
    assert "[S008" in out and "decided exactly" in out, out


@pytest.mark.parametrize("c, want", [('difference(count(recordings(b, "x")), count(recordings(b, "X")))', "= 3 (Exact)"),
                                     ('sum(recordings(b, "X"), "events")', "= 0 (Exact)")])
def test_look_alike_tasks_of_recordings_refuse_k003_together(c, want):
    """(G07, Opus 5.5 max review 07) a dataset with recordings of tasks x and X refuses K003 (kernel.bold_labels): the
    model branches on it, so the claim forms on a dataset with x only (before G07, X001: its certificates held both)."""
    out = sclaim(c)
    assert "formed" in out and want in out, out


@pytest.mark.parametrize("c, last", [('events(recording(b, "01", "x"))', 4668441), ('trials(recording(b, "01", "x"), "go")', 3408702),
                                     ('sum(recordings(b, "x"), "events")', 4668441), ('sum(recordings(b, "x"), "trials", "go")', 3408702),
                                     ('max(recordings(b, "x"), "events")', 4668441)])
def test_the_read_limit_bounds_the_events_files(c, last):
    """(G04c, Opus 5.5 max review 04 c) an events file is a table read whole: at most 67108864 bytes, the statement's
    text at most 268435456. A named recording's file holds at most (2^26 - 14) / 4 = 16777212 rows ("0<TAB>1"), or
    (2^26 - 25) / 7 = 9586977 rows of type go; a sum over recordings at most 67108848 events (4 files of 16777212: a
    fifth file's header costs more than it holds), at most 38347908 rows of go (4 files of 9586977, 25 + 7 n bytes
    each: 2^28 exactly), and a max of 16777212. One more holds only by the limit (S008); the last needs a certificate
    past MAX_ROWS (R013). Before G04c every one of them was R013. H07 (Opus 5.5 max2 review 07) charges each events table to the memory (Model.evmem): an events file of rows "0<TAB>1" costs 230 bytes a row, so the memory bounds them first: (2^30 - 379) / 230 = 4668441 rows, 3408702 of type go (and in all, a sum's files sharing the memory; H03 held the 13952 bytes the program holds from let b = bids(d), 69 rows
    lower, 50 of go: B0304, Argon review 2 04, drops them as the inline claim does, since they are made from the dataset it reads); before H07 the text bounded them, 16777212, 9586977, 67108848, 38347908."""
    out = sclaim(f"below({c}, c = {last + 1})")
    assert "[S008" in out and "it holds only by the read limit" in out, out
    out = sclaim(f"below({c}, c = {last})")
    assert "[R013" in out, out
    assert "[S008" in sclaim(f"below({c}, c = 1000000000)")


@pytest.mark.parametrize("q", ['sum(recordings(b, "x"), "volumes")', 'sum(recordings(b, "x"), "trials", "go")', 'max(recordings(b, "x"), "events")'])
def test_the_read_limit_bounds_the_events_files_necessarily(q):
    """(G04c) two quantities of recordings (3.9a, 3.9b), or a sum beside a max (3.9e): the events files' rows within
    MAX_TEXT_FILE each in all and the statement's text, a necessary bound (Model.rs_evm, rs_evlb): far past it S008 by
    the read limit (before G04c: R013, and the sum beside a max built a list of y / m recordings, killed for memory)."""
    out = sclaim(f'below(difference(sum(recordings(b, "x"), "events"), {q}), c = 1000000000)')
    assert "[S008" in out and "it holds only by the read limit" in out, out


@pytest.mark.parametrize("c, want", [('count(recordings(b, "x", participants(b)))', "formed"),
                                     ('difference(count(recordings(b, "x", participants(b))), rows(participants(b)))', "W2")])
def test_the_participant_filter_bears_through_v007(c, want):
    """(H06, Opus 5.5 max2 review 06, the code route for max review 08; overturns v4 fix 08 and Phase F's S008 W2) on a dataset without participants.tsv the filter refuses V007 and the statement
    without it answers, so the filter bears (before G08: S008 W2); with participants() read elsewhere both refuse V007
    there, and on every other dataset the filter of all participants keeps every recording (B11): idle, S008 W2."""
    out = sclaim(c)
    assert want in out if want == "formed" else ("[S008" in out and "W2" in out), out


def sclaim(c, groups=None):
    """c on the Phase F dataset (tests/test_v4_phase_f.py: sub-01, 02, 03, task x, 5 volumes, TR 2 s, events go/stop/go);
    groups: the participants' groups (default 01 a, 02 b, 03 a)."""
    import hashlib, os, tempfile
    import bidsfix
    from reality4 import kernel as K, readers as R
    root = bidsfix.mini(os.path.join(tempfile.mkdtemp(), "ds"), subjects=("01", "02", "03"), groups=groups or {"01": "a", "02": "b", "03": "a"},
                        events="onset\tduration\ttrial_type\n1.5\t2\tgo\n7.25\t2\tstop\n9\t1\tgo\n")
    files = {os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/"): open(os.path.join(d, f), "rb").read() for d, _, fs in os.walk(root) for f in fs}
    blobs = {hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (R.MANIFEST_MAGIC + "\n" + "".join(f"{hashlib.sha256(files[p]).hexdigest()}\t{len(files[p])}\t{p}\n" for p in sorted(files))).encode()
    blobs[hashlib.sha256(man).hexdigest()] = man
    st = W.MemStore(blobs)
    st.begin_program()
    return [ln for ln in K._check(f"dataset d = sha256:{hashlib.sha256(man).hexdigest()}\nlet b = bids(d)\nclaim {c}\n".encode(), st)[1] if ln.startswith("line")][0]


@pytest.mark.parametrize("c, want", [
    # (R1, 28 Oct 2026; went to the search before): count, sum, mean, min, max of recordings(b, task) (SPEC-EXACT 3.9)
    ('count(recordings(b, "x"))', "= 3"), ('count(recordings(b, "y"))', "= 0"), ('sum(recordings(b, "x"), "volumes")', "= 15"),
    ('min(recordings(b, "x"), "volumes")', "= 5"), ('mean(recordings(b, "x"), "tr")', "recorded as 2 s"),
    ('sum(recordings(b, "x"), "trials", "go")', "= 6"), ('mean(recordings(b, "x"), "events")', "= 3"),
    ('sum(recordings(b, "y"), "tr")', "= 0 s"),   # no recording: 0, not recorded; with one: recorded (two answers)
    ('atleast(min(recordings(b, "x"), "tr"), c = 0 s)', "W1"), ('exceeds(min(recordings(b, "x"), "volumes"), c = 0)', "W1"),
    ('atleast(widen(sum(recordings(b, "x"), "events"), tolerance = 2), c = 0)', "W1"),
    ('below(min(recordings(b, "x"), "tr"), c = 170000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 s)', "W1"), ('below(min(recordings(b, "x"), "tr"), c = 160000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 s)', "formed"),
    ('exceeds(max(recordings(b, "x"), "tr"), c = 1/100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 s)', "W1"), ('exceeds(max(recordings(b, "x"), "tr"), c = 1/100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 s)', "formed"),
    # the value 0 of a tr sum minus itself: recorded or not (an answer each), not one answer (bfrs seed 1, before commit)
    ('widen(difference(sum(recordings(b, "x"), "tr"), sum(recordings(b, "x"), "tr")), tolerance = 1 s)', "formed"),
    ('below(widen(mean(recordings(b, "x"), "volumes"), tolerance = 1/4), c = 6)', "formed"),   # a mean of whole numbers: S/N
    ('atmost(sum(recordings(b, "x"), "volumes"), c = 1000)', "formed"),
    # a certificate holds at most MAX_VOL volumes in all [prov]: failing needs more (KNOWN-OPEN)
    ('atmost(sum(recordings(b, "x"), "volumes"), c = 1000000000)', "R013"),
    # (R2, 28 Oct 2026; went to the search before): a set filtered by participants(b) or a where() of it; the regions of
    # the types the sets and their parts' wholes tell apart (SPEC-EXACT 3.9)
    ('count(recordings(b, "x", where(participants(b), eq("group", "a"))))', "= 2"),
    ('sum(recordings(b, "x", where(participants(b), eq("group", "b"))), "trials", "go")', "= 2"),
    ('count(recordings(b, "x", participants(b)))', "= 3 (Exact)"),   # (H06) bears through V007; was W2 (B11, v4 fix 08)
    ('count(recordings(b, "x", where(participants(b), eq("group", "a"), eq("group", "a"))))', "W2"),
    ('widen(difference(count(recordings(b, "x", where(participants(b), eq("group", "a")))), count(recordings(b, "x", where(participants(b), eq("group", "b"))))), tolerance = 1)', "formed"),
    ('atmost(count(recordings(b, "x", where(participants(b), eq("group", "z")))), c = 6)', "formed"),
    ('widen(max(recordings(b, "x", where(participants(b), eq("group", "a"))), "volumes"), tolerance = 1)', "formed"),
    ('widen(mean(recordings(b, "x", where(participants(b), eq("group", "a"))), "tr"), tolerance = 1 s)', "formed"),
    ('atleast(min(recordings(b, "x", where(participants(b), eq("group", "a"))), "tr"), c = 0 s)', "W1"),
    ('atleast(sum(recordings(b, "x", where(participants(b), ne("group", "c"))), "tr"), c = 10 s)', "V001"),
])
def test_recording_sets_are_decided_exactly(c, want, monkeypatch):
    out = sclaim(c)
    assert want in out and (want not in ("W1", "W2") or ("[S008" in out and "decided exactly" in out)), out


ALLA = {"01": "a", "02": "a", "03": "a"}


@pytest.mark.parametrize("c, groups", [
    # (G01, Opus 5.5 max review 01) two recordings() values over the same recordings are one identity (SPEC 5.1: the
    # kernel's is the recordings read), so on a dataset where the filter keeps every participant their difference is
    # exactly 0 and a comparison of it holds: the model said the identities differ on every input (S011, X001)
    ('atleast(difference(widen(sum(recordings(b, "x", where(participants(b), eq("group", "a"))), "volumes"), tolerance = 1), widen(sum(recordings(b, "x"), "volumes"), tolerance = 1)), c = 0)', ALLA),
    ('difference(widen(sum(recordings(b, "x", where(participants(b), eq("group", "a"))), "volumes"), tolerance = 1), widen(sum(recordings(b, "x"), "volumes"), tolerance = 1))', ALLA),
    # two tasks' sets, both empty here: one identity (the kernel's: no recordings), 0 exactly (formed before too: kept
    # for the two-task branch of Model.idsize)
    ('difference(widen(sum(recordings(b, "y"), "volumes"), tolerance = 1), widen(sum(recordings(b, "z"), "volumes"), tolerance = 1))', None),
    ('atleast(difference(widen(sum(recordings(b, "y"), "volumes"), tolerance = 1), widen(sum(recordings(b, "z"), "volumes"), tolerance = 1)), c = 0)', None),
])
def test_recording_sets_over_the_same_recordings_are_one_value(c, groups):
    out = sclaim(c, groups)
    assert "formed" in out and "X001" not in out and "S011" not in out, out


def test_presolve_and_relaxation_keep_the_answers():
    # equalities over counts are replaced (SPEC-EXACT 4.1); the rational relaxation proves "none" by a checked certificate
    A = [D.ge({("n", "s", 1): 1, ("n", "s", 2): -1}), D.ge({("n", "s", 1): -1, ("n", "s", 2): 1}), D.ge({("n", "s", 2): 1, D.ONE: -2})]
    atoms, subs = D.presolve(A)
    assert len(subs) == 1
    assert D.lp([({("n", "s", 1): 1}, -1), ({("n", "s", 1): -1}, 0)])[0] == "none"
    assert D.lp([({("n", "s", 1): 2}, -1)]) is None or D.lp([({("n", "s", 1): 2}, -1)])[0] == "point"


# ---- part H (phase 5): JSON paths, NIfTI dims, size and bytes -------------------------------------------

def _h(tmp_path, c):
    import bidsfix
    pj, hj = tsv(tmp_path, "j.json", '{"a": [10, 20, 30], "b": 4, "c": {"d": "x"}}')
    pn, hn = tsv(tmp_path, "img.nii", bidsfix.nifti1((64, 64, 30, 10), tr=2.0))
    pr, hr = tsv(tmp_path, "r.bin", "hello world")
    ok, text = run(f"file g = sha256:{hj}\nfile n = sha256:{hn}\nfile r = sha256:{hr}\nclaim {c}\n", [pj, pn, pr])
    return line(text, 4)


@pytest.mark.parametrize("c, want", [
    ('member(json(g), "b")', "= 4 (Exact)"),
    ('item(member(json(g), "a"), 2)', "= 20 (Exact)"),
    ('member(member(json(g), "c"), "d")', '= "x"'),
    ('difference(member(json(g), "b"), member(json(g), "b"))', "[S008"),
    ('widen(member(json(g), "b"), tolerance = 1)', "lies within [3, 5]"),
    ('dim(nifti(n), 1)', "= 64 (Exact)"),                        # finding 16: spatial dims form
    ('exceeds(dim(nifti(n), 1), c = 32)', "holds"),
    ('below(dim(nifti(n), 4), c = 40000)', "holds"),              # a dim past int16 is a NIfTI-2 header
    ('size(r)', "= 11 (Exact)"),
    ('bytes(r, 0, 5)', '= "hello"'),
    ('atleast(size(r), c = 11)', "holds"),                        # the search missed it
    ('difference(size(r), size(r))', "[S008"),
])
def test_part_h_is_decided_exactly(tmp_path, c, want, monkeypatch):
    out = _h(tmp_path, c)
    assert want in out and ("[S0" not in want or "decided exactly" in out), out


@pytest.mark.parametrize("c, want", [('member(json(g), "")', "= 5 (Exact)"), ('member(member(json(g), "a"), "")', "= 6 (Exact)"),
                                     ('exceeds(member(json(g), ""), c = 0)', "holds")])
def test_a_json_member_named_empty_is_decided(tmp_path, c, want):
    """(G09, Opus 5.5 max review 09) the empty key is a JSON key: the certificate's filler member is named apart from
    the object's named members (build.jtext; before G09 it was "" too, the document held "" twice: J002, X001)."""
    pj, hj = tsv(tmp_path, "j.json", '{"": 5, "a": {"": 6}}')
    ok, text = run(f"file g = sha256:{hj}\nclaim {c}\n", [pj])
    out = line(text, 2)
    assert "formed" in out and want in out, out


@pytest.mark.parametrize("c, want", [
    # the variance shape (SPEC-EXACT 3.7, 28 Oct 2026; went to the search before): a sum of signed variances of one table,
    # at least three or two with a widen() inside; the first two are test_v4_opass's (formed on the search, still form)
    ('difference(sample_variance(tsv(f), 1), widen(sample_variance(tsv(f), 2), tolerance = 1))', "lies within [-1, 1]"),
    ('difference(difference(sample_variance(tsv(f), 1), sample_variance(tsv(f), 2)), population_variance(tsv(f), 1))', "= -1 (Exact)"),
    ('atmost(difference(difference(sample_variance(tsv(f), 1), sample_variance(tsv(f), 2)), population_variance(tsv(f), 1)), c = 0)', "holds"),
    # V1 - V1 cancels; sample minus population of one column is Vp/(n - 1) >= 0, so the comparison always holds
    ('difference(difference(sample_variance(tsv(f), 1), population_variance(tsv(f), 1)), difference(sample_variance(tsv(f), 1), population_variance(tsv(f), 1)))', "[S008"),
    ('exceeds(difference(difference(sample_variance(tsv(f), 2), difference(population_variance(tsv(f), 2), sample_variance(tsv(f), 1))), sample_variance(tsv(f), 1)), c = -1)', "[S008"),
    ('atleast(widen(difference(sample_variance(tsv(f), 2), widen(sample_variance(tsv(f), 1), tolerance = 1)), tolerance = 1/2), c = 1)', "[V006"),
    # one value widened twice is one symbol (SPEC 5.2): widen(V) - widen(V) is 0 exactly, and the widths cancel (nwidth);
    # brute force found the comparison below refused X001 when the widths were added (bfvs seed 2, 28 Oct 2026)
    ('difference(widen(population_variance(tsv(f), 1), tolerance = 1), widen(population_variance(tsv(f), 1), tolerance = 1))', "[S008"),
    ('difference(difference(widen(sample_variance(tsv(f), 1), tolerance = 1), population_variance(tsv(f), 2)), widen(sample_variance(tsv(f), 1), tolerance = 1))', "= -1 (Exact)"),
    ('atleast(difference(difference(widen(population_variance(tsv(f), 2), tolerance = 1/2), sample_variance(tsv(f), 1)), widen(difference(widen(population_variance(tsv(f), 2), tolerance = 1/2), sample_variance(tsv(f), 2)), tolerance = 1/2)), c = -3)', "holds"),
    # a widened variance first in a difference is a variance difference (kernel.is_square; refused X001 / S006 before)
    ('difference(difference(widen(sample_variance(tsv(f), 1), tolerance = 1), population_variance(tsv(f), 2)), difference(widen(population_variance(tsv(f), 1), tolerance = 1/2), sample_variance(tsv(f), 2)))', "lies within"),
])
def test_variance_shape_is_decided_exactly(tmp_path, c, want, monkeypatch):
    p, h = tsv(tmp_path, "f.tsv", "v\tw\n1\t5\n3\t7\n")
    ok, text = run(f"file f = sha256:{h}\nclaim {c}\n", [p])
    out = line(text, 2)
    assert want in out and ("[S0" not in want or "decided exactly" in out), out


@pytest.mark.parametrize("c, want", [
    # SPEC-EXACT 3.10 (28 Oct 2026; went to the search before): one file read by nifti() and size(): a header and the
    # file's size, at least 544 bytes (NIfTI-2), 352 (NIfTI-1, dims within int16) or 19 (gzip; the certificate's own
    # gzip member and zero padding when larger). The search refused the 2nd and 3rd S008 W1 at size() (its candidates
    # kept the real file's size); the size varies with the header kept, so they form
    ('below(difference(dim(nifti(n), 1), size(n)), c = 1)', "holds"),
    ('difference(dim(nifti(n), 1), size(n))', "= -1229088 (Exact)"),
    ('atleast(difference(size(n), dim(nifti(n), 1)), c = 545)', "holds"),
    ('difference(size(n), size(n))', "[S008"),
    ('difference(size(n), dim(nifti(n), 9))', "[V008"),
])
def test_one_file_read_by_nifti_and_size_is_decided_exactly(tmp_path, c, want, monkeypatch):
    out = _h(tmp_path, c)
    assert want in out and ("[S0" not in want or "decided exactly" in out), out


@pytest.mark.parametrize("c, want", [
    # SPEC-EXACT 3.10: one file read by csv() and rows() of tsv(): a file both read has no double quote (TSV T005) and so
    # no quoted field, no comma inside a cell and one tsv() column: the csv() table's rows are the tsv() rows
    ('difference(rows(tsv(f)), rows(csv(f)))', "[S008"),
    ('difference(count(where(csv(f), eq(1, "a,b"))), rows(tsv(f)))', "[S011"),   # a cell holding a comma is quoted
    ('difference(count(where(csv(f), eq(1, "x"))), rows(tsv(f)))', "= -1 (Exact)"),
    ('atleast(rows(tsv(f)), c = 2)', "holds"),
])
def test_one_file_read_by_tsv_and_csv_is_decided_exactly(tmp_path, c, want, monkeypatch):
    p, h = tsv(tmp_path, "f.csv", "c\nx\ny\n")
    ok, text = run(f"file f = sha256:{h}\nclaim {c}\n", [p])
    out = line(text, 2)
    assert want in out and ("[S0" not in want or "decided exactly" in out), out


@pytest.mark.parametrize("c, want", [
    # SPEC-EXACT 3.10 (tc1, 28 Oct 2026): tsv() and csv() of one file each read only as number(cell(., r, 1)) or rows():
    # on a one-column file both readers read the same cells; on a wider one every tsv() cell holds a comma, so its number()
    # refuses. The first went to the search (test_14, test_outside_part_t), which refused S008 W1 as well
    ('difference(number(cell(tsv(f), 1, 1)), number(cell(csv(f), 1, 1)))', "[S008"),
    ('difference(number(cell(tsv(f), 2, 1)), number(cell(csv(f), 1, 1)))', "= 1 (Exact)"),
    ('exceeds(difference(number(cell(tsv(f), 2, 1)), number(cell(csv(f), 1, 1))), c = 0)', "holds"),
    ('atmost(difference(number(cell(csv(f), 1, 1)), number(cell(tsv(f), 1, 1))), c = 0)', "[S008"),
])
def test_one_file_read_by_tsv_and_csv_cells_is_decided_exactly(tmp_path, c, want, monkeypatch):
    p, h = tsv(tmp_path, "f.csv", "c\n1\n2\n")
    ok, text = run(f"file f = sha256:{h}\nclaim {c}\n", [p])
    out = line(text, 2)
    assert want in out and ("[S0" not in want or "decided exactly" in out), out


# ---- (f) pixdim: float64 values times the time unit (SPEC-EXACT 3.6) ----------------------------------------

FMAX = 179769313486231570814527423731704356798070567525844996598917476803157260780028538760589558632766878171540458953514382464234321326889464182768467546703537516986049910576551282076245490090389328944075868508455133942304583236903222948165808559332123348274797826204144723168738177180919299881250404026184124858368
E45 = "0." + "0" * 44 + "1"


def _p(tmp_path, c):
    import bidsfix
    pn, hn = tsv(tmp_path, "n.nii", bidsfix.nifti1((64, 64, 30, 10), tr=2.0))
    pm, hm = tsv(tmp_path, "m.nii", bidsfix.nifti1((64, 64, 30, 10), tr=1500.0, units=18))   # ms
    ok, text = run(f"file n = sha256:{hn}\nfile m = sha256:{hm}\nclaim {c}\n", [pn, pm])
    return line(text, 3)


@pytest.mark.parametrize("c, want", [
    ("pixdim(nifti(n), 4)", "recorded as 2 s"),
    ("difference(pixdim(nifti(n), 4), pixdim(nifti(m), 4))", "recorded as 0.5 s"),
    ("difference(pixdim(nifti(n), 4), pixdim(nifti(n), 4))", "[S008"),
    ("exceeds(widen(pixdim(nifti(n), 4), tolerance = 0.1 s), c = 1 s)", "holds"),
    ("atleast(pixdim(nifti(n), 4), c = -1 s)", "holds"),                        # a pixdim may be negative
    (f"below(pixdim(nifti(n), 4), c = {FMAX} s)", "holds"),                     # the largest float fails it
    (f"below(pixdim(nifti(n), 4), c = {FMAX + 1} s)", "[S008"),                 # no float reaches it
    (f"below(widen(pixdim(nifti(n), 4), tolerance = 1 s), c = {FMAX - 2} s)", "[S008"),   # no float within 1 s of it
    (f"below(widen(difference(pixdim(nifti(n), 4), pixdim(nifti(m), 4)), tolerance = {E45} s), c = 0.6 s)", "holds"),
    # no two floats times their units land within 10^-45 s of 0.4285714285714285714285714285714285 s (fwin; R013 after
    # 143 s before it, a wrong code: partb/X1/pixwin-hard.txt); 300 ms - 0 lands on 0.3 s exactly
    (f"exceeds(widen(difference(pixdim(nifti(n), 4), pixdim(nifti(m), 4)), tolerance = {E45} s), c = 0.4285714285714285714285714285714285 s)", "[S008"),
    (f"exceeds(widen(difference(pixdim(nifti(n), 4), pixdim(nifti(m), 4)), tolerance = {E45} s), c = 0.3 s)", "holds"),
])
def test_pixdim_is_decided_exactly(tmp_path, c, want, monkeypatch):
    out = _p(tmp_path, c)
    assert want in out and ("[S0" not in want or "decided exactly" in out), out


def test_two_floats_in_one_window_are_decided_exactly():
    from fractions import Fraction as F
    u, v, one = ("z", "pix", "n"), ("z", "pix", "m"), D.ONE
    box = [D.ge({u: 1, one: D.FMAX}), D.ge({u: -1, one: D.FMAX}), D.ge({v: 1, one: D.FMAX}), D.ge({v: -1, one: D.FMAX})]
    w = F(1, 10 ** 45)
    for a, b, f1, f2 in [(0.1, 2.0 ** -1000, F(1), F(1, 1000)), (-3.5e300, -1e-310, F(1, 10 ** 6), F(1)), (1.0, 1.0, F(1), F(1, 10 ** 6))]:
        C = f1 * F(a) - f2 * F(b) + w / 3
        P = D.fwin(box + [D.ge({u: f1, v: -f2, one: -(C - w)}), D.ge({u: -f1, v: f2, one: C + w})], [0])
        x = {next(k for k in A[0] if k != one): -A[0][one] for A in P[::2]}
        assert D.is_float(x[u]) and D.is_float(x[v]) and C - w <= f1 * x[u] - f2 * x[v] <= C + w
    C = F("0.4285714285714285714285714285714285")   # no pair in s and s (the other units: partb/X1/pixwin-hard.txt)
    assert D.fwin(box + [D.ge({u: 1, v: -1, one: -(C - w)}), D.gt({u: -1, v: 1, one: C + w})], [0]) == []
    assert D.fwin(box + [D.ge({u: 1, v: -1, ("n", "t", "A"): 1})], [0]) is None   # another variable: not this shape


def test_float_helpers_match_the_floats():
    import math
    import random
    from fractions import Fraction as F
    rng = random.Random(3)
    xs = [0.0, 5e-324, 2.0 ** -1022, 2.0 ** -1022 - 5e-324, 1.0, 0.5, 3.0, 1.7976931348623157e308]
    xs += [2.0 ** rng.uniform(-1074, 1024) for _ in range(3000)]
    for x in (y for x in xs if not math.isinf(x) for y in (x, -x)):
        q, up = F(x), math.nextafter(x, math.inf)
        assert D.is_float(q) and D.fnext(q) == (None if math.isinf(up) else F(up)), x
        if not math.isinf(up):
            assert not D.is_float((q + F(up)) / 2)
    z = ("z", "pix", "n")   # a one-binade range's lattice holds only floats; every float of a range is on its lattice
    for e in [D.EMIN, D.EMIN + 1, -60, 0, 52, D.EMAX]:
        A = D.frange(z, 1, e, e)
        st, lo, hi = F(2) ** e, -A[2][0][1], A[3][0][1]
        assert all(D.is_float(st * j) for j in (lo, lo + 1, (lo + hi) // 2, hi - 1, hi))
    for x in xs[8:200]:
        sg, ea, eb = D.frange_of(z, D.frange(z, 1, D.EMIN, D.EMAX))
        assert (F(x) / F(2) ** ea).denominator == 1


def test_empty_box_only_says_empty_without_a_solution():
    import itertools
    import random
    rng, said = random.Random(4), 0
    for _ in range(1500):
        vs = ["a", "b"][:rng.randint(1, 2)]
        ints = [({v: c for v in vs for c in [rng.randint(-6, 6)] if c} or {"a": 1}, rng.randint(-20, 20)) for _ in range(rng.randint(1, 4))]
        if D.empty_box(ints, [0]):
            said += 1
            assert not any(all(sum(c * x[vs.index(v)] for v, c in G.items()) + k >= 0 for G, k in ints) for x in itertools.product(range(41), repeat=len(vs))), ints
    assert said > 100


# ---- the variance phase: variances and SDs (SPEC-EXACT 3.7) ----------------------------------------------

V4 = "id\tg\tx\na\tF\t18\nb\tF\t27\nc\tM\t4\nd\tF\t25\n"


@pytest.mark.parametrize("c, want", [
    ('sample_variance(where(t, eq("g", "F")), "x")', "= 67/3 (Exact)"),
    ('population_sd(where(t, eq("g", "F")), "x")', "= sqrt(134/9) (Exact)"),
    ('below(sample_sd(where(t, eq("g", "F")), "x"), c = 4.73)', "holds"),
    ('exceeds(population_variance(where(t, ge("x", c = 0), le("x", c = 30)), "x"), c = 1)', "holds"),
    ('atmost(sample_variance(where(t, ge("x", c = 0), le("x", c = 30)), "x"), c = 450)', "[S008"),   # (30 - 0)^2/2 = 450 is the largest [Var]
    ('atleast(population_sd(where(t, eq("g", "F")), "x"), c = -1)', "[S008"),                        # an SD is never below 0
    ('sample_variance(where(t, eq("g", "F"), ne("g", "M")), "x")', "[S008"),                         # idle condition: W2
])
def test_variances_are_decided_exactly(tmp_path, c, want, monkeypatch):
    out = claim(tmp_path, c, V4)
    assert want in out and ("[S0" not in want or "decided exactly" in out), out


def test_variance_shapes_are_decided_exactly(tmp_path, monkeypatch):
    # under widen (item 5a) and in a difference of two variances (item 5b) a variance is in the exact fragment
    for c in ('below(widen(sample_sd(where(t, eq("g", "F")), "x"), tolerance = 0.1), c = 5)',
              'below(difference(sample_variance(where(t, eq("g", "F")), "x"), sample_variance(t, "x")), c = 5)'):
        assert "[S013" not in claim(tmp_path, c, V4)


def test_one_column_scaled_alone_finds_the_coupled_witness(tmp_path):
    # bfc seed 7 (partb/Eh/bfc7.txt): two variances of two columns over shared rows; on (A 0.5 0), (A 0.5 0.77) the
    # value lies in [0.28645, 0.30645] (V006), so widen() bears on the answer. The multiset search refused R013 at
    # MAX_CASES (12.6 s): it scaled every column together; column 3 scaled alone reaches the window (item (h), 28 Oct 2026)
    c = 'below(widen(difference(sample_variance(t, 3), population_variance(where(t, ge("x", c = 0.25), le("x", c = 0.75)), 2)), tolerance = 0.01), c = 0.3)'
    assert claim(tmp_path, c, "g\tx\ty\nB\t0\t1\nB\t0.5\t0\nB\t2\t1\nB\t2\t1\n").endswith("holds")
    assert "[V006" in claim(tmp_path, c, "g\tx\ty\nA\t0.5\t0\nA\t0.5\t0.77\n")


def test_a_mean_below_half_way_from_a_median_to_its_top_is_decided(tmp_path):
    # Item 1 (28 Oct 2026, SPEC-EXACT 3.5a half cuts): mean(x <= 1) - median(x > 0.4) stays below (1 - 0.4)/2 = 0.3 on
    # every input (the rows at or below the median are at least half of the mean's rows), so atmost c = 0.5 and c = 0.3
    # hold on every answering input: S008 W1 (bfe1 claim 60 refused R013, and before the memory charge ran out of
    # memory). The cut does not reach past the supremum: 4 rows at 0.41 and 3 at 1 give 0.2528..., above 0.25.
    d = 'difference(mean(where(t, le("x", c = 1)), 2), median(where(t, gt("x", c = 0.4)), 2))'
    for c in ("0.5", "0.3"):
        r = claim(tmp_path, f"atmost({d}, c = {c})", "g\tx\ty\nA\t2\t0\nB\t2\t0\nA\t2\t0\nA\t0\t1\n")
        assert "[S008" in r and "W1" in r, r
    seven = "g\tx\ty\n" + "A\t0.41\t0\n" * 4 + "A\t1\t0\n" * 3
    assert "[V001" in claim(tmp_path, f"below({d}, c = 0.25)", seven)


def test_a_mean_with_no_row_past_an_order_statistic_is_on_its_side(tmp_path):
    # Item 1 (SPEC-EXACT 3.5a, a = 0): brute force Y1/bfh1 (seed 1) found three claims that hold on every answering
    # input refusing R013 (26.1 s, 22.3 s, 179.3 s): a mean of rows none of which lies past the order statistic. Each
    # is S008 W1 now; the mean of rows below and at a max is at most it, of rows above and at a min at least it.
    for c in ('atmost(difference(mean(t, 2), max(where(t, ge("x", c = 0.5)), 2)), c = 0.5)',
              'exceeds(difference(mean(t, 2), order(where(t, le("x", c = 1)), 2, 1)), c = -0.3)',
              'below(difference(mean(where(t, gt("x", c = 0.4)), 2), max(where(t, ge("x", c = 0.5)), 2)), c = 0.31)'):
        r = claim(tmp_path, c, "g\tx\ty\nA\t0.5\t0\nA\t1\t0\n")
        assert "[S008" in r and "W1" in r, (c, r)
    assert "[S008" not in claim(tmp_path, 'atmost(difference(mean(t, 2), max(where(t, ge("x", c = 0.5)), 2)), c = -0.1)', "g\tx\ty\nA\t0.5\t0\nA\t1\t0\n")


def test_side_work_cannot_change_finds_path(tmp_path, monkeypatch):
    # BB's call (28 Oct 2026 17:10): a verdict must not depend on how side work is charged. Twice an accounting charge
    # inside find()'s first-round cap (4,096 steps) moved an option to a later round and changed what was decided: Mem6
    # (memory in the steps: a bfp seed 1 claim R013 instead of forming) and the half cuts' lp tests (implied: pn450 formed
    # in 352 s, then no verdict in 1,300 s). Side work is charged to the step bound only (decide.side): here every lp
    # test charges 1,000,000 more side steps and find() makes the same solves to the same certificate; with side work
    # charged to the round's steps (the old way) the same charge changes its path, so this test tells the two apart.
    c = 'atmost(difference(mean(t, 2), max(where(t, ge("x", c = 0.5)), 2)), c = -0.1)'
    rows = "g\tx\ty\nA\t0.5\t0\nA\t1\t0\n"
    n, im0, os0 = {"solves": 0, "capped": 0}, D.Model.implied, D.Model.one_solve

    def so(self, *a, **k):
        n["solves"] += 1
        return os0(self, *a, **k)

    def im(self, ints, F, budget, extra=0):
        n["capped"] += len(budget) > 1 and budget[1] > 0
        D.side(budget, extra)
        return im0(self, ints, F, budget)

    def go(extra):
        n.update(solves=0, capped=0)
        monkeypatch.setattr(D.Model, "implied", lambda self, i, F, b: im(self, i, F, b, extra))
        return claim(tmp_path, c, rows), n["solves"], n["capped"]

    monkeypatch.setattr(D.Model, "one_solve", so)
    plain, side = go(0), go(10 ** 6)
    assert "formed" in plain[0] and plain[2] > 0, plain   # lp tests made inside a capped round
    assert side[:2] == plain[:2], (plain, side)
    monkeypatch.setattr(D, "side", lambda budget, k: budget.__setitem__(0, budget[0] + k))   # the old way
    assert go(10 ** 6)[1] > plain[1]


def test_elimination_is_charged_before_its_work():
    """(e2) fm refuses (Big) before an elimination step would take its charge past the steps left (SPEC-EXACT 8):
    k lower and k upper bounds of one rational variable make k*k atoms; within the steps left it eliminates as before."""
    z, k = ("z", "y", "s", "t", 1), 40
    atoms = [D.ge({z: 1, ("n", "s", i): -1}) for i in range(k)] + [D.ge({z: -1, ("n", "s", k + i): 1}) for i in range(k)]
    rest, stack = D.fm(atoms, [z], 2 * k + k * k)
    assert len(rest) == k * k and len(stack[0][1]) == 2 * k
    assert D.fm(atoms, [z])[0] == rest
    with pytest.raises(D.Big):
        D.fm(atoms, [z], 2 * k + k * k - 1)


# ---- (F02; Opus 5.5 review 02, BB's call 29 Oct 2026) the readable inputs are bounded (SPEC-EXACT 1): each table at
# most MAX_TEXT_FILE bytes, the statement's text at most MAX_TEXT_TOTAL. A claim that holds only by these bounds is
# S008 W1 with its own reason, in every shape (rows(), size(), the text total); one that holds regardless stays plain.

LIM = "it holds only by the read limit"


def prog(tmp_path, text, claims):
    p, h = tsv(tmp_path, "f.tsv", text)
    ok, out = run(f"file f = sha256:{h}\n" + "".join(f"claim {c}\n" for c in claims), [p])
    return [line(out, i + 2) for i in range(len(claims))]


def test_a_count_past_the_read_limit_is_decided_not_x001(tmp_path):
    """Opus 02: 99999 rows of a 700-byte cell are past 64 MiB: the claim holds on every readable input (S008 by the
    read limit, not X001); at 600 bytes a failing input is readable (formed); 200000 rows of 400 bytes likewise S008."""
    out = prog(tmp_path, "g\n" + "a" * 700 + "\nb\n", [f'below(count(where(tsv(f), eq(1, "{"a" * 700}"))), c = 99999)'])
    assert "[S008" in out[0] and LIM in out[0], out
    assert "formed" in prog(tmp_path, "g\n" + "a" * 600 + "\nb\n", [f'below(count(where(tsv(f), eq(1, "{"a" * 600}"))), c = 99999)'])[0]
    out = prog(tmp_path, "g\n" + "a" * 400 + "\nb\n", [f'below(count(where(tsv(f), eq(1, "{"a" * 400}"))), c = 200000)'])
    assert "[S008" in out[0] and LIM in out[0], out


def test_rows_past_the_read_limit(tmp_path):
    """Opus 02 (rows): a one-column table's rows are each 2 bytes of text, but (unit G05) 64 + 80 + 1 accounted bytes
    in memory: a readable table has at most 7304364 rows (the real reader keeps 7304364 and refuses 7304365 R012).
    40000000, 33554432 and 7304365 hold only by the limit; 7304364 rows are readable but past MAX_ROWS (R013). Before
    G05, 20000000 was R013 though the reader refuses it R012."""
    out = prog(tmp_path, "g\na\nb\n", ["below(rows(tsv(f)), c = 40000000)", "below(rows(tsv(f)), c = 33554432)", "below(rows(tsv(f)), c = 7304365)", "below(rows(tsv(f)), c = 7304364)"])
    assert all("[S008" in o and LIM in o for o in out[:3]), out
    assert "[R013" in out[3], out


def test_size_past_the_read_limit(tmp_path):
    """Opus 02 (size): size(f) − rows is at most 67108864 only by the limit (S008, its reason); 67108863 is passed."""
    out = prog(tmp_path, "g\na\nb\n", ["atmost(difference(size(f), rows(tsv(f))), c = 67108864)", "atmost(difference(size(f), rows(tsv(f))), c = 67108863)"])
    assert "[S008" in out[0] and LIM in out[0], out
    assert "formed" in out[1], out


def test_the_statements_text_total_is_a_read_limit(tmp_path):
    """(256 MiB) six reads of one table charge its text six times. Rows of a 300-byte literal (301 bytes each; unit G05:
    short rows meet the memory limit first) fit (2^28 / 6 - 1) / 301 = 148635 times: 148636 holds only by the total;
    148635 is readable but past MAX_ROWS (R013)."""
    L = "a" * 300
    c = lambda v: f'count(where(tsv(f), eq(1, "{v}")))'   # noqa: E731
    e = f"difference(difference({c(L)}, {c('z')}), difference(difference({c('y')}, {c('z')}), difference({c('y')}, {c('v')})))"
    out = prog(tmp_path, "g\na\nb\n", [f"below({e}, c = 148636)", f"below({e}, c = 148635)"])
    assert "[S008" in out[0] and LIM in out[0], out
    assert "[R013" in out[1], out


def test_a_let_is_read_once_in_its_own_statement(tmp_path):
    """(G03, Opus 5.5 max review 03) the kernel reads a let once, in its own statement with its own text total, and a
    claim using it reads nothing for it: with t a let, 80,000 rows of a 600-byte literal (48 MB, one read) are a
    readable input on which the claim fails, so it forms; with tsv(f) written six times, 288 MB is past the total and it
    holds only by the read limit (S008, as before)."""
    L = "a" * 600
    c = lambda t, v: f'count(where({t}, eq(1, "{v}")))'   # noqa: E731
    e = lambda t: f"difference(difference({c(t, L)}, {c(t, 'z')}), difference(difference({c(t, 'y')}, {c(t, 'z')}), difference({c(t, 'y')}, {c(t, 'v')})))"   # noqa: E731
    assert "formed" in claim(tmp_path, f"below({e('t')}, c = 80000)", "g\na\nb\n")
    out = prog(tmp_path, "g\na\nb\n", [f"below({e('tsv(f)')}, c = 80000)"])
    assert "[S008" in out[0] and LIM in out[0], out


def test_the_read_limit_counts_each_rows_least_line_exactly(tmp_path):
    """(G04, Opus 5.5 max review 04 a, b) a table whose column 3 is read as a 600-byte literal: each row at least two
    tabs, the literal and a line feed, the header 'a<TAB>b<TAB>c', so a readable table holds at most (67108864 - 5) / 603
    = 111291 such rows (without the separators, 111661): 111292 holds only by the limit (S008), 111291 needs a readable
    table past MAX_ROWS (R013). (Rows of empty cells meet the memory limit first, unit G05.) A number strictly between 1 and
    1 + 10^-900 is spelled in at least 903 bytes, so at most 74235 such rows fit: 74236 holds only by the limit, and at
    74235 a readable table fails it, and its certificate (67 MB of numbers) is past the stated step bound (SPEC-EXACT 8):
    R013 on the counted steps, never on a certificate past the read limit."""
    L = "a" * 600
    hdr = f"a\tb\tc\nx\ty\t{L}\n"
    out = prog(tmp_path, hdr, [f'below(count(where(tsv(f), eq(3, "{L}"))), c = 111292)', f'below(count(where(tsv(f), eq(3, "{L}"))), c = 111291)'])
    assert "[S008" in out[0] and LIM in out[0], out
    assert "[R013" in out[1], out
    t = "1." + "0" * 899 + "1"
    c = lambda n: f"below(count(where(tsv(f), gt(1, c = 1), lt(1, c = {t}))), c = {n})"   # noqa: E731
    out = prog(tmp_path, "g\n2\n", [c(74236), c(74235)])
    assert "[S008" in out[0] and LIM in out[0], out
    assert "[R013" in out[1] and "counted steps" in out[1] and "past the read limit" not in out[1], out


def test_the_read_limit_counts_accounted_memory_exactly(tmp_path):
    """(G05, Opus 5.5 max review 05) 2000 columns, column 2000 read: a row is at least 2000 bytes of text, 64 + 80 a
    cell of table (kernel._table_size) and 72 of where()'s rows, so the statement's accounted memory (1 GiB, R012)
    holds at most 6621 rows: 7000 and 6622 hold only by the limit (S008; before G05 the certificate refused R012, X001),
    6621 is failed by a readable table (formed)."""
    W = 2000
    hdr = "\t".join(f"h{i}" for i in range(1, W + 1)) + "\n" + "\t".join("1" for _ in range(W)) + "\n"
    out = [prog(tmp_path, hdr, [f'below(count(where(tsv(f), ne({W}, "a"))), c = {n})'])[0] for n in (7000, 6622, 6621)]   # (B0304) one program each: an earlier statement's rows of f are charged on the candidate too
    assert all("[S008" in o and LIM in o for o in out[:2]), out
    assert "formed" in out[2], out


def test_the_let_walker_reads_each_let_once_in_its_own_statement():
    """(WLK; G03, G05, G04c) letwalk, which stmts, wheres and evreads share: a let used twice, and inside a second let,
    is walked once, in its own statement (the kernel reads a let once; witness.evaluate keeps its value): its tsv()
    read is charged there, its where() is accounted once, and the claim's own statement reads nothing for it."""
    from reality4.syntax import Call, Name, Str
    f = Call("tsv", (Name("f"),), ())
    w = Call("where", (f, Call("ne", (Str(b"1"), Str(b"a")), ())), ())   # let w = where(tsv(f), ...)
    v = Call("where", (w, Call("eq", (Str(b"1"), Str(b"z")), ())), ())   # let v = where(w, ...)
    top = Call("difference", (Call("count", (w,), ()), Call("count", (Call("where", (w, Call("eq", (Str(b"2"), Str(b"y")), ())), ()),), ())), ())
    top = Call("difference", (top, Call("count", (v,), ())), ())
    D.LETS.clear()
    D.LETS[id(w)], D.LETS[id(v)] = (w, "w"), (v, "v")
    try:
        assert D.stmts(top) == [{}, {"f": 1}, {}]
        names, ws = D.wheres(top)
        assert names == {"f"} and len(ws) == 3 and ws[0] is w and ws[2] is v, ws
        assert len(D.evreads(top)) == 3
    finally:
        D.LETS.clear()


@pytest.mark.parametrize("mode", ["other", "literal", "long", "none"])
def test_a_wrong_least_spelling_is_x001_r013_or_the_same(tmp_path, monkeypatch, mode):
    """(SPL) vmin moved to build.py, outside the base: a least_table cell's spelling feeds only the certificate's bytes,
    which the reader and the evaluator check; the bound (Model.cmin, rlb) does not use it. A vmin giving another
    value's spelling, a literal, a longer spelling or none gives X001, R013 or the unmutated verdict; some give X001."""
    orig = D.Model.vmin
    def vm(self, s, k, v):
        w = orig(self, s, k, v)
        return {"other": "2", "literal": "x", "long": (w or "1") + ".000000", "none": None}[mode]
    L = "a" * 600
    cl = [f'below(sum(where(tsv(f), eq(2, "{L}"), ge(1, c = 1), le(1, c = 1)), 1), c = {n})' for n in (111291, 111292, 111661)]
    base = prog(tmp_path, f"a\tb\n1\t{L}\n", cl)
    assert "[R013" in base[0] and all("[S008" in o and LIM in o for o in base[1:]), base
    monkeypatch.setattr(D.Model, "vmin", vm)
    out = prog(tmp_path, f"a\tb\n1\t{L}\n", cl)
    for b, o in zip(base, out):
        assert o == b or "[X001" in o or "[R013" in o, (b, o)
    if mode in ("other", "literal"):
        assert all("[X001" in o for o in out), out


def test_a_claim_true_regardless_of_the_bound_stays_plain(tmp_path):
    out = prog(tmp_path, "g\na\nb\n", ["atleast(rows(tsv(f)), c = 0)"])
    assert "[S008" in out[0] and LIM not in out[0], out


def _internal_tags():
    """(H01) every kind tag the model puts beside a user name in a variable: the second element of ("z", tag, ...)."""
    import os
    import re
    src = os.path.dirname(D.__file__)
    tags = set()
    for f in ("decide.py", "search.py", "build.py"):
        tags |= set(re.findall(r'\("z", "([A-Za-z_][A-Za-z0-9_]*)"', open(os.path.join(src, f), encoding="utf-8").read()))
    return sorted(tags | {"on", "du", "cell", "rs"})   # on, du: ("z", fn[:2], ...) of onsets() and durations()


def test_the_kind_tags_are_known():
    assert {"pix", "raw", "y", "yp", "ps", "pv", "mu", "w", "tr", "j", "cell", "rs"} <= set(_internal_tags())


def _named(n, data, claims):
    import hashlib
    from reality4 import kernel as K
    h = hashlib.sha256(data).hexdigest()
    out = []
    for c in claims:
        st = W.MemStore({h: data})
        st.begin_program()
        out.append(K._check(f"file {n} = sha256:{h}\nlet {n}_t = tsv({n})\n{c(n)}\n".encode(), st)[1])
    return out


def _dnamed(n, claims):
    from reality4 import kernel as K
    pt = b"participant_id\tg\tx\nsub-p\tA\t1\nsub-p\tB\tn/a\n"
    blobs, mh = __import__("reality4.build").build._dataset({"subs": [], "recs": [], "ids": []}, pt, {})
    out = []
    for c in claims:
        st = W.MemStore(blobs)
        st.begin_program()
        out.append(K._check(f"dataset {n} = sha256:{mh}\nlet {n}_b = bids({n})\nlet {n}_t = participants({n}_b)\n{c(n)}\n".encode(), st)[1])
    return out


@pytest.mark.parametrize("tag", _internal_tags())
def test_a_user_name_spelled_like_a_kind_tag_changes_nothing(tag):
    """(H01, max2 finding 01) user names live at another place of a variable than the model's kind tags (a cell is
    ("z", "cell", slot, row, column), a region's rational ("z", "rs", slot, ...)), so no name can be read as a kind: a
    file, let or dataset named like any kind tag gives the output a name f gives."""
    half, c = "0." + "0" * 30 + "5", "0.1" + "0" * 29 + "05"
    tab = [lambda n: f"claim exceeds(widen(number(cell(tsv({n}), 1, 1)), tolerance = {half}), c = {c})",
           lambda n: f"claim exceeds(number(cell({n}_t, 1, 1)), c = 0.5)",
           lambda n: f"claim exceeds(difference(mean({n}_t, 1), number(cell(tsv({n}), 1, 1))), c = 0)",
           lambda n: f"claim below(sum(where({n}_t, ge(1, c = 0)), 1), c = 5)",
           lambda n: f"claim exceeds(number(header({n}_t, 1)), c = 0)"]
    ds = [lambda n: f'claim mean(where({n}_t, ne("x", "n/a")), "x")',
          lambda n: f'claim exceeds(number(extra(participant({n}_b, "w1"), 3)), c = 0.5)']
    rec = [lambda n: f"claim below(tr({n}_r), c = 2 s)", lambda n: f"claim below(onset({n}_r, 1), c = 2 s)",
           lambda n: f"claim atleast(volumes({n}_r), c = 2)"]
    outs = [(_named(tag, b"5\n1\n3\n", tab), _named("f", b"5\n1\n3\n", tab)), (_dnamed(tag, ds), _dnamed("d", ds)), (_rnamed(tag, rec), _rnamed("d", rec))]
    assert all(a == b for a, b in outs), outs
    assert all("formed" in o[0] for _, b in outs for o in b), outs


def _rnamed(n, claims):
    """rclaim's dataset (one BOLD recording, sub-01 task-x, and its events) under the names n, n_b, n_r."""
    import hashlib
    from fractions import Fraction
    from reality4 import kernel as K, readers as R
    files = {"dataset_description.json": b'{"Name": "g", "BIDSVersion": "1.0.1"}', "README": b"g\n",
             "sub-01/func/sub-01_task-x_bold.nii": W._nii((1, 1, 1, 2), Fraction(1)),
             "sub-01/func/sub-01_task-x_bold.json": b'{"TaskName": "x", "RepetitionTime": 1}',
             "sub-01/func/sub-01_task-x_events.tsv": b"onset\tduration\n1.5\t1\n"}
    blobs = {hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (R.MANIFEST_MAGIC + "\n" + "".join(f"{hashlib.sha256(files[p]).hexdigest()}\t{len(files[p])}\t{p}\n" for p in sorted(files))).encode()
    blobs[hashlib.sha256(man).hexdigest()] = man
    out = []
    for c in claims:
        st = W.MemStore(blobs)
        st.begin_program()
        prog = f'dataset {n} = sha256:{hashlib.sha256(man).hexdigest()}\nlet {n}_b = bids({n})\nlet {n}_r = recording({n}_b, "01", "x")\n{c(n)}\n'
        out.append(K._check(prog.encode(), st)[1])
    return out


@pytest.mark.parametrize("cls, cell", [
    ("gt(1, c = 0), lt(1, c = 100000)", "1"),   # (H02, max2 finding 02 a) a decimal class whose near end is short: "1", not "100"
    (", ".join(f'ne(1, "{x}")' for x in "abcdefghijkmnopqrstuvwxyz"), "2"),   # (b) other text beside 25 letters: "2", not "aa"
])
def test_the_least_text_is_exact_near_a_short_end_and_past_letters(cls, cell):
    """(H02, max2 finding 02) the read limit's bound is the least readable text: N rows of a one-byte cell are readable up
    to N = 4,902,929 (219 N + 339 accounted bytes), so a cutoff there needs a readable table of more than MAX_ROWS rows
    (R013) and one past it holds only by the read limit (S008). G04's in_iv started at the interval's width scale and
    the other-text search tried letters only: both charged 2 bytes a row too many, a wrong S008 from 4,814,985 rows."""
    import hashlib
    from reality4 import kernel as K
    data = f"g\n{cell}\n".encode()
    h = hashlib.sha256(data).hexdigest()
    out = []
    for c in (4902929, 4902930):
        st = W.MemStore({h: data})
        st.begin_program()
        out.append(K._check(f"file f = sha256:{h}\nclaim below(count(where(tsv(f), {cls})), c = {c})\n".encode(), st)[1][0])
    assert "[R013" in out[0] and "[S008" in out[1] and "read limit" in out[1], out


def test_other_text_takes_any_ascii_and_counts_csv_quotes():
    """(H02) the least other text is any ASCII text the reader keeps (no tab or quote in a TSV; quoted in a CSV, at its
    quoting's bytes), no literal, looking like none, and no decimal where the column is a number."""
    M = D.Model.__new__(D.Model)
    M.lmemo, M.pay, M.kind, M.lits = {}, [0], {"t": "tsv", "c": "csv"}, {}
    M.classes = {("t", 1): [("oth", None, None)], ("t", 2): [("oth", None, None), ("iv", (0, 1), None)], ("c", 1): [("oth", None, None)]}
    q = lambda c: len(c.encode())   # noqa: E731
    qc = lambda c: len(c.encode()) + (2 + c.count('"') if any(x in c for x in ',";\t') else 0)   # noqa: E731
    lets = "abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_!#$%&'()*+-./:<=>?@[\\]^`{|}~l"
    M.lits = {("t", 1): {x.encode() for x in lets + ",;"}, ("t", 2): {b"a"}, ("c", 1): {x.encode() for x in lets}}
    assert M.cmin1("t", 2, ("oth", None, None), True, q, False) == (1, "b")
    assert M.cmin1("t", 1, ("oth", None, None), True, q, False)[0] == 2   # every printable byte a literal, look-alikes too
    assert M.cmin1("c", 1, ("oth", None, None), True, qc, False)[0] == 2   # ',', ';' quoted cost 3: two bytes win


def _evclaim(c, rows=1):
    """c on rclaim's dataset (one BOLD recording, sub-01 task-x) whose events file has rows rows "0<TAB>1"."""
    import hashlib
    from fractions import Fraction
    from reality4 import kernel as K, readers as R
    files = {"dataset_description.json": b'{"Name": "g", "BIDSVersion": "1.0.1"}', "README": b"g\n",
             "sub-01/func/sub-01_task-x_bold.nii": W._nii((1, 1, 1, 2), Fraction(1)),
             "sub-01/func/sub-01_task-x_bold.json": b'{"TaskName": "x", "RepetitionTime": 1}',
             "sub-01/func/sub-01_task-x_events.tsv": b"onset\tduration\n" + b"0\t1\n" * rows}
    blobs = {hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (R.MANIFEST_MAGIC + "\n" + "".join(f"{hashlib.sha256(files[p]).hexdigest()}\t{len(files[p])}\t{p}\n" for p in sorted(files))).encode()
    blobs[hashlib.sha256(man).hexdigest()] = man
    st = W.MemStore(blobs)
    st.begin_program()
    prog = f'dataset d = sha256:{hashlib.sha256(man).hexdigest()}\nlet b = bids(d)\nlet r = recording(b, "01", "x")\nclaim {c}\n'
    return [ln for ln in K._check(prog.encode(), st)[1] if ln.startswith("line")]


def test_an_events_table_is_charged_and_refused_before_it_is_built():
    """(H07, max2 finding 07) a parsed events file is kept like a plain table: its cells alone past the bound refuse
    R012 before it is parsed (bids(d)'s conformance gate parses it too), so a 64 MiB events file cannot pass the
    memory floor; 6.8 million rows "0<TAB>1" (27 MB, under MAX_TEXT_FILE) is refused, not parsed (RSS stays small)."""
    out = _evclaim("events(r)", 6_800_000)
    assert "[R012" in out[0], out


@pytest.mark.parametrize("c, want", [(4668441, "[R013"), (4668442, "[S008")])
def test_the_events_tables_memory_is_in_the_read_limit(c, want):
    """(H07) the model charges each events file the statement reads as the reader keeps it (Model.evmem: 2 x its text,
    193 + 79 c a file, 64 + 79 c a row): rows "0<TAB>1" cost 230 bytes and the file 379, so past (2^30 - 379) / 230
    rows no events file is readable (S008 by the read limit); at it a failing input needs more than MAX_ROWS rows
    (R013); (B0304) what the program holds from its let b = bids(d) is made from the dataset, so left out as inline. Without the charge the bound was the text's, 16.7 million rows."""
    out = _evclaim(f"below(events(r), c = {c})")
    assert want in out[-1] and (want != "[S008" or "read limit" in out[-1]), out


def _after_a_big_table(c, g=None):
    """(H03) claim 2 (G05's 2000-column shape) after claim 1 has read a 1.4-million-row table (205,800,275 accounted
    bytes, held by the program); g: the program's g (one row, column 2000 = a) or the bytes given."""
    import hashlib
    from reality4 import kernel as K
    h = lambda d: hashlib.sha256(d).hexdigest()   # noqa: E731
    A = b"x\n" * 1_400_001
    g = g or ("\t".join("x" * 2000) + "\n" + "\t" * 1999 + "a\n").encode()
    st = W.MemStore({h(A): A, h(g): g})
    st.begin_program()
    p = f'file a = sha256:{h(A)}\nfile g = sha256:{h(g)}\nclaim exceeds(rows(tsv(a)), c = 0)\nclaim below(count(where(tsv(g), ne(2000, "a"))), c = {c})\n'
    return [ln for ln in K._check(p.encode(), st)[1] if ln.startswith("line 4")][0]


@pytest.mark.parametrize("c, want, real", [(5352, "formed", "[V001"), (5353, "[S008", "[R012")])
def test_the_memory_limit_is_the_programs(c, want, real):
    """(H03, max2 finding 03) the reader keeps one account a program (readers.Store: begin() does not reset it), so the
    model's memory atom and the certificates start from what the program holds before the statement, less its own
    files' (Store.held): after 205,800,275 bytes of claim 1, a failing g of 5352 rows (one-byte header names) is
    readable and the claim forms; one of 5353 rows is refused R012, so the claim holds only by the read limit."""
    out = _after_a_big_table(c)
    assert want in out and (want != "[S008" or "read limit" in out), out
    fail = ("\t".join("x" * 2000) + "\n" + ("\t" * 1999 + "b\n") * c).encode()
    assert real in _after_a_big_table(c, fail)


_LETS = "abcdefghijkmnopqrstuvwxyz"
_PLETS = "wvqxyz" + "abcdefghijkmnoprstu"


@pytest.mark.parametrize("lits", [_LETS, _LETS + "_#$%&*@^"])
def test_a_least_cell_does_not_run_out_of_letters(tmp_path, lits):
    """(H04, Opus 5.5 max2 review 04 a) size() beside a one-column table's literals naming every letter: the least other
    cell is another one-byte cell (decide.FILLC, then decide.fills); before H04 StopIteration, X001."""
    conds = ", ".join(f'ne(1, "{c}")' for c in lits)
    out = claim(tmp_path, f"atleast(difference(size(f), count(where(t, {conds}))), c = 1)", data=b"g\na\n2\n")
    assert "[S008" in out and "W1" in out, out


@pytest.mark.parametrize("more", ["", "aa", "aa ab ac"])
def test_a_made_up_participant_label_does_not_run_out(more):
    """(H04 b) participants(b) beside literal labels sub-<a>1 for every made-up letter (and sub-aa1, ...): Model.plabel and
    build.rec_dataset take the next of decide.fills; before H04 StopIteration, X001."""
    import hashlib, os, tempfile
    import bidsfix
    from reality4 import kernel as K, readers as R
    conds = ", ".join(f'ne(1, "sub-{a}1")' for a in list(_PLETS) + more.split())
    subs = ("01x", "02x", "03x")   # not sub-01: sub-o1 would look like it (K002)
    root = bidsfix.mini(os.path.join(tempfile.mkdtemp(), "ds"), subjects=subs, groups=dict(zip(subs, "aba")))
    files = {os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/"): open(os.path.join(d, f), "rb").read() for d, _, fs in os.walk(root) for f in fs}
    blobs = {hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (R.MANIFEST_MAGIC + "\n" + "".join(f"{hashlib.sha256(files[q]).hexdigest()}\t{len(files[q])}\t{q}\n" for q in sorted(files))).encode()
    blobs[hashlib.sha256(man).hexdigest()] = man
    st = W.MemStore(blobs)
    st.begin_program()
    prog = f"dataset d = sha256:{hashlib.sha256(man).hexdigest()}\nlet b = bids(d)\nclaim count(where(participants(b), {conds}))\n"
    out = [ln for ln in K._check(prog.encode(), st)[1] if ln.startswith("line")][0]
    assert "formed" in out and "= 3 (Exact)" in out, out


@pytest.mark.parametrize("types", ["zyxwv", "zyxwvabc"])
def test_a_filler_trial_type_does_not_run_out(types):
    """(H04 c) events beside trials of z, y, x, w, v (and a, b, c): build.rs_recs2's filler type is the next of
    decide.fills; before H04 StopIteration, X001."""
    v = 'sum(recordings(b, "x"), "events")'
    for t in types:
        v = f'difference({v}, sum(recordings(b, "x"), "trials", "{t}"))'
    out = sclaim(f"exceeds({v}, c = 0)")
    assert "formed" in out and "holds" in out, out


def test_the_made_up_names_are_unbounded():
    """(H04) witness._fresh goes past three letters; decide.fills gives its head, then _fresh."""
    import itertools
    from reality4 import decide as D
    assert next(itertools.islice(W._fresh(), 26 + 26 ** 2 + 26 ** 3, None)) == "aaaa"
    assert list(itertools.islice(D.fills("zy"), 4)) == ["z", "y", "a", "b"]


@pytest.mark.parametrize("bad", ["bounds", "above"])
@pytest.mark.parametrize("c", ['difference(sum(t, 3), max(t, 3))', 'exceeds(difference(max(t, 3), mean(t, 3)), c = 0)',
                               'below(difference(median(where(t, ge("x", c = 1)), 3), sum(where(t, eq("g", "A")), 3)), c = 2)',
                               'atleast(difference(sum(t, 3), order(t, 3, 2)), c = -100)'])
def test_a_piece_with_wrong_facts_is_x001(tmp_path, monkeypatch, c, bad):
    """(H08, Opus 5.5 max2 review 08) search.piece_atoms (untrusted) builds the pieces' PAtoms, whose facts (S = mu·N,
    lo <= mu <= hi) cert.prange_split trusts. Wrong bounds (inverted: the review's tamper; or above every row's value)
    made these formed claims certified S008 refusals; cert.py now trusts a PAtom outside
    the option only when it is one of decide.Model.piece_facts: X001 (or R013), never another verdict."""
    real = D.Model.piece_atoms

    def tampered(self, case):
        out = real(self, case)
        for P in out:
            P.lo, P.hi = (5, 4) if bad == "bounds" else (3, None)   # inverted (the review's), or above every row's value
        return out
    monkeypatch.setattr(D.Model, "piece_atoms", tampered)
    out = claim(tmp_path, c, M5)
    assert "[X001" in out or "[R013" in out or "formed" in out, out


def test_a_sum_of_repetition_times_is_no_single_read_value(tmp_path):
    """(A04, Argon review 04, its repro) A region's sum of RepetitionTimes (("z", "rs", d, "y", ..)) was split as one
    number the reader reads (band, 1000 digits), so widen() was refused S008 W2 "decided exactly" on a dataset while
    another readable one (TRs 9 and 1.0...04 s, sum 10 + 4e-999 s) makes it bear (V001 without it, V006 with it). The
    model's kinds (decide.zkind) make it a sum (a step split): not S008 now (R013: the search finds no such point)."""
    import struct
    from helpers import manifest

    def nii(tr):
        head = bytearray(352)
        struct.pack_into("<i", head, 0, 348)
        struct.pack_into("<8h", head, 40, 4, 1, 1, 1, 2, 1, 1, 1)
        struct.pack_into("<2h", head, 70, 2, 8)
        struct.pack_into("<8f", head, 76, 1.0, 1.0, 1.0, 1.0, tr, 1.0, 1.0, 1.0)
        struct.pack_into("<f", head, 108, 352.0)
        head[123] = 8
        head[344:348] = b"n+1\x00"
        return bytes(head) + b"\x00\x00"
    ds = tmp_path / "ds"
    for p, b in [("dataset_description.json", b'{"Name": "x", "BIDSVersion": "1.0.1"}\n'), ("README", b"test\n"),
                 ("participants.tsv", b"participant_id\nsub-01\nsub-02\n")] + \
            [(f"sub-0{i}/func/sub-0{i}_task-rest_bold.{e}", nii(tr) if e == "nii" else b'{"TaskName": "rest", "RepetitionTime": %d}\n' % tr)
             for i, tr in ((1, 11), (2, 1)) for e in ("nii", "json")]:
        (ds / p).parent.mkdir(parents=True, exist_ok=True)
        (ds / p).write_bytes(b)
    out = tmp_path / "m"
    out.mkdir()
    mh = manifest(str(ds), str(out))
    c, t = "2" + "0" * 998 + "1" + " / 2" + "0" * 998, "1 / 8" + "0" * 998
    prog = f'dataset m = sha256:{mh}\nlet b = bids(m)\nclaim exceeds(widen(sum(recordings(b, "rest"), "tr"), tolerance = {t} s), c = {c} s)\n'
    ok, text = run(prog, [str(out / (mh + ".manifest"))], [str(ds)])
    assert "[S008" not in text and ("formed" in text or "[R013" in text), text


def test_a_lets_memory_is_not_counted_twice(tmp_path, monkeypatch):
    """(A03, Argon review 03, its repro, at a 40,000,000-byte accounted cap) A claim over a let: the memory the program held
    before it (H03) kept what the let's own file and its where() rows took, and the model charged both again, so the
    readable inputs were cut short and atmost(count(w), c = 170000) was a certified S008 (holds only by the read limit)
    though 182,646 rows of "a" are readable (count 182,646, V001). Its files are the let's too (actual_reads), and its
    where() bytes (store.anon_by, B0304: by the files they come from) are left out: S008 starts exactly at the readable bound, 182,646."""
    from reality4 import readers as R0
    monkeypatch.setattr(R0, "MAX_ACCOUNTED", 40000000)

    def verdict(row, n, c):
        p, h = tsv(tmp_path, f"{row}{n}.tsv", "c1\n" + (row + "\n") * n)
        out = run(f'file f = sha256:{h}\nlet w = where(tsv(f), eq(1, "a"))\nclaim atmost(count(w), c = {c})\n', [p])[1]
        return " ".join(x for x in out.split("\n") if x.startswith("line"))
    assert "[V001" in verdict("a", 182646, 182645) and "[R012" in verdict("a", 182647, 182646)   # the readable bound
    for row, n in (("a", 20000), ("b", 50000)):   # where()'s rows kept by the let; the let's file
        assert "[S008" not in verdict(row, n, 170000) and "[S008" not in verdict(row, n, 182645)
        assert "[S008" in verdict(row, n, 182646)


def test_widened_variances_of_one_column_by_two_readers_share_one_symbol(tmp_path):
    """(A06, Argon review 06, its repro) Wherever both answer, sample_variance(tsv(f), 1) and sample_variance(csv(f), 1)
    are one value (the identity names no reader, SPEC 5.1), so their widen() symbols cancel; nwidth keyed them by repr,
    width 30 for 10: a certified S008 W1 on "x 0 20" though "x 0 2" fails (V001), and an X001 for exceeds(.., c = 25)."""
    w = "widen(sample_variance(tsv(f), 1), tolerance = 10), difference(widen(sample_variance(csv(f), 1), tolerance = 10), "
    for data, cmp, last, want in (("x\n0\n20\n", "atleast", "widen(population_variance(csv(f), 1), tolerance = 10)", "formed"),
                                  ("x\n0\n2\n", "atleast", "widen(population_variance(csv(f), 1), tolerance = 10)", "V001"),
                                  ("x\n0\n20\n", "exceeds", "population_variance(csv(f), 1)", "formed")):
        p, h = tsv(tmp_path, f"{cmp}{len(data)}.tsv", data)
        out = run(f"file f = sha256:{h}\nclaim {cmp}(difference({w}{last})), c = 25)\n", [p])[1]
        got = [x for x in out.split("\n") if x.startswith("line")]
        assert len(got) == 1 and (": formed" in got[0] if want == "formed" else f"[{want}" in got[0]), got


def test_a_header_number_by_two_readers_is_one_value(tmp_path):
    """(B08, Argon review 2 08, its repro; A06 for headers) number(header(tsv(f), 1)) and number(header(csv(f), 1)) are
    one value (the identity names no reader, SPEC 5.1, as Model.ident), but the kernel's Header sort kept the reader, so
    their widen() symbols did not cancel: V006 for both cuts where the width 1 + 2 decides them, and two tolerances on
    the one value were not S012."""
    p, h = tsv(tmp_path, "h.tsv", "1\n0\n20\n")
    d = "difference(widen(number(header(tsv(f), 1)), tolerance = 1), widen(number(header(csv(f), 1)), tolerance = 2))"
    for c, want in ((-2, "S008"), (2, "V001")):
        got = [x for x in run(f"file f = sha256:{h}\nclaim atleast({d}, c = {c})\n", [p])[1].split("\n") if x.startswith("line")]
        assert len(got) == 1 and f"[{want}" in got[0], (c, got)
    out = run(f"file f = sha256:{h}\nclaim widen(number(header(tsv(f), 1)), tolerance = 1)\n"
              f"claim widen(number(header(csv(f), 1)), tolerance = 2)\n", [p])[1]
    assert [x[:21] for x in out.split("\n") if x.startswith("line")] == ["line 2: refused [S012", "line 3: refused [S012"], out
