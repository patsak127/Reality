# 11. One run index, two recordings: `run-1` and `run-01`, or a run-less file next to `run-1`

**Category:** hit (item 2: two readings of "run 1"; item 6: two formed claims about one
recording that cannot both hold).
**Spec clause:** §1 items 2 and 6; BIDS 1.0.1 §8.4 (`[_run-<index>]`; "If only one run was
acquired the suffix can be omitted"); SPEC §2 item 9 ("exact template match").
**Severity:** medium. **Confidence:** high that it forms; medium that it is a hit (1.0.1 never
defines `<index>` beyond its examples; later BIDS versions define it as a non-negative integer
that may be zero-padded, under which `1` and `01` are the same index).

## Program

`findings\11-run-index-two-recordings.rl`, with the made-up dataset `findings\11-ds\` (manifest in
`findings\11-m\`): sub-01 has `task-x_run-1_bold.nii` (5 volumes) and `task-x_run-01_bold.nii`
(7 volumes); sub-02 has `task-x_bold.nii` (no run, 4 volumes) and `task-x_run-1_bold.nii`
(9 volumes); each with its events file.

```
dataset d = sha256:c85cea891e44997f76fd10d9e559fc60e25e28c36867c154090e6d91f9f08a9c
let b = bids(d)
claim volumes(recording(b, "01", "x", "1"))
claim volumes(recording(b, "01", "x", "01"))
claim onset(recording(b, "01", "x", "1"), 1)
claim onset(recording(b, "01", "x", "01"), 1)
claim volumes(recording(b, "02", "x"))
claim volumes(recording(b, "02", "x", "1"))
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\11-run-index-two-recordings.rl --files findings\11-m --root findings\11-ds
line 3: formed: VolumeCount[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x run 1: #2]] = 5 (Exact)
line 4: formed: VolumeCount[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x run 01: #2]] = 7 (Exact)
line 5: formed: EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x run 1: #2], #3 row 1] is recorded as 1.5 s (Recorded[s])
line 6: formed: EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x run 01: #2], #3 row 1] is recorded as 3.25 s (Recorded[s])
line 7: formed: VolumeCount[BOLDRecording[BIDS-1.0.1[#1], sub 02 task x: #2]] = 4 (Exact)
line 8: formed: VolumeCount[BOLDRecording[BIDS-1.0.1[#1], sub 02 task x run 1: #2]] = 9 (Exact)
accepted
```

(The `#k = sha256:…` lines are in `findings\11-output.txt`; every BOLD file has its own hash.)

## Demonstration (§5)

- `run-<index>`: 1.0.1 calls the run entity an index ("will be indexed with a suffix: _run-01,
  _run-02, _run-03 etc."). Read as a number, `run-1` and `run-01` are the same run of the same task
  of the same subject, and the dataset holds two BOLD files for it; lines 3/4 (5 versus 7 volumes)
  and 5/6 are then two formed claims about one recording that cannot both hold (item 6). Read as a
  string, they are two runs. The text admits both readings (item 2) and v2 picks one silently.
- sub-02: 1.0.1 says the run suffix "can be omitted" only "if only one run was acquired". A
  run-less file next to a `run-1` file therefore says both "this is the only run" and "runs are
  indexed". v2 reads two recordings (lines 7, 8).
- v2 already treats "two files for one recording" as a failure when the two files differ only in
  `.nii` versus `.nii.gz` (B07); this is the same defect one level up.

## Cause

`classify` checks that a run label is digits (`bids101._index`, `bids101.py:29-30`, used at `:61`)
but recordings are matched by string equality (`kernel.py:515-516`), and nothing compares the runs
of one subject and task with each other.

## What would fix it

Read the run index as a number: two BOLD files of one subject, task, acq and rec whose run indices
are equal as numbers (or one with no run next to one with a run) are a B07-style failure ("two
files for one recording"). Compare `recording()`'s run argument numerically too.
