"""Gate F: the demo transcript is reproduced byte for byte, with a throwaway test key."""
import re, subprocess, sys
from pathlib import Path

REQ = Path(__file__).resolve().parents[1]
EXPECTED = REQ / "demo" / "expected" / "transcript.txt"


def test_demo_transcript_byte_for_byte(tmp_path, demo_data):
    r = subprocess.run([sys.executable, str(REQ / "demo" / "demo.py"), "--work", str(tmp_path / "w")],
                       capture_output=True, timeout=900)
    assert r.returncode == 0, r.stderr.decode()[-2000:]
    assert r.stdout == EXPECTED.read_bytes()


def test_transcript_has_the_story_in_order():
    t = EXPECTED.read_text()
    marks = ["G001 refused", "PROPOSED", "M1 ADOPTED", "M1 HOLDS", "M1 DOES NOT HOLD",
             "M2 DOES NOT HOLD", "G014 refused", "G012 refused", "F1 ADOPTED", "F1 DOES NOT HOLD",
             "G001 refused: task T4", "P1 ADOPTED", "P1 DOES NOT HOLD", "G014 refused: the adoption on line 45",
             "P1 HOLDS", "P1 WITHDRAWN", "measure P1b proposed", "P1b ADOPTED", "P1b HOLDS",
             "G001 refused: task T5", "E1 ADOPTED", "E1 DOES NOT HOLD", "E2 DOES NOT HOLD", "G014 refused: the adoption on line 70",
             "E1 was NOT CHECKED", "E1 WITHDRAWN", "measure E1b proposed", "E1b ADOPTED", "E1b HOLDS", "E1 (withdrawn; adopted line 70",
             "measure Gate proposed", "Gate ADOPTED", "Gate HOLDS as a composite"]
    pos = [t.find(m) for m in marks]
    assert -1 not in pos and pos == sorted(pos), list(zip(marks, pos))
    assert "TEST key, not Patsak's" in t



def test_readme_copies_only_public_material():
    md = (REQ / "demo" / "README.md").read_text()
    for line in md.splitlines():
        if re.search(r"\b(cp|scp|rsync|cat)\b.*reality_adopt\b(?!\.pub)", line):
            raise AssertionError("README line handles the private key: " + line)
    assert "reality_adopt.pub" in md and "allowed_signers" in md
