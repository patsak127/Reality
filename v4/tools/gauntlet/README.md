# tools/gauntlet: probes for the failure patterns the reviews keep finding

Builder Bluebell, 24 Oct 2026 (Europe/Berlin).

```sh
cd v2
python3 tools/gauntlet/run.py                  # all probes (about 10 s on the box)
python3 tools/gauntlet/run.py --only env,neighbours
python3 tools/gauntlet/run.py --json           # the same report as JSON
python3 tools/gauntlet/run.py --python PATH    # interpreter for the subprocess probes
```

The subprocess probes use the harness interpreter (`~/reality-harness/venv/bin/python`) when it
exists, otherwise the one running `run.py`. Standard library only. Nothing under `v2/` is written;
scratch files go to a temporary directory.

## Where the idea comes from, and what was taken

Thoughtlogging has a `.gauntlet/` folder: a config and three rulesets (`thoughtlogging.toml`,
`unreal-cpp.toml`, `blender-pipeline.toml`) read by a runner in `Tools/gauntlet/`. Each rule says
what it checks, `why` it exists, and in `verifies` what a pass proves "**and what it does not**".
Reality already has a port of that runner and format in `harness/gauntlet.py` with
`harness/rules/reality.toml`. That ruleset still points at `checker/` (the rcheck package), not at
v2.

What is taken here is the habit, not the runner:
- every probe states what it verifies and what it does not (below);
- a check that cannot run says so; it is never read as clean (exit 3);
- the rule from Thoughtlogging's README, "A rule that is permanently red gets ignored", which is
  why only one probe can change the exit code.

What is not taken, on purpose:
- no `block` severity on design rules, no freezing of wording, and no hook that runs this
  automatically;
- no model-judged ("judge") rules. The judgement items are in `CHECKLIST.md` for a person or a
  reviewer to answer;
- no file-pattern rules of the kind `none-may-match`, because Reality's failures are in
  behaviour, not in spelling.

## Exit code

| code | meaning |
|---|---|
| 0 | No invariant probe found anything. Observations may still be listed. |
| 1 | `env` found a difference: an output depended on something other than the text and the bytes. |
| 2 | Bad command line. |
| 3 | A probe itself broke. A broken probe is never a pass. |

Only `env` can give 1, because principle clause 4 is an invariant: "the verdict depends on
anything other than the text and the file bytes" is nonsense by definition. Everything else is a
report. A probe that finds something does not mean the code is wrong. It means two things the
project treats as the same are not treated the same, or a document and the code disagree. Deciding
which side moves is a person's call.

## The probes

| probe | review pattern | what it verifies | what it does not |
|---|---|---|---|
| `env` | verdict depends on the environment (v1 #1; v2 05, 06, 10) | `python -m reality2 check` gives the same exit code, stdout bytes and (empty or not) stderr for a fixed corpus under: PYTHONHASHSEED 1 and random; PYTHONINTMAXSTRDIGITS 640 and 0; console encoding ascii and latin-1 with UTF-8 mode off; locale C; TZ; cwd `/`; `--files` reversed and given as one folder; programs in reverse order; each file program alone versus with the others. The corpus is 4 programs over 4 files written by `run.py` (one with a 5 000-digit cell, one with a non-ASCII cell) plus every `tests/old/*.rl`. | Memory and recursion limits, other machines (that is `harness/xrun.py`), time across days, and any input outside the corpus. A clean run says "nothing found on this corpus". |
| `neighbours` | one rule applied to one case and not its neighbours (§10.2; v2 11, 14, 15, INDEX (e)) | For 14 separator-like hazards (CR, BOM, U+2028, U+2029, NEL, FF, VT, NUL, `"`, NBSP, ZWSP, soft hyphen, trailing space, byte 0xFF) placed in a data cell, a header and at the file start, and 11 lookalike pairs (4 ASCII, 5 non-ASCII, NFC/NFD, U+2011) placed in `key()`, `eq()` and header lookups of the plain TSV reader, it prints what the checker does. It lists any hazard treated differently in different places, and any place where some hazards of a class are refused and others form. | Which treatment is right. The two classes are this tool's grouping and are meant to be edited. JSON, the BIDS TSV reader, NIfTI and the manifest are not probed. |
| `codes` | docs and model name things the code does not have (v2 (f): C003, V009) | The refusal codes raised in `src/reality2` against SPEC §3 (ranges expanded), the README, `bids/RULES-1.0.1.md`, `metatheory/*.lean`, and whether any file in `tests/` mentions each code. | A mention is not a test. A code quoted in prose counts as named. |
| `surface` | docs overclaim (v2 OVERALL) | The computations in `kernel.py` (`c_*` methods plus the `eq`/`ne`/`key` forms) against the README's **Computations** table, both ways. | Whether the README describes each one correctly. |
| `numbers` | docs overclaim | README's trusted-base line counts, the `__main__.py` line count and "(N tests)" against `wc`-style counts and `pytest --collect-only`. | Numbers written in other shapes; timings. A reworded claim is not found, and that is silence, not a failure. |
| `independence` | a second check that is not independent (v2 17, 18) | Whether `reality2_ref` imports `reality2`; whether the differential test hands the reference the program text or a pre-parsed query; and, by replaying the test's generator with its own seed and loop counts, which computations, `is`, and row positions it ever produces. | Whether the reference was written from the spec by someone else, and whether check 2's trace is written by code separate from the sort (finding 17). Those are on the checklist. |
| `table` | docs drift from code | SPEC §4's F/N rows against what `tools/acceptance_table.py` prints now, row by row. | Whether the expectations themselves are right. |

## Changing it

Add a hazard, a variant or a probe whenever a review finds a new instance of a pattern. Remove one
when it stops telling anyone anything. Nothing else depends on this tool.
