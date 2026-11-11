"""Harness JSONL adapters (Inspect / DeepEval shaped) → hash-bound Reality TSVs."""
from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys

REQ = pathlib.Path(__file__).resolve().parents[1]
DEMO = REQ / "demo"
PY = sys.executable
ENV = {**os.environ, "PYTHONPATH": f"{REQ / 'src'}:{REQ.parent / 'v4' / 'src'}"}


def test_jsonl_adapter_stable(tmp_path):
    out_p, out_e = tmp_path / "prompts_A.tsv", tmp_path / "evals_A.tsv"
    subprocess.run(
        [PY, str(DEMO / "harness" / "jsonl_to_eval_tsv.py"),
         "--jsonl", str(DEMO / "harness" / "fixtures" / "sample_inspect.jsonl"),
         "--prompts-out", str(out_p), "--evals-out", str(out_e), "--set-name", "A"],
        env=ENV, capture_output=True, text=True, check=True,
    )
    assert out_p.is_file() and out_e.is_file()
    assert "sha256:" in out_e.read_text()
    h1 = hashlib.sha256(out_e.read_bytes()).hexdigest()
    subprocess.run(
        [PY, str(DEMO / "harness" / "jsonl_to_eval_tsv.py"),
         "--jsonl", str(DEMO / "harness" / "fixtures" / "sample_inspect.jsonl"),
         "--prompts-out", str(tmp_path / "p2.tsv"), "--evals-out", str(tmp_path / "e2.tsv")],
        env=ENV, check=True, capture_output=True,
    )
    assert hashlib.sha256((tmp_path / "e2.tsv").read_bytes()).hexdigest() == h1


def test_readme_states_tested_versions_only():
    md = (DEMO / "harness" / "README.md").read_text()
    assert "Tested versions" in md or "tested versions" in md.lower()
    assert "Inspect" in md and "DeepEval" in md
    assert "not pinned" in md.lower() or "not tested" in md.lower() or "adapter code only" in md.lower()
