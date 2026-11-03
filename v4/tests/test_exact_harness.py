"""Exact-decision Phase 0: the frozen old search and the old-vs-new harness (tools/exact_diff.py)."""
import hashlib
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
V4 = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(V4, "tools"))
import exact_diff as X  # noqa: E402
import exact_measure as M  # noqa: E402
from reality4.syntax import parse_line  # noqa: E402
from test_source import TRUSTED  # noqa: E402

ORIGINAL_SHA = "76100d70349340c34aa342515e704de6dbac3dc9f0ec528be1042704d73c822e"   # src/reality4/witness.py at 6f21606
IMPORTS = [("from reality4 import readers as R\n", "from . import readers as R\n"),
           ("from reality4.syntax import ", "from .syntax import "),
           ("    from reality4.kernel import Checker, fail\n", "    from .kernel import Checker, fail\n")]


def test_frozen_copy_is_witness_at_6f21606_but_for_its_imports():
    text = open(os.path.join(HERE, "old_witness.py"), encoding="utf-8").read()
    head, body = text.split("\n", 5)[:5], text.split("\n", 5)[5]
    assert ORIGINAL_SHA in head[0] and "UNTRUSTED" in head[0]
    for new, old in IMPORTS:
        assert body.count(new) == 1
        body = body.replace(new, old)
    assert hashlib.sha256(body.encode("utf-8")).hexdigest() == ORIGINAL_SHA


def test_frozen_copy_is_outside_the_checker():
    assert "old_witness.py" not in TRUSTED and not os.path.exists(os.path.join(V4, "src", "reality4", "old_witness.py"))
    for f in os.listdir(os.path.join(V4, "src", "reality4")):
        if f.endswith(".py"):
            assert "old_witness" not in open(os.path.join(V4, "src", "reality4", f), encoding="utf-8").read(), f


def test_old_and_live_agree_on_the_bruteforce_family():
    """Since phase 3 the live checker decides part T exactly: on this family every verdict and code is
    the old one, and only the S008/S011 wording of the exact path differs (16 lines; 28 since the phase 3
    checkpoint added number conditions to part T, BB's ruling 3; 29 with part N in phase 4)."""
    a, b = X.run(X.decider("old"), "bruteforce"), X.run(X.decider("live"), "bruteforce")
    d = X.compare(a, b, "bruteforce")
    assert len(a) == 86 and len(d) == 29 and all(x[3] == "text" and "decided exactly" in x[6] for x in d), d


class _AlwaysBears:
    """A broken decider: every value bears. The harness must see the claims it lets form."""
    @staticmethod
    def check(checker, expr):
        return None

    @staticmethod
    def _as_judged(expr, checker):
        return expr


def test_harness_sees_a_broken_decider():
    a, b = X.run(X.decider("live"), "bruteforce"), X.run(_AlwaysBears, "bruteforce")
    d = X.compare(a, b, "bruteforce")
    assert d and {x[3] for x in d} == {"refuse/form"}, d
    assert any("difference(rows(tsv(f)), count(tsv(f)))" in a[x[1]][2].decode() for x in d)


def test_harness_restores_the_kernel():
    from reality4 import kernel, witness
    X.run(_AlwaysBears, "bruteforce")
    assert kernel.witness is witness and kernel.parse_line is parse_line


@pytest.mark.parametrize("stmt, raw, grouped", [
    ('count(where(tsv(f), eq(1, "x"), gt(2, c = 1)))', 8, 6),     # 2 classes x (point, 2 intervals, not a decimal)
    ("rows(tsv(f))", 1, 1),
    ('share(where(tsv(f), eq(1, "x")), where(tsv(f), ne(1, "y")))', 3, 3),
])
def test_row_type_estimate(stmt, raw, grouped):
    e = parse_line(f"claim {stmt}", 1).expr
    est = M.estimate(e)
    assert est["f"][1:3] == (raw, grouped), est
