# 16 — `reality2_ref` diverges from `reality2` on 7 plain-TSV inputs (including an `IndexError` crash, silent wrap-around on row `0`, inverted intervals, and unchecked `share`/`bool` `is_`), masked by narrow differential generators

- **Category:** **bug** (also a **docs overclaim** on `README.md:129`)
- **Spec clauses:** `REVIEW.md` (f) (disagreements between `reality2` and `reality2_ref`), `README.md:129`
- **Code locations:** `src/reality2_ref/ref.py:92–225` (`evaluate`), `tests/test_differential.py:1–180`
- **Severity:** **medium**
- **Confidence:** **high**

## Root cause

`README.md:129` presents `src/reality2_ref/` + `tests/test_differential.py` as key verification evidence for the trusted base:
> *"a second implementation of the plain-TSV fragment, written separately, agreeing with the checker on 16 000 random claims over random tables, including every case the TSV reader refuses and lookalike cells"*

Inspection of `src/reality2_ref/ref.py` and `tests/test_differential.py` reveals **seven concrete disagreements** inside the plain-TSV fragment, plus **two missing plain-TSV operations**, all hidden because `test_differential.py` only generates well-typed ASTs with `pos >= 1`, `tol >= 0`, ASCII lookalikes in `K`, and `is_=None`:

1. **`row = ("pos", 0)` wraps around to the last row (`ref.py:114`):** `ref.py` checks `if r > len(rows): return ("refused", "V002")` without checking `r < 1`, so `rows[0 - 1]` evaluates `rows[-1]` and **forms** `('formed', ('bytes', b'20'))`, whereas `reality2` refuses `S006`!
2. **`row = ("pos", -5)` crashes `reality2_ref` (`ref.py:114`):** `rows[-6]` raises an **uncaught `IndexError: list index out of range`**, whereas `reality2` refuses `S006`!
3. **`col = ("pos", 0)` and `header(0)` return wrong refusal codes (`ref.py:86, 155`):** `ref.py` returns `('refused', 'V002')`, whereas `reality2` returns `S006` (`position` check precedes table bounds).
4. **Negative `tolerance` in `widen` forms an inverted interval (`ref.py:187`):** `ref.py` omits `tol < 0` validation (`S004` in `reality2`) and computes `(lo - tol, hi + tol) = (15, 5)` on `10` with `tol = -5` — allowing `exceeds(..., 12)` (`lo > c`) and `below(..., 8)` (`hi < c`) to **both form simultaneously** in `reality2_ref`!
5. **False `share` assertions with `is_` form (`ref.py:216`):** `ref.py:216` checks `is_` for `"bytes"`, `"count"`, and `"num"`, **completely forgetting `kind == "share"`**! Thus `share(..., is_=(99, 100))` on a table whose true share is `1/2` returns `('formed', ('share', (1, 2)))` instead of `('refused', 'V001')`! (`test_differential.py` never passes `is_` at all.)
6. **`exceeds` / `below` with `is_` forms (`ref.py:216`):** Passing `is_=True` on `exceeds` returns `('formed', ('bool', True))` in `reality2_ref`, whereas `reality2` refuses `S010` (*"a comparison claim takes no 'is'"*).
7. **`@<64-hex>` byte literal in `where` (`ref.py:128` vs `kernel.py:580`):** `reality2_ref` (which has no string-regex Check 2) rightly returns `('formed', ('count', 0))`, whereas `reality2` fails with `C001, floor` (Finding 01) — a genuine differential bug in `reality2` that `test_differential.py` missed because its literal generator never drew `@` + 64 hex chars!
8. **Missing plain-TSV operations & blind spots:** `ref.py` omits `difference(a, b)` and `count(tsv(f))` (table without `where`), and replicates `keys.py`'s exact 4-rule `skeleton()` shortcut so both implementations share the non-`K` lookalike blind spot (Finding 04).

## Minimal reproducing files and commands

Saved in `findings\`:
- `findings\16-reference-implementation-divergences.rl`
- `findings\16-table.tsv` (`id\tv\na\t10\nb\t20\n`)
- `findings\16-run-ref.py` (executes all 7 cases through both `reality2_ref.ref.evaluate` and `reality2.kernel.check`)

### Command 1 (`reality2` CLI on `16-reference-implementation-divergences.rl`)
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\16-reference-implementation-divergences.rl --files findings\16-table.tsv
```

### Actual output 1 (`rc = 1`)
```text
line 2: refused [S006, item 1]: a row is a position: a whole number from 1
line 3: refused [S006, item 1]: cell()'s column is a position: a whole number from 1
line 4: refused [S004, item 1]: widen(): slot 'tolerance' takes a number at least 0
line 5: refused [V001, item 5]: the claim writes 0.99; computed from the bytes it is 0.5
line 6: refused [C001, floor]: check 2: the claim's sort names sha256:0000000000000000000000000000000000000000000000000000000000000000, but its value was not computed from it; the sort and the dependency set disagree (a refusal, and a bug report against one of them)
refused (5 statements)
```

### Command 2 (side-by-side comparison with `reality2_ref`)
```powershell
.venv\Scripts\python.exe findings\16-run-ref.py
```

### Actual output 2
```text
[row=0]
  reality2_ref : ('formed', ('bytes', b'20'))
  reality2     : line 2: refused [S006, item 1]: a row is a position: a whole number from 1
[row=-5]
  reality2_ref : CRASH IndexError: list index out of range
  reality2     : line 2: refused [S006, item 1]: a row is a position: a whole number from 1
[col=0]
  reality2_ref : ('refused', 'V002')
  reality2     : line 2: refused [S006, item 1]: cell()'s column is a position: a whole number from 1
[widen tol=-5]
  reality2_ref : ('formed', ('num', (Fraction(15, 1), Fraction(5, 1))))
  reality2     : line 2: refused [S004, item 1]: widen(): slot 'tolerance' takes a number at least 0
[share false is_]
  reality2_ref : ('formed', ('share', (1, 2)))
  reality2     : line 2: refused [V001, item 5]: the claim writes 0.99; computed from the bytes it is 0.5
[exceeds with is_]
  reality2_ref : ('formed', ('bool', True))
  reality2     : line 2: refused [S010, item 1]: a comparison claim takes no 'is'; it holds or it is refused
[@<64-hex> literal]
  reality2_ref : ('formed', ('count', 0))
  reality2     : line 2: refused [C001, floor]: check 2: the claim's sort names sha256:0000000000000000000000000000000000000000000000000000000000000000, but its value was not computed from it; the sort and the dependency set disagree (a refusal, and a bug report against one of them)
```

## Fix direction

Fix `ref.py`'s position/tolerance/`is_` guards, add `difference` and `count(table)`, parse `.rl` text directly in `reality2_ref` (or broaden `test_differential.py` to generate boundary integers `<= 0`, negative tolerances, `is_` clauses of every kind, `difference`, Unicode/ASCII confusables directly from `confusables.txt`, and `@<64-hex>` literals).
