"""v4 reader changes (SPEC 6.1, 6.2): CR LF, one trailing empty line, blank headers, BIDS empty cells."""
import pytest

from reality4.readers import Refusal, Steps, parse_tsv
from reality4 import bids101


def tsv(b):
    return parse_tsv(b, "0" * 64, Steps())


def code(f, *a):
    with pytest.raises(Refusal) as e:
        f(*a)
    return e.value.code


def test_crlf_is_a_line_end():
    t = tsv(b"a\tb\r\n1\t2\r\n")
    assert t.header == ["a", "b"] and t.rows == [["1", "2"]]


def test_mixed_line_ends_refuse():
    """Patsak, 25 Oct 2026 22:29: TSV refuses mixed line ends, as CSV does (principle section 12)."""
    assert code(tsv, b"a\tb\n1\t2\r\n3\t4\n") == "T010"
    assert code(tsv, b"a\tb\r\n1\t2\n") == "T010"
    with pytest.raises(Refusal) as e:
        bids101.bids_tsv(b"participant_id\tg\r\nsub-01\tA\n", "0" * 64, "participants.tsv", Steps())
    assert e.value.code == "T010"


@pytest.mark.parametrize("data", [b"a\tb\r1\t2\n", b"a\tb\n1\t2\r", b"a\tb\n1\t\r2\n", b"a\r\n\r"])
def test_lone_cr_refuses(data):
    assert code(tsv, data) == "T002"


def test_crlf_leaves_no_cr_in_cells():
    t = tsv(b"a\tb\r\nx\t\r\n")
    assert t.rows == [["x", ""]]


def test_one_trailing_empty_line_multicolumn_is_no_row():
    assert tsv(b"id\tg\ns1\tA\ns2\tB\n\n").rows == [["s1", "A"], ["s2", "B"]]
    assert tsv(b"id\tg\r\ns1\tA\r\n\r\n").rows == [["s1", "A"]]


def test_two_trailing_empty_lines_refuse():
    assert code(tsv, b"id\tg\ns1\tA\n\n\n") == "T003"


def test_empty_line_inside_refuses():
    assert code(tsv, b"id\tg\n\ns1\tA\n") == "T003"


def test_one_column_trailing_empty_line_refuses():
    assert code(tsv, b"id\ns1\n\n") == "T003"


@pytest.mark.parametrize("data", [b"a\t\n1\t2\n", b"\tb\n1\t2\n", b"a\tb\t\n1\t2\t\n"])
def test_blank_header_refuses_t007(data):
    assert code(tsv, data) == "T007"


def test_bids_tsv_trailing_empty_line_refuses():
    assert code(bids101.bids_tsv, b"participant_id\tg\nsub-01\tA\n\n", "0" * 64, "participants.tsv", Steps()) == "T003"


@pytest.mark.parametrize("data", [b"participant_id\tg\nsub-01\t\n", b"participant_id\tg\tage\nsub-01\tA\t\n"])
def test_bids_tsv_empty_cell_refuses_b04(data):
    assert code(bids101.bids_tsv, data, "0" * 64, "participants.tsv", Steps()) == "B04"


def test_bids_tsv_crlf_reads():
    t = bids101.bids_tsv(b"participant_id\tg\r\nsub-01\tA\r\n", "0" * 64, "participants.tsv", Steps())
    assert t.rows == [["sub-01", "A"]]
