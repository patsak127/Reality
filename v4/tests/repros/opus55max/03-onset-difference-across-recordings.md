# 03. `difference` subtracts onsets measured from different reference events

**Category:** hit (item 1: a part the claim needs, a common reference event, is missing; the
operands are of the wrong sort for a difference).
**Spec clause:** §1 item 1 ("a frame, a reference event … missing, of the wrong sort"); §2 table
("`EventOnset[recording, row]` in seconds from the first volume of *that* recording"); BIDS 1.0.1
§8.5 ("Timing should be measured from the beginning of the acquisition of the first volume in the
corresponding task imaging data file").
**Severity:** high. **Confidence:** high that it forms; high that it is nonsense by item 1.

## Program

`findings\03-onset-difference-across-recordings.rl`, with the made-up dataset `findings\03-ds\`
(manifest in `findings\03-m\`): two subjects, one BOLD run each, `RepetitionTime` 2 s. sub-01's
events have onsets 1.5 and 9.25, sub-02's 7.25.

```
dataset d = sha256:69afb96445b1476693779165a85d7dc414bb894deb7595291da441813c7a1188
let b = bids(d)
let r1 = recording(b, "01", "x")
let r2 = recording(b, "02", "x")
# onsets are seconds from the first volume of *their own* recording (two different events)
claim difference(onset(r2, 1), onset(r1, 1))
claim exceeds(difference(onset(r2, 1), onset(r1, 1)), c = 5)
# a duration minus a time point
claim difference(tr(r1), onset(r1, 1))
# for contrast, a meaningful one: two events of one recording
claim difference(onset(r1, 2), onset(r1, 1))
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\03-onset-difference-across-recordings.rl --files findings\03-m --root findings\03-ds
line 6: formed: Difference[EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 02 task x: #2], #3 row 1], EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x: #4], #5 row 1]] is recorded as 5.75 s (Recorded[s])
  #1 = sha256:69afb96445b1476693779165a85d7dc414bb894deb7595291da441813c7a1188
  #2 = sha256:6ca4c457ee33ce2cbd26a094bbe63a160c1ec34b39c6b727fadda19301152691
  #3 = sha256:b04ccf4072aa7ead718dd5377e1994d438c4a9f78d12b9a6c1a229614d7acb97
  #4 = sha256:2332e1fb224ea541dcec22cd75345b9c9fb9b0f396c46a10cec5254eb5bbde6e
  #5 = sha256:275f55117f8267ee63bdd8d01a544fe7a39b827ef185b6f1f37bd7d36c2c7f7c
line 7: formed: Exceeds[Difference[EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 02 task x: #2], #3 row 1], EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x: #4], #5 row 1]], c = 5 s] holds of the recorded value
  (same five files)
line 9: formed: Difference[RepetitionTime[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x: #2], from #3], EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x: #2], #4 row 1]] is recorded as 0.5 s (Recorded[s])
  ...
line 11: formed: Difference[EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x: #2], #3 row 2], EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x: #2], #3 row 1]] is recorded as 7.75 s (Recorded[s])
  ...
accepted
```

Full output: `findings\03-output.txt`. The same forms on the fabricated complete copy of ds001734
(for example `difference(onset(recording(b, "001", "MGT", "01"), 1), onset(recording(b, "002",
"MGT", "01"), 1))` "is recorded as 0.02 s").

## Demonstration (§5, items 1–2: the missing part)

An `EventOnset` is a time coordinate whose origin is the start of *its own* BOLD acquisition; the
spec put the recording into the sort for exactly this reason. Lines 6 and 7 subtract coordinates
with two different origins (two acquisitions, of two different people, at unknown times). The
missing part is the common reference event. Without it, "5.75 s" is not the time between any two
events, and line 7, "the difference exceeds 5 s", reads as "sub-02's first event came more than
5 s after sub-01's", which nothing in the text fixes; with the two origins related differently,
the true difference could have any value. Line 9 subtracts a time point from a duration (the TR),
which is a second missing-sort case: it is not a time of anything.
Line 11 is the meaningful case, two events of one recording, and should keep forming.

## Cause

`c_difference` (`kernel.py:391-399`) checks only that both operands carry the same unit string
(`if x.unit != y.unit`). The reference event is in the sort text but not in the value's type, so
nothing compares it. `compare` (exceeds/below) then accepts the result as an ordinary number of
seconds.

## What would fix it

Type time values affinely: an `EventOnset` is a point with an origin (its BOLD file); the
difference of two points with the same origin is a duration; points with different origins have
no difference; a duration and a point can be added but not subtracted in that order. This is the
frame machinery v1 had, reduced to what BIDS 1.0.1 defines (one origin per recording).
