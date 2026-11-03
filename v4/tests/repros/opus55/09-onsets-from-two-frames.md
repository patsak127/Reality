# 09. `difference()` subtracts onsets measured from two different reference events

- **Category:** hit (item 1: "a frame, a reference event … is missing, of the wrong sort, ambiguous"); v1 finding 22 (anchors) in another form
- **Spec clauses:** §1 item 1; §2 table (`EventOnset[recording, row]` "in seconds from the first volume of *that* recording"); §10.2 (i)
- **Severity:** medium-high (this is how event timing will be used once F9 exists). **Confidence:** medium-high.

## What happens

Under BIDS 1.0.1 §8.5 an onset is "measured from the beginning of the acquisition of the first volume
in the corresponding task imaging data file". v2 types it as `Num(q, q, "s", recorded=True)`
(`kernel.py:560`). The precision type carries the *unit* "s" and nothing else. `difference()`
checks only that the units are equal (`kernel.py:397`). So it subtracts:

- the onset of event 1 in sub-001 run 01 from the onset of event 1 in sub-002 run 01. These are two
  time points measured from two different reference events (two separate scans), so the difference
  is a number of seconds between nothing in particular;
- an onset (a time point) minus a repetition time (a duration of another recording);
- a duration of one recording minus an onset in another.

All three form, and comparisons on them form too.

## Reproduce

On the fabricated complete copy (`scratch/cmp`, built by `tests/bidsfix.complete_copy`; manifest
`09-fabricated-complete.manifest`, sha256 `67178ff6…`). Program `09-onsets-from-two-frames.rl`:

```
dataset d = sha256:67178ff61c675a0a1101689c4f16fe90ce26e891e03b9609b5a9db8b90f13a24
let b = bids(d)
let r1 = recording(b, "001", "MGT", "01")
let r2 = recording(b, "002", "MGT", "01")
claim difference(onset(r1, 1), onset(r2, 1)) is 0.02 s
claim exceeds(difference(onset(r1, 1), onset(r2, 1)), c = 0)
claim difference(onset(r1, 1), tr(r2))
claim exceeds(difference(duration(r1, 1), onset(r2, 1)), c = -1)
```

```
python -c "import sys; sys.path[:0]=['tests','src']; import bidsfix; bidsfix.complete_copy('scratch/cmp')"
.venv\Scripts\python.exe -m reality2 check findings\09-onsets-from-two-frames.rl --files findings\09-fabricated-complete.manifest --root scratch\cmp
```

Output (`09.out`, file lines omitted):

```
line 7: formed: Difference[EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 001 task MGT run 01: #2], #3 row 1], EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 002 task MGT run 01: #2], #4 row 1]] is recorded as 0.02 s (Recorded[s])
line 8: formed: Exceeds[Difference[EventOnset[… sub 001 …], EventOnset[… sub 002 …]], c = 0 s] holds of the recorded value
line 9: formed: Difference[EventOnset[… sub 001 …], RepetitionTime[… sub 002 …, from #4]] is recorded as 3.071 s (Recorded[s])
line 10: formed: Exceeds[Difference[EventDuration[… sub 001 …], EventOnset[… sub 002 …]], c = -1 s] holds of the recorded value
accepted
```

(In the fabricated copy every BOLD file has the same bytes, so both recordings print `#2`. With the
real data they differ. The same thing shows a second weakness: "seconds after the first volume of
#2" does not identify a reference event when two recordings have equal bytes.)

## Demonstration (§5)

*Item 1, the missing or ambiguous part.* Line 7's value is "seconds", but seconds after what? The two
operands are measured from different reference events, and no byte relates the two scans' start
times (1.0.1's `acq_time` lives in scans files, which v2 refuses with B14). The sort prints both
recordings, so the reader can *see* that the frames differ. But the language forms the subtraction
as if they were one frame, and the comparison on line 8 asserts an order between two events in
different frames.

## Fix

Make the reference event part of the precision type: `Recorded[s from BOLDRecording r]` for onsets,
and `Recorded[s]` (a duration, no frame) for durations and TR. Allow time point − time point only
within one frame (it gives a duration), time point ± duration within one frame, and duration ±
duration. Refuse everything else with U001.
