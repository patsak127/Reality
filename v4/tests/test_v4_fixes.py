"""v4-fixes: regression tests for the preliminary Opus 5.5 max v4 review findings
(../review-opus55max-v4/PRELIM.md). Each test is built from the finding's own repro."""
import os
import tempfile

import pytest

import bidsfix
import helpers
from helpers import run, tsv


def lines(text, n):
    return [ln for ln in text.split("\n") if ln.startswith(f"line {n}:")][0]


def _bids(tmp_path, body, **kw):
    d = tempfile.mkdtemp(dir=str(tmp_path))
    root = bidsfix.mini(os.path.join(d, "ds"), **kw)
    md = os.path.join(d, "m")
    os.mkdir(md)
    h = helpers.manifest(root, md)
    return run(f"dataset d = sha256:{h}\n{body}\n".replace("{h}", h), [md], [root])


# ---- 01: two names for one hash are one slot (SPEC 4.1) -----------------------------------------

def test_01_two_names_one_hash(tmp_path):
    p, h = tsv(tmp_path, "f.tsv", "c\na\nb\n")
    ok, text = run(f"file f = sha256:{h}\nfile g = sha256:{h}\n"
                   "claim difference(rows(tsv(f)), rows(tsv(g)))\n"
                   'claim exceeds(difference(count(where(tsv(f), eq(1, "a"))), count(where(tsv(g), eq(1, "a")))), c = -1)\n', [p])
    assert "[S008" in lines(text, 3) and "[S008" in lines(text, 4), text


def test_01_two_dataset_names_one_manifest(tmp_path):
    ok, text = _bids(tmp_path, "dataset e = sha256:{h}\nclaim difference(count(participants(bids(d))), count(participants(bids(e))))")
    assert "[S008" in lines(text, 3), text


def test_01_two_hashes_still_two_slots(tmp_path):
    p, h = tsv(tmp_path, "f.tsv", "c\na\nb\n")
    q, g = tsv(tmp_path, "g.tsv", "c\na\n")
    ok, text = run(f"file f = sha256:{h}\nfile g = sha256:{g}\nclaim difference(rows(tsv(f)), rows(tsv(g)))\n", [p, q])
    assert ok, text


# ---- 02: one condition twice, by header or by position (BB's call 02, on Patsak's behalf) --------

@pytest.mark.parametrize("claim", [
    'count(where(t, eq("id", "a"), eq(1, "a")))', 'count(where(t, eq(1, "a"), eq(1, "a")))',
    'sum(where(t, ge("v", c = 2), ge(2, c = 2)), 2)', 'count(where(where(t, eq("id", "a")), eq(1, "a")))',
    'cell(t, key("id", "b", 1, "b"), 2)', 'cell(t, key(1, "b", 1, "b"), 2)'])
def test_02_same_condition_twice_refuses(tmp_path, claim):
    p, h = tsv(tmp_path, "f.tsv", "id\tv\na\t1\nb\t2\na\t3\n")
    ok, text = run(f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {claim}\n", [p])
    assert "[S008, item 1]" in lines(text, 3), text


def test_02_different_conditions_on_one_column_still_judged_by_w2(tmp_path):
    p, h = tsv(tmp_path, "f.tsv", "id\tv\na\t1\nb\t2\na\t3\n")
    ok, text = run(f'file f = sha256:{h}\nlet t = tsv(f)\nclaim count(where(t, eq("id", "a"), ne(1, "b")))\n', [p])
    assert "eq(...)" not in lines(text, 3), text


# ---- 03: renaming a file does not change the witness search (SPEC 4.4, 4.5) ---------------------

def _witness_steps(tmp_path, monkeypatch, a, b, claim):
    from reality4 import witness as W
    calls, ev = [0], W.evaluate
    monkeypatch.setattr(W, "evaluate", lambda *x: calls.__setitem__(0, calls[0] + 1) or ev(*x))
    p, hp = tsv(tmp_path, "f.tsv", "c\td\te\nq\t100\tq\nq\t100\tq\nq\t100\tq\n")
    q, hq = tsv(tmp_path, "g.tsv", "d\nr\n")
    ok, text = run(f"file {a} = sha256:{hp}\nfile {b} = sha256:{hq}\n{claim.format(a=a, b=b)}\n", [p, q])
    return lines(text, 3).split(": ", 1)[1], calls[0]   # W1 + W2 evaluations, the work R013 bounds


@pytest.mark.parametrize("names", [("z", "g"), ("a", "g"), ("f", "b"), ("g", "f")])
def test_03_renaming_keeps_verdict_and_witness_work(tmp_path, monkeypatch, names):
    claim = 'claim difference(count(where(tsv({a}), ne(1, "x"), ge(2, c = 99), ne(3, "v"))), count(where(tsv({b}), ne(1, "y"))))'
    assert _witness_steps(tmp_path, monkeypatch, *names, claim) == _witness_steps(tmp_path, monkeypatch, "f", "g", claim)


# ---- 04: the memory floor holds (v4 SPEC 9.4) -----------------------------------------------------

def test_04_witness_out_of_memory_is_no_verdict_not_a_refusal(tmp_path, monkeypatch):
    from reality4 import readers as R
    real = R.parse_tsv
    p, h = tsv(tmp_path, "g.tsv", "c\n" + "a\n" * 40)
    mine = open(p, "rb").read()   # every candidate on which the claim holds runs out of memory
    monkeypatch.setattr(R, "parse_tsv", lambda data, *a, **k: real(data, *a, **k) if data == mine or data.count(b"\n") < 40 else (_ for _ in ()).throw(MemoryError()))
    ok, text = run(f"file g = sha256:{h}\nclaim atleast(rows(tsv(g)), c = 39)\n", [p])
    assert ok is None and "no verdict" in text and "S011" not in text, text


def test_04_a_kept_selection_is_charged_per_row_object(tmp_path):
    from reality4 import readers as R
    from reality4.kernel import check
    p, h = tsv(tmp_path, "f.tsv", "c\n" + "a\n" * 1000)
    got = []
    for extra in ("", 'let s = where(t, ne(1, "x"))\n'):
        store = R.Store([p])
        check(f"file f = sha256:{h}\nlet t = tsv(f)\n{extra}".encode(), store)
        got.append(store.prog_bytes)
    assert got[1] - got[0] == 72 * 1000 + 64


def test_04_a_table_too_big_for_the_bound_refuses_before_it_is_built(tmp_path, monkeypatch):
    from reality4 import readers as R
    monkeypatch.setattr(R, "MAX_ACCOUNTED", 50_000)
    built = []
    real = R.parse_tsv
    monkeypatch.setattr(R, "parse_tsv", lambda *a, **k: built.append(1) or real(*a, **k))
    p, h = tsv(tmp_path, "f.tsv", "a\tb\n" + "1\t2\n" * 400)
    ok, text = run(f"file f = sha256:{h}\nclaim rows(tsv(f))\n", [p])
    assert "[R012" in text and not built, text


@pytest.mark.skipif(os.name != "posix", reason="RLIMIT_DATA exists only on POSIX; the Windows limit (a job object) is test_v4_cli::test_below_memory_floor_in_a_windows_job")
def test_04_the_floor_reads_rlimit_data(tmp_path):
    import resource, subprocess, sys
    p, h = tsv(tmp_path, "f.tsv", "c\na\n")
    prog = tmp_path / "p.rl"
    prog.write_text(f"file f = sha256:{h}\nclaim rows(tsv(f))\n")
    lim = 1 << 30
    r = subprocess.run([sys.executable, "-m", "reality4", "check", str(prog), "--files", p], capture_output=True,
                       env={**os.environ, "PYTHONPATH": os.path.join(os.path.dirname(__file__), "..", "src")},
                       preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_DATA, (lim, resource.RLIM_INFINITY)))
    assert r.returncode == 3 and b"(1073741824 bytes) is below" in r.stdout, r


def test_04_the_floor_reads_every_ancestor_cgroup(monkeypatch):
    import io
    from reality4 import machine
    files = {"/proc/self/cgroup": b"0::/a/b\n", "/sys/fs/cgroup/a/b/memory.max": b"max\n",
             "/sys/fs/cgroup/a/memory.max": b"1000\n", "/sys/fs/cgroup/memory.max": b"max\n"}
    monkeypatch.setattr(machine, "open", lambda p, mode="r": io.BytesIO(files[p]) if p in files else (_ for _ in ()).throw(OSError(p)), raising=False)
    assert machine._cgroup_max() == 1000


# ---- 05: a NIfTI header read from the cache is still a read (check 2) -----------------------------

def test_05_two_header_claims_on_one_image(tmp_path):
    p, h = tsv(tmp_path, "img.nii", bidsfix.nifti1((4, 4, 3, 10), tr=2.0))
    ok, text = run(f"file n = sha256:{h}\nclaim dim(nifti(n), 4)\nclaim pixdim(nifti(n), 4)\n", [p])
    assert ok and "C001" not in text, text


def test_05_a_header_claim_after_another_program(tmp_path):
    from reality4 import readers as R
    from reality4.kernel import check
    p, h = tsv(tmp_path, "img.nii", bidsfix.nifti1((4, 4, 3, 10), tr=2.0))
    store = R.Store([p])
    first = check(f"file n = sha256:{h}\nclaim pixdim(nifti(n), 4)\n".encode(), store)
    second = check(f"file n = sha256:{h}\nclaim dim(nifti(n), 4)\n".encode(), store)
    assert first[0] and second[0], (first, second)


# ---- 06: an answer on an input one reader rejects is no witness (SPEC 4.1) ------------------------

def test_06_csv_and_tsv_of_one_file(tmp_path):
    p, h = tsv(tmp_path, "f.csv", "c\nx\ny\n")
    ok, text = run(f'file f = sha256:{h}\nclaim difference(count(where(csv(f), eq(1, "a,b"))), rows(tsv(f)))\n', [p])
    assert "[S011" in lines(text, 2) or "[S008" in lines(text, 2), text


# ---- 07: widen() is judged at the statement's answer, like every other part (SPEC 4.3 W2) --------

IDLE_WIDEN = 'let d = difference(rows(tsv(f)), count(where(tsv(f), eq(1, "a"))))\nclaim exceeds({}, c = 1/2)\n'


def test_07_a_widen_that_no_input_can_matter_refuses(tmp_path):
    p, h = tsv(tmp_path, "f.tsv", "c\na\nx\ny\n")
    ok, text = run(f"file f = sha256:{h}\n" + IDLE_WIDEN.format("widen(d, tolerance = 1/1000)"), [p])
    assert "[S008, item 1]: widen()" in lines(text, 3), text
    ok, text = run(f"file f = sha256:{h}\n" + IDLE_WIDEN.format("d"), [p])
    assert ok, text


@pytest.mark.parametrize("claim", ["below(widen(number(cell(t, 3, 2)), tolerance = 0.5), c = 1)",
                                   "below(widen(widen(number(cell(t, 2, 2)), tolerance = 2.5), tolerance = 1/2), c = 30)",
                                   'exceeds(widen(mean(t, 2), tolerance = 1), c = 20)'])
def test_07_a_widen_that_can_change_the_comparison_forms(tmp_path, claim):
    p, h = tsv(tmp_path, "f.tsv", "c\tx\na\t1\nb\t2\nc\t0.1\n")
    ok, text = run(f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {claim}\n", [p])
    assert "[S008" not in text, text


# ---- 08: the participant filter of recordings() is a W2 part ----------------------------------------

def test_08_a_filter_that_keeps_every_participant_bears(tmp_path):
    ok, text = _bids(tmp_path, 'let b = bids(d)\nclaim count(recordings(b, "x", participants(b)))\nclaim count(recordings(b, "x"))',
                     subjects=("01", "02", "03"), groups={"01": "a", "02": "b", "03": "a"})
    # Unit H06 (Opus 5.5 max2 review 06, 30 Oct 2026): overturns this fix's S008 W2. On a dataset without
    # participants.tsv the filter refuses V007 and the statement without it answers: a refusal and an answer are two
    # outcomes (SPEC-EXACT 1, 5.2), so the filter bears and the claim forms.
    assert "formed" in lines(text, 3) and "= 3" in lines(text, 3) and "formed" in lines(text, 4), text


def test_08_a_filter_that_selects_forms(tmp_path):
    ok, text = _bids(tmp_path, 'let b = bids(d)\nclaim count(recordings(b, "x", where(participants(b), eq("group", "a"))))',
                     subjects=("01", "02", "03"), groups={"01": "a", "02": "b", "03": "a"})
    assert "formed" in lines(text, 3) and "= 2" in lines(text, 3), text


# ---- 09: JSON exponents are read with their exact value (principle §11 as amended 26 Oct) --------

def test_09_json_exponents_read_exactly(tmp_path):
    p, h = tsv(tmp_path, "j.json", '{"RepetitionTime": 2e0, "a": 1.5E-2, "b": 1e1000}')
    ok, text = run(f'file j = sha256:{h}\nclaim member(json(j), "RepetitionTime")\nclaim member(json(j), "a")\n'
                   'claim exceeds(member(json(j), "b"), c = 1)\n', [p])
    assert ok and "= 2 (Exact)" in lines(text, 2) and "= 0.015 (Exact)" in lines(text, 3) and "holds" in lines(text, 4), text


# ---- 10: the form of 1.0.1's lists, dictionaries and booleans is checked -------------------------
# ---- 12: participant_id first; a column description key 1.0.1 does not list refuses B30 (BB's call 12)

GROUP_A = 'claim count(where(participants(bids(d)), eq("group", "a")))'
CASES_10_12 = {
    "levels": ({"participants.json": '{"group": {"Levels": "a or b"}}'}, "B19", "Levels"),
    "authors": ({"dataset_description.json": '{"Name": "mini", "BIDSVersion": "1.0.1", "Authors": "Jane Doe", "ReferencesAndLinks": 42}'}, "B01", "Authors"),
    "derivative": ({"task-x_events.json": '{"kind": {"Description": "what was shown", "Derivative": "yes"}}'}, "B30", "Derivative"),
    "mtm": ({"phenotype/q.tsv": "participant_id\tscore\nsub-01\t3\nsub-02\t4\n",
             "phenotype/q.json": '{"MeasurementToolMetadata": {"Version": 2}, "score": {"Description": "s"}}'}, "B19", "MeasurementToolMetadata"),
    "fields": ({"participants.json": '{"group": {"Descripton": "typo of Description", "Colour": 7}}'}, "B30", "Colour"),
}


@pytest.mark.parametrize("name", sorted(CASES_10_12))
def test_10_12_structure_faults_do_not_conform(tmp_path, name):
    extra, code, word = CASES_10_12[name]
    ok, text = _bids(tmp_path, GROUP_A, subjects=("01", "02"), groups={"01": "a", "02": "b"}, extra=extra)
    assert "[B00" in lines(text, 2) and f"{code} x" in lines(text, 2) and word in lines(text, 2), text


def test_12_participant_id_second_does_not_conform(tmp_path):
    ok, text = _bids(tmp_path, GROUP_A, participants=False, extra={"participants.tsv": "group\tparticipant_id\na\tsub-01\nb\tsub-02\n"})
    assert "B11 x1, first: participants.tsv: participant_id is not the first column" in lines(text, 2), text


@pytest.mark.parametrize("extra", [
    {"participants.json": '{"group": {"LongName": "g", "Description": "d", "Levels": {"a": "A", "b": "B"}, "Units": "n/a", "TermURL": "u", "Derivative": true}}'},
    {"dataset_description.json": '{"Name": "mini", "BIDSVersion": "1.0.1", "Authors": ["Jane Doe"], "ReferencesAndLinks": ["x"]}'},
    {"phenotype/q.tsv": "participant_id\tscore\nsub-01\t3\nsub-02\t4\n",
     "phenotype/q.json": '{"MeasurementToolMetadata": {"Description": "q", "TermURL": "u"}, "score": {"Description": "s", "Derivative": false}}'},
])
def test_10_12_well_formed_descriptions_still_conform(tmp_path, extra):
    ok, text = _bids(tmp_path, GROUP_A, subjects=("01", "02"), groups={"01": "a", "02": "b"}, extra=extra)
    assert ok and "= 1 (Exact)" in lines(text, 2), text


# ---- 13: a share within a subset (BB's call 13): a base condition repeated in sel is judged in both

SHARE_DATA = "group\tage\nA\t30\nB\t40\nP\t17\nA\t16\nA\t25\n"


@pytest.mark.parametrize("claim,want", [
    ('share(where(t, ne("group", "P"), eq("group", "A")), where(t, ne("group", "P")))', "= 3/4 (Exact)"),
    ('share(where(t, ge("age", c = 18), ge("age", c = 30)), where(t, ge("age", c = 18)))', "= 2/3 (Exact)"),
    ('share(where(t, ne("group", "P"), ne("group", "B")), where(t, ne("group", "P")))', "= 3/4 (Exact)"),
])
def test_13_share_of_a_sub_base_forms(tmp_path, claim, want):
    p, h = tsv(tmp_path, "f.tsv", SHARE_DATA)
    ok, text = run(f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {claim}\n", [p])
    assert want in lines(text, 3), text


@pytest.mark.parametrize("claim", [
    'share(where(t, ne("group", "P"), ne(1, "P"), eq("group", "A")), where(t, ne("group", "P")))',   # call 02, by header and number
    'share(where(t, ne("group", "P"), ne("group", "P"), eq("group", "A")), where(t, ne("group", "P")))',
    'share(where(t, eq("group", "A"), eq("group", "A")), where(t, eq("group", "A")))',
])
def test_13_idle_conditions_in_a_share_still_refuse(tmp_path, claim):
    p, h = tsv(tmp_path, "f.tsv", SHARE_DATA)
    ok, text = run(f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {claim}\n", [p])
    assert "[S008" in lines(text, 3) or "[S011" in lines(text, 3), text


# ---- 14: seven conditions on seven columns form; the real bytes are a witness candidate ------------

SEVEN = "c1\tc2\tc3\tc4\tc5\tc6\tc7\nk\tk\tk\tk\tk\tk\tk\nk\tk\tk\tk\tk\tk\tz\nz\tk\tk\tk\tk\tk\tk\n"


@pytest.mark.parametrize("claim", [
    'count(where(t, eq(1, "k"), eq(2, "k"), eq(3, "k"), eq(4, "k"), eq(5, "k"), eq(6, "k"), eq(7, "k")))',
    'count(where(where(t, eq(1, "k"), eq(2, "k"), eq(3, "k")), eq(4, "k"), eq(5, "k"), eq(6, "k"), eq(7, "k")))',
])
def test_14_seven_conditions_form(tmp_path, claim):
    p, h = tsv(tmp_path, "f.tsv", SEVEN)
    ok, text = run(f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {claim}\n", [p])
    assert "= 1 (Exact)" in lines(text, 3), text


# ---- 15: two files against a cutoff: each slot is also varied against the others' real bytes ------

def test_15_cross_file_cutoff_forms(tmp_path):
    p, hp = tsv(tmp_path, "f.tsv", "c\na\nb\nc\nd\n")
    q, hq = tsv(tmp_path, "g.tsv", "c\ny\nb\n")
    ok, text = run(f"file f = sha256:{hp}\nfile g = sha256:{hq}\n"
                   'claim atleast(difference(count(where(tsv(f), ne(1, "x"))), count(where(tsv(g), ne(1, "y")))), c = 2)\n', [p, q])
    assert ok and "holds" in lines(text, 3), text


# ---- 16: dim() of a spatial axis has witnesses -------------------------------------------------------

@pytest.mark.parametrize("claim,want", [("dim(nifti(n), 1)", "= 64 (Exact)"), ("dim(nifti(n), 2)", "= 64 (Exact)"),
                                        ("dim(nifti(n), 3)", "= 30 (Exact)"), ("exceeds(dim(nifti(n), 1), c = 32)", "holds")])
def test_16_spatial_dims_form(tmp_path, claim, want):
    p, h = tsv(tmp_path, "img.nii", bidsfix.nifti1((64, 64, 30, 10), tr=2.0))
    ok, text = run(f"file n = sha256:{h}\nclaim {claim}\n", [p])
    assert ok and want in lines(text, 2), text


# ---- 17: a .nii.gz of several gzip members reads the same header-only as whole ----------------------

@pytest.mark.parametrize("split,pad", [(100, b""), (100, b"\0" * 16), (348, b""), (None, b"\0" * 8)])
def test_17_multi_member_gzip_header(tmp_path, split, pad):
    import gzip
    img = bidsfix.nifti1((2, 2, 2, 5), tr=2.0)
    raw = (gzip.compress(img[:split]) + gzip.compress(img[split:]) if split else gzip.compress(img)) + pad
    p, h = tsv(tmp_path, "img.nii.gz", raw)
    ok, text = run(f"file n = sha256:{h}\nclaim dim(nifti(n), 4)\n", [p])
    assert ok and "= 5 (Exact)" in lines(text, 2), text


# ---- 18: the order of conditions never changes a verdict (BB's call on Patsak's behalf, 2026-10-26) --

@pytest.mark.parametrize("body,want", [("a\tb\n1\tx\n9\t5\n8\t2\n", "= 1 (Exact)"),   # row 1 is decided by col 1
                                       ("a\tb\n9\tx\n9\t5\n8\t2\n", "V005")])          # row 1 is decided by nothing
def test_18_condition_order_never_changes_the_verdict(tmp_path, body, want):
    import itertools
    p, h = tsv(tmp_path, "f.tsv", body)
    conds = ["gt(1, c = 5)", "gt(2, c = 3)", 'ne(1, "7")']
    prog = f"file f = sha256:{h}\nlet t = tsv(f)\n" + "".join(f"claim count(where(t, {', '.join(o)}))\n" for o in itertools.permutations(conds))
    ok, text = run(prog, [p])
    got = [want in lines(text, n) for n in range(3, 9)]
    assert all(got), text


# ---- 19: a count is identified by its selection's row set, so S012 sees through its spelling --------

T19 = "a\tb\nx\tp\ny\tq\nx\tq\nz\tp\n"
XP, PX, Y = 'count(where(t, eq(1, "x"), eq(2, "p")))', 'count(where(t, eq(2, "p"), eq(1, "x")))', 'count(where(t, eq(1, "y")))'
X = 'count(where(t, eq(1, "x")))'


@pytest.mark.parametrize("a,b,y1,y2,s012", [(XP, XP, Y, Y, True), (XP, PX, Y, Y, True), ("rows(t)", "count(t)", X, X, True),
                                           (XP, 'count(where(t, eq(1, "z")))', Y, Y, False)])   # same count, other rows
def test_19_count_identity_is_the_row_set(tmp_path, a, b, y1, y2, s012):
    p, h = tsv(tmp_path, "f.tsv", T19)
    ok, text = run(f"file f = sha256:{h}\nlet t = tsv(f)\nclaim widen(difference({a}, {y1}), tolerance = 1/10)\n"
                   f"claim widen(difference({b}, {y2}), tolerance = 3/10)\n", [p])
    assert ("S012" in lines(text, 3) and "S012" in lines(text, 4)) == s012 and (ok != s012), text


# ---- 11: SliceTiming's axis (BB's call on Patsak's behalf, 2026-10-26): S0369 names no default -------

def _bold(dims, dim_info):
    img = bytearray(bidsfix.nifti1(dims, tr=2.0))
    img[39] = dim_info   # NIfTI-1 dim_info: slice_dim in bits 4-5
    return bytes(img)


@pytest.mark.parametrize("dims,dim_info,n,code", [
    ((3, 3, 2, 5), 0, 2, None),      # fits k only: that axis
    ((3, 3, 2, 5), 0, 3, "B30"),     # fits i and j, nothing names the axis: two readings
    ((3, 3, 2, 5), 0x10, 3, None),   # slice_dim 1 names i, and it fits
    ((3, 3, 2, 5), 0x10, 2, "B10"),  # slice_dim 1 names i, and it does not fit
    ((3, 3, 2, 5), 0, 4, "B10"),     # fits no axis
    ((106, 106, 64, 5), 0, 64, None),    # ds001734's 319 headers with dim_info 0
    ((106, 106, 64, 5), 48, 64, None)])  # ds001734's 113 headers with dim_info 48 (slice_dim 3)
def test_11_slice_timing_axis(tmp_path, dims, dim_info, n, code):
    times = ", ".join(str(i / 100) for i in range(n))
    extra = {f"sub-{s}/func/sub-{s}_task-x_bold.nii": _bold(dims, dim_info) for s in ("01", "02")}
    extra["task-x_bold.json"] = '{"TaskName": "x", "RepetitionTime": 2, "SliceTiming": [%s]}' % times
    root = bidsfix.mini(str(tmp_path / "ds"), extra=extra)
    md = tmp_path / "m"
    md.mkdir()
    mh = helpers.manifest(root, str(md))
    ok, text = run(f"dataset d = sha256:{mh}\nclaim count(participants(bids(d)))\n", [str(md)], [root])
    assert (ok and code is None) or (not ok and code and f"{code} x" in text and len(set(__import__("re").findall(r"B\d\d x", text)) - {"B00 x"}) == 1), text


# ---- review 25: an empty sum of tr keeps the quantity's unit ----------------------------------------

def _mini_run(tmp_path, claims, **kw):
    root = bidsfix.mini(str(tmp_path / "ds"), **kw)
    md = tmp_path / "m"
    md.mkdir()
    mh = helpers.manifest(root, str(md))
    return run(f"dataset d = sha256:{mh}\nlet b = bids(d)\n" + "".join(f"claim {c}\n" for c in claims), [str(md)], [root])


def test_r25_empty_tr_sum_is_seconds(tmp_path):
    empty = 'sum(recordings(b, "x", where(participants(b), eq("group", "c"))), "tr")'
    ok, text = _mini_run(tmp_path, [empty, empty + " is 0 s", 'sum(recordings(b, "x", where(participants(b), eq("group", "c"))), "volumes")'],
                         groups={"01": "a", "02": "b"})
    assert ok and "= 0 s (Exact)" in lines(text, 3) and "= 0 s (Exact)" in lines(text, 4) and "= 0 (Exact)" in lines(text, 5), text


# ---- review 24: equal values in two sidecars of one folder: the claim names both --------------------

def test_r24_equal_sidecars_named_both(tmp_path):
    extra = {"sub-01_task-x_bold.json": '{"RepetitionTime": 2}', "sub-02_task-x_bold.json": '{"RepetitionTime": 2}'}
    ok, text = _mini_run(tmp_path, ['tr(recording(b, "01", "x"))'], extra=extra)
    h = {name: helpers.sha(os.path.join(str(tmp_path / "ds"), name)) for name in ("task-x_bold.json", "sub-01_task-x_bold.json")}
    assert ok and ", from #3, #4]" in lines(text, 3) and all(x in text for x in h.values()), text


# ---- review 23: SPEC 9.2's literal node count is the code's ----------------------------------------

def test_r23_literal_nodes_match_spec():
    from reality4.sorts import S, Lit
    spec = open(os.path.join(os.path.dirname(__file__), "..", "SPEC.md"), encoding="utf-8").read()
    assert "A byte literal counts ⌊len/64⌋ + 1 nodes" in spec and "⌈len/64⌉ + 1 nodes" not in spec.replace("corrected from ⌈len/64⌉ + 1", "")
    for n in (0, 1, 63, 64, 65, 127, 128, 1000):
        assert S(Lit(b"a" * n)).size == 1 + n // 64 + 1   # the sort's own node plus the literal's


# ---- review 22: big numbers from short cells are charged by their size -------------------------------

def _steps_and_time(path, claim):
    import time
    from reality4 import readers as R, kernel as K
    from reality4.syntax import parse_line
    store = R.Store([path], [])
    store.begin_program()
    ck = K.Checker(store)
    h = helpers.sha(path)
    out = []
    for ln, text in enumerate([f"file f = sha256:{h}", "let t = tsv(f)", f"claim {claim}"], start=1):
        store.begin()
        t0 = time.perf_counter()
        ck.statement(parse_line(text, ln))
        out.append((store.steps.n, time.perf_counter() - t0))
    return out[-1]


@pytest.mark.parametrize("claim", ['atleast(sample_variance(t, 1), c = 1)', 'atleast(median(t, 1), c = 0)', 'count(where(t, gt(1, c = 5)))'])
def test_r22_big_numbers_cost_steps(tmp_path, claim):
    rates = []
    for name, cells in (("plain", ["9", "1", "7", "3"]), ("big", ["9e999", "1e-999", "7e-998", "3e997"])):
        p, _ = tsv(tmp_path, name + ".tsv", ("x\n" + "".join(cells[i % 4] + "\n" for i in range(3001))).encode())
        steps, dt = _steps_and_time(p, claim)
        rates.append(dt / steps)
    assert rates[1] < 6 * rates[0], rates   # before the fix: about 27 times for the variance


# ---- review 20: SPEC 4.4's witness family: deleted with the search in exact-decision phase 7 (28 Oct 2026) ----


# ---- review 26: the soundness argument is stated with its conditions, and measured -------------------

def test_r26_no_unconditional_soundness_theorem():
    here = os.path.join(os.path.dirname(__file__), "..")
    texts = {p: open(os.path.join(here, p), encoding="utf-8").read() for p in ("SPEC.md", "DESIGN.md", "KNOWN-OPEN.md", "src/reality4/witness.py")}
    for p, t in texts.items():
        for phrase in ("no idle value can form, because", "It cannot make nonsense form.", "Soundness never depends on this section",
                       "an idle value cannot form however it is spelled"):
            assert phrase not in t, (p, phrase)
    assert "not a theorem" in texts["SPEC.md"] and os.path.exists(os.path.join(here, "tests", "test_v4_bruteforce.py"))


# ---- review 28: the Lean header says what it models -------------------------------------------------

def test_r28_lean_header_scope():
    head = open(os.path.join(os.path.dirname(__file__), "..", "metatheory", "Scope.lean"), encoding="utf-8").read().split("-/")[0]
    assert "as kernel.py does it" not in head and "does not model v4" in head and "not a proof" in head
    assert "v3's abstract scope, trace and renaming" in head and "W1/W2" in head


# ---- review 29: stale notes and texts --------------------------------------------------------------

@pytest.mark.parametrize("op,word", [("exceeds", "above"), ("below", "below"), ("atleast", "at least"), ("atmost", "at most")])
def test_r29_v001_names_the_relation_in_words(tmp_path, op, word):
    p, h = tsv(tmp_path, "f.tsv", "c\n1\n2\n3\n")
    cut = {"exceeds": 5, "below": 1, "atleast": 5, "atmost": 1}[op]
    ok, text = run(f"file f = sha256:{h}\nclaim {op}(rows(tsv(f)), c = {cut})\n", [p])
    ln = lines(text, 2)
    assert "[V001" in ln and f"the value is {word} {cut};" in ln, text


def test_r29_no_text_names_v3_and_notes_are_current():
    here = os.path.join(os.path.dirname(__file__), "..")
    src = os.path.join(here, "src", "reality4")
    for f in sorted(os.listdir(src)):
        if f.endswith(".py"):
            assert "Reality v3" not in open(os.path.join(src, f), encoding="utf-8").read(), f
    read = lambda p: open(os.path.join(here, p), encoding="utf-8").read()  # noqa: E731
    assert "Nothing here has been run on the real dataset yet" not in read("README.md") and "abad0e4" in read("README.md")
    assert "is a Phase G deliverable" not in read("SPEC.md") and "neither test was built" in read("DESIGN.md")
    assert "the count is 3 only because" not in read("tests/acceptance.py") + read("ACCEPTANCE.md")
    assert all(f"\n{n}. " in read("KNOWN-OPEN.md") for n in (10, 11, 12, 13, 14)) and "S0280" in read("KNOWN-OPEN.md")


# ---- envmatrix: a relative --python path (the interpreter runs with cwd "/") ------------------------

@pytest.mark.skipif(os.name != "posix", reason="tools/envmatrix.py uses resource (POSIX only)")
def test_envmatrix_relative_python(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("envmatrix", os.path.join(os.path.dirname(__file__), "..", "tools", "envmatrix.py"))
    em = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(em)
    import sys
    monkeypatch.chdir(os.path.dirname(os.path.dirname(sys.executable)))
    rel = os.path.join(os.path.basename(os.path.dirname(sys.executable)), os.path.basename(sys.executable))
    p, h = tsv(tmp_path, "f.tsv", "c\n1\n")
    prog = tmp_path / "p.rl"
    prog.write_text(f"file f = sha256:{h}\nclaim rows(tsv(f)) is 1\n")
    rc, out, err = em.run(rel, [str(prog), "--files", p], {})
    assert rc == 0 and b"formed" in out, (rc, out, err)


# ---- taste call 1 (BB's call on Patsak's behalf, 2026-10-26): onsets past the run's end ----------

def test_call1_onset_after_end_is_realitys_own_rule(tmp_path):
    ok, text = _bids(tmp_path, "claim count(participants(bids(d)))", events="onset\tduration\n10\t1\n")   # 5 x 2 s = 10 s
    assert "B30" in text and "Reality's own rule" in text and "does not fix one reading" not in text, text
    ok, text = _bids(tmp_path, "claim count(participants(bids(d)))", events="onset\tduration\n9.5\t1\n")
    assert "formed" in lines(text, 2), text
    import csv
    reg = {r["id"]: r for r in csv.DictReader(open(os.path.join(os.path.dirname(__file__), "..", "bids", "REGISTER-1.0.1.tsv"), encoding="utf-8"), delimiter="\t")}
    assert reg["S0412"]["class"] == "reality-call" and reg["S0412"]["codes"] == "B30" and not reg["S0412"]["decision"]


# ---- taste call 2 (BB's call on Patsak's behalf, 2026-10-26): CR LF in BIDS TSVs ------------------

def test_call2_crlf_bids_tsv_is_realitys_own_call(tmp_path):
    ok, text = _bids(tmp_path, "claim count(participants(bids(d)))", events="onset\tduration\r\n1\t1\r\n")
    assert "formed" in lines(text, 2), text
    ok, text = _bids(tmp_path, "claim count(participants(bids(d)))", events="onset\tduration\r\n1\t1\n")
    assert "mixed line ends" in text and "formed" not in lines(text, 2), text
    import csv
    reg = {r["id"]: r for r in csv.DictReader(open(os.path.join(os.path.dirname(__file__), "..", "bids", "REGISTER-1.0.1.tsv"), encoding="utf-8"), delimiter="\t")}
    assert reg["S0145"]["class"] == "reality-call" and "CR LF" in reg["S0145"]["note"] and "Reality's own call" in reg["S0145"]["note"]


# ---- taste call 5 (BB's call on Patsak's behalf, 2026-10-26): one number grammar, no leading zeros -

@pytest.mark.parametrize("cell", ["010", "00", "-01", "00.5", "01e1"])
def test_call5_leading_zero_refuses_where_read_as_number(tmp_path, cell):
    p, h = tsv(tmp_path, "f.tsv", f"a\tb\n{cell}\tx\n1\ty\n")
    for claim in ("number(cell(t, 1, 1))", "sum(t, 1)", "count(where(t, gt(1, c = 0)))"):
        ok, text = run(f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {claim}\n", [p])
        assert "[V005" in lines(text, 3), (claim, text)
    ok, text = run(f"file f = sha256:{h}\nclaim cell(tsv(f), 1, 1)\n", [p])
    assert f'= "{cell}"' in lines(text, 2), text     # the bytes are still stated


def test_call5_one_grammar_with_json():
    from reality4 import readers as R
    for s in ("0", "-0", "0.5", "10", "1e05", "-0.0"):
        assert R.decimal(s) is not None and R.parse_json(s.encode(), "x") == R.decimal(s), s
    for s in ("00", "007", "-01", "00.5", "01e1"):
        assert R.decimal(s) is None, s
        with pytest.raises(R.Refusal):
            R.parse_json(s.encode(), "x")


def test_call5_bids_onset_with_leading_zero(tmp_path):
    ok, text = _bids(tmp_path, "claim count(participants(bids(d)))", events="onset\tduration\n01\t1\n")
    assert "B06 x" in text and "onset must be a number" in text and "formed" not in lines(text, 2), text


# ---- taste call 6 (BB's call on Patsak's behalf, 2026-10-26): '|' in CSV and ',' in TSV are bytes --

def test_call6_other_files_delimiters_are_bytes(tmp_path):
    p, h = tsv(tmp_path, "p.csv", "a\n1|2\n")
    q, k = tsv(tmp_path, "c.tsv", "a\n1,5\n")
    ok, text = run(f"file p = sha256:{h}\nfile c = sha256:{k}\nclaim cell(csv(p), 1, 1)\nclaim cell(tsv(c), 1, 1)\n"
                   "claim number(cell(tsv(c), 1, 1))\n", [p, q])
    assert '= "1|2"' in lines(text, 3) and '= "1,5"' in lines(text, 4) and "[V005" in lines(text, 5), text
    s, m = tsv(tmp_path, "s.csv", "a\n1;2\n")
    ok, text = run(f"file s = sha256:{m}\nclaim cell(csv(s), 1, 1)\n", [s])
    assert "[T009" in lines(text, 2), text
    pr = "/workspace/team/research/principle-nonsense-unformable.md"
    if os.path.exists(pr):   # the principle lives on the box only
        t = open(pr, encoding="utf-8").read()
        assert "'|' in CSV and ',' in TSV are bytes" in t and os.path.exists(pr.replace(".md", ".pre-amendment-2026-10-26-delimiters.md"))


# ---- taste call 3 (BB's call on Patsak's behalf, 2026-10-26): README in derivatives/ and sourcedata/ -

@pytest.mark.parametrize("d", ["derivatives", "sourcedata"])
def test_call3_folder_readme_binds_when_the_manifest_holds_files_there(tmp_path, d):
    claim = "claim count(participants(bids(d)))"
    ok, text = _bids(tmp_path, claim, extra={f"{d}/x/out.txt": "a\n"})
    assert "B01" in text and f"{d}/ holds files but no {d}/README" in text and "formed" not in lines(text, 2), text
    ok, text = _bids(tmp_path, claim, extra={f"{d}/x/out.txt": "a\n", f"{d}/README": "about\n"})
    assert "formed" in lines(text, 2), text
    root = bidsfix.mini(str(tmp_path / "empty"))
    os.makedirs(os.path.join(root, d, "fmriprep", "sub-01", "anat"))      # folders only, as ds001734's derivatives/
    from reality4 import readers
    assert f"\t{d}/".encode() not in readers.make_manifest(root)              # the manifest omits empty folders
    md = tmp_path / "m"
    md.mkdir()
    h = helpers.manifest(root, str(md))
    ok, text = run(f"dataset d = sha256:{h}\n{claim}\n", [str(md)], [root])
    assert "formed" in lines(text, 2), text


# ---- taste call 4 (BB's call on Patsak's behalf, 2026-10-26): CHANGES under the CPAN Changes convention -

CPAN_FORMS = {
    "bids-8.1.2": "1.0.1 2015-08-27\n\n  - Fixed slice timing information.\n\n1.0.0 2015-08-17\n\n  - Initial release.\n",
    "cpan-synopsis": "Revision history for perl module Foo::Bar\n\n0.02 2009-07-17\n\n - Added more foo() tests\n\n0.01 2009-07-16\n\n - Initial release\n",
    "cpan-basic": "0.01 2009-07-16\n - Initial release\n",
    "cpan-groups": "Revision history for perl module Foo::Bar\n\n0.03 2009-07-18\n\n [Important Security Information]\n - This release fixes critical bug RT #1234\n\n"
                   " [Other Changes]\n - Added some feature\n\n0.02 2009-07-17\n\n - Added more foo() tests\n\n0.01 2009-07-16T19:20:30+01:00\n\n - Initial release\n",
    "cpan-separator": "0.01 - 2013-12-11 \n - Simple Change\n - This is a very very very long\n   change line\n",
    "cpan-release-note": "0.01 2013-04-01 Codename: April Fool\n\n  - First Release\n",
    "dotted-v": "v1.2.3_4 2020-01-01\n - x\n", "decimal-underscore": "1.23_04 2020-01\n - x\n", "no-date": "1.0 Not Released\n - x\n",
    "crlf": "1.0 2020-01-01\r\n - x\r\n", "time-without-T": "1.0 2020-01-01 10:00Z\n - x\n",
}
CPAN_REFUSES = {
    "v1.2 2020-01-01\n - x\n": "B31", "1.23_04_05 2020-01-01\n - x\n": "B31", "1. 2020-01-01\n - x\n": "B31", "1.0\n - x\n": "B31",
    "": "B31", "1.0 2020-01-01\n": "B31", "1.0 2020-01-01\r\n - x\n": "B31", "1.2.1000 2020-01-01\n - x\n": "B31",
    "1.0 2020-02-30\n - x\n": "B30", "1.0 2020-01-01T10:00\n - x\n": "B30", "1.0 2020-13\n - x\n": "B30",
    "1.0 2020-01-01\n- x\n": "B30", "1.0 2020-01-01\n [group\n - x\n": "B30", "1.0 2020-01-01\n [group] \n - x\n": "B30",
    "1.1 2020-01-02\n1.0 2020-01-01\n - x\n": "B30", "1.0 \u2014 2020-01-01\n - x\n": "B30", "1.2_1000 2020-01-01\n - x\n": "B30",
}


def test_call4_ds001734_changes_bytes_form():
    from reality4.bids101 import changes
    import hashlib
    data = open(os.path.join(os.path.dirname(__file__), "data", "ds001734-box", "CHANGES"), "rb").read()
    assert hashlib.sha256(data).hexdigest() == "362a1f073c0fa2b7e3532286532cb7999b447710242ae94a4da348c9b72d20c4"
    assert b"1.0.0\t2019-02-07\n\n\t- Initial snapshot\n" in data and b"Fix license \n" in data   # tab separator, blank lines, tab indent, trailing space
    assert changes(data.decode("utf-8")) is None


@pytest.mark.parametrize("name", sorted(CPAN_FORMS))
def test_call4_bids_and_cpan_examples_form(name):
    from reality4.bids101 import changes
    assert changes(CPAN_FORMS[name]) is None


@pytest.mark.parametrize("text,code", sorted(CPAN_REFUSES.items()))
def test_call4_malformed_or_ambiguous_changes_refuse(text, code):
    from reality4.bids101 import changes
    r = changes(text)
    assert r and r[0] == code and ("S0235" in r[1] or "Reality's own call" in r[1]), (text, r)


def test_call4_changes_in_a_dataset(tmp_path):
    ok, text = _bids(tmp_path, "claim count(participants(bids(d)))", extra={"CHANGES": "1.0 2020-02-30\n - x\n"})
    assert "B30" in text and "formed" not in lines(text, 2), text
    ok, text = _bids(tmp_path, "claim count(participants(bids(d)))", extra={"CHANGES": "v1.2 2020-01-01\n - x\n"})
    assert "B31" in text and "formed" not in lines(text, 2), text
    ok, text = _bids(tmp_path, "claim count(participants(bids(d)))", extra={"CHANGES": CPAN_FORMS["bids-8.1.2"]})
    assert "formed" in lines(text, 2), text
