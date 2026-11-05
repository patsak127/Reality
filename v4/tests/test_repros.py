"""Every reproducer from the v2 reviews, as a v3 regression test.

1. tests/repros/<review>/ holds each review's small reproducer files (copied unchanged from
   review-argon-v2/findings, review-argon-v2/box-repro/extra, review-opus55-v2/findings and
   review-opus55max-v2/findings; files of 300 KB or more and the 14-* folders were left out).
   EXPECTED.tsv is the verdict of every line of every program under v3, reviewed one by one
   (LOG.md and repros/README.md give the hit each one belongs to). It must not change silently.
2. Reproducers that need big or generated inputs, a subprocess environment or a changing file
   are rebuilt here in code, one test per hit.
"""
import io
import os
import re
import subprocess
import sys
import time

import pytest

import bidsfix
import helpers
from reality4 import readers as R
from reality4.kernel import check

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import run_repros  # noqa: E402


def codes(text):
    return re.findall(r"^line \d+: refused \[(\w+),", text, re.M)


def test_every_copied_reproducer_has_its_reviewed_verdict():
    # EXPECTED.tsv was reviewed with the OpenNeuro ds001734-box fixture in the store;
    # without it, programs that name its hashes refuse F001 instead of the reviewed codes.
    if not os.path.isdir(bidsfix.BOX):
        pytest.skip(bidsfix.SKIP_DS001734)
    out = io.StringIO()
    run_repros.run_all(run_repros.default_dirs(), out, full=False)
    with open(os.path.join(HERE, "repros", "EXPECTED.tsv"), encoding="utf-8") as f:
        want = f.read()
    assert out.getvalue() == want


def test_no_copied_reproducer_forms_a_known_hit():
    """The formed lines in EXPECTED.tsv are each a must-form case or a file-level claim that is
    true and printed unambiguously; none of them is one of the 17 hits. Spot-check the hit lines."""
    with open(os.path.join(HERE, "repros", "EXPECTED.tsv"), encoding="utf-8") as f:
        exp = dict(line.rstrip("\n").split("\t", 1) for line in f if "\t" in line)
    must_refuse = {
        "03-manifest-omission-n17-box-bypass.rl": "2:B00",                  # hit 2
        "02-n17-zero-subject-dataset.rl": "3:B00",                          # hit 2
        "05-duplicate-headers-in-bids-tsvs.rl": "2:B00",                    # hit 11
        "09-duplicate-onset-column.rl": "3:B00",                            # hit 11
        "06-bids-inheritance-ambiguous-precedence.rl": "2:B00",             # hit 12
        "10-sidecar-precedence.rl": "2:B00",                                # hit 12
        "11-run-index-two-recordings.rl": "2:B00",                          # hit 13 / run-1 vs run-01
        "12-phenotype-files-skipped.rl": "2:B00",                           # hit 14
        "07-bids-whole-dataset-conformance-gaps.rl": "2:B14",               # hit 15 (root events.tsv: S0132, B14 first)
        "24-lookalike-scope.rl": "3:K002",                                  # hit 16
        "11-non-ascii-lookalikes-pass.rl": "6:K002",                        # hit 17
        "22-manifest-unchecked-fields.rl": "2:M003",                        # hit 10
        "03-onset-difference-across-recordings.rl": "2:B00",                # hit 8: its copied dataset has no README (B01); test_hit08 checks U003 on the complete copy
        "10-python-runtime-limits-and-uncaught-crash.rl": "2:R007",         # hit 5
    }
    for prog, first in must_refuse.items():
        assert exp[prog].startswith(first), (prog, exp[prog])
    assert "9:S008" in exp["12-idle-parts-and-unchecked-manifest-sizes.rl"]   # hit 9: tolerance = 0
    assert "12:S012" in exp["12-idle-parts-and-unchecked-manifest-sizes.rl"]  # call 4: mixed tolerances


def test_v3_review_bids_hits_under_v4():
    """Opus 5.5 max review of v3, findings 5-11 (tests/repros/opus55max-v3/OPEN.md): each hit
    refuses with the code of its v4 rule, each control keeps its verdict, overcorrection 11 forms."""
    with open(os.path.join(HERE, "repros", "EXPECTED.tsv"), encoding="utf-8") as f:
        sec = f.read().split("#### opus55max-v3\n")[1].split("####")[0]
    exp = dict(line.split("\t", 1) for line in sec.splitlines() if "\t" in line)
    want = {
        "05-run-label-sidecar.rl": "2:B00",            # B30, S0265
        "06-magnitude-intendedfor.rl": "2:B00",        # B30, S0495/S0510
        "06b-control-no-magnitude-json.rl": "2:B00",   # B10, as v3
        "07-tasks-tsv-example.rl": "2:B14",            # sub-01/tasks.tsv, S0132
        "07b-tasks-tsv-root.rl": "2:B14",
        "09-data-dictionaries.rl": "2:B00",            # B19, phenotype dictionary
        "09b-phenotype-dictionary-alone.rl": "2:B00",  # B19, no TSV
        "09c-events-dictionary.rl": "2:B00",           # B19, events dictionary
        "10-participant-level-events.rl": "2:B14",     # S0132
        "11-events-dictionary-in-func.rl": "3:formed",
        "11b-control-events-dictionary-at-root.rl": "3:formed",
        "21g-rules-coverage.rl": "2:B00",              # B03, same as 21f at the root
    }
    for prog, first in want.items():
        assert exp[prog].startswith(first), (prog, exp[prog])


# ---- hit 1: a byte literal can never print as a file -------------------------------------

def test_hit01_literals_print_as_literals(tmp_path):
    p, h = helpers.tsv(tmp_path, "d.tsv", "id\n#1\n")
    ok, text = helpers.run(f'file f = sha256:{h}\nclaim count(where(tsv(f), eq(1, "#1"))) is 1\n'
                           f'claim count(where(tsv(f), eq(1, "@{h}"))) is 0\n'
                           f'claim count(where(tsv(f), eq(1, "@{"0" * 64}"))) is 0\n', [p])
    assert ok, text
    lines = [ln for ln in text.split("\n") if ": formed:" in ln]
    assert len(set(ln.split(": formed: ")[1] for ln in lines)) == 3      # three claims, three printed forms
    assert 'col 1 = "#1"' in text and f'col 1 = "@{h}"' in text


# ---- hit 2: a dataset name promises the whole dataset (call 1) -----------------------------

def test_hit02_partial_manifests_refuse(tmp_path, box):
    root = box[1]
    rows = []
    for rel in ("dataset_description.json", "participants.tsv"):
        with open(os.path.join(root, rel), "rb") as f:
            b = f.read()
        rows.append(f"{R.sha256_file(os.path.join(root, rel))[0]}\t{len(b)}\t{rel}")
    man = ("reality-manifest 1\n" + "\n".join(rows) + "\n").encode()
    mp = tmp_path / "m.manifest"
    mp.write_bytes(man)
    import hashlib
    mh = hashlib.sha256(man).hexdigest()
    ok, text = helpers.run(f"dataset d = sha256:{mh}\nlet b = bids(d)\n"
                           'claim count(where(participants(b), eq("group", "equalRange"))) is 54\n', [str(mp), root], [root])
    assert codes(text) == ["B00", "N003"] and "B11 x1" in text and "have no subject folder" in text


def test_hit02_bids_sort_prints_what_the_name_covers(complete):
    ok, text = helpers.run(f"dataset d = sha256:{complete[2]}\nclaim count(participants(bids(d)))\n", [complete[0]], [complete[1]])
    assert ok and "BIDS-1.0.1[#1: 108 subjects, " in text, text


# ---- hit 3: the store is pure ----------------------------------------------------------

def test_hit03_files_and_root_give_identical_verdicts(tmp_path):
    root = bidsfix.mini(str(tmp_path / "ds"))
    md = tmp_path / "m"
    md.mkdir()
    mh = helpers.manifest(root, str(md))
    ph = helpers.sha(os.path.join(root, "participants.tsv"))
    prog = (f"dataset d = sha256:{mh}\nfile p = sha256:{ph}\nclaim rows(tsv(p)) is 2\nlet unused = bids(d)\n"
            "claim rows(tsv(p)) is 2\nclaim nothing(p)\nclaim rows(tsv(p)) is 2\n")
    _, a = helpers.run(prog, [str(md), root])
    _, b = helpers.run(prog, [str(md)], [root])
    assert a == b
    assert a.count("RowCount[TSV[#1]] = 2") == 3


def test_hit03_order_of_statements_does_not_change_a_verdict(tmp_path):
    root = bidsfix.mini(str(tmp_path / "ds"))
    md = tmp_path / "m"
    md.mkdir()
    mh = helpers.manifest(root, str(md))
    claim = 'claim tr(recording(bids(d), "01", "x")) is 2 s\n'
    _, a = helpers.run(f"dataset d = sha256:{mh}\n" + claim, [str(md)], [root])
    _, b = helpers.run(f"dataset d = sha256:{mh}\nclaim count(participants(bids(d)))\nclaim bogus(d)\n" + claim, [str(md)], [root])
    la = [ln for ln in a.split("\n") if "RepetitionTime" in ln][0].split(": ", 1)[1]
    lb = [ln for ln in b.split("\n") if "RepetitionTime" in ln][0].split(": ", 1)[1]
    assert la == lb


# ---- hit 4: work is counted, not left to the machine's memory -------------------------------

def test_hit04_doubling_lets_hit_a_fixed_bound(tmp_path):
    p, h = helpers.tsv(tmp_path, "n.tsv", "x\ty\n1\t2\n")
    lets = "let a0 = number(cell(tsv(f), 1, 1))\nlet b0 = number(cell(tsv(f), 1, 2))\n"
    for i in range(40):
        lets += f"let a{i + 1} = difference(a{i}, b{i})\nlet b{i + 1} = difference(b{i}, a{i})\n"
    t0 = time.monotonic()
    ok, text = helpers.run(f"file f = sha256:{h}\n" + lets + "claim a40\n", [p])
    assert time.monotonic() - t0 < 20
    assert "R006" in text and ": formed:" not in text
    first = re.search(r"^line (\d+): refused \[R006", text, re.M).group(1)
    ok2, text2 = helpers.run(f"file f = sha256:{h}\n" + lets + "claim a40\n", [p])
    assert re.search(r"^line (\d+): refused \[R006", text2, re.M).group(1) == first


# ---- hit 5: digit limits are Reality's, not the interpreter's -------------------------------

@pytest.mark.parametrize("limit", [640, 4300, 0])
def test_hit05_interpreter_digit_limit_changes_nothing(tmp_path, limit):
    p, h = helpers.tsv(tmp_path, "l.tsv", "n\tm\n" + "9" * 999 + "\t1\n" + "9" * 1001 + "\t2\n")
    prog = (f"file f = sha256:{h}\nclaim number(cell(tsv(f), 1, 1))\nclaim number(cell(tsv(f), 2, 1))\n"
            f"claim cell(tsv(f), {'9' * 999}, 1)\nclaim cell(tsv(f), {'9' * 1001}, 1)\n")
    old = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(limit)
        ok, text = helpers.run(prog, [p])
    finally:
        sys.set_int_max_str_digits(old)
    assert codes(text) == ["R007", "V002", "R010"], text
    assert "= " + "9" * 999 + " (Exact)" in text


# ---- hit 6: output bytes do not depend on the console encoding -------------------------------

def test_hit06_output_bytes_identical_under_every_io_encoding(tmp_path):
    p, h = helpers.tsv(tmp_path, "u.tsv", "name\tv\n\u00e9t\u00e9\t1\nabc\t2\n")
    prog = tmp_path / "p.rl"
    prog.write_bytes(f"file f = sha256:{h}\nclaim significant(tsv(f))\nclaim cell(tsv(f), 1, 1)\nclaim rows(tsv(f))\n".encode())
    outs = {}
    for enc in ("utf-8", "ascii", "cp437", "cp1252", "latin-1"):
        env = dict(os.environ, PYTHONPATH=os.path.join(HERE, "..", "src"), PYTHONIOENCODING=enc, PYTHONUTF8="0")
        r = subprocess.run([sys.executable, "-m", "reality4", "check", str(prog), "--files", p], env=env, capture_output=True, timeout=120)
        outs[enc] = (r.returncode, r.stdout, r.stderr)
    assert len(set(outs.values())) == 1, outs
    rc, out, err = outs["utf-8"]
    assert rc == 1 and err == b"" and b"\r" not in out and b"RowCount[TSV[#1]] = 2" in out
    out.decode("utf-8")


# ---- hit 7: renaming cannot cross the program bound -------------------------------------

def test_hit07_renaming_keeps_the_verdict(tmp_path):
    from reality4 import syntax
    p, h = helpers.tsv(tmp_path, "r.tsv", "a\n1\n")
    n = 20000
    short = f"file f = sha256:{h}\n" + "".join(f"let a{i} = tsv(f)\n" for i in range(n)) + "claim rows(a0)\n"
    long_ = short.replace("let a", "let " + "q" * 55).replace("rows(a0)", "rows(" + "q" * 55 + "0)")
    assert len(long_) > 1_000_000 > len(short)
    assert syntax.measured_size(short) == syntax.measured_size(long_)
    _, a = helpers.run(short, [p])
    _, b = helpers.run(long_, [p])
    assert a.rsplit("\n", 2)[-2:] == b.rsplit("\n", 2)[-2:] and "RowCount[TSV[#1]] = 1" in a


# ---- hit 8: time values carry their recording ------------------------------------------

def test_hit08_times_from_two_recordings_do_not_combine(complete):
    head = (f"dataset d = sha256:{complete[2]}\nlet b = bids(d)\nlet r1 = recording(b, \"001\", \"MGT\", \"01\")\n"
            "let r2 = recording(b, \"002\", \"MGT\", \"01\")\n")
    ok, text = helpers.run(head + "claim difference(onset(r1, 1), onset(r2, 1)) is 0.02 s\n"
                           "claim exceeds(difference(onset(r1, 1), onset(r2, 1)), c = 0 s)\n"
                           "claim exceeds(difference(duration(r1, 1), onset(r2, 1)), c = -1 s)\n"
                           "claim difference(onset(r1, 2), onset(r1, 1))\n", [complete[0]], [complete[1]])
    assert codes(text) == ["U003", "U003", "U003"], text
    assert "from the first volume of BOLD #2" in text


# ---- hit 9: idle and contradictory parts --------------------------------------------------

def test_hit09_idle_parts_refuse(tmp_path):
    p, h = helpers.tsv(tmp_path, "t.tsv", "id\tg\tv\na\tA\t1\nb\tB\t2\nc\tA\t3\n")
    ok, text = helpers.run(
        f"file f = sha256:{h}\nlet t = tsv(f)\n"
        'claim count(where(t, eq(2, "A"), ne(2, "B")))\n'
        'claim count(where(t, eq(2, "A"), ne(2, "A")))\n'
        'claim count(where(t, eq(2, "A"), eq(2, "B")))\n'
        "claim widen(max(t, 3), tolerance = 0)\n"
        "claim difference(max(t, 3), max(t, 3))\n"
        'claim count(where(where(t, eq(2, "A")), eq(2, "A")))\n'
        "claim exceeds(count(t), c = -1)\nclaim below(share(where(t, eq(2, \"A\"))), c = 2)\n"
        "claim exceeds(count(t), c = 3)\n", [p])
    assert codes(text) == ["S008", "S011", "S011", "S008", "S008", "S008", "S008", "S008", "V001"], text


# ---- hit 13: run labels -------------------------------------------------------------------

def test_hit13_runless_next_to_run_refuses(tmp_path):
    img = bidsfix.nifti1((2, 2, 2, 5), tr=2.0)
    root = bidsfix.mini(str(tmp_path / "ds"), extra={"sub-01/func/sub-01_task-x_run-1_bold.nii": img,
                                                     "sub-01/func/sub-01_task-x_run-1_events.tsv": "onset\tduration\n1\t1\n"})
    md = tmp_path / "m"
    md.mkdir()
    mh = helpers.manifest(root, str(md))
    ok, text = helpers.run(f"dataset d = sha256:{mh}\nclaim volumes(recording(bids(d), \"01\", \"x\"))\n", [str(md)], [root])
    assert codes(text) == ["B00"] and "B30 x1" in text


# ---- hits 14 and 15: machine-checkable 1.0.1 rules ------------------------------------------

@pytest.mark.parametrize("extra,code", [
    ({"participants.json": "[1, 2]"}, "B03"),
    ({"participants.json": '{"nosuch": {"Description": "x"}}'}, "B19"),
    ({"T1w.json": '"just a string"'}, "B03"),
    ({"task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 2, "EchoTime": "banana"}'}, "B21"),
    ({"task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 2, "EchoTime": [0.01, "a"]}'}, "B21"),
    ({"task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 2, "SliceTiming": [0, 0.5, 1]}'}, "B10"),
    ({"task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 2, "SliceEncodingDirection": "k", "SliceTiming": [0, 2.5]}'}, "B10"),
    ({"task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 2, "PhaseEncodingDirection": ["j-"]}'}, "B10"),
    ({"sub-01/anat/sub-01_T1w.nii": bidsfix.nifti1((2, 2, 2)),
      "sub-01/anat/sub-01_T1w.nii.gz": bidsfix.gzip_stored(bidsfix.nifti1((2, 2, 2)))}, "B07"),
    ({"sub-01/fmap/sub-01_phasediff.nii": bidsfix.nifti1((2, 2, 2)), "sub-01/fmap/sub-01_magnitude1.nii": bidsfix.nifti1((2, 2, 2)),
      "sub-01/fmap/sub-01_phasediff.json": '{"EchoTime1": 0.004, "EchoTime2": 0.006, "IntendedFor": "func/sub-01_task-x_run-9_bold.nii"}',
      "task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 2, "EchoTime": 0.03, "EffectiveEchoSpacing": 0.0005, "PhaseEncodingDirection": "j-"}'}, "B12"),
    ({"phenotype/bdi.tsv": "participant_id\tscore\nsub-07\t3\n"}, "B22"),
    ({"phenotype/notes.txt": "x"}, "B17"),
    ({"README": b"\xff\xfe"}, "B18"),
    ({"participants.tsv": "participant_id\tgroup\tGroup\nsub-01\ta\ta\nsub-02\ta\ta\n"}, "B04"),
    ({"sub-01/func/sub-01_task-x_events.tsv": "onset\tduration\tstim_file\n1\t1\tpic.png\n"}, "B20"),
    ({"sub-01/func/sub-01_task-x_events.tsv": "onset\tduration\tresponse_time\n1\t1\tfast\n"}, "B06"),
    ({"task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 2}', "sub-01/sub-01_task-x_bold.json": '{"TaskName": "X"}'}, "B08"),
])
def test_hit15_rule(tmp_path, extra, code):
    root = bidsfix.mini(str(tmp_path / "ds"), extra=extra)
    md = tmp_path / "m"
    md.mkdir()
    mh = helpers.manifest(root, str(md))
    ok, text = helpers.run(f"dataset d = sha256:{mh}\nclaim count(participants(bids(d)))\n", [str(md)], [root])
    assert codes(text) == ["B00"] and re.findall(r"(B\d\d) x\d+", text) == [code], text


def test_hit14_phenotype_that_conforms_forms(tmp_path):
    root = bidsfix.mini(str(tmp_path / "ds"), extra={"phenotype/bdi.tsv": "participant_id\tscore\nsub-01\t3\n",
                                                     "phenotype/bdi.json": '{"score": {"Description": "BDI"}}'})
    md = tmp_path / "m"
    md.mkdir()
    mh = helpers.manifest(root, str(md))
    ok, text = helpers.run(f"dataset d = sha256:{mh}\nclaim count(participants(bids(d)))\n", [str(md)], [root])
    assert ok, text


def test_hit15_v2_fabricated_copy_with_two_slices_refuses(tmp_path):
    """opus55 16/17: v2's fabricated copy had 2-slice BOLD images under a 64-entry SliceTiming."""
    import shutil
    dst = str(tmp_path / "ds")
    bidsfix.complete_copy(dst)
    for dp, _, fns in os.walk(dst):
        for fn in fns:
            if fn.endswith("_bold.nii.gz"):
                with open(os.path.join(dp, fn), "wb") as f:
                    f.write(bidsfix.gzip_stored(bidsfix.nifti1((2, 2, 2, 3))))
    md = tmp_path / "m"
    md.mkdir()
    mh = helpers.manifest(dst, str(md))
    ok, text = helpers.run(f"dataset d = sha256:{mh}\nclaim onset(recording(bids(d), \"001\", \"MGT\", \"01\"), 1)\n", [str(md)], [dst])
    assert codes(text) == ["B00"] and "SliceTiming has 64 times" in text
    shutil.rmtree(dst)


def test_hit15_complete_copy_without_one_run_refuses(tmp_path, complete):
    """opus55 16: run-04 left out of the manifest while sub-001's IntendedFor still names it."""
    md, root, mh = complete
    with open(os.path.join(md, mh + ".manifest"), "rb") as f:
        lines = f.read().decode().split("\n")
    kept = [ln for ln in lines if "sub-001_task-MGT_run-04" not in ln]
    data = "\n".join(kept).encode()
    out = tmp_path / "cut.manifest"
    out.write_bytes(data)
    import hashlib
    ok, text = helpers.run(f"dataset d = sha256:{hashlib.sha256(data).hexdigest()}\nclaim count(participants(bids(d)))\n", [str(out)], [root])
    assert codes(text) == ["B00"] and "IntendedFor names" in text


# ---- check 2 reads the BOLD file it names (opus55 17, opus55max 20) ---------------------------

def test_check2_onset_reads_its_bold_file(complete, monkeypatch):
    seen = []
    orig = R.Store.nifti

    def spy(self, h, what, full):
        seen.append(h)
        return orig(self, h, what, full)
    monkeypatch.setattr(R.Store, "nifti", spy)
    ok, text = helpers.run(f"dataset d = sha256:{complete[2]}\nclaim onset(recording(bids(d), \"001\", \"MGT\", \"01\"), 1) is 4.071 s\n",
                           [complete[0]], [complete[1]])
    bold = helpers.sha(os.path.join(complete[1], "sub-001", "func", "sub-001_task-MGT_run-01_bold.nii.gz"))
    assert ok and f"sha256:{bold}" in text and bold in seen


# ---- opus55max 25: a file that changes after it was supplied ---------------------------------

def test_a_file_that_changes_after_hashing_refuses(tmp_path):
    p, h = helpers.tsv(tmp_path, "c.tsv", "id\nAAAA\n")
    st = R.Store([p], [])
    with open(p, "wb") as f:
        f.write(b"id\nBBBB\n")
    ok, out = check(f"file f = sha256:{h}\nclaim cell(tsv(f), 1, 1)\n".encode(), st)
    assert ok is False and any("[F002" in ln for ln in out) and not any("formed" in ln for ln in out)


# ---- opus55max 27: ExtraCell columns are labelled -------------------------------------------

def test_extracell_label_in_every_column_computation(tmp_path):
    root = bidsfix.mini(str(tmp_path / "ds"), extra={"participants.tsv": "participant_id\tage\nsub-01\t30\nsub-02\t41\n"})
    md = tmp_path / "m"
    md.mkdir()
    mh = helpers.manifest(root, str(md))
    ok, text = helpers.run(f"dataset d = sha256:{mh}\nlet p = participants(bids(d))\nclaim max(p, \"age\")\n"
                           "claim mean(p, 2)\nclaim count(where(p, eq(\"age\", \"30\")))\n", [str(md)], [root])
    assert ok and text.count("ExtraCell col 2") == 3, text


# ---- quadratic scans (opus55 07, opus55max 13, 14) ---------------------------------------

def test_lookalike_scan_is_linear(tmp_path):
    rows = "".join(f"k{i}\t{i}\n" for i in range(80000))
    p, h = helpers.tsv(tmp_path, "big.tsv", "id\tv\n" + rows)
    t0 = time.monotonic()
    ok, text = helpers.run(f"file f = sha256:{h}\nclaim count(where(tsv(f), eq(1, \"zz\")))\n", [p])
    assert time.monotonic() - t0 < 30
    assert "K002" in text or ok   # k1/kl-style pairs cannot occur here (digits only after k); either way it is quick


def test_bids_reader_is_not_quadratic(tmp_path):
    def build(n):
        subs = tuple(f"{i:05d}" for i in range(n))
        root = bidsfix.mini(str(tmp_path / f"ds{n}"), subjects=subs)
        md = tmp_path / f"m{n}"
        md.mkdir()
        return root, str(md), helpers.manifest(root, str(md))
    times = []
    for n in (300, 1200):
        root, md, mh = build(n)
        t0 = time.monotonic()
        ok, text = helpers.run(f"dataset d = sha256:{mh}\nclaim count(participants(bids(d)))\n", [md], [root])
        times.append(time.monotonic() - t0)
        assert ok, text[-300:]
    assert times[1] < times[0] * 4 * 2.5 + 2, times
