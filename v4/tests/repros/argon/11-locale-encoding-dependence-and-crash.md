# 11 — Locale-dependent `stdout` encoding and CRLF line endings in `__main__.py` crash on `§` under ASCII/CP437 locales, break byte-identical output on Windows, and fail `test_01_hash_seed_does_not_change_output`

- **Category:** **hit** (also **uncaught CLI crash**, **cross-platform nondeterminism**, and **failing test in `tests/`**; regression of v1 Finding 1)
- **Spec clauses:** Principle §1 item 4 (no locale or OS dependence), §5 (two runs differing in one outside factor: locale encoding), `SPEC.md` §5 Finding 1 (*"output byte-identical ... across 4 machines"*), `README.md:109–120, 128`
- **Code locations:** `src/reality2/__main__.py:53–55` (`print(line)`), `tests/test_findings.py:30` (`test_01_hash_seed_does_not_change_output`)
- **Severity:** **high**
- **Confidence:** **high**

## Root cause

`README.md:109–120` excludes `src/reality2/__main__.py` from the "Trusted base" table (*"The trusted base is everything a verdict depends on"*), yet CLI runs execute `__main__.py:53–55`:

```python
for line in out:
    print(line)
```

Because `sys.stdout` is never reconfigured to `encoding="utf-8", newline="\n"`, Python encodes `stdout` using the OS/locale default text encoding and platform line separator (`\r\n` on Windows, `\n` on POSIX). Meanwhile, refusal messages across `kernel.py`, `keys.py`, `readers.py`, and `bids101.py` contain the non-ASCII Unicode section sign **`§` (`U+00A7`)**.

This produces three concrete failures:

1. **Item 4 Hit + Uncaught CLI Crash (`LC_ALL=C` / `PYTHONIOENCODING=ascii` or `cp437`):**
   Consider a 2-claim `.rl` file where claim 1 refuses with a message containing `§` (e.g. `K001`, `K002`, `B00`, `S002`) and claim 2 is a valid claim that **forms** (`README.md:48`: *"A line that is refused doesn't stop the check"*).
   - Under `PYTHONIOENCODING=utf-8`, claim 1 prints its refusal and **claim 2 forms and prints** (`RowCount[TSV[#1]] = 2 (Exact)`).
   - Under `PYTHONIOENCODING=ascii` (standard POSIX `LC_ALL=C` container/CI locale) or `cp437` (classic Windows OEM console), `print(line)` on claim 1 **crashes `reality2` with an uncaught `UnicodeEncodeError` traceback before claim 2 ever prints**!
2. **Non-UTF-8 bytes + `\r\n` on Windows (`cp1252`):**
   On Windows with piped `stdout` (default `cp1252`), `§` is emitted as single byte `0xa7` (invalid UTF-8!) instead of `0xc2 0xa7`, and every line ends with `\r\n` (`0d 0a`) instead of `\n` (`0a`), directly violating `SPEC.md` §5 #1 (*"output byte-identical under different seeds, and across 4 machines"*).
3. **Suite fails out of the box on Windows:**
   Running `.venv\Scripts\python.exe -m pytest -q tests` in this repository fails immediately on `tests/test_findings.py::test_01_hash_seed_does_not_change_output` with `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa7` (already recorded in `.pytest_cache/v/cache/lastfailed` prior to this review).

## Minimal reproducing files and commands

Saved in `findings\`:
- `findings\11-locale-encoding-dependence-and-crash.rl`
- `findings\11-bad.tsv`
- `findings\11-good.tsv`

`findings\11-locale-encoding-dependence-and-crash.rl`:
```text
file bad = sha256:9f2ca2a8301be7e0bd189c02d73d6fd21132e38f347892bf3a27a8286cf6312d
file good = sha256:55fc01feec80df5521dde64da128cf7c9a69b3dad5d275b5008f6ba671f8c915
claim cell(tsv(bad), key(1, "sub-001"), 1) is "sub-001"
claim rows(tsv(good)) is 2
```

### Command A (`PYTHONIOENCODING=utf-8` — line 4 forms)
```powershell
$env:PYTHONPATH = "src"
$env:PYTHONIOENCODING = "utf-8"
.venv\Scripts\python.exe -m reality2 check findings\11-locale-encoding-dependence-and-crash.rl --files findings\11-bad.tsv findings\11-good.tsv
```

### Actual output A (`rc = 1`, claim on line 4 formed)
```text
line 3: refused [K001, item 1]: key(): "sub-001" is not a key; a key is one or more ASCII letters or digits (principle §10.3)
line 4: formed: RowCount[TSV[#1]] = 2 (Exact)
  #1 = sha256:55fc01feec80df5521dde64da128cf7c9a69b3dad5d275b5008f6ba671f8c915
refused (1 statement)
```

### Command B (`PYTHONIOENCODING=ascii` / `LC_ALL=C` — crashes before line 4)
```powershell
$env:PYTHONPATH = "src"
$env:PYTHONIOENCODING = "ascii"
.venv\Scripts\python.exe -m reality2 check findings\11-locale-encoding-dependence-and-crash.rl --files findings\11-bad.tsv findings\11-good.tsv
```

### Actual output B (`rc = 1`, uncaught crash, nothing formed)
```text
Traceback (most recent call last):
  ...
  File "C:\Users\user\reality-review-argon-v2\src\reality2\__main__.py", line 54, in main
    print(line)
UnicodeEncodeError: 'ascii' codec can't encode character '\xa7' in position 119: ordinal not in range(128)
```

## Spec §5 demonstration

- **Formed text:** Line 4 of `findings\11-locale-encoding-dependence-and-crash.rl` (`claim rows(tsv(good)) is 2`) forms in Run A (`RowCount[TSV[#1]] = 2 (Exact)`).
- **§5 demonstration:** Two runs on the **exact same `.rl` program and `.tsv` files** differing only in locale/encoding (`PYTHONIOENCODING=utf-8` vs `ascii`/`LC_ALL=C` or `cp1252`) change both whether line 4's formed claim appears in the output at all (formed output vs uncaught `UnicodeEncodeError` crash) and the exact output bytes (`0xc2 0xa7 ... 0x0a` vs `0xa7 ... 0x0d 0x0a`, §1 item 4).
- **Why neither defence applies:** Line 4 forms in Run A, and locale encoding is an explicit outside factor listed in `REVIEW.md:73` and Principle §1 item 4.

## Fix direction

Write directly to `sys.stdout.buffer` as explicit UTF-8 with LF (`sys.stdout.buffer.write(("\n".join(out) + "\n").encode("utf-8"))`), matching `manifest`'s binary UTF-8 output (`__main__.py:28`), and include `__main__.py` inside the audited trusted base.
