# 23. A consistent NIfTI-2 BOLD file fails B09: its float64 pixdim is compared with a float32

**Category:** bug / must-form refused (overcorrection): a dataset that conforms to BIDS 1.0.1 is
refused.
**Spec clause:** BIDS 1.0.1 §4.1 ("either 1.0 or 2.0 version"), §8.4 (RepetitionTime "needs to be
consistent with the 'pixdim[4]' field"); SPEC §2 item 9 [call] ("the nearest float32 in the
header's time unit"); README "NIfTI headers fully (I00x)".
**Severity:** low (ds001734 is NIfTI-1), but every NIfTI-2 dataset whose TR is not a dyadic
fraction (0.8 s, 0.72 s, 2.2 s …) is refused. **Confidence:** high.

## Program

`findings\23-nifti2-tr-float32.rl`, with the made-up dataset `findings\23-ds\` (manifest
`findings\23-m\`): a NIfTI-2 BOLD file whose pixdim[4] is the float64 nearest 0.8, time unit
seconds, and `task-x_bold.json` `"RepetitionTime": 0.8`.

```
dataset d = sha256:<see the .rl>
claim tr(recording(bids(d), "01", "x"))
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\23-nifti2-tr-float32.rl --files findings\23-m --root findings\23-ds
line 2: refused [B00, reading rules]: the dataset does not conform to BIDS 1.0.1 (1 failures), so nothing BIDS-based forms from it (principle §1, whole-dataset conformance). B09 x1, first: sub-01/func/sub-01_task-x_bold.nii: RepetitionTime 4/5 s is not consistent with pixdim[4] 3602879701896397/4503599627370496 (§8.4; consistent means pixdim[4] is the nearest float32 to RepetitionTime in the header's time unit)
refused (1 statement)
```

3602879701896397/4503599627370496 is the double nearest 0.8, i.e. exactly what a NIfTI-2 writer
stores for a TR of 0.8 s; the float32 nearest 0.8 is 13421773/16777216, so the comparison fails.

## Cause

`bids101.py:306` always compares with `f32_nearest(…)`, although `nifti_header` reads NIfTI-2's
pixdim as float64 (`readers.py:297`).

## What would fix it

Compare with the nearest value of the header's own float type: float32 for NIfTI-1, float64 for
NIfTI-2.
