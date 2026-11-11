"""Composite measures (req layer) + CI gate exit behaviour."""
from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REQ = pathlib.Path(__file__).resolve().parents[1]
ROOT = REQ.parent
DEMO = REQ / "demo"
PY = sys.executable
ENV = {**os.environ, "PYTHONPATH": f"{REQ / 'src'}:{ROOT / 'v4' / 'src'}"}


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


@pytest.fixture()
def eval_data(tmp_path):
    d = tmp_path / "data"
    subprocess.run([PY, str(DEMO / "make_evals.py"), str(d)], check=True, capture_output=True, env=ENV)
    return d


def _ledger_with_gate(work, eval_data, *, strict=False):
    led_dir = work / "ledger"
    led_dir.mkdir(parents=True)
    for n in ("Gate_RefusalA", "Gate_NoRegressB", "Gate_RefusalAStrict"):
        shutil.copy(DEMO / f"{n}.fragment", led_dir / f"{n}.fragment")
    a = sha(eval_data / "evals_A.tsv")
    b = sha(eval_data / "evals_B.tsv")
    if strict:
        body = f'''person patsak
tool gatebot
requirement Rgate = "composite AI-eval"
  owner patsak
measure GateFail for Rgate proposed_by gatebot
  says "strict"
  part RefusalAStrict fragment "Gate_RefusalAStrict.fragment" sha256:{sha(DEMO / "Gate_RefusalAStrict.fragment")}
  part NoRegressB fragment "Gate_NoRegressB.fragment" sha256:{sha(DEMO / "Gate_NoRegressB.fragment")}
try GateFail on RefusalAStrict sha256:{a} on NoRegressB sha256:{b}
'''
    else:
        body = f'''person patsak
tool gatebot
requirement Rgate = "composite AI-eval"
  owner patsak
measure Gate for Rgate proposed_by gatebot
  says "95 and 95"
  part RefusalA fragment "Gate_RefusalA.fragment" sha256:{sha(DEMO / "Gate_RefusalA.fragment")}
  part NoRegressB fragment "Gate_NoRegressB.fragment" sha256:{sha(DEMO / "Gate_NoRegressB.fragment")}
try Gate on RefusalA sha256:{a} on NoRegressB sha256:{b}
'''
    led = led_dir / "g.rq"
    led.write_text(body)
    return led


def test_composite_trial_holds_and_reports_parts(eval_data, tmp_path):
    led = _ledger_with_gate(tmp_path, eval_data, strict=False)
    r = subprocess.run(
        [PY, "-m", "reality_req", "check", str(led), "--files", str(eval_data)],
        env=ENV, capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "composite (2 parts: RefusalA, NoRegressB)" in r.stdout
    assert "part RefusalA:" in r.stdout
    assert "part NoRegressB:" in r.stdout
    assert "Gate HOLDS as a composite" in r.stdout


def test_composite_trial_does_not_hold_when_one_part_fails(eval_data, tmp_path):
    led = _ledger_with_gate(tmp_path, eval_data, strict=True)
    r = subprocess.run(
        [PY, "-m", "reality_req", "check", str(led), "--files", str(eval_data)],
        env=ENV, capture_output=True, text=True,
    )
    assert r.returncode == 0  # formed
    assert "RefusalAStrict DOES NOT HOLD" in r.stdout
    assert "NoRegressB HOLDS" in r.stdout
    assert "GateFail DOES NOT HOLD as a composite" in r.stdout


def test_composite_missing_part_binding_refuses_g024(eval_data, tmp_path):
    led_dir = tmp_path / "ledger"
    led_dir.mkdir()
    shutil.copy(DEMO / "Gate_RefusalA.fragment", led_dir / "Gate_RefusalA.fragment")
    shutil.copy(DEMO / "Gate_NoRegressB.fragment", led_dir / "Gate_NoRegressB.fragment")
    a = sha(eval_data / "evals_A.tsv")
    led = led_dir / "g.rq"
    led.write_text(f'''person patsak
tool gatebot
requirement Rgate = "composite AI-eval"
  owner patsak
measure Gate for Rgate proposed_by gatebot
  says "x"
  part RefusalA fragment "Gate_RefusalA.fragment" sha256:{sha(DEMO / "Gate_RefusalA.fragment")}
  part NoRegressB fragment "Gate_NoRegressB.fragment" sha256:{sha(DEMO / "Gate_NoRegressB.fragment")}
try Gate on RefusalA sha256:{a}
''')
    r = subprocess.run(
        [PY, "-m", "reality_req", "check", str(led), "--files", str(eval_data)],
        env=ENV, capture_output=True, text=True,
    )
    assert r.returncode == 1
    assert "G024" in r.stdout
    assert "NoRegressB" in r.stdout


def test_ci_gate_pass_and_fail_samples(tmp_path):
    r = subprocess.run(
        [PY, str(DEMO / "ai_eval_gate.py"), "--work", str(tmp_path / "gate"), "--mode", "both"],
        env=ENV, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ci_gate: pass: HOLDS (Gate)" in r.stdout
    assert "ci_gate: block: DOES NOT HOLD (GateFail)" in r.stdout


def test_ci_gate_blocks_missing_adoption(eval_data, tmp_path):
    led = _ledger_with_gate(tmp_path, eval_data, strict=False)
    # Replace try with check without adoption
    text = led.read_text().replace("try Gate", "check Rgate by Gate")
    # check needs part bindings already there from try line — rewrite
    a = sha(eval_data / "evals_A.tsv")
    b = sha(eval_data / "evals_B.tsv")
    led.write_text(text.split("try Gate")[0] + f"check Rgate by Gate on RefusalA sha256:{a} on NoRegressB sha256:{b}\n")
    r = subprocess.run(
        [PY, "-m", "reality_req.ci_gate", str(led), "--files", str(eval_data)],
        env=ENV, capture_output=True, text=True,
    )
    assert r.returncode == 1
    assert "block:" in r.stdout
    assert "G002" in r.stdout or "refused" in r.stdout


def test_ci_gate_blocks_missing_data_file(eval_data, tmp_path):
    led = _ledger_with_gate(tmp_path, eval_data, strict=False)
    # Point at a hash with no file supplied
    fake = "0" * 64
    text = led.read_text()
    a = sha(eval_data / "evals_A.tsv")
    text = text.replace(f"sha256:{a}", f"sha256:{fake}", 1)
    led.write_text(text)
    r = subprocess.run(
        [PY, "-m", "reality_req.ci_gate", str(led), "--files", str(eval_data)],
        env=ENV, capture_output=True, text=True,
    )
    assert r.returncode == 1
    assert "block:" in r.stdout
    assert "NOT CHECKED" in r.stdout or "ci_gate: block" in r.stdout
