"""Every refusal code src/reality4 raises is mentioned in tests/, and the codes no other test
reaches are triggered here, one program each."""
import os
import re

import pytest

import bidsfix  # noqa: F401  (keeps the import order of the other test files)
import helpers
from reality4 import readers

SRC = os.path.join(helpers.HERE, "..", "src", "reality4")
CODE = r"(B[0-9]{2}|[CFIJKMNPRSTUVX][0-9]{3})"
T = "id\tv\na\t1\nb\t2\n"


def codes(text):
    return re.findall(r"^line \d+: refused \[(\w+),", text, re.M)


def run(tmp_path, body, data=T):
    p, h = helpers.tsv(tmp_path, "t.tsv", data)
    return helpers.run(f"file f = sha256:{h}\n" + body, [p])


@pytest.mark.parametrize("body,code", [
    ("claim rows(tsv(f)) is 2 $\n", "P001"),                       # a character the grammar has no use for
    ('claim cell(tsv(f), 1, 1) is "a\n', "P002"),                   # a string not closed on its line
    ("let claim = tsv(f)\n", "P004"),                              # a keyword as a name
    ("claim rows(sha256:" + "0" * 64 + ")\n", "P005"),             # a hash written inside an expression
    ("let " + "a" * 200 + " = tsv(f)\n", "P010"),                  # a name longer than the bound
    ("claim bytes(f, 0, 100000000)\n", "R004"),                     # a slice longer than the bound
    ("claim rows(tsv(f)) is 2\nclaim exceeds(rows(tsv(f)), c = 1) is 1\n", "S010"),  # 'is' on a comparison
    ("claim exceeds(widen(number(cell(tsv(f), 1, 2)), tolerance = 1), c = 1)\n", "V006"),  # [0, 2] straddles 1
])
def test_code(tmp_path, body, code):
    ok, text = run(tmp_path, body)
    assert code in codes(text), text


def test_P009_non_ascii_byte_in_the_program(tmp_path):
    p, h = helpers.tsv(tmp_path, "t.tsv", T)
    ok, text = helpers.run(f"file f = sha256:{h}\nclaim rows(tsv(f)) is 2 \u00b5\n".encode("utf-8"), [p])
    assert codes(text) == ["P009"], text


def test_K004_invisible_character_in_a_compared_literal_column(tmp_path):
    ok, text = run(tmp_path, 'claim count(where(tsv(f), eq(1, "a")))\n', "id\tv\na\t1\na\u200b\t2\n")
    assert codes(text) == ["K004"], text


def test_R008_json_nested_too_deep(tmp_path):
    p, h = helpers.tsv(tmp_path, "d.json", "[" * 5000 + "]" * 5000)
    ok, text = helpers.run(f"file f = sha256:{h}\nclaim size(f)\n", [p])
    assert ok, text   # a file-level claim does not read the JSON
    assert readers.MAX_JSON_DEPTH < 5000
    with pytest.raises(readers.Refusal) as e:
        readers.parse_json(("[" * 5000 + "]" * 5000).encode(), "d.json")
    assert e.value.code == "R008"


def test_R009_a_value_too_long_to_print():
    from fractions import Fraction

    from reality4.kernel import fmt
    with pytest.raises(readers.Refusal) as e:
        fmt(Fraction(1, 2 ** 3001))   # 3001 decimal places
    assert e.value.code == "R009"


def test_C002_a_gate_read_outside_every_named_manifest_refuses(tmp_path, monkeypatch):
    """C002 is a bug report against the BIDS reader: it can only fire if the reader reads a file
    the manifest does not list. Simulate that bug and check that the kernel refuses."""
    root = bidsfix.mini(str(tmp_path / "ds"))
    md = tmp_path / "m"
    md.mkdir()
    h = helpers.manifest(root, str(md))
    stray, hs = helpers.tsv(tmp_path, "stray.tsv", "x\n1\n")
    orig = readers.Store.measured

    def buggy(self, key, fn):
        v = orig(self, key, fn)
        self.gate.add(hs)
        return v
    monkeypatch.setattr(readers.Store, "measured", buggy)
    ok, text = helpers.run(f"dataset d = sha256:{h}\nclaim rows(participants(bids(d)))\n", [str(md), stray], [root])
    assert "C002" in codes(text), text


def test_every_raised_code_is_mentioned_in_tests():
    src = set()
    for n in os.listdir(SRC):
        if n.endswith(".py"):
            src |= set(re.findall(r"[\"']" + CODE + r"[\"']", open(os.path.join(SRC, n), encoding="utf-8").read()))
    text = ""
    for n in os.listdir(helpers.HERE):
        if n.endswith(".py"):
            text += open(os.path.join(helpers.HERE, n), encoding="utf-8").read()
    missing = sorted(src - set(re.findall(r"\b" + CODE + r"\b", text)))
    assert not missing, missing


@pytest.mark.parametrize("data,code", [
    ('id\tv\na\t"1"\n', "T005"),            # a quote: escape or not, two readings (call 7)
    ("id\tv\na\t1\u2028b\t2\n", "T006"),    # U+2028: a line break to some readers
    ("id\tv\na\t1\x0cb\n", "T006"),         # form feed
])
def test_tsv_structure_characters_refuse_file_wide(tmp_path, data, code):
    ok, text = run(tmp_path, "claim cell(tsv(f), 1, 1)\n", data)
    assert codes(text) == [code], text


def test_the_first_structure_character_in_the_file_is_named(tmp_path):
    """The message names the first such character in the file, whatever the hash seed (envmatrix)."""
    ok, text = run(tmp_path, "claim rows(tsv(f))\n", "id\tv\na\t1\x0c\u2028\n")
    assert "U+000C" in text and "U+2028" not in text, text
