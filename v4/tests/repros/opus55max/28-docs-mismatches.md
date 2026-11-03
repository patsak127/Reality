# 28. Smaller documentation mismatches

**Category:** docs overclaim (each item is small; together they show where the documents are
ahead of the code).
**Spec clause:** README, SPEC, `keys.py`, `pyproject.toml`, `bids/RULES-1.0.1.md` as cited.
**Severity:** low. **Confidence:** high.

## Programs

`findings\28-docs-mismatches.rl`:

```
file f = sha256:0000000000000000000000000000000000000000000000000000000000000000
dataset d = sha256:1111111111111111111111111111111111111111111111111111111111111111
```

`findings\28-docs-mismatches-b.rl` (with `findings\08-table.tsv`):

```
file f = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
let tbl = tsv(f)
claim rows(tbl) tbl
```

## Commands and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\28-docs-mismatches.rl
accepted
(exit code 0)

> python -m reality2 check findings\28-docs-mismatches-b.rl --files findings\08-table.tsv
line 3: refused [P001, item 1]: unexpected 'tbl' after the end of the statement
refused (1 statement)
```

## The mismatches

| document says | what the code does | evidence |
|---|---|---|
| README: "A name that points to bytes nobody supplied is refused (F001)." | Only when something reads it. A program that names two files nobody supplied is `accepted`, exit 0. | `28-docs-mismatches.rl` |
| README: "The output never contains the program's own names." | P001 messages quote the unexpected token, which can be a user name. (Renaming changes such a message by exactly the renaming, which item 3 allows; the sentence is still not true.) | `28-docs-mismatches-b.rl` |
| `keys.py:10`: the confusables pin is "checked by tests/test_keys.py on the box". | There is no `tests/test_keys.py`; nothing tests `CONFUSABLES_SHA256` or derives `ASCII_ENTRIES` from the pinned file. (I checked both by hand: the SHA-256 of `context\sources\confusables.txt` is the pinned one, and its entries with ASCII letters or digits on both sides are exactly `1→l`, `I→l`, `0→O`, `m→rn`; `scratch\confusables_ascii.py`.) | `tests\` listing |
| README and SPEC §2 item 13: "The fuzzers assert X001 never occurs"; README: "an internal error refuses (X001)". | X001 is reachable from valid input (findings 01, 06, 16), and some errors escape as tracebacks (findings 01 c, 07). | 01, 06, 07, 16 |
| README: "So is a file that changes while it is being read (F002)." | Only for files read whole. | 25 |
| SPEC §1: unimplemented 1.0.1 kinds "are refused as unimplemented (B14), never skipped"; RULES-1.0.1.md: "The list above covers the sections whose files appear in ds001734, plus every file kind that triggers B14." | `phenotype/` (§8.11) is skipped as extra. | 12 |
| SPEC §2 item 12: bounds "are the same constants on every machine, so verdicts don't depend on the machine"; SPEC §5 rows 11 and 12 "fixed". | Time and memory are not bounded by the constants. | 04, 06, 13, 14, 15 |
| README: "agreeing with the checker on 16 000 random claims …"; `ref.py`: "… with 'is'". | No `is`, no sorts compared; with `is`, 51 disagreements in 1,195. | 18 |
| README, Lean row: "proves … that renaming never changes the output". | True of the model only. | 19, 21 |
| SPEC §2 item 11: "the claim still names the whole set it was checked against". | Extra entries and sizes are never checked. | 22 |
| README "Running": the harness run "must be GREEN" on all four machines. | On this machine (Windows 11, Python 3.14.7, cp1252 console) `tests\test_findings.py::test_01_hash_seed_does_not_change_output` fails: "1 failed, 186 passed". | 07 |
| `pyproject.toml`: "tests/test_stdlib_only.py checks this". | The test is `tests/test_source.py::test_stdlib_only`. | `tests\` listing |
| README: "JSON is read strictly (J00x)". | Valid JSON with a number of more than 4,300 digits is refused as "not JSON" (J001, finding 01), and a valid exponent can stall the reader (finding 15). | 01, 15 |

What I found accurate: the trusted-base line counts (1,873 lines; 1,612 without blank and comment
lines), the test count (187), the acceptance table (every row reproduces), and README's statements
that F1–F11 form only on a fabricated copy and that the real check is still to run on the PC.
