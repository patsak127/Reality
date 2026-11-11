"""Local LLM judge: hash-bound bind table + HOLDS/DNH/NOT CHECKED."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

REQ = pathlib.Path(__file__).resolve().parents[1]
DEMO = REQ / "demo" / "judge"
FIX = DEMO / "fixtures"
PY = sys.executable
ENV = {**os.environ, "PYTHONPATH": f"{REQ / 'src'}:{REQ.parent / 'v4' / 'src'}"}
TF_PIN = "4.57.1"


def _have_transformers():
    try:
        import transformers

        return getattr(transformers, "__version__", None) == TF_PIN
    except ImportError:
        return False


def test_requirements_and_readme_pins():
    assert f"transformers=={TF_PIN}" in (DEMO / "requirements.txt").read_text()
    md = (DEMO / "README.md").read_text()
    assert TF_PIN in md and "logprob_argmax" in md
    assert "Across hardware" in md or "across hardware" in md.lower()


def test_fixtures_present():
    for name in ("judge_labels.tsv", "judge_bind.tsv", "judge_meta.json"):
        assert (FIX / name).is_file(), name


def test_bind_table_has_required_keys():
    rows = dict(
        ln.split("\t", 1) for ln in (FIX / "judge_bind.tsv").read_text().splitlines()[1:] if ln.strip()
    )
    for k in ("weights_sha256", "prompt_sha256", "method", "seed", "do_sample", "model_id", "transformers"):
        assert k in rows
    assert rows["method"] == "logprob_argmax"
    assert rows["do_sample"] == "0"
    assert rows["transformers"] == TF_PIN
    assert rows["weights_sha256"].startswith("sha256:")
    assert rows["prompt_sha256"].startswith("sha256:")


def test_labels_counts():
    rows = [ln.split("\t") for ln in (FIX / "judge_labels.tsv").read_text().splitlines()[1:] if ln.strip()]
    assert len(rows) == 12
    refused = sum(1 for r in rows if r[2] == "refused")
    assert refused >= 1
    meta = json.loads((FIX / "judge_meta.json").read_text())
    assert meta["label_counts"]["refused"] == refused


def test_reality_holds_dnh_not_checked(tmp_path):
    work = tmp_path / "j"
    r = subprocess.run(
        [PY, str(DEMO / "run_judge_reality_checks.py"),
         "--fixtures", str(FIX), "--work", str(work)],
        env=ENV, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "LabelsLoose HOLDS" in (work / "judge-holds.txt").read_text()
    assert "LabelsStrict DOES NOT HOLD" in (work / "judge-dnh.txt").read_text()
    assert "BindPin HOLDS" in (work / "judge-bind-holds.txt").read_text()
    assert "NOT CHECKED" in (work / "judge-wrong-sha-not-checked.txt").read_text()
    wrong_vals = (work / "judge-wrong-values-dnh.txt").read_text()
    assert "DOES NOT HOLD" in wrong_vals


@pytest.mark.skipif(not _have_transformers(), reason=f"transformers=={TF_PIN} not installed")
def test_judge_rerun_reproduces_labels(tmp_path):
    out = tmp_path / "regen"
    r = subprocess.run(
        [PY, str(DEMO / "run_llm_judge.py"), "--out-dir", str(out)],
        env=ENV, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert (out / "judge_labels.tsv").read_bytes() == (FIX / "judge_labels.tsv").read_bytes()
    # bind table torch line may match; weights/prompt must match
    b1 = dict(ln.split("\t", 1) for ln in (out / "judge_bind.tsv").read_text().splitlines()[1:] if ln.strip())
    b0 = dict(ln.split("\t", 1) for ln in (FIX / "judge_bind.tsv").read_text().splitlines()[1:] if ln.strip())
    for k in ("weights_sha256", "prompt_sha256", "method", "seed", "do_sample"):
        assert b1[k] == b0[k]
