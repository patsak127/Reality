# 24. Lookalike keys are refused per literal, not per key column as §10.3 says

**Category:** design issue (a deviation from the frozen §10.3, in the lax direction), and an
inconsistency between the plain-TSV and BIDS paths.
**Spec clause:** §10.3 *Handling* ("Two *distinct* keys with equal skeletons inside one claim's
scope refuse the claim (finding 8). The scope is every key column the derivation reads.").
**Severity:** low (I found no claim whose answer the lookalike pair changes). **Confidence:** high.

## Program

`findings\24-lookalike-scope.rl`, with `findings\24-keys.tsv`, whose key column holds `A1`, `Al`
(a lookalike pair under the pinned table: `l → 1`) and `B`:

```
file f = sha256:061576c484d6bbf1ad58cca5d2159dad833b2894d4f17e29d42df26699132e64
let t = tsv(f)
claim cell(t, key(1, "B"), 3)
claim count(where(t, ne(1, "B")))
claim cell(t, key(1, "A1"), 3)
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\24-lookalike-scope.rl --files findings\24-keys.tsv
line 3: formed: Cell[TSV[#1], row 3 (the row whose col 1 is "B"), col 3] = "29"
  #1 = sha256:061576c484d6bbf1ad58cca5d2159dad833b2894d4f17e29d42df26699132e64
line 4: formed: Count[Rows[TSV[#1] where col 1 != "B"]] = 2 (Exact)
  #1 = sha256:061576c484d6bbf1ad58cca5d2159dad833b2894d4f17e29d42df26699132e64
line 5: refused [K002, item 1]: key(): the key "A1" and the cell "Al" in column 1 look alike (principle §10.3); the row is not picked out by bytes that can be told apart
refused (1 statement)
```

## What is wrong

Lines 3 and 4 read key column 1, which holds two distinct keys with equal skeletons; §10.3 says
the claim is refused. v2 compares only the written key with the cells (`kernel.py:323-327`,
`:288-300`), so the claim forms unless it happens to name one of the pair (line 5). For BIDS
participants v2 does follow §10.3: `labels_distinct` checks every label of the column (K003,
`kernel.py:457-460`, `:470`), so the same table as `participants.tsv` would refuse every
participant claim. I could not make the pair change an answer (line 4 counts rows, and rows are
distinct by position), which is why this is not counted as a hit; but the code and the frozen spec
disagree, and SPEC §2 item 5 does not mention it.

## What would fix it

Run `keys.lookalikes` over the whole key column whenever `key()` or a condition reads it, as
`c_participants` does; or amend §10.3 to the per-literal rule and say why it is enough.
