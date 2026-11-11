# Reality v4 (in progress)

Reality v4 is being built on local branch `v4` from v3 (`../v3`, unchanged). It implements the
design principle "nonsense is unformable" (not included in this repository; with the amendments of
§10, 24 Oct 2026, §11, 25 Oct 2026, 21:14 CET, and §12, 22:10 CET) through three general
mechanisms instead of v3's case lists: witnesses for idleness (W1/W2), a register of every
sentence of BIDS 1.0.1, and metered costs (DESIGN.md, SPEC.md).

**Status.** Not finished and not reviewed. STATUS.md says which phase is reached; LOG.md has
every step with its time. The real dataset was checked on the PC at commit abad0e4 (Phase H,
26 Oct 2026, ended 07:34 CET: 3 passed, every v3 reference value reproduced); the later commits on
branch v4-fixes are checked on the box only (KNOWN-OPEN 14). Until the review,
treat every statement below as the author's own check, not an independent one.

## Trusted base

The checker is these files (`wc -l`, 10000 lines, including native questions). v3's README counted 2,684 lines in 7 files;
v4 also counts the witness check (`witness.py`), the exact square roots (`exact.py`) and the
memory floor (`machine.py`), because each of them decides verdicts. `tests/test_source.py` fails
above the cap and checks that the total below is the current one.

**Cap: 9,312 lines now; target 4,000 or less.** Patsak set the cap at 4,000 on 25 Oct 2026 21:36
CET. The CSV reader (principle §12) was approved at 22:10, after that cap, and took the base to
4,233; so on 25 Oct 2026 22:29 CET Patsak raised the cap to 4,250 for that reason. Phase G aims
for 4,000 or less. On 26 Oct 2026 Patsak raised the cap to 4,300 as a technical call, for the same reason:
the CHANGES checker (CPAN Changes convention, taste call 4) was added after the 4,250 cap was set; shrinking
first (joining five more lone docstring quotes) left it at 4,296. The Windows memory floor (v4-fixes, 26 Oct 2026:
`machine.py` reads the process's job object limits, KNOWN-OPEN) was first squeezed into 4,300 by compressing its
Windows structures; that was undone, and on 26 Oct 2026 BB, on Patsak's behalf (technical call, reversible), raised the
cap to the measured 4,335: readability of trusted code over line count (DESIGN §10). Which number holds: **4,335 (the
target of 4,000 is not met: 4,335 after the Windows memory floor)**. On branch exact-decision the base was
4,354, 19 over that cap: BB's call D4 (26 Oct 2026, on Patsak's behalf) keeps the nested share spelling refused
and makes its S008 message name the one spelling that forms (`witness.py`). On 26 Oct 2026 21:29 CET BB, on
Patsak's behalf (technical call, reversible), raised the cap by the measured 19 lines to **4,354**, for the same
reason as 4,335: an honest count, the message not trimmed to fit (DESIGN §10.2). From here the cap moves only by
measured amounts at each exact-decision phase checkpoint, each logged. Which number holds: **4,354 (target 4,000
unmet)**. Phase 3 of exact-decision (26 Oct 2026, stopped before its checkpoint) puts `intstep.py` (the integer
step, SPEC-EXACT 4) and `decide.py` (the part-T model and questions, SPEC-EXACT 3, 5, 6) in the table, since
part-T verdicts now depend on them: the base is **4,933**, 579 over the 4,354 cap. The cap is not raised here: it
moves only by the measured amount at the phase 3 checkpoint, logged; until then `test_trusted_base_size` fails on
this branch on purpose. At the phase 3 checkpoint (27 Oct 2026) part T also takes number conditions, `cell` (by
position and by key), `header` and `number()` (BB's ruling 3 of 26 Oct 22:12), and `decide.py` grows to 799 lines:
the base is **5,340**, and the cap is raised by exactly the measured 986 lines to **5,340**, logged (DESIGN §10.3,
LOG), not compressed to fit. Which number holds: **5,340 (target 4,000 unmet, by 1,340)**. At the phase 4 checkpoint
(27 Oct 2026) part N (sum, mean, max, min, order, median, widen; SPEC-EXACT 3.5, 4.2) takes `decide.py` to 1,188
lines and the base to **5,729**; the cap is raised by exactly the measured 389 lines to **5,729** (DESIGN §10.4,
LOG). Which number holds: **5,729 (target 4,000 unmet, by 1,729)**. At the phase 5 checkpoint (27 Oct 2026) part H
(JSON paths, NIfTI dims, size and bytes; SPEC-EXACT 3.6) takes `decide.py` to 1,363 lines and the base to **5,904**;
the cap is raised by exactly the measured 175 lines to **5,904** (DESIGN §10.5, LOG). Which number holds: **5,904
(target 4,000 unmet, by 1,904)**. At the variance phase checkpoint (27 Oct 2026) part V (variances and SDs,
SPEC-EXACT 3.7) takes `decide.py` to 1,507 lines and the base to **6,048**; the cap is raised by exactly the measured
144 lines to **6,048** (DESIGN §10.6, LOG). Which number holds: **6,048 (target 4,000 unmet, by 2,048)**. On 27 Oct 2026 BB merged
v4-fixes into this branch (the fix pass of FIX-BRIEF.md, 4,335 -> 4,402, and the O pass, 4,402 -> 4,490, each
measured and logged there; DESIGN §11, §12): the base is **6,203** = 6,048 + 155, and the cap follows by exactly that
measured amount. The exact path then needs fix pass R3 (W2 for a file slot) decided exactly too, or the merge would drop it on part T:
`decide.py` +40 lines (DESIGN §10.7). Which number holds: **9,312 (target 4,000 unmet, by 5,312)**: the certificates of no point (SPEC-EXACT 6.1) add `cert.py` (491) and decide.py's logs, trees, checks, a refusal's replay, the model's own disjunctions, records and points, and the variance shapes' range and value records; then decide.py's search (presolve, tidy, empty_box, lp, fm, back, MSearch and Model's solve, solve1, half_cut, count_ints, implied, one_solve*, finish, find: 614 lines) moved to `search.py`, outside the base (unit I3, BB's call 18:05): every "none" it gives a refusal is replayed and checked by `cert.py`, every solution it gives a form is confirmed on bytes, so it can make a refusal X001 or R013, never a wrong answer. decide.py's model and questions (the semantics of part T over counts) stay trusted: no certificate can replace them without a second model (verify-opus-exact/partb/CERT/ITEM3.md). Item 4 shape 3 (number() of a file's bytes, SPEC-EXACT 3.11) adds the model's numbers of n bytes by layout and their spellings to decide.py (+219, measured); shape 2 (size() of a table, SPEC-EXACT 3.12) its least lines and the padded certificate table (+46, measured); its review (BB's call 23:30, SPEC-EXACT 3.12a, 3.12b) the text total per tsv()/csv() call in place of the cap of 4 calls, and a one-column table's empty literal by its two layouts (+73, measured). Shape 1's first cut (SPEC-EXACT 3.13) a tsv() line of a file read by csv() too, the csv width as a model case (+102, measured); its review (SPEC-EXACT 3.13a) a forced look-alike csv line as a class of its own (+15, measured); case 1 (SPEC-EXACT 3.13b) number() of a tsv() line, Wc = 1 as its own case (+12, measured); case 4 (SPEC-EXACT 3.13c) an aggregate of the tsv() column (+7, measured); case 3 (SPEC-EXACT 3.13d) number() of the tsv() header (+8, measured); 3.13e a key() row of tsv(f) (+8, measured); 3.13f widen() beside them (-2, measured: a NotT removed). 3.7a a variance's part hidden by another refusing value: S013, not a refusal (+12, measured). 3.13g a variance of the tsv() column (+2, measured); 3.13h size() of the file beside rows() and where() counts of both readers, by width case (+63, measured). 3.7b 3.7a's S013 decided by a witness search outside the base (search.joint_rows), its rows confirmed on bytes, and same_rows (equal good types less the cases' zero types) keeping W2; none found is R013 (+33, measured). 3.9a two quantities of one dataset's recordings (volumes beside events or trials of a type): kinds as pairs, a state per quantity, certificates with both values per recording (+100, measured). 3.9b two quantities of one events file (events beside trials, two trial types): a state per events-file class, events >= the read types' trials, filler rows in certificates (+50, measured). 3.8a two named recordings, one's labels within the other's: the inherited sidecar a folder up in certificates (+6, measured). (Part B's measured moves: DESIGN §10.8) Then the base shrank by moves only (partb/SHRINK/AUDIT.md): the certificate inputs' bytes to `build.py`, outside the base (unit BLD: each input checked as a store by decide.store_ok, then read by the real readers and evaluator; -547, 9,502 -> 8,955); the search's helpers left in decide.py to `search.py` (unit SRH: -238, 8,955 -> 8,717); the variance shapes' witness pickers to `search.py` (unit HIT: what they find is confirmed on bytes, a None of theirs refuses only through a range certificate cert.py checks, else X001; -239, 8,717 -> 8,478). Then the Opus 5.5 review's fixes added trusted checks: unit F01 (a leaf's atoms are its node's exactly, cert.Tree; a summed column's parts partition its bands; +15, 8,478 -> 8,493), unit F03 (every "none" kept for the check by trusted code, Model.find; +18, 8,493 -> 8,511), unit F02 (readable inputs bounded by the read limit in every shape, SPEC-EXACT 1: a second pass with each table's least text and the statement's total as case atoms, a certificate past the limit OverRead, and the "holds only by the read limit" reason; +77, 8,511 -> 8,588), unit F04 (the mutation sweep's one hole: a search point where a mean has no rows made w1's "no other answer" vacuous; X001 now; +3, 8,588 -> 8,591), unit MUT (the claim tested: tests/test_search_mutants.py runs search.py mutants on 8 claims and each gives X001, R013 or the verdict it gave unmutated; partb/MUT's sweep (each search.py function, 5 mutants each, over the GT runners and the part-T families) found one hole, fixed at F04, and no other verdict change (33 of 43 functions reached; the 10 no runner calls are not shown by it); cert.py's docstring says why; +5, 8,591 -> 8,596). Then the Opus 5.5 max review's fixes: unit G02 (nothing checked is trusted by object identity: a checked system by its forms, a node's atoms and case and the question's options by fingerprints of their contents, so a search that edits an object after its check gets X001; +26, 8,596 -> 8,622), unit G02b (the reason "it holds only by the read limit" only from a point found without the limit that decide.py's model confirms past it, Model.past_limit; an unconfirmed point X001; +24, 8,622 -> 8,646), unit G01 (two recordings() aggregates over the same recordings are one identity, as in the kernel: Model.idsize; +13, 8,646 -> 8,659), unit G03 (a let is read once, in its own statement with its own text total, as the kernel reads it: the model charges each statement's own tsv()/csv() calls and witness.evaluate reads a let once; decide.py +67, witness.py +22; +89, 8,659 -> 8,748). Opus 5.5 max review 04 a, b (unit G04, BB's call on Patsak's behalf 30 Oct 2026, reversible): the read limit's atoms count each table's least text exactly, each row type's least line from its columns' least cells, separators, csv quoting and the least decimal spelling (Model.rlb, lline, cmin, dec_len, dec_spells, in_iv), so a claim true on every readable input is S008 by the read limit, not R013 (decide.py +173, 8,748 -> 8,921). Opus 5.5 max review 05 (unit G05, BB's call on Patsak's behalf 30 Oct 2026, reversible): the reader's accounted memory (R012, 1 GiB) is part of the read limit: a certificate refused R012 is past it, and with the limit each statement's accounted memory is a case atom (Model.mlb, wheres), so a claim true on every readable input is S008 by the read limit, not X001 (decide.py +58, 8,921 -> 8,979). Opus 5.5 max review 06 (unit G06): a trial type with a double quote or a break character is in no readable events file, so its counts are 0 (tt_holds; decide.py +17, 8,979 -> 8,996). Opus 5.5 max review 07 (unit G07): recordings() of a dataset holding recordings of two look-alike tasks refuses K003, and the model branches on it (Model.alike_br; decide.py +16, 8,996 -> 9,012). Opus 5.5 max review 08 (unit G08): recordings()' participant filter on a dataset without participants.tsv is excluded from W2 by a rule SPEC-EXACT 2 now states (v4 fix 08), not by the false reason it gave; the base is unchanged. Opus 5.5 max review 09 (unit G09): the certificates' filler JSON member is named apart from the object's named members (build.jtext, untrusted; the base is unchanged). Opus 5.5 max review 04 c (unit G04c): the BIDS events files are within the read limit too: each named recording's events file and each recordings() set's (exact for one quantity read by sums, means or a max; a necessary bound for a min, two quantities or a sum beside a max or min) at most MAX_TEXT_FILE and the statement's text over them at most MAX_TEXT_TOTAL, as case atoms at their least text, which the limit pass's certificates write (Model.evlb, rs_evlb, rs_evm, evreads; decide.py +119, 9,012 -> 9,131). Then a move (unit WLK, BB's call on Patsak's behalf 30 Oct 2026, reversible): the three walkers that read a let once (G03's stmts, G05's wheres, G04c's evreads) are one, letwalk, with charged for the per-statement counts (decide.py -13, 9,131 -> 9,118; verdicts unchanged). Then a move (unit SPL, BB's call on Patsak's behalf 30 Oct 2026, reversible): Model.vmin, a least_table cell's spelling of a value the decision fixed, to `build.py` (only the certificate's bytes use it, which the reader and the evaluator check; decide.py -13, 9,118 -> 9,105). cmin1 and dec_spells stay: the bound's exactness needs that every shorter spelling is a literal or looks like one, which only the same enumeration shows, and the memory bound (lchars) counts the least cell's characters (KNOWN-OPEN). The 4,000 target stays unmet: the files other than decide.py are 4,777 lines of semantics and checker that nothing re-checks, and decide.py's model is what the certificates are checked against (AUDIT.md section 4).

| file | lines |
|---|---|
| `decide.py` | 4548 |
| `kernel.py` | 1276 |
| `bids101.py` | 789 |
| `readers.py` | 787 |
| `witness.py` | 443 |
| `syntax.py` | 413 |
| `intstep.py` | 209 |
| `machine.py` | 111 |
| `sorts.py` | 111 |
| `__main__.py` | 107 |
| `keys.py` | 99 |
| `exact.py` | 98 |
| `cert.py` | 642 |
| `questions.py` | 367 |
| **total** | **10000** |

Outside the base: `search.py` (1192 lines) and `build.py` (649 lines) are untrusted (tests/test_source.py checks both counts; unit G10); their loops are still charged or named (tests/test_v4_loops.py). (B07, Argon review 2 07) They run in the checker's process: the guarantee is for code that computes and returns, not a sandbox against code that rewrites the checker's own state (SPEC-EXACT 6.1); Model.find and cert.mcall keep the model's state from the search, and tests/test_source.py checks what they write. (C01, review 3 01) cert.py reads every value they hand it as one copy of exact types it makes itself (cert.exact): a subclass whose own methods could show two values is X001. (D01, review 4 01) Nothing the search derived is read from those copies: a range is read from the atoms' forms (decide.frange_in, cert. (D02, review 4 02) A certificate's re-run of earlier statements uses the program's value of a let on other files, as the kernel does, so its rows are held once.prange_split).
Nothing else is imported except the Python standard library and the pinned UTS #39 data file.

## Checks so far

`~/reality-harness/venv/bin/python -m pytest -p no:cacheprovider -q tests` (see LOG.md for the
count and time of each run). What they do not cover is in KNOWN-OPEN.md.
