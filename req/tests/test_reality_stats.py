"""Wilson / bootstrap / kappa / seed-variance / judge-bind + HOLDS/DNH on stats tables."""
from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys

import pytest

REQ = pathlib.Path(__file__).resolve().parents[1]
ROOT = REQ.parent
DEMO = REQ / "demo"
PY = sys.executable
ENV = {**os.environ, "PYTHONPATH": f"{REQ / 'src'}:{ROOT / 'v4' / 'src'}"}


@pytest.fixture(scope="module")
def stats_data(tmp_path_factory):
    d = tmp_path_factory.mktemp("stats")
    subprocess.run([PY, str(DEMO / "make_stats.py"), str(d)], check=True, env=ENV, capture_output=True)
    return d


def _check_frag(frag_name, data_file, data_dir):
    from reality4 import readers
    from reality4.kernel import check

    frag = (DEMO / frag_name).read_text()
    p = data_dir / data_file
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    prog = f"file d = sha256:{h}\nlet t = tsv(d)\n".encode() + frag.encode()
    store = readers.Store([str(p)], [])
    return check(prog, store)


def test_wilson_lower_monotonic():
    from reality_stats import wilson_lower

    a = wilson_lower(196, 200, 0.95)
    b = wilson_lower(200, 200, 0.95)
    assert a < b
    assert float(a) >= 0.80


def test_bootstrap_seed_reproducible():
    from reality_stats import bootstrap_ci_lower

    bits = [i % 2 for i in range(40)]
    x = bootstrap_ci_lower(bits, seed=20261112, n_boot=200, conf=0.95)
    y = bootstrap_ci_lower(bits, seed=20261112, n_boot=200, conf=0.95)
    z = bootstrap_ci_lower(bits, seed=99, n_boot=200, conf=0.95)
    assert x == y
    assert x != z


def test_seed_variance_pinned():
    from reality_stats import seed_variance_lower

    bits = [1] * 196 + [0] * 4
    mean_a, var_a = seed_variance_lower(bits, seed=20261112, n_runs=5, n_boot=200, conf=0.95)
    mean_b, var_b = seed_variance_lower(bits, seed=20261112, n_runs=5, n_boot=200, conf=0.95)
    assert mean_a == mean_b and var_a == var_b
    assert var_a >= 0


def test_kappa_perfect_and_disagree():
    from reality_stats import cohens_kappa

    labs = ["refused", "complied", "refused", "complied"]
    assert float(cohens_kappa(labs, labs)) == 1.0
    flipped = ["complied", "refused", "complied", "refused"]
    assert float(cohens_kappa(labs, flipped)) < 1.0


def test_stats_table_pins_all_params(stats_data):
    row = (stats_data / "stats_A.tsv").read_text().splitlines()[1].split("\t")
    assert row[5] == "0.95"
    assert row[6] == "20261112"
    assert row[7] == "2000"
    assert row[8] == "5"
    assert float(row[2]) >= 0.80  # wilson_lo


def test_judge_meta_hashes(stats_data):
    text = (stats_data / "judge_meta_A.tsv").read_text()
    assert "judge_model\tsha256:b32989bfa2991125" in text
    assert "judge_prompt\tsha256:dc0dc07d5e33e055" in text


def test_stats_wilson_a_holds(stats_data):
    ok, lines = _check_frag("StatsWilsonA.fragment", "stats_A.tsv", stats_data)
    assert ok is True
    assert any("holds" in ln for ln in lines)


def test_stats_wilson_a_strict_does_not_hold(stats_data):
    ok, lines = _check_frag("StatsWilsonAStrict.fragment", "stats_A.tsv", stats_data)
    text = "\n".join(lines)
    assert "does not hold" in text or ok is False
    assert "0.99" in text


def test_judge_bind_holds(stats_data):
    ok, lines = _check_frag("JudgeBindA.fragment", "judge_meta_A.tsv", stats_data)
    assert ok is True


def test_judge_bind_wrong_meta_does_not_hold(stats_data, tmp_path):
    bad = tmp_path / "judge_meta_bad.tsv"
    bad.write_text("key\tvalue\njudge_model\tsha256:" + ("0" * 64) + "\njudge_prompt\tsha256:" + ("1" * 64) + "\n")
    ok, lines = _check_frag("JudgeBindA.fragment", "judge_meta_bad.tsv", tmp_path)
    text = "\n".join(lines)
    assert ok is False or "does not hold" in text


def test_run_stats_gate_holds_and_dnh(tmp_path):
    work = tmp_path / "sg"
    r = subprocess.run(
        [PY, str(DEMO / "run_stats_gate.py"), "--work", str(work), "--mode", "both"],
        env=ENV, capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    pass_t = (work / "pass" / "transcript.txt").read_text()
    fail_t = (work / "fail" / "transcript.txt").read_text()
    assert "StatsGate HOLDS as a composite" in pass_t or "StatsGate HOLDS" in pass_t
    assert "StatsGateFail DOES NOT HOLD" in fail_t
    assert "TEST key" in pass_t or "REALITY-TEST-KEY-NOT-PATSAK" in (work / "pass" / "test-key" / "key.pub").read_text()
    assert "ADOPTED" in pass_t and "ADOPTED" in fail_t
