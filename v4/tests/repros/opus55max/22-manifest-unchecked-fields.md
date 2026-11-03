# 22. The dataset's name carries written values nobody checks: sizes, and entries without bytes

**Category:** hit (§1 *False is not nonsense*: "a written value that differs from the file" is
nonsense if it forms), at the low end; the most contestable hit of this review, see below.
**Spec clause:** §1 *Floor* ("The bytes are always the floor"); README ("A manifest lists `hash,
size, path` for every file"); SPEC §2 items 10 and 11 ("the claim still names the whole set it was
checked against").
**Severity:** low. **Confidence:** high that it forms; medium on the classification.

## Program

`findings\22-manifest-unchecked-fields.rl`, with the made-up dataset `findings\22-ds\` and the
hand-edited manifest in `findings\22-m\`:

```
reality-manifest 1
57a5483d…	1	dataset_description.json
00000000…0000	999999999	notes/never-supplied.txt
293eac50…	1	participants.tsv
2332e1fb…	1	sub-01/func/sub-01_task-x_bold.nii
ffcf3a72…	1	sub-01/func/sub-01_task-x_events.tsv
5a7c297e…	1	task-x_bold.json
```

Every size is false (the BOLD file is 392 bytes, for example), and the second line names a file
whose bytes exist nowhere (hash 0…0, 999,999,999 bytes); the folder `findings\22-ds\` does not
contain it.

```
dataset d = sha256:7e109487442ec0fcb8397e5edcfddd02f07b08599b08f9b96bb416195bd2b1d8
let b = bids(d)
claim count(participants(b))
claim volumes(recording(b, "01", "x"))
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\22-manifest-unchecked-fields.rl --files findings\22-m --root findings\22-ds
line 3: formed: Count[Participants[BIDS-1.0.1[#1] from #2]] = 1 (Exact)
  #1 = sha256:7e109487442ec0fcb8397e5edcfddd02f07b08599b08f9b96bb416195bd2b1d8
  #2 = sha256:293eac506f0087701fbb7d96e686c1ce554da692f1c2632044080c81408203ff
line 4: formed: VolumeCount[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x: #2]] = 5 (Exact)
  #1 = sha256:7e109487442ec0fcb8397e5edcfddd02f07b08599b08f9b96bb416195bd2b1d8
  #2 = sha256:2332e1fb224ea541dcec22cd75345b9c9fb9b0f396c46a10cec5254eb5bbde6e
accepted
```

## Demonstration and classification

Both claims name `#1`, the manifest, as their dataset, and SPEC §2 item 11 defends the gate/value
split with "the dataset's manifest hash is in every BIDS sort, so the claim still names the whole
set it was checked against". But this set was not checked: six of its sizes are false and one
entry has no bytes, and all of that is visible from the text alone (the supplied bytes have other
sizes; the hash `0…0` has no bytes). The manifest is Reality's own format, read by Reality's fixed
manifest reader, and it is the dataset's name in the claim's form. A name that misstates the bytes
it names, accepted by the language's own reader, is "a written value that differs from the file".

The counter-argument is that no value of either claim depends on the sizes or on the phantom entry,
so the claims are exactly right about the files they read. If the author takes that view, this is a
design issue rather than a hit; the fix is the same, and it matters for finding 05: an unchecked
manifest is what lets the author decide what "the whole dataset" contains.

## Cause

`parse_manifest` stores the size (`readers.py:377`) and nothing compares it with a file; extra
files are "never read or hash-checked" (SPEC §2 item 10, RULES-1.0.1.md).

## What would fix it

Verify each entry's size when its bytes are located, and require every entry, extra files included,
to be supplied and hash-checked before any BIDS sort forms; or drop the size field.
