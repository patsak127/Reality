"""Phase G: the tests the mutation run of v3 proposed (DESIGN 4 "Tests", mutation-v3/RESULTS-*.md).

Each test names the v3 survivor it kills (module and line in v3 6b6f88f) and pins v4's verdict.
The __main__ survivors (exit codes, usage, the manifest command) are in test_v4_cli.py. Two tests
here found v4 bugs, fixed in the same commit (LOG, Phase G, 25 Oct): duration() refused S008 on
every events file and count of events refused S011, because the witness gave the events onset
column non-decimal candidates; and a cutoff of 1 s or less had no candidate between 0 and it for
values 1.0.1 requires to be positive (a duration, a RepetitionTime)."""
import os
import struct
import tempfile

import pytest

import bidsfix
import helpers
from helpers import HERE, run, sha, tsv
from reality4 import readers as R
from reality4.kernel import check

MUT = os.path.join(HERE, "data", "mutation")


def one(tmp_path, prog, tables):
    """Run prog with `file <name> = <hash>` lines for the tables {name: text}; return (ok, first line)."""
    files, head = [], ""
    for i, (name, text) in enumerate(tables.items()):
        p, h = tsv(tmp_path, f"{i}.tsv", text)
        files.append(p)
        head += f"file {name} = sha256:{h}\n"
    ok, text = run(head + prog + "\n", files)
    return ok, [ln for ln in text.split("\n") if ln.startswith("line ")][0]


T = {"f": "a\tb\n0.2\t22\n1/5\t3\n"}
K = {"k": "id\tv\nab\t1\ncd\t2\n"}


# ---- kernel.py survivors ------------------------------------------------------------------------

@pytest.mark.parametrize("prog,out", [
    ("claim number(cell(tsv(f), 1, 1))", "= 0.2 (Exact)"),                          # 62 k5
    ("claim atleast(count(tsv(f)), c = 1/5)", "c = 0.2] holds"),                     # 62 k5, a cutoff
    ("claim atleast(count(tsv(f)), c = 1/25)", "c = 0.04] holds"),
    ("claim atleast(count(tsv(f)), c = 4/5)", "c = 0.8] holds"),
    ("claim atleast(count(tsv(f)), c = 3/40)", "c = 0.075] holds"),
])
def test_fmt_of_five_heavy_denominators(tmp_path, prog, out):
    ok, line = one(tmp_path, prog, T)
    assert ok and line.endswith(out), line


def test_r009_decimal_places_edge(tmp_path):                                         # 66
    ok, line = one(tmp_path, f"claim atleast(count(tsv(f)), c = 1/{2 ** 3000})", T)
    assert ok, line
    ok, line = one(tmp_path, f"claim atleast(count(tsv(f)), c = 1/{2 ** 3001})", T)
    assert not ok and "[R009" in line, line


@pytest.mark.parametrize("prog,code", [
    ("claim exceeds(widen(number(cell(tsv(f), 1, 2)), tolerance = 2), c = 20)", "V006"),   # 533 exceeds
    ("claim below(widen(number(cell(tsv(f), 1, 2)), tolerance = 2), c = 24)", "V006"),     # 533 below
    ("claim exceeds(widen(number(cell(tsv(f), 1, 2)), tolerance = 2), c = 19)", None),
    ("claim below(widen(number(cell(tsv(f), 1, 2)), tolerance = 2), c = 25)", None),
])
def test_interval_touching_the_cutoff_refuses_v006(tmp_path, prog, code):
    ok, line = one(tmp_path, prog, T)
    assert (ok, line) and (ok if code is None else (not ok and f"[{code}" in line)), line


@pytest.mark.parametrize("prog,expect", [
    ("claim bytes(b, 1, 2)", 'Bytes[#1, 1..3] = "12"'),                              # 252 printed range
    ("claim bytes(b, 0, 8)", 'Bytes[#1, 0..8] = "01234567"'),                        # 249 whole file
    ("claim bytes(b, -1, 2)", "[S006"),                                              # 243
    ("claim bytes(b, 2, 20)", "[V002"),                                              # 249 past the end
    ("claim bytes(b, 0, 9)", "[V002"),
])
def test_bytes_ranges_and_boundaries(tmp_path, prog, expect):
    p, h = tsv(tmp_path, "b.bin", b"01234567")
    ok, text = run(f"file b = sha256:{h}\n{prog}\n", [p])
    assert expect in text.split("\n")[0] and ok == (not expect.startswith("[")), text


def test_bytes_r004_edge(tmp_path):                                                  # 246
    p, h = tsv(tmp_path, "big.bin", b"0123456789" * 500)
    ok, text = run(f"file b = sha256:{h}\nclaim bytes(b, 0, 4096)\nclaim bytes(b, 0, 4097)\n", [p])
    lines = [ln for ln in text.split("\n") if ln.startswith("line ")]
    assert lines[0].startswith("line 2: formed: Bytes[#1, 0..4096]"), text
    assert lines[1].startswith("line 3: refused [R004"), text


def test_printed_row_of_a_keyed_cell(tmp_path):                                      # 408
    ok, line = one(tmp_path, 'claim cell(tsv(k), key(1, "cd"), 2)', K)
    assert ok and 'Cell[TSV[#1], row 2 (the row whose col 1 is "cd"), col 2] = "2"' in line, line


def test_three_part_key_with_an_idle_part_refuses(tmp_path):                         # 405
    t = {"k": "a\tb\tc\nx\tp\tm\nx\tq\tm\ny\tp\tm\n"}
    ok, line = one(tmp_path, 'claim cell(tsv(k), key(1, "x", 2, "p", 3, "m"), 3)', t)
    assert not ok and "[S008" in line, line
    ok, line = one(tmp_path, 'claim cell(tsv(k), key(1, "x", 2, "p"), 3)', t)
    assert ok and line.endswith('= "m"'), line


@pytest.mark.parametrize("cond", ['foo(1, "ab")', 'eq(1, "ab", "cd")', 'eq(1, "ab", c = 1)', '"x"'])
def test_unknown_conditions_and_extra_arguments_refuse_s006(tmp_path, cond):        # 336 x3
    ok, line = one(tmp_path, f"claim count(where(tsv(k), {cond}))", K)
    assert not ok and "[S006" in line, line


def test_trailing_space_in_a_long_key_cell_refuses_k004(tmp_path):                  # keys.py 87
    ok, line = one(tmp_path, 'claim cell(tsv(k), key(1, "cd"), 2)', {"k": "id\tv\nab \t1\ncd\t2\n"})
    assert not ok and "[K004" in line and '"ab "' in line, line


def test_s012_lines_carry_their_own_line_number(tmp_path):                           # 894
    ok, text = run_t(tmp_path, "claim atleast(number(cell(tsv(f), 1, 2)), c = 1)\n"
                               "claim atleast(widen(number(cell(tsv(f), 1, 2)), tolerance = 1), c = 1)\n")
    lines = [ln for ln in text.split("\n") if ln.startswith("line ")]
    assert [ln[:23] for ln in lines] == ["line 2: refused [S012, ", "line 3: refused [S012, "], text


def run_t(tmp_path, body):
    p, h = tsv(tmp_path, "t.tsv", T["f"])
    return run(f"file f = sha256:{h}\n{body}", [p])


@pytest.mark.parametrize("prog,steps", [
    ('claim count(where(tsv(t), eq(1, "ab")))', 80),   # 48 since exact-decision phase 3: part T is decided exactly (SPEC-EXACT 8); 83 since its checkpoint (W1 of a count solves its systems, SPEC-EXACT 5.1); 80 in phase 4 (the relaxation, SPEC-EXACT 4.2)
    ('claim cell(tsv(t), key(1, "cd"), 2)', 47),   # 1285 since 14 (real bytes); 49 since the phase 3 checkpoint (cell() and key() are part T, decided exactly); 47 in phase 4 (SPEC-EXACT 4.2)
    ("claim sum(tsv(t), 2)", 49),   # 213 since 02 (column 1, which no part reads, gets one fresh value); 224 since 14 (real bytes); 46 in exact-decision phase 4 (part N decided exactly); 47 in Part B P2 (inside()'s search step is charged); 49 in Part B item 8 (one relaxed system and its closed sum bounds instead of two presence cases; measured)
])
def test_step_counts_of_fixed_programs_are_pinned(tmp_path, prog, steps):            # 211, 224, 280, 360, 446
    """R002 counts steps; the count of a fixed program (witness search included) is the same on
    every machine and every run. A change in accounting must change these numbers on purpose."""
    p, h = tsv(tmp_path, "s.tsv", "id\tv\nab\t1\ncd\t2\nef\t3\n")
    st = R.Store([p], [])
    ok, out = check(f"file t = sha256:{h}\n{prog}\n".encode(), st)
    assert ok and st.steps.n == steps, (out, st.steps.n)


# ---- BIDS values (kernel 615-688) ---------------------------------------------------------------

def bids(tmp_path, body, first=False, **kw):
    d = tempfile.mkdtemp(dir=str(tmp_path))
    root = bidsfix.mini(os.path.join(d, "ds"), **kw)
    md = os.path.join(d, "m")
    os.mkdir(md)
    h = helpers.manifest(root, md)
    ok, text = helpers.run(f'dataset d = sha256:{h}\nlet b = bids(d)\nlet r = recording(b, "01", "x")\n{body}\n', [md], [root])
    return ok, [ln for ln in text.split("\n") if ln.startswith("line ")][0 if first else -1]


@pytest.mark.parametrize("claim,end", [
    ("claim duration(r, 1)", "#2 row 1] is recorded as 2 s (Recorded[s])"),          # 688: the duration, not the onset
    ("claim onset(r, 1)", "#3 row 1] is recorded as 1.5 s (Recorded[s])"),
    ("claim duration(r, 2)", "#2 row 2] is recorded as 2 s (Recorded[s])"),
    ("claim tr(r)", "is recorded as 2 s (Recorded[s])"),                             # 660 Recorded flag
    ("claim atleast(duration(r, 1), c = 1 s)", "holds of the recorded value"),        # bug found here (c / 2)
    ("claim atleast(tr(r), c = 1 s)", "holds of the recorded value"),
    ("claim atleast(events(r), c = 2)", "c = 2] holds"),                              # bug found here (onset)
])
def test_bids_values_and_recorded_flags(tmp_path, claim, end):
    ok, line = bids(tmp_path, claim)
    assert ok and line.endswith(end), line


@pytest.mark.parametrize("arg,code", [
    ("3", "S006"), ('foo("x")', "S006"), ('acq("x", "y")', "S006"),                 # 615 x3
    ('"a1"', "K001"),                                                                # 622 and->or
    ('"0123456789"', "V004"),                                                        # 622 <=-><
])
def test_recording_argument_codes(tmp_path, arg, code):
    ok, line = bids(tmp_path, f'claim recording(b, "01", "x", {arg})')
    assert not ok and f"[{code}" in line, line


def test_recording_without_a_task_refuses_s005(tmp_path):                            # 626
    ok, line = bids(tmp_path, 'claim recording(b, "01", acq("x"), rec("y"))')
    assert not ok and "[S005" in line, line


# ---- readers.py survivors -----------------------------------------------------------------------

@pytest.mark.parametrize("s,v", [("1234567890", 1234567890), ("0.1234567890", R.Fraction(123456789, 10 ** 9))])
def test_decimals_with_all_ten_digits(s, v):                                         # 279
    assert R.decimal(s) == v


def test_decimal_digit_bound_edge():                                                 # 281
    assert R.decimal("1" * 1000) == int("1" * 1000)
    with pytest.raises(R.Refusal) as e:
        R.decimal("1" * 1001)
    assert e.value.code == "R007"


@pytest.mark.parametrize("data,code", [
    (b"[" * 64 + b"]" * 64, None), (b"[" * 65 + b"]" * 65, "R008"),                 # 290, 291, 328
    (b'["' + b"[" * 70 + b'"]', None),                                               # 296, 297, 300
    (b"[" + b",".join([b"[]"] * 65) + b"]", None),                                   # 305
    (b"1" * 1000, None), (b"1" * 1001, "R007"),                                      # 313
    (b"1e000001", None), (b"1e1000", None), (b"1e1001", "R007"),
])
def test_json_bounds_at_their_edges(data, code):
    if code is None:
        R.parse_json(data, "j")
    else:
        with pytest.raises(R.Refusal) as e:
            R.parse_json(data, "j")
        assert e.value.code == code
    if data == b"1e000001":
        assert R.parse_json(data, "j") == 10


def test_leading_separator_refuses_t006():                                           # 249
    with pytest.raises(R.Refusal) as e:
        R.parse_tsv(b"\x0bx\ty\n1\t2\n", "h", R.Steps())
    assert e.value.code == "T006"


def _header(dim=None, vox=None, sizeof=None, n=352):
    b = bytearray(bidsfix.nifti1((1, 1, 1))[:352])
    if dim is not None:
        struct.pack_into("<8h", b, 40, *dim)
    if vox is not None:
        struct.pack_into("<f", b, 108, vox)
    if sizeof is not None:
        struct.pack_into("<i", b, 0, sizeof)
        b += b"\x00" * 200
    return bytes(b[:n]) if n < 352 else bytes(b)


@pytest.mark.parametrize("dim,ok", [
    ((0, 1, 1, 1, 1, 1, 1, 1), False), ((1, 4, 1, 1, 1, 1, 1, 1), True), ((7, 2, 2, 2, 2, 2, 2, 2), True),
    ((3, 8, 2, 2, 1, 1, 1, 1), True), ((3, 1, 1, 1, 1, 1, 1, 1), True), ((3, 2, 2, 0, 1, 1, 1, 1), False),
    ((9, 1, 1, 1, 1, 1, 1, 1), False), ((-1, 1, 1, 1, 1, 1, 1, 1), False), ((3, 2, -2, 2, 1, 1, 1, 1), False),
])
def test_nifti_dim_validation(dim, ok):                                              # 421, 11 survivors
    if ok:
        assert R.nifti_header(_header(dim=dim), "n").dim == list(dim)
    else:
        with pytest.raises(R.Refusal) as e:
            R.nifti_header(_header(dim=dim), "n")
        assert e.value.code == "I002"


@pytest.mark.parametrize("kw,code", [
    ({"vox": 352.5}, "I001"), ({"vox": float("nan")}, "I001"),                       # 405, 387
    ({"sizeof": 540}, "I001"),                                                       # 409: NIfTI-2 size, no n+2 magic
    ({"n": 348}, "I001"),
])
def test_nifti_header_refusals(kw, code):
    with pytest.raises(R.Refusal) as e:
        R.nifti_header(_header(**kw), "n")
    assert e.value.code == code


def test_nifti_header_of_exactly_352_bytes_is_read():                               # 399
    assert R.nifti_header(_header(), "n").dim[0] == 3


def test_infinite_pixdim_reads_as_no_value():                                        # 387
    b = bytearray(bidsfix.nifti1((1, 1, 1, 2))[:352])
    struct.pack_into("<f", b, 92, float("inf"))
    assert R.nifti_header(bytes(b), "n").pixdim[4] is None


H64 = "a" * 64


@pytest.mark.parametrize("line,ok", [
    (f"{H64}\t1\tx", True), (f"{H64}\t{'1' * 20}\tx", True),
    (f"{H64}\t1\tx\ty", False), (f"{H64[:63]}\t1\tx", False), (f"{'A' * 64}\t1\tx", False),   # 478
    (f"{H64}\t\u0661\tx", False), (f"{H64}\t1x\tx", False), (f"{H64}\t{'1' * 21}\tx", False),  # 479
    (f"{H64}\t-1\tx", False), (f"{H64}\t01\tx", False),
])
def test_manifest_line_validation(line, ok):
    data = (R.MANIFEST_MAGIC + "\n" + line + "\n").encode()
    if ok:
        assert list(R.parse_manifest(data, "m")) == ["x"]
    else:
        with pytest.raises(R.Refusal) as e:
            R.parse_manifest(data, "m")
        assert e.value.code == "M001"


def test_symlinks_are_ignored_by_the_store_and_the_manifest(tmp_path):              # 102, 505
    d = tmp_path / "d"
    d.mkdir()
    (d / "a.tsv").write_bytes(b"x\n1\n")
    helpers.symlink(str(tmp_path / "elsewhere.tsv"), str(d / "link.tsv"))
    (tmp_path / "elsewhere.tsv").write_bytes(b"y\n2\n")
    helpers.symlink(str(d / "a.tsv"), str(d / "b.tsv"))
    assert list(R.Store([str(d)], []).by_hash) == [sha(str(d / "a.tsv"))]
    assert R.make_manifest(str(d)).decode().count("\n") == 2   # the magic line and a.tsv


# ---- syntax.py survivors ------------------------------------------------------------------------

@pytest.mark.parametrize("prog,code", [
    ('claim cell(tsv(k), key(1, "\\q12"), 2)', "P002"),                             # 126 and->or
    ('claim cell(tsv(k), key(1, "\\x4A"), 2)', "P002"),                             # 126 slice end
    ('claim cell(tsv(k), key(1, "\\xzz"), 2)', "P002"),
    ('claim "\\x', "P002"),                                                          # 126 len guard
    ("claim x -", "P001"),                                                           # 138
    ("claim 1.", "P001"),                                                            # 142
    ("claim atleast(count(tsv(k)), c = 1.)", "P001"),                                # 142 occ1
    ("claim 1.5", "S001"),                                                           # 209
    ("claim exceeds(widen(number(cell(tsv(k), 1, 2)), tolerance = 1 is), c = 1)", "P001"),   # 246
    ('claim share(where(tsv(k), eq(1, "ab"))) is 1/0', "P007"),                     # 273
    ('claim share(where(tsv(k), eq(1, "ab"))) is 1/1', "V001"),                     # 273: 1/1 is a ratio
    ("file g = sha256:abc", "P003"), (f"file g = sha256:{'A' * 64}", "P003"),        # 163
    (f"file g = sha256:{'a' * 64}g", "P003"),
    (f"let {'a' * 65} = count(tsv(k))", "P010"),
    ("claim atleast(count(tsv(k)), c = " + "1" * 1001 + ")", "R010"),
    ("claim atleast(count(tsv(k)), c = " + "1" * 1000 + ")", "V001"),               # 149: 1000 digits are read
    ("claim " + "count(" * 64 + "tsv(k)" + ")" * 64, "R001"),
    ("claim " + "count(" * 63 + "tsv(k)" + ")" * 63, "S007"),                        # 201, 202: 64 levels nest
])
def test_syntax_edges(tmp_path, prog, code):
    ok, line = one(tmp_path, prog, K)
    assert not ok and f"[{code}" in line, line


@pytest.mark.parametrize("prog", [f"let {'a' * 64} = count(tsv(k))", "let sha256 = count(tsv(k))\nclaim sha256 is 2"])
def test_names_at_the_edge_form(tmp_path, prog):                                     # 159, 161
    ok, line = one(tmp_path, prog, K) if "claim" in prog else (run_k(tmp_path, prog), "")
    assert ok, line


def run_k(tmp_path, prog):
    p, h = tsv(tmp_path, "k.tsv", K["k"])
    return run(f"file k = sha256:{h}\n{prog}\n", [p])[0]


@pytest.mark.parametrize("prog,line", [
    (b"\n\nclaim x\r\n", 3), (b"\nclaim x \x01\n", 2),                               # 362, 364
    (b"claim x # \x7f\n", 1),                                                        # 363: even in a comment
])
def test_p009_reports_the_line_of_the_byte(prog, line):
    ok, text = run(prog)
    assert not ok and text.startswith(f"line {line}: refused [P009"), text


def test_program_size_bound_edge():                                                  # 326-352, 366
    """measured size exactly 1,000,000 (names count as one) is not R001; one more byte is."""
    prog = open(os.path.join(MUT, "size_1M.rl"), "rb").read()
    files = [os.path.join(MUT, "p2.tsv")]
    ok, text = run(prog, files)
    assert "R001" not in text, text[:300]
    ok, text = run(prog + b"x", files)
    assert not ok and text.startswith("line 0: refused [R001"), text[:300]


# ---- bids101.py survivors -----------------------------------------------------------------------

N5 = bidsfix.nifti1((2, 2, 2, 5), tr=2.0)


@pytest.mark.parametrize("extra,code", [
    ({"sub-01/func/sub-01_task-x_run-ab_bold.nii": N5}, "B17"),                      # 52: run label not an index
    ({"sub-01/func/sub-01_task-x_foo-y_bold.nii": N5}, "B17"),                       # 78: unknown entity
    ({"sub-01/func/bold.nii": N5}, "B17"),                                           # 123, 132: no entities
    ({"participants.tsv": "participant_id\tgroup\nsub-01\ta\nx01\ta\n"}, "B11"),     # 566
    ({"participants.json": '{"nogroup": {"Description": "g"}}'}, "B19"),
    ({"dataset_description.json": '{"Name": "m"}'}, "B01"),                          # 272
])
def test_bids_reader_refusals(tmp_path, extra, code):
    ok, line = bids(tmp_path, "claim count(participants(b))", first=True, extra=extra)
    assert not ok and f"{code}" in line, line


@pytest.mark.parametrize("task_json,code", [
    ('{"TaskName": "x", "RepetitionTime": "2"}', "B21"),                             # 445 string TR
    ('{"TaskName": "x", "RepetitionTime": 0}', "B08"),                               # 445 TR 0
    ('{"TaskName": 5, "RepetitionTime": 2}', "B08"),                                 # 449
    ('{"TaskName": "x", "RepetitionTime": 2, "SliceTiming": 1}', "B10"),             # 478
    ('{"TaskName": "x", "RepetitionTime": 2, "SliceEncodingDirection": "k", "SliceTiming": [0, 2]}', "B10"),        # 482: a time equal to the TR
])
def test_bids_sidecar_refusals(tmp_path, task_json, code):
    ok, line = bids(tmp_path, "claim count(participants(b))", first=True, task_json=task_json)
    assert not ok and f"{code} x" in line, line


def test_valid_participants_json_forms(tmp_path):                                    # 585
    ok, line = bids(tmp_path, "claim count(participants(b)) is 2", extra={"participants.json": '{"group": {"Description": "g"}}'})
    assert ok, line


def test_bad_subject_folder_is_not_a_subject(tmp_path):                              # 113
    # fix pass R5 (Patsak, 26 Oct 2026): it is not a subject, and it refuses B17 (S0628), no longer an extra file
    ok, line = bids(tmp_path, "claim count(participants(b)) is 2", first=True, extra={"sub-a_b/func/sub-a_b_task-x_bold.nii": N5})
    assert not ok and "B17 x1" in line and "S0628" in line, line


@pytest.mark.parametrize("tr", ["0.1", "0.7", "0.3"])
def test_inexact_tr_matches_its_float32_pixdim(tmp_path, tr):                        # 170: nearest float32
    ok, line = bids(tmp_path, "claim tr(r)", subjects=("01",), events="onset\tduration\n0\t0.1\n",
                    task_json='{"TaskName": "x", "RepetitionTime": %s}' % tr,
                    extra={"sub-01/func/sub-01_task-x_bold.nii": bidsfix.nifti1((2, 2, 2, 5), tr=float(tr))})
    assert ok and line.endswith(f"is recorded as {tr} s (Recorded[s])"), line
