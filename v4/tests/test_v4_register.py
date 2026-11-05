"""v4 SPEC 8.1-8.3: the register classifies every 1.0.1 sentence once, its codes are codes the
reader raises, and its choice points are the ones the reader computes."""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V4 = os.path.join(HERE, "..")
REG = os.path.join(V4, "bids", "REGISTER-1.0.1.tsv")
TEXTS = [os.path.join(V4, "context", "sources", "bids-1.0.1.txt")]  # public BIDS 1.0.1 text, when present
BIDS = open(os.path.join(V4, "src", "reality4", "bids101.py"), encoding="utf-8").read()


def rows():
    lines = open(REG, encoding="utf-8").read().split("\n")
    head = lines[0].split("\t")
    return [dict(zip(head, ln.split("\t"))) for ln in lines[1:] if ln]


def test_register_matches_the_splitter_and_every_row_is_classified():
    TEXT = next((t for t in TEXTS if os.path.exists(t)), None)
    if TEXT is None:
        import pytest
        pytest.skip("the pinned 1.0.1 text is at none of " + ", ".join(TEXTS))
    r = subprocess.run([sys.executable, os.path.join(V4, "tools", "split_register.py"), TEXT, REG, "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_register_is_what_the_table_gives():
    r = subprocess.run([sys.executable, os.path.join(V4, "tools", "fill_register.py"), "--check"])
    assert r.returncode == 0


def test_register_codes_are_raised_by_the_reader():
    raised = set(re.findall(r'"(B\d\d)"', BIDS))
    for r in rows():
        for c in r["codes"].split():
            assert c == "read" or c in raised, (r["id"], c)
        if r["class"] == "checked":
            assert r["codes"], r["id"]
        if r["class"] == "silent":
            assert r["decision"], r["id"]
        if r["class"] in ("unshowable", "reality-call"):
            assert r["note"], r["id"]


def test_decisions_lint():
    """Every register id the reader cites for a B30 exists and is silent; every silent decision
    is computed by a choice point that cites one of its rows."""
    by = {r["id"]: r for r in rows()}
    cited = set(re.findall(r"S\d{4}", BIDS))
    for rid in cited:
        assert rid in by, rid
    used = {by[rid]["decision"] for rid in cited if by[rid]["class"] == "silent"}
    for rid in re.findall(r'choice_point\(fails, "([^"]+)"', BIDS):
        first = rid.split(",")[0].strip()
        assert by[first]["class"] == "silent", rid
    for r in rows():
        if r["class"] == "silent":
            assert r["decision"] in used, (r["id"], r["decision"])


def test_rules_view_is_current():
    """bids/RULES-1.0.1.md is generated from the register (tools/rules_view.py); Patsak's rulings
    on S0126 and S0235 (25 Oct 2026 22:29) are in it with their sentences."""
    import subprocess
    import sys
    tool = os.path.join(os.path.dirname(__file__), "..", "tools", "rules_view.py")
    assert subprocess.run([sys.executable, tool, "--check"]).returncode == 0
    text = open(os.path.join(os.path.dirname(__file__), "..", "bids", "RULES-1.0.1.md"), encoding="utf-8").read()
    assert "| S0126 | \"A README file should be found" in text and "| S0235 | \"This file should follow" in text
