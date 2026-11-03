"""v4 SPEC 5.1 and 5.3: one value, one tolerance, judged on value identity (the computation, the
files, the positions read), not on spelling; an exact use counts as tolerance 0 (Patsak, 25 Oct)."""
from helpers import run, tsv

DATA = "id\tg\tx\ns1\tF\t18\ns2\tF\t27\ns3\tM\t30\ns4\tF\t20\n"


def lines(tmp_path, *claims, data=DATA):
    p, h = tsv(tmp_path, "c.tsv", data)
    ok, text = run("\n".join([f"file f = sha256:{h}", "let t = tsv(f)", *claims]) + "\n", [p])
    return ok, [l for l in text.split("\n") if l.startswith("line ")]


def test_two_spellings_of_one_selection_are_one_value(tmp_path):
    ok, out = lines(tmp_path, 'claim below(widen(mean(where(t, eq("g", "F")), "x"), tolerance = 1), c = 30)',
                    'claim below(widen(mean(where(t, ne("g", "M")), "x"), tolerance = 2), c = 30)')
    assert not ok and all("[S012" in l for l in out), out


def test_exact_use_is_tolerance_zero(tmp_path):
    ok, out = lines(tmp_path, 'claim mean(where(t, eq("g", "F")), "x")',
                    'claim below(widen(mean(where(t, eq("g", "F")), "x"), tolerance = 1), c = 30)')
    assert not ok and all("[S012" in l for l in out), out


def test_one_tolerance_everywhere_forms(tmp_path):
    ok, out = lines(tmp_path, 'claim below(widen(mean(where(t, eq("g", "F")), "x"), tolerance = 1), c = 30)',
                    'claim atleast(widen(mean(where(t, ne("g", "M")), "x"), tolerance = 1), c = 20)')
    assert ok, out


def test_different_rows_are_different_values(tmp_path):
    ok, out = lines(tmp_path, 'claim below(widen(mean(where(t, eq("g", "F")), "x"), tolerance = 1), c = 30)',
                    'claim below(widen(mean(where(t, eq("g", "M")), "x"), tolerance = 2), c = 40)',
                    'claim mean(t, "x")')
    assert ok, out


def test_cell_by_key_and_by_position_is_one_value(tmp_path):
    ok, out = lines(tmp_path, 'claim number(cell(t, key("id", "s2"), "x"))',
                    'claim below(widen(number(cell(t, 2, 3)), tolerance = 1), c = 30)')
    assert not ok and all("[S012" in l for l in out), out


def test_json_member_through_two_spellings_is_one_value(tmp_path):
    import hashlib
    data = b'{"a": 1.5}'
    p = tmp_path / "s.json"
    p.write_bytes(data)
    h = hashlib.sha256(data).hexdigest()
    ok, text = run(f'file f = sha256:{h}\nlet j = json(f)\nclaim below(widen(member(j, "a"), tolerance = 1), c = 3)\n'
                   f'claim below(widen(member(json(f), "a"), tolerance = 0.5), c = 3)\n', [str(p)])
    assert not ok and text.count("[S012") == 2, text


def test_affine_widen_cancels_one_value_with_itself(tmp_path):   # v4 SPEC 5.2
    ok, out = lines(tmp_path, 'let a = mean(where(t, eq("g", "F")), "x")', 'let b = mean(where(t, eq("g", "M")), "x")',
                    'claim difference(widen(a, tolerance = 1), difference(widen(a, tolerance = 1), b))')
    assert ok and out[-1].endswith("= 30 (Exact)"), out


def test_independent_values_widen_independently(tmp_path):
    ok, out = lines(tmp_path, 'let a = mean(where(t, eq("g", "F")), "x")', 'let b = mean(where(t, eq("g", "M")), "x")',
                    'claim difference(widen(a, tolerance = 1), widen(b, tolerance = 1))')
    assert ok and out[-1].endswith("lies within [-31/3, -19/3] (Interval)"), out
