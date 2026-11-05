# Mutation run of v4 (a report, not a gate)

DESIGN 4: "The mutator workflow is kept as a report (`v4/tools/mutation/`, source override
`REALITY4_SRC`)". tests/helpers.py and test_v4_cli.py import the checker from `$REALITY4_SRC`
when it is set, so a mutator worker's private copy of `src/` is the one tested.

The machine-local driver scripts that once lived here are not included in this repository.
`summarize.py` turns a logs directory into the survivor table; `REPORT.md` classifies survivors
by reading. To re-run mutation elsewhere: unpack a `git archive` of `v4`, point
`REALITY4_SRC` at that copy's `src/`, and drive unclebob/mutator with
`pytest -q -x tests --deselect tests/test_differential.py::test_differential`.
