# 17. For BIDS values, check 2's trace is written by the same code that writes the sort; it is not an independent check

- **Category:** docs overclaim / design issue
- **Spec clauses:** §1 floor, "A second, independent check sits underneath"; §2 check 2; README "The store records every file whose bytes a value read"; SPEC §2 item 11 **[call]**
- **Severity:** medium (the guarantee is advertised as independent). **Confidence:** high.

## What happens

For plain TSV and bytes, check 2 is real: the trace comes from `Store.text()`, a different path from
the code that writes the sort. For BIDS values it is not:

- `onset()`, `duration()`, `volumes()` and `tr()` call `touch_bold()` (`kernel.py:525-526`), which
  calls `store.path()`. That *records* the BOLD hash without reading a byte of it. The onset is
  computed from the events file only; `volumes()` and `tr()` use the header and metadata that were
  read during the conformance gate.
- `tr()` re-records its sidecar through the JSON cache (`store.json(h, p, gate=False)`), and
  `participants()` re-records participants.tsv through the text cache. Both are notes, not reads.
- `bids()` and `recording()` call `store.note(mh)` directly.

So each BIDS value's trace holds exactly the hashes that the same function put into its sort. If you
disable `touch_bold`, check 2 itself reports that the BOLD file in F3's sort was "not computed from".

## Reproduce

```
.venv\Scripts\python.exe findings\gen\no_touch.py
```

(It runs `17-check2-for-bids-is-written-by-the-sort-code.rl`, which is F3 on the fabricated copy,
first as shipped and then with `Checker.touch_bold` replaced by a no-op.)

Output (`17.out`):

```
-- as shipped
line 6: formed: EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 001 task MGT run 01: #2], #3 row 1] is recorded as 4.071 s (Recorded[s])
accepted
-- touch_bold disabled
line 6: refused [C001, floor]: check 2: the claim's sort names sha256:3c861ed4…, but its value was not computed from it; the sort and the dependency set disagree ...
refused (1 statement)
```

## Judgement

The BOLD file belongs in F3's sort, because it is the reference event. But it is a *reference*, not
a value dependency, and check 2 has no notion of that difference. Today the check is satisfied by
writing to the trace by hand. Either:

- give check 2 two kinds of dependency (value reads, and references that must be present in the
  manifest and must have conformed), and have the reader record each kind where it actually reads;
  or
- drop "independent" for BIDS values from README and SPEC, and say that for BIDS the second check is
  the conformance gate (C002) plus the manifest hash.

The tests (`test_03_*`) only monkeypatch TSV computations, so they cannot tell the difference.
