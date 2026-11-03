# Mutation report, Reality v4 (Phase G)

Run: unclebob/mutator on a git archive of v4 at 03c5c2f in ../mutation-v4 (started 23:38 CET, 25 Oct),
7 workers, test command `pytest -q -x tests --deselect tests/test_differential.py::test_differential`
(636 tests; the 35 s differential test is left out for time). Workflow: tools/mutation/README.md.
Classes as in mutation-v3: BLIND (a behaviour no test pins), MSG (refusal text only), EQUIV (no
observable change). Every BLIND survivor below now has a test (tests/test_v4_mutation_run.py),
checked by hand against the mutant where noted. A report, not a gate.

## Status

Modules finished: keys, sorts, syntax, readers, bids101 (exact, __main__, machine show as uncovered under
reused coverage and are rerun with --no-coverage). kernel, witness: in progress.

## Classified survivors

### keys.py (24: 20 killed, 4 survived)
- 69 `and->or` (is_header_name): BLIND; killed by test_header_names_addressable_by_name.
- 85 `!=->==`, `or->and` (invisible): BLIND; killed by test_invisible (no-break space, U+200B, U+0001).
- 87 `1->0` (leading space): BLIND; killed by test_invisible (" ab").
### sorts.py (26: 12 killed, 8 survived, 6 uncovered)
- 43, 56 x4, 58 x2: BLIND (R006 sort bounds at the edge); killed by test_sort_depth_bound_edge, test_sort_size_bound_edge.
- 77 `<-><=` (esc of 0x7f): BLIND; killed by test_del_and_tilde_print.
- 20, 33, 62 (__eq__ of File, Lit, S) UNCOVERED; test_sort_equality covers them.
### syntax.py (205: 190 killed, 13 survived, 2 uncovered)
- 175 `>->>=`: BLIND (a line of exactly 10,000 tokens); killed by test_line_token_bound_edge.
- 127 `>=->>`: MSG (an \x escape that ends an unclosed line refuses P002 either way).
- 154 x4, 191 x2, 287: MSG (refusal text only).
- 156 `i+1->i+0`, 190 `tk[0]->tk[1]`: EQUIV (as in v3: the name loop re-reads its first character; no token value is None).
- 332 `group(1)->group(0)`: EQUIV (when group 1 matches it is the whole match).
- 337 `>->>=`: EQUIV (a 64,000,000-byte program always measures over 1,000,000; same R001 line).
- 338, 346 UNCOVERED (the R001 line number): a coverage artifact; 346 `0->1` is killed by test_program_size_bound_edge (checked by hand).
### readers.py (301: 229 killed, 65 survived, 7 uncovered)
- 46, 48 (Steps default and R002 edge): BLIND; killed by test_steps_bound_edge_and_default.
- 122, 188, 234 (statement text total, R003 total and per-file edges): BLIND; killed by test_text_bounds_at_their_edges.
- 197, 206 x4, 212 (a gate's inner budget, its accounted size, its R003 edge): BLIND; killed by test_measured_charges_its_inner_reads_once.
- 167, 171 (R012 accounted-bytes edge): BLIND; killed by test_accounted_bytes_edge.
- 222 x2, 243, 247 x4, 253 x4, 271 x4, 352 x2, 399 x2 (step and byte costs of slice, text, json, json_file, nifti, parse_tsv, parse_csv): BLIND (accounting); pinned by test_step_costs_of_the_readers.
- 247 `or->and` (the json `what` label): MSG.
- 281 (Table's bom default): BLIND; test_table_bom_default.
- 328 (one final empty line in a 2-column table): BLIND; killed by test_final_empty_line_in_a_multi_column_tsv.
- 327, 330, 332, 335 (line and column numbers and the choice of T003 text): MSG, now pinned by test_csv_header_refusal_names_line_1 and test_table_refusal_messages_name_the_line_and_column.
- 374, 379 x2 (CSV: a quoted field that ends the line; an empty first field): BLIND, serious for 374 (the mutant crashes on `"a","b"`); killed by test_csv_field_edges.
- 366 x2: EQUIV (the closing-quote search starts after the opening quote, so q is never 0).
- 413 (an exponent using all ten digits): BLIND; killed by test_exponent_with_all_ten_digits_is_r007.
- 438 (an escaped quote inside a JSON string): BLIND; killed by test_escaped_quote_keeps_brackets_inside_the_string.
- 309, 422, 457, 488, 534: MSG.
- 561 `range(1->0`: EQUIV (dim[0] >= 1 is checked first).
- 576 `and->or` (gz_head keeps reading after the header): BLIND, cost: killed by test_gz_header_stops_after_the_header (2 MiB of random data after the header; the mutant refuses R003).
- 576 `<-><=`, 586, 597: EQUIV (one more decompressed byte, a larger max_length, a size one too large: the same header).
- 579 `<-><=` (a truncated gzip stream): BLIND (the mutant loops until the mutator's timeout); test_truncated_gz_refuses.
- 582 (the second compressed chunk's length): BLIND; killed by test_gz_header_after_a_long_run_of_empty_blocks.
- 622 `or->and` occ0: EQUIV (the parts check refuses "" and a leading "/"); occ1 and occ2 are killed by test_manifest_paths_refused.
- 625: EQUIV (invisible() catches every Cc first). 657: EQUIV ("" is never a manifest path).
- 640 (R003 manifest entries edge): BLIND; killed by test_manifest_entries_bound_edge.
- 262-265 UNCOVERED (Store.nifti_file's plain and gzip branches): covered now by test_gz_header_after_a_long_run_of_empty_blocks (gzip); the plain branch by test_v4_nifti.py (a coverage artifact of the reused data).

### bids101.py (404: 320 killed, 81 survived, 3 uncovered)

Each case below was probed by hand on a small BIDS dataset before the test was written; every listed kill was checked by applying the mutant by hand (with no bytecode cache) and running tests/test_v4_mutation_run.py.

- 70 (an entity key with a digit), 144 (a non-events file in func/), 151 (a non-fieldmap file in fmap/): BLIND; test_bids_file_kinds_and_labels (each is B17).
- 123, 126, 130, 131 (session folders and scans files): BLIND; the same test (each is B14).
- 612 (a participant_id with no `sub-`): BLIND; the same test (B11).
- 189 (tr_consistent's guards: a TR that is not a Fraction, zero or negative; a missing or non-positive pixdim[4]): BLIND; test_tr_consistent_guards (`tr <= 0 -> tr <= 1` killed).
- 225, 319 (step charges inside the BIDS read): BLIND, cost; test_bids_read_step_count_is_pinned pins 285 steps for the mini dataset (`len(lst) + 1 -> + 0` killed).
- 245, 251 (the folder of a sidecar next to the image): BLIND; test_sidecar_in_the_image_folder (killed).
- 364, 366, 396 (a bound hit while reading a BIDS TSV or a NIfTI header must stay R/F/M, not turn into a B code): BLIND; test_a_bound_inside_a_bids_file_read_keeps_its_code (both `code[0] -> code[1]` killed).
- 497, 552, 556 (B30 uses the onset, the end of the run under any TR, at-or-after the end): BLIND; test_onsets_after_the_end_of_the_run (all three killed).
- 233, 236: EQUIV (the folder key of a top-level file is "" either way).
- 294, 418, 426, 446, 502, 507-514, 524, 551, 557, 610 (`0->1` and similar in the indices that pick a message part): MSG, not pinned.
- 164-175 (float32 nearest-value ties in `nearest`): BLIND but exotic (needs a TR exactly half-way between two float32 values); not tested, listed in KNOWN-OPEN.
- 241, 265, 279, 404, 498, 522-532, 670, 671: not probed one by one (as in v3: messages and redundant guards by reading); left unclassified.
- 523, 524 UNCOVERED (a SliceEncodingDirection that is not i, j or k): now covered by test_slice_encoding_direction_is_checked (`or -> and` at 523 killed); 524 `0 -> 1` is MSG (it changes only the value quoted in the message).

### kernel.py (574 sites; totals in the table)

Under reused coverage, 87 kernel sites show as UNCOVERED. The tests that reach them run in a way the coverage pass did not record, so they are rerun with `--no-coverage --lines` once the batch ends (below). Survivors:

- 321 `k - 1` (killed already); 311 and 321 `jm[1] -> jm[0]` (a JSON number's identity loses its file, so two files' numbers become one value): BLIND, serious; test_numbers_in_two_json_files_are_two_values (both killed).
- 167 (a widened value's identity loses what it widens): BLIND; test_a_widened_value_is_identified_by_what_it_widens (killed). 166 `== -> !=`: EQUIV (the fallback identity is the sort, which also names what is widened and the tolerance).
- 718, 719 (`below`/`atleast` at exactly the cutoff): BLIND; test_comparisons_at_the_cutoff (both killed).
- 144 `0 -> 1` (a tolerance of 0 gets S004, not S008): BLIND, code; test_a_zero_tolerance_is_idle_not_ill_typed (killed). 144 `== -> !=`: MSG.
- 686, 687: not reached (every interval `difference()` sees carries an affine form, so the line-686 bounds are always replaced). 707 `+ -> -`: EQUIV (the radius sums absolute coefficients, and each key's coefficients come from one widen). test_difference_of_a_widened_value pins the bounds anyway.
- 286 `1 -> 0`: EQUIV (the identity keeps the file and path either way).
- 118, 132, 224, 246, 366, 679, 723, 895, 1035, 1046, 1206, 1212: MSG.
- 726 `True -> False`: EQUIV (a formed comparison's value is not read; the line prints "holds").
- 258, 263, 302, 516, 748, 818, 1101 (the step charges for TSV, CSV, member() and the BIDS label passes, and the memory charges for a selection and a table): BLIND, cost; test_kernel_charges_are_pinned pins steps and accounted bytes for five small programs (all seven killed).
- 1144, 1151, 1184, 1185, 1188 (output bytes and the R014/R011 edges): BLIND, bounds; test_output_bounds_at_their_edges sets each bound to the exact size, then one byte less (all killed). 1145 `0 -> 1`: EQUIV (count_refusals sets `counted` to 0 before the first result exists). 1150 is killed.
- 65 (the R009 print bound): no input reaches it, because R007 bounds exponents at 1000 and literals at 1000 digits. It is a defensive bound, now pinned by test_print_bound_at_its_edge, which calls fmt directly (all three killed).
- 384 `or -> and` (a non-ASCII header name): BLIND; test_a_non_ascii_header_name_is_k001 (killed).
- 228, 230 `1 -> 0` in the sort: EQUIV (a bare file or dataset name is not printed or compared; the readers build their sorts from the hash). 887 `False -> True`: EQUIV in output (store.nifti with full=True gives the same dim and pixdim; only the read differs). 963 `and -> or`: EQUIV (by reading: `exprs` holds only let names, and each is bound in `env`).

### machine.py (6 sites, run with --no-coverage: 3 killed, 3 survived)

- 20 (cgroup memory.max of `max`), 31 (the Windows branch taken off Windows when sysconf fails), 69 (a limit exactly at the floor meets it): BLIND; test_cgroup_memory_max, test_physical_memory_unreadable_off_windows, test_memory_floor_edge (all three killed).

### witness.py (552: 382 killed, 141 survived, 29 uncovered under reused coverage)

**Correction (26 Oct 2026, review finding 26):** the argument below is false as stated. Two accepted candidates with different answers are a real witness only if the assignment is a possible input and the judged text is the formed claim; findings 01-08 of the full review broke each condition (fixed on v4-fixes; SPEC 4.4 item 12 lists them). The classification of survivors as "completeness only" rests on it and is not re-derived here; the brute-force measurement (tests/test_v4_bruteforce.py) is the end-to-end soundness check that was missing.

**Why most of these survivors cannot make nonsense form** (as written 25 Oct; see the correction above). The witness search only *proposes* inputs. Each candidate is evaluated by the real kernel and the real readers (on a MemStore), and only inputs the readers accept count. So two accepted inputs with different answers are always a real witness, however they were chosen. A mutant that changes the candidate set can therefore only:
- find fewer witnesses (a false S008/S011 on a sensible claim), or
- find more witnesses, or the same ones in another order. The chosen witness is never printed.

Neither lets an idle value form. These survivors are classed **SEARCH**: completeness only. Each one is a candidate a test claim did not need. They are not tested one by one, because every candidate the spec lists would need a claim that only that candidate can witness.

- SEARCH (candidate collection in Plan.__init__): 172, 177, 183, 187, 192, 198 (x7: an onset/duration row named by position, 1..100 000), 219, 220, 222, 223, 228, 229, 235, 244 (x3), 247, 249, 255, 265.
- SEARCH (candidate values and tables): 281, 285 (x3), 288 (x4), 292, 301 (x2), 321, 331 (x2), 346, 351 (x2), 353, 354, 356.
- SEARCH (candidate datasets, NIfTI sizes and raw sizes): 371, 372 (x7), 373 (x4), 424 (x4), 549, 563 (x2), 566, 568 (x2), 569 (x4), 577, 587, 762 (x4: which candidate is the base of the others).
- Tested (pure helpers; each kill checked by hand with no bytecode cache):
  - 85 (`_as_csv` quoting): test_as_csv_quotes_what_the_csv_reader_would_split.
  - 99, 101, 103 (`slot_of`, `ds_of`): test_slot_and_dataset_of_an_expression.
  - 125 (`rec_ents` acq/rec): test_recording_entities_as_the_kernel_reads_them.
  - 140, 149, 150, 152 (`dec_text`): test_dec_text.
  - 432 (the first `and -> or`), 434, 436, 441 (`json_chain`, including its 1..1000 item bound): test_json_chain. The second `and -> or` at 432 is EQUIV: a two-argument call that is neither member() nor item() returns None inside the loop, just as it does after the loop.
  - 471 (`_build` array padding): test_build_json_tree.
  - 513 (the `_shells` cap): test_interleave_and_shells.
  - 523, 532 (`_nii`): test_nii_header_fields.
- Tested (cost; the witness's steps are charged to the program):
  - 48 (NIfTI read charge): killed by test_kernel_charges_are_pinned (volumes).
  - 62 (text read charge): killed by test_kernel_charges_are_pinned.
  - 53 (bytes() slice charge): test_bytes_charge_in_the_witness_is_pinned.
- Tested (W2 key parts): 714 (x6), 715, 716 (x2): test_an_idle_key_part_refuses_w2. An idle key part of `cell(t, key(...), c)` refuses S008; a two-part key that bears forms.
- Tested (the witness budget): 777, 800 (`>` -> `>=`, R013 at exactly the budget): test_witness_budget_at_its_edge pins the least budget that forms (31 for `count(t)`, 318 for one where condition), and checks that one less refuses R013.
- 772 `> -> >=`: EQUIV. At the edge the mutant only skips adding the last evaluation's results; the check at 777 applies the same bound.
- 60 `> -> >=`: EQUIV in practice. No candidate is anywhere near MAX_TEXT_FILE; the largest is a table of at most 100 000 short rows.
- 122 `1 -> 0`: EQUIV (`bids(d)`, the extra first argument, is neither a Str nor acq/rec).
- 525 (x7): EQUIV (pixdim 0-3 and 5-7 of a candidate header are not read by any value v4 computes; pixdim[4], the time step, is not mutated here). 656 `0 -> 1`: EQUIV (the third field of a file binding is not read).
- 671 `0 -> 1`: unreachable. It is the budget charge after an internal error inside a witness evaluation, which is itself a bug path.
- 784 `and -> or`: a code choice. When a value never answers, the mutant says S011 where v4 says S008; both refuse. Not pinned.
- **788 `False -> True` and 807 `1 -> 0`: open, soundness-relevant.**
  - 788: W2 would pass a part when the first inputs give the statement no answer.
  - 807: W2 would pass a part when removing it leaves no well-formed value at any level.
  - Both need a statement whose first witness inputs refuse at the top. None of eight statements I tried distinguishes them (KNOWN-OPEN).
- 29 UNCOVERED (382, 409-415, 459, 469: `niftis()`, `jsons()` and `_build`'s branches): covered by tests the reused coverage did not record. Rerun with --no-coverage (totals below).

## Rerun against the tests at HEAD (26 Oct 2026, from 01:54 CET)

The rerun covers the survivors and uncovered sites of the first run (mutator's differential selection, `--no-coverage`, tools at mutation-v4/run-head.sh and batch-head.sh). It uses a git archive of the commit whose tests it runs; the source is unchanged since 03c5c2f.

### witness.py at a5a222e (170 sites rerun, 01:54-02:15 CET): 552 sites, 445 killed, 107 survived, 0 uncovered

The 107 survivors are all accounted for above, plus these:
- 409-415 (x17, `niftis()` candidate counts and steps) and 459 (`_build` rejecting a path through a raw value): SEARCH. These were uncovered under reused coverage.
- 48 `0 -> 1` (a NIfTI read counted as 1 byte of text) and 62 `+ -> -` (the accounted size of a text): EQUIV in effect. Both are off by a constant that no bound is near on the witness's small candidates; the step charges on the same lines are killed.
- 716 `1 -> 0`: EQUIV (`range(0, len(ka), 2)` and `range(0, len(ka) - 1, 2)` are the same for the even-length key argument lists that reach here).
- Every other survivor is one listed above as SEARCH, EQUIV, a code choice (784), unreachable (671), or open (788, 807).

### Final totals (rerun at HEAD's tests, a5a222e; ended 03:11 CET)

| module | sites | killed | survived | uncovered |
|---|---|---|---|---|
| keys | 24 | 24 | 0 | 0 |
| sorts | 26 | 26 | 0 | 0 |
| exact | 38 | 21 | 17 | 0 |
| __main__ | 30 | 29 | 1 | 0 |
| syntax | 205 | 192 | 13 | 0 |
| readers | 301 | 280 | 21 | 0 |
| bids101 | 404 | 341 | 63 | 0 |
| kernel | 574 | 512 | 62 | 0 |
| machine | 6 | 6 | 0 | 0 |
| witness | 552 | 445 | 107 | 0 |
| **total** | **2160** | **1876** | **284** | **0** |

The first run had 1,579 killed, 379 survived and 202 uncovered. Not classified yet: the 17 exact.py survivors and the 1 __main__.py survivor, which ran for the first time in the rerun (logs/head-exact.log, logs/head-__main__.log). The other survivors are classified above. test_differential is deselected in every mutant run.
