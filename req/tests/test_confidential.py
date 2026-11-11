"""Confidential hash-only prompt sets: adopt/check vs sha256 (+ optional Merkle helper)."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REQ = pathlib.Path(__file__).resolve().parents[1]
DEMO = REQ / "demo"
PY = sys.executable
ENV = {**os.environ, "PYTHONPATH": f"{REQ / 'src'}:{REQ.parent / 'v4' / 'src'}"}


def test_merkle_root_stable():
    sys.path.insert(0, str(DEMO / "confidential"))
    from merkle import merkle_root

    a = merkle_root(["p1", "p2", "p3"])
    b = merkle_root(["p1", "p2", "p3"])
    c = merkle_root(["p1", "p3", "p2"])
    assert a == b
    assert a != c
    assert len(a) == 64


def test_confidential_bundle_try_holds(tmp_path):
    work = tmp_path / "conf"
    subprocess.run(
        [PY, str(DEMO / "confidential" / "make_confidential_bundle.py"), "--work", str(work)],
        env=ENV, check=True, capture_output=True,
    )
    r = subprocess.run(
        [PY, "-m", "reality_req", "check", str(work / "ledger" / "confidential.rq"),
         "--files", str(work / "data")],
        env=ENV, capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "HOLDS" in r.stdout
    assert "TRIAL" in r.stdout


def test_confidential_wrong_prompt_set_not_silent_holds(tmp_path):
    work = tmp_path / "conf"
    subprocess.run(
        [PY, str(DEMO / "confidential" / "make_confidential_bundle.py"), "--work", str(work)],
        env=ENV, check=True, capture_output=True,
    )
    # Point try at evals_B while fragment pins set A → empty filter / failed counts
    rq = (work / "ledger" / "confidential.rq").read_text()
    import hashlib
    eb = hashlib.sha256((work / "data" / "evals_B.tsv").read_bytes()).hexdigest()
    # replace the try hash (last sha256 on try line)
    lines = []
    for ln in rq.splitlines():
        if ln.startswith("try ConfA on sha256:"):
            lines.append(f"try ConfA on sha256:{eb}")
        else:
            lines.append(ln)
    (work / "ledger" / "confidential.rq").write_text("\n".join(lines) + "\n")
    r = subprocess.run(
        [PY, "-m", "reality_req", "check", str(work / "ledger" / "confidential.rq"),
         "--files", str(work / "data")],
        env=ENV, capture_output=True, text=True,
    )
    # Must not silently HOLDS when the wrong eval bytes are supplied
    assert "ConfA HOLDS" not in r.stdout
    assert ("DOES NOT HOLD" in r.stdout) or ("NOT CHECKED" in r.stdout)
