# 26. P007 does not check the denominator's sign

**Category:** bug (a wrong refusal code where nothing forms).
**Spec clause:** SPEC §3 (P007 "ratio literal"); the message itself ("a ratio literal is a whole
number over a positive whole number").
**Severity:** low. **Confidence:** high.

## Program

`findings\26-negative-denominator.rl`, with `findings\26-table.tsv` (two of three rows hold `A`):

```
file f = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
claim share(where(tsv(f), eq(2, "A"))) is -2/-3
claim share(where(tsv(f), eq(2, "A"))) is 2/-3
```

## Command and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\26-negative-denominator.rl --files findings\26-table.tsv
line 2: refused [P007, item 1]: a ratio literal is a whole number over a positive whole number
line 3: refused [V001, item 5]: the claim writes -2/3; computed from the bytes it is 2/3
refused (2 statements)
```

Line 3 is not a ratio literal by P007's own rule, but it is parsed as one (−2/3) and refused as a
false claim instead.

## Cause

`syntax._P.literal` tests `v.startswith("-")` for the numerator and `int(d) == 0` for the
denominator (`syntax.py:240`); the tokenizer gives `-3` as one integer token, so a negative
denominator passes.

## What would fix it

Refuse `int(d) <= 0`.
