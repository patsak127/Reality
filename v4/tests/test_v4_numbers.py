"""v4 SPEC 6.3 and 7.1: number columns read over selected rows; variance, order, median."""
from helpers import run, tsv

DATA = "id\tg\tx\r\ns1\tF\t18\r\ns2\tF\t27\r\ns3\tC\t30 \r\ns4\tF\t20\r\n"


def prog(h, *claims):
    return "\n".join([f"file f = sha256:{h}", "let t = tsv(f)", 'let s = where(t, eq("g", "F"))', *claims]) + "\n"


def one(tmp_path, claim):
    p, h = tsv(tmp_path, "c.tsv", DATA)
    ok, text = run(prog(h, claim), [p])
    return ok, text.split("\n")[0]


def test_mean_over_selection_skips_unselected_non_decimal(tmp_path):   # finding 12
    ok, line = one(tmp_path, 'claim mean(s, "x")')
    assert ok and line.endswith("= 65/3 (Exact)"), line


def test_mean_over_base_still_refuses_v005(tmp_path):
    ok, line = one(tmp_path, 'claim mean(t, "x")')
    assert not ok and "[V005" in line and "row 3" in line, line


def test_selected_non_decimal_refuses_v005(tmp_path):
    ok, line = one(tmp_path, 'claim max(where(t, ne("g", "z")), "x")')
    assert not ok and "[V005" in line, line


def test_sample_and_population_variance_exact(tmp_path):
    assert one(tmp_path, 'claim sample_variance(s, "x")')[1] == 'line 4: formed: SampleVariance[Rows[TSV[#1] where col 2 = "F"], col 3] = 67/3 (Exact)'
    assert one(tmp_path, 'claim population_variance(s, "x")')[1].endswith("= 134/9 (Exact)")


def test_variance_needs_two(tmp_path):
    ok, line = one(tmp_path, 'claim sample_variance(where(t, eq("id", "s1")), "x")')
    assert not ok and "[V003" in line, line
    ok, line = one(tmp_path, 'claim population_variance(where(t, eq("id", "s1")), "x")')
    assert ok and line.endswith("= 0 (Exact)"), line


def test_order_and_median(tmp_path):
    assert one(tmp_path, 'claim order(s, "x", 1)')[1].endswith("= 18 (Exact)")
    assert one(tmp_path, 'claim order(s, "x", 3)')[1].endswith("= 27 (Exact)")
    assert one(tmp_path, 'claim median(s, "x")')[1].endswith("= 20 (Exact)")
    ok, line = one(tmp_path, 'claim order(s, "x", 4)')
    assert not ok and "[V003" in line
    ok, line = one(tmp_path, 'claim order(s, "x", 0)')
    assert not ok and "[S006" in line


def test_median_even_count_refuses_v009(tmp_path):
    ok, line = one(tmp_path, 'claim median(where(t, ne("id", "s3"), ne("id", "s4")), "x")')
    assert not ok and "[V009" in line, line


# ---- blockers 5 and 6 (v4 SPEC 7.3, 7.1) ----

def test_number_condition_selects_by_value(tmp_path):
    ok, line = one(tmp_path, 'claim count(where(t, eq("g", "F"), ge("x", c = 20)))')
    assert ok and line.endswith("= 2 (Exact)"), line
    assert "col 3 >= 20" in line, line


def test_number_condition_reads_only_rows_the_byte_conditions_keep(tmp_path):
    # row 3 holds "30 " (not a decimal); eq("g","F") drops it whatever order the conditions are written in
    for claim in ('claim count(where(t, lt("x", c = 25), eq("g", "F")))', 'claim count(where(t, eq("g", "F"), lt("x", c = 25)))'):
        ok, line = one(tmp_path, claim)
        assert ok and line.endswith("= 2 (Exact)"), line


def test_number_condition_on_a_non_decimal_refuses_v005(tmp_path):
    ok, line = one(tmp_path, 'claim count(where(t, gt("x", c = 1)))')
    assert not ok and "[V005" in line, line


def test_number_condition_takes_no_unit(tmp_path):
    ok, line = one(tmp_path, 'claim count(where(t, gt("x", c = 1 s)))')
    assert not ok and "[U002" in line, line


def test_contradictory_number_conditions_refuse_s011(tmp_path):
    ok, line = one(tmp_path, 'claim count(where(s, gt("x", c = 30), lt("x", c = 20)))')
    assert not ok and "[S011" in line, line


def test_implied_number_condition_refuses_s008(tmp_path):
    ok, line = one(tmp_path, 'claim count(where(s, gt("x", c = 30), gt("x", c = 20)))')
    assert not ok and "[S008" in line, line


def test_share_of_a_selection(tmp_path):
    ok, line = one(tmp_path, 'claim share(where(s, lt("x", c = 25)), s)')
    assert ok and line.endswith("= 2/3 (Exact)"), line


def test_share_of_needs_base_conditions_in_sel(tmp_path):
    ok, line = one(tmp_path, 'claim share(s, where(t, eq("g", "C")))')
    assert not ok and "[S006" in line, line
    ok, line = one(tmp_path, 'claim share(s, s)')
    assert not ok and "[S008" in line, line


def test_witness_search_bound_refuses_r013(tmp_path, monkeypatch):   # v4 SPEC 4.5
    from reality4 import witness
    monkeypatch.setattr(witness, "MAX_WITNESS_STEPS", 10)
    ok, line = one(tmp_path, 'claim mean(s, "x")')
    assert not ok and "[R013" in line, line


def test_empty_literal_is_a_readable_cell_beside_another_column(tmp_path):   # witness audit, 2026-10-25
    p, h = tsv(tmp_path, "e.tsv", "id\tg\ns1\t\ns2\tF\n")
    ok, text = run(f'file f = sha256:{h}\nlet t = tsv(f)\nclaim count(where(t, eq(2, "")))\n', [p])
    assert ok and text.split("\n")[0].endswith("= 1 (Exact)"), text


def test_count_bound_with_excluding_conditions_forms(tmp_path):   # witness audit, 2026-10-25
    # the witness rows must be able to pass ne(1, ...) and eq(4, ...) at once, many times over
    p, h = tsv(tmp_path, "w.tsv", "a\tb\tc\td\nx\t1\t2\trn\ns1\t1\t2\trn\n")
    ok, text = run(f'file f = sha256:{h}\nlet t = tsv(f)\nclaim atmost(count(where(where(t, ne(1, "equalRange"), eq(4, "rn")), ne(1, "s1"))), c = 300)\n', [p])
    assert ok and text.split("\n")[0].endswith("holds"), text


# ---- standard deviations as exact roots (SPEC 7.2; Patsak 25 Oct: bare names refuse) ----

def test_sample_sd_is_an_exact_root(tmp_path):
    ok, line = one(tmp_path, 'claim sample_sd(s, "x")')
    assert ok and line == 'line 4: formed: SampleSD[Rows[TSV[#1] where col 2 = "F"], col 3] = sqrt(67/3) (Exact)', line
    ok, line = one(tmp_path, 'claim population_sd(s, "x")')
    assert ok and line.endswith("= sqrt(134/9) (Exact)"), line


def test_sd_comparisons_decided_by_squaring(tmp_path):
    assert one(tmp_path, 'claim below(sample_sd(s, "x"), c = 4.73)')[0]          # 4.73^2 = 22.3729 > 67/3
    ok, line = one(tmp_path, 'claim below(sample_sd(s, "x"), c = 4.72)')            # 22.2784 < 67/3
    assert not ok and "[V001" in line, line


def test_widened_sd_straddling_a_cutoff_refuses_v006(tmp_path):
    ok, line = one(tmp_path, 'claim below(widen(sample_sd(s, "x"), tolerance = 0.1), c = 4.8)')
    assert not ok and "[V006" in line, line


def test_rational_sd_prints_as_a_rational(tmp_path):
    p, h = tsv(tmp_path, "r.tsv", "id\tx\na\t1\nb\t3\n")
    ok, text = run(f'file f = sha256:{h}\nlet t = tsv(f)\nclaim population_sd(t, "x")\n', [p])
    assert ok and text.split("\n")[0].endswith("= 1 (Exact)"), text


def test_bare_variance_and_sd_refuse_v009(tmp_path):
    for fn in ("variance", "sd", "pvariance", "psd"):
        ok, line = one(tmp_path, f'claim {fn}(s, "x")')
        assert not ok and "[V009" in line and "sample_" in line, line


def test_difference_with_a_root_refuses_s006(tmp_path):
    ok, line = one(tmp_path, 'claim difference(sample_sd(s, "x"), mean(s, "x"))')
    assert not ok and "[S006" in line, line


def test_exponent_cells_read_exactly(tmp_path):   # SPEC 6.4, one number reader with JSON
    p, h = tsv(tmp_path, "e.tsv", "id\tx\na\t1.5e1\nb\t-5E-1\n")
    ok, text = run(f'file f = sha256:{h}\nlet t = tsv(f)\nclaim sum(t, "x")\n', [p])
    assert ok and text.split("\n")[0].endswith("= 14.5 (Exact)"), text
