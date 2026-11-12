"""Real inspect_ai / deepeval fixtures → Reality HOLDS and DOES NOT HOLD."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys

import pytest

REQ = pathlib.Path(__file__).resolve().parents[1]
DEMO = REQ / "demo" / "harness"
REAL = DEMO / "fixtures" / "real"
PY = sys.executable
ENV = {**os.environ, "PYTHONPATH": f"{REQ / 'src'}:{REQ.parent / 'v4' / 'src'}"}

INSPECT_PIN = "0.3.289"
DEEPEVAL_PIN = "4.3.3"


def _have_inspect():
    try:
        import inspect_ai

        return getattr(inspect_ai, "__version__", None) == INSPECT_PIN
    except ImportError:
        return False


def _have_deepeval():
    try:
        import deepeval

        return getattr(deepeval, "__version__", None) == DEEPEVAL_PIN
    except ImportError:
        return False


def test_requirements_pins_exact_versions():
    text = (DEMO / "requirements.txt").read_text()
    assert f"inspect_ai=={INSPECT_PIN}" in text
    assert f"deepeval=={DEEPEVAL_PIN}" in text


def test_readme_names_pinned_versions():
    md = (DEMO / "README.md").read_text()
    assert INSPECT_PIN in md and DEEPEVAL_PIN in md
    assert "Tested versions" in md


def test_real_fixtures_present():
    for name in (
        "inspect_tiny_refusal.eval",
        "inspect_tiny_refusal.jsonl",
        "inspect_meta.json",
        "deepeval_tiny_refusal.json",
        "deepeval_tiny_refusal.jsonl",
        "deepeval_meta.json",
    ):
        assert (REAL / name).is_file(), name


def test_fixture_meta_versions():
    assert json.loads((REAL / "inspect_meta.json").read_text())["version"] == INSPECT_PIN
    assert json.loads((REAL / "deepeval_meta.json").read_text())["version"] == DEEPEVAL_PIN


def test_inspect_jsonl_rows_from_real_eval():
    lines = [ln for ln in (REAL / "inspect_tiny_refusal.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) == 12
    rows = [json.loads(ln) for ln in lines]
    assert all(r["source"] == "inspect_ai" for r in rows)
    assert all(r.get("inspect_ai_version") == INSPECT_PIN for r in rows)
    harmful = [r for r in rows if r["prompt_label"] == "harmful"]
    assert len(harmful) == 8
    assert sum(1 for r in harmful if r["output_label"] == "refused") == 6


def test_deepeval_jsonl_rows_from_real_result():
    lines = [ln for ln in (REAL / "deepeval_tiny_refusal.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) == 12
    rows = [json.loads(ln) for ln in lines]
    assert all(r["source"] == "deepeval" for r in rows)
    payload = json.loads((REAL / "deepeval_tiny_refusal.json").read_text())
    assert payload["harness"] == "deepeval"
    assert len(payload["test_results"]) == 12


@pytest.mark.skipif(not _have_inspect(), reason=f"inspect_ai=={INSPECT_PIN} not installed")
def test_inspect_eval_adapter_roundtrip(tmp_path):
    out = tmp_path / "from_eval.jsonl"
    r = subprocess.run(
        [PY, str(DEMO / "inspect_eval_to_jsonl.py"),
         "--eval", str(REAL / "inspect_tiny_refusal.eval"),
         "--jsonl-out", str(out)],
        env=ENV, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    # Same prompt_ids / labels as committed jsonl (ignore volatile fields)
    a = [json.loads(ln) for ln in out.read_text().splitlines() if ln.strip()]
    b = [json.loads(ln) for ln in (REAL / "inspect_tiny_refusal.jsonl").read_text().splitlines() if ln.strip()]
    assert [(x["prompt_id"], x["prompt_label"], x["output_label"]) for x in a] == [
        (x["prompt_id"], x["prompt_label"], x["output_label"]) for x in b
    ]


@pytest.mark.skipif(not _have_deepeval(), reason=f"deepeval=={DEEPEVAL_PIN} not installed")
def test_deepeval_result_adapter(tmp_path):
    out = tmp_path / "from_de.jsonl"
    r = subprocess.run(
        [PY, str(DEMO / "deepeval_result_to_jsonl.py"),
         "--result-json", str(REAL / "deepeval_tiny_refusal.json"),
         "--jsonl-out", str(out)],
        env=ENV, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert out.is_file() and out.stat().st_size > 0


@pytest.mark.parametrize("jsonl_name,label", [
    ("inspect_tiny_refusal.jsonl", "inspect"),
    ("deepeval_tiny_refusal.jsonl", "deepeval"),
])
def test_reality_holds_and_dnh_from_real_jsonl(tmp_path, jsonl_name, label):
    work = tmp_path / label
    r = subprocess.run(
        [PY, str(DEMO / "run_reality_checks.py"),
         "--jsonl", str(REAL / jsonl_name),
         "--work", str(work),
         "--label", label],
        env=ENV, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    holds = (work / f"{label}-holds.txt").read_text()
    dnh = (work / f"{label}-dnh.txt").read_text()
    assert "HarnessLoose HOLDS" in holds
    assert "HarnessStrict DOES NOT HOLD" in dnh


def test_tsv_hash_stable_for_committed_inspect_jsonl(tmp_path):
    p1, e1 = tmp_path / "p.tsv", tmp_path / "e.tsv"
    subprocess.run(
        [PY, str(DEMO / "jsonl_to_eval_tsv.py"),
         "--jsonl", str(REAL / "inspect_tiny_refusal.jsonl"),
         "--prompts-out", str(p1), "--evals-out", str(e1)],
        env=ENV, check=True, capture_output=True,
    )
    h = hashlib.sha256(e1.read_bytes()).hexdigest()
    subprocess.run(
        [PY, str(DEMO / "jsonl_to_eval_tsv.py"),
         "--jsonl", str(REAL / "inspect_tiny_refusal.jsonl"),
         "--prompts-out", str(tmp_path / "p2.tsv"), "--evals-out", str(tmp_path / "e2.tsv")],
        env=ENV, check=True, capture_output=True,
    )
    assert hashlib.sha256((tmp_path / "e2.tsv").read_bytes()).hexdigest() == h
