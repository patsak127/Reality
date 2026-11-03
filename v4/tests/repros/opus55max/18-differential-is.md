# 18. The differential test does not cover `is`, sorts or `difference`; with `is` the two implementations disagree

**Category:** docs overclaim (verification claim), plus a defect in `reality2_ref`.
**Spec clause:** README ("a second implementation of the plain-TSV fragment, written separately,
agreeing with the checker on 16 000 random claims over random tables, including every case the
TSV reader refuses and lookalike cells"); `src\reality2_ref\ref.py` docstring ("the computations
rows, count, share, cell …, exceeds, below, with 'is'"); REVIEW brief (f).
**Severity:** medium. **Confidence:** high.

## Program

`findings\18-differential-is.rl` with `findings\18-table.tsv`, and the script
`findings\18-diff-is.py`, which gives the same claims to `reality2_ref` and then reruns the test's
own random generator with an `is` literal (right or wrong at random) on every claim.

```
file f = sha256:<hash of 18-table.tsv>
let t = tsv(f)
claim share(where(t, eq(2, "A"))) is 1/3
claim exceeds(number(cell(t, 1, 3)), c = 0) is 1
```

## Commands and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\18-differential-is.rl --files findings\18-table.tsv
line 3: refused [V001, item 5]: the claim writes 1/3; computed from the bytes it is 2/3
line 4: refused [S010, item 1]: a comparison claim takes no 'is'; it holds or it is refused
refused (2 statements)

> python -I findings\18-diff-is.py
Part 1: the claims of 18-differential-is.rl
  claim share(where(t, eq(2, "A"))) is 1/3
    reality2:     ('refused', 'V001')
    reality2_ref: ('formed',)
  claim exceeds(number(cell(t, 1, 3)), c = 0) is 1
    reality2:     ('refused', 'S010')
    reality2_ref: ('formed',)

Part 2: 1195 random claims with 'is'; 51 disagreements
  44 x kind=share: reality2 ('refused', 'V001'), reality2_ref ('formed',); e.g. claim share(where(t, ne(1, "B"), eq(1, "0"))) is 1/3
  7 x kind=bool: reality2 ('refused', 'S010'), reality2_ref ('formed',); e.g. claim below(widen(number(cell(t, 2, 1)), tolerance = 0.5), c = -0.5) is 1
```

## What the test actually covers

`tests\test_differential.py` compares only `(verdict, code, value)`:
- `kernel_eval` never writes `is`, and calls `ref.evaluate(data, q)` without `is_`; the reference's
  `is` handling, which the docstring advertises, is never run. When it is run, it forms a wrong
  share and an `is` on a comparison (above), and it has no notion of units (U002), ratio literals
  (P007) or decimal points in counts.
- The **sort** is never compared. The sort is the claim's subject (spec §2, "The sort is the
  claim's subject, not a note beside it"), yet a wrong row, column or file in the printed sort
  would pass the test.
- `difference`, `size` and `bytes` are in the fragment README describes (its "numbers" and
  "bytes" rows) but not in the reference.
- The generator's cells and headers come from fixed small lists (no number longer than 5
  characters, at most 6 rows), so it cannot reach findings 01, 06 or 13.
- Both implementations encode SPEC's decisions, not the principle: the reference also refuses only
  the literal repeat (S008) and checks lookalikes per literal, so the test cannot see findings 08
  or 24. That is expected of differential testing, but README's "agreeing … including every case
  the TSV reader refuses" reads as more than that.

## What would fix it

Compare the printed sort too (the reference can build the same string from its tuple query); add
`is` (with units, ratios and decimals), `difference`, `size` and `bytes` to both the reference and
the generator; draw numbers of any length and tables of a few thousand rows. And say in README
that the test checks agreement with SPEC's decisions on the TSV fragment, which it does well.
