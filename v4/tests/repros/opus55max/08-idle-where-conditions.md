# 08. Conditions that cannot bear on the answer form; only the literal repeat is refused

**Category:** hit (item 1: a part "does not bear on the answer"). v1 finding 15 (a respect that
ignores its arguments) in v2's vocabulary, and the same shape as v1 finding 10: a check on a
spelling where a check on meaning was needed.
**Spec clause:** §1 item 1 ("a respect whose body ignores an argument; a kind changed by
multiplying by 1"); SPEC §3 S008 ("idle condition"); README "a condition that doesn't bear
(written twice) is refused (S008)".
**Severity:** medium. **Confidence:** high that they form; high that v2's own rule calls them
nonsense (S008's message says the repeated condition "does not bear on the answer").

## Program

`findings\08-idle-where-conditions.rl`, with `findings\08-table.tsv` (`id group` / `s1 A` /
`s2 B` / `s3 A`):

```
file f = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
let t = tsv(f)
claim count(where(t, eq(2, "A")))
claim count(where(t, eq(2, "A"), eq(2, "A")))
claim count(where(t, eq(2, "A"), ne(2, "B")))
claim count(where(t, ne(2, "\xff")))
claim count(where(t, ne(2, "A\x09B")))
claim count(where(t, eq(2, "A"), ne(2, "A")))
claim share(where(t, ne(2, "\xff")))
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\08-idle-where-conditions.rl --files findings\08-table.tsv
line 3: formed: Count[Rows[TSV[#1] where col 2 = "A"]] = 2 (Exact)
  #1 = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
line 4: refused [S008, item 1]: the condition eq(col 2, "A") is written twice; the second does not bear on the answer
line 5: formed: Count[Rows[TSV[#1] where col 2 = "A" and col 2 != "B"]] = 2 (Exact)
  #1 = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
line 6: formed: Count[Rows[TSV[#1] where col 2 != "\xff"]] = 3 (Exact)
  #1 = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
line 7: formed: Count[Rows[TSV[#1] where col 2 != "A\x09B"]] = 3 (Exact)
  #1 = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
line 8: formed: Count[Rows[TSV[#1] where col 2 = "A" and col 2 != "A"]] = 0 (Exact)
  #1 = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
line 9: formed: Share[Rows[TSV[#1] where col 2 != "\xff"] of TSV[#1]] = 3/3 (Exact)
  #1 = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
refused (1 statement)
```

## Demonstration (§5, items 1–2: the idle part)

For every table the TSV reader accepts, not just this one:
- line 5: `ne(2, "B")` removes no row that `eq(2, "A")` kept. It is idle exactly as line 4's
  repeated `eq(2, "A")` is, and v2 refuses line 4 for that reason;
- lines 6, 7, 9: no cell can ever be the bytes `\xff` (cells are valid UTF-8) or contain a TAB, so
  the condition removes nothing; the claim is `rows(t)` with a different sort, which is item 1's
  "a kind changed by multiplying by 1";
- line 8: the conditions exclude each other, so the answer is 0 whatever the file holds: the
  table does not bear on the answer.

## Cause

S008 compares conditions by their spelling after column resolution, `(fn, column, bytes)`
(`kernel.py:273`). Nothing checks what a condition can select. `no_lookalike` returns early for a
literal that is not UTF-8 (`kernel.py:289-292`), so such a literal is never even compared with
the cells.

## What would fix it

Refuse a byte literal that no cell can hold (not UTF-8, or containing TAB, LF or CR). Within one
`where`, refuse a second condition on a column that already has an `eq` condition (with one `eq`,
any other condition on that column is either implied or contradictory), and refuse `eq`/`ne` of the
same bytes on one column. With only `eq`/`ne` on byte strings these rules are complete: idleness is
decidable syntactically per column.
