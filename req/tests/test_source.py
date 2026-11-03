"""Trusted base of req/ under its cap; v4's trusted base unchanged at 9,539 lines (req/SPEC.md 9)."""
from conftest import REQ, ROOT

CAP = 900
TRUSTED = ["__init__.py", "syntax.py", "form.py", "say.py", "run.py", "bind.py", "__main__.py"]
V4 = ["decide.py", "kernel.py", "bids101.py", "readers.py", "witness.py", "syntax.py", "intstep.py", "machine.py",
      "sorts.py", "__main__.py", "keys.py", "exact.py", "cert.py"]


def lines(p):
    return len(p.read_bytes().splitlines()) if p.exists() else 0


def test_req_trusted_base_under_cap():
    total = sum(lines(REQ / "src" / "reality_req" / f) for f in TRUSTED)
    assert total <= CAP, total


def test_v4_trusted_base_unchanged():
    assert sum(lines(ROOT / "v4" / "src" / "reality4" / f) for f in V4) == 9539


def test_only_listed_files_in_package():
    have = {p.name for p in (REQ / "src" / "reality_req").glob("*.py")}
    assert have <= set(TRUSTED) | {"sign.py"}, have - set(TRUSTED)
