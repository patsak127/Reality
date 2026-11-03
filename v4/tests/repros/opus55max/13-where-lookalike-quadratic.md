# 13. `where` is quadratic in the number of distinct cells, outside the step count

**Category:** bug (slow; the step bound R002 does not bound time). v1 finding 11 returns.
**Spec clause:** §1 item 4 ("the checker's … speed"); SPEC §2 item 12; SPEC §5 row 11 ("fixed:
counted steps (R002)").
**Severity:** medium. **Confidence:** high.

## Program

Made by `python -I findings\13-gen.py N`: a TSV whose column 1 holds N distinct keys
`k0 … k{N-1}`, and `findings\13-where-lookalike-quadratic-N.rl`:

```
file f = sha256:<hash of 13-distinct-N.tsv>
let t = tsv(f)
claim rows(t)
claim count(where(t, eq(1, "k5")))
```

`13-distinct-20000.tsv` (169 KB) and `13-distinct-80000.tsv` (709 KB) are included.

## Commands and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\13-where-lookalike-quadratic-20000.rl --files findings\13-distinct-20000.tsv
line 3: formed: RowCount[TSV[#1]] = 20000 (Exact)
line 4: formed: Count[Rows[TSV[#1] where col 1 = "k5"]] = 1 (Exact)
accepted
[exit code 0; wall 1.3 s; peak private memory 16 MB]

> python -m reality2 check findings\13-where-lookalike-quadratic-80000.rl --files findings\13-distinct-80000.tsv
line 3: formed: RowCount[TSV[#1]] = 80000 (Exact)
line 4: formed: Count[Rows[TSV[#1] where col 1 = "k5"]] = 1 (Exact)
accepted
[exit code 0; wall 25.1 s; peak private memory 34 MB]
```

Four times the rows, about 19 times the time (an earlier run: 1.4 s and 23.4 s). With
N = 160,000 (a 1.49 MB file, `13-gen.py 160000`) the run is still going when stopped at 60 s. The counted steps of that check are under 10^6, against
`MAX_STEPS` = 2 × 10^8.

## Cause

`Checker.no_lookalike` collects the column's distinct values in a Python list and tests each
cell with `not in vals` (`kernel.py:293-296`): O(rows × distinct values) comparisons, none of them
counted. The other loops in `where` add `len(idx)` steps; this one adds nothing.

## What would fix it

Use a set (or a dict from skeleton to value, as `keys.lookalikes` already does) and count one step
per cell. Then the step bound is a bound on this work, as SPEC claims.
