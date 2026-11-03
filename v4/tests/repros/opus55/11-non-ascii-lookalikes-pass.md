# 11. Lookalikes outside ASCII are never compared: `key()` picks "S1" while a Cyrillic "Ѕ1" sits in the same key column

- **Category:** hit for `key()` (v1 finding 8 rewritten, N12; §10.3). The `eq()` and header parts are an accuracy-guideline (§10.2) inconsistency, not hits.
- **Spec clauses:** §3 "Keys across files" (keys that look alike within a claim's scope are refused); §10.3 "Handling" and "Why by construction"; §5 N12; SPEC §2 items 2 and 5
- **Severity:** medium. **Confidence:** medium (the spec says a non-K cell "is not a key", which v2 reads as "may be ignored").

## What happens

The skeleton (`keys.skeleton`) folds only ASCII. A character outside K is "kept as it is", so a cell
holding CYRILLIC CAPITAL DZE + `1` never has the skeleton of `S1`. Three places compare skeletons:

- `key(col, "S1")` checks the *literal* against K, but not the other cells of the key column. It
  scans that column for lookalikes using the ASCII skeleton only. A non-K cell that renders exactly
  like the key is ignored, and the row "whose col 1 is S1" is picked as if it were unique.
- `eq(col, "bytes")` takes any bytes. Its lookalike check (K002) refuses `equalRange` against the
  ASCII `equaIRange`, but accepts the literal `equalR` + CYRILLIC A + `nge` against the ASCII
  `equalRange`.
- Headers: `gr` + CYRILLIC O + `up` and `group` do not block naming `"group"`.

§10.3 justifies the design with: "A ban list can miss a new lookalike. An allow list cannot, because
every non-ASCII lookalike is simply not in K." That argument holds only if every cell of a column
used as a key is required to be in K. v2 checks K on the literal only.

## Reproduce

`11-lookalikes.tsv` (bytes, shown as `printf` input):
`id\tgroup\tgr\xd0\xbeup\nS1\tequalRange\tx\n\xd0\x851\tequalR\xd0\xb0nge\ty\nS2\tequaIRange\tz\n`

```
.venv\Scripts\python.exe -m reality2 check findings\11-non-ascii-lookalikes-pass.rl --files findings\11-lookalikes.tsv
```

Output (`11.out`, file lines omitted):

```
line 6: formed: Cell[TSV[#1], row 1 (the row whose col 1 is "S1"), col 2] = "equalRange"
line 7: formed: Count[Rows[TSV[#1] where col 1 = "S1"]] = 1 (Exact)
line 8: formed: Count[Rows[TSV[#1] where col 2 = "equalR\xd0\xb0nge"]] = 1 (Exact)
line 9: refused [K002, item 1]: the bytes "equalRange" and the cell "equaIRange" in column 2 look alike (UTS #39 confusables 18.0.0, ASCII entries, with case folding); ...
refused (1 statement)
```

## Demonstration (§5)

*N12 / §10.3.* v1 finding 8 was a key that looks like another key across a non-ASCII character
(U+2011). In v2's syntax, the member picked out by `key(1, "S1")` (line 6) is "the row whose col 1 is
S1". Row 2's key cell is displayed as `S1` by any viewer, and the claim forms anyway. The printed
sort escapes the claim's own literal, but it does not show the rival cell, so a reader of the formed
claim cannot see the second candidate. Compare line 9: the same situation with an ASCII lookalike is
refused.

*Accuracy guideline (not counted as a hit).* Lines 8 and 9 apply two standards to one question
("can these bytes be told apart?"): `I`/`l` is refused, Cyrillic а/a is accepted. The UTS #39 file
the language already pins maps both to the same skeleton.

## Fix

A column used by `key()` or `eq()` must have every cell in K, or every non-K cell must be refused as
a lookalike candidate (K002, "not comparable"). Or use the full UTS #39 skeleton (the pinned file
already has it) for the *comparison*, while K stays the alphabet for keys.
