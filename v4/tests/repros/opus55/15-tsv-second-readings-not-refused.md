# 15. The TSV reader refuses CR and BOM as "two readings" but accepts U+2028, form feed and quoted fields

- **Category:** design issue / accuracy guideline (§10.2). Not counted as a hit, because the language's own fixed reader gives these bytes exactly one reading.
- **Spec clauses:** §10.2 (one standard of accuracy); SPEC §2 item 6 **[call]** ("These are the cases where the bytes have two readings"); BIDS reader B04 (refuses `"` for the same reason)
- **Severity:** low-medium. **Confidence:** high.

## What happens

T001 and T002 refuse a BOM and a CR because "it could end a line or belong to a cell, two readings".
Exactly the same is true of:

- U+2028 LINE SEPARATOR, U+2029, U+0085 NEL, form feed `\x0c`, vertical tab `\x0b` and `\x1c`–`\x1e`.
  Python's own `str.splitlines()` treats all of them as line ends, and so do many Unicode-aware
  readers.
- Quoted fields (`"q<TAB>"`). CSV-style TSV writers (pandas `to_csv(sep="\t")`, Excel) quote fields
  that hold tabs, and their readers take a quoted tab as part of the cell. The BIDS reader refuses `"`
  for this very reason (B04), but the plain reader splits on it.

## Reproduce

`15-tsv.tsv` is `a\tb\tc\n1<U+2028>2\t3\t4\n5\x0c6\t7\t8\n"q\t"\t9\n`.

```
.venv\Scripts\python.exe -m reality2 check findings\15-tsv-second-readings-not-refused.rl --files findings\15-tsv.tsv
```

Output (`15.out`, file lines omitted):

```
line 6: formed: RowCount[TSV[#1]] = 3 (Exact)
line 7: formed: Cell[TSV[#1], row 1, col 1] = "1\xe2\x80\xa82"
line 8: formed: Cell[TSV[#1], row 3, col 1] = "\"q"
line 9: formed: Cell[TSV[#1], row 3, col 2] = "\""
accepted
```

`str.splitlines()` on the same file gives 6 lines; Reality gives 4 (a header and 3 rows).

## Judgement

Choose one criterion. Either "two readings under common conventions" is the rule, and then these
characters and quotes must be refused like CR. Or the rule is "Reality's fixed reader", and then the
CR and BOM refusals are not needed. I recommend refusing them: they are rare in real data, and the
spec prefers refusing to choosing.
