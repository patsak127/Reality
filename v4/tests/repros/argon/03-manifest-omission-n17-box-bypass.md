# 03 — Author-chosen manifest subsetting plus zero-subject / folderless-participant allowance forms BIDS claims (`F1`) on the incomplete `ds001734-box` copy (`N17` bypass)

- **Category:** **hit** (also central to Review (c) false-vs-nonsense boundary and (d) `SPEC.md` §2 item 1 & item 9)
- **Spec clauses:** Principle §1 Whole-dataset conformance, §1 Reading rules (reading comes from the named standard alone, never chosen by the author), §1 "False is not nonsense" boundary, §5 Must-not-form #17 (`N17`), BIDS 1.0.1 §3.2 Definition 1 (`context/sources/bids-1.0.1.txt:179–180`), `SPEC.md` §2 item 1 & item 9
- **Code locations:** `src/reality2/bids101.py:259–408` (`load`), `src/reality2/bids101.py:362–395` (`participants.tsv` check), `SPEC.md:35, 64`, `README.md:84`
- **Severity:** **high**
- **Confidence:** **high**

## Root cause

Three implementation choices in `bids101.py` and `SPEC.md` §2 interact to defeat whole-dataset BIDS conformance (`N17`) without fabricating a single neuroimaging byte:

1. **Zero-subject datasets accepted (`bids101.py:259–408`):** BIDS 1.0.1 §3.2 Definition 1 (`bids-1.0.1.txt:179–180`) explicitly defines a BIDS dataset as:
   > *"1. Dataset - a set of neuroimaging and behavioural data acquired for a purpose of a particular study. **A dataset consists of data acquired from one or more subjects**, possibly from multiple sessions."*
   `bids101.load` never checks `len(subjects) >= 1` or `len(recordings) >= 1` (nor presence of any MRI modality `func`/`anat`/`dwi`/`fmap`).
2. **Folderless `participants.tsv` rows accepted (`SPEC.md` §2 item 9, `bids101.py:362–395`):** `bids101.load` allows `participants.tsv` to list 108 subjects (`sub-001`..`sub-124`) even when **none** of those subjects have a `sub-<label>/` folder in the dataset.
3. **Author-chosen manifest file list (`SPEC.md` §2 item 1):** A dataset is defined solely by the `reality-manifest 1` file list the author constructs.

Combine these on the **unmodified `tests/data/ds001734-box/` fixture** — the exact 548-file incomplete copy used for must-not-form test `N17` (`README.md:84`: *"The box copy of ds001734 has no images, so it refuses: 432 events files lack their BOLD file and 216 fieldmap sidecars lack their images (N17)"*):
- Using `reality2 manifest tests/data/ds001734-box` includes the broken `sub-*/` directories and refuses (`N17`).
- Listing only `dataset_description.json` and `participants.tsv` from `tests/data/ds001734-box` (every byte genuine, zero fabricated NIfTIs) **passes `bids(d)`** and **forms `F1`'s exact BIDS claim** on `ds001734-box`!

Even when a dataset has real neuroimaging folders (say 108 subjects), an author can construct 2^108 - 1 non-empty subsets of subjects in the manifest (for instance, keeping only the 54 `equalRange` subjects so `share(where(participants(b), eq("group", "equalRange")))` becomes `54/54` instead of `54/108` if `participants.tsv` is edited, or — without touching `participants.tsv` at all! — dropping any subset of `sub-*/` folders whose `events.tsv` or `bold.nii.gz` happened to fail `B06`/`B09` so that `F1` still forms on a broken dataset!).

## Minimal reproducing files and command

Saved in `findings\`:
- `findings\03-manifest-omission-n17-box-bypass.rl`
- `findings\03-box2.manifest` (2-entry manifest referencing the unmodified `dataset_description.json` and `participants.tsv` inside `tests\data\ds001734-box`)

`findings\03-box2.manifest`:
```text
reality-manifest 1
ed2b5cd62ca371dc6fb91fe1a9ffbfdd6abbf1ec0f53c20726bcbe97bf3e1c9d	1015	dataset_description.json
d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8	2765	participants.tsv
```

`findings\03-manifest-omission-n17-box-bypass.rl`:
```text
dataset d = sha256:aea79593c2bec4d88382cc73619daf8cfff6ea580b85d72458b4a51d589ef0fe
let b = bids(d)
claim count(where(participants(b), eq("group", "equalRange"))) is 54
```

### Command
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\03-manifest-omission-n17-box-bypass.rl --files findings\03-box2.manifest --root tests\data\ds001734-box
```

### Actual output (`rc = 0`)
```text
line 3: formed: Count[Rows[Participants[BIDS-1.0.1[#1] from #2] where ExtraCell col 2 = "equalRange"]] = 54 (Exact)
  #1 = sha256:aea79593c2bec4d88382cc73619daf8cfff6ea580b85d72458b4a51d589ef0fe
  #2 = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
accepted
```

## Spec §5 demonstration

- **Formed text:** `findings\03-manifest-omission-n17-box-bypass.rl` + `findings\03-box2.manifest` against unmodified `tests\data\ds001734-box` (`accepted`).
- **§5 demonstration:**
  1. **Must-not-form #17 (`N17`) & BIDS 1.0.1 §3.2 Def. 1 break:** Principle §5 #17 requires refusing a BIDS-based claim on a dataset missing its neuroimaging files (*"a dataset with missing BOLD files does not conform to BIDS 1.0.1 even if the file the claim touches is present"*). Here the manifest contains **zero** `sub-<label>/` folders and **zero** neuroimaging files, violating BIDS 1.0.1 §3.2 Def. 1 (*"data acquired from one or more subjects"*), while `participants.tsv` explicitly declares 108 subjects (`sub-001`..`sub-124`).
  2. **False-vs-nonsense boundary (§1):** This defect is **not** "visible only against the world" (the fabrication defence): **from the supplied text alone** (`03-box2.manifest` + `participants.tsv`), 108 subjects are listed in `participants.tsv` and 0 subject folders exist in the manifest. Moreover, on a dataset where 1 of 108 subjects has a broken BOLD header, omitting that `sub-XXX/` folder from the manifest while keeping all 108 rows in `participants.tsv` lets the author choose a manifest projection that silences `B00` while still claiming `Count[Rows[Participants[BIDS-1.0.1[#1] ...]]] = 54` over all 108 participants!
- **Why neither defence applies:** `reality2` forms the claim (`rc = 0`), and both the 0-subject violation and the 108-row vs 0-folder mismatch are strictly internal to the supplied bytes.

## Fix direction

1. Enforce BIDS 1.0.1 §3.2 Def. 1 in `bids101.load`: require at least one `sub-<label>/` folder containing at least one BIDS neuroimaging scan (`func`, `anat`, `dwi`, or `fmap`).
2. Require exact bidirectional agreement (or at minimum: every `participants.tsv` row must have a `sub-<label>/` folder in the manifest, and every `sub-<label>/` folder must appear in `participants.tsv` when `participants.tsv` is present), so an author cannot drop broken subject folders while keeping `participants.tsv` intact.
3. Print dataset summary counts in the BIDS sort (`BIDS-1.0.1[#1: 108 subjects, 432 BOLD recordings]`) so any subject/recording omission changes the explicit subject of the claim rather than hiding behind an opaque manifest hash (analyzed in detail in `findings\INDEX.md` §(d)).
