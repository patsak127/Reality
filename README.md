# Reality

Reality is a checker language built around explicit evaluation criteria. Before a claim can be
checked, its metric, threshold, data, and the person who adopted the test must all be fixed. The
machine can propose tests but never adopt them, and an adopted test can't be quietly changed
after a result. It is domain-independent and currently checks exact arithmetic over data files.

It began as an attempt to build a language out of mathematics, instead of describing mathematics
in English.

## What it looks like

A requirement such as "players understand wall-running" can be written down, but it can't be
assigned as work until a person adopts a measure for it, for example "at least 80 percent of
first-time players finish the tutorial without external help in under 240 seconds". Adoption is
signed with the adopter's SSH key. Once adopted, the measure is checked against the data and the
result is HOLDS, DOES NOT HOLD or NOT CHECKED. Editing the bar after a result is refused; the team
can change its mind only with new, later, signed lines (withdraw the old measure, adopt a new
one), and the old result stays on record. Reality never says whether a measure is a good one.

The adoption step is analogous to pre-registration in science: the criterion is fixed before the
experiment is run.

## Quick start

Needs Python 3.13 and OpenSSH (`ssh-keygen`). The checker itself uses only the standard library;
the tests need `pytest`.

```sh
python3 req/demo/demo.py --work /tmp/reality-demo
```

Without `--key`, the demo generates a throwaway test key in the work folder (comment
`REALITY-TEST-KEY-NOT-PATSAK`) and types the confirmations itself. The expected output is
`req/demo/expected/transcript.txt`. To adopt with your own key, see `req/demo/README.md`.

The demo has three examples: an image upscaler ("must preserve artistic intent"), loot-drop
odds ("drops should feel fair") and a playtest ("players understand wall-running").

## Layout

| path | what |
|---|---|
| `req/` | the requirements layer: requirements, proposed and adopted measures, signed adoption and withdrawal, checks (`SPEC.md`, `STATUS.md`) |
| `req/src/reality_req/` | its trusted code (668 lines; cap 900), plus the untrusted signing helper `sign.py` |
| `req/demo/` | the demo driver, its made-up data producers and the expected transcript |
| `req/tests/` | tests of the requirements layer |
| `v4/` | the checker kernel that `req` runs every adopted measure through (`SPEC.md`, `SPEC-EXACT.md`, `KNOWN-OPEN.md`) |
| `v4/src/reality4/` | the kernel (trusted base 9,539 lines); `reality4_ref` is an independent reference implementation used by the tests |
| `v4/metatheory/` | Lean proofs about the kernel's arithmetic |
| `v4/bids/` | the BIDS 1.0.1 sentence register the file reader follows |
| `v4/tests/`, `v4/tools/` | the kernel's test suite and test tools |

## Tests

```sh
cd req && python3 -m pytest -q tests
cd v4  && python3 -m pytest -q tests
```

Part of the v4 suite reads a small copy of OpenNeuro dataset ds001734 (events files and JSON
sidecars only, no images) at `v4/tests/data/ds001734-box/`. It is third-party data and is not
included here; without it those tests error with "missing fixture". Download ds001734 from
https://openneuro.org/datasets/ds001734 and copy its non-image files there; `v4/tests/bidsfix.py`
pins the expected hashes.

## Limits

- Only counts, shares, sums, comparisons and exact arithmetic over data files. There are no
  statistical tests: "37 of 50 is below 80 percent" is a count, not a significance result, and
  small samples make such results noisy.
- All demo data is made up by the producers in `req/demo/` (no company or playtest data from
  anyone). The demo is built with a game studio audience in mind; no studio was involved.
- Units are plain text inside measure descriptions and are not checked.
- Proposals are not signed; who proposed a measure is what the ledger says.
- Not independently reviewed as a whole. `req/STATUS.md` and `v4/KNOWN-OPEN.md` list what is
  known to be open.

## License

No license has been chosen yet. Until one is added, all rights are reserved.
