# 15. A 57-byte `dataset_description.json` stalls the BIDS reader: exact JSON numbers expand exponents

**Category:** bug (slow and memory-heavy from a tiny valid input; the bounds do not see it).
**Spec clause:** §1 item 4; SPEC §2 item 12; README "JSON is read strictly (J00x)".
**Severity:** medium. **Confidence:** high.

## Program

`findings\15-json-exponent-stall.rl`, with the made-up dataset `findings\15-ds\` (manifest
`findings\15-m\`), whose `dataset_description.json` is valid RFC 8259 JSON:

```
{"Name": "x", "BIDSVersion": "1.0.1", "Size": 1e60000000}
```

```
dataset d = sha256:<see the .rl>
claim count(participants(bids(d)))
```

`15-json-exponent-stall-small.rl` (dataset `15-ds-small`) is the same with `1e10000000`.

## Commands and output

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\15-json-exponent-stall-small.rl --files findings\15-m-small --root findings\15-ds-small
line 2: formed: Count[Participants[BIDS-1.0.1[#1] from #2]] = 1 (Exact)
  ...
accepted
[exit code 0; wall 5.9 s; peak private memory 29 MB]

> python -m reality2 check findings\15-json-exponent-stall.rl --files findings\15-m --root findings\15-ds
[KILLED at 60 s; wall 60.0 s; peak private memory 113 MB]
```

The field is not one BIDS defines, and nothing reads it; the cost is all in parsing. The text
read is 57 bytes, i.e. 1 counted step.

## Cause

`parse_json` reads every JSON number as an exact `Fraction` (`readers.py:218`), and
`Fraction("1e60000000")` computes `10**60000000` (a 199-million-bit integer). With `1e40000000`
the same check took 52.8 s in one run and was stopped at 60 s in another. The cost grows
faster than linearly in the exponent, so a few more digits in the exponent mean hours, and enough
memory to fail on smaller machines (finding 06).

## What would fix it

Parse JSON numbers into an exact (mantissa, exponent) pair and expand only when a value is used,
with a fixed bound on the exponent (a refusal code beyond it); or refuse exponents beyond a fixed
size while reading. JSON numbers BIDS uses (seconds, echo times) never need more than a few
digits of exponent.
