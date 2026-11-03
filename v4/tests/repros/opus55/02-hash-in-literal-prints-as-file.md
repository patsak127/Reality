# 02. A byte literal containing `@<hash>` is printed as a file label: one printed claim, two values

- **Category:** hit (item 6, two formed claims that cannot both hold; item 2, two readings of the printed claim)
- **Spec clauses:** §1 items 2 and 6; §10.1 "Printed form and identity" (the canonical form is the claim's identity); SPEC §2 item 2 **[call]**
- **Severity:** high. **Confidence:** high.

## What happens

`kernel.py` builds each sort as a string in which files appear as `@<64 hex>`. After the claim is
computed it finds the named files with `HASH_RE = @([0-9a-f]{64})` over the whole sort string
(`kernel.py:580`) and prints the sort with every match replaced by `#k` (`kernel.py:710`). But
`eq`/`ne` literals are copied into the same string (`esc(lit)`, `kernel.py:285`), and `esc` leaves
`@` and hex digits alone. So the literal `"@<hash of the table>"` is printed as `"#1"`. The printed
claim then says something different from the claim that was checked. It is also identical to the
printed form of a different claim that has a different value.

## Reproduce

File `02-t.tsv` (`id\tv`, `a\t#1`, `b\tx`; sha256 `7da0a7c9…`). Program
`02-hash-in-literal-prints-as-file.rl`:

```
file f = sha256:7da0a7c98d0f07a7a5de598aef1921d231b176087cfe50f0ead7cbae3804888b
let t = tsv(f)
claim count(where(t, eq(2, "#1"))) is 1
claim count(where(t, eq(2, "@7da0a7c98d0f07a7a5de598aef1921d231b176087cfe50f0ead7cbae3804888b"))) is 0
claim count(where(t, ne(2, "@7da0a7c98d0f07a7a5de598aef1921d231b176087cfe50f0ead7cbae3804888b"))) is 2
```

```
.venv\Scripts\python.exe -m reality2 check findings\02-hash-in-literal-prints-as-file.rl --files findings\02-t.tsv
```

Output (`02.out`):

```
line 4: formed: Count[Rows[TSV[#1] where col 2 = "#1"]] = 1 (Exact)
  #1 = sha256:7da0a7c98d0f07a7a5de598aef1921d231b176087cfe50f0ead7cbae3804888b
line 5: formed: Count[Rows[TSV[#1] where col 2 = "#1"]] = 0 (Exact)
  #1 = sha256:7da0a7c98d0f07a7a5de598aef1921d231b176087cfe50f0ead7cbae3804888b
line 6: formed: Count[Rows[TSV[#1] where col 2 != "#1"]] = 2 (Exact)
  #1 = sha256:7da0a7c98d0f07a7a5de598aef1921d231b176087cfe50f0ead7cbae3804888b
accepted
```

## Demonstration (§5)

*Item 6.* Lines 4 and 5 are two formed claims with the same canonical printed form,
`Count[Rows[TSV[#1] where col 2 = "#1"]]`, and the values 1 and 0. Both cannot hold. Line 6 says
that every row's column 2 differs from `"#1"`, yet row 1's column 2 holds exactly the bytes `#1`.
*Item 2.* The printed claim has two readings: the bytes `#1`, or the label of file #1.

Variant: if the literal holds `@<hash>` for a file the claim does not read, the claim is refused
with C001 ("names sha256:… but its value was not computed from it"). That is a wrong refusal, and a
check-2 "bug report" that is false.

## Fix

Keep the sort as a structure, not a string, or escape `@` in literals (for example as `\x40`) before
they enter the sort. Then read the named files from the structure, never by a regex over printed
text. Add printed-form identity to the differential test: two claims with equal printed forms must
have equal values.
