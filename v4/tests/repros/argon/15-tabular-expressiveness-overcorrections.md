# 15 — Tabular expressiveness overcorrections: no composite keys (despite Principle §10.3), `where()` refuses `sel` inputs, and no `mean` / ratio-of-sums is expressible

- **Category:** **must-form refused (overcorrection)**
- **Spec clauses:** Principle §10.3 (*"A composite key is a tuple of keys"*), §5 (`REVIEW.md` b), `SPEC.md` §1 & §2 item 4
- **Code locations:** `src/reality2/kernel.py:264` (`c_where`), `src/reality2/kernel.py:312–330` (`row` / `key`), `src/reality2/kernel.py:130–145` (`OPS`)
- **Severity:** **medium**
- **Confidence:** **high**

## Root cause

Beyond the domains `SPEC.md` §1 explicitly marks out of scope (xlsx, NIfTI voxels, GLM, quantities/units, stipulated models), three omissions inside v2's **in-scope** plain-TSV and tabular surface block standard, completely unambiguous file-level scientific claims:

1. **No composite keys (`kernel.py:312–314`), even though Principle §10.3 explicitly specifies them:**
   Principle §10.3 states:
   > *"A key is a non-empty string over K ... **A composite key is a tuple of keys.**"*
   In real behavioral and clinical TSVs (long-format trial logs, longitudinal visits, multi-run summaries), rows are uniquely keyed by `(subject, trial)` or `(subject, session, run)`, never by a single column alone. Because `key(col, "val")` accepts only a single column, **no cell of a long-format TSV can be addressed by key** (`V004`: multiple rows hold `"sub01"` in column 1); authors are forced to hardcode fragile 1-based physical line numbers (`cell(t, 17, "rt")`), which silently point to the wrong subject if rows are sorted!
2. **`where()` refuses `sel` (`kernel.py:264`):**
   `c_where` restricts its first argument to `("table", "pset")`, refusing `"sel"` (`S007`), whereas `count`, `sum`, `min`, and `max` all accept `"sel"` via `rows_of()`. Thus a scientist cannot define a clean base cohort once (`let valid = where(t, ne("rt", "n/a"))`) and ask two questions about sub-cohorts (`where(valid, eq("group", "A"))` and `where(valid, eq("group", "B"))`), forcing copy-paste of every base filter into every `where(...)` call.
3. **No `mean(t_or_sel, col)` computation (`kernel.py:130–145`):**
   v2 implements exact `Fraction` arithmetic (`sum`, `min`, `max`, `difference`), yet omits `mean` (exact `Fraction(sum, count)` on non-empty selections, refusing empty selections with `V003` just like `min`/`max`/`share`). Without `mean`, even a basic demographic table claim such as *"mean age in the equalRange group exceeds 25"* cannot be stated.

## Minimal reproducing files and command

Saved in `findings\`:
- `findings\15-tabular-expressiveness-overcorrections.rl`
- `findings\15-long.tsv` (`subject\ttrial\trt\nsub01\tt1\t0.45\nsub01\tt2\t0.52\nsub02\tt1\t0.49\n`)

`findings\15-tabular-expressiveness-overcorrections.rl`:
```text
file f = sha256:1b42bc0880bd208cb05de1529f6d4026b49788b7683295d4bb6fc11b9302a898
claim cell(tsv(f), key("subject", "sub01"), "rt") is "0.45"
let s1 = where(tsv(f), eq("subject", "sub01"))
claim count(where(s1, eq("trial", "t1"))) is 1
```

### Command
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\15-tabular-expressiveness-overcorrections.rl --files findings\15-long.tsv
```

### Actual output (`rc = 1`)
```text
line 2: refused [V004, item 2]: key(): 2 rows hold "sub01" in column 1; a key picks out exactly one row
line 4: refused [S007, item 1]: where()'s first argument must be a TSV table or a BIDS participant set, not a selection of rows
refused (2 statements)
```

## Fix direction

1. Support composite keys `key(col1, k1, col2, k2, ...)` (checking `is_key` and `skeleton` lookalikes per component/tuple as specified in Principle §10.3).
2. Allow `"sel"` in `c_where` (flattening and checking the combined condition list against `S008` so duplicate/contradictory predicates across nested `where`s are still refused).
3. Add `mean(table_or_sel, col)` returning exact `Num(total / n, total / n, unit, rec)` (and refusing `n == 0` with `V003`).
