# 03. The manifest's sizes and its extra files' hashes are never checked; claims form on a manifest that misstates the files

- **Category:** hit (item 5 and the "false is not nonsense" clause: "a written value that differs from the file"; floor: the text names bytes that nobody supplied)
- **Spec clauses:** §1 *What counts as text*, item 5, *False is not nonsense*; SPEC §2 items 1 and 10
- **Severity:** medium. **Confidence:** medium on classification (it is a hit only because the manifest is part of the claim's text); high on reproduction.

## What happens

A BIDS claim names its dataset by the hash of a manifest, so the manifest's bytes are part of the
text (§1). Each manifest line states `sha256 TAB size TAB path`. The reader:

- never compares the stated size with the file (`bids101.py` reads `for p, (h, _), pn in entries`
  and ignores the size; `readers.parse_manifest` only checks the size's syntax);
- never reads or locates extra files (README: "never read or hash-checked"), so an extra file may be
  listed under a hash that no supplied file, and possibly no file at all, has.

## Reproduce

`03-false-sizes.manifest` is `01-subset.manifest` with `participants.tsv`'s size written as `1`
(the file has 3 002 bytes) and `KEYS.txt` listed with the hash `000…0` and size 7.

```
.venv\Scripts\python.exe -m reality2 check findings\03-manifest-sizes-and-extra-hashes-unchecked.rl --files findings\03-false-sizes.manifest tests\data\ds001734-box\participants.tsv --root tests\data\ds001734-box
```

Output (`03.out`):

```
line 5: formed: Count[Rows[Participants[BIDS-1.0.1[#1] from #2] where ExtraCell col 2 = "equalRange"]] = 54 (Exact)
  #1 = sha256:43b12e773af54bb0caa8cbf6cff2635e3732de36a6da095320c957aa2d8df092
  #2 = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
line 6: formed: ByteCount[#1] = 3002 (Exact)
  #1 = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
accepted
```

## Demonstration (§5)

*Item 5 / written value.* The formed claim on line 5 rests on manifest #1, and #1 states that
`sha256:d127d7…` is 1 byte long. Line 6 forms in the same program, from the same text, and says that
file is 3 002 bytes. One of the two values in the text is wrong, and the text alone shows which. §1
lists "a written value that differs from the file" as nonsense, never as false. Changing the stated
size to any other number keeps line 5 forming, so the size is an idle written value inside the
claim's text (item 1).

*Floor.* Dataset #1 includes a file `KEYS.txt` whose bytes nobody supplied. F001 ("a name that points
to bytes nobody supplied is refused") is enforced for every other name.

## Fix

Check every manifest entry: locate it and compare its hash and size, extra files included. Or drop
`size` from the format, and require every listed hash to be supplied. Once the manifest names the
dataset, everything it states is part of the claim.
