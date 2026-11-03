"""Part B of 27 Oct 2026 on exact-decision-opus (verify-opus-exact/REPORT.md): regression tests per item."""
import pytest
import hashlib

import helpers  # noqa: F401 (puts src on the path)
from reality4 import kernel as K, witness as W


def run(prog, files):
    st = W.MemStore(files)
    st.begin_program()
    ok, out = K._check(prog.encode(), st)
    return [ln for ln in out if ln.startswith("line")]


RAW = b"hello"
RH = hashlib.sha256(RAW).hexdigest()


def raw(claim):
    return run(f"file r = sha256:{RH}\nclaim {claim}\n", {RH: RAW})


# ---- item 7: a raw file's size is decided arithmetically, any size up to 2^63 - 1 ----------------

def test_item7_size_atmost_large_cutoffs_forms():   # was R013 ("more than 100000 rows in one table", P3)
    for c in ("10000000", "1000000000000", str(2 ** 63 - 2)):
        out = raw(f"atmost(size(r), c = {c})")
        assert out[0].startswith("line 2: formed:"), (c, out)


def test_item7_size_atmost_the_largest_off_t_always_holds():
    out = raw(f"atmost(size(r), c = {2 ** 63 - 1})")
    assert out[0].startswith("line 2: refused [S008"), out


def test_item7_periodic_file_reads_like_its_bytes():
    p = W.Periodic(1000, 3)
    assert len(p) == 1000 and p[10:20] == p.whole[10:20] and p.sha == hashlib.sha256(p.whole).hexdigest()
    q = W.Periodic(2 ** 40, 3)
    assert len(q) == 2 ** 40 and q[2 ** 40 - 5:2 ** 40] == bytes(p.cycle[i % 256] for i in range(2 ** 40 - 5, 2 ** 40))


# ---- P1: the model holds only numbers the reader reads (at most 1000 digits, |exponent| <= 1000) ----------

from fractions import Fraction  # noqa: E402

from reality4 import decide as D, readers as R  # noqa: E402

X = "g\tx\ty\nA\t0.5\t1\nB\t0.25\t2\nA\t0.75\t3\n"


def tab(claim, data=X):
    h = hashlib.sha256(data.encode()).hexdigest()
    return run(f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {claim}\n", {h: data.encode()})


def test_p1_readable_numbers_and_their_spellings():
    for q in (Fraction(0), Fraction(1, 10 ** 1999), Fraction(10 ** 1000 - 1, 10 ** 1999), D.RMAX, -D.RMAX, Fraction(1, 2) + Fraction(1, 10 ** 1000), Fraction(7, 4)):
        assert D.in_r(q)
        for v in range(4):
            t = D.dec_seq(q, v)
            assert R.decimal(t) == q, (q, v, t)
    for q in (Fraction(1, 10 ** 2000), D.RMAX + 1, 1 + Fraction(1, 10 ** 1000), Fraction(1, 3)):
        assert not D.in_r(q) and D.dec_seq(q, 0) is None
    assert D.nxt(Fraction(0)) == Fraction(1, 10 ** 1999) and D.prv(Fraction(1)) == 1 - Fraction(1, 10 ** 1000)
    assert D.nxt(Fraction(1)) == 1 + Fraction(1, 10 ** 999) and D.nxt(None) == -D.RMAX and D.prv(None) == D.RMAX
    assert D.inside(Fraction(1), 1 + Fraction(1, 10 ** 999), [0]) is None


def test_p1_d1_forms_a_readable_value_below_ten_to_the_minus_999_exists():   # verify report D1 (was X001)
    out = tab(f'count(where(t, gt("x", c = 0), lt("x", c = 0.{"0" * 998}1)))')
    assert out[0].startswith("line 3: formed:"), out   # 1e-1999 is read (readers.decimal), so the count can be 0 or 1


def test_p1_an_interval_with_no_readable_number_holds_no_row():
    out = tab(f'count(where(t, gt("x", c = 1), lt("x", c = 1.{"0" * 998}1)))')   # (1, 1 + 10^-999): nothing between
    assert out[0].startswith("line 3: refused [S011"), out


def test_p1_d2_forms():   # verify report D2 (was X001; old S008)
    out = tab(f'max(where(t, ge("x", c = 0.5), lt("x", c = 0.5{"0" * 997}1)), "x")', "g\tx\nA\t0.5\n")
    assert out[0].startswith("line 3: formed:"), out


def test_p1_v8d_variance_sup_over_readable_numbers_is_decided_fast():   # verify report V8d (was 214 s, X001)
    import time
    t0 = time.time()
    claim = f'below(sample_variance(where(t, gt("x", c = 0), lt("x", c = 0.{"9" * 999})), "x"), c = 0.4{"9" * 998})'
    out = tab(claim)
    assert out[0].startswith("line 3: refused [S008"), out   # the readable ends 10^-1999 and 1 - 2·10^-1000... never pass c
    assert time.time() - t0 < 30


def test_p1_an_interval_with_one_readable_number_has_no_variance():
    one = f'1.{"0" * 998}1'
    out = tab(f'population_variance(where(t, gt("x", c = 1), lt("x", c = 1.{"0" * 998}2)), "x")', f"g\tx\nA\t{one}\n")   # only 1 + 10^-999
    assert out[0].startswith("line 3: refused [S008"), out


# ---- item 8: whether a summed type has rows is split only where a solution needs it --------------------

N = "group\tsite\tage\tscore\nA\ts1\t30\t2\nB\ts2\t41\t5\nP\ts1\t-4.5\t2\nB\ts1\t7\t0.5\nZ\ts2\t12\t9\n"   # exact_diff's PART_N_TABLE


def test_item8_pn535_forms_as_under_the_search():   # was R013: 256 presence cases x 192 order cases > MAX_CASES
    out = tab('difference(order(t, "age", 3), difference(min(where(t, le("age", c = 1/3), ne("group", "A")), "age"), '
              'sum(where(t, le("score", c = 10), lt("age", c = 10)), "score")))', N)
    assert out[0].startswith("line 3: formed:") and out[0].endswith("= 19 (Exact)"), out


S16 = ('difference(sum(where(t, gt("x", c = 0)), "x"), sum(where(t, ne("g", "a"), ne("g", "b"), ne("g", "c"), '
       'ne("h", "p"), ne("h", "q"), ne("h", "r")), "x"))')   # 16 summed types of an interval class: 2^16 cases before
T16 = "g\th\tx\na\tp\t0.5\nb\tq\t2\nc\tr\t-1\nd\tp\t3\ne\tq\t0.25\n"


def test_item8_sixteen_summed_types_decide():
    assert tab(S16, T16)[0].endswith("= 5.75 (Exact)")
    assert tab(f"atmost({S16}, c = 100)", T16)[0].startswith("line 3: formed:")


def test_item8_the_branch_bound_still_refuses_r013(monkeypatch):
    from reality4 import decide as D
    monkeypatch.setattr(D, "MAX_CASES", 1)   # the first relaxed solution breaks a type: two more systems
    out = tab(S16, T16)
    assert out[0].startswith("line 3: refused [R013") and "summed types have rows" in out[0], out


# ---- call 2: no readable point at the solver's choices is searched exactly over R's bands (SPEC-EXACT 3.1) --------
C2 = f'below(sum(where(t, gt("x", c = 0.{"0" * 996}5), le("y", c = 2.05)), "x"), c = 1{"0" * 400}.{"0" * 499}2)'


def test_call2_a_sum_thinner_than_the_solvers_choice_is_searched_and_forms():   # was R013 ("ends closer than ... reads")
    out = tab(C2)
    assert out[0].startswith("line 3: formed:"), out


def test_call2_bands_cover_r_in_order():
    B = D.bands()
    assert B[0][0] * B[0][1] == -D.RMAX and B[-1][0] * B[-1][2] == D.RMAX
    for (g, a, b), (h, c, _) in zip(B, B[1:]):   # no readable number between two bands, none skipped
        assert D.nxt(g * b) == h * c
    for p in (Fraction(1, 10 ** 1999), Fraction(1), 1 + Fraction(1, 10 ** 999), -Fraction(7, 4), D.RMAX):
        g, a, b = D.band(p)
        assert (g, a, b) in B and a <= p / g <= b and (p / g).denominator == 1, p


# ---- call 3: rows strictly between two order statistics get the band split (no R013 for a thin gap) ------------

Z = "0" * 998
X3 = f"g\tx\ty\nA\t1.{Z}1\t1\nB\t1.{Z}2\t2\nC\t1.{Z}3\t3\n"
W5 = f'where(t, gt("x", c = 1), lt("x", c = 1.{Z}5))'
W4 = f'where(t, gt("x", c = 1), lt("x", c = 1.{Z}4))'


def test_call3_a_piece_between_order_statistics_is_band_split():   # all three were R013 ("ends closer than ... reads")
    out = tab(f'below(order({W5}, "x", 2), c = 1.{Z}3)', X3)
    assert out[0].startswith("line 3: formed:"), out
    # between 1 and 1 + 4·10^-999 only 1 + 10^-999, 2·10^-999, 3·10^-999 are readable: the spread is at most 2·10^-999
    out = tab(f'atmost(difference(order({W4}, "x", 3), order({W4}, "x", 1)), c = 0.{Z}2)', X3)
    assert out[0].startswith("line 3: refused [S008") and "atmost()" in out[0], out
    out = tab(f'atmost(difference(order({W5}, "x", 3), order({W5}, "x", 1)), c = 0.{Z}2)', X3)
    assert out[0].startswith("line 3: refused [S008") and "R013" not in out[0], out


def test_call3_gap_cases_cover_a_band():
    m = D.Model.__new__(D.Model)
    one = D.Fraction(1)
    cs = m.gap_cases(("p", 0), (("z", "w", 0), one), (None, one + D.Fraction(1, 10 ** 999)))
    assert len(cs) == 5 and cs[0] == [D.ge({("p", 0): -1})]   # none; in the band below its last; at it; below; above
    assert m.gap_cases(("p", 0), (None, D.RMAX), (None, None)) == [[D.ge({("p", 0): -1})]]


# ---- item 5a (b): a variance or SD under widen(), and its comparison, decided exactly ---------------------------

def test_item5a_widened_variance_shapes_form():   # were the old search (S008 "found no readable input" on 2-4)
    sel = 'where(t, gt("x", c = 0.2), lt("x", c = 0.8))'
    for claim in ("exceeds(widen(sample_variance(t, 2), tolerance = 0.01), c = 0.01)",
                  f"exceeds(widen(sample_variance({sel}, 2), tolerance = 0.01), c = 0.01)",
                  f"below(widen(population_sd({sel}, 2), tolerance = 0.01), c = 0.25)",
                  'atleast(widen(widen(sample_sd(where(t, ge("x", c = 0.25)), 2), tolerance = 0.01), tolerance = 0.02), c = 0.1)',
                  'widen(population_variance(where(t, gt("x", c = 0.2)), 2), tolerance = 1)'):
        out = tab(claim)
        assert out[0].startswith("line 3: formed:"), (claim, out)


def test_item5a_widened_comparison_that_cannot_fail_refuses_w1():
    # in (0.2, 0.8) the sample variance is below 0.18, so V >= 0.17 + 0.05 never holds
    out = tab('below(widen(sample_variance(where(t, gt("x", c = 0.2), lt("x", c = 0.8)), 2), tolerance = 0.05), c = 0.17)')
    assert out[0].startswith("line 3: refused [S008") and "decided exactly" in out[0], out


B500 = "1" + "0" * 500
Z998 = "0." + "0" * 998


def test_item5a_widen_bears_only_through_three_rows():   # the old search ran out of memory here
    # readable values in the class: 10^500 + k·10^-499, k = 1, 2, 3; two rows give variances 0.5 and 2 (units of
    # 10^-998), only three rows (1, 2, 3) give 1, inside where widen() changes the answer (0.6, 1.2]
    hi = B500 + "." + "0" * 498 + "4"
    data = f"g\tx\ty\nA\t{B500}.{'0' * 498}1\t1\nB\t{B500}.{'0' * 498}3\t2\n"
    sel = f'where(t, gt("x", c = {B500}), lt("x", c = {hi}))'
    for claim in (f"exceeds(widen(sample_variance({sel}, 2), tolerance = {Z998}3), c = {Z998}9)",
                  f"exceeds(widen(population_variance({sel}, 2), tolerance = {Z998}1), c = {Z998}8)"):
        out = tab(claim, data)
        assert out[0].startswith("line 3: formed:"), out


def test_item5a_root_bounds_are_inward():
    for x in (D.Fraction(2), D.Fraction(81, 100), D.Fraction(1, 3)):
        lo, hi = D.root(x, 0), D.root(x, 1)
        assert lo * lo <= x < hi * hi and hi - lo == D.Fraction(1, 10 ** 2100)
    assert D.root(D.Fraction(81, 100)) == D.Fraction(9, 10) and D.root(D.Fraction(2)) is None


# ---- item 5b (c): a difference of two variances, uncoupled, decided exactly --------------------------------------

X5 = "g\tx\ty\nA\t0.5\t1\nA\t0.75\t2\nB\t0.25\t3\nB\t0.3\t4\nA\t0.65\t5\nB\t0.35\t6\n"
VA, VB = 'sample_variance(where(t, eq("g", "A")), 2)', 'sample_variance(where(t, eq("g", "B")), 2)'


def test_item5b_difference_of_variances_forms():   # were S008 ("could not find two inputs") under the old search
    for claim in (f"exceeds(difference({VA}, {VB}), c = 0.01)", f"difference({VA}, {VB})",
                  f'exceeds(widen(difference({VA}, population_variance(where(t, ne("g", "A")), 2)), tolerance = 0.01), c = 0.003)'):
        out = tab(claim, X5)
        assert out[0].startswith("line 3: formed:"), (claim, out)


def test_item5b_difference_that_cannot_fail_refuses_w1():
    # in (0.2, 0.4) the sample variance is below 0.02, so V1 - V2 >= 0.03 never holds
    out = tab('below(difference(sample_variance(where(t, gt("x", c = 0.2), lt("x", c = 0.4)), 2), '
              'sample_variance(where(t, gt("x", c = 0.6)), 2)), c = 0.03)', X5)
    assert out[0].startswith("line 3: refused [S008") and "decided exactly" in out[0], out


def test_item5b_difference_over_two_tables():
    a, b = "x\n1\n2\n", "x\n5\n9\n"
    ha, hb = (hashlib.sha256(d.encode()).hexdigest() for d in (a, b))
    prog = f"file f = sha256:{ha}\nfile h = sha256:{hb}\nlet t = tsv(f)\nlet u = tsv(h)\nclaim below(difference(sample_variance(t, 1), sample_variance(u, 1)), c = 0)\n"
    out = run(prog, {ha: a.encode(), hb: b.encode()})
    assert out[0].startswith("line 5: formed:"), out


def test_item5b_coupled_variances_decided(monkeypatch):
    # both selections hold rows of one type: the finite-domain search (no NotT, so not the old search)
    monkeypatch.setattr(D, "NotT", type("NoSearch", (Exception,), {}))
    for claim in ('exceeds(difference(sample_variance(t, 2), sample_variance(where(t, gt("x", c = 0.5)), 2)), c = 0.01)',
                  'exceeds(widen(difference(sample_variance(t, 2), sample_variance(where(t, gt("x", c = 0.5)), 2)), tolerance = 0.01), c = 0.01)'):
        assert tab(claim, X5)[0].startswith("line 3: formed:"), claim
    # one selection: sample minus population variance is Vp/(n - 1) >= 0, so atleast(.., c = 0) never fails
    out = tab('atleast(difference(sample_variance(t, 2), population_variance(t, 2)), c = 0)', X5)
    assert out[0].startswith("line 3: refused [S008") and "decided exactly" in out[0], out
    out = tab('difference(sample_variance(t, 2), sample_variance(t, 2))', X5)   # 0 on every input
    assert out[0].startswith("line 3: refused [S008") and "decided exactly" in out[0], out


def test_item5b_file_slot_of_a_difference():
    # the file read by V1 bears only through a V2 value in [1, 1.5] (fails needs V2 >= 1 + V1): decided by var_hit
    a, b = "x\n0\n1\n", "x\n0\n3\n"
    ha, hb = (hashlib.sha256(d.encode()).hexdigest() for d in (a, b))
    sel = lambda n, hi: f'sample_variance(where({n}, ge("x", c = 0), le("x", c = {hi})), 1)'
    prog = f"file f = sha256:{ha}\nfile h = sha256:{hb}\nlet t = tsv(f)\nlet u = tsv(h)\nclaim exceeds(difference({sel('t', 1)}, {sel('u', 3)}), c = -1)\n"
    out = run(prog, {ha: a.encode(), hb: b.encode()})
    assert out[0].startswith("line 5: refused [V001"), out   # 1/2 - 9/2 = -4: it fails, and is a claim (both slots bear)


# ---- item 6 (d): named rows and aggregates of one table, decided exactly ------------------------------------------

XN = "g\tx\nA\t0.5\nA\t0.75\nB\t0.25\nB\t3\n"


@pytest.mark.parametrize("claim, want", [
    ('exceeds(difference(sum(t, 2), number(cell(t, 1, 2))), c = 3)', "formed:"),        # the named row is in the sum
    ('exceeds(difference(sum(where(t, eq("g", "A")), 2), number(cell(t, 1, 2))), c = 0)', "formed:"),
    ('atmost(difference(min(where(t, gt("x", c = 0.3)), 2), number(cell(t, 1, 2))), c = 0)', "formed:"),
    ('atleast(difference(max(t, 2), number(cell(t, 4, 2))), c = 0)', "refused [S008"),  # a row is never above the max
    ('atmost(difference(min(t, 2), number(cell(t, 2, 2))), c = 0)', "refused [S008"),   # nor below the min
])
def test_item6d_named_rows_with_aggregates(claim, want, monkeypatch):
    out = tab(claim, XN)
    assert out[0].startswith("line 3: " + want), out


# ---- (g): a costly option no longer starves one two rows satisfy -----------------------------------------------

def test_g_claim3_probe_forms():
    # below(sum(where(t, ge(x, 3·10^-999)), x), c = 10^900 + 10^-98): W2 of the condition holds on two rows (x = c and
    # x = -1); the option that needs a value within 3·10^-999 of 10^900 has none at readable scale and used to exhaust
    # the step bound first (R013, BB's ruling 27 Oct 16:20: a claim two rows satisfy must form)
    lo, c = "0." + "0" * 998 + "3", "1" + "0" * 900 + "." + "0" * 97 + "1"
    out = tab(f'below(sum(where(t, ge("x", c = {lo})), "x"), c = {c})', "g\tx\ty\nA\t0.5\t1\nB\t0.25\t2\nC\t0.75\t3\n")
    assert out[0].startswith("line 3: formed:"), out[0][:200]


# ---- item (h): 5a/5b R013 narrowed (inputs of many rows of two values; coupled pieces scaled) ----------------------

B502 = "1" + "0" * 502
G2 = lambda k: B502 + "." + "0" * 496 + str(k)   # 10^502 + k·10^-497: the readable step there is 10^-497
DEC = lambda n, e: (lambda s: s[:-e] + "." + s[-e:])(str(n).rjust(e + 1, "0"))


def test_h_a_piece_reached_by_two_thousand_rows_of_two_values_forms():   # was R013 (the multisets stop at MAX_CASES)
    # the class holds two readable values; the outer widen bears only on k(n-k)/n² in (0.24001, 0.24002] (units
    # 10^-994): first at n = 2002, k = 801
    sel = f'where(t, gt("x", c = {B502}), lt("x", c = {G2(3)}))'
    out = tab(f"exceeds(widen(widen(population_variance({sel}, 2), tolerance = {DEC(12000, 999)}), tolerance = {DEC(1, 999)}), c = {DEC(12001, 999)})",
              f"g\tx\ty\nA\t{G2(1)}\t1\nB\t{G2(2)}\t2\n")
    assert out[0].startswith("line 3: formed:"), out[0][:200]


def test_h_a_piece_below_the_least_positive_variance_of_max_rows_rows_is_shown_over_the_bound():
    # step 10^-499 at 10^500: any rows not all equal have SD >= 10^-499/sqrt(2·10^5); the pieces are near 10^-998
    b5 = "1" + "0" * 500
    g5 = lambda k: b5 + "." + "0" * 498 + str(k)
    sel = f'where(t, gt("x", c = {b5}), lt("x", c = {g5(9)}))'
    out = tab(f"exceeds(widen(widen(population_sd({sel}, 2), tolerance = {DEC(2, 999)}), tolerance = {DEC(1, 999)}), c = {DEC(12, 999)})",
              f"g\tx\ty\nA\t{g5(1)}\t1\nB\t{g5(2)}\t2\n")
    assert out[0].startswith("line 3: refused [R013") and f"more than {D.MAX_ROWS} rows" in out[0] and "least positive variance" in out[0], out[0][:300]


@pytest.mark.parametrize("m, c, q, want", [
    (3, 42500, 2500, "refused [S008"),   # two values: sample variances j(n - j)/(n(n - 1)) skip (1/3, 1/2) (units 10^5)
    (3, 31000, 500, "refused [S008"),    # and (0.3, 1/3)
    (3, 30000, 500, "formed:"),          # 0.3: five rows, two at the top
    (5, 301424, 502, "refused [S008"),   # four values (D = 3 steps): only two rows reach above 3·9/9 = 3 (bf5a seed 1)
])
def test_5a_a_window_no_readable_input_reaches_is_no_input(m, c, q, want):
    # 5a's no-input sub-case (28 Oct 2026; was R013 at MAX_CASES multisets, 12.7 s, a wrong code): a class holding few
    # readable values (at most 64) gives all of them to the multisets; once every multiset of n rows is tried and the
    # largest variance of more rows, floor(n/2)·ceil(n/2)·D²/(n(n − d)), lies below every piece, no input reaches them:
    # widen() does not bear (S008 W2). Two values: two_vals tries every n to its cap first.
    sel = f'where(t, gt("x", c = {B502}), lt("x", c = {G2(m)}))'
    out = tab(f"exceeds(widen(sample_variance({sel}, 2), tolerance = {DEC(q, 999)}), c = {DEC(c, 999)})",
              f"g\tx\ty\nA\t{G2(1)}\t1\nB\t{G2(m - 1)}\t2\n")
    assert out[0].startswith("line 3: " + want), out[0][:200]
    assert want == "formed:" or "W2" in out[0], out[0][:200]
    # (H05, Opus 5.5 max2 review 05) the vdeep record holds at any number of rows: no read-limit reason (m = 5 had it)
    assert want == "formed:" or "read limit" not in out[0], out[0][:300]


def test_h_coupled_differences_over_an_unbounded_column_are_scaled_into_the_piece(monkeypatch):
    # were R013 (partb/Ec bfc): the multisets of ±RMAX and 0 reach the sign, and V1 − V2 scales by λ²
    monkeypatch.setattr(D, "NotT", type("NoSearch", (Exception,), {}))
    for claim in ('atleast(widen(difference(sample_variance(where(t, gt("x", c = 0.2)), 3), population_variance(where(t, ge("x", c = 0.25), le("x", c = 0.75)), 3)), tolerance = 0.01), c = -0.3)',
                  'atmost(widen(difference(population_variance(where(t, gt("x", c = 0.2)), 3), sample_variance(where(t, eq("g", "A"), gt("x", c = 0.2)), 3)), tolerance = 0.01), c = 0.01)'):
        out = tab(claim, X5)
        assert out[0].startswith("line 3: formed:"), (claim, out[0][:200])


def test_4_a_vertex_at_many_rows_is_replaced_by_two_rows():   # was R013 ("checking its certificates needs more than 50000000 counted steps")
    # unr-claims #4: the solver's vertex for one condition's W2 had 100,000 rows of 1000-digit values; two rows answer
    e = "0." + "0" * 997 + "9"
    claim = f'exceeds(difference(sum(where(t, lt("y", c = 1{e[1:]})), "x"), sum(where(t, gt("x", c = 1{"0" * 400}), gt("y", c = 0)), "y")), c = {e})'
    out = tab(claim, "g\tx\ty\nA\t0.5\t1\nB\t0.25\t2\nC\t0.75\t3\n")
    assert out[0].startswith("line 3: formed:"), out[0][:200]


def test_d_named_rows_and_a_variance_of_one_table_cannot_be_written():
    # (d) leftover: the model's gate "named rows and a variance of one table" was removed (dead code). A variance reaches
    # the model only as the statement, under widen(), as one side of a difference of two variances, or compared with a
    # literal c (Model.__init__, vtop); its arguments are a selection and a column position. So a named row (cell, key,
    # header, number) of its table would have to sit in one of these places, and every such spelling refuses first.
    for claim in ('exceeds(difference(sample_variance(t, 2), number(cell(t, 1, 2))), c = 0)',
                  'exceeds(sample_variance(t, 2), c = number(cell(t, 1, 2)))',
                  'widen(sample_variance(t, 2), tolerance = number(cell(t, 1, 2)))',
                  'sample_variance(where(t, eq(1, cell(t, 1, 1))), 2)',
                  'sample_variance(where(t, eq(header(t, 1), "A")), 2)',
                  'sample_variance(t, number(cell(t, 1, 2)))',
                  'difference(sample_variance(t, 2), population_variance(where(t, eq(1, cell(t, key(1, "A"), 1))), 2))'):
        out = tab(claim)
        assert out[0].startswith("line 3: refused [S006") or out[0].startswith("line 3: refused [P006"), (claim, out[0][:200])
