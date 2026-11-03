# 10 — Unhandled Python `int_max_str_digits`, `RecursionError`, and `1e-4500` `B09` float32 underflow cause uncaught CLI crashes, `X001` internal errors, and environment-dependent verdicts

- **Category:** **hit** (also **uncaught CLI crash** and **`X001` internal error bug**; regression of v1 Findings 11 & 13)
- **Spec clauses:** Principle §1 item 4 (no environment/stack-depth dependence), §5 (two runs differing in one outside factor), `SPEC.md` §2 item 13 (`X001`) & §5 Findings 11 & 13, `README.md:128`
- **Code locations:** `src/reality2/kernel.py:75` (`fmt`), `src/reality2/kernel.py:682` (`check` calling `parse_line` outside `try`), `src/reality2/syntax.py:213, 248`, `src/reality2/readers.py:229–245` (`parse_json`), `src/reality2/readers.py:265` (`decimal`), `src/reality2/bids101.py:296, 306` (`B08` / `B09`)
- **Severity:** **high**
- **Confidence:** **high**

## Root cause

Python 3.11+ limits `int <-> str` conversions for non-power-of-two bases to `sys.get_int_max_str_digits()` (default `4300`, configurable via `PYTHONINTMAXSTRDIGITS`), and limits Python recursion to `sys.getrecursionlimit()` (default `1000`). `reality2` enforces neither deterministic digit/exponent bounds nor recursion guards in four places:

1. **Item 4 Hit + `X001` in `readers.decimal` (`readers.py:265`):**
   A tiny 4,310-byte TSV containing `1.` followed by 4,305 `'0'`s passes `DEC_RE`, then calls `Fraction(cell)`. Under `PYTHONINTMAXSTRDIGITS=10000`, the claim **forms** (`Decimal[...] = 1 (Exact)`, `accepted`). Under default `PYTHONINTMAXSTRDIGITS=4300`, `Fraction(cell)` raises `ValueError`, which `kernel.py:668` catches as **`X001: internal error ValueError; nothing formed (please report)`** (`SPEC.md` §2 item 13: *"The fuzzers assert X001 never occurs"*).
2. **Uncaught CLI crash in `syntax.py` / `kernel.py:682`:**
   In `kernel.check` (`kernel.py:682`), `st = parse_line(text, ln)` is called **outside** any `try ... except Exception:` block (only `RealityError` is caught)! Any integer or decimal literal > 4,300 digits in a `.rl` file (~4.3 KB, well below `MAX_LINE_BYTES = 16,384`) raises an **uncaught `ValueError` traceback** that crashes `python -m reality2 check`, falsifying `README.md:128` and `SPEC.md` §5 #13.
3. **`B09` float32 underflow to `0.0` + `X001` in `kernel.fmt` (`bids101.py:296, 306`, `kernel.py:75`):**
   In a BIDS sidecar JSON, `"RepetitionTime": 1e-4500` parses via `parse_float=Fraction` as $10^{-4500} > 0$, passing `B08` (`tr_s <= 0`). Next, `B09` checks `Fraction(hdr.pixdim[4]) * scale != R.f32_nearest(tr_s)` — and `f32_nearest(10**-4500)` **underflows IEEE-754 float32 to `0.0`**, so a NIfTI header with `pixdim[4] = 0.0` **passes `B09`**! `claim tr(r)` then **forms** on line 3, and `difference(tr(r1), tr(r2))` on line 4 computes `1 - 10**-4500` whose 4,500-digit numerator triggers **`X001: internal error ValueError`** inside `kernel.fmt()`! (Relatedly, an 18-byte JSON `{"a": 1e99999999}` makes `Fraction` compute `10**99999999` in C, stalling CPU/RAM completely outside `Steps` and `MAX_TEXT_FILE`.)
4. **Item 4 Hit + `X001` in `readers.parse_json` (`readers.py:237`):**
   `json.loads` parses nested JSON in C without hitting Python's recursion limit, then `walk(v)` recurses in Python **outside** `try ... except RecursionError:`. At depth 981 in `dataset_description.json`, `reality2 check` **forms** (`accepted`) at normal CLI stack depth and fails with **`X001: internal error RecursionError`** when invoked with deeper call stack (or nested `widen(...)`).

## Minimal reproducing files and commands

Saved in `findings\`:
- `findings\10-python-runtime-limits-and-uncaught-crash.rl` + `findings\10-bigdec.tsv` (Item 4 flip: `accepted` vs `X001`)
- `findings\10-crash.rl` (uncaught Python traceback crash)
- `findings\10-underflow.rl` + `findings\10-underflow.manifest` + `findings\10-underflow-root\` (`B09` underflow to `0.0` + `X001`)

### Command 1A & 1B (Item 4 hit — environment variable flips `accepted` vs `X001`)
```powershell
$env:PYTHONPATH = "src"
$env:PYTHONINTMAXSTRDIGITS = "10000"
.venv\Scripts\python.exe -m reality2 check findings\10-python-runtime-limits-and-uncaught-crash.rl --files findings\10-bigdec.tsv

Remove-Item Env:PYTHONINTMAXSTRDIGITS
.venv\Scripts\python.exe -m reality2 check findings\10-python-runtime-limits-and-uncaught-crash.rl --files findings\10-bigdec.tsv
```

### Actual output 1A (`PYTHONINTMAXSTRDIGITS=10000`, `rc = 0`) and 1B (default, `rc = 1`)
```text
line 2: formed: Decimal[Cell[TSV[#1], row 1, col 1]] = 1 (Exact)
  #1 = sha256:15c5bd3c7cb61d10c3ae7572c7b132225f42c6888d8a39c8d5d5cee9af6d7bd7
accepted
```
```text
line 2: refused [X001, bug]: internal error ValueError; nothing formed (please report)
refused (1 statement)
```

### Command 2 (uncaught CLI traceback crash)
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\10-crash.rl --files findings\10-bigdec.tsv
```

### Actual output 2 (`rc = 1`, uncaught exception)
```text
Traceback (most recent call last):
  ...
  File "C:\Users\user\reality-review-argon-v2\src\reality2\kernel.py", line 682, in check
    st = parse_line(text, ln)
  File "C:\Users\user\reality-review-argon-v2\src\reality2\syntax.py", line 248, in literal
    return ("num", Fraction(v), unit, v)
ValueError: Exceeds the limit (4300 digits) for integer string conversion: value has 4305 digits; use sys.set_int_max_str_digits() to increase the limit
```

### Command 3 (`B09` float32 underflow `1e-4500` forming `tr(r)` then hitting `X001` in `difference`)
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\10-underflow.rl --files findings\10-underflow.manifest --root findings\10-underflow-root
```

### Actual output 3 (`rc = 1`)
```text
line 3: formed: RepetitionTime[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x run 2: #2], from #3] is recorded as 0.0000...0001 s (Recorded[s])
  ...
line 4: refused [X001, bug]: internal error ValueError; nothing formed (please report)
refused (1 statement)
```

## Spec §5 demonstration

- **Formed text:** `findings\10-python-runtime-limits-and-uncaught-crash.rl` + `findings\10-bigdec.tsv` (`accepted` under `PYTHONINTMAXSTRDIGITS=10000`).
- **§5 demonstration:** Two runs on the **exact same `.rl` program and `.tsv` bytes** differing in one outside environment setting (`PYTHONINTMAXSTRDIGITS`, or Python caller stack depth on 981-deep JSON) flip the verdict between `accepted` and `refused [X001]` (§1 item 4). Additionally, `10-underflow.rl` forms `RepetitionTime` on a scan whose NIfTI `pixdim[4]` is `0.0` (violating BIDS 1.0.1 §8.4 positive `RepetitionTime` consistency because `f32_nearest(1e-4500)` underflows to `0.0`).
- **Why neither defence applies:** Both claims form cleanly in the first run (`rc = 0`), and the defects are pure runtime/environment leaks.

## Fix direction

1. Enforce explicit, machine-independent bounds (`R001` / `J00x` / `T00x`) on integer/decimal digit counts (e.g., $\le 1000$ digits), JSON exponent magnitude (e.g., $|e| \le 1000$ before calling `Fraction`), and JSON nesting depth (iterative `walk` with explicit stack bounded at e.g. 64).
2. Require `f32_nearest(tr_s) > 0` and `math.isfinite` in `B09`.
3. Wrap `parse_line` in `kernel.check` under the same `X001` safety net as `statement()`.
