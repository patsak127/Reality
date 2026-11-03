# 09 — Call-by-name `let` re-evaluation without step counting causes $O(2^k)$ blowup (`steps.n == 3`), making verdicts depend on machine RAM

- **Category:** **hit** (regression of v1 Findings 11 & 12; also a direct model-vs-code divergence from `metatheory/Scope.lean`)
- **Spec clauses:** Principle §1 item 4 (no machine or memory-limit dependence), §5 (two runs differing in one outside factor: available memory), `SPEC.md` §2 item 12 & §5 Findings 11 & 12, `README.md:130`
- **Code locations:** `src/reality2/kernel.py:151–156` (`meaning` on `Name`), `src/reality2/kernel.py:399–410` (`c_difference`), `src/reality2/kernel.py:659` (`let_stmt`), `src/reality2/kernel.py:710` (`HASH_RE.sub`), `metatheory/Scope.lean:183` (`Stmt.let_`)
- **Severity:** **high**
- **Confidence:** **high**

## Root cause

`SPEC.md` §2 item 12 states:
> *"Bounds. Program size, line length, nesting, let-depth (R001, R005), counted steps (R002), bytes read (R003, R004). These refuse; they never answer 'no'. They are the same constants on every machine, so verdicts don't depend on the machine."*

And `metatheory/Scope.lean:183` models `let` as **call-by-value** (evaluating the right-hand side once to a `Val` and binding `Val` in `Env`).

In `src/reality2/kernel.py`, however, `let_stmt` (`kernel.py:659`) evaluates the right-hand side once **and discards the computed `M`**, storing the **unevaluated AST `st.expr`** in `self.lets[st.name] = st.expr` (so that future claims can replay its `store` trace)! Then `meaning` (`kernel.py:151–156`) re-evaluates `self.lets[e.v]` **from scratch every time `e.v` is referenced** (call-by-name, no DAG memoization):

```python
if isinstance(e, Name):
    ...
    if e.v in self.lets:
        if d > MAX_LET_DEPTH:
            fail("R005", "1", "let definitions are nested deeper than 64")
        return self.meaning(self.lets[e.v], d + 1)
```

Worse:
1. Neither `meaning()` nor `c_difference()` (`kernel.py:399–410`) calls `self.store.steps.tick()`! A chain of $k$ lines `let x_{i+1} = difference(x_i, x_i)` has AST depth `1`, `let`-depth $k \le 64$ (passing `R005`), and **`steps.n == 3` out of `200,000,000`** (completely invisible to `R002`)!
2. Yet `c_difference` performs $2^k$ recursive evaluations and allocates `f"Difference[{a.sort}, {b.sort}]"`, doubling string length at every line:
   - At $k = 19$ (22 lines total), `steps.n` is **3**, while the output line is **26,214,507 bytes** (~26.2 MB).
   - At $k = 26..29$ (~30 lines total, well below `MAX_LET_DEPTH = 64`), `m.sort` requires **3.3 GB to 26 GB of RAM**.
   - A machine with sufficient RAM **forms** the claim (`accepted`), while a machine or container with less RAM hits `MemoryError` — either refusing with `X001: internal error MemoryError` inside `statement()` (`kernel.py:668`) or **crashing with an uncaught `MemoryError` traceback** at `HASH_RE.sub` (`kernel.py:710`, which lies *outside* `try ... except Exception:`!).

## Minimal reproducing files and commands

Saved in `findings\`:
- `findings\09-let-call-by-name-exponential-blowup.rl` (22 lines, $k = 19$)
- `findings\09-val.tsv` (`x\n1\n`, 4 bytes)
- `findings\09-run-memcap.py` (runs the exact CLI command uncapped vs inside a 55 MB Win32 Job Object memory cap in < 1 second)

`findings\09-let-call-by-name-exponential-blowup.rl`:
```text
file f = sha256:daff832f802000e645771a60983c76c963f6ee602a6230e45237bd360e91cc1a
let x0 = number(cell(tsv(f), 1, 1))
let x1 = difference(x0, x0)
let x2 = difference(x1, x1)
...
let x19 = difference(x18, x18)
claim x19 is 0
```

### Command 1 (direct CLI on an uncapped machine)
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\09-let-call-by-name-exponential-blowup.rl --files findings\09-val.tsv
```

### Actual output 1 (`rc = 0`, 26,214,507 bytes written to stdout)
```text
line 22: formed: Difference[Difference[Difference[... 524,288 leaf terms ...], Decimal[Cell[TSV[#1], row 1, col 1]]]]]]]]]]]]]]]]]]]]] = 0 (Exact)
  #1 = sha256:daff832f802000e645771a60983c76c963f6ee602a6230e45237bd360e91cc1a
accepted
```

### Command 2 (comparing uncapped vs 55 MB memory ceiling on the exact same files)
```powershell
.venv\Scripts\python.exe findings\09-run-memcap.py
```

### Actual output 2
```text
[Uncapped] rc=0, stdout=26214507 bytes, verdict=accepted
[55 MB cap] rc=1
line 20: refused [X001, bug]: internal error MemoryError; nothing formed (please report)
line 21: refused [N003, item 1]: a name used here comes from the statement on line 20, which was refused
line 22: refused [N003, item 1]: a name used here comes from the statement on line 21, which was refused
refused (3 statements)
```

## Spec §5 demonstration

- **Formed text:** `findings\09-let-call-by-name-exponential-blowup.rl` + `findings\09-val.tsv` (`accepted` on an uncapped machine).
- **§5 demonstration:** Two runs on the **exact same `.rl` program and `.tsv` bytes** differing solely in an outside factor — available process RAM (§1 item 4) — produce opposite verdicts: `accepted` (`rc = 0`) vs `refused [X001, bug]: internal error MemoryError` (`rc = 1`). Extending the chain by 8 more lines (`x27`, still depth 27 < 64 and `steps.n == 3`) reproduces the exact same split across full physical machines (e.g., an 8 GB laptop vs a 64 GB workstation).
- **Why neither defence applies:** The uncapped run forms the claim (`rc = 0`), and `SPEC.md` §2 item 12 explicitly requires resource bounds (`R001`–`R005`) to fire deterministically before machine limits so verdicts never depend on the machine.

## Fix direction

1. Tick `self.store.steps.tick()` on **every** `meaning()` call and bound total sort/output size by a deterministic constant (e.g., `MAX_SORT_NODES` / `MAX_OUTPUT_BYTES`), raising `R002` deterministically before memory exhaustion.
2. Evaluate `let` **call-by-value** (matching `Scope.lean:183`!): store `(M, trace_of_let)` in `self.lets[name]` so referencing `x_i` replays `trace_of_let` in $O(|\text{unique files}|)$ instead of re-evaluating the expression tree $2^k$ times.
