# 12. A NIfTI-2 BOLD file with an exact float64 TR fails B09: whole NIfTI-2 datasets never conform

- **Category:** must-form refused (overcorrection) / bug
- **Spec clauses:** §10.2 C (check every machine-checkable 1.0.1 rule, but correctly); BIDS 1.0.1 §8.4 ("consistent with pixdim[4]"); SPEC §2 item 9 **[call]** "nearest float32"
- **Severity:** medium (every NIfTI-2 dataset whose TR is not a dyadic rational, for example 0.72 s, 0.8 s or 2.2 s, is refused as a whole). **Confidence:** high.

## What happens

`bids101.read` compares `f32_nearest(RepetitionTime / unit)` with `header.pixdim[4]`
(`bids101.py:306`). For NIfTI-2, `pixdim` is float64 (`readers._f64`), so a correct header holds the
float64 nearest 0.72, which differs from the float32 nearest 0.72. B09 fails, and with it the whole
dataset, so nothing BIDS-based forms. B05 accepts NIfTI-2 files, so they are clearly meant to be
supported.

## Reproduce

`gen/gen_12.py` writes `12-nifti2/`: one subject, one NIfTI-2 BOLD file (`pixdim[4] = 0.72`
as float64, `xyzt_units = 10`), `task-x_bold.json` with `"RepetitionTime": 0.72`, an events file and
participants.tsv. Its manifest is `12-nifti2.manifest`.

```
.venv\Scripts\python.exe -m reality2 check findings\12-nifti2-tr-never-consistent.rl --files findings\12-nifti2.manifest --root findings\12-nifti2
```

Output (`12.out`):

```
line 2: refused [B00, reading rules]: the dataset does not conform to BIDS 1.0.1 (1 failures), so nothing BIDS-based forms from it (principle §1, whole-dataset conformance). B09 x1, first: sub-01/func/sub-01_task-x_bold.nii: RepetitionTime 18/25 s is not consistent with pixdim[4] 3242591731706757/4503599627370496 (§8.4; consistent means pixdim[4] is the nearest float32 to RepetitionTime in the header's time unit)
refused (1 statement)
```

## Fix

Round to the header's own storage type: float32 for NIfTI-1, float64 for NIfTI-2. Add a NIfTI-2 case
to `test_bids.py`.
