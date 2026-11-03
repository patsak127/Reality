# 18 — `Recorded[s]` acts as a prose disclaimer that permits zero-tolerance strict inequalities (`exceeds` / `below`) on rounded sidecar/event numbers

- **Category:** **design issue** (also concerns `SPEC.md` §2 item 8 **[call]** and Principle §10.2 One Standard of Accuracy)
- **Spec clauses:** Principle §10.2 (One standard of accuracy: *"No standard may demand total accuracy in one aspect while accepting 'true enough' in another"*; *"A label is not a defence"*), Principle §1 item 5, `SPEC.md` §2 item 8
- **Code locations:** `src/reality2/kernel.py:42–51` (`Num`), `src/reality2/kernel.py:428–457` (`c_exceeds`, `c_below`), `src/reality2/kernel.py:545, 560` (`c_tr`, `event`), `src/reality2/kernel.py:604` (`render`)
- **Severity:** **medium**
- **Confidence:** **high**

## Root cause

Principle §10.2 states:
> *"No standard may demand total accuracy in one aspect while accepting 'true enough' in another ... Precision is part of every value's type (`Exact` vs `Interval`), never an unlabelled rounding."*

And Principle §1 / `REVIEW.md:62` emphasizes that **"labelled" is not a defence**.

In `SPEC.md` §2 item 8, v2 introduces a third precision tag, **`Recorded[s]`**, for BIDS `RepetitionTime`, `onset`, and `duration` (`kernel.py:545, 560`). Internally, `Num(v, v, "s", recorded=True)` stores a **zero-width point interval `[v, v]`** (`lo == hi == v`) alongside boolean `recorded=True`!

Look at the resulting two-standard asymmetry (`kernel.py:428–457, 604`):
1. On a plain TSV decimal cell holding `4.071` (say a rounded millisecond timestamp), the spec's motivation for `widen(..., tolerance = 0.0005)` is that a finite decimal recording in a table has measurement/rounding uncertainty; comparing it within $10^{-9}$ without `tolerance` overstates precision unless it is genuinely an exact mathematical value.
2. On a BIDS `events.tsv` cell holding the **exact same bytes `4.071`**, `onset(r, 1)` represents a **physical stimulus onset time in seconds** measured and rounded to 1 ms (`0.001 s`). Yet because `Num` sets `lo = hi = 4.071` and `recorded = True`, `reality2` **forms** both:
   - `claim exceeds(onset(r, 1), c = 4.070999999)`
   - `claim below(onset(r, 1), c = 4.071000001)`
   with **zero tolerance**, justifying a 1-nanosecond strict inequality on a 1-millisecond-rounded sidecar number solely by appending the prose disclaimer **`"holds of the recorded value"`**!
3. Worse, notice the unit inconsistency between `is` and `exceeds`/`below` (`kernel.py:432` vs `kernel.py:622`):
   - `claim onset(r, 1) is 4.071` **refuses with `U002`** because `4.071` lacks the unit `s` (`claim onset(r, 1) is 4.071 s` is required)!
   - Yet `claim exceeds(onset(r, 1), c = 4.070999999)` **forbids** writing `s` in `c = ...` (`syntax.py:194` `slot` rejects units on slot numbers!) and silently auto-attaches `x.val.unit` (`s`) to the unitless parameter `c` (`kernel.py:441`: `u = f" {x.val.unit}" if x.val.unit else ""`)! Thus a scientist writes a **unitless** cutoff `c = 4` against a quantity in seconds and `reality2` supplies the unit `s` by default — contradicting `README.md:63` (*"There are no defaults and no slots for df, n or units"*) and `U002`!

## Minimal reproducing files and command

Saved in `findings\`:
- `findings\18-recorded-precision-quasi-label-and-comparisons.rl`
- `findings\18-manifest.txt`
- `findings\18-root\` (`sub-01_task-x_events.tsv` with `onset = 4.071`, `duration = 1.000`)

`findings\18-recorded-precision-quasi-label-and-comparisons.rl`:
```text
dataset d = sha256:f659f26d7d67cf41580df816e3c57b4e841eb44f78be2cc88548ad868b34517b
let r = recording(bids(d), "01", "x")
claim exceeds(onset(r, 1), c = 4.070999999)
claim below(onset(r, 1), c = 4.071000001)
```

### Command
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\18-recorded-precision-quasi-label-and-comparisons.rl --files findings\18-manifest.txt --root findings\18-root
```

### Actual output (`rc = 0`)
```text
line 3: formed: Exceeds[EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x: #2], #3 row 1], c = 4.070999999 s] holds of the recorded value
  #1 = sha256:f659f26d7d67cf41580df816e3c57b4e841eb44f78be2cc88548ad868b34517b
  #2 = sha256:35045e26af8ad0d01e4c6c2e9061de0e76fe5208a738f23df3606ecd101143a2
  #3 = sha256:ff45b57287d316db41f26cfa843f72aba1dcad757b1a197e3ade3e7e889bf595
line 4: formed: Below[EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x: #2], #3 row 1], c = 4.071000001 s] holds of the recorded value
  #1 = sha256:f659f26d7d67cf41580df816e3c57b4e841eb44f78be2cc88548ad868b34517b
  #2 = sha256:35045e26af8ad0d01e4c6c2e9061de0e76fe5208a738f23df3606ecd101143a2
  #3 = sha256:ff45b57287d316db41f26cfa843f72aba1dcad757b1a197e3ade3e7e889bf595
accepted
```

## Fix direction

1. Require `c` in `exceeds(x, c = ...)` and `below(x, c = ...)` (and `tolerance` in `widen(x, tolerance = ...)`) to carry the **exact same explicit unit** as `x` (`c = 4.071 s`, refusing unit mismatch with `U002` just like `is` does!).
2. Either restrict `Recorded[unit]` to direct `is recorded as ...` inspection unless explicitly widened via `widen(..., tolerance = ... s)` before entering `exceeds` / `below`, or make `Recorded` carry at least half-ULP decimal/float representation bounds when compared as a physical timing rather than using `"holds of the recorded value"` as a prose label.
