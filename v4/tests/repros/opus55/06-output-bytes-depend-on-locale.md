# 06. The output bytes depend on the console encoding; the suite's own determinism test fails on Windows

- **Category:** bug (non-deterministic output; a crash with a traceback)
- **Spec clauses:** §1 item 4 ("the locale", "the machine"); SPEC §5 finding 1 ("output byte-identical under different seeds, and across 4 machines")
- **Severity:** low to medium (the verdict text is the same; the bytes and, under an ASCII locale, the run itself are not). **Confidence:** high.

## What happens

Refusal messages contain non-ASCII characters (`§`, and 45 non-comment lines in `src/reality2/` hold
non-ASCII text). `print()` encodes them with the console or pipe encoding of the machine: cp1252 on this
Windows PC when piped, UTF-8 on Linux. Under an ASCII stdout (`PYTHONIOENCODING=ascii`, or some
minimal containers) the checker dies with a `UnicodeEncodeError` traceback. A verdict line, an exit
code or both are lost.

## Reproduce

`06-output-encoding.rl` is the single line `claim significant(x)`.

```
.venv\Scripts\python.exe -m reality2 check findings\06-output-encoding.rl > a.out
set PYTHONIOENCODING=utf-8 & .venv\Scripts\python.exe -m reality2 check findings\06-output-encoding.rl > b.out
set PYTHONIOENCODING=ascii & .venv\Scripts\python.exe -m reality2 check findings\06-output-encoding.rl
```

Output (`06.out`: sha256 of the output in the default and the UTF-8 run, then the last line of the ASCII run):

```
c1a6a7765984445670bf423039268e60c853605be6d1d095d4964f01de5e0fe3 *-
3facb0f6e22794d9a42aed5045f93b4dcfd7b2ea8d73b7386872de5d61fbad9e *-
UnicodeEncodeError: 'ascii' codec can't encode character '\xa7' in position 160: ordinal not in range(128)
```

The suite shows the same thing. `pytest tests` on this PC (Python 3.14.7) gives
`1 failed, 186 passed`. The failure is `test_findings.py::test_01_hash_seed_does_not_change_output`:
`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa7`. The seeds agreed with each other; the
test assumed UTF-8 output.

## Fix

Make every message printable ASCII (the program text already is, P009), or write
`sys.stdout.buffer` with an explicit UTF-8 encoding. Then add a check to the test that the output is
ASCII.
