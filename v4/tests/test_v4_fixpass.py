"""Fix pass of 26-27 Oct 2026 (FIX-BRIEF.md): regression tests for the breaks the Argon v4 run found
(argon/ASSESSMENT.md R1-R6, W1, W2). Each test is built from Argon's repro (argon/sub, argon/scratch)."""
import hashlib

import helpers  # noqa: F401 (puts src on the path)
from reality4 import kernel as K, readers as R, witness as W


def run_mem(files, prog):
    """Check prog against a dataset made of `files` ({path: bytes}) held in memory; {h} in prog is
    the manifest's hash. Returns (ok, the output without the #k lines)."""
    blobs = {hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (R.MANIFEST_MAGIC + "\n" + "".join(f"{hashlib.sha256(files[p]).hexdigest()}\t{len(files[p])}\t{p}\n"
                                             for p in sorted(files, key=lambda p: p.encode("utf-8")))).encode("utf-8")
    mh = hashlib.sha256(man).hexdigest()
    blobs[mh] = man
    st = W.MemStore(blobs)
    st.begin_program()
    ok, out = K._check(prog.replace("{h}", mh).encode("utf-8"), st)
    return ok, "\n".join(ln for ln in out if not ln.startswith("  #"))


def line(text, n):
    return [ln for ln in text.split("\n") if ln.startswith(f"line {n}:")][0]


EV = b"onset\tduration\n1.5\t2\n4.0\t1\n7.0\t1\n"
ONE = {"dataset_description.json": b'{"Name": "m", "BIDSVersion": "1.0.1"}', "README": b"ok\n",
       "participants.tsv": b"participant_id\nsub-01\n", "task-x_bold.json": b'{"TaskName": "x", "RepetitionTime": 2}',
       "sub-01/func/sub-01_task-x_run-01_bold.nii": W._nii((2, 2, 2, 5), 2.0),
       "sub-01/func/sub-01_task-x_run-01_events.tsv": EV}
REC = 'dataset d = sha256:{h}\nlet r = recording(bids(d), "01", "x", "01")\n'


# ---- R2: S012 counts every use of a BIDS recorded value, widened or not (SPEC 5.3) ---------------

def test_r2_unwidened_and_widened_tr_refuse_s012():   # argon/scratch/bb/b4.rl
    ok, text = run_mem(ONE, REC + "claim exceeds(tr(r), c = 1 s)\nclaim exceeds(widen(tr(r), tolerance = 0.5 s), c = 1 s)\n")
    assert not ok and "[S012" in line(text, 3) and "[S012" in line(text, 4), text


def test_r2_onset_and_duration_uses_are_counted():
    for fn in ("onset", "duration"):
        ok, text = run_mem(ONE, REC + f"claim {fn}(r, 1) is {'1.5' if fn == 'onset' else '2'} s\n"
                           f"claim exceeds(widen({fn}(r, 1), tolerance = 0.2 s), c = 0.5 s)\n")
        assert not ok and "[S012" in line(text, 3) and "[S012" in line(text, 4), (fn, text)


def test_r2_controls_still_form():   # one tolerance per value; two different rows are two values
    ok, text = run_mem(ONE, REC + "claim exceeds(widen(tr(r), tolerance = 0.5 s), c = 1 s)\n"
                       "claim below(widen(tr(r), tolerance = 0.5 s), c = 3 s)\nclaim onset(r, 1) is 1.5 s\n"
                       "claim exceeds(widen(onset(r, 2), tolerance = 1 s), c = 2 s)\n")
    assert ok, text


# ---- R1: a BIDS aggregate is identified by its dataset and the paths it reads, not file hashes ---

PC = dict(ONE)
del PC["sub-01/func/sub-01_task-x_run-01_bold.nii"], PC["sub-01/func/sub-01_task-x_run-01_events.tsv"]
PC["participants.tsv"] = b"participant_id\tgroup\nsub-01\tcontrol\nsub-02\tpatient\nsub-03\tpatient\n"
for _s, _v in (("01", 5), ("02", 6), ("03", 7)):   # three events files with the same bytes (argon/sub/patctl.py)
    PC[f"sub-{_s}/func/sub-{_s}_task-x_bold.nii"] = W._nii((2, 2, 2, _v), 2.0)
    PC[f"sub-{_s}/func/sub-{_s}_task-x_events.tsv"] = EV
GROUP = 'recordings(b, "x", where(participants(b), eq("group", "{g}")))'


def test_r1_patient_minus_control_is_an_interval():   # argon/sub/patctl.py, argon/sub/pc.rl
    P, C = (f'widen(sum({GROUP.format(g=g)}, "events"), tolerance = 1)' for g in ("patient", "control"))
    ok, text = run_mem(PC, f"dataset d = sha256:{{h}}\nlet b = bids(d)\nlet pat = {P}\nlet ctl = {C}\n"
                       "claim difference(pat, ctl)\nclaim exceeds(difference(pat, ctl), c = 2)\n")
    assert line(text, 5).endswith("lies within [1, 5] (Interval)"), text
    assert "[V006" in line(text, 6), text   # [1, 5] lies on both sides of 2


def test_r1_tsv_analog_agrees():   # the control Argon ran: the same numbers as a plain TSV
    t = b"g\tv\np\t3\np\t3\nc\t3\n"
    h = hashlib.sha256(t).hexdigest()
    st = W.MemStore({h: t})
    st.begin_program()
    ok, out = K._check((f'file f = sha256:{h}\nlet a = widen(sum(where(tsv(f), eq(1, "p")), 2), tolerance = 1)\n'
                        'let z = widen(sum(where(tsv(f), eq(1, "c")), 2), tolerance = 1)\nclaim difference(a, z)\n').encode(), st)
    assert out[0].endswith("lies within [1, 5] (Interval)"), out


def test_r1_every_rset_aggregate_and_count_by_paths():
    """sum/mean/max/min over recordings of each quantity, and count(), over two groups whose files
    have the same bytes: never one value (no S012 across groups, no cancelling); one group spelled
    two ways is one value (S012 when its tolerances differ)."""
    for q in ('"events"', '"volumes"', '"tr"'):
        for fn in ("sum", "mean", "max", "min"):
            a, b = (f"{fn}({GROUP.format(g=g)}, {q})" for g in ("patient", "control"))
            u = " s" if q == '"tr"' else ""
            ok, text = run_mem(PC, f"dataset d = sha256:{{h}}\nlet b = bids(d)\nlet a = {a}\nlet c = {b}\n"
                               f"claim widen(a, tolerance = 1{u})\nclaim widen(c, tolerance = 2{u})\n")
            assert ok, (fn, q, text)
    same = 'recordings(b, "x", where(participants(b), ne("group", "control")))'
    for fn, q in (("sum", '"events"'), ("count", None)):
        x, y = (f"{fn}({r}, {q})" if q else f"{fn}({r})" for r in (GROUP.format(g="patient"), same))
        z = f'{fn}({GROUP.format(g="control")}, {q})' if q else f'{fn}({GROUP.format(g="control")})'
        ok, text = run_mem(PC, f"dataset d = sha256:{{h}}\nlet b = bids(d)\nclaim widen(difference({x}, {z}), tolerance = 1)\n"
                           f"claim widen(difference({y}, {z}), tolerance = 2)\n")
        assert "[S012" in line(text, 3) and "[S012" in line(text, 4), (fn, text)


# ---- R3: W2's file-slot form (SPEC 4.3): a file that cancels out of the answer is idle -----------

def files_run(tmp_path, tables, body):
    """tables: {name: tsv text}; body uses the names. Returns (ok, text)."""
    head, paths = "", []
    for n, t in tables.items():
        p, h = helpers.tsv(tmp_path, n + ".tsv", t)
        head, paths = head + f"file {n} = sha256:{h}\n", paths + [p]
    return helpers.run(head + body, paths)


def test_r3_a_slot_that_cancels_refuses(tmp_path):   # ASSESSMENT R3, first program
    ok, text = files_run(tmp_path, {"t1": "c\na\nb\n", "t2": "x\n1\n2\n3\n"},
                         'claim difference(difference(rows(tsv(t1)), rows(tsv(t2))), difference(count(where(tsv(t1), eq(1, "a"))), rows(tsv(t2)))) is 1\n')
    assert not ok and "[S008" in line(text, 3) and "W2" in line(text, 3), text


def test_r3_a_minus_a_minus_b_refuses_and_names_the_idle_file(tmp_path):   # ASSESSMENT R3, second program
    ok, text = files_run(tmp_path, {"f1": "v\n999999\n", "f2": "v\n42\n"},
                         "let a = number(cell(tsv(f1), 1, 1))\nlet b = number(cell(tsv(f2), 1, 1))\n"
                         "claim difference(a, difference(a, b)) is 42\nclaim difference(a, b)\n")
    h1 = helpers.sha(str(tmp_path / "f1.tsv"))
    assert "[S008" in line(text, 5) and f"the file sha256:{h1}" in line(text, 5), text
    assert "formed" in line(text, 6), text   # both files bear on a - b


def test_r3_slot_rule_is_renaming_invariant(tmp_path):
    """The slot is named by its hash, and slots are searched in hash order (SPEC 4.4 item 10)."""
    outs = []
    for a, b in (("f1", "f2"), ("zz", "aa")):
        d = tmp_path / a
        d.mkdir()
        ok, text = files_run(d, {a: "v\n999999\n", b: "v\n42\n"},
                             f"claim difference(number(cell(tsv({a}), 1, 1)), difference(number(cell(tsv({a}), 1, 1)), number(cell(tsv({b}), 1, 1))))\n")
        outs.append(text)
    assert outs[0] == outs[1] and "[S008" in outs[0], outs


def test_r3_multi_file_claims_still_form(tmp_path):
    ok, text = files_run(tmp_path, {"f1": "v\n7\n", "f2": "v\n42\n", "t": "g\tx\na\t1\nb\t2\n"},
                         "claim exceeds(difference(number(cell(tsv(f2), 1, 1)), number(cell(tsv(f1), 1, 1))), c = 30)\n"
                         'claim difference(sum(where(tsv(t), eq(1, "a")), 2), number(cell(tsv(f1), 1, 1)))\n'
                         "claim difference(rows(tsv(t)), rows(tsv(f1)))\n")
    assert ok, text


# ---- R4: a CHANGES Version line needs a Date (SPEC 8.5, taste call 4's strict grammar) -------------

import pytest  # noqa: E402

R4_NOT_A_DATE = {"BANANA": "B31", "Aug 27, 2015": "B31", "UnknownFooBar": "B31", "": "B31",   # no Date: no Version line
                 "2015-8-27": "B30", "2015/08/27": "B30", "2015-08-2710:00Z": "B30", "20150827": "B30"}   # a shorter date + glued note


@pytest.mark.parametrize("date,code", sorted(R4_NOT_A_DATE.items()))
def test_r4_a_version_line_without_a_date_does_not_conform(date, code):   # argon/sub/3d5d-122.py, 3d5d-124.py
    from reality4.bids101 import changes
    r = changes(f"1.0.1 {date}\n - x\n")
    assert r and r[0] == code, (date, r)
    ok, text = run_mem({**ONE, "CHANGES": f"1.0.1 {date}\n - x\n".encode()}, "dataset d = sha256:{h}\nclaim count(participants(bids(d)))\n")
    assert not ok and f"{code} x1" in text, text


@pytest.mark.parametrize("date", ["2015-08-27", "2015-08-27 Codename: x", "2015-08-27, x", "2015", "2015-08-27 10:00Z",
                                  "2015-08-27T10:00:00+01:00", "Unknown", "Unknown Release Date", "Not Released yet", "Development"])
def test_r4_dates_and_no_date_words_still_conform(date):
    from reality4.bids101 import changes
    assert changes(f"1.0.1 {date}\n - x\n") is None, date


def test_r4_a_preamble_line_that_starts_with_a_number_is_preamble():   # argon/sub/3d5d-124.py, first two cases
    from reality4.bids101 import changes
    assert changes("108 subjects in this dataset\n\n1.0.0 2020-01-01\n  - Initial release\n") is None
    assert changes("2020 Changelog for study\n\n1.0.0 2020-01-01\n  - Initial release\n") is None


# ---- R5: a sub-<label> folder whose label is not a label refuses B17 (S0628) ----------------------

@pytest.mark.parametrize("folder", ["sub-02-bad", "sub-03_bad", "sub-"])
def test_r5_bad_subject_label_folder_refuses_b17(folder):   # ASSESSMENT R5
    ok, text = run_mem({**ONE, f"{folder}/func/{folder}_task-x_bold.nii": b"not a nifti"},
                       "dataset d = sha256:{h}\nclaim count(participants(bids(d)))\n")
    assert not ok and "B17 x1" in text and "S0628" in text, text


def test_r5_other_top_level_folders_are_still_extra():
    ok, text = run_mem({**ONE, "code/run.sh": b"x\n", "subjects/notes.txt": b"x\n"}, "dataset d = sha256:{h}\nclaim count(participants(bids(d)))\n")
    assert ok, text


# ---- R6: manifest reading is n log n and charged; W2's witness steps are charged (SPEC 4.5) -------

def test_r6_deep_manifest_path_is_linear_and_charged():   # argon/scratch/probe_quad.py
    import time
    took = []
    for n in (25_000, 200_000):
        rel = "a/" * n + "b"
        data = f"{R.MANIFEST_MAGIC}\n{'0' * 64}\t1\t{rel}\n".encode()
        st = R.Steps()
        t = time.perf_counter()
        assert list(R.parse_manifest(data, "m", st)) == [rel]
        took.append(time.perf_counter() - t)
        assert st.n >= len(data)   # charged per byte, before the work
    assert took[1] < 40 * max(took[0], 1e-3), took   # 8x the bytes; quadratic was 64x (6.3 s at 25 000 on the box)


def test_r6_manifest_folder_clash_still_found():
    ok = f"{R.MANIFEST_MAGIC}\n{'0' * 64}\t1\ta-b\n{'0' * 64}\t1\ta.c\n{'0' * 64}\t1\ta/x\n".encode()
    assert list(R.parse_manifest(ok, "m")) == ["a-b", "a.c", "a/x"]
    for paths in (["a", "a-b", "a/x"], ["a/b", "a/b/c"], ["x/a", "x/a.d", "x/a/b"]):
        data = (R.MANIFEST_MAGIC + "\n" + "".join(f"{'0' * 64}\t1\t{p}\n" for p in paths)).encode()
        try:
            R.parse_manifest(data, "m")
            raise AssertionError(paths)
        except R.Refusal as e:
            assert e.code == "M002" and "both a file and a folder" in e.msg, (paths, e.msg)


def test_r6_store_skips_a_manifest_past_the_file_bound(tmp_path, monkeypatch):
    p = tmp_path / "m.tsv"
    p.write_bytes(f"{R.MANIFEST_MAGIC}\n{'0' * 64}\t1\tx\n".encode())
    assert R.Store([str(p)]).hints
    monkeypatch.setattr(R, "MAX_TEXT_FILE", 10)
    assert not R.Store([str(p)]).hints   # no statement could read it (R003), so it is not parsed at start


def test_r6_w2_witness_steps_are_charged(monkeypatch):
    t = b"g\tv\na\t1\nb\t2\n"
    h = hashlib.sha256(t).hexdigest()
    budgets, charged = [], []
    ev, chk = W.evaluate, W.check

    def evaluate(cls, expr, names, a, budget, lets=None, held=0, pre=None):   # (H03) held: the program's memory at the statement; (B0304) pre
        out = ev(cls, expr, names, a, budget, lets, held, pre)
        budgets.append(budget[0])
        return out

    def check(checker, expr):
        before = checker.store.steps.n
        budgets.clear()
        try:
            chk(checker, expr)
        finally:
            charged.append((checker.store.steps.n - before, budgets[-1]))
    monkeypatch.setattr(W, "evaluate", evaluate)
    monkeypatch.setattr(W, "check", check)
    st = W.MemStore({h: t})
    ok, out = K._check(f'file f = sha256:{h}\nclaim sum(where(tsv(f), ne(1, "a"), ne(1, "b")), 2)\n'.encode(), st)
    assert ok and charged and charged[0][0] == charged[0][1] > 0, (charged, out)   # every witness step, W1's and W2's


# ---- W1: no component of a path under --root (or --files) may be a symlink or a junction ----------

import os  # noqa: E402
import sys  # noqa: E402


def _linked_root(tmp_path):
    """root/real/a.tsv, root/linked -> ../outside (secret.tsv), root/real/flink.tsv -> ../../outside/secret.tsv,
    and a hand-written manifest naming all three (argon/scratch/bb/lnk)."""
    out, root = tmp_path / "outside", tmp_path / "root"
    (root / "real").mkdir(parents=True)
    out.mkdir()
    (out / "secret.tsv").write_bytes(b"s\n1\n")
    (root / "real" / "a.tsv").write_bytes(b"a\n1\n2\n")
    helpers.symlink(str(out), str(root / "linked"))
    helpers.symlink(str(out / "secret.tsv"), str(root / "real" / "flink.tsv"))
    hs, ha = helpers.sha(str(out / "secret.tsv")), helpers.sha(str(root / "real" / "a.tsv"))
    man = f"{R.MANIFEST_MAGIC}\n{hs}\t4\tlinked/secret.tsv\n{ha}\t6\treal/a.tsv\n{hs}\t4\treal/flink.tsv\n".encode()
    (tmp_path / "m.tsv").write_bytes(man)
    return root, hs, ha


def test_w1_a_symlinked_folder_under_root_is_not_followed(tmp_path):   # ASSESSMENT W1, Linux case
    root, hs, ha = _linked_root(tmp_path)
    ok, text = helpers.run(f"file s = sha256:{hs}\nfile a = sha256:{ha}\nclaim rows(tsv(s))\nclaim rows(tsv(a))\n",
                           [str(tmp_path / "m.tsv")], [str(root)])
    assert "[F001" in line(text, 1) and "formed" in line(text, 4), text   # the linked folder and the linked file: one rule


def test_w1_manifest_and_files_skip_linked_folders(tmp_path):
    root, hs, ha = _linked_root(tmp_path)
    assert R.make_manifest(str(root)).decode().split("\n")[1:-1] == [f"{ha}\t6\treal/a.tsv"]
    assert set(R.Store([str(root)]).by_hash) == {ha}


@pytest.mark.skipif(sys.platform != "win32", reason="NTFS junctions exist only on Windows")
def test_w1_a_junction_under_root_is_not_followed(tmp_path):   # ASSESSMENT W1, argon/scratch/probe6.py, probe7.py
    import subprocess
    out, root = tmp_path / "outside", tmp_path / "root"
    out.mkdir()
    root.mkdir()
    (out / "secret.tsv").write_bytes(b"s\n1\n")
    subprocess.run(["cmd", "/c", "mklink", "/J", str(root / "linked_dir"), str(out)], check=True, capture_output=True)
    assert os.path.isjunction(str(root / "linked_dir")) and R.linked(str(root / "linked_dir"))
    assert b"secret" not in R.make_manifest(str(root)) and not R.Store([str(root)]).by_hash
    hs = helpers.sha(str(out / "secret.tsv"))
    (tmp_path / "m.tsv").write_bytes(f"{R.MANIFEST_MAGIC}\n{hs}\t4\tlinked_dir/secret.tsv\n".encode())
    ok, text = helpers.run(f"file s = sha256:{hs}\nclaim rows(tsv(s))\n", [str(tmp_path / "m.tsv")], [str(root)])
    assert "[F001" in line(text, 1), text


# ---- W2: a manifest's names match the folder listings byte for byte, on every file system ---------

def test_w2_names_compare_byte_exact_with_the_listing(tmp_path, monkeypatch):   # ASSESSMENT W2, argon/scratch/probe5.py
    """A case-insensitive file system opens README when only readme is stored. Simulated here: the
    file opens as README, but the folder's listing holds readme, as NTFS would list it."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "README").write_bytes(b"hello\n")
    h = helpers.sha(str(root / "README"))
    (tmp_path / "m.tsv").write_bytes(f"{R.MANIFEST_MAGIC}\n{h}\t6\tREADME\n".encode())
    prog = f"file r = sha256:{h}\nclaim size(r)\n"
    ok, text = helpers.run(prog, [str(tmp_path / "m.tsv")], [str(root)])
    assert ok, text   # README stored as README: found
    real = os.listdir
    monkeypatch.setattr(R.os, "listdir", lambda p: [n.lower() for n in real(p)] if p == os.fsencode(str(root)) else real(p))
    ok, text = helpers.run(prog, [str(tmp_path / "m.tsv")], [str(root)])
    assert not ok and "[F001" in line(text, 1), text
