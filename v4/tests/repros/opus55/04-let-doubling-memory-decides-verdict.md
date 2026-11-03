# 04. `let` chains grow exponentially and uncounted; whether a claim forms depends on the machine's memory

- **Category:** hit (item 4: "the checker's memory or speed"; §5 "a time or memory limit that depends on the machine"); v1 findings 11/12 come back in a new place
- **Spec clauses:** §1 item 4; SPEC §2 item 12 ("They are the same constants on every machine, so verdicts don't depend on the machine")
- **Severity:** high. **Confidence:** high.

## What happens

`let` stores the *expression*, not its value (`kernel.py:658`), and `meaning()` re-evaluates the
expression at every use (`kernel.py:151`). The sort string is rebuilt each time by concatenation
(`f"Difference[{a.sort}, {b.sort}]"`). With `let x_i = difference(x_{i-1}, x_{i-1})` each level
doubles both the work and the length of the sort. None of this is counted: `difference`, `number`,
`cell` by position and name lookups add no steps, so R002 (200 000 000 counted steps) never fires.
The depth bound R005 (64) allows about 31 levels, that is about 2^31 evaluations and sort strings of
tens of gigabytes. The let-depth bound is not a work bound.

## Reproduce

`04-n.tsv` holds `v` and `5`. `gen/gen_04.py K HASH OUT` writes the program with K levels;
`04-let-doubling-19.rl` (21 lines, about 1 KB) is K = 19:

```
file f = sha256:a75fba65dbd56c79b06e2af7a7633535fab510154b19324f132a104edb5621a4
let x0 = number(cell(tsv(f), 1, 1))
let x1 = difference(x0, x0)
...
let x19 = difference(x18, x18)
claim below(x19, c = 1)
```

`gen/memlimit_run.py MB …` runs the unmodified CLI in-process inside a Windows job object with a
per-process memory limit (0 = no limit). That limit is the only thing that differs between the runs:

```
.venv\Scripts\python.exe findings\gen\memlimit_run.py 0   check findings\04-let-doubling-19.rl --files findings\04-n.tsv
.venv\Scripts\python.exe findings\gen\memlimit_run.py 120 check findings\04-let-doubling-19.rl --files findings\04-n.tsv
```

Output (`04.out`, the formed sort cut):

```
line 22: formed: Below[Difference[Difference[Difference[ ... ]]], c = 1] holds
accepted
exit 0
== same, 120 MB limit
line 21: refused [X001, bug]: internal error MemoryError; nothing formed (please report)
line 22: refused [N003, item 1]: a name used here comes from the statement on line 21, which was refused
refused (2 statements)
exit 1
```

Scaling with no limit (`gen/time_check.py`, this PC):

| levels K | seconds | counted steps | output characters |
|---|---|---|---|
| 12 | 0.10 | 3 | 204 909 |
| 14 | 0.45 | 3 | 819 309 |
| 16 | 1.87 | 3 | 3 276 909 |
| 18 | 10.07 | 3 | 13 107 309 |
| 19 | about 24 | 3 | about 26 000 000 |

## Demonstration (§5)

*Item 4.* Two runs that differ in one outside factor (the memory available to the process) give
different verdicts for the same text: accepted, and refused with X001. Without a limit, K = 25 or so
exhausts any ordinary machine, and the counted-step bound stays at 3.

## Fix

Bind each `let` to its computed meaning once (as the Lean model does: `bind env n (some m)`), and
print sorts with sharing (name sub-sorts by their hash) instead of copying them. Count every
`meaning()` call and every character of every sort built, so that the bound counts all work, not
just table operations.
