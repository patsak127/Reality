"""Every earlier Reality text kept in tests/old (v1's demos, v1's NARPS demos, and the programs
of the Opus 5.5 review of v1) is refused by v2: none of them forms anything (N8, N12)."""
import os

import pytest

import helpers

OLD = os.path.join(helpers.HERE, "old")
FILES = sorted(f for f in os.listdir(OLD) if f.endswith(".rl"))


def test_there_are_old_programs():
    assert len(FILES) == 48   # 64 upstream; the 16 v1 demos of a private client case are left out of this repo


@pytest.mark.parametrize("fn", FILES)
def test_old_program_forms_nothing(fn):
    with open(os.path.join(OLD, fn), "rb") as f:
        ok, text = helpers.run(f.read())
    assert not ok and "formed" not in text
