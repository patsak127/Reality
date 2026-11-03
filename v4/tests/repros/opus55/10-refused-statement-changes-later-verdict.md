# 10. A refused statement changes the verdict of a later, unrelated claim; so does how the same bytes are supplied

- **Category:** hit (item 4: "the order in which files are given", "the path"; README "a verdict never depends on a path, the order of supply"). Also a bug in the same class as v1 finding 18 (a refused statement leaves something behind).
- **Spec clauses:** §1 items 1 and 4; README `Store` docstring; SPEC §2 item 15
- **Severity:** medium. **Confidence:** high on behaviour, medium on calling it a hit: the first refusal is F001 ("not supplied"), and one could argue that bytes reachable only through `--root` are not supplied for a `file` statement.

## What happens

`Store.locate(h, hint)` searches the `--root` directories only when it has a manifest path as a hint.
A `file` statement has no hint, so with `--root` alone a file that *is* under the root is reported as
"no supplied file has sha256:…" (F001). But `locate` caches every hash it has verified
(`self._verified`, `readers.py:86-96`). Once any `bids(d)` call has walked the manifest, even one that
is then refused with B00, the same `file` hash is found. The cache is never reset between
statements.

## Reproduce

Program `10-refused-statement-changes-later-verdict.rl` (lines 4 and 6 are the same claim):

```
file p = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
dataset d = sha256:b6850de7d9ed854e78149bb842325892c4e888e312969b8812ea1fc9f9f0e4f2
claim rows(tsv(p)) is 108
let b = bids(d)
claim rows(tsv(p)) is 108
```

```
.venv\Scripts\python.exe -m reality2 check findings\10-refused-statement-changes-later-verdict.rl --files findings\01-box.manifest --root tests\data\ds001734-box
```

Output (`10.out`):

```
line 4: refused [F001, text]: no supplied file has sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8; the text names it, so its bytes are part of the text
line 5: refused [B00, reading rules]: the dataset does not conform to BIDS 1.0.1 (648 failures), ...
line 6: formed: RowCount[TSV[#1]] = 108 (Exact)
  #1 = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
refused (2 statements)
```

## Demonstration (§5)

*Item 4.* The program with only lines 1–4 is refused when the bytes are given as `--root
tests\data\ds001734-box`, and it forms when the same bytes are given as `--files
tests\data\ds001734-box`. The outside factor is the way the same bytes are supplied. Within one
program, two identical claims get different verdicts, and what decides it is a statement that was
itself refused.

## Fix

Make lookup independent of history: either search the roots for every hash (index them like
`--files`), or never let a `file` name be found through a root. In either case, clear any cache
that is visible to verdicts.
