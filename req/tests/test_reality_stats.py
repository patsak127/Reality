"""Wilson / bootstrap / kappa helpers + measure HOLDS/DNH on stats tables."""
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

    # Alternating bits so different seeds diverge at n_boot=200
    bits = [i % 2 for i in range(40)]
    x = bootstrap_ci_lower(bits, seed=20261112, n_boot=200, conf=0.95)
    y = bootstrap_ci_lower(bits, seed=20261112, n_boot=200, conf=0.95)
    z = bootstrap_ci_lower(bits, seed=99, n_boot=200, conf=0.95)
    assert x == y
    assert x != z


def test_stats_wilson_a_holds(stats_data):
    ok, lines = _check_frag("StatsWilsonA.fragment", "stats_A.tsv", stats_data)
    assert ok is True
    assert any("holds" in ln for ln in lines)


def test_stats_wilson_a_strict_does_not_hold(stats_data):
    ok, lines = _check_frag("StatsWilsonAStrict.fragment", "stats_A.tsv", stats_data)
    # overall program may be False when a claim refuses V001 item 5
    text = "\n".join(lines)
    assert "does not hold" in text or ok is False
    assert "0.99" in text


def test_stats_pinned_seed_in_table(stats_data):
    row = (stats_data / "stats_A.tsv").read_text().splitlines()[1].split("\t")
    assert row[5] == "0.95"
    assert row[6] == "20261112"
    assert row[7] == "2000"
