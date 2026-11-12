"""STUB tiny-gpt2 judge (fast unit tests). Primary judge is Qwen3 — see test_qwen_judge.py."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

REQ = pathlib.Path(__file__).resolve().parents[1]
DEMO = REQ / "demo" / "judge"
FIX = DEMO / "fixtures" / "stub"
PY = sys.executable
ENV = {**os.environ, "PYTHONPATH": f"{REQ / 'src'}:{REQ.parent / 'v4' / 'src'}"}
TF_PIN = "4.57.1"


def _have_transformers():
    try:
        import transformers

        return getattr(transformers, "__version__", None) == TF_PIN
    except ImportError:
        return False


def test_stub_fixtures_present():
    for name in ("judge_labels.tsv", "judge_bind.tsv", "judge_meta.json"):
        assert (FIX / name).is_file(), name


def test_stub_bind_table_keys():
    rows = dict(
        ln.split("\t", 1) for ln in (FIX / "judge_bind.tsv").read_text().splitlines()[1:] if ln.strip()
    )
    for k in ("weights_sha256", "prompt_sha256", "method", "seed", "do_sample", "model_id"):
        assert k in rows
    assert rows["method"] == "logprob_argmax"
    assert rows["model_id"] == "sshleifer/tiny-gpt2"


def test_stub_reality_holds_dnh_not_checked(tmp_path):
    work = tmp_path / "jstub"
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


@pytest.mark.skipif(not _have_transformers(), reason=f"transformers=={TF_PIN} not installed")
def test_stub_judge_rerun_reproduces_labels(tmp_path):
    out = tmp_path / "regen"
    r = subprocess.run(
        [PY, str(DEMO / "run_llm_judge.py"), "--out-dir", str(out)],
        env=ENV, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert (out / "judge_labels.tsv").read_bytes() == (FIX / "judge_labels.tsv").read_bytes()
    b1 = dict(ln.split("\t", 1) for ln in (out / "judge_bind.tsv").read_text().splitlines()[1:] if ln.strip())
    b0 = dict(ln.split("\t", 1) for ln in (FIX / "judge_bind.tsv").read_text().splitlines()[1:] if ln.strip())
    for k in ("weights_sha256", "prompt_sha256", "method", "seed", "do_sample"):
        assert b1[k] == b0[k]


def test_readme_labels_stub_clearly():
    md = (DEMO / "README.md").read_text()
    assert "stub" in md.lower() or "STUB" in md
    assert "tiny-gpt2" in md
