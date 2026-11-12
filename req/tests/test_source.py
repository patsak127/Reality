"""Trusted base of req/ under its cap; v4 trusted base at 10,000 with native questions (SPEC-ORD-EXP).

Untrusted helpers next to the package: sign.py (SSH adopt/withdraw), ci_gate.py (CI exit driver).
"""
from conftest import REQ, ROOT

CAP = 900
TRUSTED = ["__init__.py", "syntax.py", "form.py", "say.py", "run.py", "bind.py", "__main__.py"]
UNTRUSTED = {"sign.py", "ci_gate.py"}
V4 = ["decide.py", "kernel.py", "bids101.py", "readers.py", "witness.py", "syntax.py", "intstep.py", "machine.py",
      "sorts.py", "__main__.py", "keys.py", "exact.py", "cert.py", "questions.py"]
V4_TRUSTED_LINES = 10000  # after native questions (SPEC-ORD-EXP 0.3); was 9539 before questions


def lines(p):
    return len(p.read_bytes().splitlines()) if p.exists() else 0


def test_req_trusted_base_under_cap():
    total = sum(lines(REQ / "src" / "reality_req" / f) for f in TRUSTED)
    assert total <= CAP, total


def test_v4_trusted_base_unchanged():
    assert sum(lines(ROOT / "v4" / "src" / "reality4" / f) for f in V4) == V4_TRUSTED_LINES


def test_only_listed_files_in_package():
    have = {p.name for p in (REQ / "src" / "reality_req").glob("*.py")}
    assert have <= set(TRUSTED) | UNTRUSTED, have - set(TRUSTED) - UNTRUSTED
