# 06. The machine's memory decides the verdict, inside the language's own bounds

**Category:** hit (item 4: "the checker's memory or speed"; §5 "a time or memory limit that
depends on the machine"). v1 finding 12 returns: the bound is on bytes read, not on memory.
**Spec clause:** §1 item 4; SPEC §2 item 12 ("They are the same constants on every machine, so
verdicts don't depend on the machine"); SPEC §5 row 12 ("fixed: bytes read are bounded").
**Severity:** medium (real machines differ only for inputs of tens to hundreds of MB, which the
bounds allow). **Confidence:** high.

## Program

`findings\06-memory-decides-verdict.rl`, with `findings\06-wide.tsv` (1.0 MB: 1,000 columns,
330 rows of the cell `12`):

```
# a 1 MB TSV; the reader's bounds allow 64 MB per file and 512 MB per check
file f = sha256:a8946905fe99b45f7b0db2c115baee2470ec2c2f6c6121a9712ce489668edf3b
claim rows(tsv(f))
```

## Commands and output

The second run gives the process 30 MB to commit, using a Windows Job Object
(`scratch\runlimit.py --memcap 30`); that is what a machine with less memory to give does.

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\06-memory-decides-verdict.rl --files findings\06-wide.tsv
line 3: formed: RowCount[TSV[#1]] = 330 (Exact)
  #1 = sha256:a8946905fe99b45f7b0db2c115baee2470ec2c2f6c6121a9712ce489668edf3b
accepted
[exit code 0; wall 0.1 s; peak private memory 32 MB]

> python -I scratch\runlimit.py --memcap 30 -- check findings\06-memory-decides-verdict.rl --files findings\06-wide.tsv
line 3: refused [X001, bug]: internal error MemoryError; nothing formed (please report)
refused (1 statement)
[exit code 1; wall 0.1 s; peak private memory 30 MB]
```

On Linux the same is `prlimit --as=...` or `ulimit -v` before the command.

## Demonstration (§5, item 4)

Two runs, one outside factor (memory available to the process), two verdicts: formed and
accepted, or refused (X001) and exit 1. The file is 1/64 of the per-file bound. Measured cost: the
1.0 MB table takes about 20 MB above the interpreter's 12 MB baseline, about 20 bytes of memory per
byte of file. At the language's own limits, `MAX_TEXT_FILE` = 64 MB needs about 1.3 GB and
`MAX_TEXT_TOTAL` = 512 MB (kept alive together, because `Checker.tables` and the store's text cache
keep every table) needs about 10 GB, so the same program and files form on a 16 GB machine and are
refused on an 8 GB one. A `MemoryError` outside the per-statement `try` (for example in
`kernel.check`'s sort rendering, `kernel.py:710`) is a traceback instead of X001.

## What would fix it

Bound what costs memory: count cells (and characters of decoded text) against a fixed limit,
store cells compactly (offsets into the bytes rather than one Python string per cell), and drop
cached tables that later statements don't use. Then document the bound as "at most N cells", which
a reviewer can check.
