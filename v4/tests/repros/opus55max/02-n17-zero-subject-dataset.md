# 02. N17 forms from the box copy's own bytes, through a manifest with no subject in it

**Category:** hit (must-not-form N17; whole-dataset conformance in the reading-rule clause).
**Spec clause:** §1 *Reading rules: whole-dataset conformance*; §5 must-not-form N17; §1 *False is
not nonsense* (why the fabrication defence does not apply); BIDS 1.0.1 §3.2 item 1.
**Severity:** high. **Confidence:** high that it forms; medium-high that it counts as a hit (the
counter-argument is given below).

## Program

`findings\02-n17-zero-subject-dataset.rl`. The dataset is named by the manifest
`findings\02-m\d314232b….manifest`, which lists the box copy's eight root files with their real
hashes, sizes and paths, and nothing else. Every byte the checker reads comes from
`tests\data\ds001734-box\` unchanged; no file was made up and no path was invented.

```
# The manifest lists the box copy's 8 root files, byte for byte, and nothing under sub-*/.
dataset d = sha256:d314232b0eefaa20f66920acac339d3d06008b435fd0ac82bc044ffc1285a8a7
let b = bids(d)
claim count(where(participants(b), eq("group", "equalRange"))) is 54
claim share(where(participants(b), eq("group", "equalRange"))) is 54/108
claim count(where(participants(b), eq("gender", "F"))) is 60
```

The manifest (complete):

```
reality-manifest 1
362a1f07…	321	CHANGES
19a779b1…	99899	KEYS.txt
0193d7fc…	904	README
361e839c…	169	T1w.json
d5e0ecdf…	1277	dataset_description.json
d127d700…	3002	participants.tsv
c5a77954…	1171	task-MGT_bold.json
7260085b…	223	task-MGT_sbref.json
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\02-n17-zero-subject-dataset.rl --files findings\02-m --root tests\data\ds001734-box
line 4: formed: Count[Rows[Participants[BIDS-1.0.1[#1] from #2] where ExtraCell col 2 = "equalRange"]] = 54 (Exact)
  #1 = sha256:d314232b0eefaa20f66920acac339d3d06008b435fd0ac82bc044ffc1285a8a7
  #2 = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
line 5: formed: Share[Rows[Participants[BIDS-1.0.1[#1] from #2] where ExtraCell col 2 = "equalRange"] of Participants[BIDS-1.0.1[#1] from #2]] = 54/108 (Exact)
  #1 = sha256:d314232b0eefaa20f66920acac339d3d06008b435fd0ac82bc044ffc1285a8a7
  #2 = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
line 6: formed: Count[Rows[Participants[BIDS-1.0.1[#1] from #2] where ExtraCell col 3 = "F"]] = 60 (Exact)
  #1 = sha256:d314232b0eefaa20f66920acac339d3d06008b435fd0ac82bc044ffc1285a8a7
  #2 = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
accepted
```

For comparison, the same claim on the box copy's full manifest (`findings\02-n17-box.rl`, the N17
case of the acceptance table) is refused with `B00 … (648 failures) … B07 x432 … B12 x216`.
The printed lines are character for character those of F1, F2 and N14b on the fabricated complete
copy, except for the manifest hash.

## Demonstration (§5)

- **Must-not-form:** N17 is F1's text "on the box copy", and the spec says it must not form
  because the box copy has no imaging files. Here F1's text, F2's and N14b's form, as BIDS-sorted
  claims (`Participants[BIDS-1.0.1[...]]`, `ExtraCell`), from nothing but the box copy's bytes.
- **The defect is visible in the text alone**, so it is not "false": the text the claims name is a
  "BIDS 1.0.1 dataset" whose manifest lists no `sub-*` path at all, and whose `participants.tsv`
  describes 108 participants of whom none has a single file in the dataset. BIDS 1.0.1 §3.2 item 1
  (`context\sources\bids-1.0.1.txt`, lines 179–180) defines a dataset as one that "consists of data
  acquired from one or more subjects". The checker can see that this one has none; it reads the
  dataset as conformant.
- **Not fabrication either.** §1's fabrication case is "a dataset built in a standard's form in
  order to make a claim form", whose author "chose content". Here no content was chosen: every
  file and every path is the box copy's. What was chosen is *which of the box copy's files the
  standard's reader is allowed to see*. That is the scope of the conformance check, not content.
  (See finding 05 for the general question of manifest selection, which this case answers in the
  strongest form.)

## Why it happens

- `bids101.read` never requires a subject. `subjects` may be empty (`bids101.py:247`), and every
  per-subject rule then has nothing to check.
- B11 is one-sided: every subject folder needs a `participants.tsv` row, but rows without a folder
  are allowed (SPEC §2 item 9, `bids101.py:381-383`). So a manifest that drops every `sub-*` file
  removes every failing file (432 B07 and 216 B12) and leaves a conformant "dataset" behind.

## What would fix it

Refuse a BIDS dataset that has no subject folder (§3.2), and make B11 symmetric: a
`participants.tsv` row without a subject folder is a failure. With both, no selection of the box
copy's genuine files at their genuine paths conforms; forming N17's text then needs invented paths
or bytes, which is content, the false side of §1.

## Counter-argument, and why I don't accept it

"The claim names #1, a different dataset from the box copy, so N17 (about the box copy) is not
what formed." But N17 exists to say that nothing BIDS-based forms from the box copy's bytes until
the imaging files exist; a manifest is how v2 lets the author say which of those bytes are "the
dataset". If the author can make the failing files disappear by leaving them out, whole-dataset
conformance protects nothing that it was adopted to protect. The review brief (a) asks for "any
must-not-form text from §5 that forms in some spelling", and §5 itself counts "any text from the
list below that forms"; a different manifest over the same bytes is such a spelling.
