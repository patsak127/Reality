"""Qwen3-1.7B-Q8_0 GGUF judge fixtures: agreement, bind pins, HOLDS/DNH/NOT CHECKED."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

REQ = pathlib.Path(__file__).resolve().parents[1]
DEMO = REQ / "demo" / "judge"
FIX = DEMO / "fixtures" / "qwen3"
PY = sys.executable
ENV = {**os.environ, "PYTHONPATH": f"{REQ / 'src'}:{REQ.parent / 'v4' / 'src'}"}

EXPECTED_WEIGHTS = "061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a"


def test_hand_labels_size():
    rows = [ln for ln in (DEMO / "hand_labels.jsonl").read_text().splitlines() if ln.strip()]
    assert 20 <= len(rows) <= 40


def test_qwen_fixtures_present():
    for name in ("judge_labels.tsv", "judge_bind.tsv", "judge_meta.json", "label.gbnf", "labels.sha256"):
        assert (FIX / name).is_file(), name


def test_weights_sha_matches_public_gguf():
    rows = dict(ln.split("\t", 1) for ln in (FIX / "judge_bind.tsv").read_text().splitlines()[1:] if ln.strip())
    assert rows["weights_sha256"] == f"sha256:{EXPECTED_WEIGHTS}"
    assert rows["model_file"] == "Qwen3-1.7B-Q8_0.gguf"
    assert rows["model_repo"] == "Qwen/Qwen3-1.7B-GGUF"
    assert rows["method"] == "greedy_grammar"
    assert rows["temp"] == "0.0"
    assert rows["top_k"] == "1"
    assert rows["seed"] == "20261112"
    assert rows["do_sample"] == "0"
    assert rows["reasoning"] == "off"
    assert "llamacpp_version" in rows and rows["llamacpp_version"]


def test_agreement_informative():
    meta = json.loads((FIX / "judge_meta.json").read_text())
    agr = meta["agreement_vs_hand"]
    assert agr["n"] == 32
    assert agr["accuracy"] >= 0.80
    assert agr["cohens_kappa"] >= 0.50  # clearly above chance


def test_reality_holds_dnh_not_checked(tmp_path):
    work = tmp_path / "jq"
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
    assert "DOES NOT HOLD" in (work / "judge-wrong-values-dnh.txt").read_text()


def test_readme_names_qwen_and_llamacpp():
    md = (DEMO / "README.md").read_text()
    assert "Qwen3-1.7B-Q8_0" in md
    assert "llama.cpp" in md
    assert EXPECTED_WEIGHTS in md or "061b54da" in md
