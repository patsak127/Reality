"""Spec fixes after the checker-B run (AMBIGUITIES.md A3, B2, B5, E1) and the two small code
issues (an unreadable program file; README/CHANGES BOM is in test_bids_closed_lists.py)."""
import os
import subprocess
import sys

import helpers
from reality4.readers import Refusal
from reality4.sorts import File, Lit, S

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
BIG = 2 ** 3100   # 934 digits: allowed in the program (R010 is 1000), but 1/BIG needs 3100 places


def codes(text):
    import re
    return re.findall(r"^line \d+: refused \[(\w+), ([^\]]+)\]", text, re.M)


def test_r009_never_depends_on_a_message(tmp_path):
    """A3: S011's message would print a cutoff with 3100 decimal places; messages never raise
    R009, so the code is S011. A comparison that holds still refuses R009 when its sort is built."""
    _, h = helpers.tsv(tmp_path, "t.tsv", "a\tb\nx\ty\n")
    prog = (f"file f = sha256:{h}\n"
            f'claim exceeds(share(where(tsv(f), eq(1, "x"))), c = {BIG + 1}/{BIG})\n'
            f"claim atleast(count(tsv(f)), c = 1/{BIG})\n")
    ok, text = helpers.run(prog, [str(tmp_path)])
    # v4: the hand S011 is gone; a claim false on every input refuses V001 on these bytes
    assert [c for c, _ in codes(text)] == ["V001", "R009"], text


def test_r006_counts_sorts_files_and_literals_not_text():
    assert S("a", "b", "c").size == 1
    assert S("Rows[", File("0" * 64), " where ", Lit(b"x"), "]").size == 3
    assert S("Difference[", S("A"), ", ", S("B"), "]").size == 3


def test_ratio_without_denominator_is_p001_and_long_strings(tmp_path):
    """B5: INT "/" not followed by INT is P001 (a ratio is a grammar form). B2: a string is scanned
    to its closing quote first (P002 if unclosed or a bad escape), then its decoded length > 4096
    is R001."""
    long = "a" * 5000
    prog = ("claim f(c = 1/x)\nclaim f(c = 1/)\n"
            f'claim f("{long}\nclaim f("{long}")\nclaim f("{long}\\q")\nclaim f("{"\\x41" * 4096}")\n')
    ok, text = helpers.run(prog)
    assert [c for c, _ in codes(text)] == ["P001", "P001", "P002", "R001", "P002", "S002"], text


def _cli(*args):
    env = dict(os.environ, PYTHONPATH=SRC)
    return subprocess.run([sys.executable, "-m", "reality4", "check", *args], capture_output=True, env=env)


def test_unreadable_program_file_refuses_without_traceback(tmp_path):
    for p in (str(tmp_path / "missing.rl"), str(tmp_path)):
        r = _cli(p)
        out = r.stdout.decode()
        assert r.returncode == 1 and r.stderr == b"", (r.stderr, out)
        assert out.startswith("line 0: refused [F001, text]:") and out.endswith("refused: the program is not Reality text\n"), out
    q = tmp_path / "locked.rl"
    q.write_bytes(b"claim x\n")
    undo = helpers.unreadable(str(q))
    try:
        r = _cli(str(q))
        assert r.returncode == 1 and r.stderr == b"" and b"[F001, text]" in r.stdout, r
    finally:
        undo()
