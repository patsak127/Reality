"""D4 (BB's call on Patsak's behalf, 2026-10-26, reversible): a share whose numerator restates the base's
condition in a nested where() stays refused (S008), and the message names the one spelling that forms."""
import pytest

import helpers
from reality4 import readers as R
from reality4.kernel import check

TABLE = b"group\tsite\nA\ts1\nB\ts2\nP\ts1\nA\ts2\n"
CASES = [
    ('share(where(where(t, ne("group", "P")), eq("group", "A")), where(t, ne("group", "P")))',
     'share(where(t, ne("group", "P"), eq("group", "A")), where(t, ne("group", "P")))'),
    ('atleast(share(where(where(t, ne("group", "P")), eq("group", "A")), where(t, ne("group", "P"))), c = 1/2)',
     'share(where(t, ne("group", "P"), eq("group", "A")), where(t, ne("group", "P")))'),
    ('share(where(where(t, ne("group", "P"), eq("site", "s1")), eq("group", "A")), where(t, ne("group", "P")))',
     'share(where(t, ne("group", "P"), eq("site", "s1"), eq("group", "A")), where(t, ne("group", "P")))'),
]


def verdict(tmp_path, stmt):
    p, h = helpers.tsv(str(tmp_path), "g.tsv", TABLE)
    prog = f"file f = sha256:{h}\nlet t = tsv(f)\nclaim {stmt}\n".encode()
    _, lines = check(prog, R.Store([p]))
    return next(ln for ln in lines if ln.startswith("line 3"))


@pytest.mark.parametrize("nested,flat", CASES, ids=["plain", "atleast", "extra-condition"])
def test_nested_share_refuses_and_names_the_flat_spelling(tmp_path, nested, flat):
    v = verdict(tmp_path, nested)
    assert v.startswith("line 3: refused [S008"), v
    assert "the one spelling of this share is " + flat.replace("(t,", "(tsv(f),") in v, v


@pytest.mark.parametrize("nested,flat", CASES, ids=["plain", "atleast", "extra-condition"])
def test_the_named_spelling_forms(tmp_path, nested, flat):
    assert verdict(tmp_path, flat).startswith("line 3: formed"), flat


def test_other_s008_messages_do_not_name_a_spelling(tmp_path):
    v = verdict(tmp_path, 'count(where(where(t, eq("group", "A")), ne("group", "P")))')
    assert v.startswith("line 3: refused [S008") and "one spelling" not in v, v
