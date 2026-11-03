# 21. Renaming one name changes the verdict at the program-size bound

**Category:** hit (item 3: "Renaming user names one-to-one changes the verdict").
**Spec clause:** §1 item 3; §5 item 3 ("a renaming with both verdicts"); README "renaming never
changes the output" (Lean `check_rename`, model); `tests\test_rename.py`.
**Severity:** low (needs a program at the size limit). **Confidence:** high.

## Programs

`findings\21-rename-crosses-program-bound.rl` (exactly 1,000,000 bytes: four statements and a
comment line that pads to the limit) and `findings\21-rename-crosses-program-bound-renamed.rl`,
which is the same text with the user name `t` renamed to `tt` at its three uses (1,000,003
bytes). `findings\21-table.tsv` is the supplied table.

```
file f = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
let t = tsv(f)
claim rows(t)
claim count(where(t, eq(2, "A")))
# xxxx… (padding comment, unchanged by the renaming)
```

## Commands and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\21-rename-crosses-program-bound.rl --files findings\21-table.tsv
line 3: formed: RowCount[TSV[#1]] = 3 (Exact)
  #1 = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
line 4: formed: Count[Rows[TSV[#1] where col 2 = "A"]] = 2 (Exact)
  #1 = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
accepted

> python -m reality2 check findings\21-rename-crosses-program-bound-renamed.rl --files findings\21-table.tsv
line 0: refused [R001, item 1]: the program is longer than 1000000 bytes (Reality bounds)
refused: the program is not Reality text
```

## Demonstration (§5, item 3)

A one-to-one renaming of user names (`t ↦ tt`) with both verdicts: accepted with two formed claims,
and refused. (The refusal is also labelled `item 1` although R001 is a bound; `kernel.check`
prints every syntax-level refusal as item 1, `kernel.py:678`, `:686`.)

## Cause

`MAX_PROGRAM_BYTES` counts bytes (`syntax.py:293`), and a name's length is bytes. The other bounds
count tokens, depth or file bytes, which renaming does not change. Neither the rename fuzzer
(names of at most 7 characters on small programs) nor the Lean model (no bounds) can reach this.

## What would fix it

Bound the program by tokens and statements rather than bytes, and give names a fixed maximum length
as a syntax rule (a renaming must stay a program, as with keywords); or define the byte bound on the
text with every name replaced by a fixed-length placeholder.
