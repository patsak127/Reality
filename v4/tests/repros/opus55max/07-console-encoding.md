# 07. The console encoding decides the output: a crash that hides formed claims

**Category:** hit (item 4: "the locale"). Also a bug (uncaught traceback), and the reason the
suite's own `test_01_hash_seed_does_not_change_output` fails on this machine.
**Spec clause:** §1 item 4; README "Output never depends on …" (the harness claim "all four
machines … must be GREEN").
**Severity:** medium. **Confidence:** high.

## Program

`findings\07-console-encoding.rl`, with the made-up dataset `findings\07-ds\` (manifest in
`findings\07-m\`) whose `participants.tsv` has the non-conformant id `sub-Ω01`:

```
dataset d = sha256:44b827350d03ab6850139ea3146391e51510b4d7d0101a1d3e50cc3df8013931
file p = sha256:86a7aa3955685fea8afcae139e1ceff468b6eaf5747e5dc86e7f44513bbeb31b
claim count(participants(bids(d)))
claim rows(tsv(p))
```

## Commands and output (stdout redirected to a file or pipe, as harnesses and scripts do)

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\07-console-encoding.rl --files findings\07-m --root findings\07-ds > out.txt
line 3: refused [B00, reading rules]: the dataset does not conform to BIDS 1.0.1 (1 failures), so nothing BIDS-based forms from it (principle §1, whole-dataset conformance). B11 x1, first: participants.tsv row 1: participant_id 'sub-Ω01' is not sub-<label> (§5, §8.11)
line 4: formed: RowCount[TSV[#1]] = 1 (Exact)
  #1 = sha256:86a7aa3955685fea8afcae139e1ceff468b6eaf5747e5dc86e7f44513bbeb31b
refused (1 statement)

> set PYTHONIOENCODING=
> python -m reality2 check findings\07-console-encoding.rl --files findings\07-m --root findings\07-ds > out.txt
Traceback (most recent call last):
  ...
  File "...\src\reality2\__main__.py", line 54, in main
    print(line)
  File "...\Lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
UnicodeEncodeError: 'charmap' codec can't encode character 'Ω' in position 233: character maps to <undefined>
```

In the second run line 4's formed claim is never written. With an ASCII stdout
(`PYTHONIOENCODING=ascii`, the portable way to show it on the Linux box) any refusal message
crashes the printer, because almost every message contains `§`:
`claim significant(x)` alone gives `UnicodeEncodeError: 'ascii' codec can't encode character
'\xa7'`.

Even without a crash the bytes differ: in a cp1252 run `§` is written as the byte 0xA7, in a UTF-8
run as 0xC2 0xA7. That is why `tests\test_findings.py::test_01_hash_seed_does_not_change_output`
fails here (Windows 11, Python 3.14.7): it decodes the subprocess output as UTF-8 and meets 0xA7
("1 failed, 186 passed").

## Demonstration (§5, item 4)

Two runs that differ only in the output encoding (the locale's code page, or `PYTHONIOENCODING`)
give different output: a refusal plus a formed claim, or a traceback and no formed claim.

## Cause

`__main__.main` prints each line with the console's encoding (`__main__.py:53-54`). Messages carry
`§` (55 places in the five modules) and quote data through `repr()` (`bids101.py:376` for
`participant_id`, J002's key, B08's `TaskName`, and the `errors="replace"` decoding in
`kernel.py:505`, which can put U+FFFD into a K001 message).

## What would fix it

Write the output as UTF-8 bytes (`sys.stdout.buffer.write(line.encode("utf-8") + b"\n")`), or keep
every message ASCII, and escape data in messages with `esc()` as the formed lines already do.
