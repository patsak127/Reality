"""Authoring-controls slice: edit_me → real artifacts → checker feedback.

Restored for follow-up verify: was on 0d63b0ead14e line but absent from standalone
pack app/ (tests lived under req/tests/). Matches authoring app API on this branch.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
DEMO = HERE.parent / "demo" / "authoring_controls"
PY = sys.executable
REQ = HERE.parent
V4 = REQ.parent / "v4"
ENV = {**os.environ, "PYTHONPATH": f"{REQ / 'src'}:{V4 / 'src'}"}
QFRAME = "COMPARE ORDERINGS (EDIT ME) - question, not a claim"


@pytest.fixture()
def project(tmp_path):
    root = tmp_path / "ac"
    shutil.copytree(DEMO, root, ignore=shutil.ignore_patterns("work", "__pycache__", "*.pyc", "pack_standalone.py"))
    return root


def build(root, expect_ok=True):
    r = subprocess.run([PY, str(root / "build.py"), "--root", str(root)], capture_output=True, text=True, env=ENV)
    meta = json.loads((root / "work" / "build_meta.json").read_text())
    if expect_ok:
        assert r.returncode == 0, r.stdout + r.stderr
        assert meta.get("ok") is True
    return meta


def check(root):
    r = subprocess.run([PY, str(root / "check_run.py"), "--root", str(root)], capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


def set_control(root, frame, key, value):
    edit = json.loads((root / "edit_me.json").read_text())
    edit["frames"][frame][key]["value"] = value
    (root / "edit_me.json").write_text(json.dumps(edit, indent=2) + "\n")


def test_default_pass_bar_holds_on_playtest2_fails_playtest1(project):
    set_control(project, "EDIT ME - design controls", "log", "playtest_1.tsv")
    build(project)
    out = check(project)
    text = out["req"]["text"]
    assert "G002" in text
    assert "DOES NOT HOLD" in text

    set_control(project, "EDIT ME - design controls", "log", "playtest_2.tsv")
    build(project)
    out = check(project)
    text = out["req"]["text"]
    assert "HOLDS" in text
    assert "G002" in text


def test_lowering_bar_changes_verdict(project):
    set_control(project, "EDIT ME - design controls", "log", "playtest_1.tsv")
    set_control(project, "EDIT ME - design controls", "pass_bar", 0.8)
    build(project)
    assert "DOES NOT HOLD" in check(project)["req"]["text"]

    set_control(project, "EDIT ME - design controls", "pass_bar", 0.7)
    meta = build(project)
    frag = (project / "work" / "ledger" / "PassBar.fragment").read_text()
    assert "c = 0.7" in frag
    assert meta["artifacts"]["PassBar.fragment"]
    assert "HOLDS" in check(project)["req"]["text"]


def test_missing_log_is_truthful(project):
    set_control(project, "EDIT ME - design controls", "log", "no_such.tsv")
    meta = build(project, expect_ok=False)
    assert meta.get("ok") is False
    assert "missing log" in meta.get("error", "")
    out = check(project)
    text = out["req"]["text"]
    assert "DOES NOT HOLD" in text or "NOT CHECKED" in text or "G023" in text or "F001" in text or "refused" in text
    assert "PassBar DOES NOT HOLD" not in text or "NOT CHECKED" in text


def test_second_bar_alternative_forms(project):
    set_control(project, "ALTERNATIVES (EDIT ME)", "second_bar_enabled", 1)
    set_control(project, "ALTERNATIVES (EDIT ME)", "second_bar", 0.7)
    set_control(project, "EDIT ME - design controls", "log", "playtest_1.tsv")
    set_control(project, "EDIT ME - design controls", "pass_bar", 0.8)
    build(project)
    assert (project / "work" / "ledger" / "PassBarLoose.fragment").is_file()
    text = check(project)["req"]["text"]
    assert "DOES NOT HOLD" in text
    assert "HOLDS" in text


def test_question_optional_and_not_claim(project):
    set_control(project, QFRAME, "enabled", 1)
    set_control(project, QFRAME, "weight_mid", 0.5)
    build(project)
    assert (project / "work" / "compare.ro").is_file()
    out = check(project)
    assert "question" in out
    qtext = out["question"]["text"]
    assert "formed" in qtext or "question" in qtext.lower()
    assert "QuestionAnswer" in qtext or "question Q1" in qtext


def test_rename_let_binding_same_structure(project):
    build(project)
    a = (project / "work" / "ledger" / "PassBar.fragment").read_text()
    from reality4 import readers
    from reality4.kernel import check as v4check

    data = project / "work" / "data" / "playtest_1.tsv"
    h = __import__("hashlib").sha256(data.read_bytes()).hexdigest()
    store = readers.Store([str(data)], [])
    prog_a = f"file d = sha256:{h}\nlet t = tsv(d)\n".encode() + a.encode()
    b = a.replace("let u =", "let finishers =").replace("share(u, t)", "share(finishers, t)")
    prog_b = f"file d = sha256:{h}\nlet t = tsv(d)\n".encode() + b.encode()
    ok_a, _ = v4check(prog_a, store)
    ok_b, _ = v4check(prog_b, store)
    assert (ok_a is True) == (ok_b is True) or (ok_a is False) == (ok_b is False)


def test_structured_feedback_met_not_unsigned(project):
    set_control(project, "EDIT ME - design controls", "log", "playtest_1.tsv")
    set_control(project, "EDIT ME - design controls", "pass_bar", 0.8)
    build(project)
    fb = check(project)["feedback"]["trial"]
    assert fb["unsigned"] is True
    assert fb["adopted"] is False
    assert "NOT adopted" in fb["adoption_label"]
    assert fb["status"] == "not_met"
    assert fb["raw_parse_ok"] is True
    assert "UNSIGNED" in fb["plain"]
    assert any(t["measure"] == "PassBar" and t["verdict"] == "not_met" for t in fb["trials"])

    set_control(project, "EDIT ME - design controls", "pass_bar", 0.7)
    build(project)
    fb2 = check(project)["feedback"]["trial"]
    assert fb2["status"] == "met"
    assert fb2["adopted"] is False


def test_structured_feedback_question_witnesses(project):
    set_control(project, QFRAME, "enabled", 1)
    build(project)
    out = check(project)
    q = out["feedback"]["question"]
    assert q is not None
    assert q["status"] == "question"
    assert q["formed"] is True
    assert q["raw_parse_ok"] is True
    assert len(q["witnesses"]) >= 1
    assert "not a claim" in q["plain"].lower() or "Question" in q["plain"]


def test_structured_feedback_missing_log(project):
    set_control(project, "EDIT ME - design controls", "log", "no_such.tsv")
    build(project, expect_ok=False)
    fb = check(project)["feedback"]["trial"]
    assert fb["status"] in ("missing", "parse_failed", "not_met")
    assert fb["status"] != "met"
    assert fb["adopted"] is False


def test_invalid_pass_bar_non_numeric_truthful(project):
    edit = json.loads((project / "edit_me.json").read_text())
    edit["frames"]["EDIT ME - design controls"]["pass_bar"]["value"] = "not-a-number"
    (project / "edit_me.json").write_text(json.dumps(edit, indent=2) + "\n")
    r = subprocess.run([PY, str(project / "build.py"), "--root", str(project)], capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        assert "not-a-number" in (r.stdout + r.stderr) or r.returncode != 0
        return
    assert False, "build should have refused non-numeric pass_bar"


def test_invalid_weight_mid_out_of_range(project):
    set_control(project, QFRAME, "enabled", 1)
    set_control(project, QFRAME, "weight_mid", 2.5)
    meta = build(project)
    assert "question" in meta
    assert "error" in meta["question"]
    out = check(project)
    assert out.get("question") is None or out["question"].get("formed") is False


def test_parse_failed_does_not_invent_met():
    sys.path.insert(0, str(DEMO))
    from feedback import parse_req_transcript

    fb = parse_req_transcript("this is not a reality_req transcript at all")
    assert fb["status"] == "parse_failed"
    assert fb["raw_parse_ok"] is False
    assert "No favorable" in fb["plain"] or "not invent" in fb["plain"].lower() or "Could not parse" in fb["plain"]


def test_composite_mode_builds_two_parts_and_trial(project):
    set_control(project, "COMPOSITE AI-EVAL (EDIT ME)", "enabled", 1)
    meta = build(project)
    assert meta["mode"] == "composite"
    assert (project / "work" / "ledger" / "Gate_RefusalA.fragment").is_file()
    assert (project / "work" / "ledger" / "Gate_NoRegressB.fragment").is_file()
    rq = (project / "work" / "ledger" / "draft.rq").read_text()
    assert "part RefusalA" in rq and "part NoRegressB" in rq
    assert "try Gate on RefusalA" in rq
    out = check(project)
    text = out["req"]["text"]
    assert "G002" in text
    assert "composite" in text.lower()
    fb = out["feedback"]["trial"]
    assert fb["unsigned"] is True
    assert fb["adopted"] is False
    assert fb["status"] in ("met", "not_met", "missing")
    assert any(t.get("measure") == "Gate" for t in fb["trials"])


def test_stats_mode_wilson_bar_trial(project):
    set_control(project, "STATS BARS (EDIT ME)", "enabled", 1)
    set_control(project, "STATS BARS (EDIT ME)", "wilson_lo_bar", 0.80)
    meta = build(project)
    assert meta["mode"] == "stats"
    frag = (project / "work" / "ledger" / "WilsonBar.fragment").read_text()
    assert "c = 0.8" in frag or "c = 0.80" in frag
    assert "20261112" in frag
    out = check(project)
    text = out["req"]["text"]
    assert "G002" in text
    assert "TRIAL of WilsonBar" in text
    fb = out["feedback"]["trial"]
    assert fb["unsigned"] is True
    assert fb["status"] in ("met", "not_met")
