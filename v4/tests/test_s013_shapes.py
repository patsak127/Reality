"""Item 4 (BB's call on Patsak's behalf, 28 Oct 2026 21:52, reversible): the S013 shapes decided exactly, one section per
shape (verify-opus-exact/partb/S13/ITEM4.md). Each: forms, W1 and W2 refusals with checked certificates, a tampered
certificate X001; a claim holding on every input is S008 W1, never R013."""
import hashlib
import itertools
from fractions import Fraction

import helpers  # noqa: F401 (puts src on the path)
from reality4 import kernel as K, witness as W, decide as D, readers as R


def run(claim, data):
    h = hashlib.sha256(data).hexdigest()
    st = W.MemStore({h: data})
    st.begin_program()
    ok, out = K._check(f"file r = sha256:{h}\nclaim {claim}\n".encode(), st)
    return [ln for ln in out if ln.startswith("line")][0]


def run2(claim, files):
    hs = {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}
    st = W.MemStore({hs[n]: b for n, b in files.items()})
    st.begin_program()
    ok, out = K._check(("".join(f"file {n} = sha256:{h}\n" for n, h in hs.items()) + f"claim {claim}\n").encode(), st)
    return [ln for ln in out if ln.startswith("line")][0]


# ---- shape 3: number(bytes(f, o, n)) (SPEC-EXACT 3.11) ----------------------------------------------------------------

B3 = b"75 350 9 99"   # ranges (0, 2) "75", (3, 3) "350", (7, 1) "9", (9, 2) "99"
N2, N3, N1 = "number(bytes(r, 0, 2))", "number(bytes(r, 3, 3))", "number(bytes(r, 7, 1))"


def test_shape3_the_numbers_of_n_bytes_are_the_readers():
    """rnext, rprev, rin and rspell against readers.decimal over every string of 1 to 3 bytes from '0-9.-+eE' (the
    prototype's brute force, partb/S13/s3/brute.txt, went to 5 bytes: 155,134 numbers, 0 disagree)."""
    for n in (1, 2, 3):
        vals = set()
        for t in itertools.product("0123456789.-+eE", repeat=n):
            try:
                q = R.decimal("".join(t))
            except R.Refusal:
                continue
            if q is not None:
                vals.add(q)
        S = sorted(vals)
        assert D.rnext(n, None) == S[0] and D.rprev(n, None) == S[-1]
        for a, b in zip(S, S[1:]):
            assert D.rnext(n, a) == b and D.rprev(n, b) == a and D.rin(n, a) and not D.rin(n, (a + b) / 2)
            assert D.rnext(n, (a + b) / 2) == b and D.rprev(n, (a + b) / 2) == a
        for v in S:
            s = D.rspell(n, v)
            assert len(s) == n and R.decimal(s) == v
    assert D.rprev(3, None) == 9 * 10 ** 9 and D.rnext(D.RAW_LONG + 1, None) is None


def test_shape3_a_one_byte_number_below_100_is_s008_w1():
    """ITEM4's rule: every one-byte number is 0 to 9, so the claim holds on every input that answers: S008 W1."""
    D.CERTS.clear()
    out = run("below(number(bytes(r, 0, 1)), c = 100)", b"7")
    assert "[S008" in out and "W1)" in out, out
    assert sum(D.CERTS.values()) and not any(k.startswith("lemma") for k in D.CERTS), D.CERTS


def test_shape3_forms_and_its_bounds_are_the_layouts():
    assert ": formed:" in run(N2, B3) and ": formed:" in run(f"difference({N2}, {N1})", B3)
    assert ": formed:" in run(f"below({N3}, c = 8999999999)", B3)   # 9e9 is three bytes
    out = run(f"atmost({N3}, c = 9000000000)", B3)
    assert "[S008" in out and "W1)" in out, out
    out = run(f"atleast({N2}, c = -9)", B3)   # two bytes: -9 to 0 and 10 to 99
    assert "[S008" in out and "W1)" in out, out
    assert ": formed:" in run("bytes(r, 0, 2)", B3)


def test_shape3_a_gap_of_the_lattice_is_split_and_checked():
    """No two-byte number lies in (0.5, 9.5], so widen() never changes the answer: S008 W2, resting on 'spell' splits
    (each the model's disjunction, checked); three bytes reach 1.5 there, so it bears and forms."""
    D.CERTS.clear()
    out = run(f"exceeds(widen({N2}, tolerance = 4.5), c = 5)", B3)
    assert "[S008" in out and "W2)" in out, out
    assert D.CERTS.get("split: spell"), D.CERTS
    assert ": formed:" in run(f"exceeds(widen({N3}, tolerance = 4.5), c = 5)", B3)
    out = run(f"exceeds(widen(difference({N2}, {N1}), tolerance = 0.4), c = 0.5)", B3)   # a difference of integers
    assert "[S008" in out and "W2)" in out, out


def test_shape3_a_tampered_spell_split_is_x001(monkeypatch):
    real = D.Model.disjunction
    claim = f"exceeds(widen({N2}, tolerance = 4.5), c = 5)"

    def shifted(self, name, args, case, atoms, more):
        cs, need = real(self, name, args, case, atoms, more)
        if name == "spell":
            (c0, A0), *rest = cs
            cs = [(c0, [({**A0[0][0], 1: A0[0][0].get(1, 0) + 1}, A0[0][1])] + A0[1:])] + rest
        return cs, need
    monkeypatch.setattr(D.Model, "disjunction", shifted)
    out = run(claim, B3)
    assert "[X001" in out, out
    monkeypatch.setattr(D.Model, "disjunction", lambda self, *a: (lambda cs, need: (cs[:-1], need) if a[0] == "spell" else (cs, need))(*real(self, *a)))
    out = run(claim, B3)
    assert "[X001" in out, out


def test_shape3_a_spell_split_covers_its_numbers():
    z = ("z", "raw", "r", 0, 2)
    for v in (Fraction(1, 2), Fraction(5), Fraction(-3, 2), Fraction(10), Fraction(100)):
        cs = D.Model.spell_cases(None, z, v)
        for k in range(-20, 120):
            x = {z: Fraction(k), D.ONE: 1}
            if D.rin(2, Fraction(k)):
                assert any(all(D.value(F, x) > 0 if st else D.value(F, x) >= 0 for F, st in A) for A in cs), (v, k)


def test_shape3_overlapping_ranges_stay_outside():
    out = run("difference(number(bytes(r, 0, 3)), number(bytes(r, 1, 3)))", b"12345")
    assert "[S013" in out, out


# ---- shape 2: size(f) of a file read by tsv() or csv() (SPEC-EXACT 3.12) ------------------------------------------------

T2 = b"a\tb\nx\tabc\n"
C2 = b'a,b\nx,"a,b"\n'
SR = "difference(size(r), rows(tsv(r)))"
CA = 'difference(size(r), count(where(tsv(r), eq(2, "abc"))))'


def test_shape2_size_less_rows_has_its_least_and_its_greatest():
    """The least readable table of n rows: header 'a' (one column), rows of one byte, the last LF dropped: 2n + 1 bytes,
    so size - rows >= 1 on every input (S008 W1, every refusal certified, no lemma); a table is at most MAX_TEXT_FILE
    bytes (R003 past it), so size - rows < MAX_TEXT_FILE + 1 on every input, and = MAX_TEXT_FILE forms."""
    D.CERTS.clear()
    out = run(f"atleast({SR}, c = 1)", T2)
    assert "[S008" in out and "W1)" in out, out
    assert sum(D.CERTS.values()) and not any(k.startswith("lemma") for k in D.CERTS), D.CERTS
    assert ": formed:" in run(f"atleast({SR}, c = 2)", T2)
    out = run(f"below({SR}, c = {R.MAX_TEXT_FILE + 1})", T2)
    assert "[S008" in out and "W1)" in out, out
    assert ": formed:" in run(f"below({SR}, c = {R.MAX_TEXT_FILE})", T2)   # its certificate: 0 rows, MAX_TEXT_FILE bytes


def test_shape2_each_row_type_at_its_least_line():
    """Two columns: header 'a<TAB>b' (3 bytes), a row 'abc' in column 2 at least 5 bytes with its LF, others 2: size -
    count(abc rows) >= 3 on every input; >= 4 fails on the header alone, and no input tells the condition apart (S008 W2).
    In a CSV the literal a,b is quoted: 6 bytes and its LF."""
    for t, lit in ((T2, "abc"), (C2, "a,b")):
        k = "tsv" if t is T2 else "csv"
        v = f'difference(size(r), count(where({k}(r), eq(2, "{lit}"))))'
        out = run(f"atleast({v}, c = 3)", t)
        assert "[S008" in out and "W1)" in out, out
        out = run(f"atleast({v}, c = 4)", t)
        assert "[S008" in out and "W2)" in out, out


def test_shape2_outside_the_first_cut_stays_s013():
    out = run('atleast(difference(size(r), count(where(tsv(r), ge(2, c = 1)))), c = 2)', b"a\tb\n1\t2\n")   # a column read as numbers
    assert "[S013" in out, out


def _dk(k):   # k tsv() calls, no part of it constant: k·(size(r) - rows(tsv(r)))
    e = "difference(size(r), rows(tsv(r)))"
    for _ in range(k - 1):
        e = f"difference({e}, difference(rows(tsv(r)), size(r)))"
    return e, k


def test_shape2_each_tsv_call_charges_the_text_total():
    """(3.12a; BB's call 23:30) Each tsv() call charges the table's whole text to MAX_TEXT_TOTAL (readers.text via
    _cached, also for one file read again; confirmed on bytes: partb/S13/s2r/boundary.txt), so with k calls the table is at
    most min(MAX_TEXT_FILE, MAX_TEXT_TOTAL // k) bytes and every k is decided: with 5, size - rows - 0 - 0 is at most
    floor(2^28 / 5) = 53,687,091 (0 rows) on every input, and that value forms (its certificate read back at that size)."""
    for k in (3, 4, 5, 8):
        N = min(R.MAX_TEXT_FILE, R.MAX_TEXT_TOTAL // k)
        v, f = _dk(k)
        assert v.count("tsv(") == k
        out = run(f"below({v}, c = {f * N + 1})", T2)
        assert "[S008" in out and "W1)" in out, (k, out)
        if k in (4, 5):
            assert ": formed:" in run(f"below({v}, c = {f * N})", T2), k


def test_shape2_a_table_beside_one_is_charged_at_its_least():
    """(3.12a) A second table g beside r (r's size read): g's text is charged per call too, at least its least size (1
    byte: header 'a', the LF dropped, + 2 per row), so 4·size(r) + least(g) <= MAX_TEXT_TOTAL: 4·(size - rows) + size -
    rows(g) is at most 5·(2^26 - 1) on every input (S008 W1); that value forms (without g's charge it would be 5·2^26)."""
    from reality4.syntax import parse_line
    e4, _ = _dk(4)
    v = f"difference({e4}, difference(rows(tsv(g)), size(r)))"
    m = D.Model(parse_line(f"claim below({v}, c = 1)", 1).expr, ["r", "g"], {"r": "file", "g": "file"})
    assert m.sk == [{"r": 4, "g": 1}] and m.sl == {"r", "g"} and m.st == {"r"}
    top = 5 * (2 ** 26 - 1)
    out = run2(f"below({v}, c = {top + 1})", {"r": T2, "g": b"a\n"})
    assert "[S008" in out and "W1)" in out, out
    assert ": formed:" in run2(f"below({v}, c = {top})", {"r": T2, "g": b"a\n"})


def test_shape2_a_one_column_table_with_an_empty_literal_by_its_layout():
    """(3.12b; BB's call 23:30) A one-column table whose column is compared with "": in a TSV an empty line is refused
    (T003), so such rows need a second column (header 'a<TAB>b', rows '<TAB>'); with none, one column. In a CSV the
    empty cell is '""' in one column. The least size is the lesser layout's: a 'layout' split (lay_cases), checked.
    size - count("" rows) >= 1 on every input (the empty table 'a'), and >= 2 fails there only, where no condition
    bears (W2). The certificates in each layout are read back by the real reader at their least size (two columns: 3
    + 2 per "" row; a CSV's one column: 1 + 3 per "" row)."""
    E = 'count(where({k}(r), eq(1, "")))'
    for k, t in (("tsv", b"a\n"), ("csv", b"a\n")):
        e = E.format(k=k)
        D.CERTS.clear()
        out = run(f"atleast(difference(size(r), {e}), c = 1)", t)
        assert "[S008" in out and "W1)" in out, (k, out)
        assert D.CERTS.get("split: layout") and not any(x.startswith("lemma") for x in D.CERTS), D.CERTS
        out = run(f"atleast(difference(size(r), {e}), c = 2)", t)   # fails on 'a' only: no input where the condition bears (W2)
        assert "[S008" in out and "W2)" in out, (k, out)
    from reality4.syntax import parse_line
    for k, two, one in (("tsv", b"a\tb\n\t\nq\t\n\t", None), ("csv", b"a,b\n,\nq,\n,", b'a\n""\nq\n""')):
        m = D.Model(parse_line(f"claim atleast(difference(size(r), {E.format(k=k)}), c = 1)", 1).expr, ["r"], {"r": "file"})
        m.cheld = [0]
        assert m.lay == {"r"}
        et = next(t for t in m.types["r"] if m.cls("r", t, 1)[:2] == ("lit", b""))
        ot = next(t for t in m.types["r"] if t != et)
        b2 = m.stext("r", [et, ot, et], None, 0, 2)
        tab = (R.parse_tsv if k == "tsv" else R.parse_csv)(b2, "h", R.Steps())
        assert [r[0] for r in tab.rows] == ["", m.scell("r", 1, m.cls("r", ot, 1), False), ""] and len(b2) == len(two), (b2, two)
        if one:
            b1 = m.stext("r", [et, ot, et], None, 0, 1)
            assert [r[0] for r in (R.parse_csv(b1, "h", R.Steps())).rows][::2] == ["", ""] and len(b1) == len(one), b1


def test_shape2_a_tampered_layout_split_is_x001(monkeypatch):
    """(3.12b) The search's layout cases are recomputed by the model at the check (Model.disjunction): a split whose
    cases are stronger than the model's (one more byte demanded) is X001."""
    import sys
    lay = D.Model.lay_cases

    def stronger(self, s, case):
        out = lay(self, s, case)
        if sys._getframe(1).f_code.co_name == "disjunction":   # the check's own recomputation: the model's
            return out
        S = {("n", s, "size"): 1}
        return [A + [D.RAtom(D.ge(D.lin((1, S), (1, D.const(-1)))), ("lay", s), A[0].r)] for A in out]
    monkeypatch.setattr(D.Model, "lay_cases", stronger)
    out = run('atleast(difference(size(r), count(where(tsv(r), eq(1, "")))), c = 1)', b"a\n")
    assert "[X001" in out, out


def test_shape2_a_tampered_certificate_is_x001(monkeypatch):
    needed = D.Log.needed

    def tampered(self):
        steps = needed(self)
        for i in range(len(steps) - 1, -1, -1):
            if steps[i][0] == "c" and len(steps[i][1]) > 1:
                steps[i] = ("c", [(u * 2 if k == 0 else u, j) for k, (u, j) in enumerate(steps[i][1])])
                break
        return steps
    monkeypatch.setattr(D.Log, "needed", tampered)
    out = run(f"atleast({SR}, c = 1)", T2)
    assert "[X001" in out, out


def test_shape2_a_wrong_none_is_x001_on_its_replay(monkeypatch):
    one = D.Model.one_solve2

    def wrong(self, atoms, case, budget, bounded, held, log):
        return None if not self.cert and not bounded else one(self, atoms, case, budget, bounded, held, log)
    monkeypatch.setattr(D.Model, "one_solve2", wrong)
    out = run(f"atleast({SR}, c = 2)", T2)
    assert "[X001" in out and "replayed" in out, out


def test_shape2_certificates_are_the_least_tables_padded():
    """The certificate at the least size and above: read back by the real reader, exactly that many bytes."""
    from reality4.syntax import parse_line
    e = parse_line(f"claim atleast({CA}, c = 3)", 1).expr
    m = D.Model(e, ["r"], {"r": "file"})
    m.cheld = [0]
    t = next(t for t in m.types["r"] if m.cls("r", t, 2)[0] == "lit")
    o = next(t for t in m.types["r"] if m.cls("r", t, 2)[0] == "oth")
    least = 3 + 2 * m.st_len[("r", t)] + m.st_len[("r", o)]
    for n in (least, least + 1, least + 2, least + 40):
        b = m.stext("r", [t, o, t], n, 0)
        assert len(b) == n, (n, b)
        tab = R.parse_tsv(b, "h", R.Steps())
        assert [r[1] for r in tab.rows] == ["abc", "", "abc"] and len(tab.header) == 2


# ---- shape 1: tsv(f) and csv(f) of one file beyond tc1 (SPEC-EXACT 3.13) ----------------------------------------------

T1 = b"a,b\na,b\nx,y\n"
TW = 'count(where(tsv(r), eq(1, "{b}")))'
CW = 'count(where(csv(r), eq(1, "a"), eq(2, "b")))'


def test_shape1_a_tsv_line_is_the_csv_cells_joined():
    """A file both readers read holds no tab, quote or ';', so its TSV cell is the CSV line: a tsv() literal "a,b" is the
    rows whose two CSV cells are a and b when the file has two CSV columns (Wc, one per file), and no row otherwise. So
    the tsv count never exceeds the csv one (S008 W1, every certificate checked, no lemma), and they differ (formed)."""
    for b, cw in (("a,b", CW), ("a,b,c", CW), ("a", 'count(where(csv(r), eq(1, "a")))')):
        D.CERTS.clear()
        out = run(f"below(difference({TW.format(b=b)}, {cw}), c = 1)", T1)
        assert "[S008" in out and "W1)" in out, (b, out)
        assert D.CERTS and not any(x.startswith("lemma") for x in D.CERTS), D.CERTS
    out = run(f"atleast(difference({TW.format(b='a,b')}, {CW}), c = 0)", T1)
    assert ": formed:" in out, out
    out = run('atleast(difference(rows(csv(r)), count(where(tsv(r), ne(1, "a,b")))), c = 0)', T1)
    assert "[S008" in out and "W1)" in out, out


def test_shape1_a_literal_no_file_holds_has_no_row():
    """A tsv() literal with a quote or ';', the empty line, or fewer commas than the csv columns read is no line of a
    file both readers read: it has no class (no row); "a,b" is one."""
    from reality4.syntax import parse_line
    e = 'count(where(tsv(r), eq(1, "a;b"), ne(1, ""), ne(1, "a,b"), ne(1, "x")))'
    m = D.Model(parse_line(f'claim below(difference({e}, count(where(csv(r), eq(2, "b")))), c = 1)', 1).expr, ["r"], {"r": "file"})
    assert [c[1] for c in m.classes[("r", 0)]] == [b"a,b", None], m.classes[("r", 0)]


def test_shape1_certificate_rows_read_back():
    """(3.13) the certificate of case Wc: a bare table of Wc columns; a row whose line is b holds b's pieces, another row
    in each unread column a text that is no piece there; both readers read it back so."""
    from reality4.syntax import parse_line
    m = D.Model(parse_line(f"claim below(difference({TW.format(b='a,p,c')}, count(where(csv(r), eq(1, \"a\")))), c = 1)", 1).expr, ["r"], {"r": "file"})
    assert m.tw == {"r"} and m.wcs["r"] == [3, "o"], m.wcs
    lt = next(t for t in m.tok[("r", 3)] if m.cls("r", t, 0)[0] == "lit")
    ot = next(t for t in m.tok[("r", 3)] if m.cls("r", t, 0)[0] == "oth" and m.cls("r", t, 1)[:2] == ("lit", b"a"))
    assert not any(m.cls("r", t, 0)[0] == "lit" for t in m.tok[("r", "o")])
    rows = m.tw_rows("r", 3, [m.row("r", t, 0, {}, None) for t in (lt, ot)], [lt, ot])
    data = m.table("r", rows, {}, True, 3)
    assert [r[0] for r in R.parse_tsv(data, "h", R.Steps()).rows][0] == "a,p,c"
    assert [list(r) for r in R.parse_csv(data, "h", R.Steps()).rows][1][0] == "a" and R.parse_tsv(data, "h", R.Steps()).rows[1][0] != "a,p,c"


def test_shape1_a_tampered_certificate_is_x001(monkeypatch):
    needed = D.Log.needed

    def tampered(self):
        steps = needed(self)
        for i in range(len(steps) - 1, -1, -1):
            if steps[i][0] == "c" and len(steps[i][1]) > 1:
                steps[i] = ("c", [(u * 2 if k == 0 else u, j) for k, (u, j) in enumerate(steps[i][1])])
                break
        return steps
    monkeypatch.setattr(D.Log, "needed", tampered)
    out = run(f"below(difference({TW.format(b='a,b')}, {CW}), c = 1)", T1)
    assert "[X001" in out, out


def test_shape1_a_forced_look_alike_line_is_decided():
    """(3.13a) csv cells 1 and b force the line "1,b", which looks like the tsv() literal "l,b": its own class, so a row
    of it makes that where() refuse K002 as a row "l,b" makes the csv where() refuse; every answered input has the csv
    count at least the tsv one: S008 W1 (once S013), certificates checked, no lemma; a tampered certificate is X001."""
    from reality4.syntax import parse_line
    cl = 'atleast(difference(count(where(csv(r), eq(2, "b"), eq(1, "1"))), count(where(tsv(r), eq(1, "l,b"), ne(1, "a,rn")))), c = -2)'
    D.CERTS.clear()
    out = run(cl, b"a,b\nx,y\n")
    assert "[S008" in out and "W1)" in out, out
    assert D.CERTS and not any(x.startswith("lemma") for x in D.CERTS), D.CERTS
    m = D.Model(parse_line(f"claim {cl}", 1).expr, ["r"], {"r": "file"})
    assert b"1,b" in [c[1] for c in m.classes[("r", 0)]], m.classes[("r", 0)]
    out = run('atmost(count(where(tsv(r), eq(1, "l,b"))), c = 5)', b"a,b\nx,y\n")
    assert ": formed:" in out, out


def test_shape1_a_forced_look_alike_tampered_is_x001(monkeypatch):
    needed = D.Log.needed

    def tampered(self):
        steps = needed(self)
        for i in range(len(steps) - 1, -1, -1):
            if steps[i][0] == "c" and len(steps[i][1]) > 1:
                steps[i] = ("c", [(u * 2 if k == 0 else u, j) for k, (u, j) in enumerate(steps[i][1])])
                break
        return steps
    monkeypatch.setattr(D.Log, "needed", tampered)
    cl = 'atleast(difference(count(where(csv(r), eq(2, "b"), eq(1, "1"))), count(where(tsv(r), eq(1, "l,b"), ne(1, "a,rn")))), c = -2)'
    out = run(cl, b"a,b\nx,y\n")
    assert "[X001" in out, out


N1T = "number(cell(tsv(r), 1, 1))"


def test_shape1_a_tsv_line_read_as_a_number():
    """(3.13b) number() of a tsv() line beside csv() reads: the file's csv width Wc is a case, 1 or more; in Wc = 1 the
    line is csv column 1's cell, in Wc >= 2 it holds a comma, so number() refuses V005 on every row there is. On the
    inputs that answer, the line read as a number is csv column 1's number: S008 W1 (every certificate checked, no
    lemma); beside a sum it varies (formed); with a csv column 2 read, Wc = 1 is no case."""
    from reality4.syntax import parse_line
    for cl in (f"atleast(difference({N1T}, number(cell(csv(r), 1, 1))), c = 0)", f"atmost(difference({N1T}, max(csv(r), 1)), c = 0)",
               f"difference({N1T}, number(cell(csv(r), 1, 1)))"):
        D.CERTS.clear()
        out = run(cl, b"a\n5\n")
        assert "[S008" in out and "W1)" in out, (cl, out)
        assert D.CERTS and not any(x.startswith("lemma") for x in D.CERTS), D.CERTS
    out = run(f"atleast(difference({N1T}, sum(csv(r), 1)), c = 0)", b"a\n5\n")
    assert ": formed:" in out, out
    out = run(f"atleast(difference({N1T}, sum(csv(r), 2)), c = 0)", b"a,b\n5,6\n")
    assert "[V005" in out, out
    m = D.Model(parse_line(f"claim atleast(difference({N1T}, sum(csv(r), 1)), c = 0)", 1).expr, ["r"], {"r": "file"})
    assert m.tn == {"r"} and m.wcs["r"] == [1, "o"] and m.wo["r"] == 2, m.wcs
    m = D.Model(parse_line(f"claim atleast(difference({N1T}, sum(csv(r), 2)), c = 0)", 1).expr, ["r"], {"r": "file"})
    assert m.wcs["r"] == ["o"], m.wcs


def test_shape1_a_tsv_line_as_a_number_tampered_is_x001(monkeypatch):
    needed = D.Log.needed

    def tampered(self):
        steps = needed(self)
        for i in range(len(steps) - 1, -1, -1):
            if steps[i][0] == "c" and len(steps[i][1]) > 1:
                steps[i] = ("c", [(u * 2 if k == 0 else u, j) for k, (u, j) in enumerate(steps[i][1])])
                break
        return steps
    monkeypatch.setattr(D.Log, "needed", tampered)
    out = run(f"atmost(difference({N1T}, max(csv(r), 1)), c = 0)", b"a\n5\n")
    assert "[X001" in out, out


def test_shape1_an_aggregate_of_a_tsv_line():
    """(3.13c) sum/mean/min/max/median/order of tsv(f)'s column 1 (or of a where() of it) beside csv() reads: in Wc = 1
    the csv column 1's aggregate, in Wc >= 2 every selected line is no decimal (V005; a sum of no rows is 0). So
    sum(tsv) - sum(csv) is 0 on every input that answers (S008 W1), mean(tsv) >= min(csv) holds on every one (S008 W1),
    certificates checked, no lemma; a where() of it beside a sum: at most 0 on every input (S008 W1 by hand: Wc = 1 minus the 5 rows), at least 0 varies (formed); a tampered certificate is X001."""
    for cl in ("difference(sum(tsv(r), 1), sum(csv(r), 1))", "atleast(difference(mean(tsv(r), 1), min(csv(r), 1)), c = 0)",
               "atmost(difference(max(tsv(r), 1), max(csv(r), 1)), c = 0)"):
        D.CERTS.clear()
        out = run(cl, b"a\n5\n")
        assert "[S008" in out and "W1)" in out, (cl, out)
        assert D.CERTS and not any(x.startswith("lemma") for x in D.CERTS), D.CERTS
    out = run('atmost(difference(sum(where(tsv(r), ne(1, "5")), 1), sum(csv(r), 1)), c = 0)', b"a\n5\n")
    assert "[S008" in out and "W1)" in out, out
    out = run('atleast(difference(sum(where(tsv(r), ne(1, "5")), 1), sum(csv(r), 1)), c = 0)', b"a\n4\n")
    assert ": formed:" in out, out
    out = run("atleast(difference(sum(tsv(r), 1), sum(csv(r), 2)), c = 0)", b"a,b\n5,6\n")
    assert "[V005" in out, out


def test_shape1_an_aggregate_of_a_tsv_line_tampered_is_x001(monkeypatch):
    needed = D.Log.needed

    def tampered(self):
        steps = needed(self)
        for i in range(len(steps) - 1, -1, -1):
            if steps[i][0] == "c" and len(steps[i][1]) > 1:
                steps[i] = ("c", [(u * 2 if k == 0 else u, j) for k, (u, j) in enumerate(steps[i][1])])
                break
        return steps
    monkeypatch.setattr(D.Log, "needed", tampered)
    out = run("atleast(difference(mean(tsv(r), 1), min(csv(r), 1)), c = 0)", b"a\n5\n")
    assert "[X001" in out, out


def test_shape1_a_tsv_header_read_as_a_number():
    """(3.13d) number(header(tsv(f), 1)) beside csv() reads: tsv(f)'s one name is the csv names joined, so in Wc = 1 it
    is csv name 1 and in Wc >= 2 it holds a comma (V005). On the inputs that answer it equals number(header(csv(f), 1)):
    S008 W1, certificates checked, no lemma; beside a sum it varies (formed); a tampered certificate is X001."""
    H = "number(header(tsv(r), 1))"
    for cl in (f"difference({H}, number(header(csv(r), 1)))", f"below(difference({H}, number(header(csv(r), 1))), c = 1)"):
        D.CERTS.clear()
        out = run(cl, b"7\n5\n")
        assert "[S008" in out and "W1)" in out, (cl, out)
        assert D.CERTS and not any(x.startswith("lemma") for x in D.CERTS), D.CERTS
    assert ": formed:" in run(f"atleast(difference({H}, sum(csv(r), 1)), c = 0)", b"7\n5\n")
    assert "[V005" in run(f"atleast(difference({H}, sum(csv(r), 2)), c = 0)", b"7,8\n5,6\n")


def test_shape1_a_tsv_header_tampered_is_x001(monkeypatch):
    """A certificate whose header is not the one the model chose (its name 1 swapped for "c1") is X001, not a form."""
    bytes_of = D.Model.bytes_of

    def tampered(self, case, x, seed=0):
        return {s: b"c1\n" + b.split(b"\n", 1)[1] for s, b in bytes_of(self, case, x, seed).items()}
    monkeypatch.setattr(D.Model, "bytes_of", tampered)
    out = run("atleast(difference(number(header(tsv(r), 1)), sum(csv(r), 1)), c = 0)", b"7\n5\n")
    assert "[X001" in out, out


def test_shape1_a_tsv_line_under_a_key():
    """(3.13e) number(cell(tsv(f), key(1, b), 1)) beside csv() reads: the keyed row's line is b (a key holds no comma, K001,
    so in Wc >= 2 no line is b: V004), so the cell has one answer on every input that answers: S008 W1 on cell(),
    as a csv() key's cell (its class is the literal: no option differs, so no search and nothing to certify); beside
    the line of row 1 it varies (formed)."""
    for t in ("tsv", "csv"):
        out = run(f'difference(number(cell({t}(r), key(1, "5"), 1)), sum(csv(r), 1))', b"7\n5\n")
        assert "[S008" in out and "W1)" in out and "cell()" in out, (t, out)
    out = run('atleast(difference(number(cell(tsv(r), 1, 1)), max(csv(r), 1)), c = 0)', b"7\n5\n")
    assert ": formed:" in out, out


def test_shape1_widen_beside_a_file_read_by_both_readers():
    """(3.13f) widen() beside tsv() and csv() reads of one file: a widened value's identity is the kernel's (v4 SPEC 5.1:
    a cell's is its file, row and column, a selection's its files and rows, neither names the reader), and the model's
    ident() is that, so widen(number(cell(tsv(f), 1, 1))) and widen(number(cell(csv(f), 1, 1))) are one symbol: their
    difference is 0 on every input that answers (S008 W1); a widened tsv() line beside max(csv()) at least -1 varies
    (formed)."""
    W1 = "widen(number(cell(tsv(r), 1, 1)), tolerance = 1)"
    D.CERTS.clear()
    out = run(f"atmost(difference({W1}, widen(number(cell(csv(r), 1, 1)), tolerance = 1)), c = 0)", b"a\n5\n")
    assert "[S008" in out and "W1)" in out, out
    out = run("atmost(difference(widen(sum(tsv(r), 1), tolerance = 1), sum(csv(r), 1)), c = 1)", b"a\n5\n")
    assert "[S008" in out and "W1)" in out, out
    assert not any(x.startswith("lemma") for x in D.CERTS), D.CERTS
    assert ": formed:" in run(f"atleast(difference({W1}, max(csv(r), 1)), c = -1)", b"a\n5\n")


def test_shape1_a_variance_of_a_tsv_line():
    """(3.13g) a variance of tsv(f)'s column 1 beside csv() reads: in Wc = 1 csv column 1's over the same rows, in Wc >= 2
    every selected line is no decimal (V005; V003 below 1 + ddof rows), as 3.13c. The variance shape compares two
    selections without the types either candidate's case gives no row (a tsv() literal's line class beside csv column
    1's literal in Wc = 1). So svar(tsv) - svar(csv) is 0 on every input that answers (S008 W1), svar(tsv) - pvar(csv)
    at least 0 holds on every one (S008 W1), no lemma; a where() of the line beside the same where() of csv column 1:
    0 (S008 W1); svar(tsv) - pvar(csv) varies (formed, certificates written at Wc = 1 and read back); with csv column
    2 read the line holds a comma (V005)."""
    for cl in ("difference(sample_variance(tsv(r), 1), sample_variance(csv(r), 1))", "atleast(difference(sample_variance(tsv(r), 1), population_variance(csv(r), 1)), c = 0)",
               'atleast(difference(sample_variance(where(tsv(r), ne(1, "5")), 1), sample_variance(where(csv(r), ne(1, "5")), 1)), c = 0)'):
        D.CERTS.clear()
        out = run(cl, b"7\n5\n6\n4\n")
        assert "[S008" in out and "W1)" in out, (cl, out)
        assert D.CERTS and not any(x.startswith("lemma") for x in D.CERTS), D.CERTS
    out = run("difference(sample_variance(tsv(r), 1), population_variance(csv(r), 1))", b"7\n5\n6\n")
    assert ": formed:" in out and "= 0.25" in out, out
    assert ": formed:" in run("atmost(difference(sample_variance(tsv(r), 1), population_variance(csv(r), 1)), c = 0)", b"7\n7\n7\n")
    assert "[V005" in run("difference(population_variance(tsv(r), 1), sample_variance(csv(r), 2))", b"a,b\n5,1\n6,2\n")


def test_shape1_a_variance_of_a_tsv_line_tampered_range_is_x001(monkeypatch):
    from fractions import Fraction as F
    real = D.Decide.rest
    monkeypatch.setattr(D.Decide, "rest", lambda self, kind, what, v: real(self, kind, ([(F(-1), F(1))] * len(what[0]), what[1]) if kind == "vrange" else what, v))
    out = run("atleast(difference(sample_variance(tsv(r), 1), population_variance(csv(r), 1)), c = 0)", b"7\n5\n6\n")
    assert "[X001" in out and "range meets" in out, out


SW = 'difference(difference(size(r), count(where(tsv(r), eq(1, "a,b")))), difference(rows(csv(r)), count(where(csv(r), eq(1, "a")))))'   # size - n(a,b) - rows + n(a)


def test_shape1_size_beside_a_file_read_by_both_readers():
    """(3.13h, case 6) size(f) beside rows() and count(where()) of tsv(f) and csv(f). rows() of tsv(f) only (3.10): the
    least table is 'a' and a byte and LF per row, so size - rows(tsv) - (rows(csv) - n(a)) = 1 + n(a) at the least: >= 1
    on every input (S008 W1) and = 1 forms. A tsv() literal "a,b": in Wc = 2 the least is 'a,b' + 4 bytes per a,b line,
    3 per 'a,' and 2 per ','; so size - n(a,b) - rows + n(a) >= 3 there; in every other width the least width is 1 ('a',
    two bytes a line): >= 1. So >= 1 holds on every input (S008 W1, certificates checked, no lemma) and >= 2 forms (the
    file 'a': the 'o' case's least is at its least width, not at the width its other certificates use; for SW, csv()'s
    eq(1, "a") bears on no input there, W2)."""
    tc = 'difference(difference(size(r), rows(tsv(r))), difference(rows(csv(r)), count(where(csv(r), eq(1, "a")))))'
    for cl, data in ((tc, b"7\n5\n"), (SW, T1)):
        D.CERTS.clear()
        out = run(f"atleast({cl}, c = 1)", data)
        assert "[S008" in out and "W1)" in out, (cl, out)
        assert sum(D.CERTS.values()) and not any(k.startswith("lemma") for k in D.CERTS), D.CERTS
        out = run(f"atleast({cl}, c = 2)", data)   # fails on the file 'a' (SW: no input where csv()'s eq(1, "a") bears, W2)
        assert ": formed:" in out if cl == tc else "[S008" in out and "W2)" in out, (cl, out)


def test_shape1_size_certificates_read_back_by_both_readers():
    """The certificate of each width case at its least size and above: exactly n bytes, both readers read it, and the
    tsv() lines are the csv cells joined."""
    from reality4.syntax import parse_line
    m = D.Model(parse_line(f"claim atleast({SW}, c = 1)", 1).expr, ["r"], {"r": "file"})
    m.cheld = [0]
    for wc in m.wcs["r"]:
        W0 = wc if wc != "o" else m.wo["r"]
        ts = sorted(m.tok[("r", wc)])
        least = 2 * W0 - 1 + sum(m.st_len[("r", t, W0)] for t in ts)
        for n in (least, least + 1, least + 7):
            b = m.stext("r", ts, n, 0, W0)
            assert len(b) == n, (wc, n, b)
            c, t = R.parse_csv(b, "h", R.Steps()), R.parse_tsv(b, "h", R.Steps())
            assert len(c.header) == W0 and [r[0] for r in t.rows] == [",".join(r) for r in c.rows], (wc, b)
    assert m.wo["r"] == 1   # no literal line of one column: the 'o' case's least width


def test_shape1_size_an_empty_csv_cell_splits_the_other_widths():
    """A row with an empty csv cell has no line in one column (CSV writes '""', which TSV refuses, T005), so the 'o'
    case (every width no tsv() literal has) is split as 3.12b's layouts: width 1 with no such row, or the next width the
    case has (here 3) with one; the split is the model's (Model.disjunction 'layout') and checked. size - n(a,b) - rows +
    n(empty) >= 1 on every input (S008 W1), and each layout's certificate reads back at its least size and above."""
    from reality4.syntax import parse_line
    se = 'difference(difference(size(r), count(where(tsv(r), eq(1, "a,b")))), difference(rows(csv(r)), count(where(csv(r), eq(1, "")))))'
    D.CERTS.clear()
    out = run(f"atleast({se}, c = 1)", T1)
    assert "[S008" in out and "W1)" in out, out
    assert not any(k.startswith("lemma") for k in D.CERTS), D.CERTS
    m = D.Model(parse_line(f"claim atleast({se}, c = 1)", 1).expr, ["r"], {"r": "file"})
    m.cheld = [0]
    assert "r" in m.lay and m.wo["r"] == 1 and m.wo2["r"] == 3
    e = next(t for t in m.tok[("r", "o")] if m.st_len[("r", t, 1)] is None)   # the empty-cell row
    assert m.cls("r", e, 1)[:2] == ("lit", b"")
    for W0 in (1, 3):
        ts = sorted(t for t in m.tok[("r", "o")] if m.st_len[("r", t, W0)] is not None)
        assert (e in ts) == (W0 == 3)
        least = 2 * W0 - 1 + sum(m.st_len[("r", t, W0)] for t in ts)
        for n in (least, least + 5):
            b = m.stext("r", ts, n, 0, W0)
            c, t = R.parse_csv(b, "h", R.Steps()), R.parse_tsv(b, "h", R.Steps())
            assert len(b) == n and len(c.header) == W0 and [r[0] for r in t.rows] == [",".join(r) for r in c.rows], (W0, b)


def test_shape1_size_tampered_certificate_is_x001(monkeypatch):
    """A refusal's certificate with one multiplier doubled: the check fails, X001 (as 3.12's)."""
    needed = D.Log.needed

    def tampered(self):
        steps = needed(self)
        for i in range(len(steps) - 1, -1, -1):
            if steps[i][0] == "c" and len(steps[i][1]) > 1:
                steps[i] = ("c", [(u * 2 if k == 0 else u, j) for k, (u, j) in enumerate(steps[i][1])])
                break
        return steps
    monkeypatch.setattr(D.Log, "needed", tampered)
    out = run(f"atleast({SW}, c = 1)", T1)
    assert "[X001" in out, out


def test_shape1_outside_the_first_cut_stays_s013():
    """size() of a file read by tsv() and csv(): S013 (listed in KNOWN-OPEN)."""
    for cl in ['difference(difference(size(r), rows(csv(r))), number(cell(tsv(r), 1, 1)))']:
        out = run(cl, b"7\n5\n6\n")
        assert "[S013" in out, (cl, out)


# ---- shape 6: two quantities of one dataset's recordings (SPEC-EXACT 3.9a) ---------------------------------------------

RS6 = 'recordings(b, "x")'


def _sclaim(c):
    from test_exact_decide import sclaim
    return sclaim(c)


def test_shape6_volumes_beside_events_or_trials_are_decided():
    """(3.9a; BB's call on Patsak's behalf 29 Oct 2026 06:15, reversible) the image's volumes beside the events file's
    events or trials of a type, over one dataset's recordings: kinds per pair (a 3-D image, no events file, no
    trial_type column, each independent), each quantity's sum per region. On the Phase F dataset (3 recordings, 5
    volumes, events go/stop/go each): forms with the kernel's values; a filter that never changes the set W2; a
    difference of one quantity with itself W1 (decided exactly, a checked certificate), not R013."""
    out = _sclaim(f'difference(sum({RS6}, "volumes"), sum({RS6}, "events"))')
    assert "formed:" in out and "= 6 (Exact)" in out, out
    out = _sclaim(f'difference(sum({RS6}, "volumes"), sum({RS6}, "trials", "go"))')
    assert "formed:" in out and "= 9 (Exact)" in out, out
    out = _sclaim(f'atmost(difference(sum(recordings(b, "x", participants(b)), "trials", "go"), sum({RS6}, "volumes")), c = 1)')
    assert "formed:" in out, out   # (H06) the participant filter bears through V007 (was S008 W2, v4 fix 08)
    out = _sclaim(f'atmost(difference(sum(recordings(b, "x", where(participants(b), eq("group", "a"), eq("group", "a"))), "trials", "go"), sum({RS6}, "volumes")), c = 1)')
    assert "[S008" in out and "W2" in out and "decided exactly" in out, out
    out = _sclaim(f'atleast(difference(sum({RS6}, "volumes"), difference(sum({RS6}, "events"), sum({RS6}, "events"))), c = 0)')
    assert "[S008" in out and "W1" in out and "decided exactly" in out, out
    out = _sclaim(f'difference(sum(recordings(b, "x", where(participants(b), eq("group", "a"))), "volumes"), sum({RS6}, "trials", "go"))')
    assert "formed:" in out, out


def test_shape6_kinds_pair_up_independently():
    """Model.rs_jk: one kind per pair of the quantities' kinds (volumes: ok, 3-D; trials: ok, no events file, no
    trial_type column), and rs_nq sums the pairs holding a quantity's kind."""
    m = D.Model.__new__(D.Model)
    m.rsm, m.rsq = {"d": (("trials", b"go"), ("volumes", None))}, {}
    J = m.rs_jk("d")
    assert len(J) == 6 and set(J) == {(a, b) for a in ("ok", "noev", "nocol") for b in ("ok", "3d")}
    assert set(m.rs_nq("d", "x", 1, "3d", 0)) == {("n", "d", "rs", "x", (a, "3d"), 0) for a in ("ok", "noev", "nocol")}


def test_shape6_a_tampered_certificate_is_x001(monkeypatch):
    """A W2 refusal's certificate with one multiplier doubled: the check fails, X001."""
    needed = D.Log.needed

    def tampered(self):
        steps = needed(self)
        for i in range(len(steps) - 1, -1, -1):
            if steps[i][0] == "c" and len(steps[i][1]) > 1:
                steps[i] = ("c", [(u * 2 if k == 0 else u, j) for k, (u, j) in enumerate(steps[i][1])])
                break
        return steps
    monkeypatch.setattr(D.Log, "needed", tampered)
    out = _sclaim(f'atmost(difference(sum(recordings(b, "x", where(participants(b), eq("group", "a"), eq("group", "a"))), "trials", "go"), sum({RS6}, "volumes")), c = 1)')   # (H06) a repeated condition's W2; the participant filter's claim forms now
    assert "[X001" in out, out


def test_shape6_outside_the_cuts_stays_s013():
    """A mean, min or max of two quantities: S013 (KNOWN-OPEN). tr beside a count is U001 before any decision; two
    look-alike trial types are K002 in the kernel before any decision."""
    for cl, why in [(f'difference(max({RS6}, "volumes"), sum({RS6}, "events"))', "a mean, min or max of two quantities")]:
        out = _sclaim(cl)
        assert "[S013" in out and why in out, (cl, out)
    assert "[U001" in _sclaim(f'difference(sum({RS6}, "volumes"), sum({RS6}, "tr"))')
    assert "[K002" in _sclaim(f'difference(sum({RS6}, "trials", "go"), sum({RS6}, "trials", "Go"))')


def test_shape6_two_quantities_of_one_events_file_are_decided():
    """(3.9b; BB's call on Patsak's behalf 29 Oct 2026 07:08, reversible) events and trials of types read from one events
    file: on a file with a trial_type column events >= the read types' trials (filler rows of another type make up the
    rest); without one, events answers and trials refuse V002. A claim holding on every input is S008 W1 with a checked
    certificate (never R013); its subset/superset variants form or refuse by the sets."""
    RA = 'recordings(b, "x", where(participants(b), eq("group", "a")))'
    out = _sclaim(f'atleast(difference(sum({RS6}, "events"), sum({RS6}, "trials", "go")), c = 0)')
    assert "[S008" in out and "W1" in out and "decided exactly" in out, out
    out = _sclaim(f'atleast(difference(difference(sum({RS6}, "events"), sum({RS6}, "trials", "go")), sum({RS6}, "trials", "stop")), c = 0)')
    assert "[S008" in out and "W1" in out and "decided exactly" in out, out
    out = _sclaim(f'atleast(difference(sum({RS6}, "events"), sum({RA}, "trials", "go")), c = 0)')
    assert "[S008" in out and "W1" in out, out
    out = _sclaim(f'atleast(difference(sum({RA}, "events"), sum({RS6}, "trials", "go")), c = 0)')
    assert "formed:" in out, out
    out = _sclaim(f'difference(sum({RS6}, "trials", "stop"), sum({RS6}, "trials", "go"))')
    assert "formed:" in out and "= -3 (Exact)" in out, out
    out = _sclaim(f'difference(sum({RS6}, "events"), sum({RS6}, "trials", "go"))')
    assert "formed:" in out and "= 3 (Exact)" in out, out


def test_shape6_without_the_coupling_a_wrong_form_is_caught(monkeypatch):
    """Mutant: Model.rs_couple (events >= trials) dropped. The model then claims an input where events < trials; no
    file has one, so its certificate is not confirmed on bytes: X001, never a verdict."""
    monkeypatch.setattr(D.Model, "rs_couple", lambda self, d, t, r: [])
    out = _sclaim(f'atleast(difference(sum({RS6}, "events"), sum({RS6}, "trials", "go")), c = 0)')
    assert "[X001" in out, out


def _nclaim(c, recs=(("", 1, 2), ("_acq-hi", 1, 3))):
    """c on a dataset with sub-01 task-x recordings, one per (entities suffix, TR, volumes), sidecars beside the images."""
    import hashlib
    from fractions import Fraction
    from reality4 import kernel as K, readers as R
    files = {"dataset_description.json": b'{"Name": "g", "BIDSVersion": "1.0.1"}', "README": b"g\n"}
    for e, tr, v in recs:
        stem = f"sub-01/func/sub-01_task-x{e}"
        files[stem + "_bold.nii"] = W._nii((1, 1, 1, v), Fraction(tr))
        files[stem + "_bold.json"] = ('{"TaskName": "x", "RepetitionTime": %s}' % tr).encode()
        files[stem + "_events.tsv"] = b"onset\tduration\n1\t1\n"
    blobs = {hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (R.MANIFEST_MAGIC + "\n" + "".join(f"{hashlib.sha256(files[p]).hexdigest()}\t{len(files[p])}\t{p}\n" for p in sorted(files))).encode()
    blobs[hashlib.sha256(man).hexdigest()] = man
    st = W.MemStore(blobs)
    st.begin_program()
    prog = f'dataset d = sha256:{hashlib.sha256(man).hexdigest()}\nlet b = bids(d)\nclaim {c}\n'
    return [ln for ln in K._check(prog.encode(), st)[1] if ln.startswith("line")][0]


N0, NA, NAR = 'recording(b, "01", "x")', 'recording(b, "01", "x", acq("hi"))', 'recording(b, "01", "x", acq("hi"), rec("lo"))'


def test_shape5_nested_recordings_are_decided():
    """(3.8a; BB's call on Patsak's behalf 29 Oct 2026 07:30, reversible) two named recordings, one's labels within the
    other's: the smaller one's sidecar is inherited by the other, which overrides it with its own, so every pair of values
    stays reachable; the certificate puts the inherited sidecar a folder up (a deeper one overrides it, S0133)."""
    out = _nclaim(f'difference(volumes({N0}), volumes({NA}))')
    assert "formed:" in out and "= -1 (Exact)" in out, out
    out = _nclaim(f'atleast(difference(tr({N0}), tr({NA})), c = 0 s)')
    assert "formed:" in out, out
    out = _nclaim(f'difference(difference(tr({N0}), tr({NA})), tr({NAR}))', recs=(("", 1, 2), ("_acq-hi", 1, 3), ("_acq-hi_rec-lo", 1, 2)))
    assert "formed:" in out, out
    out = _nclaim(f'difference(events({N0}), events({NA}))')
    assert "formed:" in out and "= 0 (Exact)" in out, out


def test_shape5_a_recording_and_its_run_never_answer_together():
    """A recording and one equal but for a run label: a dataset holding both refuses in bids() (B30 inside B00, S0265),
    one without the other refuses V004, so a statement naming both never answers and is never decided (four recordings
    nested by labels always hold such a pair: rdep's NotT is not reached by a statement that answers)."""
    out = _nclaim(f'difference(volumes({N0}), volumes(recording(b, "01", "x", "1")))', recs=(("", 1, 2), ("_run-1", 1, 3)))
    assert "line 2: refused [B00" in out and "scan of its own" in out, out
    out = _nclaim(f'difference(volumes({N0}), volumes(recording(b, "01", "x", "1")))')
    assert "[V004" in out, out


def test_shape5_sidecars_side_by_side_are_caught(monkeypatch):
    """Mutant: every sidecar beside its image (rdep 2). The certificate with two TRs then sets RepetitionTime twice in one
    folder (B30 inside B00), so the form is not confirmed on bytes: X001, never a verdict."""
    real = D.Model.__init__

    def flat(self, *a, **k):
        real(self, *a, **k)
        self.rdep = {key: 2 for key in getattr(self, "rdep", {})}
    monkeypatch.setattr(D.Model, "__init__", flat)
    out = _nclaim(f'atleast(difference(tr({N0}), tr({NA})), c = 0 s)')
    assert "[X001" in out, out


def _pclaim(c, rows=(("01", "a"), ("02", "b"), ("03", "a")), recs=(("01", 1, 3),)):
    """c on a dataset whose participants.tsv (participant_id, group) has these rows and with sub-L task-x recordings
    (label, TR, volumes) each with a one-row events file; every other participant a T1w image."""
    import hashlib
    from fractions import Fraction
    from reality4 import kernel as K, readers as R
    files = {"dataset_description.json": b'{"Name": "g", "BIDSVersion": "1.0.1"}', "README": b"g\n",
             "participants.tsv": ("participant_id\tgroup\n" + "".join(f"sub-{L}\t{g}\n" for L, g in rows)).encode()}
    for L, tr, v in recs:
        stem = f"sub-{L}/func/sub-{L}_task-x"
        files[stem + "_bold.nii"] = W._nii((1, 1, 1, v), Fraction(tr))
        files[stem + "_bold.json"] = ('{"TaskName": "x", "RepetitionTime": %s}' % tr).encode()
        files[stem + "_events.tsv"] = b"onset\tduration\n1\t1\n"
    for L, _ in rows:
        if L not in {r[0] for r in recs}:
            files[f"sub-{L}/anat/sub-{L}_T1w.nii"] = W._nii((1, 1, 1), 1)
    blobs = {hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (R.MANIFEST_MAGIC + "\n" + "".join(f"{hashlib.sha256(files[p]).hexdigest()}\t{len(files[p])}\t{p}\n" for p in sorted(files))).encode()
    blobs[hashlib.sha256(man).hexdigest()] = man
    st = W.MemStore(blobs)
    st.begin_program()
    prog = f'dataset d = sha256:{hashlib.sha256(man).hexdigest()}\nlet b = bids(d)\nlet t = participants(b)\nlet r = recording(b, "01", "x")\nclaim {c}\n'
    return [ln for ln in K._check(prog.encode(), st)[1] if ln.startswith("line")][0]


def test_shape4_participants_beside_a_named_recording_are_decided():
    """(3.8b; BB's call on Patsak's behalf 29 Oct 2026 08:40, reversible) participants(b) and a named recording of one
    dataset: bids() refuses a subject folder without a participants.tsv row (B11), so a recording there has its
    subject's row: a literal's class when participant_id is read and sub-L is one, else a row whose label is no literal.
    The values form with the kernel's; a filter that never changes the set is S008 W2; a selection that has no row is S011."""
    out = _pclaim('difference(rows(t), volumes(r))')
    assert "formed:" in out and "= 0 (Exact)" in out, out
    out = _pclaim('difference(count(where(t, eq("group", "a"))), events(r))')
    assert "formed:" in out and "= 1 (Exact)" in out, out
    out = _pclaim('difference(volumes(r), count(where(t, eq("participant_id", "sub-01"))))')
    assert "formed:" in out and "= 2 (Exact)" in out, out
    out = _pclaim('difference(volumes(r), count(where(t, eq("group", "a"), eq("group", "a"))))')
    assert "[S008" in out and "W2" in out and "decided exactly" in out, out
    out = _pclaim('difference(volumes(r), count(where(t, eq("participant_id", "sub-01"), eq("participant_id", "sub-03"))))')
    assert "[S011" in out, out


def test_shape4_without_the_subjects_row_a_form_is_caught(monkeypatch):
    """Mutant: the (3.8b) atoms dropped. The model then has a recording with no row for its subject; its certificate
    (B11 in bids()) is not confirmed on bytes: X001, never a verdict."""
    import inspect
    src = inspect.getsource(D)
    mut = src.replace('        for s in sorted(d for d in self.recs if self.kind[d] == "pt"):   # (3.8b)', '        for s in []:   # (3.8b)')
    assert mut != src
    ns = dict(D.__dict__)
    exec(compile(mut, D.__file__, "exec"), ns)
    monkeypatch.setattr(D.Model, "case_atoms", ns["Model"].case_atoms)
    assert "[X001" in _pclaim('difference(rows(t), volumes(r))')


def test_shape4_outside_stays_s013():
    """recordings() beside a named recording of one dataset (the named one is one of the set's): S013."""
    out = _pclaim('difference(count(recordings(b, "x")), volumes(r))')
    assert "[S013" in out and "recordings() and a named recording of one dataset" in out, out



def _views_model(c):
    """The models (and their rs_firsts calls) deciding claim c on the Phase F dataset."""
    from test_exact_decide import sclaim
    seen = []
    real = D.Model.rs_firsts

    def spy(self, d, t, os, S=None):
        seen.append((self, d, t, os))
        return real(self, d, t, os, S)
    D.Model.rs_firsts = spy
    try:
        sclaim(c)
    finally:
        D.Model.rs_firsts = real
    return seen


def _r1_union(m, d, t, os):
    """R1's branches before 3.9c, per order and per view's branch: (codes, pairs there, pairs none), the infeasible dropped."""
    vs, out = m.rs_views(d, t), set()
    for o in os:
        seqs = [m.rs_seq(d, o, v) for v in vs]
        for js in itertools.product(*[range(len(sq) + 1) for sq in seqs]):
            there = frozenset(sq[j] for sq, j in zip(seqs, js) if j < len(sq))
            none = frozenset(p for sq, j in zip(seqs, js) for p in sq[:j])
            if not there & none:
                out.add((((),) + tuple(D.RSCODE[sq[j][1]] if j < len(sq) else None for sq, j in zip(seqs, js)), there, none))
    return out


OM = [f'difference(sum({{a}}, "trials", "go"), sum({{n}}, "trials", "stop"))',
      f'difference(difference(sum({{n}}, "trials", "stop"), sum({{b}}, "events")), sum({{a}}, "events"))',
      f'difference(sum({{all}}, "volumes"), sum({{a}}, "events"))', f'atmost(sum({{n}}, "trials", "go"), c = 3)']


def _om(c):
    return c.format(**{k: f'recordings(b, "x", where(participants(b), {v}))' for k, v in (("a", 'eq("group", "a")'), ("b", 'eq("group", "b")'), ("n", 'ne("group", "a")'))}, all=RS6)


def test_order_model_keeps_r1s_branches():
    """(3.9c; BB's call on Patsak's behalf 29 Oct 2026 08:58, reversible) the smaller order model: a case keeps, per view,
    its first refusing (region, kind) or none, with the pairs none before it; of those with the same codes only the least
    by inclusion. Every R1 branch combination (an order, a branch per view) lies within a kept one with its codes, each
    kept one is an R1 one with an order that realises it, and there are fewer."""
    for c in OM:
        seen = _views_model(_om(c))
        assert seen, c
        for m, d, t, os in seen:
            r1, kept = _r1_union(m, d, t, os), m.rs_firsts(d, t, os)
            seqs = {}
            assert kept
            for o, ch, pi in kept:
                js = dict(ch)
                there = frozenset(m.rs_seq(d, o, v)[j] for v, j in js.items() if j < len(m.rs_seq(d, o, v)))
                none = frozenset(p for v, j in js.items() for p in m.rs_seq(d, o, v)[:j])
                codes = (pi,) + tuple(D.RSCODE[m.rs_seq(d, o, v)[j][1]] if j < len(m.rs_seq(d, o, v)) else None for v, j in sorted(js.items(), key=repr))
                seqs.setdefault(codes, []).append((there, none))
                assert (codes, there, none) in r1, (c, codes)
            for codes, there, none in r1:
                assert any(a <= there and b <= none for a, b in seqs.get(codes, ())), (c, codes, there, none)
            # (H06) w2_nopt's model of the statement without the filter has one unfiltered view: fewer is not claimed there
            assert len(kept) < len(os) * max(1, len(m.rs_views(d, t))) or len(os) == 1 or m.rs_views(d, t) == [((0,), None)], (c, len(kept), len(os))


def test_order_model_without_the_nones_is_caught(monkeypatch):
    """Mutants of 3.9c: a choice that keeps no pairs none before it, or one case per codes: the first claims orders no
    dataset has, the second drops R1 branches; test_order_model_keeps_r1s_branches fails on each."""
    import inspect
    src = inspect.getsource(D)
    for a, b in [("                    none |= set(sq[:j])\n", ""), ("                if any(a <= there and b <= none for a, b, _, _ in ks):", "                if ks:")]:
        mut = src.replace(a, b)
        assert mut != src
        ns = dict(D.__dict__)
        exec(compile(mut, D.__file__, "exec"), ns)
        monkeypatch.setattr(D.Model, "rs_firsts", ns["Model"].rs_firsts)
        try:
            test_order_model_keeps_r1s_branches()
        except AssertionError:
            continue
        raise AssertionError(f"mutant not caught: {a!r}")


def _tclaim(c, rows=(("01", "a"), ("02", "b"), ("03", "a")), recs=(("01", "x", "go"), ("02", "x", "nocol"), ("02", "y", "go"), ("03", "y", "go"))):
    """c on a dataset whose participants.tsv (participant_id, group) has these rows and with sub-L task-T recordings (TR 2 s,
    one volume) whose events file has one "go" row ("go"), one row without trial_type ("nocol") or is missing (None)."""
    import hashlib
    from fractions import Fraction
    from reality4 import kernel as K, readers as R
    files = {"dataset_description.json": b'{"Name": "g", "BIDSVersion": "1.0.1"}', "README": b"g\n",
             "participants.tsv": ("participant_id\tgroup\n" + "".join(f"sub-{L}\t{g}\n" for L, g in rows)).encode()}
    for L, t, ev in recs:
        stem = f"sub-{L}/func/sub-{L}_task-{t}"
        files[stem + "_bold.nii"] = W._nii((1, 1, 1, 1), Fraction(2))
        files[stem + "_bold.json"] = ('{"TaskName": "%s", "RepetitionTime": 2}' % t).encode()
        if ev:
            files[stem + "_events.tsv"] = {"go": b"onset\tduration\ttrial_type\n0\t1\tgo\n", "nocol": b"onset\tduration\n0\t1\n"}[ev]
    for L, _ in rows:
        if L not in {r[0] for r in recs}:
            files[f"sub-{L}/anat/sub-{L}_T1w.nii"] = W._nii((1, 1, 1), 1)
    blobs = {hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (R.MANIFEST_MAGIC + "\n" + "".join(f"{hashlib.sha256(files[p]).hexdigest()}\t{len(files[p])}\t{p}\n" for p in sorted(files))).encode()
    blobs[hashlib.sha256(man).hexdigest()] = man
    st = W.MemStore(blobs)
    st.begin_program()
    prog = f'dataset d = sha256:{hashlib.sha256(man).hexdigest()}\nlet b = bids(d)\nclaim {c}\n'
    return [ln for ln in K._check(prog.encode(), st)[1] if ln.startswith("line")][0]


XA, YN = 'recordings(b, "x", where(participants(b), eq("group", "a")))', 'recordings(b, "y", where(participants(b), ne("group", "a")))'


def test_shape8_trials_of_two_tasks_over_groups_are_decided():
    """(3.9d; BB's call on Patsak's behalf 29 Oct 2026 09:09, reversible) trials of two tasks over participant groups: one
    partition for both tasks; a region with one participant row sorts its recordings at that row's label in both tasks,
    one with two or more can give each task its own; so the two tasks' orders agree on the one-row regions only. The
    values form with the kernel's; the dataset's other refusals as the kernel gives them."""
    out = _tclaim(f'difference(sum({XA}, "trials", "go"), sum({YN}, "trials", "go"))')
    assert "formed:" in out and "= 0 (Exact)" in out, out
    out = _tclaim(f'atleast(difference(sum({XA}, "trials", "go"), sum({YN}, "trials", "go")), c = -1)')
    assert "formed:" in out and "holds" in out, out
    out = _tclaim(f'sum(recordings(b, "x", where(participants(b), ne("group", "a"))), "trials", "go")')
    assert "[V002" in out, out
    out = _tclaim(f'atleast(sum({XA}, "trials", "go"), c = 0)')
    assert "[S008" in out and "W1" in out and "decided exactly" in out, out
    out = _tclaim(f'difference(sum({XA}, "volumes"), sum(recordings(b, "y"), "volumes"))')   # two tasks, two partitions (not 3.9d)
    assert "formed:" in out and "= -1 (Exact)" in out, out


def _disagreeing_first(monkeypatch, rs_cases, rs_dataset):
    """Model.rs_cases with the cases whose two tasks order their common regions differently first (the same cases)."""
    def cases(self, d):
        def dis(c):
            ts = sorted(c)
            o1, o2 = [r for r, _ in c[ts[0]][0]], [r for r, _ in c[ts[1]][0]]
            return [r for r in o1 if r in o2] == [r for r in o2 if r in o1]
        return iter(sorted(rs_cases(self, d), key=dis) if d in self.rs8 else rs_cases(self, d))
    monkeypatch.setattr(D.Model, "rs_cases", cases)
    monkeypatch.setattr(D.Model, "rs_dataset", rs_dataset)


def test_shape8_certificates_whatever_the_case_order(monkeypatch):
    """(3.9d) every kept pair of cases has a certificate: tried first, the pairs whose orders differ (on two-or-more-row
    regions only) still give the verdict, not X001. Mutants: both tasks' recordings at a region's first row whatever
    its flag, or pairs kept whatever their one-row regions' order: X001 (the label orders do not merge). The default
    case order reaches agreeing pairs first, so ground truth alone does not catch these."""
    import inspect
    rows = (("01", "a"), ("02", "b"), ("03", "a"), ("04", "b"))
    recs = tuple((L, t, "go") for L, _ in rows for t in "xy")
    c = 'atleast(difference(sum(recordings(b, "x", participants(b)), "trials", "go"), sum(recordings(b, "y", where(participants(b), eq("group", "a"))), "trials", "go")), c = 0)'
    base = _tclaim(c, rows=rows, recs=recs)
    assert "[S008" in base, base
    _disagreeing_first(monkeypatch, D.Model.rs_cases, D.Model.rs_dataset)
    assert _tclaim(c, rows=rows, recs=recs) == base
    from reality4 import build as B   # (BLD) the certificate inputs' bytes: rs_dataset lives there
    for mod, a, b in [(B, "rows[0 if c[t][3][r] == 1 or len(rows) < 2 else ti]", "rows[0]"), (D, " if p1 == p2 else ():", ":")]:
        src = inspect.getsource(mod)
        mut = src.replace(a, b)
        assert mut != src, a
        ns = dict(mod.__dict__)
        exec(compile(mut, mod.__file__, "exec"), ns)
        monkeypatch.undo()
        _disagreeing_first(monkeypatch, ns["Model"].rs_cases if mod is D else D.Model.rs_cases, ns["rs_dataset"] if mod is B else D.Model.rs_dataset)
        out = _tclaim(c, rows=rows, recs=recs)
        assert "[X001" in out, (a, out)


def test_shape8_outside_stays_s013():
    """trials of two tasks over groups beside another quantity, or with participant_id read: S013 with the stated reason."""
    out = _tclaim(f'difference(sum({XA}, "trials", "go"), sum({YN}, "trials", "stop"))')
    assert "[S013" in out and "over participant groups" in out, out
    out = _tclaim(f'difference(sum(recordings(b, "x", where(participants(b), eq("participant_id", "sub-01"))), "trials", "go"), sum({YN}, "trials", "go"))')
    assert "[S013" in out, out


RX7, RA7 = 'recordings(b, "x")', 'recordings(b, "x", where(participants(b), eq("group", "a")))'


def test_shape7_a_sum_beside_a_max_or_min_is_decided():
    """(3.9e; BB's call on Patsak's behalf 29 Oct 2026 09:26, reversible) a sum beside a max or a min of one task's
    recordings, the count read nowhere else: per answering region y >= m (max of volumes); max 0 and sum 0, or max >= 1
    and sum >= max (events, trials); one recording (sum = min) or two or more (sum >= 2 min) (min of events, trials)."""
    out = _sclaim(f'difference(sum({RX7}, "volumes"), max({RA7}, "volumes"))')
    assert "formed:" in out and "(Exact)" in out, out
    out = _sclaim(f'atleast(difference(sum({RX7}, "volumes"), max({RA7}, "volumes")), c = 0)')
    assert "[S008" in out and "W1" in out and "decided exactly" in out, out
    out = _sclaim(f'atleast(difference(sum({RX7}, "trials", "go"), min({RX7}, "trials", "go")), c = 0)')
    assert "[S008" in out and "W1" in out, out
    out = _sclaim(f'atleast(difference(difference(sum({RX7}, "events"), min({RX7}, "events")), min({RX7}, "events")), c = 0)')
    assert "formed:" in out, out
    out = _sclaim(f'difference(sum({RX7}, "events"), max({RX7}, "events"))')
    assert "formed:" in out and "= 6 (Exact)" in out, out


def test_shape7_without_the_split_a_verdict_changes(monkeypatch):
    """Mutants: the sum's coupling dropped (a sum below the max: a wrong form, X001), or only 'two or more' for a min (the
    one-recording inputs lost: a wrong S008 W1)."""
    import inspect
    src = inspect.getsource(D)
    for a, b, c, want in [
            ("                            out += [ge(lin((1, Y), (-1, M)))]\n", "                            out += []\n",
             f'atleast(difference(sum({RX7}, "volumes"), max({RX7}, "volumes")), c = 0)', "[X001"),
            ("        return list(itertools.product(*[(0, 1) if x == \"p\" else (0,) for x in st]))",
             "        return list(itertools.product(*[(1,) if x == \"p\" else (0,) for x in st]))",
             f'atleast(difference(difference(sum({RX7}, "events"), min({RX7}, "events")), min({RX7}, "events")), c = 0)', "W1")]:
        mut = src.replace(a, b)
        assert mut != src, a
        ns = dict(D.__dict__)
        exec(compile(mut, D.__file__, "exec"), ns)
        monkeypatch.setattr(D.Model, "case_atoms", ns["Model"].case_atoms)
        monkeypatch.setattr(D.Model, "rs_sp", ns["Model"].rs_sp)
        assert want in _sclaim(c), (a, _sclaim(c))
        monkeypatch.undo()


def test_shape7_outside_stays_s013():
    """A min of volumes beside a sum (y in N m .. m + (N - 1) MAX_DIM leaves gaps), a sum beside a max of tr, a mean
    beside another set: S013 with their reasons."""
    out = _sclaim(f'difference(sum({RX7}, "volumes"), min({RA7}, "volumes"))')
    assert "[S013" in out and "a min of volumes" in out, out
    out = _sclaim(f'difference(sum({RX7}, "tr"), max({RA7}, "tr"))')
    assert "[S013" in out and "or of tr" in out, out
    out = _sclaim(f'difference(mean({RX7}, "volumes"), sum({RA7}, "volumes"))')
    assert "[S013" in out, out
