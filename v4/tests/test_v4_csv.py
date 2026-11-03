"""Principle section 12 (25 Oct 2026, 22:10) and v4 SPEC 6.5: CSV as a file-level reader.

The end-to-end real-file case of the upstream suite is not included in this repository."""
import hashlib
import os

import pytest

from helpers import HERE, run
from reality4 import readers as R


def t(data):
    return R.parse_csv(data, "x", R.Steps())


def code(data):
    try:
        t(data)
    except R.Refusal as e:
        return e.code
    return None


def test_rfc4180_quoting_and_bytes_untrimmed():
    tab = t(b'a,b\r\n"x,""y""",Female \r\n"",\r\n')
    assert tab.header == ["a", "b"] and tab.rows == [['x,"y"', "Female "], ["", ""]]
    assert t(b"a,b\n1,2").rows == [["1", "2"]]                  # last line without a line end


@pytest.mark.parametrize("data,want", [
    (b"a,b\n1\n", "T004"),                    # ragged row
    (b"a,b\n1,2,3\n", "T004"),
    (b'a,b\nx"y,2\n', "T008"),                # quote inside an unquoted field
    (b'a,b\n"x"y,2\n', "T008"),               # text after a closing quote
    (b'a,b\n"x\n",2\n', "T008"),              # line break inside quotes
    (b"a,b\r\n1,2\n", "T010"),                # mixed line ends
    (b"a,b\r1,2\r", "T002"),                  # lone CR
    (b"a;b\n1;2\n", "T009"),                  # another delimiter
    (b"a\tb\n1\t2\n", "T009"),
    (b"a,\n1,2\n", "T007"),                   # blank header name
    (b"a,b\n\n1,2\n", "T003"),                # blank line inside
    (b"", "T003"),
    (b"a,b\n\xff,1\n", "T001"),               # not UTF-8
    (b"a,b\n1,\xe2\x80\xa8\n", "T006"),       # U+2028
    (b'a,b\n";",1\n', None),                  # a semicolon inside quotes is a cell byte
    (b"a,b\n1,2\n\n", None),                  # one final empty line: no row (as TSV)
])
def test_every_csv_ambiguity_refuses(data, want):
    assert code(data) == want


def test_repeated_header_refuses_when_named():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        data = b"g,g\n1,2e0\n"
        p = os.path.join(d, "x.csv")
        open(p, "wb").write(data)
        h = hashlib.sha256(data).hexdigest()
        ok, text = run(f'file f = sha256:{h}\nlet t = csv(f)\nclaim count(where(t, eq("g", "1")))\n', [p])
        assert not ok and "[K002" in text
        ok, text = run(f'file f = sha256:{h}\nlet t = csv(f)\nclaim mean(t, 2) is 2\n', [p])
        assert ok, text                                           # numbers: the same exact reader
