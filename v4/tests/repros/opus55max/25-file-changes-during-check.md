# 25. A file that changes after it was hashed: `bytes()` and `size()` form claims about other bytes

**Category:** bug (a wrong formed claim when a supplied file is modified during a check) and a
README overclaim.
**Spec clause:** README ("Bytes are the floor. … So is a file that changes while it is being read
(F002)"); §1 *Floor*; §5 floor ("a formed claim whose sentence or sort is not producible from its
named files").
**Severity:** low (needs another process to write the file during the check; on the PC, a download
that is still running is such a process). **Confidence:** high.

## Program

`findings\25-file-changes-during-check.rl`, which names `findings\25-before.tsv` (`id\nAAAA\n`),
run by `findings\25-file-changes-during-check.py`: the script supplies a copy of the file, lets the
store hash it (as `python -m reality2 check` does before it checks anything), then overwrites the
copy with `id\nBBBB\n` (the same length) and checks.

```
file f = sha256:dc708387663dc8dabdeb2d0088ef2567bc7a27bd35890bc821cc7768bcb3679e
claim bytes(f, 3, 4)
claim size(f)
claim cell(tsv(f), 1, 1)
```

## Command and output

```
> set PYTHONIOENCODING=utf-8
> python -I findings\25-file-changes-during-check.py
line 2: formed: Bytes[#1, 3..7] = "BBBB"
  #1 = sha256:dc708387663dc8dabdeb2d0088ef2567bc7a27bd35890bc821cc7768bcb3679e
line 3: formed: ByteCount[#1] = 8 (Exact)
  #1 = sha256:dc708387663dc8dabdeb2d0088ef2567bc7a27bd35890bc821cc7768bcb3679e
line 4: refused [F002, text]: sha256:dc708387663dc8dabdeb2d0088ef2567bc7a27bd35890bc821cc7768bcb3679e changed while it was being read
refused (1 statement)
```

Line 2 says that the file with hash `dc708387…` holds `BBBB` at bytes 3..7; that file holds `AAAA`
there. Only the whole-file read (line 4) notices.

## Cause

`Store.text` re-hashes what it reads (`readers.py:127`), but `c_bytes` opens the path and seeks
(`kernel.py:197-205`), `Store.size` calls `os.path.getsize` (`readers.py:141`), and
`nifti_read` streams the image from the path (`readers.py:314-337`); none compares the bytes it
uses with the hash. `size()` and the NIfTI header (for `volumes`, B05, B09) have the same gap.

## What would fix it

Read each file once into a verified buffer (for files up to the text bound), or hash while
streaming and compare at the end before any value from that read is used; for `bytes()`, hash the
whole file while reading the slice (it is bounded by `MAX_TEXT_FILE` anyway).
