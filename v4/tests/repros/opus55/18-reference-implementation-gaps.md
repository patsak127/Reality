# 18. `reality2_ref` disagrees with the checker on `share … is` and on row 0; the differential test never exercises either

- **Category:** docs overclaim (README: "a second implementation of the plain-TSV fragment … with 'is'", "agreeing with the checker on 16 000 random claims") and a bug in the reference
- **Spec clauses:** §6 plan item 5 ("each with a second implementation"); README "What checks the trusted base"
- **Severity:** medium (the evidence is weaker than claimed). **Confidence:** high.

## What happens

- `ref.evaluate(data, q, is_)` has an `is` path, but `tests/test_differential.py` never passes `is_`.
  When `is_` is given for a share, the reference ignores it and forms. reality2 refuses a wrong share
  with V001.
- Row positions in the test are drawn from 1–7, so row 0 is never tried. The reference's `rowpos`
  checks only `r > len(rows)`, so row 0 returns `rows[-1]`, the *last* row. reality2 refuses with S006.
- Both implementations call `int()`/`Fraction()` on digit strings, so both crash in the same way on a
  5 000-digit cell (finding 05). A shared failure mode is not caught by agreement.
- Not covered at all: `difference`, `size`, `bytes`, the printed sort (so finding 02 is invisible), the
  check-2 trace, keys and lookalikes outside ASCII (both use the same ASCII-only skeleton, so finding
  11 is invisible), and all BIDS.

## Reproduce

```
.venv\Scripts\python.exe -m reality2 check findings\18-ref-disagrees.rl --files findings\18-t.tsv
.venv\Scripts\python.exe findings\gen\ref_vs_kernel.py
```

Output (`18.out`):

```
line 4: refused [V001, item 5]: the claim writes 1/3; computed from the bytes it is 2/3
line 5: refused [S006, item 1]: a row is a position: a whole number from 1
refused (2 statements)
== reality2 vs reality2_ref
share 2/3 claimed as 1/3:
  reality2     ('refused', 'V001')
  reality2_ref ('formed', ('share', (2, 3)))
count 2 claimed as 5:
  reality2     ('refused', 'V001')
  reality2_ref ('refused', 'V001')
row 0:
  reality2     ('refused', 'S006')
  reality2_ref ('formed', ('bytes', b'B'))
5000-digit decimal:
  reality2     ('EXCEPTION', 'ValueError')
  reality2_ref ('EXCEPTION', 'ValueError')
```

## Judgement

The reference was written from the same reading of the spec (same skeleton, same TSV rules, same
lookalike scope). So it can catch coding slips, but not a gap in the reading rules, and
the gaps found in this review are reading-rule gaps. Generate `is` literals, positions ≤ 0, and
printed-form comparisons in the differential test. Also write the reference's decimal reader without
`int()` on unbounded strings.
