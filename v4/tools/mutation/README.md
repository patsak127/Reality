# Mutation run of v4 (a report, not a gate)

DESIGN 4: "The mutator workflow is kept as a report (`v4/tools/mutation/`, source override
`REALITY4_SRC`)". tests/helpers.py and test_v4_cli.py import the checker from `$REALITY4_SRC`
when it is set, so a mutator worker's private copy of `src/` is the one tested.

1. `git archive <commit> v4 | tar -x -C ../mutation-v4`, then copy the untracked fixture
   `tests/data/ds001734-box` into the copy (it is not in git).
2. `mutation-v4/run.sh` and `batch.sh` (copies here) run unclebob/mutator with 7 workers and
   `pytest -q -x tests --deselect tests/test_differential.py::test_differential` (the differential
   test takes 35 of the 63 s and compares against the reference implementation; it is left out for
   time and the report says so). Coverage is taken once (keys) and reused; modules only reached in
   subprocesses (`__main__`, `machine`) or that coverage shows as unreached run with `--no-coverage`.
3. `python3 tools/mutation/summarize.py ../mutation-v4/logs ../mutation-v4/v4/src/reality4` prints
   the table and every survivor with its source line; REPORT.md classifies them by reading.
