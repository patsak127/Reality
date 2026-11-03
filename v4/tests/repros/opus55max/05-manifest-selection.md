# 05. The author's manifest decides which subjects and runs "the whole dataset" has

**Category:** judgement call (SPEC §2 item 1), with a design issue in the spec's notion of
fabrication. The strongest instance, a manifest with no subjects at all, is a hit (finding 02).
**Spec clause:** §1 *whole-dataset conformance*, *False is not nonsense* (fabrication), item 5
("identity … chosen by the author"), *Reading rules* ("No reading rule is chosen by a claim's
author"); SPEC §2 items 1, 9 ("participants rows without a folder are allowed") and 11.
**Severity:** high (it decides what whole-dataset conformance means). **Confidence:** high on the
facts; the classification is my judgement, argued below.

## Program

`findings\05-manifest-selection.rl`, with the made-up dataset `findings\05-ds\` (two subjects,
two BOLD runs each with events, a fieldmap whose `IntendedFor` names both runs) and three
manifests in `findings\05-m\`: the full listing, the listing without `sub-02/`, and the listing
without sub-01's run 2 (BOLD and events). No byte of any listed file differs between them.

```
dataset full = sha256:15c7cce9f71a20580532aa22e34d0104d75c21962b3a5c5ec16cb5faccd69313
dataset nosub02 = sha256:14f2238b6e98e0d88f74d9880122ac0eba3d83e6771a397f54ea5c733cd1b512
dataset norun2 = sha256:6c5364c529fa7ce7a05020aced8ac6a272556b9beed804627a8fbc64c509c34b
claim count(participants(bids(full)))
# sub-02's folder (4 images, 2 events files, a sidecar) left out; its row is still there
claim count(participants(bids(nosub02)))
claim extra(participant(bids(nosub02), "02"), "group")
# sub-01 run 2 (BOLD and events) left out, though sub-01's phasediff.json IntendedFor names it
claim volumes(recording(bids(norun2), "01", "x", "1"))
claim volumes(recording(bids(norun2), "01", "x", "2"))
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\05-manifest-selection.rl --files findings\05-m --root findings\05-ds
line 4: formed: Count[Participants[BIDS-1.0.1[#1] from #2]] = 2 (Exact)
  #1 = sha256:15c7cce9f71a20580532aa22e34d0104d75c21962b3a5c5ec16cb5faccd69313
  #2 = sha256:6a422c2c4a2365bee24047b85c04503fca0dffcf7eda34d706e31fc704e6971c
line 6: formed: Count[Participants[BIDS-1.0.1[#1] from #2]] = 2 (Exact)
  #1 = sha256:14f2238b6e98e0d88f74d9880122ac0eba3d83e6771a397f54ea5c733cd1b512
  #2 = sha256:6a422c2c4a2365bee24047b85c04503fca0dffcf7eda34d706e31fc704e6971c
line 7: formed: ExtraCell[Participant[Participants[BIDS-1.0.1[#1] from #2], sub-02], col 2] = "b"
  #1 = sha256:14f2238b6e98e0d88f74d9880122ac0eba3d83e6771a397f54ea5c733cd1b512
  #2 = sha256:6a422c2c4a2365bee24047b85c04503fca0dffcf7eda34d706e31fc704e6971c
line 9: formed: VolumeCount[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x run 1: #2]] = 6 (Exact)
  #1 = sha256:6c5364c529fa7ce7a05020aced8ac6a272556b9beed804627a8fbc64c509c34b
  #2 = sha256:6ca4c457ee33ce2cbd26a094bbe63a160c1ec34b39c6b727fadda19301152691
line 10: refused [V004, item 2]: recording(): 0 BOLD recordings in the dataset match sub-01 task-x run-2 (a recording with run labels needs the run; one without needs none); exactly one is needed
refused (1 statement)
```

All three listings conform. In `nosub02`, sub-02 is a BIDS `Participant` (line 7) with no data in
the dataset. In `norun2`, sub-01's own `phasediff.json` says the run exists, and the dataset is
still "whole".

## The question (review brief (d)) and my answer

**Is leaving files out "fabrication" (false) or an author-chosen selection of what a claim sees
(nonsense)?** It depends on whether the result is something the declared standard allows and the
text cannot tell apart from a real dataset.

1. **By the letter of §1, a manifest is content.** It is a file, named by hash, and the claim
   prints its hash, so the claim says exactly which files it saw. §1 calls "a dataset built in a
   standard's form in order to make a claim form" fabrication, and fabrication is false, not
   nonsense. If the subset is a BIDS 1.0.1 dataset that could exist (a study that released fewer
   subjects or runs), nothing in the text can show it was cut, so it is false at worst.
2. **But the defence requires that the defect "can be seen only against the world".** Several
   selections leave visible traces that v2 does not read:
   - no subject at all (finding 02, a hit: BIDS 1.0.1 §3.2 says a dataset has one or more subjects);
   - `participants.tsv` rows for subjects with no folder (`nosub02`): 1.0.1 §8.11 says the file
     "describe[s] properties of participants" and "each participant needs to be described by one
     and only one row"; it does not say a row needs data, so this one is arguable, and v2 decided
     it in the permissive direction ([call] in SPEC §2 item 9);
   - `IntendedFor` naming a BOLD file that is not in the dataset (`norun2`): 1.0.1 §8.9 defines the
     field as paths to the scans the fieldmap was acquired for; v2 never reads it;
   - extra files that list the missing data (the box copy's own `KEYS.txt` lists all 1,836
     per-subject files), and manifest entries whose bytes were never checked (finding 22).
   Where the text shows the cut, forming is nonsense under §1 ("Anything that can be shown wrong,
   ambiguous or undetermined from the text alone is nonsense if it forms").
3. **The deeper issue is in the spec, not the code.** Whole-dataset conformance means "the files
   the author listed conform together". The spec presents it as a property of *the dataset*
   (ds001734), but Reality has no name for ds001734 other than a manifest the author writes. So the
   "whole" is chosen by the claim's author, for that claim, which is what the reading-rule clause
   forbids for readings. The fabrication clause then has to absorb every omission, and it can,
   because it is worded as "built in a standard's form in order to make a claim form": any manifest
   that makes a claim form qualifies. That makes "false" a catch-all for selection.

**Would printing the number of subjects settle it?** No. A printed count (or file count) is a
label: it makes the selection visible to a careful reader, but the claim still forms, and §5 says
"labelled" is not a defence. It would help with honesty of output, not with formability.

**What I would decide instead:**
- Make the text-visible cuts unformable: refuse a dataset with no subject (finding 02); make B11
  symmetric (a row needs its subject folder); treat an `IntendedFor` path that the manifest does
  not list as a failure. After that, removing a subject means changing `participants.tsv`'s bytes
  and removing a run means changing a sidecar's bytes: genuine content fabrication, on the false
  side, as §1 intends.
- Make the manifest entirely bytes: verify every entry's size and require every listed file,
  extra files included, to be supplied and hash-checked (finding 22), so "the claim names the whole
  set it was checked against" (SPEC §2 item 11) becomes true.
- Say plainly in README and SPEC what remains: Reality cannot know a dataset's published extent;
  a BIDS claim is about the listed set; omissions that leave no trace in the listed bytes are
  fabrication by definition. If a standard listing exists for a dataset (for OpenNeuro, the
  snapshot's file list), offer a form that names the dataset by that listing instead of by the
  author's manifest; that would turn "the whole dataset" into something no claim's author chooses.
