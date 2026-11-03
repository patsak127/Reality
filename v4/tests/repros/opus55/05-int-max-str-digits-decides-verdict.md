# 05. A long decimal cell: the verdict depends on the environment variable PYTHONINTMAXSTRDIGITS

- **Category:** hit (item 4: verdict depends on something other than the text); also a bug (X001 reachable from file content)
- **Spec clauses:** §1 item 4; SPEC §2 item 13 ("The fuzzers assert X001 never occurs")
- **Severity:** medium. **Confidence:** high.

## What happens

`readers.decimal()` accepts any string of ASCII digits and then calls `Fraction(s)`. CPython (3.11 and
later) refuses to convert a decimal string longer than `sys.int_info.str_digits_check_threshold`
digits, 4 300 by default. That limit is set per process by `PYTHONINTMAXSTRDIGITS` or
`-X int_max_str_digits`. A 5 000-digit cell therefore raises `ValueError` inside the reader. The
kernel turns this into X001. With the variable set to 0 (no limit), the same claim forms. The same
limit applies to `fmt()` when it prints a result, to JSON numbers in sidecars (read with
`parse_int=Fraction`; there the error becomes J001, "not JSON", for valid JSON), and to the
BIDS onset/duration check (`bids101.py:340`), where it becomes X001 for the whole dataset.

## Reproduce

`05-long.tsv` is `v` followed by one cell of 5 000 `1`s. Program `05-int-max-str-digits.rl`:

```
file f = sha256:d54faf8cd4f274b57ba67510bdcb7171725fb4c6d2390f4a6299fec74a12e6fe
claim exceeds(number(cell(tsv(f), 1, 1)), c = 0)
```

```
.venv\Scripts\python.exe -m reality2 check findings\05-int-max-str-digits.rl --files findings\05-long.tsv
set PYTHONINTMAXSTRDIGITS=0
.venv\Scripts\python.exe -m reality2 check findings\05-int-max-str-digits.rl --files findings\05-long.tsv
```

Output (`05.out`):

```
line 3: refused [X001, bug]: internal error ValueError; nothing formed (please report)
refused (1 statement)
== PYTHONINTMAXSTRDIGITS=0
line 3: formed: Exceeds[Decimal[Cell[TSV[#1], row 1, col 1]], c = 0] holds
  #1 = sha256:d54faf8cd4f274b57ba67510bdcb7171725fb4c6d2390f4a6299fec74a12e6fe
accepted
```

## Demonstration (§5)

*Item 4.* Two runs that differ in one environment variable give different verdicts (exit 1 and
exit 0). The verdict also depends on the Python version: 3.10.6 and earlier have no such limit.

## Fix

Parse decimals with an explicit digit loop (as `reality2_ref.dec` nearly does, though it calls
`int()` too and fails in the same way), or set a fixed bound on digits that is part of the language
(an R code). Then call `sys.set_int_max_str_digits` once to a fixed value at start-up, so the
environment cannot change it. Add file-content mutation to the fuzzer; it mutates programs only.
