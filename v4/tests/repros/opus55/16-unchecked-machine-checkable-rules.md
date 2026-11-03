# 16. Machine-checkable 1.0.1 links go unchecked; the fabricated copy contradicts itself and still forms F3/F8/F11

- **Category:** judgement call / design issue (questions c and e). Not counted as a hit (1.0.1 does not state these as rules in so many words).
- **Spec clauses:** §10.2 C ("The reader must check every machine-checkable 1.0.1 rule"); §1 *False is not nonsense*; BIDS 1.0.1 §8.9 (IntendedFor), §8.4 (SliceTiming), §8.5 (onsets relative to the first volume)
- **Severity:** medium. **Confidence:** high on behaviour, medium on classification.

## What happens

The reader checks some cross-file consistency rules (B09, TR against `pixdim[4]`; B10,
SliceEncodingDirection against `slice_dim`) and skips others that are just as machine-checkable:

- **IntendedFor** (§8.9) holds paths, relative to the subject folder, of the images a fieldmap is
  for. A dangling path is not checked.
- **SliceTiming** (§8.4) is "a list of times … for each slice … along the slice axis", so its length
  is the number of slices. ds001734's root sidecar has 64 entries. The fabricated images have 2 slices.
- **Events within the recording.** Onsets are seconds from the first volume, and the recording lasts
  `dim[4] × TR`. The fabricated BOLD files last 3 s, and run 01's events run to 441 s.

## Reproduce

`16-dangling-intendedfor.manifest` is the fabricated complete copy's manifest with sub-001 run-04
(BOLD, sbref, events) removed. `sub-001_phasediff.json` still says
`"IntendedFor": [… "func/sub-001_task-MGT_run-04_bold.nii.gz"]`.

```
.venv\Scripts\python.exe -m reality2 check findings\16-unchecked-machine-checkable-rules.rl --files findings\16-dangling-intendedfor.manifest --root scratch\cmp
```

Output (`16.out`, file lines omitted):

```
line 7: formed: VolumeCount[BOLDRecording[BIDS-1.0.1[#1], sub 001 task MGT run 01: #2]] = 3 (Exact)
line 8: formed: RepetitionTime[BOLDRecording[BIDS-1.0.1[#1], sub 001 task MGT run 01: #2], from #3] is recorded as 1 s (Recorded[s])
line 9: formed: EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 001 task MGT run 01: #2], #3 row 1] is recorded as 4.071 s (Recorded[s])
line 10: formed: EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 001 task MGT run 01: #2], #3 row 64] is recorded as 441.024 s (Recorded[s])
line 11: refused [V004, item 2]: recording(): 0 BOLD recordings in the dataset match sub-001 task-MGT run-04 ...
```

## Why this matters for (c), false versus nonsense

README and SPEC call the fabricated copy "fabricated", so its claims are "false, not nonsense". But
lines 7, 8 and 10 are three formed claims about one named BOLD file. Together they say that the
recording has 3 volumes 1 s apart, and that an event happened 441 s after its first volume. A text
that contains a fieldmap pointing at a missing image, 64 slice times for 2 slices, and events
hundreds of seconds past the end of the scan shows its own inconsistency. Under §1 ("anything that
can be shown wrong … from the text alone is nonsense if it forms") the fabrication defence does not
apply. The checker could see it, and doesn't look.

## Recommendation

Check IntendedFor targets, SliceTiming length (and each value < TR), and `onset ≤ dim[4] × TR`. Or
publish, in `bids/RULES-1.0.1.md`, a reason for each 1.0.1 sentence that is not checked, as §10.2 D
requires. The current list covers only the sections whose files appear in ds001734, and IntendedFor
is in one of those sections.
