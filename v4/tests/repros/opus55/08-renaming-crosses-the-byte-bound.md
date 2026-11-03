# 08. Renaming one name changes the verdict: the program bound is counted in bytes, and names have length

- **Category:** hit (item 3: "Renaming user names one-to-one changes the verdict")
- **Spec clauses:** §1 item 3; README "renaming never changes the output" (stated of the Lean model); SPEC §5 finding 2
- **Severity:** low (needs a program near 1 MB). **Confidence:** high.

## What happens

`split_program` refuses a program longer than `MAX_PROGRAM_BYTES = 1 000 000` bytes (R001). The bound
is checked on the raw bytes, so it counts the length of user names. Renaming a name one-to-one to a
longer one can carry a program over the bound. The Lean `check_rename` theorem does not cover this,
because the model has no parser and no bounds. The renaming fuzzer does not cover it either, because
it never works near the bound.

## Reproduce

`gen/gen_08.py` writes `08-rename-a.rl` (999 990 bytes) and `08-rename-b.rl` (1 000 022 bytes). They are
the same two statements, padded with one comment line. The only difference is the name: `f` in a,
`participants_file` in b.

```
file f = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
claim rows(tsv(f)) is 108
#xxxx… (padding)
```

```
.venv\Scripts\python.exe -m reality2 check findings\08-rename-a.rl --files tests\data\ds001734-box\participants.tsv
.venv\Scripts\python.exe -m reality2 check findings\08-rename-b.rl --files tests\data\ds001734-box\participants.tsv
```

Output (`08.out`):

```
line 2: formed: RowCount[TSV[#1]] = 108 (Exact)
  #1 = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
accepted
== renamed
line 0: refused [R001, item 1]: the program is longer than 1000000 bytes (Reality bounds)
refused: the program is not Reality text
```

## Demonstration (§5)

*Item 3.* A renaming (`f` → `participants_file`, one-to-one) with both verdicts: accepted, and
refused. A smaller point: R001 is reported as `item 1` and on `line 0`.

## Fix

Bound the program by tokens or statements, or count each name as one unit. More generally, make
every bound a function of the program's structure after names are resolved.
