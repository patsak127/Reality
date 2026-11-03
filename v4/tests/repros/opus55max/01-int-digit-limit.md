# 01. An interpreter setting (`PYTHONINTMAXSTRDIGITS`) decides the verdict

**Category:** hit (item 4: the verdict depends on something other than the text). Also a bug:
X001 and an uncaught traceback are reachable from valid input.
**Spec clause:** §1 item 4 ("the clock, the hash seed, the machine, ..."), §5 item 4; SPEC §2 item 7
(the decimal reader), README "The fuzzers assert X001 never occurs".
**Severity:** high. **Confidence:** high (reproduced; cause traced).

This is v1 finding 1 (the hash seed decided E002) in a new form: an environment variable of the
interpreter decides whether a claim forms.

## Programs

`findings\01-int-digit-limit.rl`, with `findings\01-long-cell.tsv` (a header `v` and one cell of
5,000 digits `111…1`, which the decimal reader `-?[0-9]+(\.[0-9]+)?` accepts):

```
# The cell holds a decimal of 5000 digits (valid under the decimal reader -?[0-9]+).
file f = sha256:d54faf8cd4f274b57ba67510bdcb7171725fb4c6d2390f4a6299fec74a12e6fe
claim rows(tsv(f))
claim exceeds(number(cell(tsv(f), 1, 1)), c = 1)
```

`findings\01-int-digit-limit-b.rl`, with the made-up dataset `findings\01-ds\` and its manifest in
`findings\01-m\`. Its `task-x_bold.json` is valid RFC 8259 JSON, `"RepetitionTime": 2.000…0` with
5,000 zeros (the BOLD header's pixdim[4] is 2.0):

```
dataset d = sha256:b375775c4ec54fff4fc9b691503f5523c3271e95cb57024b0756edde8cbfa450
let b = bids(d)
claim count(participants(b))
claim tr(recording(b, "01", "x"))
```

`findings\01-int-digit-limit-c.rl`: `claim rows(tsv(f)) is 000…01` with 4,400 leading zeros
(the literal means 1, which is the right answer).

## Commands and output (Windows, Python 3.14.7)

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\01-int-digit-limit.rl --files findings\01-long-cell.tsv
line 3: formed: RowCount[TSV[#1]] = 1 (Exact)
  #1 = sha256:d54faf8cd4f274b57ba67510bdcb7171725fb4c6d2390f4a6299fec74a12e6fe
line 4: refused [X001, bug]: internal error ValueError; nothing formed (please report)
refused (1 statement)
(exit code 1)

> set PYTHONINTMAXSTRDIGITS=0
> python -m reality2 check findings\01-int-digit-limit.rl --files findings\01-long-cell.tsv
line 3: formed: RowCount[TSV[#1]] = 1 (Exact)
  #1 = sha256:d54faf8cd4f274b57ba67510bdcb7171725fb4c6d2390f4a6299fec74a12e6fe
line 4: formed: Exceeds[Decimal[Cell[TSV[#1], row 1, col 1]], c = 1] holds
  #1 = sha256:d54faf8cd4f274b57ba67510bdcb7171725fb4c6d2390f4a6299fec74a12e6fe
accepted
(exit code 0)
```

The BIDS variant: with the default setting the whole dataset is non-conformant; with the variable
set it conforms and both claims form.

```
> python -m reality2 check findings\01-int-digit-limit-b.rl --files findings\01-m --root findings\01-ds
line 3: refused [B00, reading rules]: the dataset does not conform to BIDS 1.0.1 (3 failures), so nothing BIDS-based forms from it (principle §1, whole-dataset conformance). B03 x1, first: task-x_bold.json is not JSON: Exceeds the limit (4300 digits) for integer string conversion (§4.3); B08 x2, first: sub-01/func/sub-01_task-x_bold.nii: no positive RepetitionTime in its sidecar files (§8.4, required)
line 4: refused [N003, item 1]: a name used here comes from the statement on line 3, which was refused
line 5: refused [N003, item 1]: a name used here comes from the statement on line 3, which was refused
refused (3 statements)

> set PYTHONINTMAXSTRDIGITS=0
> python -m reality2 check findings\01-int-digit-limit-b.rl --files findings\01-m --root findings\01-ds
line 4: formed: Count[Participants[BIDS-1.0.1[#1] from #2]] = 1 (Exact)
  #1 = sha256:b375775c4ec54fff4fc9b691503f5523c3271e95cb57024b0756edde8cbfa450
  #2 = sha256:293eac506f0087701fbb7d96e686c1ce554da692f1c2632044080c81408203ff
line 5: formed: RepetitionTime[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x: #2], from #3] is recorded as 2 s (Recorded[s])
  #1 = sha256:b375775c4ec54fff4fc9b691503f5523c3271e95cb57024b0756edde8cbfa450
  #2 = sha256:2332e1fb224ea541dcec22cd75345b9c9fb9b0f396c46a10cec5254eb5bbde6e
  #3 = sha256:8ce194867fdcd96753989dff97f20cce4879c159346605e2fa886c5d0569a7b8
accepted
```

The literal variant is worse than X001: the parser's `ValueError` is not caught at all, so the
checker prints a Python traceback and nothing else (line 2's claim, which formed, is lost):

```
> python -m reality2 check findings\01-int-digit-limit-c.rl --files findings\01-long-cell.tsv
Traceback (most recent call last):
  ...
  File "...\src\reality2\syntax.py", line 248, in literal
    return ("num", Fraction(v), unit, v)
  ...
ValueError: Exceeds the limit (4300 digits) for integer string conversion: value has 4401 digits; use sys.set_int_max_str_digits() to increase the limit
(exit code 1)

> set PYTHONINTMAXSTRDIGITS=0
> python -m reality2 check findings\01-int-digit-limit-c.rl --files findings\01-long-cell.tsv
line 2: formed: RowCount[TSV[#1]] = 1 (Exact)
  ...
line 3: formed: RowCount[TSV[#1]] = 1 (Exact)
  ...
accepted
```

Full outputs: `findings\01-output.txt`.

## Demonstration (§5, item 4)

Two runs that differ in one outside factor, the environment variable `PYTHONINTMAXSTRDIGITS`
(equivalently `python -X int_max_str_digits=0`), give different verdicts on the same program and
the same bytes: refused (X001) / formed; non-conformant (B00) / conformant with two formed BIDS
claims; a traceback / accepted. The default of 4,300 digits also differs between Python builds
and can be changed by `sys.set_int_max_str_digits` in a host process that imports the checker.

## Cause

Every number reader goes through Python's `int(str)`, whose length limit (added in CPython 3.11
for CVE-2020-10735) is configurable:
- `readers.decimal` returns `Fraction(s)` (`readers.py:196`), so a long cell raises `ValueError`
  in `number`, `sum`, `min`, `max` and in the BIDS events check (`bids101.py:340`); the kernel
  turns it into X001.
- `parse_json` passes `parse_float=Fraction, parse_int=Fraction` (`readers.py:218`); the
  `ValueError` is caught as "not JSON" (J001), so a valid sidecar becomes a B03 failure.
- `syntax.py:184`, `:187`, `:207`, `:209`, `:242` and `:248` call `int(v)` / `Fraction(v)` while
  parsing, outside every `try` that catches it (`kernel.py:681-688` catches only `SyntaxRefusal`).
- `kernel.fmt` (`str(n)`) has the same limit when a value with more than 4,300 digits is printed.

## What would fix it

Make the bound a Reality constant instead of an interpreter setting: set
`sys.set_int_max_str_digits(0)` once at start-up (or parse digit strings without `int(str)`),
and add a fixed digit limit with its own refusal code, applied identically in the decimal reader,
the JSON reader, the parser and the printer. Add a fuzz case with numbers of 4,000–5,000 digits.
