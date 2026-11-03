"""Phase G: the copied reproducers that stop at B01 (KNOWN-OPEN, "Copied reproducers that now stop
at B01"), re-tested at their own point. Taste call 2 makes a root README binding, so each copy
without one refuses B01/B00 before its line's point. The copies stay byte-identical; here each
dataset is copied to a temporary folder with a README added, its manifest is rewritten, and the
program's dataset hash is replaced (and, where named, one edit is made), so the line reaches the
point it was written for."""
import hashlib
import os
import re
import shutil

import pytest

from helpers import HERE
from reality4 import readers as R
from reality4.kernel import check

REP = os.path.join(HERE, "repros")
BOX = os.path.join(HERE, "data", "ds001734-box")


def roots_in(d):
    return [dp for dp, _, fns in os.walk(d) if "dataset_description.json" in fns]


def rebuilt(tmp_path, rel, edits=()):
    """The verdict lines of the copied program `rel`, on its datasets with a README added."""
    top = os.path.join(REP, rel.split("/")[0])
    prog = open(os.path.join(REP, rel), "rb").read()
    mans = {}
    for dp, _, fns in os.walk(top):
        for fn in fns:
            b = open(os.path.join(dp, fn), "rb").read()
            if b.startswith((R.MANIFEST_MAGIC + "\n").encode()):
                mans[hashlib.sha256(b).hexdigest()] = b
    md = tmp_path / "m"
    md.mkdir()
    roots = []
    for h in dict.fromkeys(re.findall(rb"dataset \w+ = sha256:([0-9a-f]{64})", prog)):
        man = R.parse_manifest(mans[h.decode()], h.decode())
        src = next(r for r in roots_in(top) if all(os.path.isfile(os.path.join(r, *q.split("/"))) and R.sha256_file(os.path.join(r, *q.split("/")))[0] == eh for q, (eh, _) in man.items()))
        nr = tmp_path / ("r" + h[:8].decode())
        for q in man:
            dst = nr.joinpath(*q.split("/"))
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(os.path.join(src, *q.split("/")), dst)
        assert "README" not in man
        (nr / "README").write_bytes(b"A copied review dataset; README added in Phase G.\n")
        data = R.make_manifest(str(nr))
        nh = hashlib.sha256(data).hexdigest()
        (md / (nh + ".manifest")).write_bytes(data)
        prog = prog.replace(h, nh.encode())
        roots.append(str(nr))
    for a, b in edits:
        assert a in prog, a
        prog = prog.replace(a, b)
    ok, out = check(prog, R.Store([top, str(md), BOX], sorted(roots + [BOX])))
    return {int(ln[5:].split(":", 1)[0]): ln.split(": ", 1)[1] for ln in out if ln.startswith("line ")}


def test_argon_02_an_idle_bids_let_changes_nothing(tmp_path):
    got = rebuilt(tmp_path, "argon/02-store-cache-outside-factor-and-idle-let.rl")
    assert 4 not in got   # the let forms (a let prints no line)
    assert got[3] == got[5] == "formed: RowCount[TSV[#1]] = 1 (Exact)", got


def test_argon_13_two_acquisitions_are_named_by_acq(tmp_path):
    got = rebuilt(tmp_path, "argon/13-bids-acq-rec-and-events-overcorrections.rl")
    assert got[2].startswith("refused [V004") and "sub-01 task-rest;" in got[2], got   # acq is part of the name
    for acq in (b"ap", b"pa"):
        got = rebuilt(_sub(tmp_path, acq), "argon/13-bids-acq-rec-and-events-overcorrections.rl", [(b'"rest"))', b'"rest", acq("' + acq + b'")))')])
        assert got[2].startswith("formed: VolumeCount[") and f"task rest acq {acq.decode()}]" in got[2] and got[2].endswith("= 10 (Exact)"), got


def _sub(tmp_path, name):
    p = tmp_path / name.decode()
    p.mkdir()
    return p


def test_argon_18_recorded_comparisons_need_the_unit_and_are_labelled(tmp_path):
    got = rebuilt(tmp_path, "argon/18-recorded-precision-quasi-label-and-comparisons.rl")
    assert got[3].startswith("refused [U004") and got[4].startswith("refused [U004"), got
    got = rebuilt(_sub(tmp_path, b"s"), "argon/18-recorded-precision-quasi-label-and-comparisons.rl",
                  [(b"4.070999999)", b"4.070999999 s)"), (b"4.071000001)", b"4.071000001 s)")])
    # call 6: a Recorded value compares as recorded and says so
    assert got[3].endswith("c = 4.070999999 s] holds of the recorded value"), got
    assert got[4].endswith("c = 4.071000001 s] holds of the recorded value"), got


def test_argon_extra_e2_lookalike_acq_labels_refuse_k003(tmp_path):
    got = rebuilt(tmp_path, "argon-extra/fx/e2.rl")
    assert got[3] == "formed: RowCount[Participants[BIDS-1.0.1[#1: 1 subjects, 6 files] from #2]] = 1 (Exact)", got
    assert got[4].startswith("refused [K003") and '"01" and "O1"' in got[4], got
    got = rebuilt(_sub(tmp_path, b"a"), "argon-extra/fx/e2.rl", [(b'"x"))', b'"x", acq("01")))')])
    assert got[4].startswith("refused [K003"), got


def test_argon_extra_e11_tr_in_milliseconds(tmp_path):
    got = rebuilt(tmp_path, "argon-extra/fx/e11.rl")
    assert got[2].endswith("is recorded as 0.72 s (Recorded[s])"), got


def test_argon_extra_e12_scientific_notation_in_events(tmp_path):
    got = rebuilt(tmp_path, "argon-extra/fx/e12.rl")
    assert got[2].endswith("= 4 (Exact)"), got
    got = rebuilt(_sub(tmp_path, b"o"), "argon-extra/fx/e12.rl",
                  [(b'claim volumes(recording(bids(d), "01", "x"))', b'claim onset(recording(bids(d), "01", "x"), 1)')])
    assert got[2].endswith("is recorded as 0.015 s (Recorded[s])"), got


def test_opus55max_05_the_manifest_cannot_select_part_of_a_dataset(tmp_path):
    got = rebuilt(tmp_path, "opus55max/05-manifest-selection.rl")
    assert got[4].startswith("formed: Count[Participants[") and got[4].endswith("= 2 (Exact)"), got
    for n in (6, 7):   # a participants row whose folder the manifest leaves out
        assert got[n].startswith("refused [B00") and "B11 x1" in got[n], got
    for n in (9, 10):  # IntendedFor naming a run the manifest leaves out
        assert got[n].startswith("refused [B00") and "B12 x1" in got[n], got


def test_opus55max_20_run_1_reads_run_1s_events(tmp_path):
    got = rebuilt(tmp_path, "opus55max/20-check2-not-independent.rl")
    assert "task x run 1]" in got[2] and got[2].endswith("is recorded as 1.5 s (Recorded[s])"), got   # run 2's is 8.75


def test_opus55max_23_nifti2_tr_is_consistent(tmp_path):
    got = rebuilt(tmp_path, "opus55max/23-nifti2-tr-float32.rl")
    assert got[2].endswith("is recorded as 0.8 s (Recorded[s])"), got
