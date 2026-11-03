# 09. An events file with two columns named `onset` conforms, and `onset()` forms

**Category:** hit (item 1: "a column name that occurs twice"; item 2: two readings of "the onset").
**Spec clause:** §1 item 1 (its own example); §3 *Columns* ("Duplicate or blank headers are
refused (finding 19)"); §10.3 *Outside the alphabet* (the BIDS reader matches `onset` by name);
v1 finding 19.
**Severity:** medium. **Confidence:** high that it forms; medium-high that it is a hit (BIDS 1.0.1
also fixes the onset column by position, see below).

## Program

`findings\09-duplicate-onset-column.rl`, with the made-up dataset `findings\09-ds\` (manifest in
`findings\09-m\`). Its only events file is

```
onset	duration	onset
1.5	2	9.75
```

```
dataset d = sha256:a10dbd0030880e3116ca1f06a166fcb076cad5ebbac87a1917900cfe381b3182
file e = sha256:ff0e6a4b6f57691ff53deb3c94165b60d64b8ccea395d6d6045159d9df542cbd
let r = recording(bids(d), "01", "x")
claim onset(r, 1)
claim header(tsv(e), 3)
claim number(cell(tsv(e), 1, 3))
claim number(cell(tsv(e), 1, "onset"))
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\09-duplicate-onset-column.rl --files findings\09-m findings\09-ds --root findings\09-ds
line 4: formed: EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x: #2], #3 row 1] is recorded as 1.5 s (Recorded[s])
  #1 = sha256:a10dbd0030880e3116ca1f06a166fcb076cad5ebbac87a1917900cfe381b3182
  #2 = sha256:2332e1fb224ea541dcec22cd75345b9c9fb9b0f396c46a10cec5254eb5bbde6e
  #3 = sha256:ff0e6a4b6f57691ff53deb3c94165b60d64b8ccea395d6d6045159d9df542cbd
line 5: formed: Header[TSV[#1], col 3] = "onset"
  #1 = sha256:ff0e6a4b6f57691ff53deb3c94165b60d64b8ccea395d6d6045159d9df542cbd
line 6: formed: Decimal[Cell[TSV[#1], row 1, col 3]] = 9.75 (Exact)
  #1 = sha256:ff0e6a4b6f57691ff53deb3c94165b60d64b8ccea395d6d6045159d9df542cbd
line 7: refused [K002, item 1]: cell()'s column: headers "onset", "onset" (columns 1, 3) look alike or repeat, so the name picks no single column; address it by position
refused (1 statement)
```

## Demonstration (§5, items 1–2)

In one program, about one file: v2's plain-TSV rule refuses the name `onset` in this file because
"the name picks no single column" (line 7), while the BIDS reader, which finds the onset column by
that very name (the spec's §10.3: "The BIDS reader matches its standard's own fixed names
(`participant_id`, `onset`, …) byte-exactly"), forms an `EventOnset` of 1.5 s (line 4). The
column named `onset` holds 1.5 or 9.75; the text has two readings and the spec's item 1 names this
case ("a column name that occurs twice"). The same holds for a repeated `duration`.

The best defence is that BIDS 1.0.1 §8.5 also fixes position ("The first two columns are mandatory
and should contain onset and duration in that order"), so column 1 is the onset and column 3 an
"additional column". But the standard identifies the column by name and position together, and a
reader of the file (or a BIDS tool that indexes columns by name) cannot tell which one the dataset
means. v2 treats the same ambiguity as fatal for `participant_id` (B11 "exactly one participant_id
column") and for plain-TSV names (K002); events are the exception.

## Cause

`bids101.py:336` checks only `t.header[:2] == ["onset", "duration"]`; no rule looks at the other
headers. `kernel.event` then reads column 0 or 1 by position (`kernel.py:559`).

## What would fix it

Make a repeated or lookalike `onset`/`duration` header (anywhere in the line) a B06 failure, as
B11 does for `participant_id`; more generally, refuse BIDS TSV files whose header repeats a name.
