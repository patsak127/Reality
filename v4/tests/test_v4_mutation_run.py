"""Phase G: tests for the survivors of the mutation run of v4 itself (tools/mutation/REPORT.md).
Each names the v4 module and line (at 03c5c2f) of the survivor it kills."""
import pytest

from helpers import run, tsv
from reality4 import keys, sorts
from reality4.readers import Refusal


# ---- keys.py ------------------------------------------------------------------------------------

@pytest.mark.parametrize("s,bad", [
    ("a\u00a0b", "\u00a0"),     # 85 != -> ==: a no-break space inside is invisible; U+0020 inside is not
    ("a b", None),
    ("a\u200bb", "\u200b"),     # 85 or -> and: a format character
    ("a\x01b", "\x01"),
    (" ab", " "),               # 87 1 -> 0: a space at the start
    ("ab ", " "),
])
def test_invisible(s, bad):
    assert keys.invisible(s) == bad


@pytest.mark.parametrize("s,ok", [("a_b", True), ("ab", True), ("a-b", False), ("é", False), ("", False)])
def test_header_names_addressable_by_name(s, ok):   # 69 and -> or
    assert keys.is_header_name(s) is ok


# ---- sorts.py -----------------------------------------------------------------------------------

def test_sort_depth_bound_edge():                   # 43, 56, 58
    s = sorts.S("x")
    for _ in range(399):
        s = sorts.S("[", s, "]")
    assert s.depth == 400
    with pytest.raises(Refusal) as e:
        sorts.S("[", s, "]")
    assert e.value.code == "R006"


def test_sort_size_bound_edge():                    # 56 > -> >=
    assert sorts.S(*[sorts.File("a" * 64)] * 99_999).size == 100_000
    with pytest.raises(Refusal) as e:
        sorts.S(*[sorts.File("a" * 64)] * 100_000)
    assert e.value.code == "R006"


def test_sort_equality():                           # 20, 33, 62 (uncovered)
    f, g = sorts.File("a" * 64), sorts.File("b" * 64)
    assert f == sorts.File("a" * 64) and f != g and f != sorts.Lit(b"a")
    assert sorts.Lit(b"x") == sorts.Lit(b"x") and sorts.Lit(b"x") != sorts.Lit(b"y")
    assert sorts.S("A[", f, "]") == sorts.S("A[", f, "]") and sorts.S("A[", f, "]") != sorts.S("A[", g, "]")


def test_del_and_tilde_print(tmp_path):             # 77 < -> <=
    assert sorts.esc(b"~\x7f") == '"~\\x7f"'
    p, h = tsv(tmp_path, "t.tsv", b"x\ty\n\x7f\tb\n")
    ok, text = run(f"file f = sha256:{h}\nclaim cell(tsv(f), 1, 1)\n", [p])
    assert ok and text.split("\n")[0].endswith('= "\\x7f"'), text


# ---- syntax.py ----------------------------------------------------------------------------------

def test_line_token_bound_edge():                   # 175 > -> >=
    from reality4 import syntax
    line = "claim g(" + ", ".join(["1"] * 4998) + ") 1"   # claim g ( 4998 numbers, 4997 commas ) 1 = 10000
    assert len(syntax._tokens(line, 1)) == 10_000
    with pytest.raises(syntax.SyntaxRefusal) as e:
        syntax._tokens(line + " 1", 1)
    assert e.value.code == "R001"


# ---- readers.py ---------------------------------------------------------------------------------

import gzip  # noqa: E402
import os  # noqa: E402
import zlib  # noqa: E402

import bidsfix  # noqa: E402
from reality4 import readers as R  # noqa: E402


def _store(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data)
    st = R.Store([str(p)], [])
    return st, R.sha256_file(str(p))[0]


def test_steps_bound_edge_and_default(monkeypatch):     # 46, 48
    monkeypatch.setattr(R, "MAX_STEPS", 10)
    s = R.Steps()
    s.add()
    assert s.n == 1
    s.add(9)
    with pytest.raises(Refusal) as e:
        s.add()
    assert e.value.code == "R002"


def test_text_bounds_at_their_edges(tmp_path, monkeypatch):   # 122, 188, 234
    st, h = _store(tmp_path, "t.tsv", b"x" * 100)
    monkeypatch.setattr(R, "MAX_TEXT_FILE", 100)
    monkeypatch.setattr(R, "MAX_TEXT_TOTAL", 100)
    st.begin()
    assert st.text(h) == b"x" * 100 and st.text_total == 100
    with pytest.raises(Refusal) as e:
        st.text(h)                      # a second whole read in the same statement: 200 > 100
    assert e.value.code == "R003"
    monkeypatch.setattr(R, "MAX_TEXT_FILE", 99)
    st.begin()
    with pytest.raises(Refusal) as e:
        st.text(h)
    assert e.value.code == "R003" and "100 bytes" in str(e.value)


def test_measured_charges_its_inner_reads_once(tmp_path, monkeypatch):   # 197, 206, 212
    st, h = _store(tmp_path, "t.tsv", b"x" * 100)
    monkeypatch.setattr(R, "MAX_TEXT_TOTAL", 100)
    st.begin_program()
    st.begin()
    st._manifests["m"] = frozenset({"a", "b"})
    assert st.measured(("bids", "m"), lambda: len(st.text(h))) == 100
    assert st.text_total == 100 and st.prog_bytes == 1024 * 3 + 164   # the gate, and the text it read (len + 64)
    st.begin()
    monkeypatch.setattr(R, "MAX_TEXT_TOTAL", 99)
    with pytest.raises(Refusal) as e:
        st.measured(("bids", "m"), lambda: 0)
    assert e.value.code == "R003"


def test_accounted_bytes_edge(tmp_path, monkeypatch):    # 167, 171
    st, _ = _store(tmp_path, "t.tsv", b"x")
    monkeypatch.setattr(R, "MAX_ACCOUNTED", 100)
    st.begin_program()
    st.account(100)
    with pytest.raises(Refusal) as e:
        st.account(1)
    assert e.value.code == "R012"


def test_step_costs_of_the_readers(tmp_path):           # 222, 243, 247, 253, 271, 352, 399
    data = b'{"a": [' + b"1, " * 60 + b'1]}'             # 190 bytes: 3 steps per 64
    st, h = _store(tmp_path, "j.json", data)
    st.begin()
    st.slice(h, 0, 130)
    assert st.steps.n == 3
    st.begin()
    st.text(h)
    assert (st.steps.n, st.text_total) == (3, 190)
    st.begin()
    st.json(h)
    assert (st.steps.n, st.text_total) == (6, 190)
    st.begin()
    st.json_file(h)
    assert (st.steps.n, st.text_total) == (6, 190)
    img = bidsfix.nifti1((2, 2, 2, 5))
    st, h = _store(tmp_path, "i.nii", img + b"\x00" * 9000)
    st.begin()
    st.nifti(h, "i.nii", False)
    assert st.steps.n == 1
    st.begin()
    st.nifti(h, "i.nii", True)
    assert st.steps.n == (len(img) + 9000) // 4096 + 1
    s = R.Steps()
    R.parse_tsv(b"a\tb\n" + b"1\t2\n" * 40, "h", s)
    assert s.n == 164 // 64 + 1
    s = R.Steps()
    R.parse_csv(b"a,b\n" + b"1,2\n" * 40, "h", s)
    assert s.n == 164 // 64 + 1


def test_table_bom_default():                          # 281
    assert R.Table("h", ["a"], []).bom is False


@pytest.mark.parametrize("data,rows", [
    (b"a\tb\n\n", []),                                  # 328: one final empty line in a 2-column table
    (b"a\tb\n1\t2\n\n", [["1", "2"]]),
])
def test_final_empty_line_in_a_multi_column_tsv(data, rows):
    assert R.parse_tsv(data, "h", R.Steps()).rows == rows


@pytest.mark.parametrize("data,text", [
    (b"a\tb\n\n1\t2\n", "line 2 is empty: an empty line is a row only if the table has one column"),   # 330, 332
    (b"a\n\n1\n", "line 2 is empty: in a one-column table"),
    (b"a\t\tc\n1\t2\t3\n", "header column 2 has no name"),                                                 # 335
])
def test_table_refusal_messages_name_the_line_and_column(data, text):
    with pytest.raises(Refusal) as e:
        R.parse_tsv(data, "h", R.Steps())
    assert text in str(e.value)


def test_csv_header_refusal_names_line_1():           # 327
    with pytest.raises(Refusal) as e:
        R.parse_csv(b'a,b"c\n1,2\n', "h", R.Steps())
    assert "line 1:" in str(e.value)


@pytest.mark.parametrize("data,rows", [
    (b'x,y\n"a","b"\n', [["a", "b"]]),                 # 374: a quoted field ending the line
    (b"x,y\n,b\n", [["", "b"]]),                        # 379: an empty first field
    (b"x,y\na,\n", [["a", ""]]),
])
def test_csv_field_edges(data, rows):
    assert R.parse_csv(data, "h", R.Steps()).rows == rows


def test_exponent_with_all_ten_digits_is_r007():       # 413
    with pytest.raises(Refusal) as e:
        R.decimal("1e0123456789")
    assert e.value.code == "R007"


def test_escaped_quote_keeps_brackets_inside_the_string():   # 438
    v = R.parse_json(b'["\\"' + b"[" * 70 + b'"]', "j")
    assert v == ['"' + "[" * 70]


def _gz(*parts):
    body = zlib.compressobj(9, zlib.DEFLATED, -15)
    # raw deflate blocks, then the RFC 1952 trailer (CRC-32 and length of what they decompress to), so the file is
    # a whole gzip stream (O8, 27 Oct 2026: nifti(f) refuses I004 on one that is not)
    return (b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff" + b"".join(parts[:-1]) + body.compress(parts[-1]) + body.flush()
            + zlib.crc32(parts[-1]).to_bytes(4, "little") + len(parts[-1]).to_bytes(4, "little"))


def test_gz_header_stops_after_the_header(tmp_path):  # 576 and -> or
    hdr = bidsfix.nifti1((2, 2, 2, 5), tr=2.0)
    p = tmp_path / "big.nii.gz"
    p.write_bytes(gzip.compress(hdr + os.urandom(2 * R.MAX_GZ_HEAD)))
    assert R.nifti_read(str(p), True, "big.nii.gz", False).dim[4] == 5


def test_gz_header_after_a_long_run_of_empty_blocks(tmp_path):   # 582
    hdr = bidsfix.nifti1((2, 2, 2, 5), tr=2.0)
    data = _gz(b"\x00\x00\x00\xff\xff" * 20_000, hdr)       # 100,000 bytes before the header
    st, h = _store(tmp_path, "e.nii.gz", data)
    st.begin()
    assert st.nifti_file(h)[0].dim[4] == 5
    p = tmp_path / "e2.nii.gz"
    p.write_bytes(data)
    assert R.nifti_read(str(p), True, "e2.nii.gz", False).dim[4] == 5


def test_truncated_gz_refuses(tmp_path):               # 579 < -> <=
    p = tmp_path / "t.nii.gz"
    p.write_bytes(gzip.compress(bidsfix.nifti1((2, 2, 2, 5)))[:40])
    with pytest.raises(Refusal) as e:
        R.nifti_read(str(p), True, "t.nii.gz", False)
    assert e.value.code in ("I001", "I004")


@pytest.mark.parametrize("path", ["a\\b", "/a", "a\u00a0b", "a//b", "a/./b"])
def test_manifest_paths_refused(path):                 # 622
    data = (R.MANIFEST_MAGIC + "\n" + "a" * 64 + "\t1\t" + path + "\n").encode()
    with pytest.raises(Refusal) as e:
        R.parse_manifest(data, "m")
    assert e.value.code == "M001"


def test_manifest_entries_bound_edge(monkeypatch):    # 640
    monkeypatch.setattr(R, "MAX_MANIFEST_ENTRIES", 2)
    lines = ["a" * 64 + f"\t1\t{n}" for n in ("x", "y", "z")]
    assert len(R.parse_manifest((R.MANIFEST_MAGIC + "\n" + "\n".join(lines[:2]) + "\n").encode(), "m")) == 2
    with pytest.raises(Refusal) as e:
        R.parse_manifest((R.MANIFEST_MAGIC + "\n" + "\n".join(lines) + "\n").encode(), "m")
    assert e.value.code == "R003"


# ---- bids101.py ---------------------------------------------------------------------------------

import tempfile  # noqa: E402

import helpers  # noqa: E402
from fractions import Fraction  # noqa: E402
from reality4 import bids101  # noqa: E402

N5 = bidsfix.nifti1((2, 2, 2, 5), tr=2.0)


def _bids(tmp_path, body, **kw):
    d = tempfile.mkdtemp(dir=str(tmp_path))
    root = bidsfix.mini(os.path.join(d, "ds"), **kw)
    md = os.path.join(d, "m")
    os.mkdir(md)
    h = helpers.manifest(root, md)
    ok, text = helpers.run(f"dataset d = sha256:{h}\nlet b = bids(d)\n{body}\n", [md], [root])
    return ok, [ln for ln in text.split("\n") if ln.startswith("line ")][0]


@pytest.mark.parametrize("extra,code", [
    ({"sub-01/ses-1/func/sub-01_ses-1_task-x_bold.nii": N5}, "[B14"),     # 123, 126: sessions
    ({"sub-01/sub-01_scans.tsv": "filename\tacq_time\n"}, "[B14"),        # 130, 131: scans files
    ({"sub-01/func/sub-01_task-x_foo.tsv": "a\tb\n"}, "B17 x1"),          # 144: not an events file
    ({"sub-01/fmap/sub-01_phasediff.txt": "x"}, "B17 x1"),                # 151: not a fieldmap file
    ({"sub-01/func/sub-01_task-x_s1-y_bold.nii": N5}, "B17 x1"),          # 70: an entity key with a digit
    ({"participants.tsv": "participant_id\tgroup\nsub-01\ta\nsub-02\ta\nsubx01\ta\n"}, "B11 x1"),   # 612
])
def test_bids_file_kinds_and_labels(tmp_path, extra, code):
    ok, line = _bids(tmp_path, "claim count(participants(b))", extra=extra)
    assert not ok and code in line, line


def test_a_bound_on_an_events_number_keeps_its_code(tmp_path):
    ok, line = _bids(tmp_path, "claim count(participants(b))", events="onset\tduration\n" + "1" * 1001 + "\t1\n")
    assert line.startswith("line 2: refused [R007"), line


@pytest.mark.parametrize("tr,events,ok", [
    (1, "onset\tduration\n7.25\t0.5\n", False),    # 497: TR 1 (5 volumes end at 5 s)
    (2, "onset\tduration\n10\t0.5\n", False),      # 556: an onset exactly at the end
    (2, "onset\tduration\n9.5\t0.5\n", True),
    (2, "onset\tduration\n11\t0.5\n", False),      # 552: the onset, not the duration, is checked
])
def test_onsets_after_the_end_of_the_run(tmp_path, tr, events, ok):
    imgs = {f"sub-0{s}/func/sub-0{s}_task-x_bold.nii": bidsfix.nifti1((2, 2, 2, 5), tr=float(tr)) for s in "12"}
    got, line = _bids(tmp_path, "claim count(participants(b))", events=events, extra=imgs,
                      task_json='{"TaskName": "x", "RepetitionTime": %d}' % tr)
    assert got == ok and (ok or "B30 x2" in line), line


def test_sidecar_in_the_image_folder(tmp_path):     # 245, 251
    side = {f"sub-0{s}/func/sub-0{s}_task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 2}' for s in "12"}
    ok, line = _bids(tmp_path, 'claim tr(recording(b, "01", "x"))', drop=["task-x_bold.json"], extra=side)
    assert ok and line.endswith("is recorded as 2 s (Recorded[s])"), line


def test_tr_consistent_guards():                     # 189
    hd = R.nifti_header(bidsfix.nifti1((2, 2, 2, 5), tr=2.0)[:352], "n")
    assert bids101.tr_consistent(Fraction(2), hd)
    assert not bids101.tr_consistent(Fraction(0), hd)
    assert not bids101.tr_consistent(2.0, hd)
    hd.pixdim[4] = None
    assert not bids101.tr_consistent(Fraction(2), hd)
    hd.pixdim[4] = Fraction(0)
    assert not bids101.tr_consistent(Fraction(2), hd)


def test_bids_read_step_count_is_pinned(tmp_path):   # 225, 319
    d = tempfile.mkdtemp(dir=str(tmp_path))
    root = bidsfix.mini(os.path.join(d, "ds"))
    md = os.path.join(d, "m")
    os.mkdir(md)
    h = helpers.manifest(root, md)
    st = R.Store([md], [root])
    from reality4.kernel import check
    ok, out = check(f"dataset d = sha256:{h}\nclaim count(participants(bids(d)))\n".encode(), st)
    assert ok and st.steps.n == STEPS_BIDS, (out, st.steps.n)


STEPS_BIDS = 2384   # Part B item 2b (28 Oct 2026): 3980 -> 2384, count(participants(bids(d)))'s W1 is decided exactly (its certificates: two datasets) instead of by the search's candidate datasets; O14: +12, 2 events files x 2 run readings x 3 folders of metadata index (was 3968); 285 before the fix pass; R6 charges a manifest one step per byte (its paths are checked character by character), here and in every witness dataset read


@pytest.mark.parametrize("where", ["bids_tsv", "nifti"])
def test_a_bound_inside_a_bids_file_read_keeps_its_code(tmp_path, monkeypatch, where):   # 364, 366, 396
    def bound(*a, **k):
        raise R.Refusal("R003", "bound", "a bound was hit")
    if where == "bids_tsv":
        monkeypatch.setattr(bids101, "bids_tsv", bound)
    else:
        monkeypatch.setattr(R.Store, "nifti", bound)
    ok, line = _bids(tmp_path, "claim count(participants(b))")
    assert line.startswith("line 2: refused [R003"), line


@pytest.mark.parametrize("sed,ok", [('"x"', False), ('"k"', True), ('"j-"', True)])
def test_slice_encoding_direction_is_checked(tmp_path, sed, ok):    # 523, 524 (uncovered before)
    got, line = _bids(tmp_path, "claim count(participants(b))",
                      task_json='{"TaskName": "x", "RepetitionTime": 2, "SliceEncodingDirection": %s}' % sed)
    assert got == ok and (ok or "B10 x2" in line), line


# ---- kernel.py ----------------------------------------------------------------------------------

def _kp(tmp_path, body):
    p, h = tsv(tmp_path, "t.tsv", "x\ty\n3\t5\n7\t2\n")
    j, hj = tsv(tmp_path, "j.json", '{"a": [10, 20, 30]}')
    ok, text = run(f"file f = sha256:{h}\nfile g = sha256:{hj}\nlet t = tsv(f)\nlet j = json(g)\n{body}\n", [p, j])
    return ok, [ln for ln in text.split("\n") if ln.startswith("line ")]


@pytest.mark.parametrize("k,v", [(1, "10"), (2, "20"), (3, "30")])
def test_item_picks_the_kth_item(tmp_path, k, v):         # 321
    ok, lines = _kp(tmp_path, f'claim item(member(j, "a"), {k})')
    assert ok and lines[0].endswith(f"= {v} (Exact)"), lines


@pytest.mark.parametrize("op,ok", [("below", False), ("atleast", True), ("exceeds", False), ("atmost", True)])
def test_comparisons_at_the_cutoff(tmp_path, op, ok):      # 718
    got, lines = _kp(tmp_path, f"claim {op}(number(cell(t, 1, 1)), c = 3)")
    assert got is ok and (ok or "[V001, item 5]" in lines[0]), lines


def test_a_zero_tolerance_is_idle_not_ill_typed(tmp_path):   # 144
    ok, lines = _kp(tmp_path, "claim widen(number(cell(t, 1, 1)), tolerance = 0)")
    assert "[S008, item 1]" in lines[0], lines
    ok, lines = _kp(tmp_path, "claim widen(number(cell(t, 1, 1)), tolerance = -1)")
    assert "[S004, item 1]" in lines[0], lines


def test_a_widened_value_has_its_own_identity(tmp_path):    # 166, 167
    ok, lines = _kp(tmp_path, "claim widen(number(cell(t, 1, 1)), tolerance = 1)\nclaim widen(number(cell(t, 1, 1)), tolerance = 1)")
    assert ok, lines
    ok, lines = _kp(tmp_path, "claim widen(number(cell(t, 1, 1)), tolerance = 1)\nclaim widen(number(cell(t, 1, 1)), tolerance = 2)")
    assert not ok and all("[S012, item 6]" in ln for ln in lines), lines
    # O9 (27 Oct 2026): widen(w, 1) is the cell widened by 2, so beside w (by 1) it is one value at two tolerances
    ok, lines = _kp(tmp_path, "let w = widen(number(cell(t, 1, 1)), tolerance = 1)\nclaim widen(w, tolerance = 1)\nclaim w")
    assert not ok and all("[S012, item 6]" in ln for ln in lines[:2]), lines
    ok, lines = _kp(tmp_path, "let w = widen(number(cell(t, 1, 1)), tolerance = 1)\nclaim widen(w, tolerance = 1)\nclaim widen(number(cell(t, 1, 1)), tolerance = 2)")
    assert ok, lines


def test_difference_of_a_widened_value(tmp_path):           # 686, 687, 707
    ok, lines = _kp(tmp_path, "claim difference(widen(number(cell(t, 1, 1)), tolerance = 1), number(cell(t, 2, 2)))")
    assert ok and lines[0].endswith("lies within [0, 2] (Interval)"), lines
    ok, lines = _kp(tmp_path, "claim difference(widen(number(cell(t, 1, 1)), tolerance = 1), widen(number(cell(t, 2, 1)), tolerance = 2))")
    assert ok and lines[0].endswith("lies within [-7, -1] (Interval)"), lines


def test_numbers_in_two_json_files_are_two_values(tmp_path):      # 311, 321 (jm[1], the file)
    j1, h1 = tsv(tmp_path, "a.json", '{"a": [1], "b": 1}')
    j2, h2 = tsv(tmp_path, "b.json", '{"a": [2], "b": 2}')
    head = f"file g1 = sha256:{h1}\nfile g2 = sha256:{h2}\n"
    for v in ('member(json(g{}), "b")', 'item(member(json(g{}), "a"), 1)'):
        ok, text = run(head + f"claim widen({v.format(1)}, tolerance = 1)\nclaim widen({v.format(2)}, tolerance = 2)\n", [j1, j2])
        assert ok, text


def test_a_widened_value_is_identified_by_what_it_widens(tmp_path):   # 167
    ok, lines = _kp(tmp_path, "claim widen(widen(number(cell(t, 1, 1)), tolerance = 1), tolerance = 1)\n"
                              "claim widen(widen(number(cell(t, 2, 2)), tolerance = 1), tolerance = 2)")
    assert ok, lines


@pytest.mark.parametrize("which,steps,mem", [
    ("tsv", 22, 818), ("csv", 22, 818), ("member", 51, 1883), ("where", 77, 954), ("volumes", 2165, 17721)])   # volumes 9460 -> 2165 at Part B item 2c (28 Oct 2026): volumes()'s W1 is decided exactly (two certificate datasets of 5 files) instead of by the search's candidate datasets; 718 -> 9460 at the merge of v4-fixes: fix pass R6 (a manifest is charged one step per byte, +8,658) and O14 (+84)   # 22/22/77 in exact-decision phase 4 (the relaxation, SPEC-EXACT 4.2); member 51 in phase 5 (part H decided exactly)   # tsv/csv 23, where 80 since the phase 3 checkpoint (W1 of a count solves its systems, SPEC-EXACT 5.1)   # where: 954 since 04 (72 bytes per kept row); tsv/csv/where steps since exact-decision phase 3: part T is decided exactly, its charge is the probes, types, solver calls and certificates (SPEC-EXACT 8)
def test_kernel_charges_are_pinned(tmp_path, which, steps, mem):   # 258, 263, 302, 516, 748, 818, 1101
    from reality4.kernel import check
    p, h = tsv(tmp_path, "t.tsv", "x\ty\n3\t5\n7\t2\n")
    c, hc = tsv(tmp_path, "t.csv", "x,y\n3,5\n7,2\n")
    j, hj = tsv(tmp_path, "j.json", '{"a": [10, 20, 30], "b": 4}')
    root = bidsfix.mini(os.path.join(str(tmp_path), "ds"))
    md = os.path.join(str(tmp_path), "m")
    os.mkdir(md)
    hm = helpers.manifest(root, md)
    prog, files = {
        "tsv": (f"file f = sha256:{h}\nclaim count(tsv(f))\n", [p]),
        "csv": (f"file f = sha256:{hc}\nclaim count(csv(f))\n", [c]),
        "member": (f'file g = sha256:{hj}\nclaim member(json(g), "b")\n', [j]),
        "where": (f'file f = sha256:{h}\nclaim count(where(tsv(f), eq(1, "3")))\n', [p]),
        "volumes": (f'dataset d = sha256:{hm}\nclaim volumes(recording(bids(d), "01", "x"))\n', [md]),
    }[which]
    st = R.Store(files, [root])
    ok, out = check(prog.encode(), st)
    assert ok and (st.steps.n, st.prog_bytes) == (steps, mem), out


@pytest.mark.parametrize("slack,ok", [(0, True), (-1, False)])
def test_output_bounds_at_their_edges(tmp_path, monkeypatch, slack, ok):   # 1144, 1145, 1150, 1151, 1184-1188
    from reality4 import kernel
    p, h = tsv(tmp_path, "t.tsv", "x\ty\n3\t5\n7\t2\n")
    prog = f"claim count(nope)\nfile f = sha256:{h}\nclaim count(tsv(f))\n"
    _, text = run(prog, [p])
    lines = text.split("\n")
    refusal = len(lines[0]) + 1
    formed = sum(len(t) + 1 for t in lines[1:3])
    monkeypatch.setattr(kernel, "MAX_LINE_OUTPUT", formed + slack)
    got, text = run(prog, [p])
    assert ("line 3: formed" in text) is ok and (ok or "[R014" in text), text
    monkeypatch.setattr(kernel, "MAX_LINE_OUTPUT", 1 << 20)
    monkeypatch.setattr(kernel, "MAX_PROGRAM_OUTPUT", refusal + formed + slack)
    got, text = run(prog, [p])
    assert ("line 3: formed" in text) is ok and (ok or "[R011" in text), text


def test_print_bound_at_its_edge():          # 65 (no input reaches it under R007; fmt is checked directly)
    from reality4.kernel import fmt
    assert len(fmt(Fraction(10 ** 3000 - 1))) == 3000
    assert fmt(Fraction(1, 2 * 10 ** 2999)).startswith("0.")
    for q in (Fraction(10 ** 3000), Fraction(-10 ** 3000), Fraction(1, 10 ** 3000)):
        with pytest.raises(Refusal) as e:
            fmt(q)
        assert e.value.code == "R009"


def test_a_non_ascii_header_name_is_k001(tmp_path):    # 384
    p, h = tsv(tmp_path, "t.tsv", "x\ty\n3\t5\n")
    ok, text = run(f'file f = sha256:{h}\nclaim cell(tsv(f), 1, "x\\xe9")\n', [p])
    assert "line 2: refused [K001, item 1]" in text, text


# ---- machine.py ---------------------------------------------------------------------------------

import io  # noqa: E402

from reality4 import machine  # noqa: E402


@pytest.mark.parametrize("raw,want", [(b"max\n", None), (b"4096\n", 4096)])
def test_cgroup_memory_max(monkeypatch, raw, want):        # 20
    def fake_open(path, mode="r"):
        return io.BytesIO(b"0::/x\n" if path == "/proc/self/cgroup" else raw)
    monkeypatch.setattr(machine, "open", fake_open, raising=False)
    assert machine._cgroup_max() == want


def test_physical_memory_unreadable_off_windows(monkeypatch):   # 31
    def bad(name):
        raise ValueError(name)
    monkeypatch.setattr(machine.os, "sysconf", bad, raising=False)   # Windows' os has no sysconf
    monkeypatch.setattr(machine.sys, "platform", "linux")
    assert machine._physical() is None


@pytest.mark.parametrize("lim,ok", [(machine.FLOOR, True), (machine.FLOOR - 1, False), (None, False)])
def test_memory_floor_edge(monkeypatch, lim, ok):           # 69
    monkeypatch.setattr(machine, "memory_limit", lambda: lim)
    assert (machine.below_floor() is None) is ok


# ---- witness.py: the pure helpers of the candidate search ---------------------------------------

from reality4 import witness as W  # noqa: E402
from reality4.syntax import parse_line  # noqa: E402


def _expr(src):
    return parse_line("claim " + src, 1).expr


@pytest.mark.parametrize("q,t", [(Fraction(0), "0"), (Fraction(5), "5"), (Fraction(-5, 2), "-2.5"),
                                 (Fraction(1, 8), "0.125"), (Fraction(-3, 100), "-0.03"), (Fraction(1, 3), None)])
def test_dec_text(q, t):                         # 140, 149, 150, 152
    assert W.dec_text(q) == t


def test_slot_and_dataset_of_an_expression():    # 99, 101, 103
    assert W.slot_of(_expr('count(where(tsv(f), eq(1, "a")))')) == "f"
    assert W.slot_of(_expr("count(csv(f))").args[0]) == "f"
    assert W.slot_of(_expr("count(participants(bids(d)))").args[0]) == "P:d"
    assert W.slot_of(_expr("count(tsv(cell(t, 1, 1)))").args[0]) is None
    assert W.slot_of(_expr("count(participants(x))").args[0]) is None
    assert W.slot_of(_expr("number(cell(tsv(f), 1, 1))")) is None    # number() is not a table function
    assert W.ds_of(_expr('volumes(recording(bids(d), "01", "x"))').args[0]) == "d"


def test_recording_entities_as_the_kernel_reads_them():      # 122, 125
    c = _expr('volumes(recording(bids(d), "01", "x", "2", acq("hi"), rec("lo")))').args[0]
    assert W.rec_ents(c) == {"sub": "01", "task": "x", "run": "2", "acq": "hi", "rec": "lo"}
    c = _expr('volumes(recording(bids(d), "01", "x", acq(1)))').args[0]
    assert W.rec_ents(c) == {"sub": "01", "task": "x"}


def test_nii_header_fields():                     # 523, 525, 532
    hd = R.nifti_header(W._nii((1, 1, 1, 4), Fraction(3, 2), 16)[:352], "n")
    assert hd.dim[:5] == [4, 1, 1, 1, 4] and list(hd.dim[5:8]) == [1, 1, 1]
    assert [hd.pixdim[i] for i in range(1, 5)] == [1, 1, 1, Fraction(3, 2)]
    assert len(W._nii((2, 1, 1), 1)) == 354 and len(W._nii((2, 1, 1), 1, data=False)) == 352


# ---- witness.py: W2 key parts and the witness budget --------------------------------------------

def _wt(tmp_path, body):
    p, h = tsv(tmp_path, "w.tsv", "x\ty\tz\na\t5\tq\nb\t2\tr\n")
    ok, text = run(f"file f = sha256:{h}\nlet t = tsv(f)\n{body}\n", [p])
    return ok, [ln for ln in text.split("\n") if ln.startswith("line 3")][0]


def test_an_idle_key_part_refuses_w2(tmp_path):     # 714, 715, 716
    ok, line = _wt(tmp_path, 'claim cell(t, key("x", "a", "x", "a"), "y")')
    assert "[S008, item 1]: cell(): on no readable input does the key part on column 1 change the answer (decided exactly" in line, line
    ok, line = _wt(tmp_path, 'claim cell(t, key("x", "a", "z", "q", "z", "q"), "y")')
    assert "[S008, item 1]: cell(): on no readable input does the key part on column 3 change the answer (decided exactly" in line, line
    ok, line = _wt(tmp_path, 'claim number(cell(t, key("x", "a", "z", "q"), "y"))')
    assert ok, line


def _least_budget(tmp_path, monkeypatch, body):
    lo, hi = 1, 10_000_000
    while lo < hi:
        mid = (lo + hi) // 2
        monkeypatch.setattr(W, "MAX_WITNESS_STEPS", mid)
        if _wt(tmp_path, body)[0]:
            hi = mid
        else:
            lo = mid + 1
    return lo


@pytest.mark.parametrize("body,m", [("claim count(t)", 16), ('claim count(where(t, eq("x", "a")))', 65)])   # 11 and 33 since exact-decision phase 3 (part T decided exactly: probes, types, solver calls, certificates; SPEC-EXACT 8); 17 and 68 since its checkpoint (W1 of a count solves its systems, SPEC-EXACT 5.1); 16 and 65 in phase 4 (the relaxation, SPEC-EXACT 4.2)
def test_witness_budget_at_its_edge(tmp_path, monkeypatch, body, m):   # 777, 800 (m pinned: the least budget that forms)
    assert _least_budget(tmp_path, monkeypatch, body) == m
    monkeypatch.setattr(W, "MAX_WITNESS_STEPS", m)
    assert _wt(tmp_path, body)[0]
    monkeypatch.setattr(W, "MAX_WITNESS_STEPS", m - 1)
    ok, line = _wt(tmp_path, body)
    assert not ok and "[R013, bounds]" in line, line


def test_bytes_charge_in_the_witness_is_pinned(tmp_path):   # witness 53
    from reality4.kernel import check
    p, h = tsv(tmp_path, "b.bin", b"\x01\x02\x03")
    st = R.Store([p], [])
    ok, out = check(f"file f = sha256:{h}\nclaim bytes(f, 0, 2)\n".encode(), st)
    assert ok and st.steps.n == 16, (out, st.steps.n)   # 14 by the search; 11 since exact-decision phase 5 (part H decided exactly); 16 since Part B item 7 (the off_t bound atom: the integer step counts 2 atoms, +5)
