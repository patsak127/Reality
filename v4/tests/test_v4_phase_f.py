"""Phase F (DESIGN 4, finding 29): joins on BIDS keys and aggregates over recordings.

recordings(b, task[, sel]) is the set of BOLD recordings of a task, optionally only those whose
sub entity matches a participant_id ("sub-<label>", 1.0.1 text line 1238) in a selection of
participants(b). count(rs), and sum/mean/max/min(rs, q) with q from the closed list volumes,
events, tr, trials (with a trial type)."""
import os

import pytest

import bidsfix
import helpers

EV = "onset\tduration\ttrial_type\n1.5\t2\tgo\n7.25\t2\tstop\n9\t1\tgo\n"


def run(tmp_path, body, **kw):
    kw.setdefault("subjects", ("01", "02", "03"))
    kw.setdefault("groups", {"01": "a", "02": "b", "03": "a"})
    import tempfile
    d = tempfile.mkdtemp(dir=str(tmp_path))
    root = bidsfix.mini(os.path.join(d, "ds"), **kw)
    md = os.path.join(d, "m")
    os.mkdir(md)
    h = helpers.manifest(root, md)
    ok, text = helpers.run(f"dataset d = sha256:{h}\nlet b = bids(d)\n{body}\n", [md], [root])
    return ok, [ln for ln in text.split("\n") if ln.startswith("line ")]


def one(tmp_path, body, **kw):
    ok, lines = run(tmp_path, body, **kw)
    return ok, lines[0]


@pytest.mark.parametrize("claim", [
    'claim count(recordings(b, "x")) is 3',
    'claim count(recordings(b, "x", where(participants(b), eq("group", "a")))) is 2',
    'claim count(recordings(b, "y")) is 0',
    'claim sum(recordings(b, "x"), "volumes") is 15',
    'claim min(recordings(b, "x"), "volumes") is 5',
    'claim mean(recordings(b, "x"), "tr") is 2 s',
    'claim sum(recordings(b, "x"), "events") is 9',
    'claim max(recordings(b, "x", where(participants(b), eq("group", "b"))), "events") is 3',
    'claim sum(recordings(b, "x"), "trials", "go") is 6',
    'claim mean(recordings(b, "x", where(participants(b), eq("group", "a"))), "trials", "stop") is 1',
])
def test_forms(tmp_path, claim):
    ok, line = one(tmp_path, claim, events=EV)
    assert ok, line


def test_sorts_name_the_set_the_join_and_the_files(tmp_path):
    ok, line = one(tmp_path, 'claim max(recordings(b, "x", where(participants(b), eq("group", "b"))), "events")', events=EV)
    assert ok and line.startswith("line 3: formed: Max[BOLDRecordings[BIDS-1.0.1[#1") and ", task x, of Rows[Participants[" in line
    assert line.endswith("events from #3] = 3 (Exact)"), line


def test_tr_keeps_unit_and_recorded(tmp_path):
    ok, line = one(tmp_path, 'claim mean(recordings(b, "x"), "tr")')
    assert ok and line.endswith("is recorded as 2 s (Recorded[s])"), line
    ok, line = one(tmp_path, 'claim mean(recordings(b, "x"), "tr") is 2')
    assert not ok and "[U00" in line, line


def test_join_never_drops_a_recording_silently(tmp_path):
    """A recording whose subject has no participants row: the dataset does not conform (B11), so
    no join forms and none can leave that recording out unnoticed."""
    extra = {"sub-04/func/sub-04_task-x_bold.nii": bidsfix.nifti1((2, 2, 2, 7), tr=2.0),
             "sub-04/func/sub-04_task-x_events.tsv": EV}
    ok, lines = run(tmp_path, 'claim count(recordings(b, "x", participants(b)))', events=EV, extra=extra)
    assert not ok and "B11 x1" in lines[0], lines


def test_join_picks_by_participant_id(tmp_path):
    ok, lines = run(tmp_path, 'claim count(recordings(b, "x", where(participants(b), eq("participant_id", "sub-02")))) is 1\n'
                    'claim sum(recordings(b, "x", where(participants(b), eq("group", "b"))), "trials", "go") is 2', events=EV)
    assert ok, lines


@pytest.mark.parametrize("claim,code", [
    ('claim mean(recordings(b, "y"), "volumes")', "V003"),            # empty set
    ('claim sum(recordings(b, "x"), "bogus")', "S006"),               # not in the closed list
    ('claim sum(recordings(b, "x"), "trials")', "S003"),              # trials needs a type
    ('claim sum(recordings(b, "x"), "volumes", "go")', "S003"),
    ('claim count(recordings(b, "x", where(participants(b), eq("group", "a"), eq("group", "a"))))', "S008"),  # idle (W2)
    ('claim count(recordings(b, "x y"))', "K001"),
    ('claim count(recordings(b))', "S003"),
])
def test_refuses(tmp_path, claim, code):
    ok, line = one(tmp_path, claim, events=EV)
    assert not ok and f"[{code}," in line, line


def test_a_filter_of_every_participant_forms(tmp_path):
    """(H06, Opus 5.5 max2 review 06) overturns Phase F's S008 (v4-fixes 08): the filter bears through V007 on a
    dataset without participants.tsv, where the statement without it answers (SPEC-EXACT 2)."""
    ok, line = one(tmp_path, 'claim count(recordings(b, "x", participants(b)))', events=EV)
    assert ok and "formed" in line and "= 3" in line, line


def test_selection_from_another_table_refuses(tmp_path):
    p, h = helpers.tsv(str(tmp_path), "t.tsv", "participant_id\tg\nsub-01\ta\n")
    root = bidsfix.mini(str(tmp_path / "ds"))
    md = tmp_path / "m"
    md.mkdir()
    mh = helpers.manifest(root, str(md))
    ok, text = helpers.run(f"dataset d = sha256:{mh}\nfile f = sha256:{h}\nlet b = bids(d)\n"
                           'claim count(recordings(b, "x", where(tsv(f), eq("g", "a"))))\n', [str(md), p], [root])
    assert not ok and "[S007," in text or "[S006," in text, text


def test_let_bound_set(tmp_path):
    ok, lines = run(tmp_path, 'let rs = recordings(b, "x")\nclaim sum(rs, "volumes") is 15\nclaim count(rs) is 3', events=EV)
    assert ok, lines
