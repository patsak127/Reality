# 07. The lookalike scan in `where()` is quadratic and uncounted: a 3.6 MB table takes many minutes

- **Category:** bug (slow; counted steps do not measure work); the item-4 risk of v1 finding 11 in a new place
- **Spec clauses:** §1 item 4 ("the checker's … speed"); SPEC §2 item 12; SPEC §5 finding 11 ("fixed: counted steps (R002)")
- **Severity:** medium. **Confidence:** high on the measurement. It becomes a verdict difference only if a time limit is applied, which v2 does not have but every harness does.

## What happens

`Checker.no_lookalike` (`kernel.py:288-300`) builds `vals`, the distinct cells of the column, with
`if r[k - 1] not in vals: vals.append(...)`. That is a linear scan of a Python list per row, so
O(rows × distinct values). It also computes a skeleton per distinct cell. None of this is counted;
the only step charge is `steps.add(len(idx))` afterwards.

## Reproduce

`gen/gen_07.py N TSV RL` writes a one-column table of N distinct keys and the program
`claim count(where(tsv(f), eq(1, "zz")))`. The files kept here are N = 40 000
(`07-distinct.tsv`, 360 KB, and `07-quadratic-lookalike-scan.rl`).

```
.venv\Scripts\python.exe findings\gen\time_check.py findings\07-quadratic-lookalike-scan.rl findings\07-distinct.tsv
```

Output (`07.out`): `seconds=8.62 counted_steps=85627 output_chars=153 accepted=True`

| rows (distinct) | file size | seconds | counted steps |
|---|---|---|---|
| 10 000 | 90 KB | 0.46 | 21 408 |
| 20 000 | 180 KB | 1.76 | 42 814 |
| 40 000 | 360 KB | 8.35 | 85 627 |

Time grows ×4 per doubling. Extrapolated, 400 000 rows (3.6 MB) take about 14 minutes. A table at
the 64 MB text bound would take days, while the counted steps stay below 0.1 % of `MAX_STEPS`.

## Demonstration

Under the README's own harness (`--timeout`) or the review's one-minute rule, the claim's verdict
depends on the speed of the machine: it forms on a fast machine and is killed on a slow one. v2's
bound R002 is meant to make that impossible, and here it does not.

## Fix

Use a set or dict keyed by skeleton (O(n)), and charge one step per cell visited, in every scan:
`no_lookalike`, `key()`, `column()` skeletons and `labels_distinct`.
