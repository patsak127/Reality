# 06 — BIDS JSON inheritance resolves same-level sidecars by entity count and ASCII path order instead of refusing ambiguous same-level applicability

- **Category:** **hit**
- **Spec clauses:** Principle §1 item 2 (no two readings), §1 Reading rules (reading comes from the named standard alone, not an implementation tie-breaker), §1 Floor (`trace == named`), BIDS 1.0.1 §3.5 (`context/sources/bids-1.0.1.txt:250–258`), `bids/RULES-1.0.1.md` (`B15`), `SPEC.md` §2 item 9
- **Code locations:** `src/reality2/bids101.py:168–202` (`_inherited_meta`), `src/reality2/kernel.py:543–545` (`c_tr`)
- **Severity:** **high**
- **Confidence:** **high**

## Root cause

BIDS 1.0.1 §3.5 ("The Inheritance Principle", `bids-1.0.1.txt:251–252`) defines inheritance precedence **strictly by directory level**:
> *"Any metadata file (.json, .bvec, .tsv, etc.) may be defined at any directory level. The values from the top level are inherited by all lower levels unless they are overridden by a file at the lower level."*

BIDS 1.0.1 §3.5 does **not** define entity-count precedence among multiple applicable sidecars within the **same directory**, nor does it define ASCII filename precedence when two sidecars have the same directory depth and the same number of entities.

In `bids101._inherited_meta` (`bids101.py:175, 189–196`), however, v2 assigns each candidate JSON file `rank = (_level(src_path), len(ents))`, sorts `cands` by `(rank, src_path)`, and checks `B15` only when `prev_rank == rank and prev_val != v`:

1. **Same directory level, conflicting values (`level = 0`, `len(ents) = 1` vs `2`):**
   At the dataset root (`level = 0`), `task-y_bold.json` defines `"RepetitionTime": 3` and `task-y_acq-b_bold.json` defines `"RepetitionTime": 2`. Both files live at the **top directory level** and both match `sub-01/func/sub-01_task-y_acq-b_bold.nii`. Because `rank` compares `(0, 1)` vs `(0, 2)`, `B15` never fires (`prev_rank != rank`) and `bids101` silently picks `2` over `3` using an invented precedence rule absent from BIDS 1.0.1 §3.5!
2. **Equal `rank` (`(1, 2)` vs `(1, 2)`), tie-broken by ASCII path order:**
   In `sub-01/`, `sub-01_acq-a_bold.json` (`sha256:884cc661...`) and `sub-01_task-x_bold.json` (`sha256:1423355d...`) both have `rank = (1, 2)` and both define `"RepetitionTime": 2` (plus distinct non-conflicting keys `"FromAcq": 1` and `"FromTask": 1`). Because `prev_val == v`, `B15` does not fire; `sources["RepetitionTime"] = src_path` is overwritten on the second loop iteration solely because `"sub-01/sub-01_task-x_bold.json" > "sub-01/sub-01_acq-a_bold.json"` in ASCII! `c_tr` (`kernel.py:543–545`) then touches **only** that winning hash with a dummy `self.store.json(h, p, gate=False)` (discarding its return value) and prints `from #3` naming `sub-01_task-x_bold.json` alone — hiding `sub-01_acq-a_bold.json` completely.
3. **Unchecked entity order on root/subject `"meta"` files (`bids101.py:130–145`):**
   `_classify` never calls `_order_ok` on root or subject-level JSON sidecars (`"meta"`), so out-of-order root sidecars like `acq-a_task-x_bold.json` also participate in inheritance instead of failing conformance.

## Minimal reproducing files and command

Saved in `findings\`:
- `findings\06-bids-inheritance-ambiguous-precedence.rl`
- `findings\06-manifest.txt`
- `findings\06-root\`
  - `sub-01/sub-01_acq-a_bold.json` (`{"TaskName": "x", "RepetitionTime": 2, "FromAcq": 1}`)
  - `sub-01/sub-01_task-x_bold.json` (`{"TaskName": "x", "RepetitionTime": 2, "FromTask": 1}`)
  - `task-y_bold.json` (`{"TaskName": "y", "RepetitionTime": 3}`)
  - `task-y_acq-b_bold.json` (`{"TaskName": "y", "RepetitionTime": 2}`)

`findings\06-bids-inheritance-ambiguous-precedence.rl`:
```text
dataset d = sha256:ca2bea8cff0308f16d8d30520d555c8979d77a53d5588ab9a8a886c4ef9c8fec
let b = bids(d)
claim tr(recording(b, "01", "x")) is 2 s
claim tr(recording(b, "01", "y")) is 2 s
```

### Command
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\06-bids-inheritance-ambiguous-precedence.rl --files findings\06-manifest.txt --root findings\06-root
```

### Actual output (`rc = 0`)
```text
line 3: formed: RepetitionTime[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x acq a: #2], from #3] is recorded as 2 s (Recorded[s])
  #1 = sha256:ca2bea8cff0308f16d8d30520d555c8979d77a53d5588ab9a8a886c4ef9c8fec
  #2 = sha256:35045e26af8ad0d01e4c6c2e9061de0e76fe5208a738f23df3606ecd101143a2
  #3 = sha256:1423355deba04c74cfdde357e533eb90ed82b2542012d507f82fcb08dd699dc2
line 4: formed: RepetitionTime[BOLDRecording[BIDS-1.0.1[#1], sub 01 task y acq b: #2], from #3] is recorded as 2 s (Recorded[s])
  #1 = sha256:ca2bea8cff0308f16d8d30520d555c8979d77a53d5588ab9a8a886c4ef9c8fec
  #2 = sha256:35045e26af8ad0d01e4c6c2e9061de0e76fe5208a738f23df3606ecd101143a2
  #3 = sha256:00660ca31bd3c412a9ffe660b532ec9f881c2aaa454cb7bcb018bd32455b44f7
accepted
```

## Spec §5 demonstration

- **Formed text:** `findings\06-bids-inheritance-ambiguous-precedence.rl` + `06-manifest.txt` + `06-root\` (`accepted`, 2 formed claims).
- **§5 demonstration:**
  1. **Two readings under BIDS 1.0.1 §3.5 (§1 item 2 & Reading rules):** On line 4, both `task-y_bold.json` (`RepetitionTime = 3`) and `task-y_acq-b_bold.json` (`RepetitionTime = 2`) reside at the root directory level (`level = 0`), where BIDS 1.0.1 §3.5 specifies override only across directory levels — giving two readings (`3 s` vs `2 s`) resolved only by v2's private `len(ents)` tie-breaker.
  2. **Two readings of support / Floor break (line 3):** Both `sub-01_acq-a_bold.json` and `sub-01_task-x_bold.json` apply at the exact same specificity `(1, 2)`, yet the printed sort `from #3` names only `1423355d...` (`sub-01_task-x_bold.json`) by ASCII path order.
- **Why neither defence applies:** Both claims form (`rc = 0`), and the ambiguity is strictly internal to the supplied sidecar JSON files and the pinned BIDS 1.0.1 text.

## Fix direction

Match later BIDS validator clarifications of §3.5 and Principle §1 item 2: refuse (`B15`) whenever **more than one** metadata file at the **same directory level** applies to a given data file (or at minimum whenever two applicable files at the same directory level both define the same key, even if their values happen to agree, so `from #3` is uniquely determined without path-order tie-breaking), and enforce `_order_ok` on all `"meta"` JSON filenames.
