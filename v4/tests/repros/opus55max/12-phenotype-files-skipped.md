# 12. `phenotype/` files (BIDS 1.0.1 §8.11) are silently "extra", so a dataset that breaks §8.11 conforms

**Category:** hit (whole-dataset conformance, reading-rule clause), and a SPEC/code mismatch
(SPEC §1: unimplemented kinds "are refused as unimplemented (B14), never skipped").
**Spec clause:** §1 *whole-dataset conformance*; §10.2 C ("The reader must check every
machine-checkable 1.0.1 rule"); BIDS 1.0.1 §8.11.
**Severity:** medium. **Confidence:** high.

## Programs

`findings\12-phenotype-files-skipped.rl`, with the made-up dataset `findings\12-ds\` (manifest in
`findings\12-m\`): a conformant one-subject dataset plus

```
phenotype/bdi.tsv     score	who / 12	someone            (no participant_id column)
phenotype/bdi.json    {"score": {"Description": "x"}, "score": 1}   (a key twice)
```

```
dataset d = sha256:e28c89b30803c50bbfe2c6d6e8cc951949e6427bcdfdfe3256e2e9e8c6b788b6
claim count(participants(bids(d)))
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\12-phenotype-files-skipped.rl --files findings\12-m --root findings\12-ds
line 2: formed: Count[Participants[BIDS-1.0.1[#1] from #2]] = 1 (Exact)
  #1 = sha256:e28c89b30803c50bbfe2c6d6e8cc951949e6427bcdfdfe3256e2e9e8c6b788b6
  #2 = sha256:293eac506f0087701fbb7d96e686c1ce554da692f1c2632044080c81408203ff
accepted
```

## Demonstration (§5, reading rules)

BIDS 1.0.1 §8.11 lists `phenotype/<measurement_tool_name>.tsv` and `.json` in the participant
key file's template and says of them: "one of them has to be `participant_id` with matching
`sub-<participant_label>`" (`context\sources\bids-1.0.1.txt`, lines 1213–1240). The phenotype
table above has no `participant_id`, and its JSON has a duplicate key, which v2's own JSON reader
refuses everywhere else (J002, "two readings"). The dataset therefore does not conform to the
version it declares, yet a BIDS-sorted claim forms from it. That is the case the whole-dataset
rule exists to exclude.

## Cause

`classify` (`bids101.py:68-124`) knows the root files, `code/derivatives/stimuli/sourcedata`, and
`sub-*`; a top-level `phenotype/` folder falls to the final `return ("extra", None)`. So it is
neither checked nor refused as unimplemented (B14). RULES-1.0.1.md's list of unimplemented content
does not mention it.

## Related gaps (softer, so not counted as hits)

`findings\12-phenotype-files-skipped-b.rl` (dataset `findings\12-ds-b\`) also conforms although it
has an sbref sidecar with `"TaskName": "zzz", "RepetitionTime": -4` next to a BOLD of task `x`,
and fieldmap `magnitude1.json` / `magnitude2.json` with no fieldmap image at all:

```
line 2: formed: Count[Participants[BIDS-1.0.1[#1] from #2]] = 1 (Exact)
line 3: formed: RepetitionTime[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x: #2], from #3] is recorded as 2 s (Recorded[s])
accepted
```

1.0.1 states its required fields (RepetitionTime "the time in seconds between …", TaskName) for
the task imaging data and mentions sbref only as a variant, and its fieldmap case 1 template has
no magnitude sidecars, so these are arguable. But v2 is strict about the same things for BOLD
(B08 > 0, B09) and for `phasediff.json` (B12 requires its images), and lax next to them; see the
accuracy section of INDEX.md.

## What would fix it

Classify `phenotype/*.tsv|json` as defined files: parse them strictly and require a
`participant_id` column with `sub-<label>` values (and decide whether those labels must appear in
`participants.tsv`). Or refuse them with B14 until then. Apply B08's checks to every sidecar that
gives `RepetitionTime` or `TaskName`, not only to BOLD's.
