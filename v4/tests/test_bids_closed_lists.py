"""H5 (checker B run, 25 Oct 2026): the open lists of RULES-1.0.1.md closed from the 1.0.1 text.

B21's number-valued keys (sections 8.4, 8.9.1), B10's "required with fieldmap data" (8.4, 8.9),
IntendedFor targets (8.9), phenotype file names (8.11), README/CHANGES with a byte-order mark
(8.1). Datasets under data/bidsamb/ are copies of checker-b-run/bidsamb/ (made by checker B's
probes); the rest are built with bidsfix.mini."""
import os
import re

import pytest

import bidsfix
import helpers

HERE = os.path.dirname(os.path.abspath(__file__))
AMB = os.path.join(HERE, "data", "bidsamb")
FMAP_IMG = bidsfix.nifti1((2, 2, 2))


def bcodes(text):
    return re.findall(r"(B\d\d) x\d+", text)


def run_amb(tmp_path, name):
    md = tmp_path / "m"
    md.mkdir()
    root = os.path.join(AMB, name)
    h = helpers.manifest(root, str(md))
    return helpers.run(f'dataset d = sha256:{h}\nclaim volumes(recording(bids(d), "01", "x", "1"))\n', [str(md)], [root])


@pytest.mark.parametrize("name", ["MultibandAccelerationFactor", "NumberShots", "ParallelReductionFactorInPlane", "PartialFourier"])
def test_number_keys_of_1_0_1_refuse_a_string(tmp_path, name):
    ok, text = run_amb(tmp_path, name)
    assert not ok and bcodes(text) == ["B21"], text
    assert "section 8.4" in text


@pytest.mark.parametrize("name", ["DwellTime", "SliceThickness", "H5_delay"])
def test_keys_not_in_1_0_1_are_not_number_checked(tmp_path, name):
    """DelayTime, DwellTime and SliceThickness do not occur in the 1.0.1 text: no overcorrection."""
    ok, text = run_amb(tmp_path, name)
    assert ok and ": formed: VolumeCount[" in text, text


def test_echo_time_banana_refuses(tmp_path):
    ok, text = run_amb(tmp_path, "H5_echo")
    assert not ok and bcodes(text) == ["B21"], text


@pytest.mark.parametrize("name,ok_expected", [("H7_bom", True), ("H8_pheno5", True), ("H8_pheno6", True),
                                               ("A5_noptsv", True), ("A6_b15same", True), ("base", True)])
def test_checker_b_ambiguity_datasets(tmp_path, name, ok_expected):
    """H7: a README with a UTF-8 BOM is UTF-8 (8.1), accepted. H8: phenotype/x.tsv is a phenotype
    file (8.11 gives no length rule). A5: no participants.tsv is allowed (8.11 "Optional: Yes").
    A6: two files in one folder setting a key to EQUAL values: v3 refused (B15); in v4 this is a
    choice point (SPEC 8.3, register S0133) whose two readings give the same value, so it forms.
    Different values refuse B30 (test_bids.py)."""
    ok, text = run_amb(tmp_path, name)
    assert ok is ok_expected, text


@pytest.mark.parametrize("key", ["NumberShots", "PartialFourier", "FlipAngle", "MagneticFieldStrength",
                                 "NumberOfVolumesDiscardedByUser", "TotalReadoutTime", "InversionTime",
                                 "ParallelReductionFactorInPlane", "MultibandAccelerationFactor",
                                 "NumberOfVolumesDiscardedByScanner", "EffectiveEchoSpacing"])
def test_every_listed_key_must_be_a_number(tmp_path, key):
    ok, text = _check(tmp_path, task_json='{"TaskName": "x", "RepetitionTime": 2, "%s": "banana"}' % key)
    assert not ok and bcodes(text) == ["B21"], text
    ok, text = _check(tmp_path / "n", task_json='{"TaskName": "x", "RepetitionTime": 2, "%s": 2}' % key)
    assert ok, text


def test_misspelt_example_key_is_not_checked(tmp_path):
    """Section 8.4.1's example writes "MultibandAccellerationFactor"; 1.0.1 defines no such key."""
    ok, text = _check(tmp_path, task_json='{"TaskName": "x", "RepetitionTime": 2, "MultibandAccellerationFactor": "x"}')
    assert ok, text


def _check(tmp_path, **kw):
    os.makedirs(tmp_path, exist_ok=True)
    root = bidsfix.mini(str(tmp_path / "ds"), **kw)
    md = tmp_path / "m"
    md.mkdir()
    h = helpers.manifest(root, str(md))
    return helpers.run(f"dataset d = sha256:{h}\nclaim count(participants(bids(d)))\n", [str(md)], [root])


def _fmap(sub="01", intended=None, mag_json=None):
    body = '{"EchoTime1": 0.006, "EchoTime2": 0.007%s}' % (
        "" if intended is None else ', "IntendedFor": ' + intended)
    out = {f"sub-{sub}/fmap/sub-{sub}_phasediff.json": body,
           f"sub-{sub}/fmap/sub-{sub}_phasediff.nii": FMAP_IMG,
           f"sub-{sub}/fmap/sub-{sub}_magnitude1.nii": FMAP_IMG}
    if mag_json is not None:
        out[f"sub-{sub}/fmap/sub-{sub}_magnitude1.json"] = mag_json
    return out


def test_fieldmap_without_intended_for_requires_the_keys(tmp_path):
    """A fieldmap with no IntendedFor may correspond to any scan of its subject (8.9 makes the
    field optional and does not say): its subject's BOLD images need PED, EES, EchoTime."""
    ok, text = _check(tmp_path, extra=_fmap())
    assert not ok and bcodes(text) == ["B10"], text


def test_fieldmap_names_its_scan(tmp_path):
    ok, text = _check(tmp_path, extra=_fmap(intended='"func/sub-01_task-x_bold.nii"'))
    assert not ok and bcodes(text) == ["B10"], text
    full = '{"TaskName": "x", "RepetitionTime": 2, "EchoTime": 0.03, "EffectiveEchoSpacing": 0.0005, "PhaseEncodingDirection": "j"}'
    ok, text = _check(tmp_path / "ok", task_json=full, extra=_fmap(intended='"func/sub-01_task-x_bold.nii"'))
    assert ok, text


def test_fieldmap_for_another_scan_does_not_require_the_keys(tmp_path):
    """sub-01's fieldmap names only an anat image: the BOLD images are not its corresponding scans."""
    extra = _fmap(intended='"anat/sub-01_T1w.nii"')
    extra["sub-01/anat/sub-01_T1w.nii"] = FMAP_IMG
    ok, text = _check(tmp_path, extra=extra)
    assert ok, text


@pytest.mark.parametrize("intended", ['"func/sub-01_task-x_events.tsv"', '"func/sub-01_task-y_bold.nii"',
                                      '["func/sub-01_task-x_bold.nii", 3]', '[]', '"../sub-02/func/sub-02_task-x_bold.nii"'])
def test_intended_for_names_a_scan_of_the_subject(tmp_path, intended):
    full = '{"TaskName": "x", "RepetitionTime": 2, "EchoTime": 0.03, "EffectiveEchoSpacing": 0.0005, "PhaseEncodingDirection": "j"}'
    ok, text = _check(tmp_path, task_json=full, extra=_fmap(intended=intended))
    assert not ok and bcodes(text) == ["B12"], text


def test_intended_for_on_a_magnitude_image_is_checked(tmp_path):
    full = '{"TaskName": "x", "RepetitionTime": 2, "EchoTime": 0.03, "EffectiveEchoSpacing": 0.0005, "PhaseEncodingDirection": "j"}'
    ok, text = _check(tmp_path, task_json=full, extra=_fmap(intended='"func/sub-01_task-x_bold.nii"',
                                                            mag_json='{"IntendedFor": "func/nothing.nii"}'))
    # v4: the two IntendedFor sources are a choice point (S0495, S0510); since O7 (27 Oct 2026) it compares the BOLD
    # images each reading covers, and here both cover the one task-x scan (nothing.nii is no scan), so no B30;
    # the bad path is still B12
    assert not ok and bcodes(text) == ["B12"], text


@pytest.mark.parametrize("rel,expect", [("phenotype/x.tsv", None), ("phenotype/.tsv", "B17"), ("phenotype/x.csv", "B17"),
                                        ("phenotype/a/x.tsv", "B17"), ("phenotype/acds_adult.tsv", None)])
def test_phenotype_names(tmp_path, rel, expect):
    """8.11: phenotype/<measurement_tool_name>.tsv; the text gives no length or character rule
    (its own example is acds_adult), so any non-empty name directly in phenotype/ is one."""
    ok, text = _check(tmp_path, extra={rel: "participant_id\tq\nsub-01\t1\n"})
    if expect is None:
        assert ok, text
    else:
        assert not ok and bcodes(text) == [expect], text


@pytest.mark.parametrize("name", ["README", "CHANGES"])
def test_bom_readme_is_utf8(tmp_path, name):
    ok, text = _check(tmp_path, extra={name: b"\xef\xbb\xbf" + (b"1.0 2020-01-01\n - hello\n" if name == "CHANGES" else b"hello\n")})   # CHANGES: the CPAN grammar too
    assert ok, text
    ok, text = _check(tmp_path / "bad", extra={name: b"\xffhello\n"})
    assert not ok and bcodes(text) == ["B18"], text


@pytest.mark.parametrize("files", [("magnitude1.nii",), ("magnitude2.nii", "magnitude1.nii"), ("phasediff.nii",),
                                   ("phasediff.json",)])
def test_case1_fieldmap_needs_phasediff_and_magnitude1_images(tmp_path, files):
    """8.9.1 case 1: a phase difference image and at least magnitude1. A lone magnitude image or a
    lone phasediff refuses (B12); a lone magnitude JSON is not a fieldmap (no rule)."""
    full = '{"TaskName": "x", "RepetitionTime": 2, "EchoTime": 0.03, "EffectiveEchoSpacing": 0.0005, "PhaseEncodingDirection": "j"}'
    extra = {f"sub-01/fmap/sub-01_{f}": (FMAP_IMG if f.endswith(".nii") else '{"EchoTime1": 0.006, "EchoTime2": 0.007}') for f in files}
    ok, text = _check(tmp_path, task_json=full, extra=extra)
    assert not ok and "B12" in bcodes(text), text


def test_lone_magnitude_json_is_no_fieldmap(tmp_path):
    ok, text = _check(tmp_path, extra={"sub-01/fmap/sub-01_magnitude1.json": "{}"})
    assert ok, text
