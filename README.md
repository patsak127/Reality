# Reality

Reality makes proposing a criterion and adopting one different kinds of statement.

Before any data is checked, a person has to commit, with a signature, to what counts as success:
the metric, the threshold and the data. The machine can propose measures but can never adopt
them. Once a measure is adopted, it can't be quietly changed after a result. Withdrawing it is
possible, but the withdrawal is signed and stays in the history. Reality won't let you rewrite
history.

This is pre-registration, as in science, made mechanical: the criterion is fixed before the
experiment is run, and the language enforces it.

Reality never says whether a measure is a good one. Its job is to make evaluation criteria explicit and their history impossible to rewrite, not to choose them.

## What it looks like

A requirement such as "drops should feel fair" or "players understand wall-running" can be
written down, but it cannot become work or be checked until it has an adopted measure. So a
question without an agreed measure can't be stated. This is what is left of the original aim: a
language built out of mathematics, instead of describing mathematics in English, in which
unformed questions can't be asked.

For wall-running, a proposed measure could be "at least 80 percent of first-time players finish
the tutorial without external help in under 240 seconds". A person adopts it by signing with
their SSH key. Reality then checks the measure, never the requirement text, against the data,
and the result is HOLDS, DOES NOT HOLD or NOT CHECKED. Editing the bar after a result is
refused; the only way to change course is new, later, signed lines (withdraw the old measure,
adopt a new one), and the old result stays on record.

## Quick start

Needs Python 3.13 and OpenSSH (`ssh-keygen`). The checker itself uses only the standard library;
the tests need `pytest`.

```sh
python3 req/demo/demo.py --work /tmp/reality-demo
```

The demo has four examples: loot-drop odds ("drops should feel fair"), a playtest ("players
understand wall-running"), an image upscaler ("must preserve artistic intent") and an AI
evaluation ("the model refuses harmful requests", with the prompt set pinned by its hash). Without
`--key`, it generates a throwaway test key in the work folder (comment
`REALITY-TEST-KEY-NOT-PATSAK`) and types the confirmations itself. The expected output is
`req/demo/expected/transcript.txt`. To adopt with your own key, see `req/demo/README.md`.

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

## Current limits

- Only counts, shares, sums, comparisons and exact arithmetic over data files. There are no
  statistical tests: "37 of 50 is below 80 percent" is a count, not a significance result, and
  small samples make such results noisy.
- All demo data is made up by the producers in `req/demo/` (no company or playtest data from
  anyone; no real model, prompts or benchmark). The demo is built with a game studio audience in mind; no studio was involved.
- The checker is pinned to Python 3.13 (Unicode 15.1). On another Python version it gives no
  verdict rather than risk a different answer.
- Units are plain text inside measure descriptions and are not checked.
- Proposals are not signed; who proposed a measure is what the ledger says.
- Not independently reviewed as a whole. `req/STATUS.md` and `v4/KNOWN-OPEN.md` list what is
  known to be open.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE). Copyright 2026 patsak127.
