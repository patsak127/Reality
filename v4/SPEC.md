# Reality v4: specification

Status: Phase B text, 25 Oct 2026 (Europe/Berlin). Normative for v4. It is written **against
v3/SPEC.md §9** (the base): every rule of v3 SPEC §9.1–§9.13 holds in v4 unless a section below
replaces it, and every number here that differs from v3 replaces v3's. A self-contained text (v3 §9
merged with this file) was planned for Phase G and is not written (KNOWN-OPEN 10); until it is, this
file read over v3 §9 is the specification, and an independent checker cannot be written from one text.
Design reasons are in DESIGN.md; this file states rules only.

Provisional numbers (to be fixed by measurement in Phase C and reported before freezing) are
marked **[prov]**. They were not measured or fixed; they are still the author's guesses (KNOWN-OPEN 12).

## 1. Scope of v4 over v3

- Idleness and contradiction are decided by witnesses (§4), not by sort spelling.
- Value identity (§5) keys the one-tolerance rule; `widen` is affine (§5.2).
- The plain and BIDS TSV readers change (§6): CR LF line ends; one trailing empty line in
  multi-column plain TSVs; blank headers refuse; BIDS empty cells refuse.
- New computations (§7): `variance`, `pvariance`, `sd`, `psd`, `order`, `median`, `share(…, of =)`,
  `recordings`, aggregates over recordings. Number columns are read only over selected rows.
- The BIDS reader cites a register sentence for every decision; choice points refuse B30 (§8).
- Costs are upper bounds on work; output and memory are bounded; paths are bytes (§9).
- CLI and store corrections (§10).

## 2. Readings and calls (replaces v3 §2 where they differ)

1. Call 1 (a dataset name promises the whole dataset) is unchanged, B11 both directions. The
   register records it as `reality-call`, not as a 1.0.1 sentence.
2. Idleness (principle item 1) is **structural**: W1/W2 of §4 over every readable input. The v3
   data-dependent `key()` S008 is removed.
3. Call 3 (refuse where 1.0.1 is silent) is the algorithm of §8.3, not a list. Onsets with
   `onset ≥ dim[4] × RepetitionTime` (in seconds, exact) are such a silence and refuse B30.
4. Call 4 (one tolerance per value) groups by value identity (§5.1); an un-widened use of a value is
   tolerance 0.
5. 1.0.1 "should" binds when it states a property of a 1.0.1-defined file that the bytes can show.
   So "Missing values should be coded as n/a" binds (BIDS TSV empty cells refuse B04), and "a free
   form text file (README) ... should be provided" binds (no root README: B01).
6. Everything else in v3 §2 stands.

## 3. Codes (changes to v3 §3)

| code | v4 meaning |
|---|---|
| S008 | a value fails W1 (constant over every readable input), or a part fails W2 (§4) |
| S011 | the value is an empty selection, or a comparison that does not hold, on every readable input |
| S012 | one value identity (§5.1) is used with two tolerances in one program (exact use = 0) |
| S013 | new (exact-decision phase 7, 28 Oct 2026; D5): a statement outside the exactly decided fragment (SPEC-EXACT 2, part T); Reality cannot decide it, which says nothing about whether its values are constant |
| B13, B15 | retired; their cases are B30 (run index two ways or omitted next to indexed runs: S0265; two files in one folder setting a key to different values: S0133, unless a deeper file overrides that key, since only resolved values are compared (O5, 27 Oct 2026); equal values agree and form, and a value both run readings agree on rests on, and cites, the sidecars of both, the most specific included (O13, 27 Oct 2026)) |
| B30 | new: a choice point of §8.3 whose readings give different results |
| B31 | new: CHANGES does not follow the CPAN Changes convention (§8.5) |
| B01 | also: no root README (§2 item 5) |
| B04 | also: an empty cell or an empty header name in a BIDS TSV |
| T002 | only a CR that is not immediately followed by LF |
| T003 | an empty line, except one final empty line in a plain TSV with ≥ 2 columns (§6.1) |
| T007 | new: an empty header name in a plain TSV or a CSV (principle §3) |
| T001 | a BOM now refuses only a BIDS TSV and JSON; a plain TSV or CSV with a BOM is read (§6.1) |
| T008 | new: CSV quoting with no single reading: a quote in an unquoted field, text after a closing quote, a quoted field not closed on its line (§6.5) |
| T009 | new: a tab or semicolon outside quotes in a CSV (another delimiter, §6.5) |
| T010 | new: a TSV (plain or BIDS) or CSV whose line ends are not all the same (§6.1, §6.5) |
| T011 | new: a use of the first header name (by name, or `header(t, 1)`) of a plain TSV or CSV that starts with a BOM (§6.1) |
| R006 | a sort beyond the node or depth bound; a byte literal now counts ⌊len/64⌋ + 1 nodes (§9.2) |
| R014 | new: a formed statement's printed output longer than the statement bound (§9.3) |
| R011 | new: the program's total output beyond the program bound (§9.3) |
| R012 | new: accounted memory beyond the bound (§9.4) |
| R013 | new: witness work beyond its bound (§4.5) |
| V003 | also: `sample_variance`/`sample_sd` with n < 2, `population_variance`/`population_sd`/`median` with n < 1, `order` k > n |
| V009 | new: a name with two conventions: `median` of an even number of values; bare `variance`, `sd`, `pvariance`, `psd` (Patsak, 25 Oct 21:14) |
| I005 | new: a header time step with no time unit, or not a number (§7.6) |
| J004 | new: a JSON member or item that is true, false or null (§7.5) |
| X002 | new, exit 3: the machine's memory limit is below the floor (§9.4); nothing is checked |

## 4. Witnesses: W1 and W2 (replaces every idle/contradiction rule of v3 §9.12)

### 4.1 Readable inputs

For a statement, the **file slots** are the distinct file hashes it names (directly or through
`let`). A **readable input** assigns to each slot a byte string accepted by every reader the
statement applies to that slot (for example `tsv` and `size`), within the bounds of §9. For a
dataset slot it is a manifest plus files that the 1.0.1 reader finds conformant and that contain
every subject, task, run, acq and rec label the statement writes. The statement's own text
(literals, labels, cutoffs, tolerances) is fixed; only the bytes vary.

### 4.2 The answer

The answer of a value is what §9.9 of v3 would print for it as a claim: the value and its
precision class; for an interval its two ends; for bytes the bytes; for a comparison whether it
holds. A comparison that is undetermined (V006) on an input has no answer on that input.

### 4.3 The rules

- **W1.** For the claim and for each computed sub-value, there are two readable inputs with
  different answers (for a comparison: one where it holds, one where it does not).
- **W2.** For each part, there is a readable input on which the value with the part and the value
  without it have different answers. Parts and their removal: a `where` condition (removed; a
  selection with no condition left is its base); a `key` pair (removed; with no pair left the part
  is not removable and is exempt); `widen` (the widened value replaced by its argument); the
  participant filter of `recordings()` (removed: the two-argument form; v4-fixes 08); a
  file slot (every other slot held at an arbitrary readable assignment, this one varied; this
  form of W2 says the answer is not constant in that slot, so no file cancels out of the answer;
  a refusal is no answer, §4.2; with one slot it is W1 on the statement). (Fix pass R3, 26 Oct
  2026: the file-slot form was stated here but not built, so `difference(a, difference(a, b))`
  formed naming a's file, whose value cancels.)
- Checked innermost first, in the order sub-values finish evaluating; the first failure refuses.
  W1 failing because every input gives the empty selection or a comparison that never holds is
  **S011**; any other failure is **S008**. The message names the value or part. When the part is a
  condition of a `where()` nested in a share's numerator that restates a condition of the share's base
  (`share(where(where(B, c, …), d, …), where(B, c, …))`), the message also names the one spelling that
  says it, `share(where(B, c, …, d, …), where(B, c, …))` (BB's call D4, DESIGN §10.1).
- W1/W2 are checked after the value is computed on the real bytes and after check 2 (so a sort and dependency-set disagreement is reported as C001, the floor, first).

### 4.4 Building witnesses (normative, so implementations agree)

**Deleted in exact-decision phase 7 (28 Oct 2026):** no statement is decided by this section's search any more. A
statement in part T is decided exactly (SPEC-EXACT); every other one refuses S013. The text below is the record
of the search that decided statements before (frozen, untrusted copy: tests/old_witness.py, run only by the
differential harness); its bounds MAX_TYPES, MAX_PAIR_TYPES and MAX_REAL are gone with it.

**Since exact-decision phase 3 (26 Oct 2026):** a statement in part T (SPEC-EXACT 2: `tsv`/`csv` slots,
`where` with `eq`/`ne` on string literals and, since its checkpoint (27 Oct), number conditions; `rows`, `count`,
`share`; `cell` by position or `key`, `header`, `number()` of a cell or header; `difference` of counts or of
numbers, and comparisons of those; since phase 4 also part N: `sum`, `mean`, `max`, `min`, `order`, `median`,
`widen`; since phase 5 part H: `json`/`member`/`item`, `nifti`/`dim`, `size`, `bytes`; since the variance phase variances and SDs alone or
compared with a cutoff; with the limits SPEC-EXACT 2
states) is decided exactly by SPEC-EXACT, not by the search below
(`decide.py`). The search decides every other statement until its part's phase.

Rewritten 26 Oct 2026 from `witness.py` (review finding 20: the earlier text was not what was
built, and a checker built from it refused claims v4 forms). Every list below is in the order
given, duplicates dropped keeping the first. A second checker that builds exactly this family and
this search reaches the same verdicts; `tests/test_v4_fixes.py::test_r20_*` enumerates the family
from this text independently and compares it with the code's, byte for byte.

1. **What the statement names.** Walking the statement depth first, left to right:
   - *Table slots.* A slot is a `tsv(f)` or `csv(f)` file name, or `P:d` for `participants(bids(d))`,
     reached through `where`, `cell`, `header`, the aggregates, `rows`, `count`, `share`. Per slot,
     the columns it names, each a position (an integer) or a header name (a string), and per
     column the literals compared with it, in order of first appearance: the second argument of
     `eq`/`ne` in `where`, and the key literals of `key()` in `cell`. A column is **numeric** if a
     `ge/gt/le/lt` condition, a numeric aggregate (`sum mean max min sample_variance
     population_variance sample_sd population_sd order median`) or `number(cell(t, r, k))` reads it;
     a participants column named by `extra` is numeric if `number(extra(p, col))` reads it (O6).
     Rows named by position: the integer r of `cell(t, r, k)` (1 ≤ r ≤ 100 000).
   - *Cutoffs* c: every numeric parameter of every call (`c =`, `tolerance =`, ...), calls taken in
     pre-order (a call before its arguments, arguments left to right);
     *tolerances* q: the absolute values of `widen()`'s.
   - *BIDS.* Per dataset name d: the subject labels of `participant`/`recording`, the entity sets of
     `recording` (sub, task, run, `acq()`, `rec()`), the task labels of `recordings`; an events slot
     `E:d` (column 1, the onset, numeric; column 2 numeric when `duration` is read; trial types
     named by `trials` as literals of column `trial_type`; rows named by `onset/duration(r, i)`);
     participants columns named by `extra`.
   - *JSON* paths named by `member`/`item` chains from `json(f)` (item index 1–1000); *NIfTI* slots
     `nifti(f)`; *raw* slots read by `size(f)` or `bytes(f, o, n)` (need o + n).
2. **Candidate decimals** (`Plan.values`), each written as its shortest decimal (a value with no
   finite decimal is dropped): 0; then, for each cutoff c and each nonzero tolerance q,
   c + (Σ tolerances − q/2) and c − (Σ tolerances − q/2); then, for each cutoff c and each Q in the
   absolute values of all cutoffs (or 0 when there are none), c + 2Q + 1 and c − 2Q − 1; then 1, 2;
   then c, c + 1, c − 1 for each cutoff; then c/2 for each cutoff.
3. **Options per column.** Columns in order: positions 1 … (largest position named), then names in
   order of first appearance. A numeric column's options interleave the candidate decimals with its
   literals that are not among them (a1, b1, a2, b2, …, duplicates dropped). Any other column's
   options interleave its fresh literals with its literals; fresh literals are the first byte
   strings over `a`–`z` in length-then-lexical order (lengths 1–3) that are not its literals: two
   for a column the statement names, one for a position only filled in.
4. **Row types** (`_shells`, at most 64 **[prov]**): types in order of their largest option index
   (all types using options 0..r before any that needs r + 1), lexicographic within a shell.
5. **A table's bytes.** Header: names as written, positions as `c<i>` (the *alternate* header uses
   `d<i>`); no column at all: `c1` (`d1`). If any option is the empty string, one more column
   `zpad<i>` (the first such name not named by the statement) holding `p`. A row with no cell and
   no pad column is written `z`. Tab-separated, LF line ends, final LF.
6. **Table candidates, in order:** the header only; every type as a one-row table; every pair
   (i ≤ j) of the first 16 types **[prov]**; for each m in the first 4 of the sorted set
   {⌊|c|⌋ + 1 : |c| ≥ 2}, every type repeated min(m, 100 000) times; for each of the first 8 named
   rows (increasing) that is above 3, r, the table of r − 1 copies of type 0 and then each of the first 16 types; when more
   than 6 columns, the *full row* (each column's option 1, or 0 if it has one option) alone, then
   for each column j the full row followed by the full row with column j at option 0; the
   alternate header alone, then with type 0; every triple (i ≤ j ≤ k) of the first 6 types.
   A `csv` slot takes the same tables written as CSV (§6.5).
7. **Other slots.** NIfTI: the 3-D header 1×1×1; then 4-D headers 1×1×1×n over the types (as 4) of
   (counts, time steps, unit) with counts 1, 2 and the sorted set {⌊|c|⌋ + d : d ∈ {0, 1}} within
   1–100 000, time steps the positive candidate decimals then 1000·c for each positive cutoff, unit
   s then ms; then, for each spatial axis, the 3-D headers with that axis at each entry of the
   count list after its first (1, 2, then the set, here without dropping repeats). JSON: `{}`, then the trees built from the types (as 4) whose options per leaf path (a named path
   no other named path extends)
   interleave the candidate decimals with two quoted fresh strings (missing array items are 0; a
   type whose paths clash is skipped). Raw: for each size in sorted {0, 1, need, need + 1}, that many 0x00
   bytes, then that many 0x01 bytes. A slot's candidates: NIfTI, then JSON, then TSV, then CSV, then raw, as it is read.
8. **The real bytes.** A file slot whose bytes the checker has read whole (in this or an earlier
   statement), at most 1 MiB **[prov]**, also
   takes them as its last candidate, if not already a candidate.
9. **BIDS slots** (`Plan.datasets`; the template `witness._dataset` is normative; `tests/bidsmin.py`,
   named here before, never existed). A candidate dataset has a description, a README, a
   participants table (participant_id first; the statement's subject labels first, then ids the
   statement writes, then `w1`, `w2`, …), and per named recording one BOLD image 1×1×1×v, its sidecar
   (TaskName, RepetitionTime) and its events TSV (onset and duration added when missing); with
   `recordings(b, task)`, every participant gets a recording of each task; subjects with no
   recording get a T1w image. RepetitionTimes are 2 then the first 8 other positive candidate
   decimals; volume counts 5, 1, 2, then the first 8 of the sorted set {⌊|c|⌋ + d : d ∈ {0, 1}}
   within 3–100 000; a recording not varied in its volume count has max(5, ⌊onset/TR⌋ + 2 over its
   events) volumes. Order: the base dataset (the second
   participants candidate, or the first if only one); every participants candidate; with
   recordings(), for each of the first 16 participants candidates, every events candidate, every
   RepetitionTime and every volume count applied to all recordings at once; then, for each named
   recording in turn, its events candidates, RepetitionTimes and volume counts on the base dataset.
   Each candidate must pass the whole 1.0.1 reader to count.
10. **The search.** Slots are ordered by the hash their name is bound to (so renaming changes
   nothing). The base assignment gives every slot its second candidate (its first if it has one).
   Assignments, in order: for each slot and each of its candidates, the base with that slot
   changed; then, with two slots or more and a real-bytes candidate, the same again on the base
   with every slot that has real bytes at them. Every assignment is evaluated (within §4.5's
   bound). A reader's refusal (T, J, I, B, M, F) makes the input unreadable: none of its answers
   count; a value refusal (V) is an outcome.
11. **W1** holds for a computed value (every call but conditions, readers and sort-only calls) when
   two evaluated assignments give it different answers; else S011 when the only answers are "does
   not hold" or empty selections (or a comparison never answers), and S008 otherwise. **W2** holds
   for a part (each `where` condition, a `share` condition repeated from its base being removed
   from both, the participant filter of `recordings`, `widen`, each `key` pair of a multi-pair
   `key`) when, on some evaluated assignment in order, the statement with and without the part
   answer differently, judged at the highest enclosing value that still answers without it.
   Then, with two slots or more, **W2 for each file slot**, slots in the order of item 10: it
   holds when two evaluated assignments that agree on every other slot (bytes; a dataset by its
   manifest's hash) give the statement two different answers (a refusal is no answer; a
   comparison that does not hold answers "does not hold"); else S008, naming the slot by its
   hash (fix pass R3).
12. A value is refused when no witness exists among the candidates. This is a refusal by default:
   the candidates are a finite, fixed family, so some non-idle values may refuse (overcorrection).
   A formed value carries assignments the checker built and its own readers accepted on which it
   (and the statement, with and without each part) answers differently. This is an argument, not a theorem (review finding 26): it holds only while (i) each candidate assignment is a possible input (two names bound to one hash are one slot, v4-fixes 01; a candidate a reader refuses gives no answers at all, 06), (ii) what is judged is the claim as formed (header names resolved to positions, 02), (iii) every part is judged (widen and the recordings filter, 07, 08), and (iv) a machine failure is no verdict, never a skipped candidate, and the search order does not depend on names (03, 04). Each of these was broken before 26 Oct 2026 and let an idle value form. The evidence is measured, not proved: tests/test_v4_bruteforce.py (DESIGN 1.3 item 6) finds, for 86 generated programs over every readable table of up to 3 rows in its space, no formed claim that is constant or has an idle part there, and no overcorrection.

### 4.5 Cost

Witness work is charged to the statement's steps like other work (reading and evaluating each
candidate at the §9.1 costs) and also counted against a separate bound of 50 000 000 steps per
statement **[prov]**; beyond it R013.

## 5. Value identity and `widen`

### 5.1 Identity

The identity of a value is the triple (the computation's name, the files read by hash, the
positions read), positions resolved on the real bytes: a cell as (row number, column number); a
selection as the set of row numbers it selects; an aggregate as its selection's row set and its
column number; a count of rows (`count`, `rows`) as its selection's row set (v4-fixes 19: so
`rows(t)` and `count(t)`, or conditions in another order, are one value); a BIDS value as its dataset's manifest (by hash) and the manifest paths it reads, with the row it reads (fix pass, 26 Oct 2026: by paths, not file hashes, since two files with the same bytes at two paths, such as the events files of two subjects, are two values; R2: `tr`, `onset` and `duration` have such an identity, so S012 counts their exact uses too). Two values with equal
identity are one value for S012 and for frames, however they are written.

### 5.2 Affine `widen`

A widened value is `x + q·ε_v`, `ε_v ∈ [−1, 1]`, with one symbol per value identity v. A value is
an affine form `a0 + Σ a_v·ε_v` (a0 exact rational, or the exact root of §7.2); `difference`
subtracts forms; the interval is `[a0 − Σ|a_v|, a0 + Σ|a_v|]`. Precision classes and units as v3.

### 5.3 S012

Over the whole program, after all statements: group every use of a number (widened or not) by
identity; a group with two different tolerances (an exact use being 0) refuses S012 on every
statement in it, as v3 §9.10. A widen directly of a widened value is its base value widened by the
sum of the tolerances: `widen(widen(x, tolerance = a), tolerance = b)` is one use of x at a + b,
with one symbol (x's) in its affine form, and is the same value as `widen(x, tolerance = a + b)`
(O9, 27 Oct 2026: otherwise x could be used at a and at a + b under two identities).

## 6. Readers

### 6.1 Plain TSV (changes to v3 §9.4)

- Line ends are all LF or all CR LF; a mix refuses T010 (Patsak, 25 Oct 2026 22:29, as CSV). A CR
  not immediately followed by LF: T002. The same holds for a BIDS TSV.
- After splitting: one final empty piece (from the final line end) is dropped as before. If, after
  that, the last line is empty and the header has ≥ 2 columns, it is dropped as "no row". Any other
  empty line: T003.
- An empty header name: T007.
- A byte-order mark (changed 25 Oct 2026 with principle §12; v3 and v4 before refused T001): it
  makes one thing ambiguous, the first header name (with U+FEFF or without), and nothing else. The
  file is read without the BOM; naming that column by its name, or `header(t, 1)`, refuses T011.
  Its cells, by position, and every other column have one reading. (Principle §12 asks the CSV
  reader to follow the TSV rule, and its target file has a BOM; so the shared rule had to read
  such a file. A BIDS TSV still refuses T001: BIDS fixes the first header names.)
- Everything else as v3.

### 6.2 BIDS TSV

The plain rules of 6.1 except the one-trailing-empty-line rule (an empty line is B04), plus: an
empty cell or an empty header name is B04 (1.0.1 §4.2, "should be coded as n/a", binding by §2
item 5). CR LF is a line end (register entry for the §4.2 sentence "tab delimited values (.tsv)
files, aka csv files where commas are replaced by tabs", read as fixing CSV line structure).

### 6.3 Number columns over selections (replaces v3 §9.12 `sum/mean/max/min`)

`sum, mean, max, min, order, median, variance, pvariance, sd, psd` read the column's cells only in
the selected rows (all rows for a table or participant set). The first selected row whose cell is
not a decimal refuses V005. Then the n-conditions of §3 (V003, V009).

### 6.4 One number reader (Patsak, 25 Oct 21:36; replaces v3's decimal reader)

TSV and CSV cells (plain and BIDS), `number()` and JSON numbers are read by one grammar,
`-?(0|[1-9][0-9]*)(.[0-9]+)?([eE][+-]?[0-9]+)?` in ASCII (JSON's number grammar), as the exact rational: `1.5e-2` is 3/200. At most
1000 digits before the exponent and an exponent of at most ±1000 (six characters), else R007.
The bounds apply only to a cell the grammar matches whole: `e2026` or `sub_e2026` is not a number
(no R007), as `abc` is not (O3, 27 Oct 2026). v3 refused exponents in TSV cells (B06 for a `1e1` onset, an overcorrection): an exponent has one
exact reading, and a TSV cell has no second numeric reading that a JSON number lacks, so the two
readers now agree. What stays refused in both: `.5`, `1.`, `+1`, `1,5`, non-ASCII digits, NaN,
Infinity, spaces, and a leading zero (`007`, `00.5`, `-01`; `0`, `-0`, `0.5` are fine) in TSV and CSV
cells as in JSON (J001): wherever a cell is read as a number it refuses (V005; B06 for a BIDS onset or
duration), and `cell()` still states its bytes (BB's call on Patsak's behalf, 26 Oct 2026, reversible;
review finding 31).

### 6.5 CSV (principle §12, Patsak 25 Oct 2026 22:10)

`csv(f)` is a table, sort `CSV[#k]`, used by every table function as `tsv(f)` is. RFC 4180 with
the comma as the only delimiter:
- A field is either quoted (`"..."`, with `""` for one quote; it must close on its line and be
  followed by a comma or the line end) or unquoted (no quote at all): else T008. A line break
  inside quotes is refused (T008): RFC 4180 allows it, but line-based readers split the row.
- A tab or a semicolon outside quotes: T009 (it could be the delimiter). Inside quotes it is a byte.
- Line ends as §6.1 (all CR LF or all LF, else T010; a lone CR: T002). The last line may lack a line end.
- BOM, blank lines, empty header names, U+2028 and the other separators, and UTF-8: as §6.1.
- Every row has as many fields as the header: else T004. A repeated header name refuses when it is
  used by name (K002), as in a plain TSV.
- A cell is its bytes, quoting removed, nothing trimmed: `Female` and `Female ` differ. `"1"` and
  `1` are the same cell. Numbers: §6.4.
- Witness (§4.4): a CSV slot takes the TSV slot's candidate tables written as CSV (a cell holding
  a comma, quote, tab or semicolon is quoted), so W1/W2 judge CSV statements as TSV ones.

## 7. New computations

### 7.1 Table

| computation | result | sort | notes |
|---|---|---|---|
| `sample_variance(s, col)` | number | `SampleVariance[X, <col>]` | Σ(x − m)²/(n − 1), exact; n < 2 V003 |
| `population_variance(s, col)` | number | `PopulationVariance[X, <col>]` | Σ(x − m)²/n; n < 1 V003 |
| `sample_sd(s, col)`, `population_sd(s, col)` | root (§7.2) | `SampleSD[...]`, `PopulationSD[...]` | square root of the variance |
| `order(s, col, k)` | number | `Order[X, <col>, k]` | the k-th smallest of the selected decimals (k ≥ 1 a position); k > n V003 |
| `median(s, col)` | number | `Median[X, <col>]` | n odd: the ((n + 1)/2)-th smallest; n even V009; n = 0 V003 |
| `share(sel, base)` | share | `Share[X of B]` | `base` the table or a selection of it whose conditions are all conditions of `sel` (else S006); the same conditions S008; base with 0 rows V003 |
| `recordings(b, task[, sel])` | recording set | `BOLDRecordings[X, task T ...]` | as built in 7.7 (run, acq, rec and an `of =` slot were planned here; they are not built and refuse) |
| `count(rs)` | count | `Count[RS]` | |
| `sum/mean/max/min(rs, q)` | as above | `Mean[RS, events]` etc. | 7.7; `q` one of `events`, `volumes`, `tr`, `trials("type")`; Recorded stays Recorded, unit kept; order/median/variance/sd of a recording set are not built (S007) |

Units, precision and frames follow v3's rules for the per-recording quantities.

### 7.2 Exact roots

A root value is `√v` with v a non-negative exact rational. Printed `sqrt(<v>)` with v printed as
v3 §9.9 prints a rational, then the precision suffix; if v is a perfect square of a rational, it is
printed as that rational. A widened root prints `sqrt(v) - q` and `sqrt(v) + q` as its ends. Comparisons with a cutoff c (in the unit of the root): `√v > c` ⇔
`c < 0 ∨ v > c²` (and similarly for <, ≥, ≤), decided exactly. A widened root `√v ± q` compares by
the same rule applied to each end (`√v − q > c` ⇔ `√v > c + q`). `difference` with a root as an
argument is S006, decided by the sort (a `sample_sd`/`population_sd`, or a widen of one), not by
whether the bytes give a rational root (O4, 27 Oct 2026). Value identity is that of the variance.
A variance is in the square of its column's unit: `difference` of a variance (or a widen of one, or a difference of
two) with a number that is not one is S006, decided by the sort in the same way (Patsak's call 4 of 27 Oct 2026, 14:00
CET, following O4: squared units minus units has no meaning). Two variances subtract. A difference whose first argument
is a widened variance (or widened difference of two) is in the squared unit too (28 Oct 2026: before, its identity
`Widened[...]` hid the variance, so such a difference minus a mean formed and minus a variance refused S006).

### 7.3 Number conditions in `where`

`ge(col, c = q)`, `gt`, `le`, `lt`: keep the rows whose cell in `col` is a decimal ≥, >, ≤, < q.
`c` takes a number without a unit (a unit is U002). The printed sort writes `col k >= q` with q
printed as v3 §9.9 prints a rational. Evaluation: the eq/ne conditions run first, then the number
conditions, each over the rows still selected. A non-decimal cell gives its number condition no
answer on that row; the row is dropped if another condition is false on it, and if every other
condition keeps it the statement refuses V005. A number beyond the reader's bounds is read the
same way: no answer on that row, so it refuses R007 only if every other condition keeps the row (O3). So the verdict does not depend on the order the
conditions are written in (v4-fixes 18, BB's call on Patsak's behalf (2026-10-26), reversible). Idle, implied or contradictory number conditions are refused by §4.3 (S008,
S011). §4.4: a column a number condition names is a number column for the witness builder, and
q joins the cutoffs.

### 7.5 JSON, the file-level reader (principle §11, adopted 25 Oct 21:14)

| computation | result | sort |
|---|---|---|
| `json(f)` | JSON object or array | `JSON[#1]` |
| `member(j, "key")` | the member's value | `Member["key" of J]` |
| `item(j, k)` | the k-th item (k ≥ 1) of an array | `Item[k of J]` |

The reader is RFC 8259 in strict UTF-8. A member or item that is a number is an exact rational
with no unit and precision Exact; a string is its UTF-8 bytes; an object or an array is a JSON
value that only `member`/`item` take (claiming it is S009); true, false and null are J004.
Refusals, each because the bytes have more than one reading or none: a byte-order mark or bytes
that are not UTF-8 (T001); not JSON, including leading zeros, `.5`, trailing commas and trailing
text (J001); a key twice in one object, after escapes are decoded (J002); NaN, Infinity and a
string or key with a lone surrogate (J003); depth beyond 64 (R008); more than 1000 digits
before the exponent or an exponent beyond ±1000 (R007). Exponents are read exactly (§6.4). `member` on an array or `item` on an object, a missing key and k beyond the
array are V002. The named key is checked like a name (K004 invisible characters; K003 a sibling
key with the same UTS #39 skeleton). The BIDS reader keeps reading sidecars as v3 does
with the same reader, so the two never read one file differently.

§4.4 item 5 (witnesses for JSON): the named member/item paths of each file get candidate texts:
`{}`, then each named leaf set to a candidate decimal or one of two fresh strings, types in shell
order, at most 64.

### 7.6 One NIfTI header (file-level; DESIGN §5.3 item 1)

| computation | result | sort |
|---|---|---|
| `nifti(f)` | a NIfTI header | `NIfTI-1[#1]` or `NIfTI-2[#1]` |
| `dim(n, k)` | count, k ≥ 1 | `Dim[N, k]`; k > dim[0] V008 |
| `pixdim(n, 4)` | Recorded[s] | `Pixdim[N, 4]`; other axes S006; dim[0] < 4 V008 |

The file is gzip when its first two bytes are 1f 8b (no uncompressed NIfTI-1/2 header can begin so),
else read as is; only the header is read (at most 2^20 compressed bytes to reach it, else R003; a
broken gzip stream I004; no header I001/I002). A gzip file must still be whole (O8, 27 Oct 2026): one
or more RFC 1952 members, each ending in its CRC-32 and length, then nothing or only zero bytes, as
`gzip.open` and the BIDS reader read it; otherwise I004, checked before the header. The check
decompresses the whole stream and is charged per compressed byte and per 4096 decompressed bytes,
on every use. (B05; Argon review 2 05) The BIDS reader's check of each image's data (a .nii.gz read whole) is charged
per 4096 decompressed bytes as they are read too (R002 stops it), beside its size, on every use. A member's magic that straddles a read no longer ends the header early. `pixdim(n, 4)` is the exact stored float converted
to seconds by xyzt_units (8 s, 16 ms, 24 us; any other code, NaN or infinity I005), Recorded
(Patsak 25 Oct 21:14), printed exactly: float32 1.52 prints 1.519999980926513671875 s. It says
what the image header records, not BIDS RepetitionTime. §4.4 item 6: witness headers are a 3-D
one and 4-D ones varying volume count, step (s and ms) in shell order, at most 64.

### 7.4 Single-recording facts (not built; DESIGN §5.3)

No partial-dataset BIDS reading: `tr`, `volumes`, `trials` stay behind `bids(d)`. Built:
`nifti(f)`, `dim(n, k)`, `pixdim(n, 4)` on one file (§7.6). `json(f)`/`member()` wait on taste
call 4 (now decided: built, §7.5).

### 7.7 Recording sets: joins on BIDS keys and aggregates (Phase F, DESIGN 4 finding 29)

- `recordings(b, "task")`: the dataset's BOLD recordings of that task label, sort
  `BOLDRecordings[<bids>, task t]`, in entity order. `recordings(b, "task", s)` with `s`
  `participants(b)` or a selection of it: only the recordings whose `sub` entity is the label of a
  selected `participant_id` ("sub-<label>", 1.0.1 text line 1238, the only key 1.0.1 defines);
  sort `... , of <s>]`. A selection of anything else, or of another dataset: S006. Conformance
  already requires a participants row for every subject folder (B11), so no join can drop a
  recording unnoticed. Labels: the K003 checks of `recording()`. Cost 4R + 1 for R recordings.
- `count(rs)`; `sum/mean/max/min(rs, q)` with q from the closed list `"volumes"`, `"events"`,
  `"tr"`, and `"trials"` followed by a trial type. Each recording's value is the one `volumes(r)`,
  `events(r)`, `tr(r)` or `trials(r, type)` gives, with its refusals; the result keeps the unit
  and is Recorded when any value is. The sort names every file read (check 2). The unit is the quantity's (`tr`: s; the others none), not the first value's, so an empty set keeps
  it (v4-fixes, review finding 25). Empty set: `sum` is 0 (0 s for `tr`), Exact (no value was read), the others V003. Another q: S006. Witnesses (4.4 item 7): every participant of a candidate
  dataset gets a recording of the task, and all of them take each per-recording candidate.

## 8. BIDS: register, decisions, choice points (replaces v3 §9.11's case lists)

### 8.1 The register

`v4/bids/REGISTER-1.0.1.tsv`, UTF-8, LF, one header line:
`id line sha256_12 class codes decision note text` (TAB-separated).

- `id` `S0001…`, in text order; `line` the first line of the block the sentence is in; `sha256_12`
  the first 12 hex digits of SHA-256 of the sentence text; `text` the sentence as split.
- `class` one of: `checked` (the reader checks it; `codes` lists the refusal codes, each pinned by
  a test), `silent` (it creates a choice point; `decision` names it), `unshowable` (true or false
  of the world, not of bytes; `note` says why), `notfiles` (not about dataset files: changelog,
  licence, headings, examples' prose), `reality-call` (a rule Reality adds; `note` names the call).
- **Splitting rule** (implemented by `v4/tools/split_register.py`, which is normative): the text
  must hash to `51665a13…6a354f`; zero-width characters U+200B, U+200C, U+200D, U+2060, U+FEFF
  and soft hyphen U+00AD are removed; blank lines end blocks; inside a block a sentence ends after
  `.`, `!` or `?` followed by white space and an upper-case letter, digit, bullet, quote or `(`;
  a bullet (`●`, `○`, `•`) followed by white space starts a sentence; internal white space is
  collapsed to one space. [ran] This gives 633 sentences.
- A test fails unless the splitter's output and the register agree row for row and every row has
  a class.
- `codes` may also be `read`: a reading rule applied when forming, pinned by a forming test.

### 8.2 Decisions

Every point where the BIDS reader interprets names, entities or metadata is a **decision** in the
code: a function that returns its result and the register ids that fix it. Kinds: template match
of a path; entity value equality; applicability of a metadata file to a data file (§3.5
inheritance, any level, any metadata extension); which file supplies a field; classification of a
file as defined, defined-but-not-implemented, or extra. A test fails if a branch on names,
entities or metadata in `bids101.py` is outside a decision.

### 8.3 Choice points

A decision whose cited sentences do not fix one result (every `silent` row) is a choice point and
lists its readings. The reader computes the decision's result under each reading; if the results
differ, the dataset does not conform, **B30**, naming the register id and the readings; if they
agree, the reader goes on. Choice points known now (more come from the register):

| choice point | readings | result compared |
|---|---|---|
| run index written two ways (`run-1`, `run-01`) | one run / two runs | for every file with a run entity: which files match which |
| IntendedFor source (S0495, S0510) | phasediff JSON only / any image JSON of the fieldmap | the BOLD images of the subject the fieldmap corresponds to (its IntendedFor targets, or all of the subject's when it has none; O7, 27 Oct 2026: before, whether it had IntendedFor and the set, so readings that cover the same scans refused) |
| a TSV/bval/bvec metadata file at any level (incl. `tasks.tsv`) | inherited metadata / extra | kind implemented? if not: B14 (not B30) |
| a JSON at any level whose name could match data files (§3.5) | not a choice point: S0132 says any metadata file may sit at any level, so a name of the entity form at the root or in a subject folder is metadata (read, B03 if not JSON), never extra | |
| onset beyond the recording | conforms / does not | refuse B30 when `onset ≥ dim[4] × TR` |
| empty-entity files, footnote cases | as found in the register | |

Classification default: a file is extra only if the decision shows that no 1.0.1 template and no
§3.5 inheritance rule can apply to its name; otherwise it is defined (read) or
defined-but-not-implemented (B14).

### 8.4 Dictionaries

Every tabular file 1.0.1 defines (participants, phenotype, events, at every level its inheritance
allows) may have a dictionary with the same name and `.json` (§4.2). It is read as JSON (B03); its
top-level keys must name columns of the TSV(s) it describes (B19), except `MeasurementToolMetadata`
in a phenotype dictionary (§8.11). A dictionary without its TSV: B19. An events dictionary
(`*_events.json` at the root, in a subject folder or in `func/`) describes the events TSVs below
its folder whose entities include its own; each key names a column of at least one of them.
For each events TSV, its dictionaries are resolved by the inheritance principle exactly as a BOLD
file's sidecars are (O14, 27 Oct 2026): two dictionaries in one folder describing a column
differently, not overridden deeper, are B30 (S0133); run-1 against run-01 is the S0265 choice
point (B30 when the resolved descriptions differ). No computation reads a description yet; the
rule is the sidecars', so one dataset has one reading of its metadata.

### 8.5 CHANGES (S0235; BB's call on Patsak's behalf, 26 Oct 2026, reversible)

A CHANGES file follows CPAN::Changes::Spec 0.04 (the version BIDS 1.0.1 links; pinned as
`CPAN-Changes-0.400002-Spec.pod`, sha256 22df2f5f…5e5a, not included in this repository) with versions in
CPAN::Meta::Spec's Version Formats (`CPAN-Meta-2.150005-Spec.pm`, c17f5d81…7950). Precedence: a
BIDS 1.0.1 example that is well-formed in its own kind's grammar is BIDS's own reading and wins over
a reference on the point where they conflict, for that point only; an example with no reading at
all is an erratum and binds nothing. BIDS's example `1.0.1 2015-08-27` is a well-formed version, so
a dotted version needs no leading `v` and may have zero components. Everything else binds:
- After a BOM, lines end all LF or all CR LF (Reality's own call, as for TSV), else B31.
- A Version line starts at column 0: a version (decimal `\d+(_\d+)?(.\d+(_\d+)?)?` or dotted
  `v?\d+(.\d+)+[._]\d+`, one underscore at most, dotted components after the first at most 999),
  then whitespace followed by any whitespace or non-word characters, then a date: W3CDTF (the T
  optional: a space may stand for it, nothing may) or one of the no-date strings (Unknown Release
  Date, Unknown, Not Released, Development Release, Development, Developer Release), each ending at
  a word boundary; any text after it is the release note. A line whose text after the version is
  no date is not a Version line (`1.0.1 BANANA`, `1.0.1 Aug 27, 2015`, `1.0.1 UnknownFooBar`; fix
  pass R4: such lines conformed before). Lines before the first Version line are the
  preamble. After it, a non-blank line is indented: a group heading `[...]` or a change.
- B31: no Version line with a change (the required elements).
- B30, a point with two readings: a date-shaped start that is not a date where a shorter start is
  one (`2020-02-30`, `2020-01-01T10:00` without an offset; a date that runs on into a digit, a
  letter or one of `- / : . +`: `2015-8-27`, `2015/08/27`, `2015-08-2710:00Z`, a shorter date and a
  glued release note or no date); a non-ASCII character in the
  separator (Perl's ASCII or Unicode word characters); a version both decimal and a dotted one past
  999; an unindented non-blank line after a release (the spec's Groups example writes changes and
  headings at column 0, its grammar indents them); a line starting `[` whose matching `]` is not its last character
  (`[fix] handle [edge case]`: the spec's heading ends with the matching bracket; C3, 27 Oct 2026);
  a release with no change while another has one (required per release or per file); a character
  other readers take as a line or field break or a byte-order mark anywhere after a leading BOM
  (U+000B, U+000C, U+001C-U+001E, U+0085, U+2028, U+2029, U+FEFF, U+0000, as the TSV reader's T006;
  C2, 27 Oct 2026); a line after a release indented with a non-ASCII space such as U+00A0 (Perl's
  Unicode `\s` reads it as indentation, ASCII `\s` does not; C2); in the preamble, an unindented line
  starting with `v` or a digit that is not a version but is followed by a date, with an indented
  non-blank line under it before any other non-blank unindented line (`1.2.1000 2020-05-01` or
  `v1.2 2020-05-01` with changes, above a release: a release or preamble; C1, 27 Oct 2026; with no
  release in the file it is B31, as either reading lacks one).

## 9. Costs, output, memory, paths (replaces v3 §9.8 where they differ)

### 9.1 Abstract costs

Each charge is an upper bound on the specified algorithm's operations and is made before the work.
Changes to v3's table: `where` filtering charges, per condition, the rows still selected when the
condition runs (not R × conditions); `key()` charges R + 1 per pair, in one pass; the BIDS
inheritance step charges, per data file, the metadata files in the folders on its path (indexed by
folder and suffix); a call to `key` charges 1, as §9.8 says (finding 20); a manifest's parse charges
one step per byte (its paths are checked character by character) plus (⌊bytes/64⌋ + 1)·(bit length of
its entry count + 1) for the file-and-folder check, one binary search per path in byte order, both
before the work, here and when the store reads supplied manifests at start (each at most the file
bound, else not read; fix pass R6: the check built every folder prefix, quadratic in a path's depth,
uncharged); witness work as §4.5, its W2 evaluations included (fix pass R6: they were not added);
new computations: R + 1 for the column pass, plus n·⌈log2(n + 1)⌉ for `order`/`median`. Big
numbers (review finding 22): an exponent makes a six-byte cell a thousand-digit number, so exact
arithmetic is charged by size. With W = 1 + ⌊(bits of numerator + bits of denominator)/64⌋ for the
widest value read, a column pass adds ⌊W²/16⌋ **[prov]** per value (its sums and squares), a number
condition adds it per row it compares, and `order`/`median` multiply their n·⌈log2(n + 1)⌉ by
1 + ⌊W²/16⌋ (each comparison is two products); charged after the cells are read, before the
arithmetic. Values under 4 words add nothing. A test requires actual work ≤ K × charged steps on a
corpus and adversarial inputs, K = 64 **[prov]**; work inside C builtins is not counted by that test,
so a separate test pins time per charged step for thousand-digit cells against small ones.

### 9.2 Sort size

A byte literal counts ⌊len/64⌋ + 1 nodes **[prov]** (was 1): one node plus one per full 64 bytes, so a 1-byte literal is 1 node and a 64-byte one 2 (`sorts.py`; corrected from ⌈len/64⌉ + 1, review finding 23, which the code never did); other node counts as v3.

### 9.3 Output

A statement's printed lines are computed in length as the sort is built and printed; a statement
longer than 1 048 576 bytes **[prov]** (its lines with their LFs, `#k` lines included) refuses R014 instead of printing. The program's total output
is bounded by 67 108 864 bytes **[prov]**; the statement that would cross it refuses R011. Refusal lines count towards the
program bound too. Output is held until the program-wide S012 pass, as in v3, and is written then;
what is held is the printed text, never the sorts, so it is bounded by the program bound.

### 9.4 Memory

Every structure the checker keeps after the operation that made it (file text, tables, sorts,
values, metadata, witnesses, held lines) is charged accounted bytes: its length in bytes plus 64
per object **[prov]** (a kept selection: 8 bytes and one object per row, 72 per row; v4-fixes 04). A
plain TSV table is refused before it is built when its cells alone (80 each, one per tab or line end,
less one) would pass the bound. A BIDS table (`participants.tsv`, an events file) is kept and refused the same way, where
the dataset's conformance gate parses it and where a value reads it (unit H07, BB's call on Patsak's behalf, 30 Oct 2026,
reversible; a gate's R012 is the program's memory, not the bytes, so it is not kept for another program). A program whose accounted bytes would exceed 1 073 741 824 **[prov]**
refuses R012 at that statement. Running out of memory inside the witness search is no verdict, as
anywhere else, never a skipped input. The **memory floor** M is 2 147 483 648 bytes **[prov]**: at
start the checker reads RLIMIT_AS, RLIMIT_DATA, the cgroup v2 `memory.max` of its process and of
every ancestor cgroup, total physical memory, and on Windows the process and job memory limits of the
job object the process is in (`QueryInformationJobObject`, the immediate job only), where each exists; if the smallest is below M, it prints
`no verdict: this machine's memory limit (N bytes) is below Reality's floor (M bytes); nothing was checked`
and exits 3 (X002). The floor is part of the trusted base (principle §1).

### 9.5 Paths and encodings

Manifest paths are strict UTF-8; every filesystem operation uses the UTF-8 bytes of the path,
never the locale or the filesystem encoding. Under `--files`, symlinks, non-regular files and files
the process cannot read are skipped; under `--root`, a file that is missing or cannot be read is not
found. A named file not found is F001 either way. One rule for links, on every system (fix pass W1,
26 Oct 2026): no component of a path under a `--root` or `--files` folder may be a symlink or a
Windows junction; such a file is not found (F001) or skipped, and such a folder is not walked by
`--files` or by `reality4 manifest` (before, a symlinked folder under `--root` and an NTFS junction
were followed while a symlinked file was refused). Names compare byte for byte (fix pass W2): each
component of a manifest path must be in its folder's listing exactly, so a case-insensitive or
normalising file system cannot let `README` name a stored `readme`, and the verdict does not
depend on the file system.

## 10. CLI

- No arguments, or an unknown command: usage on stderr, exit 2.
- `manifest DIR [--out FILE]`: walks DIR with bytes paths; a name that is not strict UTF-8 or fails
  the manifest path rule (v3 §9.3) prints the offending path (escaped) on stderr and exits 2 with no
  manifest written; DIR missing or not a folder, `--out` without a file, or a FILE that cannot be
  written (a missing folder, no permission): a message on stderr, exit 2, no traceback (O10).
- `check` with no PROGRAM, with `-` (standard input) more than once, or with an option other than
  `--files`/`--root`: usage on stderr, exit 2 (O10).
- A program with no statement (only blank lines and comments, or no bytes) refuses P011 as a whole:
  "accepted" would state nothing (O10, 27 Oct 2026).
- Exit codes: 0 accepted, 1 refused (any statement or the whole program), 2 usage, 3 no verdict
  (X002, or MemoryError anywhere, including while printing).

## 11. Order of refusal (changes to v3 §9.13)

Before anything: X002. Per statement: as v3, then W1/W2 (§4.3) after the value and after check 2;
R014 when a formed statement's lines are made; R011 when the program bound is crossed; R012 at the charge
that crosses it; then the program-wide S012 pass.

## Amendment (Phase E5, 25 Oct 2026): the witness covers BIDS statements

(History: §4.4 items 9-11 now state what is built, 26 Oct 2026.)

- 4.4 item 7: a dataset name's candidates are made-up datasets built from the statement's own
  subject, task, run, acq and rec labels, participants columns, trial types and cutoffs: the
  participants table takes the table candidates of its slot (participant_id added, the
  statement's labels first), and each named recording in turn takes events-table candidates,
  RepetitionTimes and volume counts. Each must pass the whole 1.0.1 reader to count.
- W2 is judged at the highest enclosing value that still answers without the part (the
  statement's answer when it can be; one level down when the statement without the part is not
  well formed); `widen()` too (v4-fixes 07; it was judged on its own value, which let a widen no
  input can make matter form), with candidates at each cutoff less the widenings. A refusal is no
  answer, except a value refusal (V...), which is an outcome; a reader's refusal of a candidate
  (T, J, I, B, M, F) means it is not a readable input, so none of its sub-answers count (v4-fixes 06). (Before, W2 compared the part's own value, which let a
  condition idle inside a nested where() form, and counted a refusal on one side as a change.)
- The kernel's hand S008/S011 rules are gone, except three facts about bytes: a literal that
  is not UTF-8 (no cell or JSON key holds it) and a tolerance of 0.
