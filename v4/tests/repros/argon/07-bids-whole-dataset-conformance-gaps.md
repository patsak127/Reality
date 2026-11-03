# 07 — Whole-dataset BIDS 1.0.1 conformance misses malformed `func/` files, non-object `.json` sidecars, unvalidated `phenotype/` & root `.tsv`s, `run-1` + `run-01` coexistence, `TaskName` collisions, and invalid `EchoTime`s

- **Category:** **hit**
- **Spec clauses:** Principle §1 Whole-dataset conformance, §1 Reading rules, §10.2 (One standard of accuracy), `bids/RULES-1.0.1.md` (`B02`, `B03`, `B05`, `B08`, `B10`, `B12`, `B14`, `B16`), BIDS 1.0.1 §§3.3, 3.5, 4.2, 8.1, 8.3–8.5, 8.9, 8.11
- **Code locations:** `src/reality2/bids101.py:107–166` (`_classify`), `src/reality2/bids101.py:182` (`B03`), `src/reality2/bids101.py:279–358` (`load` per-kind checks)
- **Severity:** **high**
- **Confidence:** **high**

## Root cause

Principle §1 states:
> *"When a reading standard has whole-dataset conformance, a dataset that fails conformance in any file fails as a whole, even if the file a claim touches is clean."*

Checking `src/reality2/bids101.py` line-by-line against `context/sources/bids-1.0.1.txt` and `bids/RULES-1.0.1.md` reveals **eight** conformance holes where plainly non-conformant BIDS 1.0.1 files pass `bids(d)` without refusal:

1. **`B03` fails to check non-inherited BIDS `.json` files (`bids101.py:182, 260–408`):** `bids/RULES-1.0.1.md` states for `B03`: *"every BIDS-defined `.json` is valid strict JSON ... and a JSON object"*. Yet `isinstance(obj, dict)` is only checked inside `_inherited_meta` (`bids101.py:182`) and on `dataset_description.json` (`bids101.py:268`). `participants.json`, `sub-01/anat/sub-01_T1w.json`, `sub-01/func/*_sbref.json`, and `sub-01/fmap/*_magnitude1.json` containing `[1, 2, 3]` or `42` are never checked!
2. **Malformed or misordered files inside `sub-<label>/func/` (and `anat/`, `fmap/`) silently become `"extra"` (`bids101.py:146–162`):** Because `_classify` treats any path failing its exact regex/entity-order match as `"extra"` (`SPEC.md` §2 item 9), placing `sub-01/func/sub-01_run-1_task-ab_bold.nii` (entities `run` and `task` in the illegal reverse order, violating BIDS 1.0.1 §8.4) or `sub-01/func/corrupt_unparsed.nii` (corrupt non-NIfTI bytes inside `func/`) is silently ignored instead of failing BIDS conformance!
3. **BIDS 1.0.1 `phenotype/*.tsv` (§8.11), `*_events.json` (§4.2), subject-level inherited `*_events.tsv` (§3.5), and entity-less root `events.tsv` / `dwi.bval` are ignored as `"extra"` (`bids101.py:130–162`):** None of these BIDS-1.0.1-defined files are either validated or refused with `B14` (unimplemented BIDS kind). Even malformed TSV/JSON inside `phenotype/scores.tsv` or root `events.tsv` passes `bids(d)`!
4. **`ROOT_DEFINED` (`README`, `CHANGES`, §8.1) is never read (`bids101.py:29, 132`):** `_classify` classifies root `README` and `CHANGES` as `"root-doc"`, and `load` never reads them — not even checking `F001` existence or UTF-8 validity!
5. **`run-1` and `run-01` (and `run-0`) coexist without lookalike/numeric collision refusal (`bids101.py:287`, `keys.py:30`):** BIDS 1.0.1 §8.4 defines `run-<index>` as a positive integer index (`1`, `01` denote run 1). `skeleton("1") != skeleton("01")`, so `sub-01_task-ab_run-1_bold.nii` and `sub-01_task-ab_run-01_bold.nii` coexist as two "distinct" recordings in the same dataset!
6. **`B08`'s `TaskName` consistency check is broken (`bids101.py:300–304`):** `B08` strips non-alphanumerics (`re.sub(r"[^A-Za-z0-9]", "", tn)`), allowing Run 1 (`"TaskName": "a b"`) and Run 2 (`"TaskName": "a-b"`) to give two different `TaskName` strings to the same `task-ab` label, while `tasknames.setdefault(tn, task) != task` is mathematically dead code (since `re.sub` is a deterministic function of `tn`, two distinct `task` labels can never come from the same `tn` after `cleaned.lower() != task.lower()`!).
7. **`B10` and `B12` fail to validate numeric types/signs on required MRI timing parameters (`bids101.py:310–314, 350–357`):** When `PhaseEncodingDirection` is present, `B10` checks `"EffectiveEchoSpacing" in meta` and `"EchoTime" in meta` by key presence only — `"EchoTime": "banana"` and `"EffectiveEchoSpacing": -9` pass! And in `B12` (`phasediff` fieldmaps, §8.9.1), `"EchoTime1": -5, "EchoTime2": -5` (negative and equal, yielding $\Delta\text{TE} = 0$) passes!
8. **`B16` duplicate `.nii` + `.nii.gz` check (`bids101.py:290`) only covers `func-bold`:** Having both `sub-01/anat/sub-01_T1w.nii` and `sub-01/anat/sub-01_T1w.nii.gz` (or `sbref` / `fmap`) passes without refusal!

## Minimal reproducing files and command

Saved in `findings\` (a single dataset combining **all eight** violations above, plus a folderless lookalike `sub-O1` in `participants.tsv`):
- `findings\07-bids-whole-dataset-conformance-gaps.rl`
- `findings\07-manifest.txt`
- `findings\07-root\`

`findings\07-bids-whole-dataset-conformance-gaps.rl`:
```text
dataset d = sha256:411b0d114e6e9174a02b4d53eb1c9fa315a935952665d1a8ebf40d189afb6ac6
let b = bids(d)
claim volumes(recording(b, "01", "ab", "1")) is 4
claim volumes(recording(b, "01", "ab", "01")) is 9
```

### Command
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\07-bids-whole-dataset-conformance-gaps.rl --files findings\07-manifest.txt --root findings\07-root
```

### Actual output (`rc = 0`)
```text
line 3: formed: VolumeCount[BOLDRecording[BIDS-1.0.1[#1], sub 01 task ab run 1: #2]] = 4 (Exact)
  #1 = sha256:411b0d114e6e9174a02b4d53eb1c9fa315a935952665d1a8ebf40d189afb6ac6
  #2 = sha256:35045e26af8ad0d01e4c6c2e9061de0e76fe5208a738f23df3606ecd101143a2
line 4: formed: VolumeCount[BOLDRecording[BIDS-1.0.1[#1], sub 01 task ab run 01: #2]] = 9 (Exact)
  #1 = sha256:411b0d114e6e9174a02b4d53eb1c9fa315a935952665d1a8ebf40d189afb6ac6
  #2 = sha256:d74d1a98dd29f21c395587a27ca959c271ce45d4ae9d82b32522b378147331d6
accepted
```

## Spec §5 demonstration

- **Formed text:** `findings\07-bids-whole-dataset-conformance-gaps.rl` + `07-manifest.txt` + `07-root\` (`accepted`, 2 formed BIDS claims).
- **§5 demonstration:**
  1. **Whole-dataset conformance & `RULES-1.0.1.md` break (§1):** `07-root\` violates BIDS 1.0.1 §§3.3, 3.5, 4.2, 8.1, 8.3, 8.4, 8.9.1, 8.11 and v2's own `B03` (`participants.json` is `[1, 2, 3]`, `sub-01_T1w.json` is `42`, `README` is invalid UTF-8 `\xff\xfe`, `sub-01/func/` contains corrupt and entity-swapped `.nii` files, `anat` has duplicate `.nii` and `.nii.gz`, `EchoTime` is `"banana"`, `EchoTime1 == EchoTime2 == -5`, `TaskName` differs across runs of `task-ab`, and `run-1` + `run-01` coexist).
  2. **Two readings (§1 item 2):** "Run 1 of subject 01 task ab" has two recordings (`run-1` with 4 volumes and `run-01` with 9 volumes), and `sub-01_T1w` has two image files (`.nii` and `.nii.gz`).
- **Why neither defence applies:** Both BIDS claims form (`rc = 0`), and every defect is directly in the supplied files.

## Fix direction

1. Parse and require JSON `dict` (`B03`) on **every** `.json` outside `derivatives/`/`sourcedata/`.
2. Inside `sub-<label>/{func,anat,fmap,dwi,beh}/`, refuse unrecognized or misordered `.nii`/`.nii.gz`/`.tsv`/`.json` files rather than treating them as `"extra"`; refuse `phenotype/` and inherited `.tsv`s with `B14` until implemented; read and verify `ROOT_DEFINED` files in the manifest.
3. Canonicalize `run-<index>` by integer value (`int(run) >= 1`, refusing `0` and refusing coexistence of `"1"` and `"01"`), track `task -> TaskName` to require a single consistent `TaskName` per `task` label, validate positive numeric `EchoTime` / `EffectiveEchoSpacing` / `0 < EchoTime1 < EchoTime2` (`EchoTime1 != EchoTime2`), and enforce `.nii`/`.nii.gz` uniqueness across all imaging modalities.
