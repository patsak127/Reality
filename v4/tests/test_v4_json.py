"""Principle section 11 (25 Oct 2026, 21:14) and v4 SPEC 7.5: JSON as a file-level reader."""
import pytest

from helpers import run


def put(tmp_path, data: bytes, name="side.json"):
    import hashlib
    p = tmp_path / name
    p.write_bytes(data)
    return str(p), hashlib.sha256(data).hexdigest()


def first(tmp_path, data, claim):
    p, h = put(tmp_path, data)
    ok, text = run(f"file f = sha256:{h}\nlet j = json(f)\n{claim}\n", [p])
    return ok, text.split("\n")[0]


SIDE = b'{"RepetitionTime": 1.52, "TaskName": "milkyway", "SliceTiming": [0, 0.76], "Nested": {"a": 2}}'


def test_member_number_names_the_json_value(tmp_path):
    ok, line = first(tmp_path, SIDE, 'claim member(j, "RepetitionTime")')
    assert ok and line == 'line 3: formed: Member["RepetitionTime" of JSON[#1]] = 1.52 (Exact)', line


def test_member_has_no_unit(tmp_path):
    ok, line = first(tmp_path, SIDE, 'claim member(j, "RepetitionTime") is 1.52 s')
    assert not ok and "[U002" in line, line


def test_member_comparison_and_string_and_item_and_nesting(tmp_path):
    assert first(tmp_path, SIDE, 'claim below(member(j, "RepetitionTime"), c = 1.6)')[0]
    ok, line = first(tmp_path, SIDE, 'claim member(j, "TaskName") is "milkyway"')
    assert ok, line
    ok, line = first(tmp_path, SIDE, 'claim item(member(j, "SliceTiming"), 2)')
    assert ok and line.endswith('Item[2 of Member["SliceTiming" of JSON[#1]]] = 0.76 (Exact)'), line
    ok, line = first(tmp_path, SIDE, 'claim member(member(j, "Nested"), "a")')
    assert ok and line.endswith("= 2 (Exact)"), line


def test_missing_member_and_wrong_shape_refuse_v002(tmp_path):
    for claim in ('claim member(j, "EchoTime")', 'claim item(j, 1)', 'claim member(member(j, "SliceTiming"), "a")',
                  'claim item(member(j, "SliceTiming"), 3)'):
        ok, line = first(tmp_path, SIDE, claim)
        assert not ok and "[V002" in line, (claim, line)


def test_object_itself_is_not_a_claim(tmp_path):
    ok, line = first(tmp_path, SIDE, 'claim member(j, "Nested")')
    assert not ok and "[S009" in line, line


@pytest.mark.parametrize("data,code", [
    (b'{"a": 1, "a": 2}', "J002"),                      # duplicate key
    (b'{"a": 1, "\\u0061": 2}', "J002"),                # the same key through an escape
    (b'{"a": 1e1001}', "R007"),                         # exponent beyond the bound
    (b'{"a": 1e1000000}', "R007"),
    (b'{"a": NaN}', "J003"),
    (b'{"a": Infinity}', "J003"),
    (b'{"a": "\\ud800"}', "J003"),                      # lone surrogate in an escape
    (b'{"\\udc00": 1}', "J003"),                        # ... in a key
    (b'\xef\xbb\xbf{"a": 1}', "T001"),                  # byte-order mark
    (b'{"a": "\xff"}', "T001"),                         # not UTF-8
    (b'{"a": 01}', "J001"),                             # leading zero: not JSON
    (b'{"a": 1,}', "J001"),                             # trailing comma
    (b'{"a": .5}', "J001"),
    (b'{"a": 1} x', "J001"),
    (b'[' * 200 + b']' * 200, "R008"),                  # depth
    (b'{"a": ' + b'1' * 1001 + b'}', "R007"),            # digits
])
def test_every_json_ambiguity_refuses(tmp_path, data, code):
    ok, line = first(tmp_path, data, 'claim member(j, "a")')
    assert not ok and f"[{code}" in line, (data[:40], line)


def test_true_false_null_refuse_j004(tmp_path):
    for v in (b"true", b"false", b"null"):
        ok, line = first(tmp_path, b'{"a": ' + v + b'}', 'claim member(j, "a")')
        assert not ok and "[J004" in line, line


def test_lookalike_sibling_key_refuses_k003(tmp_path):
    ok, line = first(tmp_path, '{"TaskName": "x", "TaskNаme": "y"}'.encode(), 'claim member(j, "TaskName")')
    assert not ok and "[K003" in line, line


def test_invisible_key_refuses_k004(tmp_path):
    ok, line = first(tmp_path, '{"a\u200b": 1}'.encode(), 'claim member(j, "a\\xe2\\x80\\x8b")')
    assert not ok and "[K004" in line, line


def test_self_difference_of_a_member_is_idle(tmp_path):
    ok, line = first(tmp_path, SIDE, 'claim difference(member(j, "RepetitionTime"), member(j, "RepetitionTime"))')
    assert not ok and "[S008" in line, line


def test_unequal_members_difference_forms(tmp_path):
    ok, line = first(tmp_path, b'{"a": 3, "b": 1}', 'claim difference(member(j, "a"), member(j, "b"))')
    assert ok and line.endswith("= 2 (Exact)"), line


def test_idle_json_value_found_by_the_witness(tmp_path):   # no hand rule sees this; W1 does
    p, h = put(tmp_path, SIDE)
    ok, text = run(f'file f = sha256:{h}\nlet j = json(f)\nlet x = member(j, "RepetitionTime")\nclaim difference(x, widen(x, tolerance = 1))\n', [p])
    line = text.split("\n")[0]
    assert not ok and "[S008" in line and "W1" in line, line


def test_exponents_read_exactly(tmp_path):   # Patsak 25 Oct 21:36: one exact reading, so accepted
    for text, want in ((b'{"a": 1.5e0}', "= 1.5 (Exact)"), (b'{"a": 15E-1}', "= 1.5 (Exact)"),
                       (b'{"a": 1e-3}', "= 0.001 (Exact)"), (b'{"a": -2E+2}', "= -200 (Exact)")):
        ok, line = first(tmp_path, text, 'claim member(j, "a")')
        assert ok and line.endswith(want), (text, line)
