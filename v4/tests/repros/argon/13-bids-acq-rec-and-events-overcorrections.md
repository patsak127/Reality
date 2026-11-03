# 13 — `recording()` refuses every multi-`acq` or multi-`rec` BIDS 1.0.1 dataset (`V004`), and the BIDS surface cannot count/filter `events.tsv` or read scientific-notation floats in `events.tsv`

- **Category:** **must-form refused (overcorrection)**
- **Spec clauses:** Principle §1 item 1 / item 2, §5 (`REVIEW.md` b: *"anything a careful scientist would need and the spec says should form, but v2 refuses"*), BIDS 1.0.1 §§4.2, 8.3, 8.4 (`acq-<label>`, `rec-<label>`, `events.tsv`)
- **Code locations:** `src/reality2/kernel.py:498–523` (`c_recording`), `src/reality2/kernel.py:547–566` (`event`), `src/reality2/bids101.py:341` (`B06` decimal check)
- **Severity:** **high**
- **Confidence:** **high**

## Root cause

Three BIDS 1.0.1 restrictions in `kernel.py` and `bids101.py` prevent careful scientists from forming basic, unambiguous BIDS 1.0.1 claims on compliant datasets:

1. **Every multi-`acq` or multi-`rec` BOLD dataset is unqueryable (`kernel.py:498–520`):**
   BIDS 1.0.1 §8.4 explicitly defines optional `acq-<label>` (e.g. `acq-ap` / `acq-pa`, `acq-multiband` / `acq-singleband`) and `rec-<label>` entities on functional BOLD images to distinguish multiple acquisitions or reconstructions of the same `sub`/`task`/`run`. `bids101.py` parses `acq` and `rec` (`FUNC_ENT = ("sub", "ses", "task", "acq", "rec", "run")`), **and `recording()` even prints `acq` and `rec` in its output sort** (`BOLDRecording[..., sub 01 task x acq a: #2]`, `kernel.py:521`).
   Yet `c_recording` (`kernel.py:499, 515–519`) accepts only `(b, sub, task[, run])` (3 or 4 positional args, zero named slots for `acq` or `rec`) and filters via:
   ```python
   hits = [r for r in ds.recordings if all(dict(r.ents).get(k) == v for k, v in want.items())
           and set(dict(r.ents)) - {"acq", "rec"} == set(want)]
   ```
   Consequently, whenever a valid BIDS 1.0.1 dataset contains two acquisitions (`acq-ap` and `acq-pa`) or two reconstructions for `(sub, task, run)`, `len(hits) == 2` and **no recording in that subject/task can be named at all** (`refused [V004]`)!
2. **No BIDS `events(r)` table expression (`kernel.py:547–566`):**
   On a BIDS recording `r`, v2 provides only `onset(r, i)` and `duration(r, i)` for a hardcoded row integer `i`. A scientist cannot ask via BIDS how many trials occurred (`rows(events(r))`), how many trials had `trial_type = "gamble"`, what a participant's mean/sum `response_time` was, or read extra task columns (`gain`, `loss` in NARPS `ds001734`) without dropping down to raw `file` hashes — losing whole-dataset BIDS conformance and BIDS inheritance!
3. **Standard scientific notation (`1.5e-2`, `0e+00`) in `events.tsv` refuses the entire dataset (`bids101.py:341`):**
   Many BIDS exporters (`nibabel`/MATLAB/Python `numpy.savetxt`/BIDS converters) format small event durations or sub-millisecond onsets in standard IEEE ASCII scientific notation (`0.000000e+00`, `5e-3`). `readers.parse_json` accepts scientific notation in JSON sidecars, yet `bids101.py:341` calls `readers.decimal()` (`-?[0-9]+(\.[0-9]+)?`) on `events.tsv`, causing a single `5e-3` in **any** subject's `events.tsv` to fail `B06` and **refuse every BIDS claim across the entire dataset (`B00`)**!

## Minimal reproducing files and command

Saved in `findings\`:
- `findings\13-bids-acq-rec-and-events-overcorrections.rl`
- `findings\13-manifest.txt`
- `findings\13-root\` (a 100%-compliant BIDS 1.0.1 dataset with `sub-01_task-rest_acq-ap_bold.nii` and `sub-01_task-rest_acq-pa_bold.nii`)

`findings\13-bids-acq-rec-and-events-overcorrections.rl`:
```text
dataset d = sha256:6b21a3f2bd5fc559b492e8ef6b7796588c99dd100357c5e355dfdb4c6af21968
claim volumes(recording(bids(d), "01", "rest")) is 10
```

### Command
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\13-bids-acq-rec-and-events-overcorrections.rl --files findings\13-manifest.txt --root findings\13-root
```

### Actual output (`rc = 1`)
```text
line 2: refused [V004, item 2]: recording(): 2 BOLD recordings in the dataset match sub-01 task-rest; exactly one is needed
refused (1 statement)
```

## Impact and fix direction

- Accept optional entity selectors on `recording(...)` (e.g., optional named or entity arguments for `run`, `acq`, `rec`, requiring any present entity on matched files to be disambiguated when `len(hits) > 1`).
- Expose `events(r)` as a BIDS-backed table sort (`Events[BOLDRecording[...], #3]`) supporting `rows`, `where`, `count`, `share`, `extra`/`cell`, and `sum`/`min`/`max`.
- Accept bounded standard scientific notation (`-?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]{1,4})?`) consistently in both JSON and BIDS numeric TSV columns.
