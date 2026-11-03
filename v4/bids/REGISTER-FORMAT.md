# REGISTER-1.0.1.tsv: format

See SPEC.md §8.1 (normative). Regenerate the skeleton, keeping existing classes:

    python3 v4/tools/split_register.py /workspace/team/research/sources/bids-1.0.1.txt v4/bids/REGISTER-1.0.1.tsv --write

Check that every sentence is classified once (fails until Phase E fills the classes):

    python3 v4/tools/split_register.py /workspace/team/research/sources/bids-1.0.1.txt v4/bids/REGISTER-1.0.1.tsv --check

Classes: `checked` (codes required), `silent` (decision required), `unshowable` (note required),
`notfiles`, `reality-call` (note names the call). `codes` may be `read`: a reading rule the
reader applies when it forms (pinned by a forming test), not a refusal.

The class columns are generated from the table in `v4/tools/fill_register.py` (edit the table,
then run it); `tests/test_v4_register.py` checks the register against the splitter and the
table, that its codes are raised by bids101.py, and the decisions lint (every B30 the reader
cites is a silent row; every silent decision is computed by a choice point citing one of its rows).

State at Phase E (25 Oct 2026, 22:00 CET): 633 sentences, all classified: 257 checked, 228
notfiles, 15 reality-call, 10 silent, 123 unshowable.
