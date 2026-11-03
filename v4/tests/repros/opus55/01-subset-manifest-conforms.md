# 01. A manifest that leaves out the subject folders makes the box copy conform: N17's text forms

- **Category:** hit (must-not-form N17 in another spelling; reading-rule clause, whole-dataset conformance)
- **Spec clauses:** §1 *Reading rules*, "Whole-dataset conformance" (amendment 14:13); §5 N17; §1 item 5 ("a decision … chosen by the author"); SPEC §2 item 1 **[call]**
- **Severity:** high. **Confidence:** high that it reproduces; medium-high that it is a hit rather than "fabrication" (argued below).

## What happens

The box copy of ds001734 does not conform (432 events files have no BOLD file), so N17 requires that
F1's text not form from it. The dataset that `bids()` checks is whatever the author's manifest lists.
I took the box copy's own manifest (`python -m reality2 manifest`) and deleted every line whose path
starts with `sub-`. No byte of any data file was changed or made up. The remaining 8 files are the
genuine root files of ds001734 (`dataset_description.json`, `participants.tsv`, `task-MGT_bold.json`,
…). With no subject folders there are no events files, so there is nothing for B07 or B12 to fail on;
B11 accepts the 108 participants rows because "participants rows without a folder are allowed"
(SPEC §2 item 9). The dataset "conforms", and F1, F2 and "108 participants" form.

## Reproduce

Files: `01-box.manifest` (the full box-copy manifest, sha256 `b6850de7…`), `01-subset.manifest`
(the same with the `sub-*` lines removed, sha256 `d314232b…`). Program: `01-subset-manifest-conforms.rl`.

```
set PYTHONPATH=src
.venv\Scripts\python.exe -m reality2 check findings\01-subset-manifest-conforms.rl --files findings\01-subset.manifest findings\01-box.manifest --root tests\data\ds001734-box
```

Output (`01.out`, long line cut):

```
line 5: refused [B00, reading rules]: the dataset does not conform to BIDS 1.0.1 (648 failures), ... B07 x432, ...
line 6: formed: Count[Rows[Participants[BIDS-1.0.1[#1] from #2] where ExtraCell col 2 = "equalRange"]] = 54 (Exact)
  #1 = sha256:d314232b0eefaa20f66920acac339d3d06008b435fd0ac82bc044ffc1285a8a7
  #2 = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
line 7: formed: Share[Rows[Participants[BIDS-1.0.1[#1] from #2] where ExtraCell col 2 = "equalRange"] of Participants[BIDS-1.0.1[#1] from #2]] = 54/108 (Exact)
line 8: formed: Count[Participants[BIDS-1.0.1[#1] from #2]] = 108 (Exact)
refused (1 statement)
```

## Demonstration (§5)

*Must-not-form / reading rules.* Same bytes, same reader, same claim text; only the author-made
list of which files "are the dataset" differs. Line 5 (all files listed) is refused B00; line 6
(subject folders left out) forms. The selection is a choice of *what the standard's conformance check
gets to see*, made by the author for this claim. That is a reading chosen by the author, not content
chosen by the author.

## Why "fabrication" is not a defence here

§1 calls fabrication false because "its author chose content, not reading" and because "no checker
that sees only text can detect this". Neither holds:

- No content was chosen. Every byte listed is the published ds001734 byte. What was chosen is the
  scope, and the manifest is the only author-written file that the language reads as *structure*.
- The defect is visible from the text alone. The text contains `participants.tsv`, which lists 108
  `sub-<label>` participants, and a manifest with zero `sub-*` folders. BIDS 1.0.1 §8.11 says
  participants.tsv describes the participants of the dataset ("Each participant needs to be
  described by one and only one row"). A dataset in which 108 described participants have no data
  is something the text shows by itself.

## What would settle it

1. Refuse participants rows that have no subject folder (make the B11 rule two-way). After that,
   leaving out a subject means editing `participants.tsv`, which is a change of content (real
   fabrication) and gives a hash different from the published file.
2. Print the scope in every BIDS sort, for example `BIDS-1.0.1[#1: 108 subjects, 432 BOLD
   recordings, 1 845 files]`. On its own this only makes the selection visible; together with (1)
   it closes the silent case. Printing just the number of subjects would not have caught this case,
   because the participant count (108) is the same either way.
3. Any future aggregate over recordings (F9's GLM) must range over all recordings in the manifest
   and print how many there are. Otherwise dropping one run is the same selection again.
