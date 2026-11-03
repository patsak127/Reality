# 04. A 735-byte program runs for 25–36 s: `let` is re-evaluated at every use, and no step is counted

**Category:** bug (slow, memory-heavy; the step bound does not bound the work). v1 finding 11
returns in a new place.
**Spec clause:** §1 item 4 ("the checker's memory or speed"); SPEC §2 item 12 ("These are the same
constants on every machine, so verdicts don't depend on the machine"); SPEC §5 row 11 ("fixed:
counted steps (R002)").
**Severity:** high. **Confidence:** high.

## Program

`findings\04-let-chain-exponential.rl` (735 bytes), with `findings\04-cells.tsv`:

```
file f = sha256:7c48fc492d289b8af4b9418924da9b0d13faa48abf08a28d707cf555cafce953
let x0 = number(cell(tsv(f), 1, 2))
let x1 = difference(x0, x0)
let x2 = difference(x1, x1)
...
let x20 = difference(x19, x19)
claim exceeds(x20, c = -1)
```

`04-let-chain-exponential-n16.rl` and `-n18.rl` are the same with 16 and 18 lines.

## Commands and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\04-let-chain-exponential-n16.rl --files findings\04-cells.tsv
line 19: formed: Exceeds[Difference[Difference[Difference[ ... (one line of about 3.3 million characters)
[exit code 0; wall 1.7 s; peak private memory 29 MB]

> python -m reality2 check findings\04-let-chain-exponential-n18.rl --files findings\04-cells.tsv
line 21: formed: Exceeds[Difference[Difference[ ... (about 13 million characters)
[exit code 0; wall 6.3 s; peak private memory 81 MB]

> python -m reality2 check findings\04-let-chain-exponential.rl --files findings\04-cells.tsv
line 23: formed: Exceeds[Difference[Difference[ ... (about 52 million characters)
  #1 = sha256:7c48fc492d289b8af4b9418924da9b0d13faa48abf08a28d707cf555cafce953
accepted
[exit code 0; wall 24.7 s; peak private memory 288 MB]
```

(The bracketed lines are from my runner, `findings\run_all.py`; the output lines are cut in
`findings\04-output.txt`.) An earlier run of the same three programs took 1.6 s, 8.1 s and 35.5 s;
the machine's load moves the times, not the shape: every two lines of program multiply the time by
about 4 and the memory by about 3.

## Why the bounds don't stop it

- A `let` binds its *expression*, not its value (`kernel.py:658`), and each use evaluates it again
  (`kernel.py:151`). `x20` therefore evaluates `x0` 2^20 times, and the claim's sort string has
  2^20 copies of `Decimal[Cell[TSV[#1], row 1, col 2]]`.
- None of that work is counted: `cell` by position, `number`, `difference` and a cached `tsv` add
  no steps (`R002` counts table lines, filtered rows and bytes read). R005 limits let-nesting to 64,
  which allows about 30 doubling lines: 2^30 evaluations and a sort of tens of gigabytes. The run
  would take hours and end, depending on the machine's memory, in a formed claim, an X001
  (`MemoryError` inside the statement) or a traceback (`MemoryError` in `HASH_RE.sub`, which
  `kernel.check` calls outside the `try`, `kernel.py:710`).
- The Lean model (`metatheory/Scope.lean`) binds a `let` to a meaning computed once, so the model
  cannot show this (finding 19).

## What would fix it

Bind a `let` to its meaning once (keep the trace by recording the let's files with the binding),
or count one step per node evaluated and per byte of sort built, and bound the printed sort's
length with a refusal code.
