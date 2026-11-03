"""Patsak's call 5: new expressions, each with must-form cases and the must-not-form cases that
come with it. No GLM or voxel claims."""
import re

import pytest

import bidsfix
import helpers

T = "id\tgroup\tage\trt\ns1\tA\t30\t0.5\ns2\tB\t41\t0.25\ns3\tA\t25\t1\ns4\tB\t41\t0.75\n"
COMP = "subject\ttrial\trt\nsub01\tt1\t0.45\nsub01\tt2\t0.5\nsub02\tt1\t0.6\nsub02\tt2\t0.7\nsub03\tt3\t0.8\n"


def codes(text):
    return re.findall(r"^line \d+: refused \[(\w+),", text, re.M)


def run(tmp_path, body, data=T):
    p, h = helpers.tsv(tmp_path, "t.tsv", data)
    return helpers.run(f"file f = sha256:{h}\nlet t = tsv(f)\n" + body, [p])


def test_at_least_at_most_counts(tmp_path):
    ok, text = run(tmp_path, 'claim atleast(count(where(t, eq("group", "A"))), c = 2)\n'
                             'claim atmost(count(where(t, eq("group", "A"))), c = 2)\n'
                             "claim atleast(rows(t), c = 4)\n")
    assert ok and "AtLeast[Count[" in text and "AtMost[" in text, text


@pytest.mark.parametrize("body,code", [
    ('claim atleast(count(where(t, eq("group", "A"))), c = 3)\n', "V001"),     # false
    ("claim atleast(rows(t), c = 0)\n", "S008"),                              # every count is >= 0
    ("claim atmost(rows(t), c = -1)\n", "V001"),                              # no count is <= -1: false on every input
    ("claim atleast(rows(t), c = 2 s)\n", "U002"),                            # a count has no unit
    ("claim atleast(rows(t))\n", "S005"),                                     # no default cutoff
])
def test_at_least_at_most_must_not_form(tmp_path, body, code):
    ok, text = run(tmp_path, body)
    assert codes(text) == [code], text


def test_count_and_share_comparisons(tmp_path):
    ok, text = run(tmp_path, 'let a = where(t, eq("group", "A"))\n'
                             "claim exceeds(count(a), c = 1)\nclaim below(share(a), c = 3/4)\n"
                             "claim atleast(share(a), c = 1/2)\nclaim difference(count(a), count(where(t, eq(\"group\", \"B\")))) is 0\n")
    assert ok, text
    assert "c = 0.75" in text   # a ratio cutoff is exact; printed as its exact decimal


@pytest.mark.parametrize("body,code", [
    ('claim exceeds(share(where(t, eq("group", "A"))), c = 1)\n', "V001"),    # no share exceeds 1: false on every input
    ('claim below(share(where(t, eq("group", "A"))), c = 2)\n', "S008"),      # every share is below 2
    ('claim exceeds(share(where(t, eq("group", "A"))), c = 1/0)\n', "P007"),  # zero denominator (call 8)
    ('claim exceeds(share(where(t, eq("group", "A"))), c = -1/2)\n', "P007"),
    ('claim share(where(t, eq("group", "A"))) is 1/2\n', "V001"),           # 2/4 is written as 2/4 (call 8)
    ('claim difference(count(t), share(where(t, eq("group", "A"))))\n', "S007"),
    ('claim difference(count(where(t, eq("group", "A"))), max(t, 3))\n', "U001"),
])
def test_count_share_must_not_form(tmp_path, body, code):
    ok, text = run(tmp_path, body)
    assert codes(text) == [code], text


def test_mean(tmp_path):
    ok, text = run(tmp_path, 'claim mean(t, "rt") is 0.625\nclaim mean(where(t, eq(2, "A")), 3) is 27.5\nclaim mean(t, "age")\n')
    assert ok and "Mean[TSV[#1], col 4] = 0.625 (Exact)" in text and "= 137/4" not in text, text
    assert "= 137/4 (Exact)" in text or "= 34.25 (Exact)" in text


@pytest.mark.parametrize("body,data,code", [
    ('claim mean(where(t, eq(2, "C")), 3)\n', T, "V003"),          # an empty set has no mean
    ("claim mean(t, 2)\n", T, "V005"),                              # not a column of decimals
    ('claim mean(t, "rt") is 0.6\n', T, "V001"),
    ("claim mean(t, 3) is 34.25 s\n", T, "U002"),
])
def test_mean_must_not_form(tmp_path, body, data, code):
    ok, text = run(tmp_path, body, data)
    assert codes(text) == [code], text


def test_composite_keys(tmp_path):
    ok, text = run(tmp_path, 'claim cell(t, key("subject", "sub01", "trial", "t2"), "rt") is "0.5"\n'
                             'claim count(where(where(t, eq("subject", "sub01")), eq("trial", "t1"))) is 1\n', COMP)
    assert ok and 'the row whose col 1 is "sub01" and col 2 is "t2"' in text, text


@pytest.mark.parametrize("body,code", [
    ('claim cell(t, key("subject", "sub01"), "rt")\n', "V004"),                        # two rows
    ('claim cell(t, key("subject", "sub01", "subject", "sub01"), "rt")\n', "V004"),    # a column twice: V004 here, W2 (S008) where one row matches
    ('claim cell(t, key("subject", "sub01", "trial"), "rt")\n', "S003"),
    ('claim cell(t, key("subject", "sub-01", "trial", "t1"), "rt")\n', "K001"),
])
def test_composite_keys_must_not_form(tmp_path, body, code):
    ok, text = run(tmp_path, body, COMP)
    assert codes(text) == [code], text


def test_composite_key_redundant_on_these_bytes_forms(tmp_path):
    # v4: idleness is structural (Patsak, 25 Oct 2026); finding 13. Either part alone picks the
    # row here, but another table could hold two sub03 rows, so neither part is idle.
    ok, text = run(tmp_path, 'claim cell(t, key("subject", "sub03", "trial", "t3"), "rt")\n', COMP)
    assert ok and 'the row whose col 1 is "sub03" and col 2 is "t3"' in text, text


def test_nested_where_composes(tmp_path):
    ok, text = run(tmp_path, 'claim count(where(where(t, eq(2, "A")), ne(3, "25"))) is 1\n')
    assert ok, text


EV = "onset\tduration\ttrial_type\n1.5\t2\tgain\n4\t2\tloss\n7.25\t2\tgain\n"


def bids(tmp_path, body, **kw):
    root = bidsfix.mini(str(tmp_path / "ds"), **kw)
    md = tmp_path / "m"
    md.mkdir()
    mh = helpers.manifest(root, str(md))
    return helpers.run(f"dataset d = sha256:{mh}\nlet b = bids(d)\nlet r = recording(b, \"01\", \"x\")\n" + body, [str(md)], [root])


def test_trials_by_trial_type(tmp_path):
    ok, text = bids(tmp_path, 'claim trials(r, "gain") is 2\nclaim events(r) is 3\nclaim atleast(trials(r, "loss"), c = 1)\n', events=EV)
    assert ok and 'where trial_type = "gain"' in text, text


@pytest.mark.parametrize("body,events,code", [
    ('claim trials(r, "Gain")\n', EV, "K002"),                              # lookalike of "gain"
    ('claim trials(r, "gain")\n', "onset\tduration\n1\t1\n", "V002"),       # no trial_type column
    ('claim trials(r, "gain") is 3\n', EV, "V001"),
    ("claim trials(r, 2)\n", EV, "S006"),
])
def test_trials_must_not_form(tmp_path, body, events, code):
    ok, text = bids(tmp_path, body, events=events)
    assert codes(text) == [code], text


def test_acq_rec_selectors(tmp_path):
    img = bidsfix.nifti1((2, 2, 2, 7), tr=2.0)
    extra = {"sub-01/func/sub-01_task-x_acq-fast_rec-mag_bold.nii": img,
             "sub-01/func/sub-01_task-x_acq-fast_rec-mag_events.tsv": "onset\tduration\n1\t1\n"}
    ok, text = bids(tmp_path, 'claim volumes(recording(b, "01", "x", acq("fast"), rec("mag"))) is 7\nclaim volumes(r) is 5\n'
                              'claim volumes(recording(b, "01", "x", acq("fast")))\n'
                              'claim volumes(recording(b, "01", "x", rec("mag"), acq("fast")))\n', extra=extra)
    assert codes(text) == ["V004"], text            # acq alone does not name the acq+rec file
    assert text.count("acq fast rec mag") == 2


def test_nifti2_tr_is_read_as_float64(tmp_path):
    import struct
    hdr = bytearray(544)
    struct.pack_into("<i", hdr, 0, 540)
    hdr[4:12] = b"n+2\x00\r\n\x1a\n"
    struct.pack_into("<2h", hdr, 12, 2, 8)
    struct.pack_into("<8q", hdr, 16, 4, 2, 2, 2, 5, 1, 1, 1)
    struct.pack_into("<8d", hdr, 104, 1.0, 1.0, 1.0, 1.0, 0.72, 0, 0, 0)
    struct.pack_into("<q", hdr, 168, 544)
    struct.pack_into("<i", hdr, 500, 10)
    img = bytes(hdr) + b"\x00" * 40
    ok, text = bids(tmp_path, "claim tr(r) is 0.72 s\nclaim volumes(r) is 5\n",
                    task_json='{"TaskName": "x", "RepetitionTime": 0.72}',
                    extra={"sub-01/func/sub-01_task-x_bold.nii": img, "sub-02/func/sub-02_task-x_bold.nii": img},
                    events="onset\tduration\n1.5\t1\n")   # inside 5 x 0.72 s (B30 otherwise)
    assert ok, text


@pytest.mark.parametrize("body,code", [
    ("claim exceeds(onset(r, 1), c = 1)\n", "U004"),          # call 6: the cutoff's unit is written
    ("claim exceeds(onset(r, 1), c = 1 ms)\n", "U002"),       # no reader gives ms
    ("claim exceeds(onset(r, 1), c = 1 furlong)\n", "U002"),
    ("claim widen(onset(r, 1), tolerance = 0.5)\n", "U004"),
])
def test_cutoff_units_are_written(tmp_path, body, code):
    ok, text = bids(tmp_path, body)
    assert codes(text) == [code], text


def test_recorded_comparison_says_recorded(tmp_path):
    # one claim per program: an exact and a widened use of one onset in one program is S012 (SPEC 5.3;
    # fix pass R2, which this test once relied on)
    for i, body in enumerate(("claim exceeds(onset(r, 1), c = 1 s)\n", "claim exceeds(widen(onset(r, 1), tolerance = 0.25 s), c = 1 s)\n")):
        (tmp_path / str(i)).mkdir()
        ok, text = bids(tmp_path / str(i), body)
        assert ok and text.count("holds of the recorded value") == 1, text
