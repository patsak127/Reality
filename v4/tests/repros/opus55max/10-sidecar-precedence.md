# 10. The RepetitionTime comes from a precedence rule BIDS 1.0.1 does not define

**Category:** hit (reading-rule clause: "Links from files to the world come only from standards
fixed in advance, and only as far as each standard defines them"; item 2: two readings).
**Spec clause:** §1 *Reading rules*; SPEC §2 item 9 [call] "the inheritance order";
`bids/RULES-1.0.1.md` ("In the same folder, a file with more entities overrides one with fewer.
1.0.1 states the principle and gives examples, but not this ordering. The ordering is my
reading").
**Severity:** medium. **Confidence:** high that it forms; medium-high that it is a hit.

## Program

`findings\10-sidecar-precedence.rl`, with the made-up dataset `findings\10-ds\` (manifest in
`findings\10-m\`). One BOLD run, `sub-01_task-x_acq-a_rec-b_run-1_bold.nii` (pixdim[4] = 2.0,
seconds), and two sidecars in its own `func/` folder that both apply to it:

```
sub-01_task-x_acq-a_rec-b_bold.json   {"RepetitionTime": 2}            entities sub, task, acq, rec
sub-01_task-x_run-1_bold.json         {"RepetitionTime": 2.0000001}    entities sub, task, run
```

```
dataset d = sha256:b83c31be03e9ec1a05ed7a0e1491ad4c660992738a2c2d4c0d4d5d85e9ced8e3
claim tr(recording(bids(d), "01", "x", "1"))
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\10-sidecar-precedence.rl --files findings\10-m --root findings\10-ds
line 2: formed: RepetitionTime[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x acq a rec b run 1: #2], from #3] is recorded as 2 s (Recorded[s])
  #1 = sha256:b83c31be03e9ec1a05ed7a0e1491ad4c660992738a2c2d4c0d4d5d85e9ced8e3
  #2 = sha256:2332e1fb224ea541dcec22cd75345b9c9fb9b0f396c46a10cec5254eb5bbde6e
  #3 = sha256:b31421f10215b59c9aaea164ebec9cf1ec67b995c0892ff082f66d96d535f746
accepted
```

`#3` is the `acq-a_rec-b` file. Both values pass B09, because both round to the float32 2.0 that
the header holds.

## Demonstration (§5, items 1–2 and reading rules)

What 1.0.1 says (`context\sources\bids-1.0.1.txt`): §3.5, "The values from the top level are
inherited by all lower levels unless they are overridden by a file at the lower level" (an order
between levels only); §8.4, for the root `task-<label>_bold.json` against the subject file: "If
both files are specified the one corresponding to a particular participant, task and run takes
precedence." Two files in the same folder are not ordered by either sentence. The readings:

- v2's: the file with more entities wins, here `acq-a_rec-b` (4 entities) over `run-1` (3):
  **recorded as 2 s**;
- §8.4's sentence carried over to this case: the one that corresponds to the particular run wins:
  **recorded as 2.0000001 s**;
- the literal reading of 1.0.1: the standard gives no order, so no value.

Two readings that give different answers, or no reading at all; v2's answer is the reader author's
choice, which RULES-1.0.1.md states openly. That the choice is fixed before any claim satisfies
"No reading rule is chosen by a claim's author", but not "only as far as each standard defines
them". The same rule also hides conflicts: B15 fires only for equal rank, so the two files above
never conflict.

## Cause

`bids101._nested_meta` ranks applicable sidecars by `(depth, len(ents))` and lets the higher rank
overwrite (`bids101.py:175-191`).

## What would fix it

Order only what 1.0.1 orders (directory level; root versus subject-specific file). When two
applicable files of one level give one key different values, refuse (B15) whatever their entity
counts. With equal values the choice of "from #k" is harmless, and the sort could name both files.
