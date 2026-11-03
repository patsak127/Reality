"""The BIDS 1.0.1 reader, rule by rule (bids/RULES-1.0.1.md), on small made-up datasets."""
import os
import re

import pytest

import bidsfix
import helpers
from reality4 import bids101


def ds(tmp_path, **kw):
    root = bidsfix.mini(str(tmp_path / "ds"), **kw)
    md = tmp_path / "m"
    md.mkdir()
    return str(md), root, helpers.manifest(root, str(md))


def check(tmp_path, body, **kw):
    md, root, h = ds(tmp_path, **kw)
    return helpers.run(f"dataset d = sha256:{h}\nlet b = bids(d)\n" + body, [md], [root])


def codes(text):
    """Refusal codes in order; refusals that only repeat an earlier refused name (N003) are dropped."""
    return [c for c in re.findall(r"^line \d+: refused \[(\w+),", text, re.M) if c != "N003"]


def bcodes(text):
    return re.findall(r"(B\d\d) x\d+", text)


def test_mini_forms(tmp_path):
    ok, text = check(tmp_path, 'claim count(participants(b)) is 2\nclaim tr(recording(b, "01", "x")) is 2 s\n'
                     'claim onset(recording(b, "02", "x"), 2) is 7.25 s\nclaim volumes(recording(b, "01", "x")) is 5\n')
    assert ok, text


def test_nii_gz_and_extra_files(tmp_path):
    ok, text = check(tmp_path, 'claim volumes(recording(b, "01", "x"))\n', ext="nii.gz",
                     extra={"KEYS.txt": "anything", "code/run.py": "x", "sub-01/notes.txt": "n" })
    assert ok, text


def test_unrecognised_file_in_a_datatype_folder_refuses(tmp_path):
    """Patsak's call 3: 1.0.1 does not say whether sub-01/func/odd_name.nii is an extra file or a
    misnamed BIDS file, so the dataset is refused rather than one reading picked."""
    ok, text = check(tmp_path, "claim count(participants(b))\n", extra={"sub-01/func/odd_name.nii": "junk"})
    assert codes(text) == ["B00"] and bcodes(text) == ["B17"], text


@pytest.mark.parametrize("kw,expect", [
    (dict(extra={"dataset_description.json": '{"BIDSVersion": "1.0.1"}'}), ["B01"]),
    (dict(extra={"task-x_bold.json": "{"}), ["B03", "B08"]),
    (dict(extra={"participants.tsv": 'participant_id\tgroup\nsub-01\t"a"\nsub-02\tb\n'}), ["B04"]),
    (dict(extra={"sub-02/func/sub-02_task-x_events.tsv": "onset\tduration\r1\t1\n"}), ["B04"]),
    (dict(extra={"sub-02/func/sub-02_task-x_bold.nii": bidsfix.nifti1((2, 2, 2, 5), tr=2.0)[:-1]}), ["B05"]),
    (dict(events="duration\tonset\n2\t1\n"), ["B06"]),
    (dict(events="onset\tduration\n1\t0\n"), ["B06"]),
    (dict(events="onset\tduration\n1\tn/a\n"), ["B06"]),
    (dict(drop=["sub-02/func/sub-02_task-x_bold.nii"]), ["B07"]),
    (dict(extra={"sub-01/func/sub-01_task-x_bold.nii.gz": bidsfix.gzip_stored(bidsfix.nifti1((2, 2, 2, 5), tr=2.0))}), ["B07"]),
    (dict(task_json='{"TaskName": "x"}'), ["B08"]),
    (dict(task_json='{"RepetitionTime": 2}'), ["B08"]),
    (dict(task_json='{"TaskName": "y z", "RepetitionTime": 2}'), ["B08"]),
    (dict(task_json='{"TaskName": "x", "RepetitionTime": 2.5}'), ["B09"]),
    (dict(extra={"sub-01/func/sub-01_task-x_bold.nii": bidsfix.nifti1((2, 2, 2, 5), tr=2.0, units=2)}), ["B09"]),
    (dict(extra={"sub-01/func/sub-01_task-x_bold.nii": bidsfix.nifti1((2, 2, 2, 5), tr=2000.0, units=18)}), None),
    (dict(task_json='{"TaskName": "x", "RepetitionTime": 2, "PhaseEncodingDirection": "y"}'), ["B10"]),
    (dict(extra={"sub-01/fmap/sub-01_phasediff.json": '{"EchoTime1": 0.006, "EchoTime2": 0.007}'}), ["B12"]),
    (dict(extra={"participants.tsv": "participant_id\tgroup\nsub-01\ta\nsub-01\tb\nsub-02\tc\n"}), ["B11"]),
    (dict(extra={"participants.tsv": "participant_id\tgroup\nsub-01\ta\n"}), ["B11"]),
    (dict(extra={"participants.tsv": "group\tparticipant_id\na\t01\nb\tsub-02\n"}), ["B11"]),
    (dict(extra={"sub-01/func/sub-01_task-x_run-1_bold.json": '{"TaskName": "x"}',
                 "sub-01/func/sub-01_task-x_acq-a_bold.json": '{"RepetitionTime": 3}',
                 "sub-01/func/sub-01_task-x_acq-b_bold.json": '{"RepetitionTime": 4}'}), None),
    (dict(extra={"sub-01/sub-01_task-x_bold.json": '{"RepetitionTime": 2}',
                 "sub-01/sub-01_acq-a_bold.json": '{"RepetitionTime": 4}',
                 "sub-01/func/sub-01_task-x_acq-a_bold.nii": bidsfix.nifti1((2, 2, 2, 5), tr=2.0),
                 "sub-01/func/sub-01_task-x_acq-a_events.tsv": "onset\tduration\n1\t1\n"}), ["B30"]),
])
def test_conformance_rules(tmp_path, kw, expect):
    ok, text = check(tmp_path, "claim count(participants(b))\n", **kw)
    if expect is None:
        assert ok, text
    elif expect[0].startswith("B"):
        assert codes(text) == ["B00"] and bcodes(text) == expect, text
        assert "whole-dataset conformance" in text
    else:
        assert codes(text) == expect, text


def test_inheritance_lower_level_wins(tmp_path):
    ok, text = check(tmp_path, 'claim tr(recording(b, "01", "x")) is 3 s\nclaim tr(recording(b, "02", "x")) is 2 s\n',
                     extra={"sub-01/func/sub-01_task-x_bold.json": '{"RepetitionTime": 3}',
                            "sub-01/func/sub-01_task-x_bold.nii": bidsfix.nifti1((2, 2, 2, 5), tr=3.0)})
    assert ok, text
    assert "from #3" in text


@pytest.mark.parametrize("rel", ["sub-01/ses-1/func/sub-01_ses-1_task-x_bold.nii", "sub-01/dwi/sub-01_dwi.nii",
                                 "sub-01/fmap/sub-01_epi.nii", "sub-01/func/sub-01_task-x_physio.tsv.gz",
                                 "sub-01/sub-01_scans.tsv", "task-x_events.tsv"])
def test_unimplemented_kinds_refuse_the_dataset(tmp_path, rel):
    ok, text = check(tmp_path, "claim count(participants(b))\n", extra={rel: "x"})
    assert codes(text) == ["B14"], text


def test_lookalike_subject_labels(tmp_path):
    ok, text = check(tmp_path, 'claim volumes(recording(b, "O1", "x"))\nclaim count(participants(b))\n', subjects=("01", "O1"))
    assert codes(text) == ["K003", "K003"], text


def test_recording_lookup(tmp_path):
    ok, text = check(tmp_path, 'claim volumes(recording(b, "01", "x", "1"))\nclaim volumes(recording(b, "03", "x"))\n'
                     'claim volumes(recording(b, "01", "y"))\nclaim volumes(recording(b, "0-1", "x"))\n')
    assert codes(text) == ["V004", "V004", "V004", "K001"], text


def test_acq_is_part_of_the_recording_name(tmp_path):
    """A recording is named by all its entities: without acq() the run-less, acq-less file is meant;
    acq("b") names the other one; an acq label no file has names nothing."""
    img = bidsfix.nifti1((2, 2, 2, 5), tr=2.0)
    ok, text = check(tmp_path, 'claim volumes(recording(b, "01", "x"))\nclaim volumes(recording(b, "01", "x", acq("b")))\n'
                     'claim volumes(recording(b, "01", "x", acq("c")))\nclaim volumes(recording(b, "01", "x", acq("b"), acq("b")))\n',
                     extra={"sub-01/func/sub-01_task-x_acq-b_bold.nii": img,
                            "sub-01/func/sub-01_task-x_acq-b_events.tsv": "onset\tduration\n1\t1\n"})
    assert codes(text) == ["V004", "S004"], text
    assert "sub 01 task x acq b" in text


def test_no_participants_file(tmp_path):
    ok, text = check(tmp_path, "claim count(participants(b))\n", participants=False)
    assert codes(text) == ["V007"], text


def test_three_dimensional_bold_has_no_volume_count(tmp_path):
    ok, text = check(tmp_path, 'claim volumes(recording(b, "01", "x"))\n',
                     extra={"sub-01/func/sub-01_task-x_bold.nii": bidsfix.nifti1((2, 2, 2), tr=2.0)},
                     events="onset\tduration\n0.5\t1\n")   # inside the one 2 s volume (B30 otherwise)
    assert codes(text) == ["V008"], text


def test_extra_cells_and_participant_id(tmp_path):
    ok, text = check(tmp_path, 'claim extra(participant(b, "02"), "group") is "z"\nclaim extra(participant(b, "02"), 1)\n'
                     'claim count(where(participants(b), eq("participant_id", "sub-01")))\n', groups={"02": "z"})
    assert codes(text) == ["S006"], text
    assert 'formed: ExtraCell[Participant[Participants[BIDS-1.0.1[#1: 2 subjects, 8 files] from #2], sub-02], col 2] = "z"' in text
    assert 'participant_id = "sub-01"' in text


def test_classify():
    assert bids101.classify("README") == ("root", "README")
    assert bids101.classify("T1w.json")[0] == "meta"
    assert bids101.classify("task-MGT_bold.json")[0] == "meta"
    assert bids101.classify("sub-001/func/sub-001_task-MGT_run-01_events.tsv")[0] == "events"
    assert bids101.classify("sub-001/func/sub-002_task-MGT_run-01_events.tsv") == ("unknown", None)
    assert bids101.classify("sub-001/func/sub-001_run-01_task-MGT_bold.nii.gz") == ("unknown", None)
    assert bids101.classify("sub-001/func/sub-001_task-M-G_bold.nii.gz") == ("unknown", None)
    assert bids101.classify("derivatives/sub-001/func/sub-001_task-MGT_bold.nii.gz") == ("extra", None)


def test_nearest_float_per_nifti_version():
    """B09 compares in the header's own float width (finding B09: NIfTI-2 stores float64)."""
    from fractions import Fraction
    assert bids101.nearest(Fraction(1), 1) == 1
    assert bids101.nearest(Fraction(72, 100), 1) == Fraction(0.7200000286102295)
    assert bids101.nearest(Fraction(72, 100), 2) == Fraction(0.72)
