import os
import re

import pytest

import acceptance as A
import bidsfix
import helpers

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope="session")
def dec(tmp_path_factory):
    d = tmp_path_factory.mktemp("dec")
    p, h = helpers.tsv(d, "decisions.tsv", A.DECISIONS)
    return str(d), h


def setup(fixture, box, complete, dec, tmp_path):
    subs = {"P": A.P, "EV": A.EV, "BOX": box[2], "CMP": complete[2], "DEC": dec[1]}
    files, roots = [box[0], box[1]], [box[1]]
    if fixture == "complete":
        files, roots = [complete[0]], [complete[1]]
    elif fixture == "dec":
        files = [dec[0]]
    elif fixture.startswith("mini"):
        root = str(tmp_path / "mini")
        if fixture == "mini-1.2.0":
            bidsfix.mini(root, version="1.2.0")
        else:
            bidsfix.mini(root, version=None)
        md = str(tmp_path / "m")
        os.makedirs(md)
        subs["MINI"] = helpers.manifest(root, md)
        files, roots = [md], [root]
    return subs, files, roots


def refusal_codes(text):
    return re.findall(r"^line \d+: refused \[(\w+),", text, re.M)


@pytest.mark.parametrize("case", A.CASES, ids=[c[0] for c in A.CASES])
def test_case(case, box, complete, dec, tmp_path):
    cid, fixture, prog, expect, _ = case
    if expect == "all-refused":
        for fn in sorted(os.listdir(os.path.join(HERE, "old"))):
            if fn.startswith("narps-"):
                with open(os.path.join(HERE, "old", fn), "rb") as f:
                    ok, text = helpers.run(f.read())
                assert not ok and "formed" not in text, fn
        return
    subs, files, roots = setup(fixture, box, complete, dec, tmp_path)
    ok, text = helpers.run(prog.format(**subs), files, roots)
    if expect == "formed":
        assert ok, text
        assert "refused" not in text
    else:
        assert not ok
        assert refusal_codes(text) == expect, text
        assert "formed" not in text


def test_f3_names_its_bold_file(complete):
    """F3: the onset's sort names the BOLD file and the events file; both are read (check 2)."""
    _, text = helpers.run(A.CMP_HEAD.format(CMP=complete[2]) + "claim onset(r, 1)\n", [complete[0]], [complete[1]])
    bold = helpers.sha(os.path.join(complete[1], "sub-001", "func", "sub-001_task-MGT_run-01_bold.nii.gz"))
    assert f"sha256:{bold}" in text and f"sha256:{A.EV}" in text
    assert "is recorded as 4.071 s (Recorded[s])" in text


def test_n17_names_the_rule(box):
    _, text = helpers.run(A.BOX_HEAD.format(BOX=box[2]) + "claim count(participants(b))\n", [box[0], box[1]], [box[1]])
    assert "whole-dataset conformance" in text and "B07 x432" in text and "section 8.5" in text


def test_n17_file_level_still_forms(box):
    """Whole-dataset conformance blocks BIDS sorts only; F12's file-level wording still forms."""
    prog = A.BOX_HEAD + "file p = sha256:{P}\nclaim count(participants(b))\nclaim count(where(tsv(p), eq(2, \"equalRange\")))\n"
    ok, text = helpers.run(prog.format(BOX=box[2], P=A.P), [box[0], box[1]], [box[1]])
    assert refusal_codes(text) == ["B00", "N003"]
    assert 'formed: Count[Rows[TSV[#1] where col 2 = "equalRange"]] = 54 (Exact)' in text


def test_f12_exact_output(box):
    ok, text = helpers.run("file p = sha256:%s\nclaim rows(tsv(p))\nclaim count(where(tsv(p), eq(2, \"equalRange\")))\n" % A.P, [box[1]])
    assert text == (
        "line 2: formed: RowCount[TSV[#1]] = 108 (Exact)\n"
        f"  #1 = sha256:{A.P}\n"
        "line 3: formed: Count[Rows[TSV[#1] where col 2 = \"equalRange\"]] = 54 (Exact)\n"
        f"  #1 = sha256:{A.P}\n"
        "accepted")


def test_extra_file_is_allowed(complete):
    """KEYS.txt (an agent-added extra file at the root) does not break conformance; as a listed
    file of the dataset it must still be supplied with its hash and size."""
    import reality4.readers as R
    from reality4 import bids101
    ds = bids101.read(R.Store([complete[0]], [complete[1]]), complete[2])
    assert "KEYS.txt" in ds.manifest
    assert bids101.classify("KEYS.txt") == ("extra", None)
