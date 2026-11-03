# 08 — `MAX_PROGRAM_BYTES` checks raw UTF-8 byte length before tokenization, flipping `accepted` to `refused [R001]` under one-to-one identifier renaming

- **Category:** **hit** (regression of v1 Finding 2; also unmodelled in `metatheory/Scope.lean`)
- **Spec clauses:** Principle §1 item 3 (Renaming: *"Renaming user-chosen names one-to-one never changes whether a text is allowed or what any claim means"*), §5 (a renaming with both verdicts), `SPEC.md` §5 Finding 2, `README.md:47, 130`
- **Code locations:** `src/reality2/syntax.py:22` (`MAX_PROGRAM_BYTES`), `src/reality2/syntax.py:293` (`parse_program`), `metatheory/Scope.lean:273` (`check_rename`)
- **Severity:** **medium**
- **Confidence:** **high**

## Root cause

Principle §1 item 3 states unconditionally:
> *"3. **Renaming.** Renaming user-chosen names one-to-one never changes whether a text is allowed or what any claim means."*

`SPEC.md` §5 Finding 2 marks *"renaming flips the verdict"* as **fixed**, citing `test_02_renaming`, `test_rename.py`, and Lean's `check_rename`.

However, `syntax.parse_program` (`syntax.py:293`) enforces `MAX_PROGRAM_BYTES = 1_000_000` on **raw source bytes** before lexing, and `tokenize` (`syntax.py:67`) enforces `MAX_LINE_BYTES = 16_384` on raw line bytes:

```python
if len(raw) > MAX_PROGRAM_BYTES:
    fail("R001", "1", f"the program is longer than {MAX_PROGRAM_BYTES} bytes (Reality bounds)", 0)
```

Because a longer identifier (`aaaaa` vs `a`) occupies more bytes while leaving the token stream and AST identical up to alpha-renaming, **any** accepted program within a few bytes of `MAX_PROGRAM_BYTES` (or any line within a few bytes of `MAX_LINE_BYTES`) flips from `accepted` (`rc = 0`) to `refused [R001]` (`rc = 1`) when its user-chosen identifier is renamed one-to-one! `Scope.lean`'s `check_rename` misses this because `Scope.lean` operates on parsed `Prog` ASTs with no byte-length bound.

## Minimal reproducing files and commands

Saved in `findings\`:
- `findings\08-byte-cap-breaks-renaming-invariance.rl` (999,998 bytes: comment header + `file a = sha256:...` + `claim size(a) is 4`)
- `findings\08-renamed.rl` (1,000,006 bytes: **identical** comment header + one-to-one renaming `a` -> `aaaaa`: `file aaaaa = sha256:...` + `claim size(aaaaa) is 4`)
- `findings\08-four.bin` (4 bytes: `abcd`)

Last two lines of `findings\08-byte-cap-breaks-renaming-invariance.rl`:
```text
file a = sha256:88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589
claim size(a) is 4
```

Last two lines of `findings\08-renamed.rl` (exact 1-to-1 renaming $\sigma = \{a \mapsto \text{aaaaa}\}$):
```text
file aaaaa = sha256:88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589
claim size(aaaaa) is 4
```

### Command 1 (before renaming)
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\08-byte-cap-breaks-renaming-invariance.rl --files findings\08-four.bin
```

### Actual output 1 (`rc = 0`)
```text
line 10001: formed: ByteCount[#1] = 4 (Exact)
  #1 = sha256:88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589
accepted
```

### Command 2 (after 1-to-1 renaming `a` -> `aaaaa`)
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\08-renamed.rl --files findings\08-four.bin
```

### Actual output 2 (`rc = 1`)
```text
line 0: refused [R001, item 1]: the program is longer than 1000000 bytes (Reality bounds)
refused: the program is not Reality text
```

## Spec §5 demonstration

- **Formed text:** `findings\08-byte-cap-breaks-renaming-invariance.rl` + `findings\08-four.bin` (`accepted`, `rc = 0`).
- **§5 demonstration:** One-to-one renaming of the single user-chosen identifier `a` to `aaaaa` yields `findings\08-renamed.rl`, which `reality2` **refuses** (`R001`, `rc = 1`) — directly exhibiting *"a renaming with both verdicts"* under Principle §5 and §1 item 3.
- **Why neither defence applies:** The original text forms (`rc = 0`), and renaming invariance is an unconditional text-level property (§1 item 3).

## Fix direction

Bound programs by **renaming-invariant** syntactic measures — e.g., maximum statement count, maximum token count per line/program, maximum string-literal byte length, and maximum comment byte length (counting every identifier token as fixed weight `1` in the size budget while reading lines with a generous physical safety ceiling only after lexing identifiers), preserving $O(N)$ DoS protection and strict 1-to-1 renaming invariance over all valid identifiers.
