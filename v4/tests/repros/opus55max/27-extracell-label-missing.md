# 27. `max`, `min` and `sum` over BIDS participants drop the `ExtraCell` marking from the sort

**Category:** design issue (the sort does not say which reader's column it is).
**Spec clause:** §2 table (the BIDS reader gives "an `ExtraCell` for any column 1.0.1 does not
define"); README "Columns the dataset adds are reachable only as `extra(...)`, and their sort says
so (`ExtraCell`)".
**Severity:** low. **Confidence:** high.

## Program

`findings\27-extracell-label-missing.rl`, with the made-up dataset `findings\27-ds\` (manifest
`findings\27-m\`), `participants.tsv` = `participant_id group age` / `sub-01 a 30` / `sub-02 b 41`:

```
dataset d = sha256:db55c056c38e8571ace1e4366796513ad73fa46abdb1ed83b924faa14ee7a82b
let p = participants(bids(d))
claim count(where(p, eq("age", "30")))
claim max(p, "age")
claim sum(where(p, eq("group", "b")), 3)
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\27-extracell-label-missing.rl --files findings\27-m --root findings\27-ds
line 3: formed: Count[Rows[Participants[BIDS-1.0.1[#1] from #2] where ExtraCell col 3 = "30"]] = 1 (Exact)
line 4: formed: Max[Participants[BIDS-1.0.1[#1] from #2], col 3] = 41 (Exact)
line 5: formed: Sum[Rows[Participants[BIDS-1.0.1[#1] from #2] where ExtraCell col 2 = "b"], col 3] = 41 (Exact)
accepted
```

The same column, `age`, is `ExtraCell col 3` in line 3's condition and plain `col 3` in lines 4
and 5. A reader of line 4 cannot tell from the sort whether column 3 is a column BIDS 1.0.1 defines
(none is, besides `participant_id`) or an extra one, which is the distinction README promises the
sort makes.

## Cause

`c_where` names columns of a participant set `ExtraCell col k` (`kernel.py:283-284`);
`column_numbers` and `c_sum/c_max/c_min` print `col {k}` for every base (`kernel.py:377`, `:383`,
`:389`), and `extra()` is the only other place that says `ExtraCell`.

## What would fix it

Print `ExtraCell col k` (or `participant_id`) whenever the base is a participant set, in every
computation that takes a column.
