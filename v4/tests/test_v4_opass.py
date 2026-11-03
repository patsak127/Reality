"""O pass of 27 Oct 2026 (fixpass/O-QUESTIONS.md, rulings at BB's leans): regression tests for the
accepted O and C items, each built from the Argon v4 repro it answers (argon/ASSESSMENT.md)."""
import hashlib

import helpers  # noqa: F401 (puts src on the path)
from reality4 import kernel as K, witness as W
from reality4_ref import ref

T = b"a\tb\tc\n1\t2\t30\n3\t4\t31\n"
H = hashlib.sha256(T).hexdigest()
HEAD = f"file f = sha256:{H}\nlet t = tsv(f)\nlet x = number(cell(t, 1, 3))\nlet y = number(cell(t, 2, 3))\n"


def check(body, blobs=None):
    st = W.MemStore(blobs or {H: T})
    st.begin_program()
    ok, out = K._check((HEAD + body).encode("utf-8"), st)
    return ok, [ln for ln in out if not ln.startswith("  #")]


def verdicts(body):
    """{line number: refusal code or 'formed'} for the claim lines of HEAD + body."""
    ok, out = check(body)
    v = {}
    for ln in out:
        if ln.startswith("line "):
            n = int(ln[5:ln.index(":")])
            v[n] = ln[ln.index("[") + 1:ln.index("[") + 5] if "refused" in ln.split(":", 1)[1][:12] else "formed"
    return v


def ref_codes(body):
    return {ln: code for ln, st, code in ref.run((HEAD + body).encode("utf-8"), {H: T}) if st == "refused"}


# ---- O9: widen of a widened value is one use of its base value, at the summed tolerance ----------

def test_o9_nested_widen_through_let_refuses_s012():   # argon/sub/32c9-120.py, 4A
    body = "let w = widen(x, tolerance = 1)\nclaim exceeds(w, c = 28.5)\nclaim below(widen(w, tolerance = 5), c = 37)\n"
    ok, out = check(body)
    assert not ok and all("[S012" in ln for ln in out if ln.startswith(("line 6:", "line 7:"))), out
    assert ref_codes(body) == {6: "S012", 7: "S012"}


def test_o9_nested_widen_inline_refuses_s012():   # argon/sub/32c9-120.py, inline; argon/scratch/p1/p5.rl
    for second in ("below(widen(widen(x, tolerance = 1), tolerance = 5), c = 37)",
                   "widen(widen(x, tolerance = 1), tolerance = 50)"):
        body = f"claim exceeds(widen(x, tolerance = 1), c = 28.5)\nclaim {second}\n"
        ok, out = check(body)
        assert not ok and sum("[S012" in ln for ln in out) == 2, out
        assert ref_codes(body) == {5: "S012", 6: "S012"}


def test_o9_widen_inside_a_difference_inside_a_widen_still_counts():
    body = ("claim exceeds(widen(x, tolerance = 1), c = 28.5)\n"
            "claim widen(difference(widen(x, tolerance = 7), y), tolerance = 2)\n")
    ok, out = check(body)
    assert not ok and sum("[S012" in ln for ln in out) == 2, out


def test_o9_same_summed_tolerance_is_one_value():   # argon/sub/32c9-120.py, self-difference
    body = "claim exceeds(widen(widen(x, tolerance = 1), tolerance = 1), c = 20)\nclaim below(widen(x, tolerance = 2), c = 40)\n"
    ok, out = check(body)
    assert ok, out
    assert ref_codes(body) == {}
    # one value, one symbol: their difference is 0 on every input, so it does not bear on the bytes (S008)
    ok, out = check("claim difference(widen(widen(x, tolerance = 1), tolerance = 1), widen(x, tolerance = 2))\n")
    assert not ok and "[S008" in out[0], out


def test_o9_nested_widen_interval_is_the_summed_widen():
    a, b = check("claim widen(widen(x, tolerance = 1), tolerance = 5)\n"), check("claim widen(x, tolerance = 6)\n")
    assert a[0] and b[0] and a[1][0].split(" lies within ")[1] == b[1][0].split(" lies within ")[1], (a, b)


# ---- O4: difference with a standard deviation refuses S006 by its sort (SPEC 7.2), whatever the bytes give

def run_one(data, body):
    h = hashlib.sha256(data).hexdigest()
    st = W.MemStore({h: data})
    st.begin_program()
    return K._check((f"file f = sha256:{h}\n" + body).encode("utf-8"), st)


def test_o4_sd_minus_mean_refuses_s006_rational_or_not():   # argon/scratch/bb/sd.rl, sd2.rl, sd3.rl
    for data in (b"v\n1\n3\n", b"v\n1\n2\n", b"v\n1\n2\n4\n"):
        ok, out = run_one(data, "claim difference(population_sd(tsv(f), 1), mean(tsv(f), 1))\n")
        assert not ok and "[S006" in out[0], (data, out)


def test_o4_every_way_a_root_reaches_difference():
    t = b"v\tw\n1\t5\n3\t7\n"   # population_sd = 1, sample_sd = sqrt(2)
    for body in ("claim difference(mean(tsv(f), 2), population_sd(tsv(f), 1))\n",
                 "let s = sample_sd(tsv(f), 1)\nclaim difference(s, mean(tsv(f), 1))\n",
                 "claim difference(widen(population_sd(tsv(f), 1), tolerance = 1), mean(tsv(f), 1))\n",
                 "claim difference(widen(widen(population_sd(tsv(f), 1), tolerance = 1), tolerance = 1), max(tsv(f), 2))\n",
                 "claim difference(population_sd(tsv(f), 1), population_sd(tsv(f), 2))\n"):
        ok, out = run_one(t, body)
        assert not ok and "[S006" in [ln for ln in out if ln.startswith("line")][-1], (body, out)


def test_o4_controls_roots_still_compare_and_variances_still_subtract():
    t = b"v\tw\n1\t5\n3\t7\n"
    ok, out = run_one(t, "claim exceeds(population_sd(tsv(f), 1), c = 0.5)\nclaim population_sd(tsv(f), 1) is 1\n"
                         "claim difference(population_variance(tsv(f), 1), population_variance(tsv(f), 2))\n")
    assert ok, out


def test_5b_a_variance_minus_a_number_that_is_not_one_refuses_s006_by_its_sort():   # Patsak's call 4, 27 Oct 14:00
    t = b"v\tw\n1\t5\n3\t7\n"
    for body in ("claim difference(population_variance(tsv(f), 1), mean(tsv(f), 2))\n",
                 "claim difference(sum(tsv(f), 2), sample_variance(tsv(f), 1))\n",
                 "claim difference(widen(population_variance(tsv(f), 1), tolerance = 1), max(tsv(f), 2))\n",
                 "claim difference(difference(sample_variance(tsv(f), 1), sample_variance(tsv(f), 2)), mean(tsv(f), 1))\n",
                 "claim difference(number(cell(tsv(f), 1, 1)), population_variance(tsv(f), 2))\n",
                 # 28 Oct 2026: a difference whose first argument is a widened variance is a variance difference too (its
                 # identity is ("Widened", base, t)); before, it was not, so this formed (variance minus mean)
                 "claim difference(difference(widen(sample_variance(tsv(f), 1), tolerance = 1), population_variance(tsv(f), 2)), mean(tsv(f), 1))\n"):
        ok, out = run_one(t, body)
        assert not ok and "[S006" in [ln for ln in out if ln.startswith("line")][-1] and "square" in out[0], (body, out)
    for body in ("claim difference(sample_variance(tsv(f), 1), widen(sample_variance(tsv(f), 2), tolerance = 1))\n",
                 "claim difference(difference(sample_variance(tsv(f), 1), sample_variance(tsv(f), 2)), population_variance(tsv(f), 1))\n",
                 # 28 Oct 2026: refused S006 before (the widened first argument's identity hid the variance)
                 "claim difference(difference(widen(sample_variance(tsv(f), 1), tolerance = 1), population_variance(tsv(f), 2)), sample_variance(tsv(f), 2))\n"):
        ok, out = run_one(t, body)
        assert not any("[S006" in ln for ln in out), (body, out)


# ---- O3: R007 only for number-shaped cells, and never decided by the order of where's conditions ----

def test_o3_the_reader_matches_the_grammar_before_any_bound():
    from reality4 import readers as R
    for s in ("e2026", "sub_e2026", "-e2026", "x1e2026", "1.e2026", "1e+", "1ee5", "01e2026"):
        assert R.decimal(s) is None, s
    for s in ("1e2026", "-1E+2026", "1" * 1001, "1." + "0" * 1000):
        try:
            R.decimal(s)
        except R.Refusal as r:
            assert r.code == "R007", s
        else:
            raise AssertionError(s)


def test_o3_condition_order_never_decides_r007():   # argon/sub/8048-74.py
    for cell, dropped, kept in ((b"sub_e2026", "formed", "V005"), (b"e2026", "formed", "V005"), (b"1e2026", "formed", "R007"),
                                (b"1" * 1001, "formed", "R007")):
        t = b"a\tb\n" + cell + b"\t-5\n10\t10\n"
        for conds in ("gt(1, c = 0), gt(2, c = 0)", "gt(2, c = 0), gt(1, c = 0)"):
            ok, out = run_one(t, f"claim count(where(tsv(f), {conds}))\n")
            assert (ok and "= 1 (Exact)" in out[0]) if dropped == "formed" else False, (cell, conds, out)
        t = b"a\tb\n" + cell + b"\t5\n10\t10\n"   # the other condition keeps the row: no reading drops it
        for conds in ("gt(1, c = 0), gt(2, c = 0)", "gt(2, c = 0), gt(1, c = 0)"):
            ok, out = run_one(t, f"claim count(where(tsv(f), {conds}))\n")
            assert not ok and f"[{kept}" in out[0], (cell, conds, out)


# ---- O6: number(extra(participant(...), col)) makes that participants column numeric for the witness

from test_v4_fixpass import ONE, REC, line, run_mem  # noqa: E402

AGE = dict(ONE)
AGE["participants.tsv"] = b"participant_id\tage\nsub-01\t25\n"
P = 'dataset d = sha256:{h}\nlet p = participant(bids(d), "01")\n'


def test_o6_number_of_an_extra_cell_forms():   # argon/scratch/probe4.py TEST 7
    ok, text = run_mem(AGE, P + 'claim number(extra(p, "age")) is 25\nclaim exceeds(number(extra(p, "age")), c = 20)\n')
    assert ok and "= 25 (Exact)" in line(text, 3) and "holds" in line(text, 4), text
    ok, text = run_mem(AGE, P + 'claim below(widen(number(extra(p, "age")), tolerance = 1), c = 30)\n')
    assert ok, text


def test_o6_controls_constant_and_idle_still_refuse():
    ok, text = run_mem(AGE, P + 'claim difference(number(extra(p, "age")), number(extra(p, "age")))\n')
    assert not ok and "[S008" in line(text, 3), text


# ---- O10: CLI usage errors exit 2 with a message; a program with no statement refuses P011 ----------

import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")


def cli(args, stdin=b"", cwd=None):
    env = dict(os.environ, PYTHONPATH=os.path.abspath(SRC))
    r = subprocess.run([sys.executable, "-m", "reality4"] + args, input=stdin, capture_output=True, env=env, cwd=cwd)
    return r.returncode, r.stdout.decode(), r.stderr.decode()


def test_o10_manifest_out_to_a_missing_folder_is_a_usage_error(tmp_path):   # argon/scratch/probe8.py TEST 14
    (tmp_path / "ds").mkdir()
    (tmp_path / "ds" / "a.tsv").write_bytes(b"a\n1\n")
    rc, out, err = cli(["manifest", str(tmp_path / "ds"), "--out", str(tmp_path / "missing" / "m.tsv")])
    assert rc == 2 and out == "" and "cannot write" in err and "no manifest written" in err and "Traceback" not in err, (rc, out, err)


def test_o10_check_without_a_program_or_with_stdin_twice_or_an_unknown_option_is_a_usage_error(tmp_path):
    p = tmp_path / "p.rl"
    p.write_bytes(b"# nothing\n")
    for args in (["check"], ["check", "--files", str(tmp_path)], ["check", "-", "-"], ["check", str(p), "--unknown"]):
        rc, out, err = cli(args, stdin=b"claim x\n")
        assert rc == 2 and out == "" and "python -m reality4 check" in err, (args, rc, out, err)


def test_o10_a_program_with_no_statement_refuses_p011():
    for prog in (b"", b"\n", b"# only a comment\n\n", b"   \n\t\n"):
        ok, out = K._check(prog, W.MemStore({}))
        assert ok is False and out[0].startswith("line 0: refused [P011") and out[-1].startswith("refused"), (prog, out)
    rc, out, err = cli(["check", "-"], stdin=b"")
    assert rc == 1 and "[P011" in out, (rc, out, err)


def test_o10_controls_still_accepted():
    ok, out = check("claim number(cell(t, 1, 1)) is 1\n")
    assert ok, out


# ---- O12: the reference implementation builds v4 SPEC 5.2's affine widen, so the two agree -----------

def test_o12_reference_cancels_one_value_with_itself_like_v4():   # test_v4_identity's program, ASSESSMENT O12
    T2 = b"g\tx\nF\t40\nF\t40\nM\t10\n"
    h = hashlib.sha256(T2).hexdigest()
    head = f'file f = sha256:{h}\nlet t = tsv(f)\nlet a = mean(where(t, eq("g", "F")), "x")\nlet b = mean(where(t, eq("g", "M")), "x")\n'
    for claim, want in (("difference(widen(a, tolerance = 1), difference(widen(a, tolerance = 1), b))", "= 10 (Exact)"),
                        ("difference(widen(a, tolerance = 1), widen(b, tolerance = 1))", "lies within [28, 32] (Interval)")):
        prog = (head + f"claim {claim}\n").encode()
        assert ref.run(prog, {h: T2})[-1] == (5, "formed", want), claim
        st = W.MemStore({h: T2})
        st.begin_program()
        ok, out = K._check(prog, st)
        assert ok and out[0].endswith(want), out


def test_o12_reference_nested_and_summed_widen_agree_with_v4():
    for body in ("claim difference(widen(widen(x, tolerance = 1), tolerance = 2), difference(widen(x, tolerance = 3), y))\n",
                 "claim difference(difference(widen(x, tolerance = 1), y), widen(x, tolerance = 1))\n"):
        r = [v for v in ref.run((HEAD + body).encode(), {H: T}) if v[0] == 5]
        ok, out = check(body)
        assert r and out[0].startswith("line 5: ") and (r[0][1] == "refused") == ("refused" in out[0][:20]), (r, out)
        if r[0][1] == "formed":
            assert out[0].endswith(r[0][2]), (r, out)


# ---- O8: a .nii.gz read for its header must be one whole gzip file (I004); valid multi-member forms ----

import gzip  # noqa: E402

NII = W._nii((2, 3, 4, 10), 1.5, data=False)


def dim4(blob):
    h = hashlib.sha256(blob).hexdigest()
    st = W.MemStore({h: blob})
    st.begin_program()
    ok, out = K._check(f"file f = sha256:{h}\nclaim dim(nifti(f), 4)\nclaim dim(nifti(f), 1)\n".encode(), st)
    return (ok, [ln for ln in out if ln.startswith("line")]), st


def test_o8_broken_streams_refuse_i004():   # argon/sub/8048-78.py, 8048-80.py
    g = gzip.compress(NII)
    crc = bytearray(g)
    crc[-8] ^= 1
    for blob in (g[:-8], g[:-10], gzip.compress(W._nii((2, 3, 4, 10), 1.5, data=True))[:-10], g + b"CORRUPT_TRAILING_GARBAGE",
                 g + b"\0\0x", bytes(crc), g + b"\x1f"):
        (ok, out), _ = dim4(blob)
        assert not ok and "[I004" in out[0] and "[I004" in out[1], (blob[-12:], out)


def test_o8_valid_streams_form():
    g = gzip.compress(NII)
    m1 = gzip.compress(NII[:200], compresslevel=0)   # member 2's magic straddles byte 65536 (argon/sub/8048-78.py)
    m1 = m1[:3] + bytes([m1[3] | 0x10]) + m1[4:10] + b"x" * (65535 - len(m1) - 1) + b"\0" + m1[10:]
    for blob in (g, g + b"\0" * 5, gzip.compress(NII[:100]) + gzip.compress(NII[100:]), m1 + gzip.compress(NII[200:])):
        (ok, out), _ = dim4(blob)
        assert ok and out[0].endswith("= 10 (Exact)") and out[1].endswith("= 2 (Exact)"), out


def test_o8_the_whole_stream_is_charged_on_every_use():
    small, big = gzip.compress(NII), gzip.compress(NII + b"\0" * (64 << 20))   # 64 MiB of zeros compress to ~64 KiB
    costs = []
    for blob in (small, big):
        h = hashlib.sha256(blob).hexdigest()
        st = W.MemStore({h: blob})
        st.begin_program()
        prog = f"file f = sha256:{h}\nclaim dim(nifti(f), 4)\n"
        steps = []
        for _ in range(2):   # the second statement reads the cached result and is charged the same
            st.begin()
            K._check(prog.encode(), st)
            steps.append(st.steps.n)
        costs.append(steps)
    assert min(costs[1]) > max(costs[0]) + (64 << 20) // 4096, costs   # 16,384 decompressed 4 KiB pages, both times


# ---- O5: a same-folder clash that a deeper sidecar overrides decides nothing (resolved values compared) --

def o5(over):
    ds = dict(ONE)
    ds["run-1_bold.json"], ds["run-01_bold.json"] = b'{"EchoTime": 0.01}', b'{"EchoTime": 0.02}'
    if over:
        ds["sub-01/func/sub-01_task-x_run-01_bold.json"] = b'{"EchoTime": 0.03}'
    return run_mem(ds, REC_TR)


REC_TR = 'dataset d = sha256:{h}\nclaim tr(recording(bids(d), "01", "x", "01"))\n'


def test_o5_overridden_root_clash_forms():   # argon/scratch/probe2.py TEST 1C (with a README)
    ok, text = o5(True)
    assert ok and "is recorded as 2 s" in line(text, 2), text


def test_o5_controls_a_clash_that_stands_still_refuses_b30():
    ok, text = o5(False)
    assert not ok and "B30" in text, text


# ---- O14: events dictionaries inherit like sidecars: same-folder clashes and run-1/run-01 are B30 --------

EVS = dict(ONE)
EVS["sub-01/func/sub-01_task-x_run-01_events.tsv"] = b"onset\tduration\tstim\n1.5\t2\ta\n4.0\t1\tb\n"
REC_ON = REC + "claim onset(r, 1)\n"


def test_o14_same_folder_dictionaries_that_differ_refuse_b30():   # argon/scratch/probe1.py TEST 1E
    ds = dict(EVS, **{"events.json": b'{"stim": {"Levels": {"b": "no"}}}', "task-x_events.json": b'{"stim": {"Levels": {"a": "yes"}}}'})
    ok, text = run_mem(ds, REC_ON)
    assert not ok and "B30" in text and "events.json" in text, text


def test_o14_run_1_dictionary_against_run_01_refuses_b30():   # argon/scratch/probe1.py TEST 1D
    ds = dict(EVS, **{"events.json": b'{"stim": {"Levels": {"a": "ok"}}}',
                      "sub-01/sub-01_task-x_run-1_events.json": b'{"stim": {"Levels": {"b": "other"}}}'})
    ok, text = run_mem(ds, REC_ON)
    assert not ok and "B30" in text and "S0265" in text, text


def test_o14_controls_equal_or_overridden_dictionaries_form():
    for extra in ({"events.json": b'{"stim": {"Levels": {"a": "x"}}}', "task-x_events.json": b'{"stim": {"Levels": {"a": "x"}}}'},
                  {"events.json": b'{"stim": {"Levels": {"a": "x"}}}', "task-x_events.json": b'{"stim": {"Levels": {"a": "y"}}}',
                   "sub-01/func/sub-01_task-x_run-01_events.json": b'{"stim": {"Levels": {"a": "z"}}}'}):
        ok, text = run_mem(dict(EVS, **extra), REC_ON)
        assert ok and "1.5 s" in line(text, 3), text


# ---- O7: the IntendedFor choice point compares what each reading decides: the BOLD images covered -------

def fmap_ds(runs, magnitude_intended=True):
    ds = {"dataset_description.json": b'{"Name": "m", "BIDSVersion": "1.0.1"}', "README": b"ok\n",
          "participants.tsv": b"participant_id\nsub-01\n",
          "task-x_bold.json": b'{"TaskName": "x", "RepetitionTime": 2, "EchoTime": 0.03, "EffectiveEchoSpacing": 0.0005, "PhaseEncodingDirection": "j"}',
          "sub-01/fmap/sub-01_phasediff.nii": W._nii((2, 2, 2), 1.0), "sub-01/fmap/sub-01_phasediff.json": b'{"EchoTime1": 0.005, "EchoTime2": 0.007}',
          "sub-01/fmap/sub-01_magnitude1.nii": W._nii((2, 2, 2), 1.0)}
    for r in runs:
        ds[f"sub-01/func/sub-01_task-x_run-{r}_bold.nii"] = W._nii((2, 2, 2, 5), 2.0)
    if magnitude_intended:
        ds["sub-01/fmap/sub-01_magnitude1.json"] = b'{"IntendedFor": "func/sub-01_task-x_run-01_bold.nii"}'
    return ds


def test_o7_readings_that_cover_the_same_scans_form():   # argon/scratch/probe8.py TEST 13
    ok, text = run_mem(fmap_ds(["01"]), REC + "claim volumes(r)\n")
    assert ok and "= 5 (Exact)" in line(text, 3), text


def test_o7_readings_that_cover_different_scans_still_refuse_b30():
    ok, text = run_mem(fmap_ds(["01", "02"]), REC + "claim volumes(r)\n")
    assert not ok and "B30" in text and "IntendedFor" in text, text


def test_o7_control_no_intendedfor_anywhere_forms():
    ok, text = run_mem(fmap_ds(["01", "02"], magnitude_intended=False), REC + "claim volumes(r)\n")
    assert ok, text


# ---- O13: a value both run readings agree on cites the sidecars of both, the most specific included ------

def tr_line(extra):
    ds = dict(ONE, **extra)
    ok, text = run_mem(ds, REC + "claim tr(r)\n")
    return ok, text, ds


def test_o13_tr_cites_the_subject_run_1_sidecar_too():   # argon/scratch/probe2.py TEST 1A (with a README)
    ok, text, ds = tr_line({"sub-01/sub-01_task-x_run-1_bold.json": b'{"RepetitionTime": 2}'})
    assert ok and "from #3, #4]" in line(text, 3), text   # the root sidecar and the subject's run-1 one


def test_o13_a_value_one_reading_alone_supplies_is_unchanged():
    ok, text, ds = tr_line({})
    assert ok and "from #3]" in line(text, 3), text


# ---- C1-C3: CHANGES lines with two readings are B30 (argon/sub/3d5d-124.py) ------------------------------

from reality4.bids101 import changes  # noqa: E402


def test_c2_non_ascii_indent_and_line_breaks_are_b30():
    for t in ("1.0.0 2020-01-01\n\u00a0- Initial\n", "1.0.0 2020-01-01\n - first\u2028unindented\n",
              "1.0.0 2020-01-01\n - a\u2029b\n", "1.0.0 2020-01-01\n - a\x85b\n", "1.0.0 2020-01-01\n - a\x0cb\n",
              "Pre\u2028amble\n1.0.0 2020-01-01\n - a\n"):
        r = changes(t)
        assert r is not None and r[0] == "B30", (t, r)


def test_c2_controls_ascii_indent_and_a_leading_bom_conform():
    for t in ("1.0.0 2020-01-01\n - Initial\n", "1.0.0 2020-01-01\n\t- Initial\n", "\ufeff1.0.0 2020-01-01\n - Initial é\n"):
        assert changes(t) is None, t


# C1: a malformed version line with a date and indented changes, above the first release.
def test_c1_malformed_version_line_with_changes_above_a_release_is_b30():
    for head in ("1.2.1000 2020-05-01", "v1.2 2020-05-01"):
        r = changes(head + "\n  - Fixed a bug\n\n1.0.0 2020-01-01\n  - Initial release\n")
        assert r is not None and r[0] == "B30" and r[1].startswith("CHANGES line 1:"), (head, r)


def test_c1_preambles_still_conform():
    for t in ("108 subjects in this dataset\n\n1.0.0 2020-01-01\n  - Initial release\n",
              "2020 Changelog for study\n\n1.0.0 2020-01-01\n  - Initial release\n",
              "v1.2 2020-05-01 is planned\n\n1.0.0 2020-01-01\n  - Initial release\n",   # no indented line under it
              "v1.2 2020-05-01\nNotes\n  - see below\n1.0.0 2020-01-01\n  - Initial release\n",   # another line between
              "Release 2020-05-01\n  - draft\n1.0.0 2020-01-01\n  - Initial release\n"):   # not version-shaped
        assert changes(t) is None, t


def test_c1_with_no_release_after_it_stays_b31():   # either reading lacks a release (test_v4_fixes pins these)
    assert changes("v1.2 2020-05-01\n  - Fixed a bug\n")[0] == "B31"


# C3: a group heading ends with the bracket matching its opening one.
def test_c3_bracket_line_whose_match_is_not_last_is_b30():
    for ln in (" [fix] handle [edge case]", " [a]]", " [a [b]", " [x] "):
        r = changes(f"1.0.0 2020-01-01\n - Initial\n{ln}\n - more\n")
        assert r is not None and r[0] == "B30" and r[1].startswith("CHANGES line 3:"), (ln, r)


def test_c3_headings_with_nested_brackets_conform():
    for ln in (" [Fixes]", " [Fixes [docs]]", " [[x]]"):
        assert changes(f"1.0.0 2020-01-01\n{ln}\n - Initial\n") is None, ln
