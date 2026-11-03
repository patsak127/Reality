# Reality v4: design (Phase A)

Written 25 Oct 2026, Europe/Berlin (UTC+1), on branch `v4` cut from v3 at 6b6f88f. Nothing in
v0/–v3/ or core/ is changed. This is a design, not a result: nothing below has been built or run
unless it says "[ran]".

Inputs read for it: the Opus 5.5 max review of v3 (`review-opus55max-v3/`: OVERALL.md, MERGED.md,
findings 01–29), the mutation report (`mutation-v3/SUMMARY.md`, `RESULTS-*.md`), checker B's
`checker-b/AMBIGUITIES.md`, `v3/SPEC.md` §9–§10, and the frozen principle
(`/workspace/team/research/principle-nonsense-unformable.md`).

## 0. The problem in one paragraph

Each review of v1–v3 found hits, v3 closed the exact cases, and the next review found their
neighbours (MERGED.md "Overlaps": 01/02 continue v2 hit 9, 03 continues v2 hit 3, 04 continues v2
hit 4, 05 continues v2 hit 13). The cause is the same each time: a rule written as a list of
cases (spellings that are idle, characters no cell holds, BIDS silences, operations that cost
steps). A list is safe only for the cases on it. v4 replaces three such lists with rules whose
*default is refusal*, so that a case nobody thought of refuses instead of forming. Where a
mechanism cannot be made fail-safe, this document says so.

The pattern used three times: **formation needs evidence that the checker builds and checks
itself.** A claim forms only if (1) the checker has shown, with bytes its own readers accept, that
the bytes bear on the answer; (2) every reading decision the BIDS reader took is tied to a 1.0.1
sentence that fixes it; (3) the work, output and memory the statement can use were charged before
they were spent. Failure of the evidence refuses. The cost moves from "a missed case forms
nonsense" (a hit) to "a case the evidence builder cannot handle refuses" (an overcorrection),
which is the direction the principle allows and which tests can measure.

---

## 1. Mechanism 1: sameness and idleness judged on meaning

### 1.1 What v3 does and why it leaks

v3 decides idleness by inspecting the printed sort tree: `a.sort == b.sort` for `difference`
(kernel.py:493), a hand domain for `count` and `share` only (kernel.py:524), a hand list of
characters no cell can hold (`cell_literal`, kernel.py:171), and per-condition rules in `where`.
Any spelling with the same meaning and a different tree escapes (finding 01: `rows` vs `count`,
condition order, `widen(x) − x`, a selection against its base, `max − min`; finding 02: `"`).
Finding 26 names the root cause: the sort is used both as the printed subject and as the
value's identity, and it is not canonical.

A canonical form (rewrite every sort to a normal form, then compare) would close the five listed
cases, but it is itself a list: each equation (`rows ≡ count`, conditions commute, nested `where`
flattens, ...) must be thought of, and a missing equation is the next hit. I do not choose it as
the mechanism. A normal form still appears below, as a helper.

### 1.2 The rule: a part bears on the answer only if the checker can show it does

Definitions (to go into SPEC §9 in Phase B):

- **Readable input for a file.** A byte string that every reader the statement applies to that
  file accepts (`tsv(f)` and `size(f)` on one file: both must accept it). For a BIDS dataset: a
  dataset the 1.0.1 reader finds conformant that contains the entities the statement names.
- **The answer** of a value: its printed value and precision (for a number, the interval and its
  class; for bytes, the bytes; for a comparison: holds / does not hold).
- **W1, the value bears on the bytes.** For every computed value in the statement (the claim
  itself and every sub-value), there are two readable inputs on which its answers differ. For a
  comparison: one input on which it holds and one on which it does not.
- **W2, each part bears.** For every *part* of a computation (a `where` condition, a `key` pair, a
  `widen`, each named file), there is a readable input on which the computation with the part and
  the computation without it give different answers. ("Without": the condition or pair removed,
  `widen` removed, or for a file, all other files held fixed and this one varied.)
- **Refusal.** A value that fails W1 refuses **S008** ("the bytes do not bear on the answer"),
  except that a value which is the empty selection, or a comparison that does not hold, on every
  readable input refuses **S011** ("its own parts rule it out", principle item 6). A part that
  fails W2 refuses S008 naming the part.

**Witnesses are real bytes.** The checker does not reason that an input exists; it builds one.
A witness is a set of synthetic files serialised to bytes, read by the *same reader code* the
claim uses, and evaluated by the *same computation code*. A witness the reader refuses does not
count. So a claim forms only if the checker holds, at that moment, bytes that its own readers
accept and on which the answer moves. That is meant to make "idle forms" impossible regardless of spelling
(an argument with conditions, not a theorem: see the 26 Oct correction under §1.3):
for `difference(rows(t), count(t))`, `difference(count(where(t, A, B)), count(where(t, B, A)))`,
`difference(widen(x, 1), x)`, `atleast(rows − count(where(...)), c = 0)` and
`atleast(max − min, c = 0)` no witness exists, so none can be built, so all refuse. Nobody had to
list them.

**Literals no cell can hold come from the reader itself.** To show that `ne(col, "\"")` bears
(W2), the builder must produce a readable table with a row the condition removes, i.e. a cell
holding `"`. The TSV reader refuses every such table (T005), so no witness exists and the
condition refuses. The same derivation covers TAB, LF, CR, the T006 characters, an empty cell in
a BIDS TSV once empty cells refuse (taste call 2), a second `sub-01` row in participants.tsv
(unique ids), and anything a later reader refuses. There is no character list to keep in step.
This is stronger than "derived from the reader's grammar": it is derived from the reader's code,
all of its checks included.

### 1.3 How witnesses are built (the part that decides overcorrection)

Soundness was claimed not to depend on this section ("a wrong or weak builder can only fail to find a
witness, which refuses"). Corrected 26 Oct 2026 (review finding 26): that holds only under the
conditions SPEC 4.4 item 12 lists, and the full review found each of them broken once (findings
01-08, fixed on v4-fixes). Item 6's brute-force measurement is now built (tests/test_v4_bruteforce.py). Completeness (no needless refusal) does, so the builder is designed per
computation and measured.

1. **Linear normal form (LNF), the helper.** Each count is written as a linear form over *row
   types*: for the conditions a statement mentions on a table, a row type fixes, per mentioned
   column, which mentioned literal the cell equals or "another value". `count(where(t, C))` is the
   sum of the multiplicities of the row types that satisfy C; `rows(t)` is the sum over all types.
   A `difference` of counts is a linear form `Σ n_r · w_r`. A readable table can have 0 rows
   ([ran] v3 forms `rows(tsv(f)) = 0` on a header-only file), so: the form is constant iff every
   `w_r = 0`; `atleast(e, c)` holds on every table iff `c ≤ 0` and every `w_r ≥ 0`; and otherwise
   the builder writes a witness directly (one row of a type with `w_r ≠ 0`, or `⌈c / w_r⌉` copies
   of it). Row types the reader cannot realise (a cell `"`) are discovered by serialising one row
   of that type and reading it. Unique-key columns (participant_id) cap a type's multiplicity at
   1, also discovered by reading.
2. **Numbers.** Decimal cells and `sum/mean/max/min` over (selection, column) are *atoms*. A
   value is an affine form `c0 + Σ ci·atom_i + Σ dj·εj` (§1.4). The builder chooses atom values by
   writing rows with chosen decimals, using values derived from the statement's own cutoffs and
   tolerances (`c`, `c ± 1`, `c ± 2q`, 0, and a value outside every interval).
3. **Fallback: bounded enumeration.** Where 1–2 do not propose a witness (a combination outside
   the linear fragment), enumerate small tables (rows 0–3 of the mentioned row types, decimals from
   the set in 2) until a witness is found or the enumeration ends (then refuse). The bound is a
   fixed part of the spec, so every implementation tries the same inputs.
4. **BIDS values.** A minimal conformant dataset is generated with exactly the subjects, tasks,
   runs and acq/rec labels the statement names (as `tests/bidsfix.py` already does for tests),
   then the files the value reads (participants.tsv, an events TSV, a sidecar's RepetitionTime
   together with the header's `pixdim[4]`, the header's `dim[4]`) are varied, and every candidate
   is passed through the full 1.0.1 conformance check before it counts.
5. **Cost.** Witness building is charged steps like any other work (Mechanism 3) and has its own
   bound; reaching the bound refuses R002, never forms.
6. **Measurement.** A brute-force test: for every program in a generated family (small tables over
   2–3 literals per column), enumerate all readable tables up to a size and compute the ground
   truth "constant / not constant within this space". Required: no formed claim is constant (this
   is the soundness check and must be 0); reported: non-constant claims the builder refused (the
   overcorrection count). The acceptance must-form list (F tests) and the 115-program corpus must
   still form; any that do not is a builder bug to fix before the phase closes.

### 1.4 Dependence in the arithmetic (`widen`)

Interval arithmetic without dependence gives `difference(widen(x, 1), x) = [-1, 1]` when the
answer is exactly determined (finding 01 line 10; finding 26 names this the dependency problem
and points to affine arithmetic, Comba and Stolfi 1993, a citation I have not checked myself).
v4 represents a widened value as `x + q·ε_v`, where `ε_v ∈ [-1, 1]` is one symbol **per value
identity** (§1.5), not per `widen` node: the true value behind one cell is one unknown. So
`widen(x,1) − widen(x,1)` is exactly 0 (and then refuses W1), and `widen(x,1) − widen(y,1)` is
`[-2, 2]` as before. Intervals print exactly as in v3 when no symbol occurs twice; Phase D checks
on the corpus how many formed lines change (I have not counted them).

### 1.5 Value identity (for the one-tolerance rule and frames)

Patsak's call: the one-tolerance rule means one cell however it is written. v4 gives every value
an identity separate from its printed sort: **(file hashes, positions read, computation)**, with
positions resolved on the bytes (a keyed row becomes its row number) and a selection identified by
the set of rows it selects, not by how its conditions are spelled. So `cell(t, 1, 3)` and
`cell(t, key(1, "s1"), 3)` are one value, and two `sum`s over the same rows of one column are one
value. S012 groups by this identity. The printed sort is unchanged; it stays the claim's subject.

That extends the call from cells to computed values (a sum over the same rows), which I take to be
its logic, not a new decision. Whether an un-widened use counts as tolerance 0 is not decided
(taste call 4, §5).

### 1.6 What it replaces in v3, and what it costs

Derived from W1/W2 instead of written by hand (the v3 rules become tests that must still refuse):
`difference` of equal sorts; a count or share cutoff that cannot fail or cannot hold; `tolerance =
0`; an `eq` or `ne` repeated; `eq` and `ne` on one column; two different `eq` on one column (S011);
the TAB/LF/CR literal; a `key` column used twice; the `trials` literal check.

Expressiveness: nothing that forms in v3 and has a non-constant answer should refuse; the risk is
builder incompleteness, measured by §1.3 item 6. Idleness is structural (taste call 1, §5), so
"every participant is in group A" forms.

### 1.7 Open technical choices

- LNF + enumeration (lean) versus enumeration only (simpler, more refusals) versus an exact
  integer-programming decision for the whole fragment (complete for counts, much more code in the
  trusted base). Lean: LNF + enumeration; the trusted part is only the reader and evaluator that
  check each witness.
- Whether S008 for an idle sub-value names the sub-value or the whole claim (lean: the innermost
  failing value, so the message points at the defect).
- Whether v3's syntactic fast paths stay (they are implied by W1/W2; lean: keep only where they
  give the same code, so codes are defined by the general rule alone).

---

## 2. Mechanism 2: BIDS 1.0.1 silences handled by an algorithm

### 2.1 What v3 does and why it leaks

Call 3 ("where 1.0.1 is silent, refuse") is applied case by case: B13 for two *images* with
`run-1`/`run-01`, B15, B17, B14 at the root only. The neighbours pick a reading silently: a
`run-1` sidecar beside a `run-01` image (05), IntendedFor in a magnitude JSON (06), `tasks.tsv`
(07), inherited TSVs below the root (10). RULES-1.0.1.md is organised by topic and misses
sentences (finding 21), which is how the omissions got in.

### 2.2 The rule: every reading decision must cite a sentence that fixes it

1. **The sentence register.** The pinned text (`bids-1.0.1.txt`, sha256
   `51665a13…6a354f`, 1 397 lines; a rough split gives about 530 sentences [ran]) is split into
   numbered sentences by a stated rule (footnotes, table rows and list items count as sentences).
   `v4/bids/REGISTER-1.0.1.tsv` has one row per sentence: its number, its hash, its text, and one
   class: **checked** (with the code and the test that pins it), **refused where silent** (with the
   choice point it creates), **not checkable from bytes** (with the reason), or **not about files**.
   A test re-splits the text and fails unless every sentence appears exactly once and every
   "checked" row names a code that a test triggers. RULES-1.0.1.md becomes a readable view of the
   register. Then "every statement classified once" is checked by a test, not claimed.
2. **Decisions carry justifications.** The reader is restructured so that every point where it
   interprets the dataset (does this file match that template, does this metadata file apply to
   that image, are these two entity values one value, which JSON supplies this field, is this file
   extra) is a *decision* that returns its result together with the register sentences that fix
   it. A decision that no sentence fixes uniquely is a **choice point**: the reader computes the
   result under every reading the text allows and, if the results differ, the dataset does not
   conform (new code **B30**, "1.0.1 allows two readings here", naming the sentence and both
   readings). If the results agree, no refusal: silence that cannot change anything is harmless.
3. **Fail-safe default for classification.** A file is *extra* (ignored, principle "Extra
   files") only when a decision shows that no 1.0.1 template and no §3.5 inheritance rule could
   apply to its name. If one could, the file is a 1.0.1 file: read if v4 implements its kind,
   refused B14 if not. So an unclassified name refuses instead of being skipped.
4. **Lint.** A test walks the reader's code and fails if a branch that inspects names, entities or
   metadata is not inside a decision. A second test flips every choice point to its other reading
   on the fixture datasets and checks that each flip either changes nothing or makes the dataset
   refuse (the reviewer's "vary the choice, check the verdict"). *(26 Oct 2026, review finding 29:
   neither test was built; the register rows are checked only by reading them. KNOWN-OPEN 11.)*

This does not make a missed choice point impossible: someone can still write a justification that
claims a sentence fixes a reading when it does not. It moves the error into one register row that
a reviewer can check by reading one sentence, instead of a code path nobody listed. I think that is
as close to "by construction" as a reader of prose can get; the honest name is "every reading is
cited".

### 2.3 What it decides for the review's cases

| case | choice point | result |
|---|---|---|
| 05 `run-1` sidecar, `run-01` image | entity equality for run indices, applied to every file kind | merged metadata differs between readings: B30 |
| 06 IntendedFor in `magnitude1.json` | which JSON supplies IntendedFor (§8.9.1 template: phasediff JSON; or any image's JSON) | IntendedFor sets differ: B30; without the magnitude field both agree and nothing refuses |
| 07 `tasks.tsv` at the root or subject level | §3.5 names it as inherited metadata | a 1.0.1 file of a kind v4 does not read: B14 |
| 10 `sub-01/sub-01_task-y_events.tsv` | inherited TSV at any level (§3.5) | B14, same as at the root |
| 09 dictionaries | §4.2 applies to every tabular file | one dictionary rule (entries name columns, B19) for participants, phenotype (MeasurementToolMetadata allowed, §8.11) and events, at every level |
| 11 `sub-01/func/..._events.json` | §4.2 template "same name, .json" | a defined file, read as JSON (B03) and as a dictionary; no longer B17 |
| 08 empty cells, blank header | Patsak's call: "should be coded as n/a" binds | B04 in every BIDS TSV |
| 21i root `dwi.bval` | §8.8 "any level" | B14 (dwi not implemented) |
| 21f–h `notes.json` at three depths | no template or inheritance rule can apply to suffix `notes` | extra at every depth (today: B03, extra, B17) |
| KNOWN-OPEN 4, onsets after the run | conformance not fixed by the text | B30 under the algorithm; see taste call 3 |
| v4-fixes 11, SliceTiming's axis (S0369) | which spatial axis the list goes through when neither SliceEncodingDirection nor slice_dim names one | the length fits one axis: that axis, no refusal; fits several: B30; fits none, or not the named axis: B10 |

### 2.4 Costs

Expressiveness: datasets that formed in v3 by a silent reading now refuse. The real ds001734 must
be re-run (Phase H). Facts I checked on the box copy [ran]: it has a README, and no
participants.tsv or events file has an empty cell or trailing tab, so the n/a rule should not
refuse it. Whether its other files pass the new classification is not known until the run.

Work: the register is a careful read of about 530 sentences. That is the largest single item in
v4. The code change is a restructuring of `bids101.py` (618 lines) around decisions.

### 2.5 Open technical choices

- The sentence-splitting rule (lean: split on sentence ends and list/table boundaries of the
  pinned text file, normalising the zero-width characters the PDF extraction left; the rule and
  the resulting count go into the register header).
- B30 as one new code versus keeping B13/B15 (lean: B13/B15 become B30; one rule, one code; the
  map is listed in SPEC).
- Whether to compute both readings fully (rerun conformance) or locally (compare the decision's
  own result). Lean: locally; it refuses at least as often, and it is linear.

---

## 3. Mechanism 3: costs that bound real work, output and memory

### 3.1 What v3 does and why it leaks

Steps are an accounting convention, not a measure (finding 27): `key()` and inheritance are
quadratic but charged linearly (18), a filter is charged when it does no work (20), byte literals
count one node however long (04), output is unbounded and held until the end (04), and the
MemoryError guard misses printing (04: exit 1 at 1 GB). Paths go through the locale's filesystem
encoding (03, 17). An unreadable supplied file crashes the run (16).

### 3.2 The rules

1. **One meter, and no unmetered loop.** All work in the trusted base goes through one meter.
   The spec defines an abstract cost per operation of the specified algorithm (per row, per cell
   compared, per byte read, per file matched); this is normative and the same for every
   implementation. An AST test fails if a loop over input-sized data in `reality4/` is not charged
   before it runs. A measured test runs a corpus plus adversarial inputs (findings 18, 20) with an
   operation counter and requires real work ≤ K × charged cost for a fixed K stated in SPEC.
   Quadratic code is rewritten to the linear algorithm the spec charges (inheritance indexed by
   folder and suffix; `key()` redundancy in one pass), not charged quadratically.
2. **Charge only work done**, so finding 20's 200 000 000 steps for 0.4 s goes away (a filter
   over an empty selection costs nothing). Charges then depend on the bytes, which are part of the
   text, so this keeps "the same number on every machine".
3. **Output is bounded and streamed.** A sort's printed length is computed as it is built (each
   literal counts its escaped length); a line over a fixed bound refuses (R006), and the program
   has a total output bound. Lines are written as they are decided, not held. Exit-3 handling
   covers printing.
4. **Memory is bounded (Patsak's call).** Every retained structure (file text, tables, sorts,
   values, metadata, witnesses) is charged accounted bytes when it is kept; the per-program bound
   on accounted bytes is chosen so that the peak memory of every program inside the bounds is
   below a stated **memory floor** M (lean: 2 GiB; to be measured at the bounds). The checker reads
   its memory limit at start (RLIMIT_AS and cgroup `memory.max` where they exist) and, if it is
   below M, checks nothing and says so (exit 3). So either a machine meets the floor and every
   program gets its verdict, or no program is checked. Below the floor is the trusted base
   ("the machine running the checker is a floor like the bytes"), stated in README with the
   number, not a verdict that changes.
5. **Locale and encoding independence.** Manifest paths are strict UTF-8, encoded to bytes, and
   every filesystem call takes bytes paths (never the locale's filesystem encoding). The manifest
   writer walks with bytes paths, refuses (exit 2, clear message) any name that is not UTF-8 or
   fails the manifest path rule, and fails on a missing folder or a bare `--out`. A test forbids
   `str` paths in filesystem calls. The envmatrix corpus gains a non-ASCII `--root` path and a
   non-UTF-8 file name.
6. **Unreadable supplied files** are skipped like non-regular files under `--files` and are
   "not found" under `--root`, so a named one is F001 both ways (finding 16).
7. **State the dataset-size cap.** Under the step bound, the largest BIDS dataset that can form is
   about 770 GB of images (finding 27's arithmetic, which I have not redone). NARPS (about 292 GB)
   fits. SPEC and README state the cap. Conformance certificates (check once, verify a hash later)
   would lift it; that is outside v4.

### 3.3 What it closes, and what it costs

It closes the class "a resource the bounds do not cover decides the outcome": time (every loop is
charged), output (printed size is part of the sort's measure), memory (accounted, with a floor
checked before any verdict), the locale (no path goes through it). Costs: very long lines refuse
(none of the corpus's lines is near any bound I would pick; finding 20's 80 KB line would still
form), a machine below M runs nothing, and an independent implementation must count the abstract
costs exactly.

### 3.4 Open technical choices

- The numbers: memory floor M, per-line and per-program output bounds, K. Lean: measure at the
  bounds in Phase C, then fix them in SPEC; I will report them before freezing.
- How to count work for the K test (lean: `sys.monitoring` instruction events on Python 3.12+,
  which exist on the harness venv's 3.13; the PC and Deck interpreters still need checking).
- The memory floor check on Windows, where RLIMIT does not exist. I do not know yet what the PC
  runs the checker under; the real-data runs have used it. Lean: on a platform with no readable
  limit, read total physical memory and require M of it. *(26 Oct 2026, v4-fixes: Windows reads total
  physical memory (GlobalMemoryStatusEx) and the job object's process and job memory limits, the Windows
  counterpart of RLIMIT_AS and cgroup memory.max; tested by running the checker in a 1 GiB job, KNOWN-OPEN.)*

---

## 4. Other changes in v4

**Overcorrections.**
- 11: fixed by §2.3 (dictionary template).
- 12: V005 is checked over the *selected* rows of a selection (§5.1); `mean(t, col)` over a base
  table with `n/a` still refuses V005.
- 14 and 15: decided, taste calls 5 and 6 (§5).
- CRLF line ends: accepted where one reading exists (§5.1).
- Blank headers in *plain* TSVs (box probe in MERGED.md): the frozen principle §3 says "Duplicate
  or blank headers are refused", so they refuse (T-code); positional reads of other non-K headers
  still form. Technical: the principle already decides it.

**Docs overclaims.**
- "every statement classified once": becomes true by the register test (§2.2), or the sentence
  goes.
- `metatheory/Scope.lean` header: say "a model of the intended design, not a proof about the
  checker"; remove "as kernel.py does it". Lean is not installed on the box, so v4 makes no new
  claim that it compiles unless someone runs it.
- The second implementation: `reality3_ref` parses only the generator's line shapes (finding 23).
  README stops saying it "parses the program text itself". The independent check for v4 is a new
  checker B written from v4's SPEC by Opus 5.5 at medium effort (Patsak's instruction for the
  v3 one), after the spec phase.
- Stale items of finding 25 (SPEC-CHECKLIST, gauntlet counts, exit code 2, envmatrix relative path,
  memory floor sentence).

**Bugs.** Findings 16, 17, 18, 20 (above), the fabricated test copy built with the real volume
counts (24).

**Tests.**
- Every review repro (findings 01–20, all controls) becomes a regression test with its v4
  expected verdict and code.
- The mutation-proposed tests: exit 0 for an accepted program and 1/2/3 for the others; usage with
  no arguments (exit 2); the `manifest` command (arguments, `--out`, printed hash, exit codes); V006
  for an interval touching the cutoff; `fmt` of 0.2, 1/5 and other 5-heavy denominators; the R004,
  R009 and other bounds at their exact edge; `bytes()` printed ranges and boundaries; the printed
  row of a keyed cell; a 3-part key; unknown condition functions and extra arguments (S006);
  `duration` values; Recorded flags; pinned step counts for fixed programs; the S012 line prefix;
  the recording() argument codes. RESULTS-*.md list them by mutant; each gets a test that kills it.
- The mutator workflow is kept as a report (`v4/tools/mutation/`, source override
  `REALITY4_SRC`), not a gate.

**Expressiveness (finding 29, the cheap and principle-safe ones).**
- *Joins on BIDS keys.* A recording's `sub` entity and a participants.tsv row are linked only by
  1.0.1's own key: "one of them has to be participant_id with matching sub-<participant_label>"
  (text line 1238 [ran]). `recordings(b, task, ...)` gives the set of recordings, and
  `recordings(b, task, of = <selection of participants(b)>)` restricts it to the selected
  participants. No author-supplied key.
- *Aggregates over recordings.* `count(rs)`, and `sum/mean/max/min` over `rs` of a quantity from a
  closed list (`events`, `trials("type")`, `volumes`, `tr`), each keeping its precision (Recorded
  stays Recorded) and frame rules.
- *Exact order statistics.* `order(s, col, k)`: the k-th smallest decimal of the selected cells,
  exact. `median` only as in taste call 7.
- *Share within a sub-base.* `share(sel, of = base_sel)`, where `base_sel` must be a selection of
  which `sel` is a refinement (a superset of its conditions); otherwise S006.
- Each addition gets W1/W2 witnesses (§1.3), a sort template, a cost, and must-form and
  must-not-form tests. Nothing in v3 is removed, so expressiveness does not shrink except through
  the decided taste calls and the refusals the BIDS algorithm adds.

---

## 5. Taste calls (decided by Patsak, 25 Oct 2026, about 20:27 UTC+1)

1. **Idleness is structural.** W1 and W2 are judged over every readable input, never over the
   actual bytes alone. This replaces the earlier "on the data" call. So
   `count(where(participants(b), eq("group", "A"))) = 108` forms when every participant is in
   group A, and `key()` no longer refuses a pair that only these bytes make redundant (a key that
   picks not exactly one row still refuses V004). Finding 13 is closed from the `key()` side.
2. **"Should" binds when the bytes can show it.** A 1.0.1 "should" binds when it states a property
   of a 1.0.1-defined file that can be checked from its bytes; a "should" about people or process
   does not. A dataset without a root README refuses (§8.1).
3. **Onsets after the end of a recording refuse (B30)**, as call 3 applied without exceptions. The
   fabricated test copy is rebuilt with the real volume counts.
4. **An exact use counts as tolerance 0** for the one-tolerance rule (S012).
5. **One trailing blank line** is accepted as "no row" only in plain TSVs with two or more columns;
   one-column plain TSVs and every BIDS TSV still refuse it.
6. **participants.tsv rows without a subject folder still refuse (B11)**, recorded in the register
   as Reality's own call 1, not as a 1.0.1 sentence.
7. **Median** forms only for an odd count of values; `order(s, col, k)` gives the k-th smallest.

Also decided earlier and applied above: the bounds bound memory (§3.2.4); "should be coded as n/a"
binds (§2.3, row 08); the one-tolerance rule means one cell however it is written (§1.5).

### 5.1 Added to the scope after the design check

**CRLF line ends in TSVs.** v3 refuses every CR (T002) and gives "it could end
a line or belong to a cell, two readings" as the reason. Technical decision:

- *Plain TSV (Reality's own reader).* The reader is fixed before any claim, and in v3 no cell can
  hold a CR in any accepted file. So if the reader defines "CR immediately followed by LF" as a
  line end, a CR before LF has one reading: it cannot be cell content in either rule, because no
  accepted file has a cell with a CR. The "two readings" reason was never about Reality's reader;
  it was about what the file's writer may have meant, and that is the false side (content), not
  the reader's. **Accepted:** CR LF ends a line, the same as LF. A CR that is not immediately
  followed by LF (a lone CR, or a CR at the end of the file) still refuses T002: there it really
  is either an old-style line end or a byte of a cell, and the reader cannot tell. Lines may mix
  LF and CR LF; each line end has one reading either way.
- *BIDS TSV.* 1.0.1 §4.2 (text line 282) calls TSVs "aka csv files where commas are replaced by
  tabs". My reading: this sentence ties the line structure to the CSV convention, where CR LF is a
  line break, so the register cites it as fixing the reading and the BIDS reader accepts CR LF too.
  This is a reading of 1.0.1, made by me as a technical call, and a reviewer may contest it. If it
  is rejected, CR LF in BIDS TSVs becomes a B30 choice point, and C1/C3 can still be stated through
  the plain reader. *(26 Oct 2026: superseded by §9 call 2. CR LF stays accepted, as Reality's own
  call; "aka csv files" is no longer cited as fixing the reading.)*
- The JSON reader already allows CR as whitespace (RFC 8259); the manifest and program text keep
  refusing CR (M001, P009), because they are Reality's own formats and have no reason to allow it.

**Numbers read only within a selection** (overcorrection 12, needed by C1, where an excluded row
holds `"30 "`). `sum/mean/max/min/order/median/variance` read and check (V005) only the cells of
the selected rows. On a base table every row is selected, so `mean(t, col)` with a non-decimal
cell anywhere still refuses V005. The idle-part rule (W2) applies to the selection as usual.

**Variance and standard deviation (C1, C3, C7).** Defined exactly:

- `variance(s, col)`: the sample variance `Σ (x − m)² / (n − 1)` of the selected decimals, an exact
  rational; n < 2 refuses V003. `pvariance(s, col)`: the population variance `Σ (x − m)² / n`;
  n < 1 refuses V003. Both are exact functions of the bytes and need no tolerance.
- `sd(s, col)` and `psd(s, col)`: the square roots. They are exact real numbers but usually not
  rationals, so v4 represents an SD as the exact pair "square root of the rational v" and never
  rounds it. A comparison `exceeds/below/atleast/atmost(sd(...), c = q)` is decided exactly: for
  q ≥ 0, `sd > q ⇔ v > q²`, and so on; for q < 0 the comparison is constant and refuses S008/S011
  by W1. Printed as `= sqrt(v) (Exact)` with v printed as any exact rational, plus nothing
  rounded. `difference` of an SD with another number is not defined in v4 (it would need
  irrational arithmetic) and refuses S006; `widen(sd(...), tolerance = q)` is allowed and gives the
  interval [sqrt(v) − q, sqrt(v) + q], whose comparisons are again decided exactly by squaring
  where the endpoints are non-negative.
- Recorded values: a variance of Recorded values (onsets, durations, TRs over recordings) stays
  Recorded and keeps its unit squared for variance and its unit for SD.
- C1's claim becomes, for example, `below(sd(where(t, eq("Group", "F")), "MMSE"), c = 8.22)`,
  which holds exactly.

The names are a new taste call (§5.2).


### 5.3 Added from testing on real datasets (25 Oct 2026, 20:50 UTC+1)

**Blocker 1: single-recording facts.** The request: let "this recording's RepetitionTime is 1.52 s"
form with a typed sort, without the full 1.0.1 dataset check, and without dropping the dataset
reading the meaning depends on (inheritance).

*Finding: as a BIDS fact it cannot, and stays refused.* "This recording's RepetitionTime" is a
BIDS meaning: which sidecar value applies is fixed by 1.0.1's inheritance principle (v3 SPEC "Inheritance", the
lower-level file wins; two files at one level both setting the key is a B30 choice point), and
which rule applies at all is fixed by the version the dataset declares in
dataset_description.json. Reading only the recording's own sidecar silently assumes there is no
same-level competitor and no other version, which is exactly a silent choice. Reading the folder
chain and the declaration but not the rest of the dataset contradicts the frozen principle's
whole-dataset conformance clause ("If any file the version requires is missing ... nothing
BIDS-based forms from that dataset"). So a partial-dataset BIDS reading is not principle-safe, and
v4 does not add one. `tr(r)`, `volumes(r)`, `trials(r, ..)` stay behind `bids(d)`.

*What can be said, principle-safe, today:*

1. **The NIfTI header of one file** (`nifti(f)`, then `dim(n, k)`, `pixdim(n, k)`): the principle
   already lists NIfTI among the plain file-level readers that form without the standard. The sort
   says what was read, e.g. `Pixdim[NIfTI-1[#1], 4] = 1.52 s (Recorded)` and
   `Dim[NIfTI-1[#1], 4] = 240`: the time unit comes from the header's xyzt_units code, which the
   NIfTI-1 standard fixes, so it is a typed value and not "bytes at offset 80". A .nii.gz is read
   by the gzip magic bytes (1f 8b), which cannot begin an uncompressed NIfTI-1 header (that begins
   with sizeof_hdr = 348), so the choice has one reading. This states "the image header records a
   repetition of 1.52 s and 240 volumes", which is what C9/C11 compare; it does not state the BIDS
   RepetitionTime. Planned for Phase F; not built yet.
2. **A sidecar's JSON member** (`json(f)`, `member(j, "RepetitionTime")`, sort
   `JSONMember[JSON[#1], "RepetitionTime"] = 1.52`, no unit, duplicate keys refused). This would
   replace the `bytes(f, 884, 4)` workaround with a parsed, typed member. **But the frozen
   principle lists only the TSV, NIfTI and bytes readers as file-level readers**, so this needs
   Patsak to add JSON (RFC 8259) to that list. Taste call 4 below; not built.
3. **Cheaper `bids(d)`** (a cost change, not a meaning change): conformance needs every required
   file present and hashed by the manifest; whether it also needs every NIfTI header parsed is a
   register question (does a malformed header make a 1.0.1 dataset non-conformant?). If the
   register says headers are checked only when a claim reads them, `bids(d)` no longer costs a
   full read of every image. Open; decided in Phase E with the register.

**Blocker 5: number conditions in `where`.** Built: `ge/gt/le/lt(col, c = q)` (SPEC 7.3). The
cutoff is a printed parameter; no unit (a cell decimal has none, U002). Byte conditions run first
and number conditions after. A non-decimal cell in a row a number condition reads refuses V005
(skipping it would be the choice C1's `"30 "` shows) unless another condition is false on that
row, so the verdict does not depend on the order the conditions are written in. (Amended by
v4-fixes 18: before, a later number condition read only the rows earlier ones kept, so one
order formed and the other refused. BB's call on Patsak's behalf (2026-10-26), reversible: "false
and no-answer is false" was chosen over "every number condition reads every byte-selected row",
because the dropped row's answer does not depend on the unreadable cell, and no claim that formed
before refuses now.) Contradictory or implied number conditions
are refused by W1/W2 (S011/S008), not by a hand rule.

**Blocker 6: share of a selection.** Built as `share(sel, base)` (two arguments; parameters
cannot hold expressions, so `of = base` from the earlier draft is not written). `base` is the
table or a selection of it whose conditions are all conditions of `sel`, so `sel` is a part of
`base` whatever the file holds (else S006); equal conditions refuse S008 (the share is 1 wherever
defined); `base` with no rows refuses V003.

**Blocker 7: median and quantiles.** `median` (odd count only) and `order(s, col, k)` are built.
Quantiles are not added: there are at least nine conventions in use (Hyndman and Fan 1996), so
"the 25th percentile" has more than one reading. Taste call 5 below.

### 5.2 New taste calls (not decided; my leans)

1. **Which variance is "variance".** Sample (n − 1) and population (n) are two conventions, and
   C1's check needs the sample one (the reported SDs in C1 and C3 match the sample formula).
   **Lean:** `variance`/`sd` are the sample ones and `pvariance`/`psd` the population ones, each
   printed with its own sort name (`SampleVariance[...]`, `PopulationVariance[...]`), so the
   printed claim never leaves the convention unsaid. The alternative is to have no bare
   `variance` at all and only `svariance`/`pvariance`, which is more explicit and less readable.
2. **Numeric selections** (C2, C6 need "BDI < 7", "score of 4 or higher"). Not in the brief.
   `where(t, ge(col, c = 4))` with a cutoff parameter is principle-safe (the cutoff is a printed
   parameter; the cells must be decimals in the selected-from rows, V005). **Lean:** add it in
   Phase F, after the brief's own additions.
3. **List cells** (C7, `22,23` in one cell). Splitting a cell on commas is a reading rule that no
   standard Reality reads fixes; 1.0.1 does not define it. **Lean:** do not add; C7 stays
   unstateable, as the principle requires.

4. **JSON as a file-level reader** (blocker 1, §5.3 item 2). Adding `json(f)`/`member()` lets a
   sidecar value be stated as a typed JSON member without the dataset check. It needs a change to
   the frozen principle's list of file-level readers. **Lean:** add it, with the sort naming the
   JSON member and never the BIDS concept, so nobody can read it as "the recording's TR".
5. **Quantiles** (blocker 7). **Lean:** no `quantile()`; `order(s, col, k)` states any exact order
   statistic, and a paper's "25th percentile" is checked by writing the k its convention gives. The
   alternative is `quantile(s, col, p = 1/4, rule = hf7)` with the rule a closed-list parameter,
   which needs a new closed list in principle §10.1.
6. **Whether a single NIfTI header's pixdim[4] is "Recorded"** (§5.3 item 1). It is a float32 the
   header states with a unit code and no precision. **Lean:** Recorded, by principle (i), with the
   exact binary value converted to a rational (1.52 as float32 is 1.519999980926513671875; printed
   as that rational and compared with the one-tolerance rule).

## 6. Risks

- **Overcorrection from the witness builder.** If it misses witnesses, real claims refuse. This
  is the main risk to expressiveness. Mitigation: the brute-force measurement, the must-form list
  and the corpus as hard checks.
- **BIDS witnesses** need a generated conformant dataset per BIDS claim. It is the most complex new
  code in the trusted base. If it proves too large, a fallback is a leaf-level abstraction checked
  against the reader on fixtures; that is weaker (a mistake there could form an idle BIDS claim),
  and I would report it as such rather than use it silently.
- **The register is a long manual job** (about 530 sentences) and the place where a wrong
  "this sentence fixes it" can hide a silent reading. A reviewer needs to read it.
- **The real dataset may stop conforming** under the new classification, dictionary and README
  rules. Then either the rule is wrong or v3 formed claims on a dataset 1.0.1 does not settle.
  Only the PC run decides.
- **The trusted base grows** (witness builder, meter, register test), against Theseus-style
  minimalism. The builder is outside the soundness argument (a wrong builder can only refuse), so
  the base that matters grows less than the line count does.
- **Time.** At 50-minute worker slices this is several sessions. The phases below are cut so each
  ends in a commit with tests passing.
- **An independent checker for v4** has to implement witness building to agree on verdicts. The
  bounded-enumeration part must be specified exactly (which tables, in which order), or two
  checkers may disagree on overcorrections while both being sound.

## 7. Phases

| phase | content | ends with |
|---|---|---|
| A | this design | commit; stop for review |
| B | v4/SPEC.md (from v3 SPEC, rewritten for the three mechanisms), the register format and splitting rule | spec commit |
| C | code skeleton in `v4/src/reality4` (copied from v3, renamed), Mechanism 3 (meter, bytes paths, streaming output, memory floor, unreadable files, manifest writer); v3's 336 tests ported and passing | commit, envmatrix |
| D | Mechanism 1 (witnesses, affine `widen`, value identity, S012); review repros 01, 02, 12, 13, 19 | commit, brute-force report |
| E | Mechanism 2 (decisions, choice points, register filled, B30, dictionaries, n/a); repros 05–11, 21 | commit |
| F | expressiveness additions | commit |
| G | the mutation-proposed tests, all review repros, envmatrix with the new corpus, acceptance table, mutation report | commit |
| H | real-data run on the PC (ds001734) | LOG entry with the result |
| I | checker B for v4 (Opus 5.5 medium), then an Opus review; Argon kept for a large review | reports |

Nothing is pushed at any phase. Phase H is started only after a stop and a report.

## 8. Taste calls from the Opus 5.5 v4 review (BB's calls on Patsak's behalf, 2026-10-26, reversible)

- **02, one condition written twice.** BB's call on Patsak's behalf (2026-10-26), reversible: a claim in which the same condition appears twice refuses, whether its column is named by header or by number. The witness judges the statement as it formed: a header is the position it resolved to on the real bytes, so `where(t, eq("g","F"), eq(2,"F"))` on a table whose column 2 is `g` has an idle part and refuses S008 (W2); a contradictory pair refuses S011. Positions no part reads get one fresh candidate value instead of two (they cannot change an answer), which keeps the witness inside its budget.
- **09, JSON exponents.** BB's call on Patsak's behalf (2026-10-26), reversible: principle §11 is amended with a dated line saying a JSON number with an exponent is read with its exact value, per Patsak's decision of 2026-10-25 21:36 (SPEC §6.4). The text before is kept in `/workspace/team/research/principle-nonsense-unformable.pre-amendment-2026-10-26-json-exponents.md`. No code change: v4 already read them so.
- **12, participant_id and column-description keys.** BB's call on Patsak's behalf (2026-10-26), reversible: participant_id must be the first column of participants.tsv ("followed by", S0556; B11 otherwise), and a column-description key 1.0.1 does not list (LongName, Description, Levels, Units, TermURL; Derivative too in participants and phenotype files) refuses B30 (S0568). The witness builds its participants candidates with participant_id first and reads column-1 literals as participant ids.
- **13, a share within a subset.** BB's call on Patsak's behalf (2026-10-26), reversible: no new spelling. The existing one, `share(where(t, <base conditions>, <own conditions>), where(t, <base conditions>))`, now forms: W2 judges a sel condition that S006 makes sel repeat from base by removing it from both, so it bears exactly when the base condition does. A condition written twice in sel is still judged in sel alone and refuses (call 02). The nested spelling `share(where(where(t, base), own), where(t, base))` still refuses S008 (KNOWN-OPEN).


## v4-fixes 11: SliceTiming's slice axis (26 Oct 2026, 12:00 CET)

BB's call on Patsak's behalf (2026-10-26), reversible: no new rule; Mechanism 2 (the 1.0.1 silence algorithm) applied. The sentence relied on, BIDS 1.0.1 §8.4 (register S0369): "The list goes through slices along the slice axis in the slice encoding dimension (see below)." The "see below" is SliceEncodingDirection (S0372-S0374): "SliceEncodingDirection: Possible values: “i”, “j”, “k”, “i-”, “j-”, “k-” (corresponding to the first, second and third axis of the data in the NIFTI file; ...). The axis of the NIFTI data along which a slices were acquired. This value needs to be consistent with the ‘slice_dim’ field in the NIFTI header." BIDS 1.0.1 names no default slice axis (nothing in context/sources/bids-1.0.1.txt says k, or any axis, applies when SliceEncodingDirection is absent). So the axis is fixed by SliceEncodingDirection or slice_dim when either is given (the length must fit it, else B10); otherwise the reading is unambiguous only when the length fits exactly one spatial axis, and B30 when it fits more than one. A length that fits no axis is B10: every reading agrees it does not conform, so it is not a choice point. ds001734 (all 106x106x64, SliceTiming 64; dim_info 48 or 0) forms: dim_info 48 names k (64 fits); dim_info 0 leaves 64 fitting k only.

## 9. Taste calls on the full Opus v4 review (BB's calls on Patsak's behalf, 2026-10-26, reversible)

- **Call 1, onsets past a run's end.** BB's call on Patsak's behalf (2026-10-26), reversible: they keep refusing B30 (§5 call 3), but as Reality's own rule, not as a 1.0.1 ambiguity. 1.0.1 does not say an event must fall inside its run, so the register row S0412 is now `reality-call` (codes B30, no decision) and the reader raises B30 directly with a message that says "Reality's own rule (DESIGN section 5, call 3; register S0412), not by a reading of BIDS 1.0.1", instead of going through `choice_point`. ds001734 is unaffected (latest onset 441.062 s inside 453 x 1 s; Phase H passed with the rule on).
- **Call 2, CR LF in BIDS TSVs.** BB's call on Patsak's behalf (2026-10-26), reversible: accepted, as Reality's own call, not as a reading of 1.0.1. 1.0.1 says nothing about line ends; the earlier reading of §4.2's "aka csv files" as fixing them is withdrawn. Register S0145 is `reality-call` (B04) with that note. The readers are unchanged: CR LF ends a line like LF, mixed line ends refuse (T010; B04 in a BIDS TSV), a lone CR refuses (T002). ds001734 has no CR in its 433 TSVs.
- **Call 5, leading zeros.** BB's call on Patsak's behalf (2026-10-26), reversible: wherever a cell is read as a number, a leading zero refuses, so TSV, CSV and JSON share JSON's number grammar `-?(0|[1-9][0-9]*)(.[0-9]+)?([eE][+-]?[0-9]+)?` (SPEC 6.4). `007`, `00`, `-01`, `00.5` and `01e1` are not numbers: V005 in the kernel's number paths (number(), sum/mean/min/max/variances/order/median, number conditions), B06 for a BIDS onset or duration, J001 in JSON as before. `0`, `-0`, `0.5` and exponents with leading zeros (`1e05`, as JSON allows) still read. `cell()` still states the bytes. The reference implementation (src/reality4_ref) reads the same grammar. ds001734 is unaffected: 0 leading-zero numbers in its 433 box TSVs and in all 545 TSV/CSV/JSON files of the real copy (PC, read-only, 26 Oct); the acceptance table is unchanged.
- **Call 6, the §12 delimiters.** BB's call on Patsak's behalf (2026-10-26), reversible: §12 stays as written (CSV refuses a tab or semicolon outside quotes; '|' in CSV and ',' in TSV are cell bytes). A dated note at the end of principle §12 says why; the text before it is kept in `principle-nonsense-unformable.pre-amendment-2026-10-26-delimiters.md`. No code change; ds001734's TSVs hold no comma, semicolon or pipe.
- **Call 3, README in derivatives/ and sourcedata/.** BB's call on Patsak's behalf (2026-10-26), reversible: the bytes are the floor. Reality judges the manifest; a folder with no file contributes no bytes and no manifest entry, so it is not part of the dataset as Reality reads it. S0126 ("A README file should be found at the root of the sourcedata or the derivatives folder (or both)", §3.4) binds whenever the manifest holds a file under `derivatives/` or `sourcedata/`: no `<folder>/README` then refuses B01. With no file there it binds nothing. `readers.make_manifest` lists regular files only (`os.walk` file names), so empty folders never reach a manifest. ds001734 forms: on the PC its `derivatives/` is 1,525 empty folders and no file, and `sourcedata/` does not exist.
- **Call 4, CHANGES and the precedence of BIDS's examples.** BB's call on Patsak's behalf (2026-10-26), reversible (option (a) after a first, blanket rule was withdrawn because it made broken JSON conform). A BIDS 1.0.1 example counts as BIDS's own reading only if it is well-formed in its own kind's grammar (it has at least one reading as what it claims to be). An example with no reading at all is an erratum: it binds nothing and the reference stays strict. Where a well-formed example conflicts with a normative reference, the example's form conforms for that point only; everything else in the reference binds, checked from the bytes. For CHANGES (S0235): `1.0.1` is a well-formed version (BIDS versions itself so, cf. BIDSVersion), so dotted versions need no leading `v` and may have zero components; the rest of CPAN::Changes::Spec 0.04 and CPAN::Meta::Spec's Version Formats is checked strictly (SPEC 8.5; B31 for a missing required element or mixed line ends, B30 for a point with two readings). Sources pinned in team/research/sources with sha256 (CPAN tarballs matching CPAN's CHECKSUMS). ds001734's CHANGES (sha256 362a1f07…, 321 bytes) forms: dotted three-part versions (the example's point), a tab separator on the 1.0.0 line ("must start with whitespace"), blank lines ("optional"; "empty lines hold no special meaning"), a tab-indented change ("(whitespace)<Change>"), a trailing space after "Fix license" ("Change lines have no specific format"), valid YYYY-MM-DD dates.

  **Audit of register rows that rely on a normative reference or carry an example** (examples checked against the rendered PDF, not only the text extraction):

  | rows | reference / example | outcome under the rule |
  |---|---|---|
  | S0231-S0232 | 8.1.1 dataset_description.json example (PDF p.11): no comma after `"Authors"` | erratum, not JSON; binds nothing; JSON strict (B03); no verdict change |
  | S0400 | 8.4.1 bold JSON example (p.17): `"InstitutionAddress: "450 …`, no comma before `"DeviceSerialNumber"` | erratum; no verdict change |
  | S0565 | 8.11 phenotype JSON example (p.28): trailing comma | erratum; no verdict change |
  | S0235, S0237-S0240 | CPAN Changes + Version Formats; example `1.0.1 2015-08-27` (p.11) | the intended change: the new CHANGES check; leading `v` and zero components waived by the example |
  | S0545 | scans.tsv acq_time, RFC 3339; example `2009-06-15T13:45:30` (offset-less, well-formed ISO 8601 local time) | noted: an offset-less date-time will conform when scans.tsv is implemented; today B14, no verdict change |
  | S0160-S0161 | 4.2.2 participants.json example (p.7-8) | valid JSON (the extractor interleaves footnote 2 and the page footer); no conflict |
  | S0161 | TSV example with two successive tabs | BIDS's own format, not a reference; the text says it "should not happen in an actual BIDS tsv file"; no change |
  | S0162-S0167 | JSON (json.org; Reality reads RFC 8259); 4.3.1 example | valid; no conflict |
  | S0454 | 8.6 physio JSON example | valid; physio is B14 |
  | S0491-S0492 | 8.8.3 dwi JSON example | valid; dwi is B14 |
  | S0496, S0498, S0510 | 8.9 IntendedFor / phasediff JSON examples | valid; no conflict |
  | S0520, S0528, S0535 | 8.9.2-8.9.4 fieldmap JSON examples | the text extraction misplaces a quote; PDF p.25 renders valid JSON; these kinds are B14 |
  | S0140 | NIfTI-1/2 (B05) | no example bytes in the text |
  | S0295 | pixdim[4] vs RepetitionTime (B09) | no example header |
  | S0372-S0374 | SliceEncodingDirection vs slice_dim (B10) | no example header; the 8.4.1 example has no SliceEncodingDirection |
  | S0177 | ISO 8601 date-time | unshowable; no check |
  | S0029, S0172, S0305-S0398, S0399 | DICOM tags and ontology | unshowable or reality-call; nothing checked |
  | S0251-S0252, S0430, S0486 | literature URLs | no grammar taken from them |
  | S0002, S0041, S0143-S0144, S0165, S0631-S0632 | links (site, tools, validator, licenses) | notfiles |
  | S0232 `"BIDSVersion": "1.0.0rc1"` | BIDS's own version rule, not a reference | unchanged (B02) |

  No verdict changes outside CHANGES.

## 10. Trusted-base cap: 4,300 -> 4,335 (BB's technical call on Patsak's behalf, 2026-10-26, reversible)

The Windows memory floor (v4-fixes aa0e1a1: the job object's process and job memory limits, KNOWN-OPEN "The memory
floor on Windows") was first fitted under the 4,300 cap by compressing its Windows structures (MEMORYSTATUSEX's tail
folded into one array, JOBOBJECT_EXTENDED_LIMIT_INFORMATION's fields renamed to short names, lines over 100
characters). That optimised the count, not the audit. The structures are now written with their documented Windows
field names and layout (JOBOBJECT_BASIC_LIMIT_INFORMATION + IO_COUNTERS + ProcessMemoryLimit, JobMemoryLimit,
PeakProcessMemoryUsed, PeakJobMemoryUsed; MEMORYSTATUSEX in full), in the file's established style, with the same
behaviour. Measured base: 4,335 (`machine.py` 111). Following the CSV precedent (25 Oct 2026 22:29 CET, a reader
added after the cap was set), the cap is raised to exactly the measured count, 4,335, for one reason: readability of
trusted code over line count. No lines were freed elsewhere by compression. The 4,000 target stays and is not met.
## 10. Exact decision for W1/W2 (branch exact-decision; plan in plans/exact-decision-procedure.md)

Patsak approved 26 Oct 2026 19:15 CET: exact decision first, then the wedge. BB's calls on Patsak's behalf
(2026-10-26, reversible) on the plan's direction questions: variances/SDs must be decided exactly before the
switch-over (no regression, the old search is not kept for them); one honest trusted-base count, the cap
raised only by the measured amount at the switch; unbounded readable inputs with R013 when the smallest
witness is beyond the bound; a new code S013 for statements outside the decided fragment; core Lean
preferred; the 4,000-line target stays stated and unmet; the nested-share/W2-level question is decided
when its phase comes; brain claims are Patsak's, later. Until the switch-over, `witness.py` decides every
verdict and nothing in the trusted base changes.

### 10.1 D4: the nested share spelling stays refused (BB's call on Patsak's behalf, 2026-10-26 20:40 CET, reversible)
`share(where(where(t, ne("group","P")), eq("group","A")), where(t, ne("group","P")))` refuses S008. Call 02 (the
same condition printed twice refuses) and call 13 (one minimal spelling for a share within a subset; a repeated
base condition is dropped from both sides) give Reality exactly one spelling per meaning. In the nested form the
inner `ne` restates the base inside the numerator: it is the base condition said twice. Making it form would give
one meaning two spellings. The cost is paid in work: the S008 message for this shape names the flat spelling that
forms (`witness._one_spelling`; tests/test_d4_nested_share.py: plain, `atleast`-wrapped and extra-condition
variants). That takes `witness.py` from 849 to 868 lines and the base to 4,354, 19 over the 4,335 cap; the cap is
not raised on this branch without BB's word (README states the number). The exact procedure decides the same
judging level (plan section 15), so this verdict is unchanged by the switch-over; the message has to be carried
into the exact path in phase 3.

## 10.2 Trusted-base cap: 4,335 -> 4,354 (BB's technical call on Patsak's behalf, 2026-10-26 21:29 CET, reversible)

The D4 message (10.1) is 19 measured lines in `witness.py`. The cap rises by exactly those 19 lines, for the same
reason as 4,335: an honest count, and the message is not trimmed to fit. From here the cap moves only by measured
amounts at each exact-decision phase checkpoint, and each move is logged here and in LOG. Target 4,000 unmet.

## 10.3 Trusted-base cap: 4,354 -> 5,340 (exact-decision phase 3 checkpoint, 27 Oct 2026, under the cap rule of 26 Oct 21:29)

Phase 3 makes part-T verdicts depend on `intstep.py` (182 lines, the integer step, SPEC-EXACT 4) and `decide.py` (799
lines: the model, the cases of named rows, the elimination of named cell values, the questions and certificates,
SPEC-EXACT 2-8), and `witness.py` gains 5 lines that call them (868 -> 873). Measured base: 5,340 = 4,354 + 5 + 182 +
799. Under BB's cap rule (26 Oct 2026 21:29 CET: the cap moves only by measured amounts at each phase checkpoint,
logged), the cap rises by exactly 986 lines to 5,340. Nothing was compressed, joined or moved out of the trusted
files to fit. `decide.py` was 392 lines at the handoff; the growth to 799 is BB's ruling 3 (26 Oct 22:12: number
conditions, `cell`, `key`, `header` and `number()` in part T) plus the generic branches/cases structure it needs.
The old search (`witness.Plan` and the search in `witness.check`) still counts and is deleted in phase 7 (BB's
ruling 1); the plan's §6 estimate of its removal is about 330-360 lines. The 4,000 target stays and is not met.

## 10.4 Trusted-base cap: 5,340 -> 5,729 (exact-decision phase 4 checkpoint, 27 Oct 2026, under the cap rule of 26 Oct 21:29)

Part N (SPEC-EXACT 3.5: sums with a case for which summed types have rows, order statistics by a value variable and
counted pieces (L4), widen with value identities; 4.1's presolve of equalities and 4.2's exact rational relaxation
with its checked Farkas certificate) takes `decide.py` from 799 to 1,188 lines. Measured base 5,729; the cap rises by
exactly 389 lines to 5,729. Nothing compressed, joined or moved out. The 4,000 target stays and is not met.

## 10.5 Trusted-base cap: 5,729 -> 5,904 (exact-decision phase 5 checkpoint, 27 Oct 2026, under the cap rule of 26 Oct 21:29)

Part H (SPEC-EXACT 3.6: JSON paths as cases of node kinds and presence, NIfTI dim[0] as a case and dims as naturals,
a raw file's size as a natural; their certificate files) takes `decide.py` from 1,188 to 1,363 lines. Measured base
5,904; the cap rises by exactly 175 lines to 5,904. Nothing compressed. The 4,000 target stays and is not met.

## 10.6 Trusted-base cap: 5,904 -> 6,048 (exact-decision variance phase checkpoint, 27 Oct 2026, under the cap rule of 26 Oct 21:29)

Part V (SPEC-EXACT 3.7: a variance or SD alone or compared with a cutoff; W1 by its free classes and the bounds of
Exact.Var, W2 through refusals; certificate tables built from two rows) takes `decide.py` from 1,363 to 1,507 lines.
Measured base 6,048; the cap rises by exactly 144 lines to 6,048. Nothing compressed. The 4,000 target stays unmet.

## 10.7 Merge of v4-fixes: 6,048 -> 6,243 (BB, 27 Oct 2026, measured)

v4-fixes (the fix pass, DESIGN §11, and the O pass, §12) was merged into exact-decision-opus (`git merge --no-ff`;
conflicts only in the docs, the cap comments, the pinned steps and one witness.py hunk, where both sides were kept). Its
155 measured lines come with it: 6,048 + 155 = 6,203. The fix pass's R3 (W2 for a file slot: with the other files
held, two inputs of the slot give different answers) lived in witness.check's search, which part-T statements no longer
reach, so three R3 tests failed after the merge. `Decide.slot_bears` decides it exactly: the statement and its copy
reading a second file n' in n's place, both answering (refusals are no answer, SPEC 4.2), differ on some input, found
by `w2_input` over the model of both and confirmed on the certificate by the real code (X001 otherwise). The copy's
cases are taken one at a time (`Model.only`), each one's work charged, so the pair costs the sum over the copy's cases
and the MAX_CASES bound applies to each model as before (a first version built the product and turned partH's ph293
from formed into R013). +40 lines in `decide.py`; base and cap 6,243. Nothing compressed.


## 10.8 Trusted-base cap: Part B (BB on Patsak's behalf, 27 Oct 2026, measured moves only)

Each Part B item (verify-opus-exact/REPORT.md P1-P4, D1 and the part-N, pixdim, raw-size and pn535 items) moves the
cap by exactly its measured amount, in its own commit. Nothing compressed. The 4,000 target stays unmet.

| item | file deltas | base | cap |
|---|---|---|---|
| item 7 | decide +1 (off_t bound atom instead of the MAX_ROWS atom), witness +17 (Periodic certificate file; evaluate and text read it) | 6,261 | 6,243 -> 6,261 |
| P1+P2+P4 | decide +69: the readable set R (mant, in_r, scale, above, below_r, nxt, prv: +60), dec_seq exponent spellings, inside/split/back/type_rows readable or Big, Decide.ends replacing the var_rows search (-27) | 6,330 | 6,261 -> 6,330 |
| item 8 | decide +42: Model.solve splits a summed type's presence only where a solution breaks it (solve +25, inside_sum +11 with its blank line, one_solve = the old solve under a new def line +2), Unreadable +4, agg_cases without the presence product -2, case_atoms closed bounds and y = 0 for "no rows" 0 (-3, +3), type_rows +2 | 6,372 | 6,330 -> 6,372 |
| call 4 (5b sort rule) | kernel +11: is_square (a variance, a widen of one or a difference of two, by its sort; +9) and the S006 test in difference (+2) | 6,383 | 6,372 -> 6,383 |
| call 2 (exact search over R's bands) | decide +124 (measured total by tools/readme_trusted.py): new bands, band, Model.cbands, part_atoms, realize, refine, unrealized; changed split (runs), back (a sum's finest-step point), Model.solve (band and sum splits), one_solve (parts; integer-step calls charged in 64-bit words), type_rows (runs) | 6,507 | 6,383 -> 6,507 |
| call 2b (enumeration rule in intstep) | intstep +27: ub, cost; pick by cost; decide's enumeration branch (Exact.enum_rule) | 6,534 | 6,507 -> 6,534 |
| call 3 (thin pieces of ordered columns) | decide +40: Model.thin, Model.gap_cases; Model.solve splits a thin piece | 6,574 | 6,534 -> 6,574 |
| item 5a (widen variance shapes) | decide +126: vchain, width, root, Decide.var_cands (moved from w1_var), w2_widen, var_hit, var_differ, var_out; w1_var rays with c ± w; outcomes_differ, shape, ident, the model gate | 6,700 | 6,574 -> 6,700 |
| item 5b (c) (difference of two variances) | decide +252: dchain, pneg, pclip, pmeet, rays, var_of; Decide.w1_dvar, w2_dwiden, wpieces (moved from w2_widen), d_hit, d_domain, slot_dvar, d_out and d_confirm (var_out, var_confirm generalised to several slots and columns), differ_on; var_cands returns the selection and ruled-out types; shape, br, outcomes_differ, the model gate | 6,952 | 6,700 -> 6,952 |
| item 6 (d) (named rows with aggregates) | decide +31: Extra.npc; Model.cases (named rows' pieces), case_atoms (named values' classes and pieces), total and order_atoms (named rows); the model gate narrowed to variances | 6,983 | 6,952 -> 6,983 |
| item (g) (order of the work in find) | decide +27: Model.find solves the options in rounds under a growing step cap, with a pass of row counts of at most two rows after the first round | 7,010 | 6,983 -> 7,010 |
| item (h) (5a/5b R013 narrowed) | decide +97: OverRows; var_hit's shown over-bound pieces (g²/(2(N − d))) and two_vals (every n of the two ends' rows, within MAX_TEXT_FILE); vrow; one row per value in the ends multisets; d_domain items read alike merged; d_scale (degree-2 scaling); dec_seq memoised; w2_widen keeps the shown reason | 7,107 | 7,010 -> 7,107 |
| #4 (fewest rows first in find) | decide +9: Model.find re-solves a solution of more than 64 rows per slot with at most 2, then 64, rows per slot | 7,116 | 7,107 -> 7,116 |
| (d) leftover (named rows with a variance) | decide -2: Model's NotT gate for named rows and a variance of one table removed (unreachable: SPEC-EXACT 3.7, no named rows) | 7,114 | 7,116 -> 7,114 |
| (f) pixdim decided exactly | decide +182: pixdim in the model (NCase unit cases, f·u float variable, NIfTI-2 certificates); float helpers (fstep, is_float, fup, fdown, fnext, fpick); float ranges on lattices (RAtom, frange, frange_of, frange_split) split in Model.solve; empty_box bounds propagation; lp keeps its reduced-cost row; one_solve memo for pixdim models | 7,296 | 7,114 -> 7,296 |
| (e1) mean inside a difference | decide +123: PAtom (S = mu·N), prange (hull and McCormick per N range), Model.mu (mu with class-end cuts), Model.solve's N-range, nested-means and end cases, same_means, nest, cends; the solver's sort keys by variable | 7,419 | 7,296 -> 7,419 |
| (e2) column both summed and ordered | decide +111: agg 'both'; Model.pieces/piece_atoms (a summed type's sum as its pieces' sums, odd pieces w_j·P, even pieces v·P between the order statistics), shared sign splits per piece variable (psign), pcuts (a mean's cases between its lowest and highest piece's ends and its other types' class ends), type_rows piece by piece; fm and lp charged before their work (SPEC-EXACT 8); in Model.solve a broken presence of a mean's type split before its count; Model.find counts an option's rounds once (its largest) and its two-row pass solves one system per row total under the first round's cap | 7,530 | 7,419 -> 7,530 |
| (pm) the shared types' mean | decide +34: caps (for two means of one column whose rows share types without either holding the other's, a free mean of the shared types with nest's cases for each); cap_ok (whether a solution admits such a mean: the cases are linear in it, roots and the points between tried exactly); Model.solve splits on a cap's cases only at a solution breaking S = mu·N that no shared mean admits (split up front, they cost a 4-row claim 228.8 s and R013, formed in 2.9 s before); PAtom.k, the mean's (slot, column): nest compares means of one column only (it matched means by their row counts, so two columns' means over the same rows were compared as one column's: a false S008 W1) | 7,564 | 7,530 -> 7,564 |
| item 2 look-alike literals | decide +27: the NotT gate for two look-alike literals on one column removed; Model.scope (K002, principle 10.3: per where()/key() and column, the literal classes that look like one of its literals and are not, and 2^g presence patterns per skeleton group, give cases that refuse with no answer); br passes a no-answer X result on like a refusal | 7,591 | 7,564 -> 7,591 |
| item 2b BIDS participants | decide +24: participants(bids(d)) is the table slot d of kind pt (FNS bids, participants; tslot for W.slot_of's P:d; table() writes participant_id and sub-w<i> labels, readable() reads with bids101.bids_tsv, column 1 not compared; bytes_of wraps the table in witness._dataset; run() keys a dataset by its manifest hash; slot_bears' copy keeps the real kinds; reading column 1 is NotT) | 7,615 | 7,591 -> 7,615 |
| item 2c BIDS tr, volumes, onset | decide +103: a dataset slot of kind rec (recording(bids(d), labels)); RCase per named recording (absent: V004; dim[0] >= 4 or not; events none or its rows); tr in (2^-1075 x 10^-6, 1.7 x 10^308) s, volumes 1 to 2^63 - 1, onset < (2^63 - 1) x 1.7 x 10^308 s (SPEC-EXACT 3.8); one recording value per statement; rec_dataset (NIfTI-2 BOLD, sidecar, events); find tries volumes <= 2, 64, MAX_VOL = 10^6 first | 7,718 | 7,615 -> 7,718 |
| base pass (dead NEG table in decide.py) | decide.py -1 | 7,717 | 7,718 -> 7,717 |
| item R1 recording sets (no filter) | decide +210: recordings(bids(d), task) makes d a dataset slot of kind rs; recordings counted per task by kind (answering; 3-D V008, no events V007, no trial_type V002), a case order of the refusing kinds and per task whether a sum's recordings answer; sum (y within N times one recording's range), mean of tr, min, max (one value m), mean of whole numbers (S/N); Model.recd (a number's answer carries recorded); rs_dataset and bold() (rec_dataset now uses it); rs_small (fewest recordings first; MAX_VOL volumes, MAX_ROWS events in all) (SPEC-EXACT 3.9) | 7,927 | 7,717 -> 7,927 |
| item R2 recording sets with a participant filter (SPEC-EXACT 3.9) | decide +78: recordings(bids(d), task, sel), sel participants(bids(d)) or a where() of it; regions (classes of the participants table's types that no set of the statement or whole of its parts tells apart), per region a state (no recordings, none answering, answering) and kinds; an order of (region, kind) only with two refusing kinds (trials); rs_cases; rs_dataset: one participant per region and task whose runs are the region's recordings | 8,005 | 7,927 -> 8,005 |
| item 3 a named recording's values anywhere (SPEC-EXACT 3.8) | decide +46: RECF tr/volumes/onset/duration/events/trials of a named recording anywhere in a statement; per recording its reads (rread), rows (rrows) and trial types (rtt); cases per recording (absent; dim[0]; events rows vs named rows; trial_type column); duration > 0, onset < volumes x tr linear with tr or volumes read, events rows, trial counts at most the rows; ident of a recording value; rec_dataset: durations, rows, trial types, several recordings | 8,051 | 8,005 -> 8,051 |
| 4 (participant_id, participant(), extra()) | decide.py +55 | 8,106 | 8,051 -> 8,106 |
| slot shapes (csv() with rows(tsv()); nifti() dims with size()) | decide.py +48 | 8,154 | 8,106 -> 8,154 |
| the variance shape (three or more signed variances of one table, or two with a widen() inside; symbolic widths) and is_square's widened first argument | decide.py +129, kernel.py +1 | 8,284 | 8,154 -> 8,284 |
| tc1: tsv() and csv() of one file read as rows() and number(cell(., r, 1)) | decide.py +10 | 8,294 | 8,284 -> 8,294 |
| phase 7: the old search deleted (witness.py) | witness.py -475 | 7,819 | 8,294 -> 7,819 |
| base pass (structural merges) | decide -18: Decide.w1_dvar and w1_nvar share w1_hit (their pieces' test, given the hit function and width); bold() writes its header through nii2() (bytes identical, partb/S13/bold_eq.py) | 7,801 | 7,819 -> 7,801 |
| memory held before it is built (BB's call 28 Oct 2026 09:05, SPEC-EXACT 8) | decide +62: STEP_BYTES, MEM, num, bits, form_bytes, hold; lp (its tableau and each pivot), fm (its new atoms) and the integer atoms held, given back when freed | 7,863 | 7,801 -> 7,863 |
| pixdim window: two floats met only in one window decided exactly (SPEC-EXACT 3.6; the 10^-45 probe's wrong R013 became S008 W2) | decide +58: fpair, fwin, solve's hook | 7,921 | 7,863 -> 7,921 |
| coupled variances: one column's values scaled alone (d_scale cols; d_domain, n_hit): bfc7's R013 was a stopped search with a 2-row witness | decide.py +7 | 7,928 | 7,921 -> 7,928 |
| memory (item 2): a question's cases and branches, solve's stack, the integer step's frames and a certificate's rows held before they are kept (SPEC-EXACT 8) | decide.py +90 | 8,018 | 7,928 -> 8,018 |
| half cuts (item 1): a mean against an order statistic of its column, mu <= (u + h)/2 when the counts give at most half its rows above u, mirrored (SPEC-EXACT 3.5a): bfe1-60 and three bfh1 claims R013 -> S008 W1; mu <= u when no row is past u; lazy: a cut is tested and added only when a solution breaks it | decide.py +83 | 8,101 | 8,018 -> 8,101 |
| a round's cap counts its solves only (BB's call 28 Oct 17:10): side work (implied's lp tests) charged to the step bound only (decide.side: a round's budget [steps, headroom]; SPEC-EXACT 8 item (g)); pn450's regression (the lp tests in the first round's cap) removed | decide.py +17 | 8,118 | 8,101 -> 8,118 |
| 5a no input (item 1): a class of at most 64 readable numbers gives all of them to the multisets (few); once every multiset of n rows is tried and the largest variance of more rows lies below every piece, no input: S008 W2 (was R013, a wrong code; SPEC-EXACT 3.7) | decide.py +24 | 8,142 | 8,118 -> 8,142 |
| certificates of no point (BB's call 28 Oct 18:05; SPEC-EXACT 6.1): each unbounded system without a point carries a proof log checked by cert.py (exact Fractions, independent of decide.py); each option of find() a tree of solve1's splits (sign splits checked, model splits named) whose every node is closed; a log or tree that does not check is X001 | cert.py +159, decide.py +143 | 8,444 | 8,142 -> 8,444 |
| certificates (2): empty_box's "none" as bound lines (cert.py's division rule), a float system's memo closes a node only on its checked system, equal shares (5.4) recomputed by the checker | cert.py +43, decide.py +33 | 8,520 | 8,444 -> 8,520 |
| certificates checked only for a refusal (BB's guidance on C4, 28 Oct): the search builds none; a question's "none" finds and shares are kept (own memory count, dropped before the decision would meet the bound) and replayed with certificates only when its verdict is a refusal, in their own step accounts; past a bound the refusal is R013 (its check exceeded the bound); a replay that finds an input is X001; a form never waits on a check (pn450's R013 under eager checking removed) | decide.py +78 | 8,598 | 8,520 -> 8,598 |
| a mean's rows split checked (cert.prange_split: each child's range atoms present, every other added atom a McCormick product of two range facts with mu·N read as S, the children's ranges cover the parent's; S = mu·N and the classes' ends lo, hi trusted; a piece's sign taken from its end's stays a named lemma); what a refusal's check keeps counted once per object (pn472's S008 W2 had become R013: 7,190 options counted per option 1.35 GB, once 16.8 MB) | cert.py +97, decide.py +5 | 8,700 | 8,598 -> 8,700 |
| certificates (L1-L5, BB's call 28 Oct 18:05): every split of solve1 is the model's own disjunction (Model.disjunction, checked by cert.cover: one child per case, the case's atoms or the parent's; half's count condition an obligation shown by a checked system); a piece's sign by its end shown (Model.prove, cert.implied); a leaf's system the model's atoms of its case, the option's and the node's, then the model's facts; every refusal keeps a record (Decide.rest: var, recomputed by cert.var_verdict; model; lemma), one that keeps nothing is X001; each find replayed on its own model; shares with sums (5.4) shown by their points' checked finds (Decide.sums_shown); two floats pinned checked (cert.pin_split), none the model's enumeration (fwin) | cert.py +142, decide.py +176 | 9,018 | 8,700 -> 9,018 |
| certificates (L6, BB's call 28 Oct 18:05): a variance shape's "no input in K" checked by the model's ranges (Decide.vranges: variance [0, sup]; difference [-sup2, sup1], 0 for equal variances, [0, Vp sup] for one selection's sample minus population; sums by n_range; cert.vrange_none) or by every readable value (var_hit's vwhy, cert.vdeep_none); no named lemma is left: an unknown split rule or an uncertified record is X001; n_hit past every size is R013, never None | cert.py +50, decide.py +77 | 9,145 | 9,018 -> 9,145 |
| the search leaves the base (I3, BB's call 28 Oct 18:05): presolve, tidy, empty_box, lp, lp1, fm, back, MSearch and Model's solve, solve1, half_cut, count_ints, implied, one_solve, one_solve1, one_solve2, finish, find moved verbatim to search.py (decide's names read as D.name; Model's methods attached by decide.py); its "none" is checked by cert.py before any refusal, its solutions confirmed on bytes; its loops still scanned | decide.py -587 (search.py 614, outside) | 8,558 | 9,145 -> 8,558 |
| item 4 shape 3 (BB's call 28 Oct 21:52): number(bytes(f, o, n)) decided: the numbers of exactly n bytes by layout (rlays, lnext, lprev, rnext, rprev, rin; model facts, checked against readers.decimal to 5 bytes), a raw slot's class per number()-read range (nan, num), z's bounds, the spell disjunction (Model.spell_cases, checked in a refusal's replay), the spellings (rspell) and RawFile; rpick (the search's choice) in search.py; overlapping ranges stay NotT | decide.py +219 (search.py +21, outside) | 8,777 | 8,558 -> 8,777 |
| item 4 shape 2 (BB's call 28 Oct 22:57): size(f) of a file read by tsv() or csv(), first cut: each row type's least line (scell, sline), size >= header 2W - 1 + the rows' least lines, size <= MAX_TEXT_FILE (R003), the certificate the least table padded in its first header name (stext); cells, header names or numbers of that table read, widen, more than 4 tsv()/csv() reads, other text slots, a one-column table with an empty literal: NotT | decide.py +46 | 8,823 | 8,777 -> 8,823 |
| item 4 shape 2's review (BB's call 28 Oct 23:30): the text total (SPEC-EXACT 3.12a: each tsv()/csv() call charges its table's size to MAX_TEXT_TOTAL; per top one atom over the sized table's size and the least sizes of tables beside it, realised at their least; confirmed on bytes, partb/S13/s2r/boundary.txt) in place of the cap of 4 calls; a one-column table with an empty literal by its two layouts (3.12b: one column, in a TSV with no empty row, or two columns; lay_cases, the model's 'layout' disjunction checked by cert.py, lay_of for the certificate) | decide.py +73 (search.py +5, outside) | 8,896 | 8,823 -> 8,896 |
| item 4 shape 1, first cut (BB's call 29 Oct 00:31): where(tsv(f), eq/ne(1, b)) under rows()/count() of a file read by csv() too (SPEC-EXACT 3.13): the tsv line as the csv slot's column 0 (wconds, cix, tw_classes: a literal's pieces in the csv columns read, read back by both readers), the csv width Wc a model case (Slot.wc; tok: the types each Wc allows; case_atoms: the others no rows), the certificate a bare table of Wc columns (tw_rows); a forced look-alike line, other tsv() reads, widen, size: NotT | decide.py +102 | 8,998 | 8,896 -> 8,998 |
| item 4 shape 1, review (BB's call 29 Oct 01:30): a csv line every read column forces (Wc columns, each a literal class) that looks like a tsv() literal is a class of its own of the tsv line (SPEC-EXACT 3.13a; tw_line: read back by both readers, else no row); the where()'s look-alike scope refuses its rows K002 | decide.py +15 | 9,013 | 8,998 -> 9,013 |
| item 4 shape 1, case 1 (BB's call 29 Oct 02:10): number(cell(tsv(f), r, 1)) beside csv() reads of f (SPEC-EXACT 3.13b): the csv width Wc = 1 is a case of its own when only column 1 is read (the line is then csv column 1's cell); in every other Wc the line holds a comma, so number() refuses V005 on every row there is; Model.literal gives a Wc >= 2 line's literal; certificates' unread cells move on by the seed | decide.py +12 | 9,025 | 9,013 -> 9,025 |
| item 4 shape 1, case 4 (BB's call 29 Oct 02:13): sum/mean/min/max/median/order of tsv(f)'s column 1, or of a where() of it, beside csv() reads of f (SPEC-EXACT 3.13c): in Wc = 1 csv column 1's aggregate over the same rows; in Wc >= 2 no selected line is a decimal (V005 when a row is selected; a sum of none is 0) | decide.py +7 | 9,032 | 9,025 -> 9,032 |
| item 4 shape 1, case 3 (BB's call 29 Oct 02:16): number(header(tsv(f), 1)) beside csv() reads of f (SPEC-EXACT 3.13d): tsv(f)'s one header name is the csv names joined: in Wc = 1 csv name 1, in Wc >= 2 it holds a comma (V005) and its spelling is free (the certificate's name 2 moves on by the seed); a csv name past column 1 read beside it stays NotT (no readable input answers then) | decide.py +8 | 9,040 | 9,032 -> 9,040 |
| item 4 shape 1, a key() row (BB's call 29 Oct 02:20): number(cell(tsv(f), key(1, b), 1)) beside csv() reads of f (SPEC-EXACT 3.13e): the key's column is the line (column 0; Model.tkey in the literals, the named keys, the cell and its look-alike scope), its cell as 3.13b (a key holds no comma, K001: in Wc >= 2 no line is b, V004) | decide.py +8 | 9,048 | 9,040 -> 9,048 |
| item 4 shape 1, widen() (BB's call 29 Oct 02:24): widen() beside tsv() and csv() reads of one file (SPEC-EXACT 3.13f): the kernel's value identity names no reader (a cell: file, row, column; a selection: files, rows), and Model.ident is that already, so the first cut's NotT goes | decide.py -2 | 9,046 | 9,048 -> 9,046 |
| 3.7a (BB's call 29 Oct 04:10): W2 of a part of a variance's selection beside another value refusing on the same inputs: the rule "bears through V003/V005 or not at all" is not so there (Vs(sel) - Vp(sel): Vp's condition, found by ground truth); a found none it met with two variance results whose good types differ is S013 (NotT in w2, slot_bears), never S008 W2; equal good types answer alike where both answer (W2 kept) | decide.py +12 | 9,058 | 9,046 -> 9,058 |
| item 4 shape 1, a variance of the tsv() line (BB's call 29 Oct 02:53): sample/population variance of tsv(f)'s column 1 (or a where() of it) beside csv() reads (SPEC-EXACT 3.13g): in Wc = 1 csv column 1's, in Wc >= 2 no selected line is a decimal (3.13c's good types); a variance certificate (d_out) of such a file is written at Wc = 1; the variance shape (d_hit, vranges) compares two selections without the types either candidate's case gives no row | decide.py +2 | 9,060 | 9,058 -> 9,060 |
| item 4 shape 1, case 6 (BB's call 29 Oct 03:50): size(f) beside rows() and count(where(., eq/ne)) of tsv(f) and csv(f) (SPEC-EXACT 3.13h): per width case W0 the least table at width W0 (one-byte names, each row's least line: a literal line's bytes, else the read cells' least and an unread cell's empty text or a letter no literal piece looks like), the 'o' case at its least width, split as 3.12b's layouts when one column holds no line for a row with an empty csv cell (T005) | decide.py +63 | 9,123 | 9,060 -> 9,123 |
| 3.7b (BB's call 29 Oct 05:40): 3.7a's S013 (a part of a variance's selection, or a file slot, beside another variance result whose good types differ) decided: search.joint_rows (untrusted) tries multisets of rows of the variances' selected types with their classes' readable values (dvals), by size, at most MAX_CASES, for one where the real code gives the statement with and without the part different outcomes; Decide.differ_on confirms them on bytes (X001 otherwise); none found is R013 (a stopped search), never S008 W2; before it Decide.same_rows (trusted, in the base): when each variance and its place without the part have, for every both-answering pair of results a case admits, the same slot, column, ddof and good types less the case's zero types, they read the same rows wherever both answer and the W2 refusal stands (rest 'model') | decide.py +33 | 9,156 | 9,123 -> 9,156 |
| 3.9a (BB's call 29 Oct 06:15, item 4 shape 6): two quantities of one dataset's recordings read from different files of a recording, volumes beside events or trials of a type, sums and counts: a recording's kind is a pair of the quantities' kinds (Model.rs_jk, independent: different files), quantity i's recordings of a kind the sum over the pairs (rs_nq), the case's order the events-file quantity's, states per quantity (z/p for an events-file quantity, f for volumes), certificates with both values per recording (rs_recs2); two quantities of one events file, tr beside another quantity, and a mean, min or max of two quantities stay NotT | decide.py +100 | 9,256 | 9,156 -> 9,256 |
| 3.9b (BB's call 29 Oct 07:08, item 4 shape 6 coupled cut): two quantities of one events file, events beside trials of a type or two trial types (with or without volumes), sums and counts: kinds from the image (ok/3d) and events-file (ok/noev/nocol) axes written per quantity (Model.rs_jk), events-file classes ok[, nocol] (rs_evc) each with a z/p state, y per (quantity, class) (rs_ny), events' ok part >= the read types' (rs_couple), certificates with filler rows of a type no read type looks like (rs_recs2); look-alike trial types NotT | decide.py +50 | 9,306 | 9,256 -> 9,306 |
| 3.8a (BB's call 29 Oct 07:30, item 4 shape 5): two named recordings of one dataset, one's labels within the other's (S0133 inheritance): the larger one's own sidecar overrides the inherited one, so the model's per-recording values stay exact; certificates put each sidecar in the folder rdep gives (func, subject, root: above every named recording whose labels hold its own); a chain of four holds a recording and the same with a run added, which no dataset holds together (B30 inside B00, S0265), so such a statement never answers | decide.py +6 | 9,312 | 9,306 -> 9,312 |
| 3.8b (BB's call 29 Oct 08:40, item 4 shape 4): participants(b) beside a named recording of one dataset: a present recording's subject has its row (B11), a literal's class or else rows no literal labels (case_atoms); certificates relabel the table's rows to the recordings' subjects and give each other subject a T1w.nii; recordings() beside a named one and look-alike participant/recording labels stay NotT | decide.py +46 | 9,358 | 9,312 -> 9,358 |
| 3.9c (BB's call 29 Oct 08:58, item 4 order model): R1's cases were every order of a task's regions and kinds, each with all branches per aggregate; the kernel's sort is read only through each view's first refusing (region, kind), so the case is now (order, states, a branch per view), the least by inclusion per codes kept (Model.rs_firsts), one branch per view in rs_br; same union, so R1's verdicts, fewer branch products (7 of the 12 three-sum R013s of seeds 12-14 decided) | decide.py +53 | 9,411 | 9,358 -> 9,411 |
| 3.9d (BB's call 29 Oct 09:09, item 4 shape 8): trials of two tasks over participant groups: one partition for both tasks, per region both use a flag (one row: one label for both; two or more: one each), pairs of 3.9c's kept cases agreeing on the one-row regions' order (rs_firsts by pi), certificates merging the two carrier chains; empty regions dropped from orders; three tasks, two quantities, participant_id filters stay NotT; three regions stop at MAX_CASES | decide.py +52 | 9,463 | 9,411 -> 9,463 |
| 3.9e (BB's call 29 Oct 09:26, item 4 shape 7): a sum beside a max or min of one task's recordings: y <= N m / y >= N m is bilinear, but with N read nowhere else it projects out exactly per region (max volumes: y >= m; max counts: m = 0 & y = 0 or m >= 1 & y >= m; min counts: y = m or y >= 2m; a split per region, rs_sp); certificates choose N from y and m; N read, tr, min of volumes, max and min together, mean stay NotT | decide.py +39 | 9,502 | 9,463 -> 9,502 |
| the certificate inputs leave the base (unit BLD, BB's call on Patsak's behalf 29 Oct 2026, reversible; partb/SHRINK/AUDIT.md): Model.bytes_of and the builders only it calls (bytes_of1, file_bytes, type_rows, realize, rs_dataset, rs_recs2, rec_dataset, jtext, stext, tw_rows, lay_of, inside_sum; split, spell1, rspell, dec_ct, nii2, bold, merge_chains, W_split_int) and witness._dataset/_cols moved verbatim to build.py (decide's names read as D.name; Model's methods attached by decide.py); trusted store_ok checks each input is the store its hashes name (byte blobs by sha256, a lazily held file one of Periodic/RawFile/NiiFile rebuilt equal from its .args), then the real readers and evaluator read it and a form needs their answers to differ; its loops still scanned | decide.py -495, witness.py -52 (build.py 594, outside) | 8,955 | 9,502 -> 8,955 |
| the search's helpers leave the base (unit SRH, BB's call on Patsak's behalf 29 Oct 2026, reversible): Log, Model.no, prove, rs_small, refine, thin, piece_atoms, psign, unrealized, rows_of, fpick, cap_ok, fup, fdown, fstep, fnext, is_float, form_bytes, spent_all, reached from no trusted root (partb/SHRINK/cg.py), moved verbatim to search.py: the logs and leaves they make are checked by cert.py (a tree takes only systems cert.check registered), the solutions they help find are confirmed on bytes | decide.py -238 (search.py +252, outside) | 8,717 | 8,955 -> 8,717 |
| the variance shapes' witness pickers leave the base (unit HIT, BB's call on Patsak's behalf 29 Oct 2026, reversible): Decide.d_hit, n_hit, d_domain, d_scale, two_vals, dvals and var_of moved verbatim to search.py (attached by decide.py): an input they find is confirmed on bytes (differ_on, d_confirm); a None of d_hit/n_hit refuses only through vnone (a range certificate cert.vrange_none checks, else lemma, X001), one of two_vals only through var_hit's vdeep/vrange record (cert.vdeep_none, vrange_none); var_hit, vnone, vranges and w1_hit stay trusted | decide.py -239 (search.py +241, outside) | 8,478 | 8,717 -> 8,478 |
| Opus 5.5 review 01 (unit F01, BB's call on Patsak's behalf 29 Oct 2026, reversible): cert.Tree kept only each node's case, so a leaf could close its node on a stronger system (an atom search.py added to its path); now each node's atoms are kept as its split gave them (Tree.more) and a split's and a leaf's must be exactly those (same_atoms), the leaf's path the option's atoms then the node's. refine (search.py) writes the parts a summed column is cut into; part_atoms (trusted) now checks they partition the column's bands (consecutive runs from the first band to the last), else X001 | cert.py +12, decide.py +3 | 8,493 | 8,478 -> 8,493 |
| Opus 5.5 review 03 (unit F03, BB's call on Patsak's behalf 29 Oct 2026, reversible): search.py's find kept its own "none" records (PEND) and certify failed only when none was kept, so a "none" the search did not keep was never checked. Now the search's find is find_options (untrusted) and Model.find (decide.py, trusted) wraps it: every "none" a question gets is kept there for certify (memory as before: past the bound the refusal is R013), and an answer that is not one of the options is X001. certify's "a refusal that rests on nothing kept" check is removed (BB's call: the trusted side decides what is checked) | decide.py +18 | 8,511 | 8,493 -> 8,511 |
| Opus 5.5 review 02 (unit F02, BB's call on Patsak's behalf 29 Oct 2026, reversible): SPEC-EXACT 1 said readable inputs were unbounded while 3.12a and item (h) bounded them by the read limit, so rows() past it was R013 and a count certificate past 64 MiB X001. Now bounded in every shape: check() decides without the limit, and on a Past (OverRows, the search's MAX_ROWS, OverRead: a certificate the reader refuses R003) again with it (Model.rb: rlb's least text per table, MAX_TEXT_FILE, and the statement's MAX_TEXT_TOTAL, as case atoms; two_cap). A refusal whose finds do not also check without the limit (Decide.unbounded) says "it holds only by the read limit" | decide.py +77 | 8,588 | 8,511 -> 8,588 |
| Mutation sweep hole (unit F04, BB's call on Patsak's behalf 29 Oct 2026, reversible; partb/MUT): w1 asks for an input whose answer differs from the answer at the search's first point x0 (Decide.differ); for a ratio that is den(x0)·num − num(x0)·den ≠ 0. A search point with no rows under the ratio (solve answering {}) made the form 0, so "no input differs" held vacuously and a mean that forms was refused S008 W1 (42 verdicts in sweep 2). differ now refuses X001 when den(x0) = 0. Any other wrong x0 cannot make a wrong "none": the question is then "an answer other than v0", which has a point unless every input answers v0 | decide.py +3 | 8,591 | 8,588 -> 8,591 |
| The claim tested (unit MUT, BB's call on Patsak's behalf 29 Oct 2026, reversible): "a search.py bug can only cause X001 or R013" holds because every "none" is kept by Model.find (F03) and replayed by cert.py on exactly its node's atoms (F01), part_atoms checks refine's partition, differ refuses a vacuous point (F04), and every solution is confirmed on bytes; cert.py's docstring says so, tests/test_search_mutants.py runs search.py mutants on 8 claims (each X001, R013 or the unmutated verdict), partb/MUT sweeps each search.py function with 5 mutants over the runners (one hole, F04; 33 of 43 functions reached) | cert.py +5 (docstring) | 8,596 | 8,591 -> 8,596 |
| Opus 5.5 max review 02 (unit G02, BB's call on Patsak's behalf 29 Oct 2026, reversible): cert.CHECKED kept checked systems by id() and Tree.leaf compared their contents at leaf time, so a search.py that checked one list and edited it into the node's system closed the node (a certified S011 for a claim that forms). Now CHECKED holds each checked system's forms (key); Tree keeps fingerprints (fp: sha256 of their pickle, every value, attribute and type) of its root, each node's atoms and each node's case when the split that made them is checked, and split and leaf compare them (as_given); Model.find fingerprints the options before the search sees them (X001 if it changes them) and certify's options_closed compares that fingerprint and each tree's root. Tests: tests/test_search_mutants.py (the review's tamper, test_a_leaf_on_a_system_edited_after_its_check_is_x001; tamper kinds stale and edit) | cert.py +22, decide.py +4 | 8,622 | 8,596 -> 8,622 |
| Opus 5.5 max review 02b (unit G02b, BB's call on Patsak's behalf 30 Oct 2026, reversible): Decide.unbounded gave "it holds only by the read limit" whenever a find replayed without the limit did not close, so a search that returned any point (or none it could check) there put that reason on a refusal the model never showed past the limit. Now Decide.limit_shown replays each find without the limit (Model.big_ok: search.py returns a point past MAX_ROWS as it is, not Past) and gives the reason only for a point Model.past_limit confirms (every atom of the system without the limit holds, naturals natural, each mean's S = mu·N, and an atom of the limit fails); a point it does not confirm is X001; no point, Big or Unchecked keep the plain reason, true either way. Tests: tests/test_search_mutants.py test_a_read_limit_reason_from_a_point_that_is_not_one_is_x001 (the review's tamper) | decide.py +24 | 8,646 | 8,622 -> 8,646 |
| Opus 5.5 max review 01 (unit G01, BB's call on Patsak's behalf 30 Oct 2026, reversible): id_cond said two different recordings() identities differ on every input, but the kernel's identity of a recordings() aggregate is the recordings it reads (SPEC 5.1), so on a dataset where a filter keeps every participant the two sums are one value: the model gave S011 to a claim that holds on its own input, and X001 to the difference. Now id_cond gives one dataset's two recordings() aggregates of one computation and quantity the condition that the recordings only one set holds are none, and Model.idsize states it (one task: the 3.9 regions only one set takes; two tasks: both sets). Tests: tests/test_exact_decide.py test_recording_sets_over_the_same_recordings_are_one_value (the review's claims) | decide.py +13 | 8,659 | 8,646 -> 8,659 |
| Opus 5.5 max review 03 (unit G03, BB's call on Patsak's behalf 30 Oct 2026, reversible): the model charged MAX_TEXT_TOTAL per tsv()/csv() call of the inlined statement (Model.rk, sk), and witness.evaluate read the inlined statement whole, but the kernel reads a let once in its own statement (store.begin() per line) and a claim using it reads nothing for it, so `let t = tsv(f)` with six uses of t was refused S008 "only by the read limit" where a 48 MB table (one read) made it fail. Now decide.let_marks marks the judged statement's let nodes (inline() puts the one let object at each use; _as_judged keeps the shape), Model's rk and sk are per statement (decide.stmts: the claim's own calls, then each let once), rename and subst (W._subst keeping marks; a let holding the removed part is its own) carry them, and witness.evaluate(lets) reads each let once with its own text total, its later uses answering as the first. Tests: tests/test_exact_decide.py test_a_let_is_read_once_in_its_own_statement (the review's claim: formed with the let, S008 read limit with tsv(f) six times) | decide.py +67, witness.py +22 | 8,746 | 8,659 -> 8,748 |
| Opus 5.5 max review 04 a, b (unit G04, BB's call on Patsak's behalf 30 Oct 2026, reversible): Model.rlb counted a row at 1 + its read columns' bytes, without separators, csv quoting or the length of a decimal class's least spelling, so a claim true on every readable input refused R013. rlb is now each table's least text exactly per case (lline, cmin, dec_len, dec_spells, in_iv, vmin; build.py's least_table writes the certificate at that text) | decide.py +173 | 8,921 | 8,748 -> 8,921 |
| Opus 5.5 max review 05 (unit G05, BB's call on Patsak's behalf 30 Oct 2026, reversible): a certificate the real reader refused R012 (accounted memory past 1 GiB) was X001. R012 is now the read limit's (OverRead), and the limit's pass has each statement's accounted memory as a case atom: each plain table's text + 64 and kernel._table_size at its least text (Model.mlb, lchars), each where() evaluated 72 a kept row + 64 (wheres) | decide.py +58 | 8,979 | 8,921 -> 8,979 |
| Opus 5.5 max review 06 (unit G06, BB's call on Patsak's behalf 30 Oct 2026, reversible): a trial type holding a double quote (T005) or a break character (T006) was given rows in the certificate's events file, refused B04: X001. Its counts are 0 by case atoms (tt_holds), per recording and per recordings() region | decide.py +17 | 8,996 | 8,979 -> 8,996 |
| Opus 5.5 max review 07 (unit G07, BB's call on Patsak's behalf 30 Oct 2026, reversible): two recordings() tasks of one dataset that look alike: the certificates held recordings of both, refused K003 (kernel.bold_labels): X001. recordings() now has K003 branches (two of the tasks present) before its filter's (Model.alike_br) | decide.py +16 | 9,012 | 8,996 -> 9,012 |
| Opus 5.5 max review 08 (unit G08, BB's call on Patsak's behalf 30 Oct 2026, reversible): SPEC-EXACT 2 said a dataset without participants.tsv refuses V007 in the statement and without any one part alike, which is false for recordings()' participant filter: without it such a dataset can answer. The verdict (S008 W2, v4 fix 08: a filter that keeps every participant is idle) is kept, and SPEC-EXACT 2 now states the exclusion as a rule (the review's second option); w2_nopt, which counted it, was written and dropped: it reversed v4 fix 08 and Phase F's pinned verdicts | SPEC-EXACT, test | 9,012 | 9,012 -> 9,012 |
| Opus 5.5 max review 09 (unit G09, BB's call on Patsak's behalf 30 Oct 2026, reversible): the certificate's filler member "" collided with a named member "" (J002 on the certificate: X001). build.jtext names the filler apart from the object's named members and their look-alikes | build.py (untrusted) | 9,012 | 9,012 -> 9,012 |
| Opus 5.5 max review 10 (unit G10, BB's call on Patsak's behalf 30 Oct 2026, reversible): README gave search.py as 1199 lines (wc -l 1192) and build.py as 594 (630), unchecked. README line 75 states both, and tests/test_source.py test_readme_states_the_untrusted_files_sizes checks them against wc -l | docs, test | 9,012 | 9,012 -> 9,012 |
| Opus 5.5 max review 04 c (unit G04c, BB's call on Patsak's behalf 30 Oct 2026, reversible): the BIDS shapes had no read-limit atoms, so below(events(r), c = 1e9) and below(sum(recordings(b, "x"), "events"), c = 1e9) were R013 though no readable dataset reaches them. The certificates' event caps are now a Past, and the limit's pass has each events file's least text (header, "0<TAB>1" rows, the read types' bytes or a one-letter type, the last line feed dropped) at most MAX_TEXT_FILE and each statement's events text at most MAX_TEXT_TOTAL (Model.evlb, rs_evlb, rs_evm, evreads); exact at 16777213/16777212 (events), 9586978/9586977 (trials of go), 67108849/67108848 (a sum of events), 38347909/38347908 (a sum of trials), 16777213/16777212 (a max); a necessary bound for a min, two quantities and a sum beside a max or min (S008 far past the limit, R013 near it). build.py: event caps a Past, the least events text in the limit pass, and a 3.9e recordings cap checked before its list (an OOM crash on G10) | decide.py +119, build.py +4 (untrusted) | 9,131 | 9,012 -> 9,131 |
| Shrink WLK (BB's call on Patsak's behalf 30 Oct 2026, reversible; the near-copy walkers named at G04c's report): stmts/charge (G03), wheres/wwalk (G05) and evreads/evc (G04c) each walked a statement reading each let once, with the same let dedupe written three times. One trusted walker, letwalk (each call with the statement it is charged in, the statement count, the names read), and charged (a Counter per statement of a slot function) replace them; wheres, stmts and evreads keep their results, so every caller and verdict is unchanged | decide.py -13 | 9,118 | 9,131 -> 9,118 |
| Shrink SPL (BB's call on Patsak's behalf 30 Oct 2026, reversible; G04's spelling construction, asked whether the bound can use lengths alone): Model.vmin (the least spelling of a value the decision fixed, for least_table's cells) moves to build.py: only the certificate's bytes use it, and the reader and evaluator check them (tested: a wrong spelling gives X001, R013 or the same verdict). cmin1, dec_spells, dec_len and in_iv stay trusted: the read limit's bound is a lower bound, and its exactness (S008 at the boundary, not R013) needs that every spelling shorter than ell is a literal or looks like one, which is the same enumeration a certificate would need checked; lchars (G05's memory bound) counts the least cell's characters, so cmin's text is used by trusted code too | decide.py -13, build.py +15 (untrusted) | 9,105 | 9,118 -> 9,105 |
| Opus 5.5 max2 review 01 (unit H01, BB's call on Patsak's behalf 30 Oct 2026, reversible): a cell's number was the variable ("z", slot, row, column) and a tr region's rational ("z", slot, "rs" + w, ...), with the user's name in the place where the model's own variables carry their kind tag ("z", "pix", ...), ("z", "raw", ...), ("z", "y", ...); search.py and the trusted fwin, Model.disjunction and pcuts dispatch on that place, so a file named pix, raw or y changed the verdict (pix: a wrong S008 W2 certified by binade splits; raw, y: X001). Fixed at the root: the place after "z" holds only kind tags; a cell is ("z", "cell", slot, row, column) (a header ("z", "cell", slot, "h", column)), a tr region's rational ("z", "rs", slot, w, t, r); a user name is never in the tag's place, whatever its spelling, so no rename table is needed. Tested: every kind tag found in decide/search/build as a file, let and dataset name gives the output a name f gives (tables, a participants table, a recording) | decide.py 0 (keys only), build.py 0 | 9,105 | 9,105 |
| Opus 5.5 max2 review 02 (unit H02, BB's call on Patsak's behalf 30 Oct 2026, reversible): G04's least text was too high, so S008 "by the read limit" where a readable table fails the claim (a 4,850,000-row table of "1", 9.7 MB). in_iv started at the interval's width scale (digits(hi - lo) - 3), so for (0, 100000) the least was "100", not "1"; the other-text search tried letters and fresh letter names, so beside 25 one-letter literals it was "aa", not "2". Made exact rather than a lower bound: in_iv also walks the finer scales near the near end (iv_scale), down to the scale where every multiple past a > 0 has more digits than the shortest found (lead(a) - E), or past 0 where 10^E's spellings are longer; other text is any ASCII text the reader keeps (no quote or tab in a TSV, quoted in a CSV at its bytes), by length, no literal, no look-alike, no decimal where read as a number (OTHC, dec_or_none); were every ASCII text of 2 bytes a literal, 2 is a lower bound (R013 near the limit). Measured: N rows of a one-byte cell are readable up to 4,902,929, and the model's boundary is there (R013 at c = 4,902,929, S008 at 4,902,930; both classes; partb/H02/real-bound.txt reads both tables) | decide.py +34 | 9,139 | 9,105 -> 9,139 |
| Opus 5.5 max2 review 07 (unit H07, BB's call on Patsak's behalf 30 Oct 2026, reversible): kernel.events_table parsed the events file on every call and charged only its text, and bids(d)'s conformance gate parsed every events file inside Store.measured at a fixed 1024 bytes an entry, so a legal 48 MB events file (12 million rows) ran the checker out of memory at 2.2 GiB, above the 2 GiB floor, and formed at 4 GiB. Reader: a BIDS table (events, participants) is kept like a plain table: kernel.bids_tsv room-checks its cells (80 each) before it parses, caches it and charges kernel._table_size once a program; the gate's tsv_ok room-checks before it parses (transient); Store.measured does not keep a gate's R012 (the program's memory, not the bytes). Now R012 at 2.2 and at 4 GiB (finding 07's script); the largest events file that passes the gate (6.4 million rows) peaks at 1.2 GB RSS. Model: each statement's memory atom (G05) charges the events files it reads once (Model.evmem from evlb/rs_evlb/rs_evm's text forms and their variables' roles): 2 x the text, 193 + 79 c a file, 64 + 79 c a row; regions shared by two filters once. The dataset's other structures are not in it (a lower bound: R013 near the limit, never a wrong S008; R012 at 4,668,442 rows on the reader, partb/H07/real-bound.txt) | decide.py +31, kernel.py +9, bids101.py +2, readers.py +2 | 9,183 | 9,139 -> 9,183 |
| Opus 5.5 max2 review 03 (unit H03, BB's call on Patsak's behalf 30 Oct 2026, reversible): the reader keeps one accounted-memory account a program (Store.begin() resets steps and text, not prog_bytes; a cached table is charged once a program), while G05 modelled each statement alone and checked certificates in a fresh store, so after a claim that read a 1.4-million-row table (206 MB) a claim formed whose every failing input the program refuses R012. Picked what the reader does on a real run: the program's account. Store.begin() records what the program holds; Store.held(hs) is that less the structures made from the statement's own files (their texts, tables, datasets, which the statement charges itself); the model's memory atom is MAX_ACCOUNTED - held (decide.HELD) and witness.evaluate starts each certificate's store at held. Measured: after the 206 MB table, claim 2 forms at c = 5352 (a 5352-row failing g with one-byte names is read: V001) and holds only by the read limit at 5353 (that g: R012). A statement's verdict now depends on the program before it, as the reader's R012 does | decide.py +1, readers.py +6, witness.py +1 | 9,191 | 9,183 -> 9,191 |
| Opus 5.5 max2 review 06 (unit H06, BB's call on Patsak's behalf 30 Oct 2026, reversible): G08 kept v4 fix 08's verdict (a filter of every participant is idle, S008 W2) by stating a rule in SPEC-EXACT 2. The max2 review showed the rule contradicts SPEC-EXACT 1 and 5.2: on a dataset without participants.tsv the filter refuses V007 where the statement without it answers, and a refusal and an answer are two outcomes, so the filter bears. The rule is reversed and the code route taken (partb/G08/alt-code: Decide.w2_nopt decides, in the model of the statement without the filter, kind rs, whether such a dataset has the values before recordings() answering and the statement without the filter not refusing V007; confirmed on bytes). Overturned, and they were wrong: v4 fix 08's test_08 and Phase F's count(recordings(b, "x", participants(b))) S008 W2 now form (= 3); the recording-set W2 param and shape 6's W2 claim form; shape 6's W2 and tamper tests use a repeated condition instead; test_the_participant_filter_rule_is_stated removed | decide.py +41 | 9,232 | 9,191 -> 9,232 |
| Opus 5.5 max2 review 04 (unit H04, BB's call on Patsak's behalf 30 Oct 2026, reversible): G09 fixed only the JSON filler member; three more made-up names came from short fixed lists with an unguarded next(): Model.scell / tw_least (a least other cell from the letters but l), Model.plabel and build.rec_dataset (labels sub-<letter><i> from 25 letters), build.rs_recs2 (a filler trial type from z, y, x, w, v). A program naming every member got StopIteration: X001. Now every one draws from decide.fills (its list, then witness._fresh, which no longer stops at three letters); a least cell tries the other one-byte cells of FILLC (no separator, quote, digit or l) before longer names, which scell still refuses as not modelled (NotT) when the least would be longer. The review's three claims give the controls' verdicts: S008 W1, formed = 3, formed | decide.py +8 | 9,240 | 9,232 -> 9,240 |
| Opus 5.5 max2 review 05 (unit H05, BB's call on Patsak's behalf 30 Oct 2026, reversible): certify gave "it holds only by the read limit" to any refusal with a vdeep record whose row count was below MAX_ROWS, without the read limit modelled or a point from limit_shown; var_hit's multiset loop sets that count as soon as every piece lies above the greatest variance of more rows, which holds at any size, so test_partB 5a (m = 5) had the reason on a refusal decided in the first pass. The disjunct goes: the reason comes only from limit_shown's confirmed point (G02b). past() is monotone in n (the greatest variance of n + 1 or n + 2 rows only falls), so a vdeep record never rests on the limit, and var_hit's Past (not past(MAX_ROWS) and past(two_cap)) could never be raised: removed, with two_cap's rb flag, its only use. The pinned 5a test now asserts no read-limit reason (fails on H04's code) | decide.py -2, test_partB | 9,238 | 9,240 -> 9,238 |
| Opus 5.5 max2 review 08 (unit H08, BB's call on Patsak's behalf 1 Nov 2026, reversible): the pieces of a summed and ordered column (3.5 e2) have their bilinear facts (S = mu·N, lo <= mu <= hi) only as PAtoms that search.piece_atoms (untrusted, moved out at SRH) builds, and cert.prange_split trusted any PAtom's facts and accepted one outside the option on its first split. A one-line fault there (lo, hi = 5, 4) made four formed claims certified S008 W1/W2 refusals, refuting "a search.py fault can only give X001 or R013"; the sweeps' kinds never put wrong data in a trusted object. Now decide.Model.piece_facts (trusted) states each piece's facts by content (mu, S, N, lo, hi, a0, key), and prange_split trusts a PAtom only when it is one of the option's atoms or one of these: the review's tamper is X001. Tests: test_a_piece_with_wrong_facts_is_x001 (4 claims x inverted / too-high bounds; 5 fail on H05's code), test_search_mutants kind "data" (every PAtom a function returns gets inverted bounds; piece_atoms:data fails on H05's code) with a summed and ordered claim; the sweep gets the kind (partb/MUT sweep6) | decide.py +13, cert.py +2 | 9,253 | 9,238 -> 9,253 |
| Argon review 07 (unit A07, BB's call on Patsak's behalf 1 Nov 2026, reversible): Decide.w2, w2_nopt and slot_bears evaluated the statement with and without the part (or with its file slot varied) through two calls of build.py's bytes_of, and store_ok checks each store only against its hashes, so a builder giving two inputs for one point made an idle part bear: build.py alone turned an idle condition's R013 into a form, build.py with search.py a repeated condition and a cancelling file (SPEC 4.3 R3). Unit BLD's 'never a wrong form' did not hold. Now the store is built once and both sides read it (Decide.run/outcome take it): on one input a difference is a real witness whatever bytes build.py chose. Test: test_search_mutants::test_a_builder_giving_two_inputs_for_one_point_cannot_form (the review's two tampers; fails on H08's code: formed) | decide.py +3 | 9,256 | 9,253 -> 9,256 |
| Argon reviews 01 and 04 (unit A01, BB's call on Patsak's behalf 1 Nov 2026, reversible): Model.disjunction tested its split's variable by ad-hoc tag tests. 01: a spelling split of a byte range's number of 1011 bytes no slot reads was stated as no case at all, so search.py alone closed every option with no leaf (certified S008/S011 on every Part-T claim); a binade split took a natural variable of a slot named pix (the tag at index 1 is the user's name there), and a one-binade range raised ValueError in frange_split. 04 (shipped code): the band split's deny-list missed a region's sum of RepetitionTimes (('z', 'rs', d, 'y', ..)), so a sum of two TRs was treated as one 1000-digit read value and widen() was certified S008 W2 where a readable dataset (TRs 9 and 1.0...04 s) makes it bear. Now one table, decide.zkind (read / sum by the model's tags, an allow-list), decides band and step; spell needs one of the model's number()-read ranges holding a number in the case; binade needs ('z', 'pix') and two binades or more; search.py follows zkind (back, solve1). The review's 04 claim is R013 (the search finds no such point), never S008. Tests: test_search_mutants::test_a_split_on_a_variable_the_model_does_not_have_is_x001, ::test_a_binade_split_of_a_natural_or_of_one_binade_is_bad, test_exact_decide::test_a_sum_of_repetition_times_is_no_single_read_value (all 3 fail on A07's code) | decide.py +10 | 9,266 | 9,256 -> 9,266 |
| Argon review 02 (unit A02, BB's call on Patsak's behalf 1 Nov 2026, reversible): G02 fingerprinted the option's atoms (froot) but checked them only at a leaf and in options_closed, and a split read them live (Model.disjunction's atoms, prange_split's 'the option's own PAtom' identity test, implied). search.py alone appended a PAtom of no piece (lo = 1 > hi = 0) to an option, split by ('prange', P), took it away and closed the child on its contradictory atoms: every claim formed (certified S008). Tree.split now checks fp(option's atoms) = froot as well. Test: test_search_mutants::test_an_option_edited_between_its_splits_and_its_leaves_is_x001 (fails on A01's code: S008) | cert.py +1 | 9,267 | 9,266 -> 9,267 |
| Argon review 03 (unit A03, BB's call on Patsak's behalf 1 Nov 2026, reversible): H03's held() subtracted the claim's own files' memo charges but took the files from store.log | store.gate, which a let's reads are not in (they are in kernel.used_logs), and where()'s kept row numbers (72 a row + 64) were charged with no key, so for a claim over a let the model charged the let's parse and its rows twice: the readable inputs were cut short and atmost(count(w), c) was a certified S008 'holds only by the read limit' with a readable counterexample (Argon: 50,000 rows of 100 columns at the shipped cap; at a 40,000,000-byte cap S008 began at c = 149,083 or 162,645 for a bound of 182,646 readable rows). Now held() also subtracts the tables among the files its lets read (kernel.actual_reads; a let's dataset structures, which the model does not charge, stay held: a first cut subtracting every let file failed the gate, 6 BIDS boundary tests R013 for S008) and store.anon per let statement (kernel.used_lets, at any depth); S008 begins exactly at the readable bound. Test: test_exact_decide::test_a_lets_memory_is_not_counted_twice (fails on A02's code: S008) | kernel.py +2, readers.py +2 | 9,271 | 9,267 -> 9,271 |
| Argon review 06 (unit A06, BB's call on Patsak's behalf 1 Nov 2026, reversible): nwidth keyed each widen() symbol by repr(base), which names the reader, while the kernel's value identity (and the model's vranges) does not: widen(sample_variance(tsv(f), 1)) and widen(sample_variance(csv(f), 1)), one value wherever both answer, did not cancel, so the width was 30 for 10: a certified S008 W1 on 'x 0 20' though 'x 0 2' fails (V001), and X001 for exceeds(.., c = 25) (unmodified code). The key now has csv read as tsv. Verdicts on Argon's programs: S008 -> formed, X001 -> formed (ground truth: the bytes bear; V001 on 'x 0 2'). Test: test_exact_decide::test_widened_variances_of_one_column_by_two_readers_share_one_symbol (fails on A03's code) | decide.py +1 | 9,272 | 9,271 -> 9,272 |
| Argon review 08 and the CSV memory item (unit A08, BB's call on Patsak's behalf 1 Nov 2026, reversible): the memory floor (SPEC 9.4: no program inside the bounds runs out of memory) failed three ways: json()/json_file() parsed before their charge (64 a byte + 64, known before) met room(); a CSV table was charged only after it was built (its pre-check counts lines); and begin_program kept the memo up to MAX_ACCOUNTED, so a second program held its own bound and the first's. Measured on the box (peak RSS, no limit -> after): two programs of ~1.01e9 accounted bytes 2,575 -> 1,308 MB; a 26.4 MB JSON out of memory at 2.0625 GiB -> R012 at 64 MB; an 11,150,000-row CSV of 'ab,cd' 2,968 MB (out of memory at 2.0625 GiB) -> R012 at 1,677 MB; TSV 13,000,000 rows of 'a' 1,564 -> 989 MB, 6,400,000 of 'ab<TAB>cd' 1,908 -> 1,495 MB. Now _cached takes a pre charge (json, json_file), readers._table calls room() with the table's kernel._table_size so far at each row (plain TSV, CSV and BIDS tables: the same R012, earlier), and begin_program always drops the memo (pure: no verdict changes, only speed). Test: test_exact_memory::test_json_a_csv_table_and_the_memo_are_held_against_the_bound (fails on A06's code) | readers.py +5 (kernel.py, bids101.py 0) | 9,277 | 9,272 -> 9,277 |
| Argon review 10 (unit A10, BB's call on Patsak's behalf 1 Nov 2026, reversible): make_manifest's os.walk had no onerror and sha256_file's OSError was not caught: an unreadable root gave exit 0 and an empty manifest, an unreadable sub-folder a partial one (check then formed '1 subjects' of a 2-subject dataset), an unreadable file a PermissionError traceback (exit 1). Now both raise ManifestError: exit 2, 'cannot read ...', nothing written (v4 SPEC 10's contract). No verdict of check changes (a manifest names its bytes by hash). Test: test_v4_cli::test_manifest_of_a_folder_it_cannot_read_whole_exits_2 (fails on A08's code: exit 0) | readers.py +6 | 9,283 | 9,277 -> 9,283 |
| Argon review 2 01 (unit B01, BB's call on Patsak's behalf 1 Nov 2026, reversible): cert.pin_split (fwin's pair of floats pinned to one point, L5) checked that the four atoms pin floats and that the parent's atoms with u or v hold there, but not which variables were pinned. search.py alone pinned two fresh naturals to (1/2, 0) (the child rounds u = 1/2 to a contradiction: every option closed, a formed claim certified S008) or a byte range's number to 7/2 and then split it by the model's spellings (true on inputs only: certified S011). The lemma (an input moved to (a, w) is a child's point) holds only when every value of u and v is a float: pin_split now requires two pixdims (('z', 'pix', s)), each in the parent's atoms; anything else is cert.Bad (X001). Tests: test_search_mutants::test_a_pin_of_variables_that_are_not_floats_is_x001 and the mutant find_options:pin (both fail on A10's code: S008) | cert.py +3 | 9,286 | 9,283 -> 9,286 |
| Argon review 2 06 (unit B06, BB's call on Patsak's behalf 1 Nov 2026, reversible): cert.prange_split's first rows split took a0 from the children and never compared it with the option's PAtom's own a0, so a split over [a0', ∞) with a0' > P.a0 was accepted and N in [P.a0, a0') was in no child; with the read limit's atoms (Model.rb written by the tampered search, the route closed by B07) search.py alone certified a formed difference(mean, min) S008. Now a0 <= P.a0 (a lower a0 covers more). Test test_cert::test_a_means_first_rows_split_starts_at_its_own_a0 (fails on B01). | cert.py +0 | 9,286 | 9,286 -> 9,286 |
| Argon review 2 07 (unit B07, BB's call on Patsak's behalf 1 Nov 2026, reversible): cert.prange_split trusted a PAtom not in the option when it was in tree.model.piece_facts(case), read from the live Model the search runs as (search.py's functions are Model methods): a search that set piece_facts on the instance around a split of a contradictory PAtom (lo 1 > hi 0) and restored it had formed where() and sum() claims certified S008; Argon 06's tamper wrote Model.rb in check()'s first pass. cert.py now calls base, tail, disjunction and piece_facts by the model's class (cert.mcall), Model.find X001s when the model's own attributes (all but decide.SEARCH_SETS: tree, trees, leaf_at, checked, and steps, the model's work count) differ after the search, and test_source::test_the_untrusted_files_write_no_trusted_state checks search.py and build.py statically (it flags both review tampers). SPEC-EXACT 6.1 and README say what untrusted covers: code that computes and returns, not a sandbox (in-process code could write cert.CHECKED). Test test_search_mutants::test_a_search_that_writes_the_models_state_is_x001 (both tampers; fails on B06's code: S008). | cert.py +5, decide.py +3 | 9,294 | 9,286 -> 9,294 |
| Argon review 2 05 (unit B05, BB's call on Patsak's behalf 1 Nov 2026, reversible): Store.nifti(full=True), the BIDS gate's check of every image's data, charged a .nii.gz by its compressed size (size // 4096 + 1) and decompressed the whole stream in an uncounted loop: an 8 MB file of gzip members of zeros (8 GiB) took 27 s on the PC (4.6 s on the box) for the same 2,040 steps as a 0.01 s file of its size, so the step bound did not bound the work. nifti_read now counts each chunk it reads (len // 4096 + 1) on a meter that starts at the statement's steps (R002 inside the loop), and Store._nifti (shared by witness.MemStore.nifti) keeps that count with the header and charges it beside the bytes' charge on every use. An uncompressed image and a header-only read are charged as before. Test: test_readers::test_a_gzip_image_read_whole_is_counted_as_it_decompresses (fails on B07's code: 16 steps for 64 MiB) | readers.py +12, witness.py 0 | 9,306 | 9,294 -> 9,306 |
| Argon review 2 02 (unit B02, BB's call on Patsak's behalf 2 Nov 2026, reversible): Decide.run read build.py's store through its own methods (set(b), b.values(), store_ok's isinstance tests and type(v)(*v.args).__dict__ == v.__dict__), so a dict subclass showed one store to the checks and another to the evaluator (Argon's case A: build.py alone, search.py unmodified, a wrong form), a dataset could be a tuple subclass (case B2), a Periodic's whole a bytes subclass equal to anything and a dataset blob's key a str subclass equal to anything (b02-probe). Decide.input now copies the store from exact types (decide.plain; a Periodic, RawFile or NiiFile rebuilt from exact arguments, its ov list copied, and the rebuilt one used) into a Store, which Decide.run requires; A07's three sites call input() once per point, so one object is now one input. Tests test_cert::test_a_store_that_is_not_plain_is_x001 (fails on B05r's code: S008) and test_source::test_the_untrusted_files_subclass_no_builtin; Argon's script: cases A, B1, B2 X001. | decide.py +22 | 9,328 | 9,306 -> 9,328 |
| Argon review 2 09 (unit B09, BB's call on Patsak's behalf 2 Nov 2026, reversible): Model.mlb charged a table row its least line's cells' characters, counting an other-text cell's least ASCII line as its characters, but the least characters of a cell of those bytes is fewer (a 2-byte UTF-8 character is one): with another file holding memory near MAX_ACCOUNTED, below(count(where(f, ...)), c = 2000000) on a 1-row f was S008 'holds only by the read limit' while a readable 2,000,000-row UTF-8 f made the claim false (V001). Model.lchars now counts an other-text cell as ceil(bytes / 4) characters; literal and decimal classes stay exact. The bound stays a lower bound, so near the limit the answer is R013, not a false S008 (test_exact_memory::test_other_text_cells_are_charged_no_more_than_their_least_characters, at an 8,000,000-byte cap). Base 9,328 -> 9,329 measured. |
| Argon review 2 08 (unit B08, BB's call on Patsak's behalf 2 Nov 2026, reversible): A06 made a value's widen() symbol name no reader, but kernel.c_header built its Header sort without a meta, so number(header(tsv(f), 1)) and number(header(csv(f), 1)) kept the reader in their identity: atleast(difference(widen(.., 1), widen(.., 2)), c = -2) on "1 / 0 / 20" was V006 ([-3, 3]) where the width 1 is S008, c = 2 was V006 where V001 is due, and two tolerances on the one value were both formed, not S012. The Header sort now has meta ("header", reads, k), as Cell's ("cell", reads, r, k) and Model.ident's ("Header", file, k). Both readers give one header cell wherever number() reads it as a decimal (a decimal has no tab, comma or quote, and a byte-order mark is T011), so one symbol is sound. test_exact_decide::test_a_header_number_by_two_readers_is_one_value. Base 9,329 -> 9,329 (kernel.py 0). |
| Argon review 2 03 and 04 (unit B0304, BB's call on Patsak's behalf 2 Nov 2026, reversible; design note wip/B/design-B0304.md, item 3 decided (a) exact re-evaluation): the memory held at a statement (H03, A03) kept the where() rows earlier statements built from the statement's own file at their size on the actual input (03: 147 earlier claims, about 1,058 MB on 100,000 rows 'a', a false S008 'holds only by the read limit' while a 150 'a' / 80,000 'z' file is read and makes the claim false), and subtracted a let's files only when they were tables, so a let's JSON was held and charged again by each certificate (04: R013 through a let where inline forms). held() now leaves out every structure made from the statement's files (theirs, its lets', any earlier statement's: slot-derived, another size on another input), keyed or not (where() rows recorded by the files they come from), and each certificate first runs again on its candidate, in program order, every earlier let and claim that read one of those files, with the program's other files and what it holds from them as they are; its steps count on the witness budget, so too much of that work is R013 (a work bound). The model stays a lower bound. Step 0 (design note): a let over bids(d) now gives the inline claim's verdict at every count (the events boundary tests re-pinned to inline's 4,668,441 / 3,408,702). Base 9,329 -> 9,394 measured. |
| Review 3 01 (unit C01, BB's call on Patsak's behalf 2 Nov 2026, reversible; B02 part 2): a sign split's check read a child's atom through the atom's own keys() and __getitem__, check() and the leaf's fingerprints through the built-ins', so a search.py dict subclass whose views differed inside Tree.split closed two contradictory children and two formed claims were certified S008. The checker now reads every value the search hands it (a split's rule, children and atoms, a leaf's system and atoms, check()'s system and log, an obligation, find()'s point, a replay's trees) only as one copy it makes itself from exact types (cert.exact; the trusted atom classes rebuilt with their attributes; a subclass is X001), one copy per object so the identities a tree checks hold, and gives the model only the cases its own disjunctions made (Tree.mcase), never the search's. Chosen over a check of Tree.split's sign rule alone (the class is every view the checker reads). Base 9,394 -> 9,474 measured. |
| Review 3 02 (unit C02, BB's call on Patsak's behalf 2 Nov 2026, reversible): a certificate runs again every earlier let and claim that read the judged statement's files (B0304, decide.prefix), all of each, but held() left out only the where() rows made from those files, so an earlier claim that read them and another file had that file's rows held and charged again by each certificate (1,440,064 bytes for 20,000 rows at a 6,000,000 cap: R013 'a certificate input past the read limit' where the claim forms and the falsifying input, 5,256,746 bytes, is V001). where() rows are now kept by the statement that made them (kernel.st_ix, store.anon_by) and held() leaves out every row of the statements prefix() runs again: the certificate charges each once, as it charges the other files' keyed structures once through its memo. Chosen over charging only the rows of the judged files in the re-run (the re-run is the program's own evaluation, kept whole). Base 9,474 -> 9,479 measured. |
| Review 4 01 (unit D01, BB's call on Patsak's behalf 2 Nov 2026, reversible): C01's copies keep every attribute the search wrote, and the model's binade disjunction took the parent's float range from an atom's .r (frange_of): a sign split adding z <= 0 and z >= 0 (forms checked) whose .r said the other sign, then binade splits on those ranges, closed every option on contradictions that held none of its points, and search.py alone certified two formed claims S008. The model now reads a range from the atoms' forms only (decide.frange_in: the four frange atoms present, EMIN <= ea <= eb <= EMAX); cert.prange_split uses a parent's .r only when the parent's atoms state it and every range's ends are integers (a 7/2 and 9/2 pair left N = 4 in no child); every other field of a copied atom audited (PAtom facts: H08; nest, cap, half, tail: the option's own atoms); cert.exact makes a dict whose keys merge X001 and leaves no partial copy after a Bad. Chosen over rejecting this binade shape (the class is any derived field the search writes). Base 9,479 -> 9,532 measured. |
| Review 4 02 (unit D02, BB's call on Patsak's behalf 2 Nov 2026, reversible): a certificate re-runs, inlined, every earlier let and claim that read the judged files (B0304), and held() leaves out the where() rows of those statements (C02); a let they use that reads only another file was evaluated again inside them and charged on top of its rows the program holds (1,440,064 bytes for 20,000 rows at a 6,000,000 cap: R013 where the same claim with the where() written in place forms and the falsifying input is V001; also a let of a let, a let reading both files, two names of one file, a refused earlier claim). The re-run now takes the program's value of every let that reads none of the judged files (decide.prefix, witness.evaluate's let cache), as the kernel on the candidate evaluates such a let only in its own statement, on the same files: the re-run charges exactly what held() leaves out, by construction. Chosen over also leaving out the rows of every let reachable from the re-run (that undercharges when a candidate's re-run stops before the let). Base 9,532 -> 9,539 measured. |

## 11. Trusted-base cap: 4,335 -> 4,402 (fix pass; BB's technical call on Patsak's behalf, 26 Oct 2026, reversible)

The fix pass of FIX-BRIEF.md (Argon v4 breaks R1-R6, W1, W2) fixes each break at its root cause and adds
67 trusted lines: kernel 1175 -> 1191 (value identity of BIDS values, R1, R2), witness 849 -> 862 (W2's
file-slot form, R3; W2's witness steps charged, R6), bids101 755 -> 765 (the CHANGES date, R4; B17 for a
bad subject label, R5), readers 693 -> 721 (n log n manifest check charged, R6; one rule for links and
byte-exact names under --root and --files, W1, W2). Measured base 4,402; the cap is raised by exactly the
measured amount, to 4,402, following the CSV precedent. Nothing was compressed, joined or moved out of the
trusted files. The 4,000 target stays and is not met (fixpass/FIX-REPORT.md).

## 12. Trusted-base cap: O pass (BB on Patsak's behalf, 27 Oct 2026, measured moves only)

Each accepted O/C item of fixpass/O-QUESTIONS.md is built at its root; where it adds trusted lines the cap moves
by exactly the measured amount, in the item's own commit. Nothing compressed, joined or moved out. The 4,000
target stays and is not met.

| item | file deltas | base | cap |
|---|---|---|---|
| O9 | kernel +4 (widen of a widened value takes its base and summed tolerance; number_uses skips the directly nested widen) | 4,406 | 4,402 -> 4,406 |
| O4 | kernel +6 (is_root: a root by its sort; the S006 test in difference uses it) | 4,412 | 4,406 -> 4,412 |
| O3 | kernel +10 (cell_decimal: a bounds refusal is no answer in where, like a non-number; R007 at the end if the row is kept), readers -1 (grammar matched before the bounds) | 4,421 | 4,412 -> 4,421 |
| O6 | witness +5 (number(extra(p, col)) marks the participants column numeric, SPEC 4.4 item 1) | 4,426 | 4,421 -> 4,426 |
| O10 | __main__ +9 (manifest --out OSError exits 2 with a message; check with no program, '-' twice or an unknown option is usage), kernel +3 (P011 for a program with no statement) | 4,438 | 4,426 -> 4,438 |
| O8 | readers +30 (gz_whole: whole-stream gzip check, charged; nifti_file runs it first under measured; gz_head joins a member magic split across reads) | 4,468 | 4,438 -> 4,468 |
| O5 | bids101 +1 (a same-folder clash is kept only if no deeper file overrides the key) | 4,469 | 4,468 -> 4,469 |
| O14 | bids101 +2 (each events TSV resolves its dictionaries with inherited(), the sidecars' B30 choice points) | 4,471 | 4,469 -> 4,471 |
| O7 | bids101 -2 (the IntendedFor choice point compares the BOLD images each reading covers; fmap_all folded into fmap_targets) | 4,469 | 4,471 -> 4,469 (follows the base down) |
| O13 | bids101 +1 (an agreed value's provenance is the union of both run readings' sidecars) | 4,470 | 4,469 -> 4,470 |
| C2 | bids101 +5 (separator characters in CHANGES and a non-ASCII indent are B30) | 4,475 | 4,470 -> 4,475 |
| C1 | bids101 +5 (a version-shaped preamble line with a date and indented lines under it, above a release, is B30) | 4,480 | 4,475 -> 4,480 |
| C3 | bids101 +10 (_closes_at_end: a heading ends with the bracket matching its first one) | 4,490 | 4,480 -> 4,490 |
