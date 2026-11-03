# Known and open in Reality v4

Recorded so that a review does not report them as new. A review may still argue that one is
judged wrongly, or that it changes a verdict or lets nonsense form.

## Deliberate expressiveness gaps (sense that cannot be said yet; not ambiguities)

1. **JSON `true`, `false`, `null`** refuse (J004) as a member or item value. Each has exactly one
   reading in RFC 8259; v4 simply has no sort for a boolean or an absent value yet (Patsak,
   25 Oct 21:36: keep refusing for now). A claim such as "SliceEncodingDirection is present" or
   "this flag is true" cannot be stated.
2. **`pixdim` is read along time only** (`pixdim(n, 4)`); spatial voxel sizes refuse S006 because
   millimetres are not among Reality's units (Patsak, 25 Oct 21:36).
3. **No `quantile()`** (Patsak, 25 Oct 21:14): there are several conventions; write the rank with
   `order(s, col, k)`. **No list cells** (`22,23` in one cell): no standard Reality reads defines
   splitting a cell.
4. **Bare `variance`, `sd`, `pvariance`, `psd`** refuse V009 (two conventions); write
   `sample_*`/`population_*`.

## Open work (STATUS.md has the order)

5. (Closed in Phase E/F: hits 5, 6, 7, 9, 10 and overcorrection 11 of the v3 Opus review now
   refuse or form as tests/repros/opus55max-v3/OPEN.md records.) 21a-i are recorded against the
   register in EXPECTED.tsv: eight refuse (B00, B14), 21d forms; no second reader has checked them.
6. (Since exact-decision phase 7, 28 Oct 2026, the search is deleted: part T is decided exactly and every other
   statement refuses S013, so this item is history.) The witness search was incomplete: when it found no two inputs on
   which a value differed, it refused, so a gap in the search refused a sensible claim. That it cannot make nonsense form is
   an argument with conditions, not a theorem (SPEC 4.4 item 12, review finding 26); the brute-force
   measurement (tests/test_v4_bruteforce.py) is evidence for one family, not a proof.
7. What the differential test shows (restated 26 Oct 2026, review finding 27). `src/reality4_ref`
   implements v3's plain-TSV fragment only (tsv rows count share(sel) where eq ne cell key header
   number sum mean max min widen difference exceeds below atleast atmost), by the same author, and
   loads v4's own confusables data. One file per program, small fixed vocabularies. So the test is
   evidence about that fragment's readers, computations and printing on one-file programs: 24 000
   programs, 66 193 lines agree, 3 308 formed (after taste call 5; 66 185 and 3 309 before). It is no evidence about CSV, JSON, NIfTI, size/bytes,
   BIDS, the variances and SDs, order, median, share(sel, base), ge/gt/le/lt, recordings, W1/W2,
   value identity, S012 by identity, or anything multi-file. The mutation runs deselect it.
   Lines counted apart: 3 367 (3 375 before taste call 5, which made 8 S012 lines both-V005), every one listed with its reason in tests/differential-carve-outs.tsv,
   which the test compares exactly (it fails if the set changes): 1 582 W1/W2/S012 refusals (55
   where the reference forms), 876 where both refuse with different codes, 856 lines of tables with
   mixed line ends (T010, not compared), 53 T011 uses of a BOM's first name (10 where the reference
   forms). The 65 lines where the reference forms and v4 refuses are the ones with a verdict
   difference: 48 were in the 21:20 hand audit (tests/witness-only-audit.txt, 80 lines then), the
   other 17 were audited on 26 Oct (LOG): all are idle by construction (a key column read back by
   cell(), a condition on a literal no cell holds, a sum of a column selected on a non-decimal) or
   T011/S012 by design. The other 3 302 carve-outs change no verdict (both refuse, or not compared).
8. The kernel's v3 idle rules (S008/S011) remain beside W1/W2, as the only idleness check for
   BIDS statements until the witness covers them (Phase E).
9. The K-factor test counts Python line events; work inside C builtins is not seen. It is linear
   in bytes already charged except for big-number arithmetic, which is now charged by size (SPEC 9.1,
   review finding 22) and checked by time per step (test_r22_*), a wall-clock test with a 6x margin. The AST lint for uncharged loops (tests/test_v4_loops.py, 25 Oct 22:36) is coarse: a function
   that charges anything passes all its loops, and each listed reason is the author's reading.
   Until the fix pass (26 Oct 2026, R6) any `.add(` counted as a charge, so a `set.add` hid
   parse_manifest's quadratic folder loop (Argon R6, O11); now only the step meter's `.add(`,
   `._cached(` and `.measured(` count, and the seven functions that had passed through a `set.add`
   were reviewed: parse_manifest now charges; number_uses, _check, Store.__init__, witness
   subexprs/go/__init__ are listed with their bounds. Still open: one charge in a function passes
   every loop in it, whatever its size.
10. No self-contained specification (review finding 29, 26 Oct 2026). SPEC.md is written against
   v3/SPEC.md §9 and promised a merged text as a Phase G deliverable; it was not written. An
   independent checker would have to read both files and resolve the overrides itself.
11. No choice-point lint or flip test (finding 29). DESIGN §2.2 item 4 describes a test that walks
   the BIDS reader for name/metadata branches outside a decision and a test that flips each choice
   point; neither exists. A missed choice point is found only by reading the register.
12. The [prov] numbers were never measured or fixed (finding 29): the 64 row types, the 16/4/8/6
   table limits, MAX_REAL = 1 MiB, the R013 statement bound and the W²/16 big-number charge (SPEC
   4.4, 8, 9.1) are the author's choices; each is pinned by tests, none by a measurement. Since exact-decision
   phase 3 two more: MAX_ROWS = 100,000 (rows of one table in a certificate input; a claim whose smallest witness
   is larger refuses R013, D3) and MAX_CASES = 10,000 (cases of the rows one question names, SPEC-EXACT 3.4; more
   refuses R013). The search's limits (64 row types, the table limits, MAX_REAL) went with the search in phase 7
   (28 Oct 2026); these two stay.
13. Principle §4.1 vs register S0280 (finding 29). The principle's §4.1 table lists "a task-based
   BOLD run must have an events file" among the rules the reader implements; register S0280 marks
   that sentence `unshowable` (whether a scan is task-based is a fact of the experiment), so a
   BOLD file without an events file does not refuse. The register is what the code does; the
   principle's row overstates it, and nothing recorded the change until now. The principle file is
   not edited here.
14. Which commit was checked where (finding 29). ACCEPTANCE.md was made at 82e2911 and regenerated on
   v4-fixes (its header says which). The real ds001734 run on the PC (Phase H) used abad0e4. Every
   later commit (v4-fixes, including the B30 SliceTiming rule of finding 11) is checked on the box
   only, against the fabricated copies; ds001734 forming at the current commit is argued from its
   header facts (LOG), not re-run.

## Copied reproducers that now stop at B01 (no README), 25 Oct 2026 21:58 CET
Taste call 2 (a root README "should be provided" binds) makes every copied review dataset without
a README refuse B01 before the line's own point. The copies are left byte-identical (their
manifests and programs name their bytes). Lines whose point is lost this way, and where it is
tested instead: argon 02 line 4, argon 13, argon 18, argon-extra fx/e2, fx/e11, fx/e12 (not
re-tested yet); opus55 12-nifti2 (test_expressions::test_nifti2_tr_is_read_as_float64); opus55max
03-onset (test_repros::test_hit08), 05-manifest-selection line 4, 12-phenotype-b (test_hit14), 20,
23 (not re-tested yet); opus55max-v3 21a (now refuses, as call 2 says). Phase G (25 Oct, 23:24):
the untested ones are rebuilt in code in tests/test_repros_b01.py (each dataset copied with a
README, its manifest rewritten, the program's hash replaced) and reach their own point: argon 02
(the idle let changes nothing), argon 13 (acq names the acquisition, both form 10 volumes), argon 18
(U004 without the unit; with it, "holds of the recorded value", call 6), argon-extra e2 (K003),
e11 (0.72 s from ms units), e12 (1.5e-2 reads as 0.015 s), opus55max 05 (line 4 forms; the
selections refuse B11 and B12), 20 (run 1's onset 1.5 s), 23 (NIfTI-2 TR 0.8 s forms).

## A folder sub-<bad label> is an extra file (25 Oct 2026, Phase G; closed 26 Oct 2026 by Patsak's ruling)
`sub-a_b/func/sub-a_b_task-x_bold.nii` was classed extra (the folder is not a subject folder), so
the dataset formed with it ignored; tests/test_v4_mutation.py pinned only that it is not a subject.
**Overruled by Patsak (26 Oct 2026):** a file under a `sub-<label>` folder whose label is not letters
and digits refuses B17, citing S0628 ("hyphens and underscores are not allowed in subject labels"),
as the register's `checked B17` says (fix pass R5; Argon found `sub-02-bad/` and `sub-03_bad/`
skipped; test_v4_fixpass::test_r5_*). A top-level folder not starting with `sub-` is still extra.

## Register (Phase E, 25 Oct 2026)
- The 633 classes are one reader's reading of 1.0.1 (tools/fill_register.py); they have not been
  reviewed by a second reader. Most `unshowable` rows are recommended keys whose values describe
  the scanner; `reality-call` rows are mostly encouragements that call 2 does not bind.
- SPEC 8.2's lint ("a branch on names, entities or metadata outside a decision fails") is not
  built. test_v4_register.py checks citations and choice points only.

## CSV line breaks inside quotes (25 Oct 2026)
A CSV line break inside quotes is refused (T008) although RFC 4180 allows it (Patsak kept this,
22:29). TSV and CSV now both refuse mixed line ends (T010).

## Refusal texts named "Reality v3" (25 Oct 2026; fixed 26 Oct 2026, finding 29)
The nine refusal messages now say "Reality v4", and V001 says "above / below / at least / at most"
instead of "is exceeds". Output change, messages only: the snapshot differs only in those words
(LOG, finding 29).

## Float32 ties in tr_consistent are not tested

Mutation survivors at bids101.py 164-175 (the round-half-to-even step of `nearest` for float32) are not killed: a test needs a RepetitionTime that lies exactly half-way between two float32 values. The code follows IEEE 754 round-to-nearest-even; no test pins it.

## Two W2 mutants are not killed (Phase G mutation run)
witness.py 788 (`found = False -> True`) and 807 (`bad[1] -> bad[0]`) survive. Either one would let W2 pass a removable part in a corner case: when the statement has no answer on the first inputs tried, or when removing the part leaves no well-formed value at any level. No test statement reaches that corner, and I have not found one that does. The rest of the witness survivors only change which inputs are proposed, which cannot make an idle value form (tools/mutation/REPORT.md).

## The memory floor is measured for tables and selections, not for every structure (v4-fixes 04)
Opus 5.5 v4 finding 04. Fixed: the witness passes MemoryError and RecursionError on as no verdict; a kept selection is charged 72 bytes per row; a plain TSV table refuses R012 before it is built when its cells alone would pass the bound; the floor reads RLIMIT_DATA and every ancestor cgroup. Measured on the box at the bound (1 GiB accounted): 14 selections of 10^6 rows peak at 657 MB RSS; a 64 MB TSV of 1000-column rows now refuses before parsing (159 MB peak; it was 589 MB). Corrected (Argon review 08, unit A08): "neither is known to pass 2 GiB" was wrong: Argon's two JSON files (m1, m2) peaked at 2,575 MB RSS (the memo kept the first) and a CSV of short fields at 2,968 MB, past the 2.0625 GiB floor. Since A08 a TSV/CSV/BIDS table is room()-checked at its size so far as each row is built, so a CSV no longer waits until it is built (no lower bound on its cells is needed); JSON is checked before parsing; the memo is dropped at each program. Measured on the box (argon-repro/mem/A08-mem.txt): m1 and m2 1,308 MB; the CSV R012 at 1,677 MB; TSV R012 at 989 / 1,495 MB. Still open: the witness's own candidate tables are not measured at the bound.

## Finding 11 (SliceTiming axis): decided 26 Oct 12:00 CET, no longer open
Opus 5.5 v4 finding 11 proposes B30 unless the slice axis is fixed by the bytes (all three axes agree, or SliceEncodingDirection / dim_info say which). Header-only read on the Windows PC, 26 Oct 2026 about 10:40 CET: 432 BOLD headers, all 106x106x64x453; 113 have dim_info 48 (slice_dim 3, the k axis), 319 have dim_info 0 (slice_dim not given); no JSON in the dataset has SliceEncodingDirection; the only SliceTiming is the root task-MGT_bold.json (64 entries, matching k only). Under the proposed rule those 319 runs would refuse B30 (i and j have 106 slices, k has 64), so real ds001734 would stop forming. Options for Patsak: (a) leave as is: with the axis not fixed, v4 accepts a SliceTiming whose length fits any axis (ds001734 forms; the finding's repro, 2 times on a 2x3x4 image, also forms); (b) take k as the slice axis when nothing fixes it, and B30 when the length fits another axis but not k (ds001734 forms: 64 fits k; the repro refuses); (c) the finding's rule, B30 unless all three axes give the same result (ds001734 refuses, the 319 runs above). BB leans (b); not applied, as instructed. Finding 11 has no regression test and no code change on v4-fixes.

**Decided (BB's call on Patsak's behalf, 2026-10-26, reversible):** the 1.0.1 silence algorithm, since S0369 names no default axis: the named axis (SliceEncodingDirection or slice_dim) if any, else the one axis the length fits; B30 when it fits several with none named. Not options (a)-(c) above. ds001734 forms. See DESIGN, v4-fixes 11.

## The nested spelling of a share within a subset refuses (v4-fixes 13): decided 26 Oct 2026, no longer open
`share(where(where(t, ne("group", "P")), eq("group", "A")), where(t, ne("group", "P")))` refuses S008 on the inner condition: W2 removes it from sel only, and the share without it refuses S006, so it is judged one level down, where the outer condition implies it. The flat spelling forms (BB's call 13).

**Decided (BB's call D4 on Patsak's behalf, 2026-10-26, reversible; branch exact-decision):** it stays refused, because the inner condition is the base's condition said a second time and Reality keeps one spelling per meaning (calls 02 and 13). The S008 message now names the flat spelling that forms. See DESIGN §10.1; tests/test_d4_nested_share.py.

## The real NIfTI header is not a witness candidate (v4-fixes 16)
16 adds headers varying each spatial axis, but the real file's own header is not offered as a candidate the way the real bytes of a table are (14). A claim that holds only for an unusual combination of header fields not covered by the generated headers can still refuse S011. Adding it costs a header read per slot inside the witness budget; not done to stay under the 4,250 cap.

## The memory floor on Windows (26 Oct 2026, v4-fixes)
Until 26 Oct 2026 the floor read only total physical memory on Windows, so a checker run inside a Windows job object
with a process or job memory limit below M (the Windows counterpart of RLIMIT_AS or cgroup memory.max) still gave
verdicts. `machine._physical` now also reads the job object's JOB_OBJECT_LIMIT_PROCESS_MEMORY and
JOB_OBJECT_LIMIT_JOB_MEMORY (test_v4_cli::test_below_memory_floor_in_a_windows_job: X002 at 1 GiB, a verdict at 3 GiB).
Still open: only the process's immediate job is read; a limit set on a parent job of a nested job is not (Windows
has no public call that walks up the job chain). The working-set limit (JOB_OBJECT_LIMIT_WORKINGSET) is not read:
it pages memory out rather than refusing it. Commit limits (page file) are not read; they are at least physical memory.

## The exact decision of part T (exact-decision phase 3 checkpoint, 27 Oct 2026)
What part T's exact path rests on and does not prove (SPEC-EXACT; plans/CHECKPOINT-3.md):
- Readable inputs of a table slot are defined to have every column the statement reads (SPEC-EXACT 2). A table that
  lacks one makes every value reading it refuse V002, and that is not counted as a change of outcome; otherwise a
  condition on the highest column would always "bear" through V002. The search had the same input space. It is a
  definition; asked of BB at the checkpoint.
- The cases of named rows (SPEC-EXACT 3.4) have no Lean proof. The elimination of named cell values (4.1,
  Fourier-Motzkin over Q with strictness) is proved since phase 4 (Exact.Q.elim_step, elim_correct, elim_nat; the
  passage to integer atoms Q.atom_scale, Q.atom_int); that the Python `fm` computes Lean's `elim` is a reviewed
  correspondence (same atoms, same order), not a proof. Both are tested: tools/exact_bf2.py
  re-checks every exact refusal on the generated family partT2 by brute force (88 refusals, 0 contradicted) and every
  "yes" is confirmed on real bytes.
- The decimal argument of 4.1 (at most one non-strict atom with a named cell value in any system) is on paper.
- Reader facts H1 and H2 are probed (tools/exact_h1.py, 1,006,824 probes, 0 counterexamples), not proved.
- The share point test of SPEC-EXACT 5.4 adds at most two rows to a solution within MAX_ROWS; a certificate can
  then be up to two rows over the bound. It is still a real input checked by the real code; only the R013 edge moves.

## Part N (exact-decision phase 4 checkpoint, 27 Oct 2026)
- One column both summed and ordered in one statement is decided since Part B item (e2) (27-28 Oct 2026, SPEC-EXACT
  3.5): the 10 partN statements of that shape leave the search. On the committed code (frozen copy /tmp/srcE2g, 3 GB
  address-space limit, partb/Ee2/e2-g10.txt): pn450 forms in 293.3 s (= 13.5, Exact), pn349 in 32.9 s, pn300 in
  24.2 s, the other seven in at most 5.7 s; pn319 S008 W1, pn574 S008 W2. pn300 once measured 17.9 s on an earlier WIP
  (partb/Ee2/e2-new.txt); no saved WIP (22:30-23:39) reproduces it under any hash seed: not explained. The 385-475 s
  timings of pn300 and pn349 logged on 27-28 Oct were taken with runners (partb/Ee2/ten.py, one.py) that loaded the
  live v4/src whatever SRC they were given (tools/exact_diff.py puts v4/src first on sys.path), so they timed whatever
  the live tree held then, not the variant named: void. Fixed runners (ten2.py, inst2.py) assert that SRC's reality4
  is the one imported.
  Brute force partb/Ee2/bfe{1-4}.txt on /tmp/srcE2g (random sums, means and order statistics of one column in
  differences, comparisons and widen on a 4-row table; each exact W1 refusal re-checked over all 11,110 tables of 1-4
  rows of a 10-value grid by the real kernel): seed 4 complete (150 claims, 0 to the search, 8 W1 refusals re-checked,
  5,114 s); at 28 Oct 03:52 CET seeds 1-3 had completed 60, 125 and 46 claims (381 claims in all): 0 contradicted,
  0 X001, 0 R013; seeds 1-3 still running (the W1 re-checks are the cost).
  Two claims that refused R013 on earlier WIPs no longer do: `atleast(difference(mean(where(t, le("x", c = 1)), 2),
  min(t, 2)), c = 0)` (R013 at MAX_CASES after 25.6 s before the charge guard; now a W1 refusal, being re-checked) and
  `exceeds(difference(max(where(t, gt("x", c = 0.4)), 2), mean(where(t, eq("g", "B"), ge("x", c = 0.5)), 2)), c = 0)`
  (always fails: the mean's rows are above 0.4; R013 after 564.6 s when the charge guard turned find()'s scheduling cap
  into a refusal, 226 s with the old two-row pass; now S008 W2 in 62.5 s). Before (e2) the old search refused a median
  and a mean of one column S008 W1 falsely (partb/Ee/bfm4), and refused pn349, pn450, pn534 and pn578 S008 where the exact path now
  forms with checked certificates. The elimination and the relaxation are charged before their work since (e2)
  (SPEC-EXACT 8): pn450's 236 atoms in 51 rational values eliminate to 83,093 atoms, and its relaxation took 13 GB
  before it was charged.
- A mean inside a difference is decided since Part B item (e1) (27 Oct 2026, SPEC-EXACT 3.5): the 19
  partN statements of that shape decide on the exact path in at most 3.3 s each, with the search's 18 verdicts kept and
  pn404 now formed (the search said S008 "could not find"; the exact path finds and confirms a certificate)
  (partb/Ee/e1-ends.txt). Its cost is open: brute force partb/Ee/bfm1,2,4.txt (random means in differences on a 4-row
  table; seeds 1, 2, 4 complete, 750 claims; seed 3 stopped part way, bfm3.txt) found R013 on 2 of the 750, and seed 3's
  partial run on 1 more; brute force does not check R013 claims. Two refuse at MAX_CASES after 200-204 s
  (`atleast(difference(mean(where(t, gt("x", c = 0.4)), 2), mean(where(t, le("x", c = 1)), 2)), c = 0)` and
  `atleast(difference(mean(where(t, eq("g", "B"), ge("x", c = 0.5)), 2), mean(where(t, gt("x", c = 0.4)), 2)), c = 0)`;
  W1 there is answered in 0.01 s, the cost is the W2 questions, many systems whose answer is "none", each exhausting
  21-165 cases of N), one at the step bound after 528 s (`atmost(difference(mean(where(t, le("x", c = 1)), 2),
  number(cell(t, 1, 2))), c = 1)`, "checking its certificates"). Re-measured on (e2)'s code (8f646db, 28 Oct
  2026, partb/Ee2/r13-e1-g.txt, same 4-row table): the second forms (holds) in 49.0 s and the third in 0.3 s; the
  first still refuses R013 at MAX_CASES, after 104.7 s. That one is the wrong refusal, not only a slow one: the comparison
  never fails (the rows above 0.4 average at least the mean of the rows in (0.4, 1], and the rows at most 1 average at
  most it), so by 5.1 it must refuse S008 W1. The relaxation does not see it: proving "no input fails" needs that a
  mean lies between the means of its present types, which the model had no variable for. Closed 28 Oct 2026 by Part B item (pm): for two means of one column whose rows share types without either holding the other's, the shared types' mean is a variable with nest's cases for each (caps, SPEC-EXACT 3.5): S008 W1, decided exactly, in 0.2 s (partb/Pm/probe1.txt). The same item found and fixed a wrong refusal: nest() matched two means by their row counts only, so a mean of column 2 and a mean of column 3 over the same rows were compared as one column's; `atmost(difference(mean(where(t, ge("y", c = 0.5)), 2), mean(where(t, ge("y", c = 0.5), gt("x", c = 0.4)), 3)), c = 0)` refused S008 W1 on 627191a though its value is -1 on the 4-row table and 1.5 on the one row `B 2 0.5` (partb/Pm/nestcol.txt; since e5558c9; the bfm grids hold no row that shows it); it forms in 0.2 s now. Split up front, the caps' cases made a claim that formed in 2.9 s on 627191a refuse R013 at MAX_CASES (228.8 s, bfp seed 1); they are split only where a solution breaking S = mu·N admits no shared mean (cap_ok), and it forms in 2.6 s (partb/Pm/r13-bfp1a-*.txt, probe2.txt). Brute force partb/Pm/bfp.py (means of columns 2 and 3 with selections on x and y; W1 refusals and R013s re-checked by the kernel, its W1/W2 step skipped, over all 1-2 row tables of a 40-row grid and 10,000 fixed 3-4 row tables), partial at commit: seed 1 claims 0-89 and seed 2 claims 0-42 complete, 0 contradicted, 0 X001. One R013 (seed 2): `below(difference(mean(where(t, ge("y", c = 0.5), gt("x", c = 0.4)), 2), mean(where(t, ge("x", c = 1)), 2)), c = 2)` at MAX_CASES after 54.6-55.8 s; it does not hold on every input (499.5 on the rows B 1000 1, A 1 0; no grid row is that large), so it is a stopped witness search, not a wrong code; the same on 627191a (56.9 s). Seed 1's claim 90 (`below(difference(max(S, 3), mean(S, 3)), c = 0.5)`, S = where(t, lt("y", c = 1), le("x", c = 1)), one column summed and ordered, (e2)'s code path unchanged by (pm)) had run in W1's relaxation (lp) for more than 22 minutes without reaching the step bound at commit: a cost of (e2), open. Also from that run: one false S008 W1 refusal by the
  old search on a column both summed and ordered (a median and a mean of one column), the shape (e2) is to take off the
  search. (Named rows with a variance of the same table: closed 27 Oct 2026, Part B (d): no
  statement can say it, SPEC-EXACT 3.7, last paragraph; the unreachable gate is removed.) Named rows with the other aggregates of their table are decided since item 6 (d)
  (27 Oct 2026, SPEC-EXACT 3.5; brute force partb/Ed/bfn.txt: 0 contradicted, 0 X001).
- MAX_CASES = 10,000 [prov] refused R013 on a generated statement the search formed (partN pn535: two sums with 8
  summed types of interval classes, 49,152 cases). Since Part B item 8 (27 Oct 2026) whether a summed type has rows
  is not a case but split only where a solution needs it (SPEC-EXACT 3.5): pn535 forms (= 19, as under the search)
  with 192 cases; a statement whose solutions keep breaking types still refuses R013 past MAX_CASES systems.
- Not in Lean: the cases of 3.5, the presolve and the relaxation of SPEC-EXACT 4.1/4.2 (the relaxation's answers are
  checked: a Farkas certificate for "no", an integral vertex satisfying every atom for "yes"), the means' point test.
- On the generated part-N family the exact path is slower than the search (39 s vs 11 s for 600 programs).

## Part H (exact-decision phase 5 checkpoint, 27 Oct 2026)
- `pixdim(n, 4)` is decided exactly since Part B item (f) (27 Oct 2026, SPEC-EXACT 3.6: float64 values times the time
  unit, float ranges split down to one binade). Its cost is open: a statement whose answer is "no" only because no two
  floats fit a fine window walks many float ranges. Measured on the box (27 Oct 2026, partb/Fd/hard-final.txt):
  `exceeds(widen(difference(pixdim(nifti(n), 4), pixdim(nifti(m), 4)), tolerance = 10^-45 s), c = 0.4285714285714285714285714285714285 s)`
  (two slots, nine unit cases with a time unit) refuses R013 "more than 50,000,000 counted steps" after 136.9 s, and
  143.4 s on a re-run at commit (partb/Fd/hard-2035.txt). Its real answer holds; the question that does not finish is,
  by our reading, an input whose window straddles the cutoff: within 10^-45 of a 34-digit cutoff the differences of two
  floats times the unit factors (spacing near 10^-17 at 0.43, near 10^-33 for the second float) seem to leave no
  point, so every float range is walked down. An earlier profile put 97% of the time in the rational relaxation (lp,
  on lattice coefficients near 2^2000); lp now keeps its reduced-cost row (4,181 systems against the old lp: 0 differ,
  partb/Fd/lpcmp.txt) and integer bounds are propagated first, which took it from more than 300 s to about 140 s.
  A real-number relaxation for ranges wider than 64 binades was tried and was slower (279 s, R013). With cutoff 0.3
  the same window forms in 0.2 s. **Closed 28 Oct 2026 (fwin, SPEC-EXACT 3.6): that R013 was a wrong code.** An exact count
  of the float pairs (partb/X1/pixwin.py, every smaller exponent, gap and order for the nine unit pairs, s/ms/us,
  validated on windows built around random float pairs: 0 missed) finds no pair whose difference lies within
  10^-45 s of 0.4285714285714285714285714285714285 s (closed window; partb/X1/pixwin-hard.txt), so widen() bears
  on no input: the statement now refuses S008 W2, decided exactly, in about 5 s (partb/X1/hard-fwin1.txt); with c =
  0.3 s (300 ms − 0 lands on it) it forms in 0.1 s. Still open here: three or more floats, or one float in two
  forms, are walked by ranges as before and may refuse R013 at the step bound; whether any such statement's R013
  is a wrong code is not known. Also not modelled: number()
  of bytes() or of a JSON string, a file read by two kinds of reader in one statement (since the slot shapes, 28 Oct
  2026, except csv() with rows(tsv()) and nifti() dims with size(), SPEC-EXACT 3.10), look-alike keys named under one
  JSON object. In 3.10 a certificate's gzip NIfTI file is its own level-9 member (52 to about 60 bytes) and zero
  padding: a statement whose answer needs a NIfTI file of 19 bytes up to that refuses R013 (a stated bound).
- A raw file's size was bounded by MAX_ROWS (100,000 bytes) in the bounded system; since Part B item 7 (27 Oct 2026)
  it is bounded only by an off_t (2^63 - 1) and decided arithmetically (SPEC-EXACT 3.6).
- Part B P1 (27 Oct 2026): the model now holds only numbers the reader reads (SPEC-EXACT 3.1). Its one incompleteness:
  back-substitution picks each eliminated value in turn, and a system whose region holds rationals but, after those
  picks, no readable point (ends closer than 10^-999 apart at magnitude 1, say) refuses R013 instead of being decided.
  Call 2 (27 Oct 2026) replaces that refusal for read values and summed columns by an exact search over R's bands
  (SPEC-EXACT 3.1): R013 there now means only "more than MAX_CASES cases or 50,000,000 counted steps", the integer
  step's calls charged in 64-bit words of their largest coefficient. Still open: (1) that search is slow where
  1000-digit cutoffs meet 10^900-sized ones, because the integer step's branches grow with its coefficients (a
  fuzz statement below(sum(where(t, ge(x, c = 3·10^-999))), c = 10^900 + 10^-98), plainly true on two rows, refuses
  R013 at the step bound after about 50 s; since call 2b (27 Oct 2026) the integer step enumerates a variable with a small
  explicit range (SPEC-EXACT 4 rule 7a, Exact.enum_rule), which takes it to 23 s, still R013: the summed column's
  parts are cut by halving bands 13 deep, and the last system, 36 variables with coefficients near 10^3998, is not
  decided in 3,000,000 calls (79 s) either way; the statement needs rows in two bands 10^998 apart, which halving
  reaches only after about 24 cuts. Closed by item (g) (27 Oct 2026, SPEC-EXACT 6, order of the work): the options are
  solved in rounds under a growing step cap, with a pass of row counts of at most two rows after the first round; the
  statement forms in about 6 s (tests/test_partB.py test_g_claim3_probe_forms). A statement whose only witnesses need
  three or more rows still meets the slow search); (2) closed by call 3 (27 Oct 2026): rows of an ordered column strictly between two order
  statistics whose gap holds no readable number are split by cases (no rows there; or rows, with the lower end's band
  split as call 2 does and the upper end above the next readable number), so Model.type_rows no longer meets such a gap.
- The H3 probes (tools/exact_h3.py, 659 probes, 0 counterexamples) cover NIfTI headers, JSON kinds two levels deep and
  the spelled numbers, and raw sizes and slices; they are probes, not a proof.

## Part V (exact-decision variance phase checkpoint, 27 Oct 2026)
- The variance shape (28 Oct 2026, SPEC-EXACT 3.7): three or more signed variances of one table, or two with a widen()
  inside, are decided by bounds (per column a·Vs + b·Vp) and the 5b multiset search; a piece the bounds do not exclude
  and no multiset of MAX_CASES reaches refuses R013 (a stopped search over a subset of the domain, not over all of
  it). Over a selection (where()) or two tables the shape is NotT (S013 since phase 7).
- A difference of two variances (item 5b, 27 Oct 2026, SPEC-EXACT 3.7) is decided except where the pieces meet the
  values' range [−sup2, sup1] and neither the shortcuts (equal variances, sample minus population of one selection,
  the uncoupled ends) nor the finite-domain search of MAX_CASES multisets (three readable values per class) finds a
  witness: it refuses R013. For coupled selections this is the common way a never-failing comparison refuses
  (the range test is the only proof of "no input" there, apart from the two shortcuts), e.g. a comparison that holds
  on every input only because one selection contains the other. This R013 is a search that stops over a subset of
  the domain, not a measured bound over all of it: open (brute force partb/Ec: 0 contradicted). Narrowed by item (h)
  (27 Oct 2026): coupled pieces over an unbounded column (partb/Ec's R013 claims) form, because a multiset of the
  sign of a piece is scaled into it (V1 − V2 is homogeneous of degree 2) and rows read alike are one item; the
  "no input" side (a never-failing coupled comparison) is unchanged: still R013, a stopped search. **Re-classified 28 Oct 2026:** the one
  brute-force instance cited for that side (bfc seed 7, `below(widen(difference(sample_variance(t, 3),
  population_variance(where(t, ge("x", c = 0.25), le("x", c = 0.75)), 2)), tolerance = 0.01), c = 0.3)`, R013 at
  MAX_CASES in 12.6 s on f6661b1) is not never-failing: on the rows (A 0.5 0), (A 0.5 0.77) its value lies in [0.28645,
  0.30645] (V006), so widen() bears on the answer (partb/X1/bfc7-classify.txt). Its R013 was a search that missed a
  2-row witness because it scaled both columns together; one column is now scaled alone too (SPEC-EXACT 3.7), and it
  forms (holds) in 0.1 s (test_one_column_scaled_alone_finds_the_coupled_witness). No instance of a coupled
  comparison that holds on every input and refuses R013 is known now; the multiset search is still over a subset of
  the domain, so one may exist. **Instances found 29 Oct 2026** (the sibling hunt, partb/S13/s7/sibs2.py): 29 claims of
  two variances of one file whose selections differ only by rows that make one of them refuse (e.g.
  `below(difference(population_variance(where(csv(f), ne(1, "")), 1), sample_variance(csv(f), 1)), c = 1)`: on every
  answering input the rows are numeric, the where() is idle and the value is -Vs/n <= 0) refused R013 at 08a879a and
  a9b3a16 though each holds on every input (ground truth: one answer on every table of up to 3 rows). Since 3f9a83c
  (3.13g (b): d_hit and vranges compare selections without the types the cases give no row) all 29 are S008 W1 with a
  checked range certificate, re-checked by ground truth; no other verdict of the 900 moved.
- Under `widen` (item 5a, 27 Oct 2026, SPEC-EXACT 3.7) it is decided except in one case: when the pieces K where a
  widen() changes a comparison's answer meet (0, sup) but no two rows of the classes and no multiset of the classes'
  readable ends (at most MAX_CASES) have a variance in K, it refuses R013. Such a K is narrower than the spacing two
  rows reach (about 10^-999 of the value) or lies in a gap between classes; it needs three or more rows with values
  inside a class, which the search does not enumerate. This is a search that stops, not a measured work bound: open.
  Narrowed by item (h) (27 Oct 2026): every count of rows of the classes' two ends up to MAX_ROWS (and 64 MiB of
  table) is now tried exactly, and a K below the least positive variance MAX_ROWS rows reach refuses R013 with that
  shown (every witness has more rows). On a fuzz of one-band grids (partb/Eh/fz2.py, 150 claims at 10^502) the R013s
  went from 6 in 94 to 0 in 150, each now formed, no other verdict changed. Still open: a K that no two-value input
  of the ends reaches but three distinct values do (or none do) refuses R013 as a stopped search. Deciding it exactly
  is a bounded quadratic Diophantine question (is n·Σk² − (Σk)² in an interval, for integers k in the class's grid
  and n <= MAX_ROWS), for which there is no procedure here short of enumerating multisets. **Narrowed 28 Oct 2026
  (the no-input sub-case, a wrong code):** a class of at most 64 readable numbers now gives all of them to the
  multisets, and when every class does, a K above the largest variance of more rows than the multisets have tried
  (⌊n/2⌋⌈n/2⌉(U − L)²/(n(n − d))) is shown to meet no input: S008 W2 (SPEC-EXACT 3.7). Trigger partb/W5a/gap.py: two
  readable values whose sample variances skip (1/3, 1/2)·step², R013 in 12.7 s, now S008 W2 in 0.2 s; brute force
  partb/W5a/bf5a.py against ground truth. Still open, a stopped search: population variances (the bound is the sup at
  every even n, so it never falls below a piece) and windows low enough that many rows reach them, over classes
  of few values; and any K over a class of more than 64 readable values that two rows, two values and the multisets
  of the ends miss. Whether a K there meets no input is not decided: in that case R013 is a wrong code.
- Found while building item (h); fixed at F02 (d9aadf0, 29 Oct 2026). This line said a certificate past 64 MiB (MAX_TEXT_FILE)
  would give X001 and that no statement had been seen reaching it. That was wrong: the Opus 5.5 review (finding 02)
  reached it. `below(count(where(tsv(f), eq(1, L))), c = 99999)` with a 700-byte L gave X001, and the read limit was
  applied in the size shape (3.12a) and in item (h) but not in rows() (R013 where every readable input agrees).
  Since F02 the readable inputs are bounded in every shape (SPEC-EXACT 1). The 700-byte case and rows() past
  33554431 now refuse S008 W1 "it holds only by the read limit", as does the six-read text-total case
  (tests/test_exact_decide.py, F02 tests). Still R013: a failing input that is readable but has more than
  MAX_ROWS rows.
- Not in Lean: 3.7's W1 rule, its refusal argument for W2, the attainment rule at points, and the identity between the
  kernel's variance formula and Lean's `var` (algebra on paper); the bounds themselves are proved (Exact.Var).
## BIDS in the exact model (Part B items 2b, 2c, 3, 4, 28 Oct 2026)

- participants(bids(d)) is a table slot (SPEC-EXACT 2), column 1 (participant_id) read by eq/ne, participant() and
  extra() since item 4. Not modelled (NotT; S013 since phase 7, 28 Oct 2026): column 1 read as a number or a
  cell, two look-alike column-1 literals, recordings() and a named recording of one dataset in one statement, a
  participant and a recording label that look alike, trials() of recordings with a filter on column 1. participants()
  or participant() beside a named recording: decided since 422aa41 (3.8b; the recording's subject has its row, B11). The old search was wrong on two such statements
  (count(where(t, ne(1, "sub-w1"))) S011, the eq() one S008 W2; both form: test_participant_id_and_extra_are_decided_exactly).
- A named recording's values (SPEC-EXACT 3.8, items 2c, 3): onset together with both tr and volumes of one recording
  (onset < volumes x tr is bilinear; no statement can hold all three without a unit refusal, U001, since volumes is a
  count and the others times), two look-alike trial types of one recording: NotT. Two named recordings one of whose
  labels are within the other's: decided since 3d75053 (3.8a; the inherited sidecar is overridden by the other's own). A certificate's events file holds
  at most MAX_ROWS rows (else R013).
- Recording sets (SPEC-EXACT 3.9, items R1, R2; 3.9a): two quantities of one dataset, decided since 7e80704 when they read
  different files of a recording (volumes beside events or trials of a type; sums and counts), and since e744687 when both
  read the events file (events beside trials of a type, two trial types; 3.9b: a state per events-file class, events >=
  the read types' trials; look-alike trial types NotT). Some such statements over three filtered sets stop at a bound
  (R013; ground truth partb/S13/s6b: 3 and 7 of 150 at seeds 12, 13 before c486b82's order model (3.9c), 1 and 3 after, now at
  MAX_CASES; none holding on every input). Still NotT for tr beside another quantity (tr() reads the image
  header too, B09; tr cannot meet a count, U001), and for a mean, min or max of two quantities; a mean with another
  recordings() set in one statement, a min or max beside other sets except as 3.9e (since a67c0a0: a sum beside a max or min
  of one task's recordings, its count read nowhere else; still NotT: a count beside them, tr, a min of volumes, max and min together), a mean of recordings inside a difference, trials over regions of three or more tasks (two: decided since 3d78d9d, 3.9d; three
  regions over two tasks stop at MAX_CASES, R013), trials of two tasks beside another quantity or with a participant_id filter,
  trials() with a filter reading participant_id (column 1, item 4): NotT. With two refusing kinds (trials) R1's cases ordered the regions
  and each region's kinds (R! x 2^R orders); since c486b82 (3.9c) a case is an order with one branch per view, the least by
  inclusion kept (the same union, so the same verdicts). A certificate holds at most MAX_VOL volumes and MAX_ROWS events in all: e.g.
  atmost(sum(recordings(b, "x"), "volumes"), c = 10^9) refuses R013 though readable datasets failing it exist.
- NotT since phase 7 refuses S013 (SPEC-EXACT 2, D5): no statement of the suite or of the corpora reached it at the
  deletion (censuses partb/Cen). Item 4 (28 Oct 2026, ITEM4.md) builds the eight probed shapes one by one. Shape 3,
  number(bytes(f, o, n)), is decided since 116c6a5 (SPEC-EXACT 3.11). Still S013 there: two different number()-read ranges of one
  file that overlap (their joint spellings are not the product of each range's numbers; a split on the shared bytes
  is not built). A spelling refusing R007 is no readable input, as for a cell. Shape 2, size(f) of a table, is decided
  in a first cut since 6c4608a (SPEC-EXACT 3.12). Since fa4ac1c (SPEC-EXACT 3.12a, 3.12b) every number of tsv()/csv()
  calls is decided (each call charges the table's size to MAX_TEXT_TOTAL: one atom per statement), and a one-column
  table with an empty literal is decided by its two layouts (a checked 'layout' split). Still S013 there: the table's
  cells, header names or numbers read (the least spelling then depends on the value, or a W1 pair needs two spellings
  of one length), widen(), JSON/BIDS/participants slots beside it, more than 26 columns (the least header uses
  one-byte names a-z; more columns need the least set of distinct names), and a one-column table with an empty
  literal beside a sized table whose own size is not read (its least size in the text total is the lesser of two
  layouts, not linear). Shape 1, a where() of tsv(f) on its column 1 (the CSV line) beside csv(f), is decided in a first
  cut since bd4b0a6 (SPEC-EXACT 3.13: the csv width Wc a model case). Since d1f51de a csv line forced by literal classes that
  looks like a tsv() literal is decided too (3.13a: a class of its own, K002 by the where()'s look-alike scope). Since
  851b564 number(cell(tsv(f), r, 1)) (3.13b), since f5c2e2f an aggregate of tsv(f)'s column 1 (3.13c), since 0605a8c
  number(header(tsv(f), 1)) (3.13d), since c42057a a key() row of tsv(f) (3.13e), since 08a879a widen() (3.13f: the
  kernel's identities name no reader), since 3f9a83c a variance of tsv(f)'s column 1 (3.13g), since d0fa7d5 size(f) beside rows() and literal where() counts (3.13h) beside csv(f): decided. Still S013 there: size(f) beside a cell, header, number or aggregate (shape 2's open case: a numerically read cell's spelling length is a variable), a csv header
  name past column 1 beside number(header(tsv(f), 1)) (no readable input answers it: NotT by choice, LOG 02:16), tsv
  column >= 2 beside an aggregate, a piece of a tsv() literal in a numerically read csv column that the number reader
  refuses (3.1). Inherited, not new: a
  table of more rows than the accounted memory holds is still a model input (R013 at MAX_ROWS, D3). Shapes 6, 7, 8,
  4, 5: not built.
  Cost: a range of about 1,000 bytes walks some 13,000 layouts per neighbour query, uncharged but bounded (FIXED in
  test_v4_loops): exceeds(number(bytes(r, 0, 1000)), c = 5) forms in 68 s (partb/S13/s3, /tmp/bigraw.bin probe).
- A certificate's BOLD image holds at most MAX_VOL = 10^6 volumes [prov]: below(volumes(r), c = 2000000) and
  below(onset(r, 1), c = 10^320 s) refuse R013 in under 0.01 s (partb/Bi/rprobe2-Rc1.txt), though readable
  datasets that fail them exist (a 2 x 10^6-volume image; an onset above 10^320 s needs about 6 x 10^11 volumes at
  the largest tr). The model's range is the full one (no wrong verdict); the bound is on building and reading the
  certificate.

## Certificates of the exact decision's refusals (SPEC-EXACT 6.1, 28 Oct 2026; BB's call 18:05)

- **What a certificate checks.** For a refusal (S011, S008 W1/W2, a file that does not bear) the question's find()s
  that answered "none" are replayed after the decision with certificates, and cert.py checks each: every leaf system's
  proof log (presolve, fm, the integer rounding, tidy, empty_box's bounds, lp's Farkas multipliers, intstep's "none",
  re-run), every option's tree of splits closed (sign splits and a mean's rows splits, prange, checked), and the equal
  shares of 5.4 recomputed. A form never waits on a check; pn450 forms with a search trace byte-identical to b225cde's
  (17,743 one_solve lines) in 312.6 s (b225cde's code: 342-352 s on earlier runs).
- **Refusals that became R013 by the checking bound or memory: none found.** Census on the unit's code (partb/CERT4,
  c4census.py): corpora 1,343 refusals, families 340, brute force exact_bf 4 rows 154, exact_bf2 partT2 88 (partN,
  partV and bfH: see CHECKPOINT-V §9 for their counts); 0 R013 from checking, 0 X001. The costliest check is pn472's
  (34 s: a replay of 7,190 options; its decision 14 s). One refusal did become R013 on the way, and the cause is fixed:
  pn472's kept options were counted per option (1.35 GB) until each object was counted once (16.8 MB).
- **Certified since U1 (units L1-L6, 28 Oct 2026; 8bc16e3, 573333d):** every split of a refusal's search is the
  model's own disjunction (nest, cap, presence, refine, band, step, binade, gap, half cut with its condition shown, two
  floats in one window), a piece's sign by its end's is shown, leaves are checked against the model's atoms of their
  case, shares with sums are shown, and the 3.7 variance shapes' "no input" is checked by their ranges
  (cert.vrange_none) or by every readable value (cert.vdeep_none). No named lemma is left: a refusal that reaches the
  check resting on a claim with no certificate is X001 (BB's call 20:38). Census on L6 and on I3 (partb/L6, partb/I3):
  corpora 1,343, families 340, bf 154 / 88 / 57 / 18 / 23: all checked, 0 R013 from checking, 0 X001.
- **The search is outside the base (3de5d44, BB's call 20:46):** search.py (614 lines: presolve, tidy, empty_box, lp,
  fm, back, MSearch, Model's solve, find and the rest) is not in TRUSTED: every "none" it gives a refusal is replayed
  and checked by cert.py, every solution it gives a form is confirmed on bytes, so a fault there can make a refusal
  X001 or R013, never a wrong answer. Base 9,145 -> 8,558 measured (definition unchanged); target 4,000 unmet, by 4,558.
- **The trusted base shrinks by moves only (29 Oct 2026, partb/SHRINK/AUDIT.md):** each move's output is checked by cert.py or confirmed on bytes, never trusted.
  unit BLD (c7339be): the certificate inputs' bytes (Model.bytes_of and what only it calls, witness._dataset/_cols) to an untrusted build.py; a trusted decide.store_ok checks each input is the store its hashes name before the bytes confirmation; 9,502 -> 8,955.
  unit SRH (063e0cb): the search's helpers left in decide.py (Log, Model.no, prove, rs_small, refine, thin, piece_atoms, psign, unrealized, rows_of, fpick, cap_ok, the float steps, form_bytes, spent_all) to search.py; 8,955 -> 8,717.
  unit HIT (f5a8c38): the variance shapes' witness pickers (d_hit, n_hit, d_domain, d_scale, two_vals, dvals, var_of) to search.py: an input they find is confirmed on bytes, a None of theirs refuses only through a range or vdeep record cert.py checks, else X001; 8,717 -> 8,478.
  Now 8,478; target 4,000 unmet, by 4,478: the 4,768 lines outside decide.py (semantics and checker) and decide.py's model and questions are what checks are checked against (AUDIT.md section 4).
- **Opus 5.5 review fixes (29 Oct 2026, review-opus55-exact/MERGED.md):** three real hits, each fixed in trusted code with a regression test built from the review's repro.
  unit F01 (f5aea93): finding 01: a case tree's leaf closed any stricter system than its node's, and a summed column's parts (search.py's refine) were trusted to partition its bands. cert.Tree now keeps each node's atoms and a leaf must close exactly the root, the option's and the node's; decide.part_atoms checks the partition (else X001); base 8,478 -> 8,493.
  unit F03 (cedb700): finding 03: search.py's find kept its own "none" records, so a "none" it did not keep was never checked. The trusted Model.find (decide.py) now keeps every "none" a question gets for certify, and an answer that is not one of the options is X001; certify's "nothing kept" check is removed; base 8,493 -> 8,511.
  unit F02 (d9aadf0): finding 02: SPEC-EXACT 1 said readable inputs were unbounded while 3.12a and item (h) bounded them by the read limit (rows() past it R013; a certificate past 64 MiB X001). Readable inputs are now bounded in every shape (SPEC-EXACT 1): a claim that holds only by the read limit is S008 W1 "it holds only by the read limit", one that holds regardless a plain S008; base 8,511 -> 8,588.
  unit F04 (0a29f9b): the mutation sweep's one hole (partb/MUT): a search point where a mean has no rows made w1's "no other answer" vacuous, so nine search.py mutants turned 7 mean forms into S008 W1; Decide.differ now refuses X001 there; base 8,588 -> 8,591.
  unit MUT (28c8c00): "a search.py fault can make a refusal X001 or R013, never a wrong answer" is tested: tests/test_search_mutants.py (search.py mutants on 8 claims: each gives X001, R013 or its unmutated verdict, and some give X001, so the test is not vacuous; 6 of its tests fail on decide.py before F04) and partb/MUT's sweep (each search.py function, 5 mutants each, over the GT runners and the part-T families: one hole, fixed at F04, no other wrong verdict; totals in partb/MUT/RESULTS.md). Not shown: a mutant outside the 5 kinds (none, big, past, empty, flip), a claim no runner draws, and the 10 search.py functions no runner calls (empty_box, fdown, fnext, fpick, fstep, fup, joint_rows, prove, refine, rpick); cert.py's docstring says why the claim holds; base 8,591 -> 8,596.
  unit MUT4 (2620a8c): sweep 4 (partb/MUT/RESULTS.md): the 10 search.py functions no runner calls (empty_box, fdown, fnext, fpick, fstep, fup, joint_rows, prove, refine, rpick) mutated under the 107 suite tests that call them: 50 mutants, 37 with an effect, X001 57, R013 161, same 530, 0 changed. With sweeps 1-3, all 43 functions are reached, and after F04 no mutant changes a decided verdict (not shown: mutants outside the 5 kinds, claims no runner or test draws); base 8,596 -> 8,596.
- **Opus 5.5 max review fixes (29-30 Oct 2026, review-opus55-max/MERGED.md):** ten findings (02 by two routes), each fixed at its root in trusted code with a test built from the review's repro, or left open here with its reason.
  unit G02 (f726938): finding 02 (route 1): cert.CHECKED kept checked systems by object identity and Tree.leaf read their contents at leaf time, so a search.py that checked one list and edited it into the node's system closed the node (a certified S011 for a claim that forms). Nothing checked is trusted by identity now: a checked system by its forms, a node's atoms and case and the question's options by fingerprints of their contents (cert.fp); an edit after a check is X001. tests/test_search_mutants.py: the review's tamper and the tamper kinds stale and edit; base 8,596 -> 8,622.
  Not shown (G02): search.py runs in the checker's own process, so a fault that writes cert.py's records directly (a Tree's fields, CHECKED) rather than through check, split and leaf is not caught; Python has no memory protection inside one process, and closing it means running the search in a second process. Every route through cert.py's functions is checked by contents.
  unit G02b (384165a): finding 02 (route 2): Decide.unbounded gave a refusal the reason "it holds only by the read limit" whenever a find replayed without the limit did not close, so a search.py that answered any point there put that reason on a refusal the model never showed past the limit. Decide.limit_shown now gives it only for a point Model.past_limit confirms (every atom without the limit holds there, an atom of the limit fails); an unconfirmed point is X001, no point keeps the plain reason (true either way). Regression test from the review's repro (test_search_mutants); base 8,622 -> 8,646.
  Not shown (G02b): a point past the read limit is confirmed by decide.py's model only, not on bytes: no input past the limit can be read, so no reader can confirm it; the reason it gives is the model's, as every refusal's "none" is.
  unit G01 (a7f7f2a): finding 01: Model.id_cond made two recordings() over the same task and recordings two values when their where() conditions were written differently, so a claim that holds because both sides are one set was refused. Recording sets of one dataset and task are now one value up to their participant sets, and merge counts the inputs that tell them apart (Model.idsize, the regions where the sets differ). Regression test from the review's repro (test_exact_decide); base 8,646 -> 8,659.
  unit G03 (2355035): finding 03: the model charged MAX_TEXT_TOTAL per tsv()/csv() call of the inlined statement and the certificate's evaluation read the inlined statement whole, while the kernel reads a let once in its own statement; a claim through a let refused S008 by the limit where a readable input fails it. Each statement (the claim, each let once) is charged its own calls (decide.stmts, let marks kept through subst), and witness.evaluate reads a let once with its own text total. Regression test from the review's repro (test_exact_decide); base 8,659 -> 8,748.
  unit G04 (4c564f4): finding 04 (a, b): the read limit's atoms counted a row at 1 + its read columns' bytes, without separators, csv quoting or a decimal class's least spelling, so a claim true on every readable input refused R013. Model.rlb is each table's least text exactly (lline, cmin, dec_len, dec_spells, in_iv), and build.least_table writes the certificate at it. Regression test from the review's repro (test_exact_decide); base 8,748 -> 8,921.
  Not shown (G04): near the read limit a certificate can need more than the stated 50,000,000 counted steps (SPEC-EXACT 8): from about 27 MB of numbers in one table the claim refuses R013 on the counted steps (tested at 74,235 rows of 903-byte numbers), never "past the read limit". A column whose values the decision reads (an aggregate, a cell, number()) is counted at its class's least spelling, while its solved value's own spelling can be longer: the length of a value's spelling is not linear in the model's variables, so near the limit such a claim can refuse R013 (never a wrong verdict). Finding 04 (c), the BIDS shapes, is unit G04c.
  unit G05 (4d71160): finding 05: a certificate the real reader refused R012 (accounted memory past 1 GiB) was X001. R012 is the read limit's too, and with the limit each statement's accounted memory is a case atom (Model.mlb, wheres): exact boundary tested (2000 columns: 6621 rows formed, 6622 S008 by the limit); base 8,921 -> 8,979.
  Not shown (G05): a statement reading a table of another shape (size(), a csv width, item (h)) or a JSON, NIfTI or BIDS file has no accounted-memory atom: their least texts are built by their own machinery (stext, tw_rows, the dataset writers), whose accounted bytes the model does not state; near 1 GiB such a certificate is refused R012 and the statement refuses R013, not X001.
  unit G06 (ad6ba4a): finding 06: a trial type holding a double quote (or a break character) is in no readable events file; the certificate gave it rows (B04: X001). Its counts are 0 by case atoms (tt_holds): S008 W1; base 8,979 -> 8,996.
  unit G07 (70b9047): finding 07: two recordings() tasks of one dataset that look alike: the certificates held both (K003: X001). recordings() has K003 branches before its filter's (Model.alike_br); the review's claims form; base 8,996 -> 9,012.
  unit G08 (86b851d): finding 08: SPEC-EXACT 2 said a dataset without participants.tsv refuses V007 in the statement and without any one part, false for recordings()' participant filter (without it such a dataset can answer). The verdict S008 W2 is kept (v4 fix 08, Phase F: a filter that keeps every participant is idle) and SPEC-EXACT 2 states the exclusion as a rule, the review's second option; a test checks it is stated (base unchanged); base 9,012 -> 9,012.
  Decided by rule, not in code (G08, BB's call on Patsak's behalf 30 Oct 2026, reversible): a 3-argument recordings() on a dataset without participants.tsv refuses V007 where the statement without the filter can answer, and W2 does not count that; SPEC-EXACT 2 states it. The code route (Decide.w2_nopt, +41 trusted lines, written and gated) turned count(recordings(b, "x", participants(b))) and 5 other pinned verdicts from S008 W2 to formed, against v4 fix 08 and Phase F's acceptance test; Patsak may choose it instead (wt-units/wt-G08 before the rework: /tmp/bak-wt-G08-preG08rule).
  unit G09 (5c23740): finding 09: the certificate's filler JSON member "" collided with a named member "" (J002: X001). build.jtext names the filler apart from the object's named members (untrusted; base unchanged); base 9,012 -> 9,012.
  unit G10 (8b2b9d9): finding 10: README's search.py count (1199; wc -l 1192) and build.py's (594; now 630) are corrected and tests/test_source.py checks both; base 9,012 -> 9,012.
  unit G04c (25aa29e): finding 04 c: the BIDS shapes had no read-limit atoms, so below(events(r), c = 1e9) and below(sum(recordings(b, "x"), "events"), c = 1e9) were R013. Each named recording's events file, each recordings() set's (one quantity, events, sums and means) and the statement's events text are now case atoms of the limit pass (Model.evlb, rs_evlb, evreads), exact at the boundary (two quantities: a necessary bound); base 9,012 -> 9,131.
  Not shown (G04c): the events read limit is exact for a named recording's file and for a recordings() set of one quantity read by sums, means or a max; it is only a necessary bound (S008 far past the limit, R013 near it) where the certificate's files are not a linear function of the model: a min (N files of m rows: N * m, bilinear), two quantities (rows of unequal sizes split over files in whole rows, Model.rs_evm), a sum beside a min or max (3.9e: by its sum, files' rows uneven), and a named recording whose onset() or duration() rows are read without events() (rows the larger of the last named row and the types' rows)
- **Shrink after the Opus 5.5 max review fixes (30 Oct 2026):** moves only, verdicts unchanged.
  unit WLK (08df58d): the three walkers that read a let once (G03's stmts, G05's wheres, G04c's evreads) are one trusted walker, letwalk, with charged for the per-statement counts (a move; tests/test_exact_decide.py test_the_let_walker_reads_each_let_once_in_its_own_statement); base 9,131 -> 9,118.
  unit SPL (853e1b7): Model.vmin (a least_table cell's spelling of a value the decision fixed) moved to build.py, untrusted: only the certificate's bytes use it, and a wrong spelling gives X001, R013 or the same verdict (test_a_wrong_least_spelling_is_x001_r013_or_the_same); base 9,118 -> 9,105.
  Not moved (SPL): G04's cmin1, dec_spells, dec_len and in_iv stay in the base. The read limit's bound is a lower bound, so S008 rests on it. Lengths alone (the least decimal length over the class, without the literal check) would be sound but not exact, and exactness (S008 at the boundary, not R013) needs that every spelling shorter than ell is a literal or looks like one: the same enumeration a certificate check would have to run. lchars (G05's memory bound) also counts the least cell's characters, so cmin's text is used by trusted code. Found at WLK: the let dedupe in stmts and evreads does not change a verdict (a let charged twice adds the same atoms); in wheres it changed only the S008 reason at G05's 6621-row boundary; the walker's own test pins it.
- **Opus 5.5 max2 review fixes (30 Oct 2026, H01-H07):** BB's calls on Patsak's behalf, reversible.
  unit H01 (e0b63d5): max2 finding 01: a user name in a variable sat where the model's kind tags sit ("z", slot, row, column) vs ("z", "pix", ...), so a file named pix, raw or y changed the verdict; now index 1 of every "z" variable is a kind tag (a cell ("z", "cell", slot, row, column), a tr region's rational ("z", "rs", slot, ...)) and no name can be read as one; tests/test_exact_decide.py test_a_user_name_spelled_like_a_kind_tag_changes_nothing (every tag in decide/search/build as a file, let and dataset name); base 9,105 -> 9,105.
  unit H02 (67cafd4): max2 finding 02: G04's least text was too high (in_iv began at the width's scale; other text letters only), so a wrong S008 by the read limit from 4,814,985 rows; now exact: in_iv's finer scales near a short end, other text any ASCII the reader keeps; the boundary is the reader's own (4,902,929 one-byte rows readable, 4,902,930 R012; tests test_the_least_text_is_exact_near_a_short_end_and_past_letters, test_other_text_takes_any_ascii_and_counts_csv_quotes); base 9,105 -> 9,139.
  Corrected (H02): the SPL note above said the bound is exact given that every shorter spelling is a literal or looks like one. It was not exact: in_iv began at the interval's width scale, so a class with a short near end (0, 100000) got "100" for "1", and the other-text search tried letters only, so 25 one-letter literals gave "aa" for "2" (max2 finding 02, a wrong S008 W1 between 4,814,985 and 4,902,929 rows). H02 makes both exact; one lower bound is left and named: if every ASCII text of 2 or more bytes in a column is a literal or looks like one, that length is used (R013 near the limit, never a wrong S008); a BIDS participants table (kind pt) is still charged a lower bound (an unread cell the empty text where B04 needs one byte or more, participant_id not as sub-<label>), as before.
  unit H07 (1bb1498): max2 finding 07: events files were parsed uncharged (kernel.events_table each call; bids(d)'s gate at a fixed 1024 bytes an entry), so a legal 48 MB events file ran out of memory at 2.2 GiB, above the floor; now a BIDS table (events, participants) is kept like a plain one, refused R012 before it is parsed when its cells alone pass the bound, in the gate too (a gate's R012 not kept for another program), and each statement's memory atom charges its events files (Model.evmem; tests test_an_events_table_is_charged_and_refused_before_it_is_built, test_the_events_tables_memory_is_in_the_read_limit); base 9,139 -> 9,183.
  Not shown (H07): the model's memory atom for a statement reading a dataset charges its events files exactly at the certificate's least text, but not the dataset's other structures (manifest text, sidecar JSON, NIfTI headers, the conformance gate's 1024 bytes an entry) nor a participants table, which the reader now charges: a lower bound, so near 1 GiB R013 (R012 on the reader at 4,668,441 rows "0<TAB>1", the model's boundary 4,668,442). The memory floor is measured for tables, selections and now BIDS tables; a gate's transient parse is room-checked, not kept.
  Verdict changes (H07): G04c's pinned read-limit boundaries move from the text's to the memory's (an events row "0<TAB>1" costs 230 accounted bytes): below(events(r)), a sum and a max over recordings S008 by the limit from 4,668,442 (was 16,777,213 / 67,108,849), trials of a type from 3,408,703 (was 9,586,978 / 38,347,909); R013 just below. No corpus, census or ground-truth verdict changed.
  unit H03 (a409e60): max2 finding 03: the reader keeps one accounted-memory account a program but G05 modelled each statement alone (and checked certificates in a fresh store), so a claim formed whose every failing input the program refuses R012; picked the reader's real behaviour, the program's account: the model's memory atom and every certificate start from what the program holds before the statement less its own files' (readers.Store.held; test test_the_memory_limit_is_the_programs: forms at 5352, S008 by the read limit at 5353, the reader V001 / R012 on those failing inputs); base 9,183 -> 9,191.
  Corrected (H03): G05 above says each statement's accounted memory; it is the program's at the statement (SPEC-EXACT 1). A statement's exact verdict can now depend on the statements before it, as the reader's R012 does; the structures the statement's own files made earlier are left to the statement (it charges them itself), while an earlier statement's where() selections stay in what the program holds (the reader charges each evaluation and keeps the account).
  unit H06 (22323ad): max2 finding 06: G08's SPEC-EXACT 2 rule (a filter of every participant is idle, S008 W2) contradicted SPEC-EXACT 1 and 5.2: on a dataset without participants.tsv the filter refuses V007 where the statement without it answers, two outcomes, so the filter bears; the rule is reversed and the code route taken (Decide.w2_nopt, partb/G08/alt-code); v4 fix 08's and Phase F's S008 W2 verdicts are overturned (they were wrong) and the pinned tests now expect the claims to form; base 9,191 -> 9,232.
  Overturned (H06): G08 above kept v4 fix 08 and Phase F's S008 W2 for recordings()' participant filter by a stated rule; that rule is withdrawn: by SPEC-EXACT 1 and 5.2 a refusal and an answer are different outcomes, so the filter bears through V007, and count(recordings(b, "x", participants(b))) forms. test_the_participant_filter_rule_is_stated is removed.
  unit H04 (b1b4e5d): max2 finding 04: made-up names from short fixed lists with an unguarded next() (Model.scell / tw_least, Model.plabel, build.rec_dataset, build.rs_recs2) gave X001 (StopIteration) when a program named every member; every one now draws from decide.fills (its list, then witness._fresh, which no longer stops at three letters), a least cell from the one-byte FILLC first (test_a_least_cell / participant_label / filler_trial_type_does_not_run_out, test_the_made_up_names_are_unbounded); base 9,232 -> 9,240.
  Not modelled, as before (H04): a size() whose least other cell would be longer than one byte (every one-byte FILLC cell a literal or a look-alike) stays NotT (S013), not X001.
  unit H05 (c9df459): max2 finding 05: certify gave the read-limit reason to every refusal with a vdeep record below MAX_ROWS rows, decided without the limit (test_partB 5a m = 5); the reason now comes only from limit_shown's confirmed point; a vdeep record holds at any size (past() is monotone), so var_hit's never-raised Past and two_cap's rb flag go; base 9,240 -> 9,238.
  unit H08 (157c952): max2 finding 08: cert.prange_split trusted the facts (S = mu·N, lo <= mu <= hi) of any PAtom, and the pieces' PAtoms come from search.piece_atoms (untrusted), so a one-line fault there gave certified S008 refusals; decide.Model.piece_facts now states each piece's facts by content and prange_split trusts a PAtom outside the option only when it is one of them: X001 (test_a_piece_with_wrong_facts_is_x001; test_search_mutants and the sweep get the kind "data"); base 9,238 -> 9,253.
  Corrected (H08): the MUT note above (a search.py fault can only make a verdict X001 or R013) did not hold for wrong data in a PAtom the search built; it holds again for that kind (sweep 6, kind data).
  unit A07 (a31536d): Argon review 07: Decide's W2 pairs (w2, w2_nopt, slot_bears) called build.py's bytes_of once for the statement and again for it without the part (or with its file varied), and build.py is untrusted, so a builder giving two inputs for one point made an idle part bear: build.py alone turned an idle condition's R013 into a form, and with search.py a repeated condition and a cancelling file into forms. Each pair now reads one input (Decide.run/outcome take it): X001 or the honest verdict (test_a_builder_giving_two_inputs_for_one_point_cannot_form); base 9,253 -> 9,256.
  Corrected (A07): unit BLD's note above (build.py's bytes are checked by store_ok, so a fault there is X001 or R013) did not hold for a W2 pair, which compared two inputs build.py gave for one point; it holds again (one input a pair).
  unit A01 (416257f): Argon reviews 01 and 04: Model.disjunction tested a split's variable by ad-hoc tags: a spelling split on a 1011-byte range no slot reads was stated as no case at all (search.py alone then closed every option with no leaf: certified S008), a binade split took a natural variable of a slot named pix and raised ValueError on one binade, and the band split's deny-list missed a region's sum of RepetitionTimes (unmodified code: widen() certified S008 W2 where a readable dataset of TRs 9 and 1.0...04 s makes it bear). One allow-list, decide.zkind (read / sum by the model's tags), decides band and step; spell needs one of the model's number()-read ranges holding a number in the case; binade needs a float of two binades or more; search.py follows zkind. Argon 04's claim is R013 now (tests test_a_split_on_a_variable_the_model_does_not_have_is_x001, test_a_binade_split_of_a_natural_or_of_one_binade_is_bad, test_a_sum_of_repetition_times_is_no_single_read_value); base 9,256 -> 9,266.
  Corrected (A01, A02): "The search is outside the base ... a fault there can make a refusal X001 or R013, never a wrong answer" (above) did not hold for a split on a variable the model does not have (Argon 01) nor for an option edited between its splits and its leaves (Argon 02); A01 closes the first, A02 the second.
  unit A02 (135cf57): Argon review 02: G02 fingerprinted an option's atoms (froot) but checked them only at a leaf and in options_closed, while a split read them live, so search.py could add a PAtom of no piece for one prange split (prange_split trusts the option's own), take it away and close the child on its contradictory atoms, turning formed claims into certified S008 refusals. Tree.split now checks the option's atoms by contents too: X001 (test_an_option_edited_between_its_splits_and_its_leaves_is_x001); base 9,266 -> 9,267.
  unit A03 (4b53166): Argon review 03: H03's held() took the claim's own files from store.log | store.gate, which a let's reads are not in, and where()'s kept rows (72 a row + 64) were charged with no key, so for a claim over a let the model charged the let's parse and rows twice: atmost(count(w), c) was a certified S008 "holds only by the read limit" with a readable counterexample (unmodified code). held() now subtracts the tables its lets read (not a dataset's other structures, which the model does not charge) and the where() bytes each let kept (store.anon per let statement, kernel.used_lets); at a 40,000,000-byte cap S008 starts exactly at the readable bound, 182,646 rows (test_a_lets_memory_is_not_counted_twice); base 9,267 -> 9,271.
  unit A06 (9c24a94): Argon review 06: nwidth keyed each widen() symbol by repr(base), which names the reader, while the kernel's identity and vranges do not, so widen(sample_variance(tsv(f), 1)) and widen(sample_variance(csv(f), 1)) did not cancel: a certified S008 W1 with a failing readable input and an X001 (unmodified code). The key reads csv as tsv: both claims form (test_widened_variances_of_one_column_by_two_readers_share_one_symbol); base 9,271 -> 9,272.
  unit A08 (5c2feb8): Argon review 08 and the CSV item of the memory-floor entry: json()/json_file() are room()-checked with their known charge before parsing, readers._table room()-checks every TSV/CSV/BIDS table at its kernel._table_size so far as each row is built (the same R012, earlier), and begin_program drops the memo at each program (test_json_a_csv_table_and_the_memo_are_held_against_the_bound); base 9,272 -> 9,277.
  unit A10 (6c2beca): Argon review 10: make_manifest skipped a folder it could not read (exit 0, an empty or partial manifest: check then formed "1 subjects" of a 2-subject dataset) and gave a traceback on a file it could not read. Both are ManifestError now: exit 2, nothing written (test_manifest_of_a_folder_it_cannot_read_whole_exits_2); base 9,277 -> 9,283.
  Open (Argon reviews 05 and 09; not fixed: a spec unit, design notes in review-argon-exact/FIXES-argon.md): SPEC 4.3's W2 removes one occurrence of a part at a time and its W1 judges a sub-value over the readers' readable inputs, while the principle asks whether a part bears on the statement's answer. So a part that cancels between two occurrences forms (let w = where(tsv(f), ge(2, c = 0)) in difference(difference(count(w), rows(tsv(f))), difference(count(w), count(where(tsv(f), ge(2, c = 5))))), with or without the let; a widen() that cancels to Exact, pinned as formed by test_affine_widen_cancels_one_value_with_itself; a BIDS file of a dataset slot that cancels), and a sub-value constant wherever the statement answers forms (Argon 09's "uv" and "wx" claims). The code follows SPEC 4.3's text; the spec is narrower than the principle.
  unit B01 (346d4b9): Argon review 2 01: cert.pin_split did not check which variables a pin split pinned, so search.py alone pinned two naturals to (1/2, 0) or a byte range's number to 7/2 and closed every option (certified S008/S011 on formed claims). A pin now pins two pixdims of the parent's atoms only: X001 (test_a_pin_of_variables_that_are_not_floats_is_x001); base 9,283 -> 9,286.
  unit B06 (6363b82): Argon review 2 06: cert.prange_split's first rows split of the option's own PAtom took a0 from the children, so a split over [a0', ...) with a0' > P.a0 left [P.a0, a0') uncovered (with Model.rb written by the search, a certified S008 on a formed claim). a0 is now at most P.a0: X001 (test_a_means_first_rows_split_starts_at_its_own_a0); base 9,286 unchanged.
  unit B07 (e743a90): Argon review 2 07: cert.py read the model's piece facts (and base, tail, disjunctions) through the live Model the search runs as, so a search.py that set piece_facts on the instance (or wrote Model.rb, Argon 06's route) certified S008 on formed claims. cert.py calls them by the model's class (cert.mcall), Model.find X001s on a changed model attribute, and test_source checks what search.py and build.py write; SPEC-EXACT 6.1 says untrusted means code that computes and returns, not a sandbox (test_a_search_that_writes_the_models_state_is_x001); base 9,286 -> 9,294.
  unit B05 (163c637): Argon review 2 05: the BIDS gate's check of each image's data decompressed a .nii.gz whole while charging only its compressed size, so an 8 MB file took ~1,000 times the time of another of its size for the same steps. Each chunk is now counted as it is read (R002 inside the loop) and charged on every use, in the certificate store too (test_a_gzip_image_read_whole_is_counted_as_it_decompresses); base 9,294 -> 9,306.
  unit B02 (1863a13): Argon review 2 02: Decide.run read build.py's store through its own methods, so a dict, tuple, bytes or str subclass showed different stores to the checks and the evaluator (a wrong form from build.py alone). Decide.input copies the store from exact types (decide.plain; Periodic files rebuilt from their arguments) into a Store that run requires: X001 otherwise (test_a_store_that_is_not_plain_is_x001); base 9,306 -> 9,328.
  unit B09 (13fc9f1): Argon review 2 09: the memory bound counted an other-text cell's least ASCII line as its characters, more than a UTF-8 cell of those bytes has (a false S008 "holds only by the read limit" near 1 GiB). Model.lchars counts such a cell as ceil(bytes / 4) characters (test_other_text_cells_are_charged_no_more_than_their_least_characters); base 9,328 -> 9,329.
  unit B08 (1d1933f): Argon review 2 08: number(header(...)) kept its reader (tsv or csv) in the kernel's identity, so the two readers' header numbers did not cancel (V006 where S008 or V001 is due) and two tolerances on it were not S012. The Header sort names no reader, as Cell (test_a_header_number_by_two_readers_is_one_value); base 9,329 unchanged.
  unit B0304 (2d5c105): Argon review 2 03 and 04: the memory held at a statement kept the where() rows earlier statements built from its own file at their actual size (a false S008 "holds only by the read limit"), and a let's JSON, text or NIfTI was held and charged again by each certificate (R013 where inline forms). held() now leaves out every structure made from the statement's files, keyed or not, and each certificate runs the earlier lets and claims on those files again on its candidate, in program order (decide.prefix, witness.evaluate); too much of that work is R013 on the witness budget (test_earlier_statements_rows_of_the_slot_are_charged_on_the_candidate, test_a_lets_json_is_charged_once); base 9,329 -> 9,394.
  unit C01 (8b66ee5): review 3 01: Tree.split's sign rule read a child's atom through the atom's own keys() and __getitem__, check() and the leaf's fingerprints through the built-ins', so a search.py dict subclass whose views differed inside Tree.split closed two contradictory children (two formed claims certified S008). cert.py now reads every value the search hands it as one copy of exact types it makes itself (cert.exact; one copy per object a tree, so its identity rules hold) and gives the model only the cases its own disjunctions made (Tree.mcase): X001 (test_a_split_on_an_atom_whose_views_lie_is_x001); base 9,394 -> 9,474.
  unit C02 (9fe7750): review 3 02: a certificate runs again every earlier statement that read the judged statement's files (B0304), but held() left out only the where() rows made from those files, so an earlier claim that also read another file had that file's rows held and charged again (R013 "past the read limit" where the claim forms). where() rows are now kept by the statement that made them and held() leaves out every row of the statements the certificate runs again (test_a_prefix_statements_rows_of_another_file_are_charged_once); base 9,474 -> 9,479.
  unit D01 (2696185): review 4 01: C01's copies kept every attribute the search wrote and the model's binade disjunction read a float's range from an atom's .r, so a sign split whose atoms' .r gave the other sign, then binade splits on those ranges, closed every option on contradictions holding none of its points (two formed claims certified S008). A range is now read from the atoms' forms (decide.frange_in) or, for a mean's rows, used only when the parent's atoms state it with integer ends (cert.prange_split); cert.exact rejects merged dict keys and keeps no partial copy (test_a_binade_split_of_a_range_its_atoms_do_not_state_is_x001 and three more); base 9,479 -> 9,532.
  unit D02 (2e8b449): review 4 02: a let on another file used inside an earlier statement the certificate runs again was evaluated again and charged on top of the rows the program holds for it (R013 where the claim forms). The re-run now takes the program's value of every let that reads none of the judged files (decide.prefix, witness.evaluate), so it charges exactly what held() leaves out (test_a_let_on_another_file_is_not_charged_again_by_a_certificate); base 9,532 -> 9,539.
- **Still trusted:** (1) decide.py's model and question logic (PLAN.md 0: the semantics of part T restated over
  counts: which options a question asks about, cases, branches, atoms, the disjunctions a split must be, the variance
  shapes' ranges and readable values, and the "model" records: no answering case, one readable value, a width given
  back, a sum of variances with no row type every variance reads); a certificate cannot replace them without a second
  model. (2) cert.py itself and intstep (re-run, Lean-proved). (3) R013's code: whether a claim that holds on every
  input is refused R013 instead of S008 W1 is still checked only by ground truth (bfh2, bfe2, bfp2 classified as stopped
  searches). (4) The replay calls the untrusted search again (Model.find): sound because each replayed option must end
  in checked leaves under the trusted model's disjunctions (cert.options_closed); a wrong replay can only fail (X001).

## A trusted-model error: the 3.7 rule beside a second variance (found 29 Oct 2026 03:55; S013 since a9b3a16, SPEC-EXACT 3.7a)

- **What was wrong.** exceeds(difference(sample_variance(where(csv(f), ne(1, "-1")), 1), population_variance(where(csv(f),
  ne(1, "-1")), 1)), c = 0) was refused S008 W2 ("the condition does not bear"); on 1, 2, -1 dropping either condition
  changes the answer with both answering (tools/groundtruth.py recheck_w2: both conditions contradicted). A wrong
  refusal, not a wrong answer: nothing false was formed.
- **Why the certificates did not catch it.** The refusal rests on Decide.outcomes_differ's 3.7 rule "a part of a
  variance's selection bears through V003/V005 or not at all", a statement of the trusted model (this file's
  certificates section, still trusted (1)): cert.py checks the search's "none" against the model, not the model. The
  rule is true of one variance alone (dropping a condition shows, on some input, as V003 against an answer) and false
  beside another value that refuses on the same inputs (Vs(sel) is V003 wherever Vp(sel)'s condition would show by
  V003). Ground truth (witness.evaluate, no model) found it: the shape-1 runner (partb/S13/s1/bf1n.py VAR=1 seed 3).
- **When it entered.** Bisect over every commit touching v4/src (git archive copies; partb/S13/s7/bisect.txt): the
  rule's code came in with fe63899 (27 Oct 2026 09:24 CET) when a statement held one variance, where it is sound; the
  first wrong verdict is 84a24d6 (27 Oct 17:24 CET, item 5b (c), a difference of two variances decided exactly), the
  first commit putting a second variance beside the first; every later commit up to 08a879a carries it. Before 84a24d6
  the old search answered 'formed' (right). v4 (8a84b36) and v4-fixes (25486d6) have no exact decision; their kernel
  witness has no such rule and answers 'formed' (right): the published v4 line does not carry it.
- **Which statements.** A W2 question (a where() condition, or a file slot) whose part sits inside a variance's selection,
  in a statement whose value holds two variance results (a difference of two variances, alone or compared with c;
  b6f1054's sums of signed variances), when the two selections' good types differ, i.e. the dropped condition removes rows
  a variance reads as numbers. Where the good types are equal (the condition drops only rows that make V005 anyway) the
  rule stands and W2 stays decided.
- **Now (a9b3a16).** Such a found none is S013 (NotT in Decide.w2 and slot_bears), never S008 W2. Measured (partb/S13/s7/samesel*.py: the finding's class, two variances over one where() of csv(f), 5 conditions, 340 statements, each against 08a879a and a9b3a16, ground truth over 714 tables): 28 statements 08a879a refused S008 W2 are all contradicted by ground truth (each with an input where both answer), and a9b3a16 makes exactly those 28 S013; every other verdict identical (140 S008 W1, each re-checked ok).
- **Decided since 2623de5 (SPEC-EXACT 3.7b, BB's call 05:40).** Decide.same_rows (trusted): when, for every pair of
  answering results a case admits together, the two variances and their places without the part have the same slot,
  column, ddof and good types less the types the case gives no row, they read the same rows wherever both answer and
  W2 stands (a 'model' record). Else search.joint_rows (untrusted, outside the base) searches multisets of rows of the
  selected types; the first input where the real code gives the two statements different outcomes is written as bytes
  and confirmed by Decide.differ_on (X001 otherwise). None found is R013 (a stopped search), never S008 W2. The 340
  statements of the finding's class (partb/S13/s7/samesel*.py): the 28 are all formed now, each agreeing with ground
  truth (every where() part of the 28 bears with an input where both answer: partb/S13/s8/bears28.py, 28/28); every
  other verdict identical to a9b3a16's (140 S008 W1 re-checked ok).
- **Siblings (a rule about one value alone used beside others), hunted 29 Oct 2026.** outcomes_differ's other "no
  witness" returns are equalities (sound); w2_input's ratio paths claim a difference (confirmed) or use 5.4's exact
  shares; w2_nwiden's "width given back" is an identity; w2_widen beside a second variance or SD is unreachable (a
  targeted ground truth, partb/S13/s7/widsib.py, 512 statements: S013 or S006, 26 W1 ok, 0 contradicted); slot_dvar's
  shape (two files): partb/S13/s7/sibs2.py, seeds 1-3 x 300, ground truth over all pairs of 45 tables (two names of one
  hash are one slot): 0 contradicted at a9b3a16 and 3f9a83c. (sibs.py, its first version, varied two names of one hash
  apart and tried every part sharing a description: its 31 'contradicted' were the runner's.)

## bfh2's claim: a stopped search where fm's eliminations pass the memory bound (28 Oct 2026)

- `atmost(difference(mean(A, 2), min(A, 2)), c = 0.3)`, A = where(t, gt(x, 0.4), le(x, 1)): R013 on the memory bound in
  521-533 s. It varies (one row holds; rows 0.41, 1, 1 fail), so R013 is a stopped search, code right
  (CHECKPOINT-V §4 item 8). Located (partb/R4/memwho.txt): Fourier-Motzkin's P x N atoms of one elimination pass the
  memory bound (its last hold asks 93.1 million steps more, against a bound of 50 million; 497.9 s under the tracer). Open: an elimination that does not build every P x N pair (for
  example a projection that drops redundant pairs first, or the lp asked for a point before eliminating) would have to
  be built and shown to keep every verdict; not started.

## A stopped search at MAX_CASES (brute force e2, 28 Oct 2026)

- `exceeds(difference(sum(S, 3), min(S, 3)), c = -1)`, S = where(t, eq("g", "B"), ge("x", c = 0.5)), refuses R013 at
  MAX_CASES (36.3 s on 8f646db, partb/Ee2 bfe2; 33.9 s on 2988dd9, partb/Bi/r13-bfe2-Rc.txt). It does not hold on every
  readable input (two selected rows with y = -5 give -5), so S008 W1 on the comparison would be wrong;
  bfe2's grid holds only nonnegative y, so it saw one answer there. A stopped witness search, not a wrong code; open.

## Closed 28 Oct 2026 (bcc71cc): bfe1's claim 60 refused R013 where S008 W1 is its verdict

- Closed by the half cuts (SPEC-EXACT 3.5a): mu <= (u + h)/2 when the counts give at most half of the mean's rows
  above the median u; the claim refuses S008 W1, decided exactly, in about 4 s, under 3 GB
  (test_bfe1_claim_60_refuses_s008_w1_not_memory_error). The same cuts (a = 0: mu <= u) closed three bfh1 claims of the
  same kind (a mean of rows none past a max or min, R013 in 22-179 s). The record as it stood:

- `atmost(difference(mean(where(t, le("x", c = 1)), 2), median(where(t, gt("x", c = 0.4)), 2)), c = 0.5)` holds on
  every answering input, so by SPEC-EXACT 5.1 it must refuse S008 W1. By hand: with A the rows whose x is in (0.4, 1],
  the mean's other rows are at most 0.4 (below every row of A) and the median's other rows above 1 (above every row of
  A), so the value is at most mean(A) − median(A); a median needs an odd count 2k + 1 (else V009), and then
  mean(A) − median(A) ≤ k·(1 − median(A))/(2k + 1) < 0.3. With A empty the mean is at most 0.4 and the median above 1.
  The kernel agrees on every table tried: 600 random tables of 1-9 rows (values −3 to 7): 304 hold, 239 V009, 57 V003,
  none fails; and a 101-row table near the supremum holds (partb/S13/classify.txt).
- The exact path does not show it: on 2988dd9 it ran out of memory under 3 GB (an lp tableau of 2,103 integer atoms,
  8.86 million cells); on 3eeac92 it gave no verdict in more than 4,200 s under 3 GB (partb/S13/remeasure-P7.txt: the run's 5,400 s timeout less the claims before it); since the memory
  charge (SPEC-EXACT 8, BB's call 28 Oct 2026 09:05) it refuses R013 on the memory bound in 5.5 s
  (partb/S13/remeasure-Mem7.txt; 20.6 s under tracemalloc, partb/Mem/memspy-Mem7.txt), and a test pins that it never ends in MemoryError (tests/test_exact_memory.py).
  The missing piece is an argument the model does not have: the median's rows and the mean's rows share the types of A,
  and the bound needs the mean of A placed against the median of A (a product of the median's value with the mean's
  count), not only each against its class ends. (Was: open, a wrong refusal code, not a stopped search.)

## Closed 27 Oct 2026: the Windows suite needed an elevated shell (Argon R7)
Three tests create symlinks (test_v4_mutation symlinks-ignored, and two test_v4_fixpass W1 linked-folder
tests), which Windows allows only with SeCreateSymbolicLinkPrivilege. Fixed in 3bf2403: tests.helpers.symlink
attempts the link and skips only on WinError 1314, naming the missing privilege; any other error fails.
Non-elevated Windows now gives 3 skips for these; the junction test (mklink /J) covers the same rule
without privilege. Elevated runs still execute all three.

## Closed 27 Oct 2026: the reference implementation had no affine widen (Argon O12)
Argon found that `reality4_ref` widened by plain intervals, so it gave [37, 43] where v4 gives [39, 41], and [28, 32]
where v4 gives 30 (Exact) for test_v4_identity's program, with no carve-out saying so. Rather than carve it out, the
reference now builds v4 SPEC 5.2 itself (its own forms keyed by its own value keys, one symbol per value, a symbol on
both sides of a difference cancels; widen of a widened value is one use of its base, O9). tests/test_v4_opass.py
checks both programs and nested widens against v4. The S012 exact-use difference stays carved out (w1-w2-s012) as before.
