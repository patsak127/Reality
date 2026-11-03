# 17. Counts and shares cannot be compared or subtracted, though decimals can

**Category:** must-form refused (overcorrection).
**Spec clause:** §10.1 (`exceeds(x, c: Cutoff[s])` with `Cutoff[s]` "rational, of the kind of the
sort `s` being compared"; item 6's example "exceeding 3.1 contradicts not exceeding 2.0"); §5 F2,
F12 (counts and shares are the language's exact values); REVIEW brief (b).
**Severity:** medium (expressiveness). **Confidence:** high.

## Program

`findings\17-counts-and-shares-cannot-be-compared.rl`, on the box copy's `participants.tsv`:

```
file p = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
let t = tsv(p)
claim exceeds(count(where(t, eq(2, "equalRange"))), c = 49)
claim exceeds(share(where(t, eq(2, "equalRange"))), c = 0.4)
claim difference(count(where(t, eq(2, "equalRange"))), count(where(t, eq(2, "equalIndifference"))))
claim exceeds(sum(t, 4), c = 2000)
claim exceeds(number(cell(t, 1, 4)), c = 20)
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\17-counts-and-shares-cannot-be-compared.rl --files tests\data\ds001734-box\participants.tsv
line 3: refused [S007, item 1]: exceeds()'s argument must be a number, not a count
line 4: refused [S007, item 1]: exceeds()'s argument must be a number, not a share
line 5: refused [S007, item 1]: difference()'s first argument must be a number, not a count
line 6: formed: Exceeds[Sum[TSV[#1], col 4], c = 2000] holds
  #1 = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
line 7: formed: Exceeds[Decimal[Cell[TSV[#1], row 1, col 4]], c = 20] holds
  #1 = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
refused (3 statements)
```

## Why it matters

"At least 50 participants are in equalRange", "more than 40 % of the rows", "equalRange has as
many rows as equalIndifference" are the most ordinary sentences in a methods section, and the
spec's own example of item 6 is a pair of crossings. In v2 a count is the most exact value there
is (an integer read from rows), yet it is the one value that cannot cross a cutoff, while a sum of
the age column, or a single decimal cell, can. Nothing in the principle refuses comparing a count:
the cutoff is a printed parameter, and the sort is known. The refusal comes from the kernel's kind
check (`compare` and `c_difference` accept only `num`, `kernel.py:408-411`, `:391-395`).

Other things a careful scientist needs and v2 cannot say, by design or by scope (listed so the
author can decide which are overcorrection): selection by a numeric condition (`age > 30`);
a mean; the number of events in a run as a BIDS sort; anything over all recordings ("every run's
TR is recorded as 1 s", "432 events files"); `is` with a unit other than the standard's (`4071 ms`).

## What would fix it

Let `exceeds`/`below` take counts and shares (the cutoff is a rational, exact comparison), and let
`difference` take two counts of the same kind of set.
