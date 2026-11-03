# SPEC-EXACT: deciding W1 and W2 exactly (draft, phase 1 of plans/exact-decision-procedure.md)

Status: written in phase 1, before the trusted code. Since phase 3 (26 Oct 2026) `src/reality4/decide.py`
follows it for part T; every other statement is still decided by SPEC §4.4's search. When a section here and the code
disagree after the switch, this text is the definition. It covers part T (counts, rows, shares,
differences, comparisons; `eq`/`ne` and number conditions; `cell` by position or key, `header`, `number`; extended
at the phase 3 checkpoint, 27 Oct 2026, by BB's ruling 3 of 26 Oct 22:12), part N (sum, mean, max, min, order,
median, widen; phase 4, 27 Oct 2026, 3.5), part H (JSON paths, NIfTI dims, size and bytes; phase 5, 3.6), the
elimination of named cell values (4.1), the rational relaxation (4.2) and the integer step used by every later part.
Part V (variances, 3.7) is added by the variance phase; part B by phase 6.

`metatheory/Exact.lean` follows sections 3.3 (counts), 4 and 6 line by line; the names in brackets are its
theorems. Section 4.1 (elimination of named cell values) is proved since phase 4 ([elim_step], [elim_correct],
[elim_nat], [atom_scale], [atom_int]; the decimal argument stays on paper). Section 3.4 (cases of named rows) has no
Lean proof; it and 4.1 are tested (tools/exact_bf2.py, tests/test_exact_decide.py). `src/reality4/intstep.py` is section 4 in Python, function by function (phase 2); step 5's
choice is Exact.lean's `pickStd`, and [decide_std] is decide_correct for it.

## 1. What is decided

For a statement s that formed on the real bytes (SPEC §4.1–4.3 unchanged):
- **W1(v)**, for each computed value v of s (SPEC §4.3): is there a pair of readable inputs on which v
  has two different answers? A value refusal (V…) is no answer.
- **W2(p)**, for each removable part p, at its judging level (SPEC §4.3, unchanged): is there a readable
  input on which s with p and s without p have different outcomes? A value refusal is an outcome.

S011 and S008 follow from these answers as SPEC §4.4 item 11 says. Each answer is a yes or no about all
readable inputs; it does not depend on a search order, a budget that ran out, or the real bytes.
"Readable input" is bounded by the readers' read limit, as 3.12 already treats it (F02; Opus 5.5 review 02, BB's
call on Patsak's behalf, 29 Oct 2026): a TSV or CSV table is at most MAX_TEXT_FILE (64 MiB) bytes, and the text one
statement reads whole (each `tsv()`/`csv()` call charges its table's, readers._cached) at most MAX_TEXT_TOTAL
(256 MiB); an input past either is refused R003 by the real reader, so it is no readable input. There is no other
size limit in the question (D3): MAX_ROWS bounds a certificate, not the question. The procedure decides each
statement first without the read limit; when that meets a certificate past it or more than MAX_ROWS rows (a Past),
it decides again with the limit (Model.rb: each such table's least text, Model.rlb, and the statement's total, as
case atoms; the reader's accounted memory too, unit G05: a certificate refused R012 is past the limit, and the
program's accounted memory at each statement (unit H03, Opus 5.5 max2 review 03: the reader keeps one account a
program, readers.Store.begin_program; so a statement's readable inputs are those the program reads there: what it holds
when the statement starts, less what it holds for the statement's own files, which the statement charges itself,
readers.Store.held, (unit A03, Argon review 03) with its lets' files; unit B0304, Argon review 2 03 and 04: less every
structure made from those files, keyed or not, whichever statement made it, since it is another size on another
input, and (unit C02, review 3 02) every where() row made by an earlier let or claim the certificate runs again, from
any file, since it makes them again (store.anon_by keeps where() rows by the statement that made them); the model's atom and every certificate start from
it, and each certificate first runs again on its candidate, in program order, every earlier let and claim that read
one of those files (decide.prefix, witness.evaluate; the program's other files and what it holds from them as they
are; unit D02, review 4 02: a let that reads none of those files, met inside one of them, is the program's value and is
not run again, as the kernel on the candidate evaluates it only in its own statement), so it charges them exactly, its steps on the witness budget, plus the statement's own), each plain table's text + 64 and kernel._table_size at its least text (unit B09, Argon review 2 09: an other-text cell's characters
counted as at least its least bytes / 4, rounded up, since a UTF-8 character has up to 4 bytes) and each
where() evaluated, a let's once, 72 a kept row + 64, is at most MAX_ACCOUNTED, Model.mlb; and each events file it reads, once (unit H07: the reader keeps
it parsed, kernel.bids_tsv), 2 x its least text, 193 + 79 c a file and 64 + 79 c a row of c columns, Model.evmem; the
dataset's other structures (manifest, sidecars, headers, the gate's own) are not in it, a lower bound, so R013 near the limit; a statement reading a table
of another shape has no such atom and refuses R013 near it; the BIDS events files too, unit G04c: each named
recording's events file and, for a recordings() set of one quantity, events or trials of one type, each of its
recordings', at most MAX_TEXT_FILE at its least text, the header, rows "0<TAB>1", a read type's bytes or a
one-letter type, the last line feed dropped, and the statement's events text at most MAX_TEXT_TOTAL, each call
its files', Model.evlb, rs_evlb: exact for sums, means and maxes, a min's text a lower bound; two quantities, Model.rs_evm,
a necessary bound only, rows of unequal sizes split over files in whole rows, so R013 near the limit). The least text is exact (unit G04): the header's one-byte names and separators, and each row its least
line: each column's least cell (a literal its bytes; other text the least ASCII text the reader keeps in the cell that is no
literal, looks like none and, where the column is read as a number, is no decimal (unit H02: any ASCII, not letters only;
csv quoting at its bytes; were every ASCII text of two or more bytes a literal, that length, a lower bound, so R013 near
the limit); a decimal class the least spelling readers.decimal reads of a number in it, exponent forms included, at
every scale where one can be shortest, the finer scales near a short end too (unit H02: (0, 100000)'s least is "1")), the separators
and csv quoting; a readable table reaches it, so the bound is the read limit's own. A refusal there says "it holds only by the read limit", in every shape (`rows()`, `size()`, the text
total, item (h)'s variance rows), only when one of its finds, replayed without the limit, has a point the trusted
model confirms is past it (Decide.limit_shown, Model.past_limit: each natural a natural, each mean's S = mu·N, every
atom without the limit holds there and an atom of the limit fails; unit G02b); a point the model does not confirm is
the search's fault, X001. With no such point the reason is the plain one, which is true either way (every readable
input gives one answer). A point past the limit is confirmed by the model alone: no input past it can be read.
A variance refusal on its readable values (a vdeep record, 5a) holds at any number of rows (the greatest variance
of more rows only falls), so it never gives the reason by itself (unit H05, Opus 5.5 max2 review 05).
The text total is per statement as the kernel runs it (kernel._check: store.begin() per line): a `let` is read once,
in its own statement, and a claim using it reads nothing for it, so the model charges each statement's own
`tsv()`/`csv()` calls (decide.stmts: the claim's, then each let once) and a certificate is evaluated so too
(witness.evaluate: a let read once with its own text total, its later uses answering as the first; in a W2 copy a let
holding the removed part is a let of its own). Unit G03 (Opus 5.5 max review 03, BB's call on Patsak's behalf 30 Oct
2026, reversible): before, every call of the inlined statement was charged, so a claim using a let was refused S008
"only by the read limit" where a readable input made it fail. Cost limits apply to the procedure (section 8), and hitting one refuses R013; it never
gives an answer.

## 2. Part T

A statement is in part T when every call in it is one of:
- `tsv`, `csv` (on a file slot);
- `tr`, `volumes`, `onset`, `duration`, `events`, `trials` of a named `recording(bids(d), ...)`: 3.8 (since Part B items 2c
  and 3, 28 Oct 2026);
- `recordings(bids(d), task)` and `count`, `sum`, `mean`, `min`, `max` of it: 3.9 (since Part B item R1, 28 Oct 2026);
- `participants(bids(d))` (on a dataset slot d; since Part B item 2b, 28 Oct 2026): a table slot of kind `pt`, read
  by bids101.bids_tsv (no empty cell; header names distinct and not look-alike), whose first column is
  `participant_id`. Its readable tables are exactly those: every one is the participants.tsv of a readable dataset
  (one `sub-w<i>` label per row, a T1w image per subject: witness._dataset, the certificate; the header-only table
  is the dataset with no subjects), and every readable dataset's is one. Column 1 (`participant_id`, the labels;
  since Part B item 4, 28 Oct 2026) is read by eq/ne with a literal: every row's cell is `sub-<label>`, distinct
  (B11), so a literal class that is a label (`sub-` and a BIDS label) holds at most one row, and one that is not holds
  none (a case atom; Model.plabel writes each row's label: its literal's, else `sub-w<i>` or the first name of decide.fills, unit H04, that
  looks like no literal). `participant(bids(d), L)` (a label L) and `extra(participant(...), k)` (k >= 2) and
  `number()` of it read row `sub-L`'s cell k: V004 when no row is `sub-L` (a case), else a cell of the table. Outside
  part T: column 1 read as a number or as a cell, two look-alike literals of column 1 (K003 with both rows, V004 with
  one), participant() and a recording of one dataset, and trials() of recordings with a filter on column 1 (NotT).
  A dataset without participants.tsv refuses V007 in participants(),
  in the statement and in the statement without any one part alike but recordings()' participant filter, so it makes
  no two answers; for that filter it is a W2 input (unit H06, the code route for Opus 5.5 max review 08; by 1 and
  5.2 a refusal and an answer are two outcomes): the filter bears when, on such a dataset, the values before the
  recordings() call answer and the statement without the filter does not refuse V007 (Decide.w2_nopt, in the model
  of the statement without the filter, kind rs, whose certificates have no participants.tsv). This overturns v4 fix 08
  and Phase F, which called a filter that keeps every participant idle (S008 W2) by asking only of datasets whose
  participants() reads;
- `where` with conditions `eq`/`ne` (a column and a string literal) and `ge`/`gt`/`le`/`lt` (a column and a
  numeric cutoff `c`, no unit), nested `where`;
- `rows`, `count`, `share` (one or two arguments);
- `cell(t, r, k)` with t a `tsv`/`csv` table, r a row position or `key(k1, "v1", ...)` (one or more pairs), k a
  column; `header(t, k)`; `number(x)` with x a `cell` or `header`;
- `difference` of two counts or of two numbers; `exceeds`/`below`/`atleast`/`atmost` of a count, a number or a
  share with a numeric cutoff.

**Part N** (phase 4) adds: `sum`, `mean`, `max`, `min`, `order(x, k, j)`, `median` of a column over a table or
selection of a `tsv`/`csv` slot, and `widen(x, tolerance = q)` (q > 0, no unit) of a number; differences and
comparisons of these. One column both summed (`sum`, `mean`) and ordered (`max`, `min`, `order`, `median`) in one
statement is in part N since Part B item (e2), 27 Oct 2026 (3.5, summed and ordered). A `mean` inside a `difference`
is in part N since Part B item (e1), 27 Oct 2026 (3.5, means in a difference). Named rows (`cell`, `key`,
`header`) with an aggregate of the same table are in part N since item 6 (d), 27 Oct 2026 (3.5, named rows), and
with a variance of that table there is nothing to decide: such a statement cannot be written (3.7, last paragraph).

**Part H** (phase 5) adds file-level readers, each file read by one of them: `json(f)` with `member`/`item` chains
(a node may be an object, an array, a number, a string, or true/false/null); `nifti(f)` with `dim(n, k)`; `size(f)` and
`bytes(f, o, n)`; their numbers in differences, `widen` and comparisons. Since Part B item (f) (27 Oct 2026) also
`pixdim(n, 4)` (3.6: float64 values times the time unit; cutoffs and tolerances in `s`). Outside part H for now: `number()` of `bytes()` or of a JSON string; a file read by
two kinds of reader (for example `size(f)` and `json(f)`) other than those of 3.10; two look-alike keys named under one
JSON object.

**Part V** (the variance phase) adds `sample_variance`, `population_variance`, `sample_sd`, `population_sd` of a column
over a table or selection, when the variance is the statement or the statement compares it with a cutoff (3.7).
Since items 5a and 5b (27 Oct 2026) also a variance or SD under `widen`, and a `difference` of two variances (under
`widen` or compared); since the variance shape (28 Oct 2026, 3.7) a sum of three or more signed variances of one
table, or two with a `widen` inside. Outside part V for now: a variance in a statement with other aggregates of its
column or named rows of its table; the variance shape over a selection or two tables. (A variance minus a number that is not a variance never reaches the exact
path: it refuses S006 by its sort, SPEC 7.2; an SD in a difference likewise, O4.)

Columns are positions after SPEC §4.1's resolution of header names (`_as_judged`). Also outside part T: a file
name read both by `tsv` and by `csv` (except `rows()` of its `tsv`, tc1, 3.10, and a `where()` of its `tsv` under `rows()`/`count()`, 3.13); a literal on a
column read as a number that the number reader refuses (R007). A statement outside part T was decided by SPEC
§4.4 until its part's phase; since the search was deleted (phase 7, 28 Oct 2026) it refuses S013 (D5; the message
says Reality cannot decide this kind of statement, never that the value is constant).

Two literals on one column that look alike (equal UTS #39 skeletons; `key` literals included) are in part T since
Part B item 2 (28 Oct 2026). A row holding a string that looks like a `where()`'s or `key()`'s literal on that
column and is not it makes that `where()` or `key()` refuse K002 (principle section 10.3), no answer. Per `where()`
and `key()` and column, `Model.scope` splits the case by whether such a literal class has rows (and, per skeleton
group of g other literals, by the 2^g presence patterns, two present refusing); the refusing cases are no answer
(SPEC 4.4 item 11), the others go on as before. Each case is charged in Model.steps.

**Readable inputs of a table slot** have every column the statement reads: a table that lacks one refuses V002
for every value that reads it, and is not counted as an input on which a part changes the outcome. This is the
search's input space too (its tables always hold every named column, SPEC §4.4 item 5); it is stated here
because it is a definition, not a fact about readers (an open question for BB at the phase 3 checkpoint).

## 3. The model

### 3.1 Row types
For each table slot and each column the statement reads (a condition's column, a `key` column, a `cell`
column), the cell classes are: "equals ℓ" for each literal ℓ compared with that column (`eq`, `ne`, `key`);
"other", text that is no literal and no decimal; and, when the column is read as a number (a number condition
on it, or `number(cell(…, k))`), "a decimal other than the literals" at each point and in each open interval
into which the column's cutoffs and the decimal values of its literals cut ℚ (a point only when it has a
finite decimal). A literal's class has its literal's value (or none, when the number reader does not read it).
A row type is one class per such column. Every condition has one value on a type: `eq`/`ne` compare the class
with the literal; a number condition compares the class's value with its cutoff (the cutoffs are points, so it
is the same for every decimal of an interval), and has no value on a class with none. A selection is a set of
types; where() refuses V005 on the types on which every byte condition holds, every number condition holds or
has no value, and one has none (SPEC 7.3).

**Readable numbers (P1, 27 Oct 2026).** "Decimal" in this model means a number the reader reads
(readers.decimal: at most MAX_DIGITS = 1000 digits before the exponent, |exponent| ≤ MAX_EXPONENT = 1000):
R = {M·10^p : M an integer, |M| < 10^1000, −1999 ≤ p ≤ 1000}, largest RMAX = (10^1000 − 1)·10^1000. So 10^−1999
(`0.0…01e-1000`) is readable, and an interval class exists only when R meets it: (1, 1 + 10^−999) holds no readable
number and gives no class (decide.in_r, nxt, prv, inside). Every value the model writes is in R and spelled so the
reader reads it back (dec_seq: plain text while 1000 digits allow, then mantissa-exponent forms); a certificate
needing a value the solver allows only between ends closer than R allows, or more spellings of one number than R
has, is R013 (Big), never an unreadable certificate. The search for such a value (inside, split) is charged to
the step meter (P2). **No readable point at the solver's choices (call 2, 27 Oct 2026).** When back-substitution finds no readable
value for a variable, the case is not refused: the readable points are searched exactly. R is cut into bands (the
numbers of one magnitude [10^m, 10^(m+1)) are the multiples j·10^(m−999), those below 10^−1000 the multiples of
10^−1999; decide.bands). A read value z is split three ways: z = g·(a + J) with J a natural ≤ b − a (on the band
(g, a, b) of the least readable number above its lower end), z below that band, z above it. A summed column of a
type is cut into parts by bands (Model.refine): q rows in a part of one band sum to g·(a·q + K), 0 ≤ K ≤ (b − a)·q,
which are exactly the sums of q numbers of that band, so the part is exact; a part of several bands holds a sum
between q times its least and greatest numbers, and is halved whenever the solver's sum is not reached by readable
rows. A sum is a multiple of 10^−1999, so a sum with no such multiple between its ends is split at the nearest one.
Every split is one more case of the question, at most MAX_CASES (3.4) in all, and each system's integer step is
charged in 64-bit words of its largest coefficient (8), so the 50,000,000-step bound also bounds the work on
1000-digit numbers. R013 here means only that this search exceeded MAX_CASES cases or the step bound: never "no
readable point found".
**Rows between two order statistics (call 3, 27 Oct 2026).** A piece of an ordered column strictly between two of its
ends (order statistics' values or the class's ends) that holds rows at a solution but no readable number is split
(Model.thin, Model.gap_cases): no rows in it; or rows and, when the lower end is a constant e, the upper end above
nxt(e); when it is a value w, w's band (g, a, b) as above with w < g·b and the upper end above w + g (no readable
number lies between two multiples of a band's step), or w = g·b and the upper end above nxt(g·b), or w below or
above the band. Together these are exactly the solutions whose piece holds a readable number.

### 3.2 Inputs as vectors
An input is seen as the vector n of row counts per type, n_t ∈ ℕ, plus the named rows of 3.4. Literals are
taken in byte order, so the types do not depend on the order of the text. Spellings, per column: an "other"
cell is the v-th of a, b, …, z, aa, … that is not a literal, does not look like one or like an earlier spelling,
has no digit in its skeleton (so it looks like no decimal) and holds no invisible character; a decimal class's
cell is the shortest decimal of its value (an interval: the integer in it nearest 0, else the shortest decimal
above its lower end) and then the same with one, two, … more zeros, skipping any that is or looks like a
literal. Unnamed rows use spelling 0; the i-th named row spelling i + 1 (so two named rows never hold the same
bytes unless both hold one literal). A table of slot s has the header `c1 … cw zpad` (w the largest column the
statement reads; a header cell `header()` reads has its own class, 3.4) and each row one cell per column: the
class's cell in a column the statement reads, `p` elsewhere, `p` in the extra column (so no row is a blank
line). **Realisable** (probed with the slot's real reader): a class of column k is realisable when the one-row
table holding its spelling 0 in column k, `p` elsewhere, is read back with exactly those cells; a type is
realisable when each of its classes is (H1 below). Only realisable types get a variable. When the header-only
table is not read back as no rows, the slot's inputs also satisfy Σ n_t ≥ 1. [abstraction] proves that counts
of selections over all row lists equal the same sums over all vectors; [real_abstraction] carries this to all
accepted inputs under reader facts H1 and H2 (section 7).

### 3.3 Values as branches
In one case (3.4), each value is a list of **branches** (atoms, result): the atoms are a conjunction of linear
atoms over the row counts n and the named cell values z; the branches of a value exclude each other and cover
the case; the result is its outcome there. A refusal comes from the first sub-value that refuses in the
evaluator's order (arguments left to right, then the call), so a call's branches are its arguments' branches
combined in that order.

| value | branches |
|---|---|
| `tsv(f)`, `csv(f)` | one: the table (the selection of every type) |
| `where(x, c…)` | x's refusals; else, with U the types on which it refuses V005 (3.1) and G = Σ_{t∈U} n_t + (named rows of a type in U): G ≥ 1 → V005; G ≤ 0 → the selection of the types on which every condition (x's and these) holds |
| `rows(t)`, `count(x)` | x's refusals; else the form Σ_{t selected} n_t + (named rows of a selected type) |
| `share(sel[, base])` | refusals of sel, then of base; else with S, B the two counts: B ≤ 0 → V003; B ≥ 1 → (S, B) |
| `difference(a, b)` | a's refusals; else b's refusals; else form(a) − form(b) |
| comparison of a form F with c | F's refusals; else holds: F − c > 0 (exceeds), ≥ 0 (atleast), < 0 (below), ≤ 0 (atmost); fails: the negation |
| comparison of a share (S, B) with c = p/q | the share's branches; for (S, B): q·S − p·B compared with 0 as above (B ≥ 1 there) |
| `cell(t, r, k)` | V002 when position r is not present in the case; else the cell of that named row |
| `cell(t, key(…), k)` | V004 when the key is "none" or "many" in the case; else the cell of its named row |
| `header(t, k)` | the header cell k |
| `sum`, `mean`, `max`, `min`, `order`, `median` | x's refusals; then V005, V003, V009 and the value as in 3.5 |
| `widen(x, tolerance = q)` | x's branches, with q added to the term of x's identity (3.5) |
| comparison of a widened value [a0 − w, a0 + w] with c | holds and fails by SPEC 5.2's ends (exceeds: a0 − w > c, fails a0 + w ≤ c; and so on); V006 (neither) when w > 0 |
| `number(x)` | x's refusals; for a cell of class: a literal with a value, or a point → that constant; "other", or a literal with no value → V005; an interval (lo, hi) → the variable z of that cell, with the atoms lo < z < hi (a header cell: "other" or "a decimal", z unbounded) |

A share's answer is S/B when B ≥ 1 and V003 when B = 0. A cell's answer is its bytes: the literal for a
literal class, else its own spelling (3.2). Strict integer inequalities are written `g − 1 ≥ 0`.

**Region grouping.** In one system, variables whose coefficient columns are equal across all its atoms
are merged into one (their sum) [merge_columns]. This is exact, and is done before solving.

### 3.4 Cases of the rows a question names
The rows a question's values name (by position r in `cell(t, r, k)`, by `key(…)`, and the header cells of
`header(t, k)`) are not counted by n; they are fixed in finitely many **cases**, per slot:
- h, how many of the named positions r₁ < … < r_m exist (0 ≤ h ≤ m);
- for each key: "none" (no row matches), "many" (two or more), or the named row that is its one row: one of the
  h present positions, or an extra row (keys that share an extra row are numbered in order of first use);
- the type of every named row (the h positions, then the extra rows): a row that is a key's one row has a type
  that matches the key, every other named row a type that does not; with "none", no named row matches;
- the class of each header cell read ("other"; also "a decimal" when `number(header(…))` reads it).

A case adds the atoms: for a key with a row or "none", no unnamed row matches it; for "many", the matching rows
(named and unnamed) are at least 2; with h ≥ 1, the unnamed and extra rows fill the places before r_h
(Σ n + extras ≥ r_h − h); with h < m, the table has fewer than r_{h+1} rows. Every readable input is in a case
(take its rows at the named positions, the one row of each key that has one, and its header), and every
solution of a case's atoms is an input (6). The cases of a question are those of every value in it (W2: both
values), at most MAX_CASES = 10,000 [prov]; more refuses R013.

### 3.5 Aggregates (part N)
A column an aggregate reads is read as a number (3.1); its **regions** are its points and the open intervals between
them, in increasing order.
- **Sums.** For each type t of an interval class (lo, hi) that a `sum`/`mean` of the question selects, either t has
  no rows (n_t = 0, y_t = 0) or it has rows: n_t ≥ 1 and the sum y_t of the column over them, a rational, with
  n_t·lo < y_t < n_t·hi (each finite end). This is not a case (item 8, 27 Oct 2026): a system first holds, for each
  such t, the closed n_t·lo ≤ y_t ≤ n_t·hi, which every input of either kind satisfies (a relaxation). No solution:
  none of either kind. A solution where every such t is of one kind is one of the question's. Otherwise the first t
  that is of neither kind (n_t = 0 with y_t ≠ 0, or n_t ≥ 1 with y_t at an end) is decided both ways, "no rows" first,
  and each system solved the same way; so the answer is the one the 2^k cases would give, and only the types some
  solution touches are split. At most MAX_CASES systems per question; more refuses R013. A point that 5.4 moves off a
  solution (a count + 1) and that leaves a type's sum outside its bounds is written with n_t rows of the class's own
  value; its outcome is checked on the bytes as every certificate's. A point class p contributes p·n_t. sum = Σ over the selected types
  that read a decimal; mean = (that sum, the count) as a ratio, V003 when the count is 0.
- **Order statistics.** max, min, order(·, ·, j) and median have a value u, a rational: the case says which region u
  lies in (only regions holding the class of a type it selects) and, for those in one interval region, their order
  (ties allowed). In an interval region holding values w_0 < … < w_{m−1}, the rows of each type there that some order
  statistic of the column selects are counted in the 2m + 1 pieces (below w_0, at w_0, between, …, above w_{m−1}):
  natural variables adding up to n_t. "Below u", "at u", "above u" are sums of n_t (other regions) and pieces. The
  value is u exactly when [L4, kth]: fewer than j rows below and at least j at or below (order j); max: none above,
  one at; min: none below, one at; median of n = 2m' + 1 rows (m' a natural variable): at most m' below, at least
  m' + 1 at or below. V005 when a selected row is not a decimal, V003 when empty (order: fewer than j rows), V009 for
  a median of an even count n = 2m' ≥ 2.
- **Named rows (item 6 (d), 27 Oct 2026).** A named row of the case (3.4) is a row of its table, so aggregates count it:
  its value in an aggregated column is a constant (a point class) or a variable z with lo < z < hi (its interval class,
  as `number` reads it); a sum adds the named rows of the types it selects (z or the point); a count already adds them
  (3.4). When its class lies in an interval region holding order statistics' values w_0 < … < w_{m−1}, the case also
  says which of the 2m + 1 pieces it lies in (z < w_0, z = w_0, w_0 < z < w_1, …), and below / at / above u count it
  as a constant. These cases multiply the case count, at most MAX_CASES (else R013). All linear.
- **Means in a difference (Part B item (e1), 27 Oct 2026).** A mean that a difference subtracts or is subtracted from
  is a rational variable mu (one per pair of forms (S, N): two means of the same rows are one variable) with S = mu·N,
  N ≥ 1, not linear. Model.solve decides it by cases on N: first mu ≤ 0 or mu ≥ 0 with 1 ≤ N ≤ MAX_ROWS (unbounded
  in the unbounded system), each holding the hull of {(mu·N, mu)} there (a·mu ≤ S ≤ b·mu for mu ≥ 0, mirrored for
  mu ≤ 0) and, where mu's class bounds l, h exist, McCormick's four products ((mu − l)(N − a) ≥ 0 and the like); at
  a = b the atom S = a·mu is exact. A solution with S ≠ mu·n at its count n splits the range into [a, n − 1],
  [n, n] (solved first) and [n + 1, b]. So "no solution" is the answer every input gives (each atom holds on every
  input of its range), a solution is one (S = mu·n holds), and the ranges shrink, so the cases end; past MAX_CASES
  systems the question refuses R013. Atoms that hold on every input and only cut the relaxation: mu above the least
  lower end and below the greatest upper end of its types' classes (strictly unless a point class is at the end); two
  means equal once the types the system gives no rows are dropped (same_means); for a mean Q of a mean P's rows and of
  types R more (no named rows), three cases on P against R's class ends [l, h] (P ≥ h: l ≤ Q ≤ P; P ≤ l: P ≤ Q ≤ h;
  else l ≤ Q ≤ h), since Q lies between P and R's mean (P and Q of one column: the cases compare values of one column, Part B item (pm), 28 Oct 2026); for two means Q1, Q2 of one column whose rows share types I without either holding the other's, the mean P of I's rows, a rational variable with no atom of its own (it is that mean; when I has no rows, Q is R's mean, in [l, h], and one of the three cases holds whatever P is, so they hold on every input), with these cases for Q1 and for Q2 (caps, item (pm)), split only at a solution that breaks S = mu·N and admits no value of P meeting one case of each (cap_ok: the cases are linear in P, so their roots, the points between and one beyond each side are tried, exactly), since split up front they multiply the cases of questions they do not cut; and for a mean whose class end L is a point class's, two
  cases: strictly inside, or mu = L with no rows of the types off that point. Cost: a statement whose solutions keep
  breaking S = mu·n walks N and may refuse R013 (KNOWN-OPEN, Part N).
- **A column summed and ordered (Part B item (e2), 27 Oct 2026).** In a column both summed and ordered, a summed type
  of an interval region holding order statistics' values w_0 < … < w_{m−1}, selected by one of them, has its unnamed
  rows split into the 2m + 1 pieces (named rows, 3.4); its sum y is the sum of its pieces' sums S_i, with S_i = w_j·P_i
  for the piece at w_j and S_i = v·P_i for a piece between two ends, v a rational variable strictly between them (the
  piece's mean; any value when P_i = 0). Each S_i = mu·P_i (P_i ≥ 0) is decided as a mean in a difference is (above):
  cases on P_i's range, exact at a point, a solution breaking it split at its count. The sign split is shared: a w_j's
  sign is split once for every piece at it, and a piece between two ends takes the sign an end gives (lower end ≥ 0:
  v > 0; upper end ≤ 0: v < 0), no split when both region ends are finite (McCormick only). Atoms that hold on every
  input and only cut the relaxation: for a mean whose types are in such pieces (pcuts), the cases of its lowest and
  highest piece holding rows (or none), of whether its other types have rows (their classes' ends l, h), and of which
  end is the outer one; the mean lies between the lower and the upper (so a mean is at most the max of its rows). A
  certificate's rows are built piece by piece: w_j itself, or decimals strictly between the ends adding up to S_i (6).
- **A mean against an order statistic of its column: half cuts (3.5a; Part B item 1, BB's call on Patsak's behalf,
  28 Oct 2026, reversible).** For a mean M (no named rows; mu = S/N) and an order statistic u of the same column in a
  case (u's region r, its rank q among the region's w_j), let a be M's rows not known to be at or below u: its types of a
  region above r, in r the pieces above u's piece (2q + 1), and its types in r without pieces. Every other row of M is
  at most u and every row at most h, the greatest upper end of M's classes, so S ≤ (N − a)·u + a·h. When the case's
  count atoms (those over row counts, piece counts and a median's m only; a subset of the system, so they hold on every
  solution) have no rational point with 2a ≥ N + 1 (lp's Farkas certificate, checked), every solution has 2a ≤ N, and
  mu ≤ (u + h)/2 is added: for u ≤ h, S ≤ N·u + (N/2)(h − u); for u > h no row of M is above u and mu ≤ h < (u + h)/2.
  Mirrored with b, M's rows not known to be at or above u, and l, the least lower end: mu ≥ (u + l)/2. When the counts
  give a = 0 (no point with a ≥ 1), mu ≤ u, with no end needed (S ≤ N·u); b = 0, mu ≥ u. The cuts hold
  on every input, so they only cut the relaxation. They are lazy: when a case's system has a solution, the first cut
  it breaks whose count condition holds (charged as a system, as side work: its atoms, and lp's square; item (g)) is added and the case solved
  again (a case of the stack, counted in MAX_CASES); no condition is tested for a cut the solution keeps. (Computed
  eagerly once per case, they cost find()'s W2 rounds 1,551 cut computations and 6,412 lps on test_find_cap's claim,
  R013 at the step bound in 483 s; lazily 15 and 21, S008 W2 in 73 s.) Trigger: atmost(difference(mean(where(t, le(x, 1)), 2), median(where(t, gt(x, 0.4)),
  2)), c = 0.5) holds on every input (the value is below (1 − 0.4)/2 = 0.3) but walked N until the memory bound (R013,
  CHECKPOINT-V); with the cut it refuses S008 W1 in about 4 s.
- **widen and identities.** A number carries terms {identity: coefficient} (SPEC 5.2): widen adds q to the term of its
  argument's identity; difference subtracts terms. Identities are those of SPEC 5.1: an aggregate's or a count's is
  (computation, slot, the rows it selects[, column, rank]); two of them with the same computation and column are one
  exactly when the types in only one of the two selections have no row, so a difference branches on that count (0, or
  at least 1). The answer is [a0 − w, a0 + w], w = Σ|coefficients| (a constant in each branch). A `recordings()`
  aggregate's identity is the kernel's, the recordings it reads (SPEC 5.1): two of one dataset with the same
  computation and quantity are one exactly when the recordings only one set holds are none (one task: the regions of
  3.9 only one set takes have no recording; two tasks: both sets are empty), so a difference branches on that count
  too (Model.idsize; unit G01, Opus 5.5 max review 01, BB's call on Patsak's behalf 30 Oct 2026, reversible: they
  were never one before, a wrong S011 and an X001 on datasets where both sets hold the same recordings).

### 3.6 File-level atoms (part H)
- **Raw file** (`size`, `bytes`): its size is a natural variable in 0..2^63 − 1 (an off_t; item 7 of Part B, 27 Oct
  2026: no MAX_ROWS bound, so `atmost(size(f), c = 10^7)` is decided; its certificate file is held as its byte rule,
  `witness.Periodic`, so the real size() and bytes() read it at any size; up to MAX_TEXT_FILE it is also its bytes). `bytes(f, o, n)` is V002 when size < o + n, else n bytes of the file: free (any two ranges can hold
  different bytes; one range is one answer).
- **NIfTI** (`dim`): the case gives dim[0] in 1..7; `dim(n, k)` is V008 for k > dim[0], else a natural variable in
  1..2^63 − 1 (NIfTI-1 reaches 32767; a header with a larger dim is written as NIfTI-2). Only the header is read
  (SPEC 7.6).
- **JSON** (`member`, `item`): the case gives, for each node on the named paths, its kind (object, array, number,
  string, true/false/null), whether each named member is there, and each array's length as "the first h named indices
  exist" (0 ≤ h ≤ their number). A chain's outcome follows the kernel: V002 for a member of a non-object, a missing
  member, an item of a non-array or past its length; a number or string where an object or array is needed is S007,
  and true/false/null as a value is J004 (both: no answer on that input); a number leaf is a rational variable z
  (any decimal), a string leaf free bytes (its own spelling per path), an object or array leaf a free tree (another
  member or item is another answer).
- **NIfTI** (`pixdim(n, 4)`, Part B item (f), 27 Oct 2026): when pixdim() reads a slot its case also gives the time
  unit code of xyzt_units (8 s, 16 ms, 24 us; 0 for any other, which is I005 and also stands for a NaN pixdim, the same
  answer), from dim[0] = 4 (below 4: V008); with no dim() read on the slot, dim[0] takes only 1 and 4 (they stand for
  1-3 and 4-7: pixdim's answer depends on nothing else). The value is f·u, f the unit's factor in seconds and u a
  float variable: a finite float64 (|u| ≤ FMAX). A NIfTI-1 pixdim is a float32, which is a float64 too, and NIfTI-2
  holds every dim NIfTI-1 does with the same answers, so certificates are NIfTI-2 headers (pixdim[4], xyzt_units).
  The solver treats u as rational; back-substitution picks a float in u's interval (0 if it fits, else the one of
  fewest binary digits). When the interval holds no float at the solver's choices, u's range of the floats is split
  (as call 2 splits R's bands): 0 alone, the negative floats, the positive ones; a range over binades ea..eb is
  u = sg·2^ea·J with J a natural (a superset of its floats), halved until one binade, where every lattice point is a
  float, so the leaves are exact and the search is complete. In a pixdim model, before the rational relaxation, integer bounds are
  propagated (empty_box: it only ever says "no solution"); a pixdim model memoises one_solve per system (find()'s
  rounds re-solve each option), a repeat charged one step. Two floats met only in bounds on one form u + r·v (every atom naming a pixdim is that, or |u| ≤ FMAX) are
  decided before any range is split (fwin, 28 Oct 2026): with q(u + r·v) = A·u − B·w (r = p/q, w = ±v) and floats
  m·2^e (|m| < 2^53, −1074 ≤ e ≤ 971), for each smaller exponent e, gap d and order the window's multiples of 2^e
  are met by integers |x|, |y| < 2^53 with A·x − B·2^d·y in them (fpair: y's residues mod A/gcd(A, B), one per
  class, x's interval moving by exactly B/gcd per period); d runs from the least gap that reaches the window to
  where B·2^d passes every multiple, so every float pair is reached: a pair pins u and v, none drops the case. Each
  (e, d, order) and residue is charged; past the step bound R013. Other float systems (three or more floats, or a
  float in two forms) are split by ranges as above and may refuse R013 at the step bound (KNOWN-OPEN, Part H).
- **Identities** (widen): a JSON value's is its slot and path; a size's its file; a dim's its file and axis; a
  pixdim's its file (pixdim of two slots is never one identity).

### 3.7 Variances (part V)
The variance node's branches: V005 when a selected row is not a decimal, V003 with fewer than 1 + ddof selected
rows (ddof 1 for the sample convention, 0 for the population one), else an answer. In an answering case the **free**
types are the selected decimal types the case's atoms do not force to 0. Over all answering cases:
- **W1 of the variance**: two answers exist exactly when some case's free classes hold two distinct readable values
  (equal rows give 0; two different values give more). Certificates: two tables of two rows, (L, L) and (L, U).
- **Its values** reach 0 (equal rows) and reach sup = (U − L)²/2 (sample) or (U − L)²/4 (population), with L the
  least and U the greatest readable value the free classes hold (3.1: nxt of an open lower end, prv of an open upper
  one, ∓RMAX for an unbounded one, so no placeholder; P1, P4) [Var.sample_le, population_le]; the two rows L, U reach
  it [Var.reach]. An SD's comparison
  with c < 0 always holds (exceeds, atleast) or always fails (below, atmost); else it is the variance's with c².
  So, for the variance v and cutoff C: some v > C iff sup > C; some v ≥ C iff sup ≥ C;
  some v < C iff C > 0; some v ≤ C iff C ≥ 0. A comparison has two answers when it holds on some input and fails on
  another; certificates: two equal rows (v = 0), and the two rows L, U (no search; P2).
- **W2** of a condition of the variance's selection: without it the selection gains the types E. If no row of E can
  exist, the two selections are always the same. If one can, the outcomes differ on some input through refusals
  alone (the side without E's rows has fewer than 1 + ddof rows, V003, while the other answers; or E's row is not a
  decimal, V005 against V003). So two answering branches never need their values compared: their difference is
  taken as none, and the count systems of 5.2 decide.
- **Under widen() (item 5a, 27 Oct 2026).** A variance or SD under a chain of widen() (widths add: w), alone or compared
  with c. W1 of the chain is W1 of the variance. A comparison holds and fails on rays of the value with ends c ± w
  (exceeds: holds iff v > c + w, fails iff v ≤ c − w; atleast ≥ / <; below and atmost the mirror), and a ray meets
  the values exactly as above. W2 of a widen(): at the top, any answering input (another width is another answer);
  under a comparison, with w' = w − q its width without it, the outcomes differ exactly when the value lies in the
  pieces K of the line where the answer (holds, fails, V006) at w and at w' differ (constant between the four
  points c ± w, c ± w'; an SD's pieces squared). K missing [0, sup] means no input (exact). Else a witness is
  searched: 0 or sup in K (the two rows above); two rows u, v with (u − v)²/2 (sample) or /4 (population) in K,
  u an end or a short readable number of a class, v in a class between bounds within 10^−2100 of the exact square
  roots (the ends checked exactly), so every value two rows of the classes reach at the readable spacing is found;
  then (item (h), 27 Oct 2026) inputs of many rows of the classes' two readable ends L < U: j rows at U and n − j at
  L have variance j(n − j)/(n(n − d))·(U − L)², and for every n up to MAX_ROWS (and the table at most MAX_TEXT_FILE
  bytes, else it is no readable input) the j whose value first reaches a piece is solved exactly, the fewest rows
  first; then multisets of the classes' readable ends (one row per value), by size, at most MAX_CASES (BB's call 3,
  14:00). **No input (5a, 28 Oct 2026).** A class holding at most 64 readable numbers gives all of them, not only its
  ends. When every class does, the multisets range over every readable value, and n rows within [L, U] have variance at
  most ⌊n/2⌋·⌈n/2⌉·(U − L)²/(n(n − d)) (j rows at U and n − j at L, j = ⌊n/2⌋), which for n' > n is at most its value at
  n + 1 or n + 2: once every multiset of n rows is tried and that bound lies below every piece (or meets an open end),
  no input reaches K (None: widen() does not bear, S008 W2). With only two values, two_vals has tried every n up to its
  cap, so the same bound at the cap decides. (Trigger: a class of two readable values, B + step and B + 2·step at
  B = 10^502, whose sample variances skip (1/3, 1/2)·step²: a window there refused R013 at MAX_CASES in 12.7 s; S008 W2
  now in 0.2 s, partb/W5a.) A piece lying below g²/(2(MAX_ROWS − d)), g the readable step at the classes' value nearest 0 (every
  value is a multiple of g, and rows not all equal have a variance of at least range²/(2(n − d))), is met only by
  inputs of more than MAX_ROWS rows: R013 shown, not searched (D3). Past those it refuses R013: K then holds only
  values that need three or more distinct values with one inside a class of more than 64 readable numbers, or more
  rows than the multisets reach, which this search does not enumerate (KNOWN-OPEN). Each witness is confirmed by the real code on both statements.
- **A difference of two variances (item 5b, 27 Oct 2026).** V1 − V2, alone, under widen() chains, or compared with c
  (an SD, or anything else, minus a variance refuses S006 by sort, SPEC 7.2, O4). Its values lie in [−sup2, sup1]
  whatever the coupling (each Vi in [0, supi] above), so a piece of the line missing that interval is met by no input
  (exact). W1 asks whether the holds ray and the fails ray (as under widen()) each meet the values; W2 of a widen()
  whether its pieces K do; for the value itself, whether {0} and its complement do. A piece is decided by:
  - **Two equal variances** (one slot, column, selection and convention): the value is 0 on every input.
  - **One selection, sample minus population**: n·Vp/(n − 1) − Vp = Vp/(n − 1), which lies in [0, (U − L)²/4], and on
    two rows is their population variance, so the two-row search above decides it (its mirror for population minus
    sample).
  - **Uncoupled** (two slots, or one slot whose selections share no row type that can hold rows): V1 and V2 vary
    independently. A piece meeting [−sup2, sup1] meets [0, sup1] with V2 = 0 (equal rows) or [−sup2, 0] with V1 = 0;
    the ends' shifts (V1 = sup1, V2 = sup2) are tried as well; the two-row search and the multisets above find the
    other variance there.
  - **Then, and first when coupled** (selections sharing a row type), the finite domain (BB's call 2, 27 Oct 14:00) is
    searched: multisets of rows, each a row type of the selections (a type one variance cannot read is left out) with
    readable values of its classes (each class's least and greatest readable value and a short number inside; both
    columns when the variances read two), by size, the first whose exact V1 − V2 lies in the piece, at most MAX_CASES
    multisets (charged one step per row). Rows that both variances read alike (same membership, same values) are one
    item. Each variance is homogeneous of degree 2 in the values, so a multiset whose V1 − V2 = y ≠ 0 has the sign of
    a piece but misses it is scaled: its values times λ = t/X (X the largest |value|, t a short readable number with
    λ²·y in the piece), kept when every scaled value is readable and in its class (item (h), 27 Oct 2026). Each variance is also homogeneous of degree 2 in its own column alone, so with two columns one column's values are scaled alone too (λ²·V1 − V2 or V1 − λ²·V2; in a sum of variances, λ²·C_k + the rest, C_k column k's terms), on the same terms (28 Oct 2026: bfc seed 7's claim, whose window two rows reach, refused R013 at MAX_CASES before). Past that it refuses R013 (KNOWN-OPEN: the multisets use those three values
    per class, as 5a's do, so this R013 is a stopped search over a subset of the domain, not over all of it).
  - **A file slot** (W2, SPEC 4.3) under a difference over two files: with the other variance held at y, the
    slot's variance x sweeps a set in [0, sup] holding 0 and sup, and the value is ±(x − y); a value changes iff
    sup > 0, and a comparison's answer changes iff at x's two ends one holds and the other fails, i.e. y lies in
    one piece, which the two-row search finds or shows empty.
  Every witness is confirmed by the real code on the statements it separates (else X001).
- **The variance shape (28 Oct 2026).** A sum y of signed variances (sample or population; an SD there refuses S006 by
  sort) of columns of one table (no selection), at least three, or two with a `widen` inside, under `widen` anywhere in
  the difference tree, alone or compared with c. Its width w is SPEC 5.2's: each `widen` adds its tolerance, signed by
  its place in the tree, to the symbol of its base (the value under its `widen` chain), one value is one symbol, and w
  is the sum of the symbols' |coefficients| (widen(V) − widen(V) has width 0; nwidth; unit A06, Argon review 06: a value's
  symbol names no reader, as its identity, so a widened variance of tsv(f) and of csv(f) on one column cancel; unit B08,
  Argon review 2 08: so do number(header(tsv(f), k)) and number(header(csv(f), k)), the kernel's Header sort as its Cell).
  Terms of one convention and column add their signs (V − V = 0). Per column k with coefficients a (sample) and b
  (population), a·Vs + b·Vp = Vp·(a·n/(n − 1) + b) with n >= 2 rows, so it lies in Vp's range [0, (U − L)²/4] times
  [min, max] of 0, a + b and 2a + b; the columns' sums bound y, and a piece missing them is met by no input (exact).
  Else the finite domain of 5b (rows of the types every variance reads as a decimal, readable values of their classes:
  ends and a short number inside; multisets by size, scaled as item (h)) finds the witness, at most MAX_CASES multisets,
  else R013 (a stopped search, not a verdict). W1, W2 of each `widen` (the pieces where the answers at w and w − q
  differ, w − q there being the width without that `widen`, recomputed; equal widths: S008 W2) and the comparison's
  rays (c ± w) are as 5a with these values (Decide.w1_nvar, w2_nwiden, n_hit).
- **No named rows (Part B (d), 27 Oct 2026).** A variance reaches the model only as the statement, under widen(), as one
  side of a difference of two variances, or compared with a literal c (Model's vtop); its arguments are a selection and a
  column position, a selection's are a table or selection and conditions of positions, string literals and literal
  cutoffs, and a widen()'s tolerance and a comparison's c are literals (P006). The kernel refuses a variance minus any
  other number (S006, 7.2). So no cell, key, header or number of any table occurs in a statement with a variance, and the
  model's former NotT gate for "named rows and a variance of one table" could not be reached; it is removed
  (tests/test_partB.py test_d_named_rows_and_a_variance_of_one_table_cannot_be_written).

3.7a (29 Oct 2026; BB's call on Patsak's behalf 04:10, reversible). W2 of a part of a variance's selection (5.2)
compares the two values' results; for two variance results the model has said "it bears through V003/V005 or not at
all". That holds for one variance alone (dropping a condition that lets a decimal row in makes, on some input, one
selection hold d rows and the other d + 1: V003 against an answer), not beside another value refusing on the same
inputs: in Vs(sel) − Vp(sel) the condition of Vp's selection shows by V003 only where Vs(sel) is V003 as well, yet on
1, 2, −1 (sel: rows not −1) dropping it turns True into False with both answering. Two variance results whose
selections hold the same good types (those of a variance's column the number reader reads, Model.cls) answer alike
wherever both answer (a row of another type makes V005), so the rule stands there (rows not "a" beside rows not −1:
S008 W2, decided). So when that rule met two variance results whose good types differ (or a sum's, which it does not
tell apart) and no input is found, the part is not decided: S013
(NotT in Decide.w2 and slot_bears), never S008 W2. Found by the shape-1 ground-truth runner (bf1n.py VAR=1 seed 3) on
the tsv() form, then shown on csv() alone: wrong since 84a24d6 (27 Oct 2026, a difference of two variances decided), the
first commit putting a second variance beside the first (bisect, KNOWN-OPEN). Decided since 3.7b.

3.7b (29 Oct 2026; BB's call on Patsak's behalf 05:40, reversible). Where 3.7a stops, the part is decided in two
steps. (1) The same rows (Decide.same_rows, the model's): when, for each variance of the statement and its place in the
statement without the part, every pair of their answering results that a case admits together has the same slot,
column and ddof and the same good types less the types the case and the pair's atoms give no row, the two read the
same rows wherever both answer (a selected row of another type makes V005), so the statements answer alike wherever
both answer; a pair where one refuses is outcomes_differ's V against an answer, which w2_input has searched. The W2
refusal stands then (a 'model' record). (2) Else a
witness search over a finite domain (search.joint_rows, outside the trusted base): rows of the types the variances'
answering cases select (Decide.var_cands of every variance of the statement and of the statement without the part),
each with readable values of its classes (in an interval class the short numbers 0, 1, -1, 2, -2, 3 and 1/2 it
holds first, then Decide.dvals: its two readable ends and a short number inside), the shortest rows first, as
multisets by size, at most MAX_CASES multisets (each charged its rows) and W.MAX_WITNESS_STEPS.
The first multiset on which the real code gives the two statements different outcomes (an answer or a V refusal
each, SPEC 4.4 10) is written as bytes again and confirmed by Decide.differ_on: the part bears (no refusal from it);
rows that do not confirm are X001. For a file slot (slot_bears) the same search runs over the slot's and the copy's
rows. No multiset found is no proof: R013 (a stopped search at a stated bound), never S008 W2. The search's domain
is a subset of the inputs, so a part that bears only on inputs outside it refuses R013; no refusal rests on it.
Ground truth (partb/S13/s7 samesel, s8): the 28 statements of the targeted set that 08a879a refused S008 W2 wrongly
(each contradicted with an input where both answer) form; the counts are in the commit message.

### 3.8 A recording's values (BIDS; Part B items 2c and 3, 28 Oct 2026)

`tr(r)`, `volumes(r)`, `onset(r, i)`, `duration(r, i)`, `events(r)` and `trials(r, type)` of `r = recording(bids(d), sub,
task[, run], acq(..), rec(..))` (string labels; a trial type as in 3.9), anywhere in a statement (item 3; 2c: only as the
statement or its comparison, one value). The dataset slot d has kind `rec`; its cases are, per named recording: absent
(not exactly one BOLD recording has these entities: V004); present with dim[0] >= 4 or below (V008 in volumes(), only
when volumes() is read); when onset(), duration(), events() or trials() is read, no events file (V007) or one with as many
rows as the k-th named row index (V002 for a named row past them; rows: onset() and duration()'s indices); when trials()
is read and there is an events file, a single trial_type column or not (V002 in trials()). The values' readable sets:
- tr: the readable decimals q with TRLO < q < TRHI, TRLO = 2^-1075 x 10^-6 s, TRHI = 1.7 x 10^308 s. tr_consistent
  needs pixdim[4] = nearest(q / unit) > 0 and nearest()'s |q / unit| < 1.7 x 10^308 (float64, NIfTI-2): in s for
  q > 2^-1075 (ties to even send 2^-1075 to 0), in us below; no unit and no float width reach further.
- volumes: dim[4], an integer 1 to 2^63 - 1 (NIfTI-2 int64).
- onset: any readable decimal q < volumes x tr (Reality's own B30 rule; a 3-D image counts 1 volume), so: with tr read,
  q < (2^63 - 1) x tr; with volumes read, q < volumes x TRHI (4-D) or q < TRHI (3-D); with neither, q < (2^63 - 1) x
  TRHI (open: tr < TRHI). Onset with both tr and volumes of one recording (bilinear, like 3.5's S = mu·N) is not
  modelled (NotT); no statement holds the three without a unit refusal.
- duration: any readable decimal q > 0 (B06).
- events: the number of rows n, at least the case's last named row and below the next; trials(type): per type a count
  k >= 0, the types' counts together at most n (the other rows hold a type that looks like none of them; a row that
  looks like one makes trials() refuse K002, no answer, so it is no readable input of the value).
Two named recordings one of whose labels are within the other's: decided since 3.8a; participants beside a named recording: since 3.8b. Two look-alike trial types of one
recording stay outside (NotT). A value's identity (widen, difference) is its recording and
what it reads. Certificates (Model.rec_dataset): dataset_description.json and README, per named recording that is
there its NIfTI-2 BOLD image (dims 1 x 1 x 1 [x volumes], one byte per voxel, pixdim[4] the float64 nearest to tr in s,
or in us below 2^-1075), its sidecar (TaskName, RepetitionTime) and its events file (row i at its onset and duration,
other rows at 0 and 1; with trials() a trial_type column: each type's rows, then a type that looks like none); values not
read are chosen so that volumes x tr exceeds every onset (with volumes read, tr strictly between the onsets / volumes
and TRHI). A certificate image holds at most MAX_VOL = 10^6 volumes and an events file MAX_ROWS rows [prov]: find()
first looks for a solution with volumes, rows and counts <= 2, 64, then MAX_VOL (rows MAX_ROWS); one that needs more
refuses R013 (a stated bound on the certificate, not a verdict).

#### 3.8a Two named recordings, one's labels within the other's (item 4 shape 5; BB's call on Patsak's behalf 29 Oct 2026 07:30, reversible)

The smaller recording's sidecar applies to the larger one too (S0133: a JSON whose entities are a subset of the file's,
in the root, the subject folder or the file's folder; a deeper one overrides a shallower one, and two in one folder
that set a key to different values make the dataset refuse B30). A recording's values are its own image's (volumes),
its own events file's (events, trials, onset, duration: an events file is found by its stem only) and its sidecars'
(tr); the larger recording's own sidecar sets its RepetitionTime over the inherited one, so every pair of values the
two recordings' cases allow is reachable and the model of 3.8 stays exact with no new variable. Certificates
(Model.rec_dataset) put each recording's sidecar in the folder Model.rdep gives: the recording's func folder (2), else
the subject folder (1), else the root (0), one level above every named recording whose labels hold its own. A chain of
four such recordings adds the run alone at one step, and a dataset holding a recording and one equal but for the run
refuses in bids() (B30 inside B00, S0265) while one without the other refuses V004: a statement naming both never
answers, so it is never decided (the NotT "four recordings nested by labels" is not reached by one that answers).

#### 3.8b Participants and a named recording of one dataset (item 4 shape 4; BB's call on Patsak's behalf 29 Oct 2026 08:40, reversible)

participants(bids(d)) beside recording(bids(d), ...) of one dataset: the slot is kind `pt` (2b) with the named
recordings' cases (one ('rec', d) key each, as 3.8). bids() refuses a subject folder with no participants.tsv row (B11),
so a recording that is there has its subject's row: when participant_id is read and sub-L is one of the statement's
literals, that literal's class holds at least one row; else at least as many rows hold a label no literal names as
there are present recordings whose subject is none (a row per subject: its label is the subject's). A participant and a
recording label that look alike but differ (U+00A0 and the like) stay outside (NotT). recordings() beside a
named recording of one dataset stays outside (NotT "recordings() and a named recording of one dataset"). Certificates
(Model.rec_dataset with the table): the participants.tsv rows of 2b, relabelled so each present recording's subject is
a row's label, its recordings as 3.8, and per row whose subject has no recording an anat T1w.nii (B11 holds for it).

### 3.9 Recording sets (BIDS Phase F; Part B items R1, R2, 28 Oct 2026)

`count(rs)` and `sum`, `mean`, `min`, `max(rs, q[, type])` of `rs = recordings(bids(d), task[, sel])`, sel
`participants(bids(d))` of the same d or a where() of it (R2; q one of volumes, events, tr, trials with a trial type
that is UTF-8 with no tab, line break or invisible character; one holding a double quote, T005, or a character
readers._SEPARATORS names, T006, is in no readable events file: its counts are 0, case atoms, unit G06). Without a filter anywhere the dataset slot d has kind
`rs` (no participants.tsv is read); with one, or with participants(bids(d)) elsewhere, kind `pt` (2b) with recordings.
Two tasks of one dataset that look alike (unit G07): a dataset holding recordings of two of them refuses K003 at each
recordings() call, before its filter (kernel.bold_labels), a branch of the call (Model.alike_br).
One quantity per dataset in a statement (two: 3.9a, 3.9b); a mean only as the statement's one `recordings()` set and not
inside a difference, a min or max beside other sets as 3.9e (else NotT).

Regions (R2): per task, the sets of the statement and the wholes its parts make (the filter dropped, one condition
dropped) select types of the participants table (3.2; `selected`); a region is a nonempty class of types no set tells
apart, and a set is a union of regions (kind `rs`: one region, every recording). Variables per task t and region r: the
number of recordings of each kind: `ok` (its value answers) and, by q, the kinds whose value refuses: `3d` (dim[0] < 4:
V008, volumes), `noev` (no events file: V007, events and trials), `nocol` (no single trial_type column: V002, trials).
A case gives each region a state: no recordings (`e`, kind pt only), recordings but none answering (`z`), answering ones
(`p`); with no aggregate, any (kind pt: rows of its types); a region with recordings has a row of its types (a
recording's subject is a participant, B11). The kernel reads a set's values in sort order and the first refusing one
gives the refusal; a case fixes per region an order of its refusing kinds and an order of the regions (only with two
refusing kinds, trials; the certificate sorts its recordings so: any interleaving gives no other first refusal), and a
value is: V of the first refusing (region, kind) of the set with a recording, else V003 for no answering region (not
sum), else, over the set's answering regions P:
- sum: the sum of their y_r, lo·N_r < y_r < hi·N_r (tr: lo = TRLO, hi = TRHI, open), N_r <= y_r <= (2^63 - 1)·N_r
  (volumes), y_r >= 0 (events, trials; whole numbers); with none, 0: the sums of N values each in the range are exactly
  these;
- mean: (sum of y_r)/(sum of N_r), the same y_r (any such sum is a sum of N values in range; P1 for tr as for sums);
- min, max: per region one value m_r in one recording's range (TRLO < m < TRHI; 1 to 2^63 - 1; >= 0), the value the
  least (greatest) of them, a branch per region holding it (ties to the first): with each answering recording of a region
  at m_r (a max: one at m_r, the others at the least value) every value is one of these;
- count: the recordings of every kind in its regions. A recording set's answer (its paths) differs when its count does.
A number's answer carries whether it is recorded (kernel Num.recorded): a tr mean, min or max is; a tr sum is when its
set has an answering region (case), so two answers can differ by that alone (Model.recd). Certificates
(Model.rs_dataset): kind rs: no participants.tsv, one subject per recording; kind pt: the participants table (2b) and per
task and region one participant (the first row of its types) whose runs are the region's recordings, labels sorted as
the case's regions (others a T1w image); recordings in the case's order (refusing kinds, then the answering ones), each
a NIfTI-2 BOLD image (bold(), as 3.8), its sidecar and by kind its events file (onsets 0, durations 1; trial_type rows of
the type). find() first tries at most 2, then 64, then MAX_ROWS recordings per region and kind with a sum or value at
most as many (rs_small); a certificate needing more than MAX_VOL = 10^6 volumes or MAX_ROWS events in all refuses R013
(a stated bound on the certificate, not a verdict). Trials over two or more regions of two tasks: decided since 3.9d.

#### 3.9a Two quantities of one dataset's recordings (item 4 shape 6; BB's call on Patsak's behalf 29 Oct 2026 06:15, reversible)

Sums (and counts) of two quantities of one dataset's recordings in one statement, when they read different files of a
recording: `volumes` (the BOLD image's header) beside `events` or `trials` of a type (the events file). Each recording
then has one kind per quantity, and the two are independent (an image's dim[0] does not depend on the events file, nor
the other way), so a recording's kind is a pair (Model.rs_jk: ok/3d x ok/noev[/nocol], at most 6) and the variables are
the recordings of each pair per task and region; quantity i's recordings of kind k are the sum over the pairs holding k
(Model.rs_nq). The kernel reads each aggregate's values in sort order, the first refusing for that quantity giving its
refusal: volumes has one refusing kind, so only the events-file quantity's order matters (trials: noev and nocol), and
the case fixes it as in 3.9; the certificate sorts each region's recordings by that quantity's kind in the case's order,
then the answering. States per region and quantity: an events-file quantity `z` (none answering it) or `p` (some), as in
3.9 (y_i >= 0 alone would not force y_i = 0 at N_i = 0); volumes one state `f`, since N_i <= y_i <= (2^63 - 1)·N_i
gives y_i = 0 at N_i = 0. sum(rs, q_i): V of the first (region, kind of i) of the case's order with a recording, else
the sum of y_i over the set's regions with recordings answering i; count: every pair. Certificates (Model.rs_recs2):
per pair as many recordings as the solution says, each quantity's sum split over the recordings answering it
(W_split_int), TR 1 s; a 3-D image for `3d`, no events file for `noev`, a header without trial_type for `nocol`.
Still NotT: two quantities of one events file (decided by 3.9b since 29 Oct 07:08); tr beside another quantity (tr() reads the image header too, B09, and a
tr sum cannot meet a count, U001); a mean, min or max of two quantities.

#### 3.9b Two quantities of one events file (item 4 shape 6, coupled cut; BB's call on Patsak's behalf 29 Oct 2026 07:08, reversible)

`events` beside `trials` of a type, or trials of two or more types, of one dataset's recordings (with or without
`volumes`), sums and counts. These read one events file, so their kinds are not independent: a recording's kind is the
image's (ok/3d) times the events file's (ok: a file with a trial_type column; noev: no file, every events-file quantity
refuses V007; nocol: a file without the column, events answers and trials refuse V002), written per quantity
(Model.rs_jk). The events file's answering classes (Model.rs_evc): `ok`, and `nocol` when events is read beside trials
(there events answers and trials do not). States per region: one z/p per class, as 3.9 (y >= 0 alone would not force
y = 0 at N = 0); y per (quantity, class), so events' sum is its `ok` part plus its `nocol` part (Model.rs_ny). The
coupling (Model.rs_couple), on a region whose `ok` class has recordings: events' `ok` part >= the sum of the read types'
`ok` parts, since every row of a read type is an event, and nothing else couples them (rows of other types are events
of no read type; types are distinct after the kernel's K002 and the gate's look-alike check). So each read type's count
and the events count of a file are any naturals with events >= the types' sum, and the model's set of answers is exactly
the reachable one. Certificates (Model.rs_recs2): per kind as many recordings as the solution says; each read type's sum
split over the `ok` recordings, events' `ok` part likewise, the rows beyond the read types' being filler rows of a type
no read type looks like (from z, y, x, w, v, then a, b, ..., aa, ...: decide.fills, unit H04, never running out; the first not a look-alike of any), on the first `ok` recording; `nocol`
files hold events rows only. Two trial types that look alike (same skeleton, UTS #39) are NotT ("look-alike trial types
of recordings"): a file can not hold both apart in every reading. Still NotT: tr beside another quantity; a mean, min or
max of two quantities. A claim the model shows holds on every input is S008 W1 (a certificate per case, cert.py), never
R013; one past the bounds (states x orders x regions) is R013.

#### 3.9c The smaller order model (item 4, before shape 8; BB's call on Patsak's behalf 29 Oct 2026 08:58, reversible)

R1's cases per task were its orders (the regions' order times, per region, its refusing kinds' order) and in each case
an aggregate's branches were its pairs (region, kind) in that order: pair j there and the pairs before it none (its
code), or none there (its value). The kernel's sort is read only through these choices. A view is a set's regions and
the kinds its aggregate reads (Model.rs_views: each sum/mean/min/max over the task, with its parts' sets: the filter
dropped or one condition dropped); Model.rs_seq gives a view's pairs in an order. Model.rs_firsts enumerates R1's
(order, a branch per view), drops those that need one pair both there and none, and of those with the same codes per
view keeps only the least by inclusion (pairs there within, pairs none within: a larger region with the same outcomes),
each with an order that realises it; the case is (order, states, choices) and Model.rs_br gives each view its one
branch. The kept cases' union is R1's branches' union (no input lost or added), so verdicts are R1's; certificates use
the kept order, under which each view's chosen pair is first among those there (the pairs before it are none). A task
no aggregate reads keeps one order. The enumeration is charged in Model.steps (one per combination, plus the kept
ones compared); cases are still at most MAX_CASES (R013 past it).

#### 3.9d Trials of two tasks over participant groups (item 4 shape 8; BB's call on Patsak's behalf 29 Oct 2026 09:09, reversible)

trials() sums over two tasks of one dataset when the sets cut its participants into two or more regions (kind pt). The
kernel sorts a task's recordings by their entities, the subject first, so a region's place in a task's order is the
label of the participant whose runs are there. Both tasks get one partition: the cells of all the dataset's sets
(Model.rsreg, rs8). Per region both tasks have recordings in (neither state "e"), a flag: at most one participant row
(both tasks' recordings there are that row's runs, at one label) or two or more (each task its own row). Two orders
whose one-row regions come in one relative order always merge into one label order (the two-or-more rows of a region
are distinct, so no other item is shared; merge_chains), so the cases are pairs of 3.9c's kept cases, one per task,
whose orders agree on the one-row regions (Model.rs_firsts keeps them per that order, pi), with atoms size <= 1 or
size >= 2 per flagged region. Also (both kinds of dataset): a region in state "e" holds no recording, so its pairs are
dropped from the orders before 3.9c's choices (fewer cases, the same union). Certificates (Model.rs_dataset): per
task and region a carrier (the region's first row; with two or more, the task's own), labels in the merged order.
Still NotT ("trials of three or more tasks, or beside another quantity, or with participant_id read, over participant
groups"): three tasks (two-or-more rows would not give each its own), two quantities (3.9a/b over two tasks), and a
filter reading participant_id (the labels are then the table's own, not the merged order). Three regions over two
tasks give 27 x 27 states and stop at MAX_CASES (R013).

#### 3.9e A sum beside a max or a min of one task's recordings (item 4 shape 7; BB's call on Patsak's behalf 29 Oct 2026 09:26, reversible)

A min or max with other recordings() sets in one statement: per task the aggregates over its sets. A task with a max
(or a min) and no sum needs nothing new (its regions' m beside N, which no value ties); a task with a sum and a max or
min (Model.rs7) ties a region's sum y, its one value m and its count N: y <= N m and y >= m + lo (N - 1) (max), y >= N m
and y <= m + (N - 1) hi (min), bilinear in N. When N is read nowhere else (no count of the task's sets, no mean, one
quantity) it is projected out per region in state p, exactly:
- max of volumes (lo = 1): some N >= 1 meets both exactly when y >= m (N = ceil(y / m)); atom y >= m.
- max of events or trials (lo = 0): m = 0 forces every value 0, so y = 0; m >= 1 allows any y >= m; a split per region
  (Model.rs_sp): m = 0 and y = 0, or m >= 1 and y >= m.
- min of events or trials (no upper end): N = 1 gives y = m, N >= 2 any y >= 2 m (N = 2: m and y - m); the split: y = m,
  or y >= 2 m.
Certificates (Model.rs_dataset): the region's values from y and m, as many recordings as they need (max: m and y - m
split as evenly as can be over ceil(y / m) - 1 recordings, each within lo .. m; min: m, or m and y - m), the solution's
N not used. Still NotT: a max and a min of one task beside other sets; a sum beside a count of one task's sets with a
max or min (N read: y <= N m stays bilinear); tr (values in an open range: the union over N has gaps); a min of
volumes beside a sum (values up to MAX_DIM: for m > MAX_DIM / 2 the union over N of N m .. m + (N - 1) MAX_DIM has
gaps); a mean beside another set (its ratio beside another value is bilinear).

### 3.10 One file read by two kinds of reader (Part B slot shapes, 28 Oct 2026)

- **`csv(f)` and `rows(tsv(f))`.** A file both readers read holds no double quote (the TSV reader refuses one, T005), so
  no quoted CSV field, so no cell with a comma, tab or semicolon (T009 outside quotes); its TSV reading has one column
  whose cells are the CSV lines, and a final empty line (dropped by the CSV reader in a table of two or more columns)
  is an empty line of a one-column TSV table (T003). So the CSV tables of the files both read are exactly the CSV
  tables whose cells and header names hold no double quote and no comma, and the TSV table has as many rows. The slot
  is a csv slot; a class is realisable when its probe row is read back by the CSV reader and accepted, with as many
  rows, by the TSV reader (Model.readable), so a literal holding a comma or a double quote has no row, and rows(tsv(f))
  is the slot's row count. **tc1** (28 Oct 2026): when the statement names one file, has no `widen`, and reads tsv(f)
  and csv(f) only as rows() and number(cell(., r, 1)), the csv slot's tables are written with one column (no extra
  column) and a class is realisable when the TSV reader also reads back its cells: on a one-column file both readers
  read the same header and cells, and on a wider one (the TSV reading's one cell holds the CSV line's commas) every
  number() of a tsv() cell refuses, so the statement's answers are its answers over one-column files (with no `widen`
  a tsv() and a csv() cell are not one symbol only in their identity, which then changes no answer). Any other read of
  tsv(f) with csv(f): NotT.
- **`nifti(f)` with `dim()` and `size(f)`.** nifti(f) reads the header only (gzip by its magic bytes, the stream whole
  with zero padding after the last member, readers.gz_whole), so the readable files are a header of any dims (3.6) held
  as NIfTI-2 (at least 544 bytes), NIfTI-1 (at least 352, every dim within int16), or gzip, followed by any bytes
  (plain) or zero bytes (gzip). The cases are dim[0] times n2 (size >= 544), n1 (352 <= size <= 543, dims <= 32767)
  and gz (19 <= size <= 543: a gzip member is 10 header and 8 trailer bytes and at least one deflate byte), size <=
  2^63 - 1; their union holds every readable file (and, below the certificate's own gzip member, sizes no readable
  file may have: a certificate needed there refuses R013, a stated bound, never a verdict). Certificates: the header
  then the periodic bytes (decide.NiiFile, as witness.Periodic, held as its rule), or the header gzipped at level 9
  and zero bytes to the size. With pixdim() or bytes(): NotT.

### 3.11 A number read from a file's bytes (item 4 shape 3, 28 Oct 2026; BB's call on Patsak's behalf 21:52, reversible)

`number(bytes(f, o, n))`: the kernel reads the n bytes at o as ASCII by readers.decimal (no stripping), V002 first when
the file is shorter than o + n. A spelling the reader refuses R007 (more than 1,000 digits, or an exponent of more than
6 digits or above 1,000) is no readable input (SPEC 4.1: within the bounds of SPEC 9), as for a cell (3.1, P1). So per
number()-read range the case holds its class: **nan** (any n bytes the reader does not read as a number: V005) or
**num** (a number of exactly n bytes, when one exists: n <= 1,010 = '-', 1,000 digits, '.', 'e', a sign and 6 exponent
digits). The numbers of n bytes are a finite union of lattices, one per layout: an unsigned spelling of m bytes is la
digits before the point (no leading zero unless la = 1), lb after it (with a point), and an exponent of lx = 0..6
digits (leading zeros allowed, value <= 1,000) after 'e' with xs = 0 or 1 sign bytes; its values are M·10^(E - lb), M
in [0, 10^(1+lb) - 1] (la = 1) or [10^(la-1+lb), 10^(la+lb) - 1], E in [0, hi] or [-hi, hi]. The numbers of n bytes are
those of the unsigned layouts of n bytes and the negatives of those of n - 1 bytes ('-'). decide.rnext, rprev give the
least number of n bytes above, the greatest below, a point, from each lattice's own least step (exact); rin(v) is
rnext(rprev(v)) = v. Checked against readers.decimal over every string of 1 to 5 bytes of '0-9.-+eE' (155,134
numbers at 5 bytes, 0 disagree; partb/S13/s3/brute.txt; tests/test_s013_shapes.py to 3 bytes).

The model: a num class's value is a variable z = ("z", "raw", f, o, n) with the case atoms rnext(n) <= z <= rprev(n)
(the least and greatest numbers of n bytes, model facts); its identity (for widen) is the range (kernel: the Bytes
sort). The search (search.py) picks a number of n bytes inside z's bounds at back-substitution (rpick); when none is
there it splits at a point v of those bounds: z <= rprev(n, v), z >= rnext(n, v), or z = v when v is one: every
number of n bytes is in one child (Model.spell_cases, the model's disjunction "spell", recomputed by Model.disjunction
in a refusal's check, so a tampered child or a missing case is X001). Each split removes the open interval between v's
neighbours, so the splits end (at most the numbers of n bytes, and MAX_CASES: R013 past it). A certificate writes each
range's spelling of its value in exactly n bytes (rspell) over the periodic bytes (decide.RawFile), or n bytes 'a'
(seed odd: 'b') for nan; a bytes() value of a num range is paired with the same input holding nan there. Two
number()-read ranges of one file that overlap and differ: NotT (S013; a split on the shared bytes' layout positions,
ITEM4.md, not built).

### 3.12 The size of a table (item 4 shape 2, 28 Oct 2026; BB's call on Patsak's behalf 22:57, reversible)

`size(f)` of a file the statement reads by tsv() or csv() (not both: 3.10): the slot is the table's, with one more
variable n = ("n", f, "size"). Readable inputs have every column the statement reads (section 2), W = the table's
width there. The least readable text of a case: a header of W one-byte names (2W - 1 bytes and its LF), and per row
its least line: each read column's class at its least spelling (a literal its bytes, in a CSV quoted when it holds
, " ; or a tab; "oth" the empty cell, or one byte when "" is a literal: a letter, else one of _#$%&*@^~, decide.FILLC, unit H04), every other column empty, W - 1 separators,
an LF; in a one-column table a row of one byte at least (an empty line is no row, T003); the last LF is optional
(reader facts: lines end all LF or all CR LF, a BOM, CR LF, a final empty line, longer cells and more columns only
add bytes). So the case atoms are n >= 2W - 1 + the sum over row types of n_t times its least line, and n <=
MAX_TEXT_FILE (a larger table refuses R003: no readable input, as R007 in 3.11). Every size between is reached: the
first header name padded (unread, any name). A certificate is exactly that table (Model.stext): one-byte names
rotated by the seed, each row at its least line, the last LF dropped at the least size or kept and the first name
padded; it is confirmed on bytes. No new split: the atoms are the model's, so every leaf's system checks them
(cert.py), and a tampered certificate or a wrong "none" is X001 (tests/test_s013_shapes.py).

First cut (the rest stays NotT, S013): no cell(), header() or number read of that table (their least spelling
depends on the value or the spelling a W1 pair needs), no widen(), only tsv/csv/raw/nifti slots, at most 26 columns
(one-byte header names a-z).

3.12a The text total (BB's call on Patsak's behalf 28 Oct 2026 23:30, reversible; replaces the first cut's cap of 4
calls). readers.text charges a file's whole text to MAX_TEXT_TOTAL on every call through _cached (the memo saves the
read, not the charge), and size() charges nothing; so a statement (each top of the model, for R3 each copy) is readable
only if the sum over its table slots of (that slot's tsv()/csv() calls) x (its size) is at most MAX_TEXT_TOTAL (R003
past it). With a table's size read, every table of the statement is in the cut (Model.sl) and the model has one atom
per top: sum of k_s x n_s over the sized tables plus k_g x (g's least size, linear in g's row counts) over the others
<= MAX_TEXT_TOTAL (Model.sk, smin); a table beside the sized one is realised at its least, so its least is exactly
what the input pays. Every call count is decided: k calls of one table allow min(MAX_TEXT_FILE, floor(MAX_TEXT_TOTAL /
k)) bytes. Confirmed on bytes with the real constants (verify-opus-exact/partb/S13/s2r/boundary.txt): k = 5 readable
at 53,687,091 bytes and R003 at one more, k = 8 at 2^25 and R003 at one more, k <= 4 at MAX_TEXT_FILE; a table read 4
times beside a 1-byte table read once: readable at 2^26 - 1, R003 at 2^26.

3.12b A one-column table with an empty literal (Model.lay). Reader facts (on bytes): an empty line of a one-column
table is refused in both readers (T003: a row with one empty cell or no row); a one-column CSV reads '""' as the
empty cell; with a second column the empty cell is the line's first, before the separator. So a readable input is
read from one column (a TSV: no row holds the empty text; a CSV: those rows are '""', 3 bytes with the LF) or from two
or more (one more header name and a separator: header 3 bytes, each row its two-column least line). The least size is
the lesser layout's, which is no single linear atom: the model states the disjunction 'layout' (lay_cases: per layout
size >= its least, in a TSV's one column also the empty text's row counts 0, as RAtoms of ("lay", s)); the search
splits on it first and cert.py recomputes it (Model.disjunction), so a tampered split is X001; the base keeps the
per-row lesser of the two as a relaxation. The certificate is written in the layout its solution is in (lay_of). A
one-column table with an empty literal beside a sized table (not its own size read) stays NotT: its least size in the
text total is the lesser of two layouts, not linear.

### 3.13 One file read by tsv() and csv(): a tsv() line (item 4 shape 1, first cut, 29 Oct 2026; BB's call on Patsak's behalf 00:31, reversible)

Reader fact (3.10, checked on every string of 1-6 bytes over `, TAB " ; LF 1`: 884 read by both, 0 exceptions,
partb/S13/s1/facts.py): a file both readers read holds no TAB, '"' or ';', so its TSV reading is one column whose cell is
the CSV line, the CSV cells joined by ','; the CSV reader refuses a line whose field count differs from the header's
(checked on bytes), so one width **Wc** holds for the whole file, at least every csv column read and otherwise free.
`where(tsv(f), eq/ne(1, b), ...)` under `rows()`/`count()` beside `csv(f)` (no `widen`, no `size(f)`) is decided:
- The tsv line is the csv slot's column 0 (Model.wconds, cix: the last place in a type). Its classes: each literal b
  that both readers read back as one line of a table of b's comma count + 1 columns (b's pieces in the columns the
  statement reads must be literal classes there: each piece is added to that column's literals), and oth. A literal
  with a quote, ';', a CR or LF, the empty line, or fewer commas than the csv columns read has no class (no row).
- Wc is a case of the model (cases(), Slot.wc; trusted, enumerated, replayed as every case): Wc = c + 1 for each
  literal class's comma count c, or "o", any other width (the certificate's: the least above the width read that is
  no c + 1). In case Wc a type is allowed when its line class is a literal b of Wc - 1 commas whose pieces are its
  csv classes on the columns read, or its line class is oth and (when every column 1..Wc is read with a literal class)
  that line is no literal (and, Wc = 1, no empty line: T003). The others have no rows (case_atoms) and are no named
  row (slot_cases). No new split kind, no lemma.
- Certificate: a bare table of Wc columns (tw_rows): a literal row holds b's pieces, another row in each unread column a
  text no literal's piece there looks like.
- 3.13a (review, 29 Oct 2026; BB's call on Patsak's behalf 01:30, reversible): a csv line that every column 1..Wc
  forces (each read with a literal class) and that looks like a tsv() literal without being one is a class of its own
  of the line (a literal class nobody names; Model.tw_line: read back as one line by both readers, else no file holds
  it and the type has no row). The where()'s look-alike scope then refuses its rows K002 exactly as for a csv column's
  look-alike literal (no new split kind, no lemma). Such a line was S013 in the first cut.
- 3.13b (case 1, 29 Oct 2026; BB's call on Patsak's behalf 02:10, reversible): number(cell(tsv(f), r, 1)) (r a row number)
  beside csv() reads of f. The line holds Wc - 1 commas, and a comma is no decimal (readers.decimal), so in every case
  Wc >= 2 number() of the line refuses V005 on every row there is (V002 past the rows): a model fact. When the
  statement reads only csv column 1 (width 1), Wc = 1 is a case of its own (added to the Wc cases beside the
  literals' and "o", whose certificate width is then 2 or more); there the line is csv column 1's cell, so number() of
  it is that cell's number (its class). The cell() part itself: in Wc = 1 csv column 1's cell; in Wc >= 2 the line,
  whose literal is its line class's literal or, every column 1..Wc read with a literal class, their literals joined
  (Model.literal), else its spelling is free (two certificates: the seed moves the unread columns' texts in tw_rows).
  No new split kind, no lemma; a tampered certificate is X001. Was S013 (the suite's canary until then).
- 3.13c (case 4, 29 Oct 2026; BB's call on Patsak's behalf 02:13, reversible): sum, mean, min, max, median or order of
  column 1 of tsv(f), or of a where() of it, beside csv() reads of f. The Wc cases are 3.13b's (Wc = 1 its own case
  when only csv column 1 is read). In Wc = 1 the line is csv column 1's cell, so the aggregate is csv column 1's over
  the same selection; in Wc >= 2 no selected line is a decimal: V005 when the selection has a row, else the aggregate
  of no rows (a sum 0; V003 for the others), as for any column. No new split kind, no lemma. Was S013.
- 3.13d (case 3, 29 Oct 2026; BB's call on Patsak's behalf 02:16, reversible): number(header(tsv(f), 1)) beside csv()
  reads of f. TSV reads the header line as one name: the csv names joined by ','. On 3.13b's Wc cases it is csv name 1
  in Wc = 1 (its header class), and in Wc >= 2 it holds a comma: V005. The header() part: in Wc >= 2 its spelling is
  free (csv name 2 is never read beside it: a csv name past column 1 read with it stays NotT, and no readable input
  answers such a statement, every Wc there being >= 2); two certificates differ in name 2 (moved on by the seed). No
  new split kind, no lemma. Was S013.
- 3.13e (case 2, 29 Oct 2026; BB's call on Patsak's behalf 02:20, reversible): a tsv() cell read as text has no csv()
  read beside it in any statement (a text is a statement's value or number()'s argument), so case 2 is number(cell(tsv(f),
  key(1, b), 1)) beside csv() reads: the key's column is the line (column 0: its literal b a line class, its named key
  and its look-alike scope on column 0, Model.tkey); the keyed cell is 3.13b's. A key holds no comma (K001), so in Wc
  >= 2 no line is b (V004); in Wc = 1 the keyed row's csv cell 1 is b. No new split kind, no lemma. Was S013.
- 3.13f (case 5, 29 Oct 2026; BB's call on Patsak's behalf 02:24, reversible): widen() beside tsv() and csv() reads of
  one file. Two widened values are one symbol exactly when their identities are one (SPEC 5.2); the kernel's identity
  of a cell is (its files, row, column) and of a selection (its files, rows): neither names the reader (kernel nid,
  sel_id, Cell meta). Model.ident gives a cell (slot, row, column) and a selection its row set, so a tsv() and a csv()
  read of the same cell or rows are one symbol in both, as their values are one wherever both answer (Wc = 1; in Wc >=
  2 the tsv() line refuses). The first cut's NotT is removed; no new code. Was S013.
- 3.13g (29 Oct 2026; BB's call on Patsak's behalf 02:53, reversible): a sample or population variance of tsv(f)'s column
  1 (or of a where() of it) beside csv() reads of f. In Wc = 1 it is csv column 1's over the same rows; in Wc >= 2 no
  selected line is a decimal (3.13c's good types: V005 with a row, V003 below 1 + ddof rows). The variance shape (3.7)
  meets two consequences: (a) a certificate of such a statement (Decide.d_out) is written at Wc = 1 (bare, one column),
  the only case where the tsv() variance answers; (b) d_hit and Decide.vranges compare two variances' selections
  without the types either candidate's case gives no row (an input both cases admit holds none of them), so a where()
  of the line and the same where() of csv column 1 are one selection in Wc = 1 (their line class and column-1 class
  coincide there). (b) holds for every slot, not only these. No new split kind, no lemma. Was S013. W2 of a condition
  of one variance's selection beside the other variance is 3.7a's: a found none there is S013, never S008 W2.
- 3.13h (case 6, 29 Oct 2026; BB's call on Patsak's behalf 03:50, reversible): size(f) beside rows() and
  count(where(., eq/ne)) of tsv(f) and csv(f) (3.10's and 3.13's slots; 3.12's scope: no cell, header, number or
  aggregate of the table). In a width case W0 (Wc, or for 'o' every width no tsv() literal has) the least table is
  3.12's at width W0: W0 one-byte csv names (the tsv header their joined text), each row's least line (a literal
  line's bytes; else each read column's least spelling and, in a column not read, the empty text or the first letter
  no width-W0 literal line's piece there looks like, so the line is no literal line), the last LF optional, the first
  name padded above the least. The 'o' case's least is at its least width (the least >= the columns read that no
  literal has), not at the width its other certificates use. In one column a row with an empty csv cell has no line
  (CSV writes '""', which TSV refuses, T005), so when the 'o' case's least width is 1 and such a row type exists it
  is split as 3.12b's layouts: width 1 with no such row, or the case's next width (Model.lay_cases, the
  disjunction 'layout', checked); a slot beside a size() but not sized is then NotT, as 3.12b's. Each tsv() and csv()
  call charges the text (3.12a: readers._cached keys by reader). No new split kind, no lemma. Was S013.
- Still NotT (S013, listed in KNOWN-OPEN): tsv() read other than so (a header beside a csv name past column 1, tsv
  column >= 2 beside an aggregate), size() of the file beside a cell, header, number or aggregate of it (3.12's
  scope: a numerically read cell's spelling length is a variable), a numerically read csv column whose piece the
  number reader refuses (3.1).

## 4. The integer step

A system is a list of atoms over variables x ∈ ℕ^d: `f ≥ 0` and `m | f` (m ≥ 1), f linear with
integer coefficients. `decide` answers whether a common solution exists. It is defined by the steps
below, applied to the system until it has no atoms or is refused; [decide_correct] proves that it
answers true exactly when a solution exists, whatever variable each step chooses.

1. **Normalise every atom** [holds_tighten]: for `f ≥ 0`, divide the coefficients by their gcd g when
   g ≥ 2 and replace the constant c by ⌊c/g⌋; for `m | f`, take every coefficient and the constant mod m,
   then divide m, them and the constant by their common gcd g; `1 | f` becomes `0 ≥ 0`; `0 | f` becomes
   `f ≥ 0` and `−f ≥ 0`. Drop repeated atoms, keeping first occurrences.
2. **Ground atoms** (no variable): if one is false the answer is false; otherwise drop them.
3. **No atoms left**: true.
4. **Hopeless**: an atom `f ≥ 0` whose coefficients are all ≤ 0 and whose constant is < 0: false.
5. **Choose a variable y.** The choice is free for correctness. The checker prefers a variable that a
   one-signed rule (6, 7) applies to; among the preferred (or, if none, among all) it takes the one with
   the fewest branches δ·(1 + Σ positive coefficients of y), or B + 1 when y has an explicit range 0..B
   (rule 7a) and that is fewer, ties by name.
6. **pos** (no `m | f` contains y; every coefficient of y is ≥ 0) [pos_rule]: drop the atoms containing
   y. A solution of the rest extends with y = Σ max(0, −rest of each dropped atom).
7. **neg** (no `m | f` contains y; every coefficient of y is ≤ 0) [neg_rule]: put y = 0.
7a. **enum** (call 2, 27 Oct 2026) [enum_rule]: y's explicit range is 0..B, B the least ⌊c/a⌋ over the atoms
   −a·y + f ≥ 0 with a > 0 whose other coefficients are all ≤ 0 (c the constant; every solution has
   a·y ≤ c). When B + 1 ≤ the branches of rule 8, the answer is true exactly when one of the systems
   y = 0, 1, …, B has a solution, tried in this order. Each value is a call, counted like any other.
8. **lower** [lower_rule]: let δ be the lcm of the moduli of the `m | f` atoms containing y (1 if
   none). The answer is true exactly when one of these systems has a solution, tried in this order:
   - y = j, for j = 0, 1, …, δ − 1;
   - for each atom a·y + e ≥ 0 with a > 0, in order, and k = 0, 1, …, a·δ − 1: with t = k − e (so
     a·y = t), the atoms `a | t`, `t ≥ 0`, and every atom b·y + f of the system (this one included)
     replaced by b·t + a·f, with modulus m·a for `m | …`.
   Reason: the least solution's y is either below δ, or y − δ breaks some atom, which can only be a
   lower one, and then a·y + e lies in [0, a·δ).

The witness of a true answer is built as the steps return (rules 6, 7, 8 give y from the rest). It is
not the smallest witness.

### 4.1 Named cell values first (Fourier–Motzkin, exact)
[elim_step, elim_correct, elim_nat, atom_scale, atom_int] A question's system may hold atoms `F > 0` and `F ≥ 0` with rational coefficients over the counts n (naturals)
and named cell values z (decimals, 3.3). The z are eliminated one at a time, in the order of their names: the
atoms without z are kept, and each pair of an atom with a positive coefficient a of z and one with a negative
coefficient −b gives b·(first) + a·(second), strict when either is. What is left is over n alone; each atom is
multiplied by the lcm of its denominators, and `F > 0` becomes `F − 1 ≥ 0` (F is then an integer). Section 4
decides that. Over the rationals each elimination step keeps exactly the solutions' projections (z between
the largest lower and the smallest upper bound). **Decimals.** Every system a question poses has at most one
non-strict atom in which a z occurs (a comparison's "holds" or "fails", or none), and each z also has strict
bounds or none (its interval); so, with the n fixed, the z the system allows form a set that is open apart
from that one atom, and it holds a decimal whenever it holds a rational. The values are chosen last eliminated
first: the bounds of each z, given the values already chosen, leave an interval that is not a single point
(only one bound can be non-strict), and z is the integer in it nearest 0 if one is strictly inside, else the
shortest decimal step above its lower end. A point, if one were ever left, is taken as it is; a point with no
decimal would fail the certificate (6) and give X001, not a verdict. Before the elimination, each equality F = 0 over
the counts (the pieces of 3.5, a median's n = 2m' + 1) with integer coefficients and a variable of coefficient ±1 is
used to replace that variable, which is then kept ≥ 0 (exact over the naturals). After it, an atom −(x₁ + …) ≥ 0 sets
its variables to 0, an atom with no negative coefficient and constant ≥ 0 is dropped, and two atoms G + k ≥ 0 and
−G + k' ≥ 0 with k + k' < 0 mean "no solution" (each step keeps the solutions).

### 4.2 The rational relaxation first (phase 4)
Before section 4's steps, the system is solved over the non-negative rationals by phase one of the simplex method, in
exact arithmetic with Bland's rule. If it reports no rational point, the Farkas certificate u ≥ 0 with Σ u·G ≤ 0 in
every variable and Σ u·k < 0 is checked; when it checks, there is no natural solution (any solution would make
Σ u·(G x + k) both ≥ 0 and < 0) and the answer is "no". If it reports a vertex with integer coordinates that satisfies
every atom, that is the solution. Otherwise section 4 decides, as before. The answer is the same as section 4's (both
are "is there a solution"); only the witness and the steps counted differ.

## 5. The questions

### 5.1 W1
A value's **answering branches** are its branches (3.3) over all the cases of the rows it names (3.4) whose
result is not a refusal (a value refusal is no answer).
- **A comparison**: it has two answers exactly when some answering branch "holds" and some "fails" has a
  solution. None that holds: S011 ("it holds"); none that fails: S008.
- **Any other value**: take the first answering branch with a solution, x0 there, and its answer a0 there (a widened
  value's answer is its two ends: another width w is another answer).
  None: the value never answers (S008). For a cell or header of a non-literal class (3.2) the answer is its
  own spelling: a second spelling of the same input is a second answer (H2). Otherwise it has two answers
  exactly when some answering branch has a solution with an answer other than a0: for a form F (a count, a
  number; a selection's count form, since the empty table answers with no row), `F − a0 > 0` or `a0 − F > 0`;
  for a share with a0 = p/q, `q·S − p·B > 0` or `< 0`; for a cell, a branch whose cell is not of a0's literal
  class. None: S011 for a selection ("the selection has a row"), S008 otherwise.

### 5.2 W2
At the judging level, with v1 = the value with p and v2 = without: in each case of the rows either names, for
each branch (A1, r1) of v1 and (A2, r2) of v2, the system A1 ∧ A2 ∧ "r1 ≠ r2" is posed, where "r1 ≠ r2" is:
two refusals: true when the codes differ; a refusal and an answer: true; two comparisons: true when one holds
and the other fails; two forms (counts, numbers, selections by their count forms): `F1 − F2 > 0` or `< 0`;
two cells: false when they are one cell or the same literal, else true (named rows have different spellings);
two widened values: true when their widths differ, else their centres as forms or ratios.
They differ exactly when one of these systems has a solution, or, for two shares (S1, B1), (S2, B2), when the
system A1 ∧ A2 (which holds B1 ≥ 1 and B2 ≥ 1) has a solution x0 and the polynomial S1·B2 − S2·B1 is not the
zero polynomial in the variables the system does not force to 0 (5.4).

W2 for a file slot (v4 SPEC 4.3, fix pass R3; carried here at the merge of v4-fixes, 27 Oct 2026): for a statement
reading two or more file slots, each slot n bears when, with the other slots held, two inputs of n give different
answers. Decided as above with v1 = the statement and v2 = its copy reading a fresh slot n' (same reader) in n's
place, one model over both; a refusal on either side is no answer here (SPEC 4.2), so only answer pairs pose a system.
No system with a solution: S008 naming the file. A solution is confirmed on its certificate by the real code (6).

### 5.3 S011 and S008
Unchanged from SPEC §4.4 item 11, with "found" replaced by "decided". The S008 message for a nested
share that restates its base (D4) names the one spelling, as SPEC §4.3 says.

### 5.4 Why the polynomial test is exact (on paper; not in Lean yet)
B1 and B2 have coefficients 0 or 1 (they are counts), so the set {x ∈ ℕ^d : B1 ≥ 1, B2 ≥ 1}, when not
empty, contains x0 + ℕ^d for any of its points x0. A polynomial that is zero on x0 + ℕ^d is the zero
polynomial (induction on d: a nonzero polynomial in one variable has finitely many roots). So S1/B1 ≠
S2/B2 somewhere on that set exactly when S1·B2 − S2·B1 is not the zero polynomial. The same argument
gives 5.1's identity tests (a linear form is a polynomial). Caps (a unique key with a fixed literal, at
most one row) break the argument; part T's `tsv`/`csv` slots have none, and the parts that have them (B)
handle them in their phase by solving with the cap as an atom `1 − n_t ≥ 0`. The certificate for (a): with
x0 a solution of A1 ∧ A2, the first of x0, then x0 + e_v and x0 + 2e_v for each variable v,
then x0 + e_v + e_w for each pair, at which S1·B2 ≠ S2·B1. A nonzero polynomial of degree at most 2 that is
zero at x0 is nonzero at one of them (its linear and square terms show at x0 + e_v and x0 + 2e_v, its cross
terms at x0 + e_v + e_w), and all of them keep B1, B2 ≥ 1. The variables are those A1 ∧ A2 does not force to 0
(an atom −Σ n ≥ 0 from a where() that does not refuse V005 forces its types to 0); on the others the set is
still x0 + ℕ^d. Shares read no named rows (their arguments are selections), so a share's system has no case
atoms. **Means** (phase 4): S may hold sums y (3.5). With the counts fixed at a candidate point, S1·B2 − S2·B1 is
affine in the sums, which range over open boxes; it is nonzero somewhere there exactly when it is not identically
zero. So at each candidate point of the counts (the same list), the system with the counts fixed and
`S1·B2 − S2·B1 > 0` (then `< 0`) is solved; the first solution is the witness, and none at every candidate is "no".

## 6. Certificates
When a system has a solution, the witness is turned into bytes: per slot, the header of 3.2 (with the case's
header cells), the named rows at their positions, and the extra rows and each type's n_t unnamed rows (in the
order of the types) in the other places, in that order; each cell spelled as 3.2 says, a named cell value z as
its decimal. It is evaluated by the real readers and evaluator (`witness.evaluate`): W1
evaluates the value itself, W2 the two values at the judging level. W1's inputs: for a comparison, the first
"holds" and the first "fails" solution; for a cell of a non-literal class, x0 with spellings 0 and 1 (every
named row's spelling moved on by the number of named rows plus one); otherwise x0 and the first solution with
another answer. W2's: the first system with a solution, in the order of the cases and branches, then the
shares' points of 5.4. Unnamed rows (3.5): in a summed column, n_t − 1 rows hold one decimal a near y_t/n_t and
the last y_t − (n_t − 1)·a, all inside the class's interval; in an ordered column, each row holds w_i in its piece
"at w_i", else a decimal strictly inside its piece. Files (3.6): a raw file of the solved size with bytes moved on
by the seed; a NIfTI-1 header (NIfTI-2 when a dim passes 32767) with the solved dims; a JSON text from the case
(named members that are there, arrays with 0 in unnamed items, numbers from the solution, strings `s<seed>.<node>`,
a filler member `<f>: seed`, f the first of "", a-z, f0, f1, ... no named member of the object looks like, or item for the second answer of a tree). The statement's verdict is the decided one only if the real code confirms it; if it does
not, the result is no verdict (X001), a checker fault. **R013 (D3, phase 3).** The bound is MAX_ROWS = 100,000 rows in one slot's table of one input [prov].
Each question's systems (its options, in the order above) are first solved as they are; a solution within the
bound is used. Otherwise the same system with the atoms `MAX_ROWS − Σ_{t of s} n_t ≥ 0` for every slot s is
solved; section 4 decides it exactly, so it has a solution exactly when an input within the bound exists
(named rows count as rows). The
first option with an input within the bound gives the certificate. If no option has one but some option has a
solution, the statement refuses R013 ("needs a readable input with more than 100000 rows in one table"): the
smallest witness exceeds the bound. If no option has a solution, the answer is "no". **Order of the work (item (g), 27 Oct
2026).** The options are solved in rounds under a step cap (4,096 counted steps each, then x4 per round, never more
than the steps left): an option that answers within the cap answers; one stopped by the cap waits for the next round.
After the first round, each waiting option is first solved with 0, then 1, then 2 rows in all (one system per
total, its counts' sum fixed: Part B item (e2), 27 Oct 2026; before, one system per vector of counts, each under 65,536
steps, which cost a question of 494 options 25 million steps), each under the first round's cap; a solution of that
system is one of the option's, since it only adds atoms. So a costly option no longer spends the step bound before a
cheap one is tried; "no" still needs every option solved in full, and R013 for steps or cases comes only when no option
answers. The cap only schedules (item (e2)): each round solves an option again from the start, so an option's rounds
are counted once, its largest (each round's steps are those of the earlier rounds and more); the steps of 8 are the
work of the options' largest rounds, the passes of at most two rows and the other systems, and an elimination or a
relaxation that would pass a round's cap stops that round (the option waits), not the statement. **A round's cap counts
its solves only (BB's call on Patsak's behalf, 28 Oct 2026 17:10, reversible).** A verdict must not depend on how side
work is charged: side work (a check a solve makes beside its own system: 3.5a's lp tests of a cut's count condition)
is charged to the step bound only (decide.side). In a round the budget is [steps, headroom], steps starting at the bound
less the cap and headroom how far that start lies above the steps really spent; side work takes the headroom first, so
it never stops a round, and past the headroom it is steps, so the steps never fall below the steps really spent and
every check against the bound still bounds all work (the worst case stays R013). An option's rounds count its solves
and its side work. Memory was already its own account (8). Twice before a charge inside the first round's cap moved an
option to a later round and changed what was decided: memory charged as steps (Mem6, a claim that forms refused R013
at MAX_CASES) and the lp tests charged as steps (partN pn450 formed in 352 s; with them in the cap, no verdict within
1,300 s): test_side_work_cannot_change_finds_path charges each lp test 10^6 more side steps and find() makes the same
solves to the same certificate (charged as steps, 376 solves become more). **Fewest rows first (Part B
#4, 27 Oct 2026).** A solution with more than 64 rows in one slot is replaced by one of the same system with at most
2, else at most 64, rows per slot when one exists (more atoms, so it is still a solution): the solver's vertex can
sit at a large count (a fuzz statement's at 100,000 rows of 1000-digit values), whose certificate cost more than the
step bound to check (R013) although two rows answer. This depends only on the
system, which depends only on the statement as judged and the slots' hashes (3.2), not on names or the
order of the slots in the text.

### 6.1 Certificates of no point (BB's call on Patsak's behalf, 28 Oct 2026 18:05, reversible)
(Unit B07, Argon review 2 07; BB's call on Patsak's behalf 1 Nov 2026, reversible.) What "untrusted" covers:
search.py and build.py run in the checker's own Python process, so the guarantee that a fault there gives only X001
or R013 is for code that computes and returns (wrong answers, points, trees, logs or inputs). It is not a sandbox:
code there that rewrote cert.py's own state (cert.CHECKED, its functions) could pass anything. The model's state a
certificate is checked against is kept from the search: cert.py calls the model's methods by its class (cert.mcall:
one set on the instance is never read), Model.find compares the model's own attributes before and after the search
(other than decide.SEARCH_SETS, the search's own; an rb or a method set there is X001), and tests/test_source.py
checks that search.py and build.py write no trusted module's names (only decide's MEM and CERTS counters), no model
attribute outside their own, and call no setattr, delattr, exec or eval.
(Unit C01, review 3 01; B02's rule for build.py, now for search.py.) The checker reads a value the search hands it
(a split's rule, children and atoms, a leaf's system and atoms, check()'s system and log, an obligation, a point
find() returns, the trees of a replay) only as one copy it makes itself from exact types (cert.exact: None, bool,
int, str, bytes, Fraction, tuple, list, dict, and the trusted atom classes rebuilt with their attributes), read through the
built-ins' own methods; a subclass of any of them, whose own keys(), items() or __getitem__ could show the checker one
thing and a fingerprint or the model another, is X001. One copy per object (a tree's memo) keeps the identities a tree
checks. A node's case is the search's name for it only: the model's methods get the case the model's own disjunction
made (cert.Tree.mcase), never the search's object.
(Unit D01, review 4 01.) A copy keeps what the search wrote, so the checker and the model read nothing from it but forms
and identities: no field the search could have derived wrong. A float's range for a binade split is the range the
parent's atoms state by their forms (decide.frange_in: z - sg·2^ea·J >= 0 and the range's three other atoms, EMIN <= ea
<= eb <= EMAX), never an atom's .r or .z; a mean's rows range named by the parent's atoms (.r) is used only when the
parent's atoms state it (N - a >= 0, b - N >= 0, sg·mu >= 0, by form), each child's is checked as before, and a range's
ends are integers; a PAtom's facts are used only for the option's own or one equal to the model's (H08). A dict whose
copy has fewer keys than it (two keys one value once copied) is X001, and a copy that fails leaves nothing behind.
A refusal's "no" is checked, not taken. The decision's search builds no certificate (its path and verdicts are
those of the search alone); each find() that answers "none" is kept for the question (its options, held in their own
memory count; when the decision's held memory would pass the bound with them they are dropped, the decision never
meets them, and a refusal of that question is R013), and so are the equal shares of 5.4. Only when the question's
verdict is a refusal (S011, S008 W1, W2, a file that does not bear) are its kept finds (their memory counted
once per object, decide.kept_bytes) replayed with certificates
(BB's guidance on C4, 28 Oct 2026): every unbounded system Model.solve finds without a point (one_solve2's leaves)
carries a proof log (`decide.Log`, its steps held in memory as they are written), checked by `cert.py` with exact
Fractions and nothing from decide.py. The replay's search steps and the checking steps are each counted against the
stated bound, after the decision and outside its budget; past either, or past memory, the refusal is R013 saying its
certificate check exceeded the bound (a refusal not checked is not exact). A replay that finds an input where the
decision found none is X001. A form never waits on a check. Lines: a premise of the system; v >= 0 for a natural v (every variable not of kind "z");
a nonnegative combination of lines; a line over naturals scaled to integers with a strict atom moved to >= 1 (the
integer rounding of tidy); the end is a line with no variable and a negative constant (or 0 and strict), or lines
handed to the integer step (intstep, Exact.decide_correct) which finds no natural point. presolve's replacements,
fm's eliminations, the integer rounding, tidy's dropped variables and opposite pairs, lp's Farkas certificate
(with x >= 0) and the integer step's "none" each write their lines; only the lines the end rests on are checked
(Log.needed). A log that does not check is X001. Checking's lines are held in memory (twice the system's held
atoms and the log). Each option of a find() that answers "none"
has a tree (cert.Tree) of solve1's splits: a sign split is checked (its children add F >= 0 and -F >= 0); a mean's
rows split (prange, 3.5) is checked (cert.prange_split): the PAtom's facts are trusted (S = mu·N; lo <= mu <= hi, its
classes' ends) only when it is one of the option's atoms or one of the trusted model's pieces by content
(decide.Model.piece_facts; unit H08, Opus 5.5 max2 review 08: search.piece_atoms builds them, and a wrong one is X001), each child's range atoms (N - a >= 0, b - N >= 0, sg·mu >= 0) must be there, every other atom it adds
must be the product of two of those facts (or mu - lo, hi - mu, 1) with mu·N read as S and no mu·mu or N·N term (at
N = a: S - a·mu = 0), and the children's ranges must cover the parent's (the integers of [a, b], N integer-valued over
naturals; signs the parent's, 0 only on one point; the first split over [a0, ∞) with a0 at most the option's PAtom's own
a0 (unit B06, Argon review 2 06: a greater a0 left [P.a0, a0) uncovered), or a0 <= 0 for a model piece; by mu's sign, or one sign the parent's atom or
lo >= 0, hi <= 0 give, or shown: a piece's sign taken from its end's (L1) holds when the parent with sg·mu < 0 has no
point, a system Model.prove solves and cert.check shows, kept by the tree (Tree.proved, cert.implied)). Every other
split is a model disjunction (L1, 28 Oct 2026): the model states, from its own data, cases that hold together on
every input of the parent (Model.disjunction: nest, a mean against its classes' ends and its pieces' ends (pcuts);
cap, the shared types' mean, a fresh variable; presence; refine; a readable number's band; a sum's finest step; a
float's binades; a thin piece's gap cases; a half cut, whose count condition (3.5a) is an obligation: its system of
the case's count atoms and the condition >= 0 must be shown to have no point); the checker accepts the split only if
there is one child per case, in order, each child's case is the case's (Model.same_case) and each of its atoms is the
parent's own or one of the case's (cert.cover; dropping atoms is sound: more points). The search chooses where to
split; the model, not the search, says what the cases are. (A01, A04; Argon reviews 01 and 04) A disjunction is stated
only on a variable of its kind, by the model's kind tag (decide.zkind): a band on a number the reader reads, a step on
a sum (a region's sum of RepetitionTimes is a sum, not one read value), binades on a float's range of two binades or
more, spellings on one of the model's number()-read ranges that holds a number in the case (so its cases are never
none); any other is cert.Bad, X001. Two floats in one window (fwin, 3.6; L5): a pair pinned
(u = a, v = w, one child) is checked by cert.pin_split (every atom of the parent's system and facts with u or v has no
other variable and holds at (a, w); a and w are floats; (B01; Argon review 2 01) u and v are pixdims, each in the
parent's atoms, the only variables whose every value is a float: any input moved to (a, w) is one of the child's); no pair (no
child) is the model's own enumeration of the window's floats (fwin, fpair), recomputed by certify. (G02) A system is checked by its contents: a leaf closes its node only if its system, as it is when the leaf is given, is one check() showed to have no point, and the node's atoms and case and the question's options are as they were when their split was checked or the question asked (fingerprints of their contents); an edit since is X001, and (A02; Argon review 02) a split is checked only while its option's atoms are as given (an atom added for one split and taken away before the leaves is X001). A leaf closes its node only if its checked system is the model's atoms of the node's case
(Model.base), then the option's atoms and the node's, in order, then the model's facts (Model.tail: same_means);
find's "none" needs every option's tree done (cert.options_closed, called by Decide.certify on the replayed trees,
each built with the find's own model: slot_bears' copy is replayed on the copy's model), else X001. empty_box's
"none" writes each bound as a line (the atom plus the others' bound lines, divided by its coefficient: cert.py's rule
"d", the gcd division with the constant rounded down); a float system's memo closes a node only on the system
cert.check showed (cert.CHECKED, kept for the statement). The shares of 5.4 without sums: the checker recomputes the
points and q = S1 B2 - S2 B1 at each (cert.shares_zero), else X001; with sums (L4), the refusal keeps the case and
branch, and certify recomputes 5.4's points, each point's count atoms and the systems with P = B2·S1 - B1·S2 > 0 and
< 0 (Decide.sums_shown), each of which must be among the statement's checked one-option finds, else X001.

Every refusal keeps what it rests on (Decide.rest, L2): its finds, its shares, or a record: "var" (3.7, w1_var: the
comparison f, cutoff c, width w, whether an SD, and sup; the checker recomputes the verdict from the comparison's
meaning over values [0, M], M = sup or its root, both reached: cert.var_verdict; a variance is >= 0 by the kernel's
own formula, a sum of squares over n - ddof >= 1, so a verdict that needs no sup rests on that alone), "model" (the
model alone: no answering case, one readable value, a width given back, a sum of variances with no row type every
variance reads), "vrange" (L6: the variance shape's values lie in the model's ranges, Decide.vranges: a variance in
[0, sup]; a difference in [-sup2, sup1], 0 for two equal variances, [0, Vp's sup] or its negation for one selection's
sample minus population variance; a sum of signed variances in n_range; the checker shows each range misses each piece:
cert.vrange_none) or "vdeep" (L6, 5a: the classes' readable values, all of them, every multiset up to nmax rows tried and
every piece above the largest variance of more rows: cert.vdeep_none). d_hit's None rests on vranges alone (every pair
its ranges do not rule out goes to the finite search, whose None is R013); the uncoupled shifts only find inputs, which
form on bytes. A refusal that keeps nothing, or a record or split the checker does not know ("lemma"), is X001: no named
lemma is left (BB's call on Patsak's behalf, 28 Oct 2026 20:38, reversible). Not certified: the model and question
logic themselves (Model's cases, branches and atoms; Decide's questions), which are the semantics of part T restated
over counts (PLAN.md 0). Since unit I3 decide.py is split: the search (presolve, tidy, empty_box, lp, fm, back, the
integer step's wrapper, Model's solve, solve1, half_cut, count_ints, implied, one_solve*, finish, find) is search.py,
outside the trusted base, reached only through Model.find (whose every "none" is kept and checked before a refusal)
and Model.prove (whose "none" must be a system cert.py checked); its solutions are confirmed on bytes. decide.py (the
model and questions) and cert.py are in the base. The certificate inputs' bytes come from build.py (untrusted, unit
BLD), each copied from exact types as the store its hashes name (unit B02, Argon review 2 02: Decide.input and
decide.plain; a dict, tuple, bytes or str subclass, whose own methods could show two stores, is X001, and a lazily held
file is rebuilt from its arguments by its trusted class, never read as given); a question that compares two values on one point (W2: the statement
with and without a part, or with a file slot varied) builds that point's input once and evaluates both on it (unit
A07, Argon review 07: two calls could give two inputs, and two inputs make any part look as if it bears).

## 7. Reader facts (assumed, not proved; [real_abstraction] takes H1 and H2 as hypotheses)
- **H1**: a table is accepted exactly when its header is accepted and each row is accepted on its own,
  apart from the stated cross-row constraints (unique keys, one trailing empty line, consistent line ends).
- **H2**: every realisable class has unboundedly many spellings, so fresh ids and "other" cells exist; the
  spellings of 3.2 are read back as their class (an "other" spelling is no decimal; a decimal spelling is its
  value).
- Probed (plan §7.6) by `tools/exact_h1.py` for TSV and CSV: every cell of length 0–2 over TAB, LF, CR, `"`,
  `,`, `;`, space, NUL, BOM, U+2028, U+0085 and a few letters and digits, at widths 1–3, in one, two and three
  rows, two columns, and header cells; and the first spellings of 3.2. 0 counterexamples (phase 3 checkpoint).
- **H3**: the domains of the BIDS and file atoms, and their cross-atom constraints, are exactly what the
  readers and `bids101.py` accept (parts H and B; not used by part T).

## 8. Cost
Charged to the statement's steps (phase 3): each probe (its bytes / 64 + 1), each row type, each type a
selection or V005 set is computed over, each case, each branch, each relaxation (the square of its atoms), each system solved (its calls plus its atoms,
and the atoms 4.1 makes), each point tried in 5.4, and each certificate's evaluation (the counted
steps of the real readers and evaluator). The bound is SPEC §4.5's MAX_WITNESS_STEPS (5·10⁷) [prov]: the
integer step is given what is left of it as its call limit, and past it the statement refuses R013 with what
needed more. The measured systems need at most 1,507 calls (plans/exact-decision-procedure.md §15). The elimination of 4.1 and the relaxation are charged before their
work is done (Part B item (e2), 27 Oct 2026): an elimination step whose atoms would take the charge past what is left,
or a relaxation whose square would, refuses R013 then, not after the machine has built it (a statement whose 236
atoms in 51 rational values eliminated to 83,093 atoms had taken 13 GB in the relaxation before it was charged).

**Memory (BB's call on Patsak's behalf, 28 Oct 2026 09:05, reversible).** Running out of memory is never an outcome of
the exact path. The structures that grow with a system are charged before they are built, in accounted bytes at
**STEP_BYTES = ⌊(2³¹ − MAX_ACCOUNTED) / MAX_WITNESS_STEPS⌋ = 21 bytes a step** (the floor of SPEC §9.4 less the program's
own accounted bytes, over the stated bound), against the same bound MAX_WITNESS_STEPS (MEM_STEPS, fixed at 5·10⁷ when decide.py loads), in an account of the memory held
now (decide.hold, MEM): a structure's steps are held from before it is built until it is freed, then given back. Past
the bound the statement refuses R013 ("more than 50,000,000 steps of memory held at 21 bytes a step"), never
MemoryError or X001, so the exact path's working memory stays under 5·10⁷ × 21 bytes ≈ 1.05 GB. The account is apart
from the steps done (the charges above): bytes are not time, and find()'s per-round step caps (Part B item (g)) meter only
steps (charged into the steps, a 20-atom tableau's bytes outgrew the first round's cap of 4,096 and changed which option
was solved first: a claim that forms refused R013 at MAX_CASES). Held, with B the largest bit length of a number's
numerator or denominator, a number at 3·64 + 2·(⌊B/7⌋ + 1) bytes (a Fraction and two ints; CPython keeps 4 bytes per 30
bits) and a form of n entries at 256 + n·(64 + that) bytes (CPython 3.13: 224 bytes for a one-entry dict, 632 for 12):
- 4.1's elimination: each step's |P|·|N| new atoms, their numbers at 4B + 1 bits (−q_z·p + p_z·q of B-bit numbers), before
  they are made; held with the system;
- the integer atoms 4.1 leaves (each form scaled by its denominators' lcm: B plus the lcm's bits), twice (tidy's key of
  each), before each is built; held with the system;
- 4.2's tableau ((m + 2)·(n + 2m + 1) cells and their rows) before it is built, and before each pivot again at 4B + 1 bits
  (the pivot row r/p has 2B bits; a − f·b then 4B + 1), held up to its largest until lp returns.
Held too since Part B item 2 (BB's call on Patsak's behalf, 28 Oct 2026 10:40, reversible: a count bound is not a byte
bound, so a structure bounded only by a count is held by its bytes, not assumed small), each before it is kept, at
accounted sizes (size_of: a dict 256 bytes and 64 an entry, a list or tuple 64 and 8 an entry, a text 49 plus its
length, a number as above; each object counted as its own, shared or not, so the account is above CPython's):
- a question's cases (take: at most MAX_CASES + 1 per slot, recording-set dataset and aggregate list; the piece choices
  cases() makes, each case's dict and its Extra) and their branches (Decide.branches), held in the question's Decide call
  and given back when it returns (scoped: w1, var_cands, slot_bears, w2_input);
- solve's stack of waiting cases: each entry its list, its new atoms' forms (those not shared with the entry popped
  last) and a new case's dict, held at its peak until solve returns;
- the integer step's frames (MSearch, above intstep.py, which is unchanged): each frame's atoms while it runs (its depth
  and pin's growth of coefficients are bounded by nothing stated);
- a certificate's rows while bytes_of builds them (type_rows: the rows' lists, then each column's values and texts).
Not held: a statement's nodes (R006 bounds them) and the real readers' tables (charged by them, SPEC §9.4). Measured: bfe1's claim (2,103 integer atoms, an 8.86-million-cell tableau that took 3 GB uncharged) refused R013 on
the memory bound in 5.5 s (20.6 s with a peak of 3.1 MB under tracemalloc; verify-opus-exact/partb/Mem/memspy-Mem7.txt);
since the half cuts (3.5a) it refuses S008 W1 in about 4 s, held peak 2.1 MB (partb/X3/memfig on /tmp/srcY1).
