# Reality v2: review findings (index)

Reviewer: Claude (Opus 5.5), 24 Oct 2026. Code: `src\reality2\` and `src\reality2_ref\` of branch
`v2` at `e46b6046…`, as copied into this folder. Machine: Windows 11, CPython 3.14.7 (the
`.venv` interpreter and its base), console code page cp1252. Lean is not installed here, so
`metatheory\Scope.lean` was reviewed by reading only.

**Result against the acceptance test (spec §5): 12 hits, so v2 does not pass** (pass = zero hits).
Besides the hits: 8 bugs, 1 overcorrection (must-form refused), 3 documentation overclaims,
3 design issues and 1 judgement-call finding: 28 findings in all. Several hits are cheap to fix;
three are about the language, not the code (02/05, 03, 08).

## How to reproduce

From this folder, with the commands written in each finding (`set PYTHONPATH=src`, then
`python -m reality2 check …`). I also set `PYTHONIOENCODING=utf-8` for every run, only so that the
`§` in refusal messages is written the same way whether output goes to a console or a file; finding
07 shows what happens without it. On the Linux box the commands are the same with `/`
(`PYTHONPATH=src python3 -m reality2 check findings/…`).

- `python -I findings\build.py` writes every supplied file, made-up dataset (`NN-ds…\`), manifest
  (`NN-m…\<sha256>.manifest`) and program (`NN-*.rl`); it is deterministic, so the hashes in the
  programs match. `findings\13-gen.py N` and `findings\14-gen.py N` make the large inputs.
- `python -I findings\run_all.py [NN …]` reruns every command and writes the exact outputs to
  `findings\NN-output.txt` (lines in square brackets are my runner's exit code, wall time and peak
  memory, not the checker's). It uses `scratch\runlimit.py` for the 60 s stop, the memory
  measurement (Windows `GetProcessMemoryInfo`) and the memory cap of finding 06 (a Windows Job
  Object; on Linux use `prlimit --as` or `ulimit -v`).
- Findings 18, 20 and 25 are white-box scripts (`findings\NN-*.py`, run with `python -I`); their
  outputs are in `NN-output-script.txt` / `25-output.txt`.
- Everything made up for the findings is a test fixture, not study data. The box copy
  (`tests\data\ds001734-box\`) is used unchanged; its manifest reproduces the pinned
  `b6850de7…` on Windows.

## Summary, most severe first

| # | finding | category | spec clause | severity | confidence |
|---|---|---|---|---|---|
| [01](01-int-digit-limit.md) | `PYTHONINTMAXSTRDIGITS` decides the verdict: a long decimal is X001 or formed, a long JSON number makes a dataset non-conformant or conformant, a long literal is a traceback or accepted | **hit** (item 4) | §1 item 4 | high | high |
| [02](02-n17-zero-subject-dataset.md) | N17 forms: a manifest of the box copy's 8 root files (no subject) conforms, and F1/F2/N14b's texts form from the box copy's own bytes | **hit** (must-not-form N17; whole-dataset conformance) | §1 reading rules, §5 N17 | high | high (forms); medium-high (hit) |
| [03](03-onset-difference-across-recordings.md) | `difference` subtracts onsets measured from different recordings' first volumes, and `exceeds` on it holds; a duration minus a time point forms too | **hit** (item 1: reference event) | §1 item 1, §2 table | high | high |
| [04](04-let-chain-exponential.md) | a 735-byte let-chain runs 25–36 s and prints a 52-million-character sort; each two lines ×4; no steps counted | bug (slow) | §1 item 4, SPEC §2.12 | high | high |
| [05](05-manifest-selection.md) | the author's manifest decides which subjects and runs "the whole dataset" has; omissions that leave traces in the text still conform | judgement call (§2 item 1) | §1 fabrication, reading rules | high | high (facts) |
| [06](06-memory-decides-verdict.md) | the same 1 MB claim forms with enough memory and is X001 under a 30 MB cap; the bounds admit inputs needing ~1.3–10 GB | **hit** (item 4: memory) | §1 item 4, §5 | medium | high |
| [07](07-console-encoding.md) | with a cp1252 or ASCII stdout a refusal message crashes the printer and later formed claims are lost; `§` bytes differ by locale (the suite's own test_01 fails here) | **hit** (item 4: locale) | §1 item 4 | medium | high |
| [08](08-idle-where-conditions.md) | idle conditions form (`eq A` + `ne B`; literals no cell can hold; `eq A` + `ne A`); only the literal repeat is refused (S008) | **hit** (item 1: does not bear) | §1 item 1 | medium | high |
| [09](09-duplicate-onset-column.md) | an events file with two `onset` columns conforms; `onset()` forms while v2's own TSV rule calls the name ambiguous in the same file | **hit** (item 1: a column name that occurs twice) | §1 item 1, §3 | medium | high / medium-high |
| [10](10-sidecar-precedence.md) | the TR comes from v2's same-folder "more entities wins" rule, which 1.0.1 does not state; 1.0.1's own precedence sentence gives the other value | **hit** (reading rules; item 2) | §1 reading rules | medium | high / medium-high |
| [11](11-run-index-two-recordings.md) | `run-1` and `run-01` (or run-less next to `run-1`) are two recordings with different volume counts for one run index | **hit** (items 2, 6) | §1 items 2, 6 | medium | high / medium |
| [12](12-phenotype-files-skipped.md) | `phenotype/` (1.0.1 §8.11) is skipped as extra, so a dataset that breaks §8.11 conforms ("never skipped" in SPEC) | **hit** (whole-dataset conformance) | §1, §10.2 C | medium | high |
| [13](13-where-lookalike-quadratic.md) | `where`'s lookalike check is quadratic: 709 KB takes 23–25 s, 1.49 MB passes 60 s; steps < 1 % of R002 | bug (slow) | §1 item 4 | medium | high |
| [14](14-bids-reader-quadratic.md) | the BIDS reader's checks are quadratic: 40,000 subjects (3.5 MB manifest) pass 60 s | bug (slow) | §1 item 4 | medium | high |
| [15](15-json-exponent-stall.md) | `1e60000000` in a 57-byte `dataset_description.json` stalls the reader past 60 s | bug (slow, memory) | §1 item 4 | medium | high |
| [16](16-x001-from-valid-json.md) | X001 from valid JSON (a list in `PhaseEncodingDirection`; deep nesting); one dataset is X001 for one claim and conformant for the next | bug | SPEC §2.13 | medium | high |
| [17](17-counts-and-shares-cannot-be-compared.md) | counts and shares cannot be compared or subtracted, though decimals can | must-form refused | §10.1, brief (b) | medium | high |
| [18](18-differential-is.md) | the differential test never uses `is` or compares sorts; with `is`, 51 of 1,195 claims disagree | docs overclaim | README (f) | medium | high |
| [19](19-lean-model-distance.md) | the Lean theorems hold by construction of a model that lacks the parts with defects (let semantics, bounds, BIDS, the trace as a side channel) | docs overclaim | README (f) | medium | high |
| [20](20-check2-not-independent.md) | check 2 is not independent for BIDS: a planted reader bug (wrong events file) passes it | design issue | §1 floor, §2 check 2 | medium | high |
| [21](21-rename-crosses-program-bound.md) | renaming `t` to `tt` turns an accepted 1,000,000-byte program into R001 | **hit** (item 3) | §1 item 3 | low | high |
| [22](22-manifest-unchecked-fields.md) | a manifest with false sizes and an entry whose bytes exist nowhere names the dataset of formed claims | **hit** (written value differs from the file), contestable | §1 false/nonsense, floor | low | high / medium |
| [23](23-nifti2-tr-float32.md) | consistent NIfTI-2 files fail B09 (float64 pixdim compared with a float32) | bug / overcorrection | 1.0.1 §4.1, §8.4 | low | high |
| [24](24-lookalike-scope.md) | lookalike keys are refused per literal, not per key column as §10.3 says (BIDS does it per column) | design issue | §10.3 | low | high |
| [25](25-file-changes-during-check.md) | after a supplied file changes on disk, `bytes()`/`size()` form claims about bytes the named hash does not have | bug | README F002, floor | low | high |
| [26](26-negative-denominator.md) | `is 2/-3` is not refused by P007 | bug | SPEC §3 | low | high |
| [27](27-extracell-label-missing.md) | `max`/`min`/`sum` over participants print `col k`, not `ExtraCell col k` | design issue | §2 table | low | high |
| [28](28-docs-mismatches.md) | smaller documentation mismatches (F001, names in output, `test_keys.py`, X001, …) | docs overclaim | README, SPEC | low | high |

**Hits: 12** (01, 02, 03, 06, 07, 08, 09, 10, 11, 12, 21, 22). Grouped by cause:
- *The interpreter decides the verdict* (01, 06, 07): an environment variable, the memory available,
  the console encoding. This is v1 finding 1's class (the hash seed) in three new forms.
- *The BIDS reader reads beyond or short of 1.0.1* (02, 09, 10, 11, 12): a "dataset" with no
  subject, a repeated `onset`, a precedence rule 1.0.1 lacks, run indices compared as strings, a
  1.0.1 file kind skipped.
- *Arithmetic without the reference event* (03): units are checked, frames are not.
- *Idleness checked by spelling* (08).
- *A bound that counts name bytes* (21).
- *Unchecked written values in the dataset's name* (22, the most contestable).

## (b) The must-form items

I ran each on the fabricated complete copy the tests build (`bidsfix.complete_copy`; my copy is
`scratch\fx\`) or on the box copy, and compared the printed form with §5's text.

| item | what forms | matches §5? |
|---|---|---|
| F1 | `Count[Rows[Participants[BIDS-1.0.1[#1] from #2] where ExtraCell col 2 = "equalRange"]] = 54 (Exact)` | yes: a BIDS participant set, ExtraCell, the manifest and `participants.tsv` by hash; the header name is resolved to "col 2" |
| F2 | `Share[… of Participants[…]] = 54/108 (Exact)` | yes; printed unreduced, `is 1/2` would also pass |
| F3 | `EventOnset[BOLDRecording[…, sub 001 task MGT run 01: #2], #3 row 1] is recorded as 4.071 s (Recorded[s])` | yes: both files by hash, "recorded as". "First event" means row 1, which the sort says |
| F8 | `VolumeCount[BOLDRecording[…]] = 3 (Exact)` | yes in form; 3 is the made-up image's value (README says so) |
| F11 | `RepetitionTime[BOLDRecording[…], from #3] is recorded as 1 s (Recorded[s])`, `#3` = root `task-MGT_bold.json` | yes |
| F12 | `RowCount[TSV[#1]] = 108 (Exact)` and `Count[Rows[TSV[#1] where col 2 = "equalRange"]] = 54 (Exact)` on the box copy | yes |
| N3b | `Cell[TSV[#1], row 1 (the row whose col 1 is "50GV"), col 2] = "Yes"` | yes, on a made-up two-row table (no xlsx reader) |
| N14b | `Count[Rows[Participants[…] where ExtraCell col 3 = "F"]] = 60 (Exact)` | yes |
| N16b | `Decimal[Cell[TSV[#1], row 1, col 1]] = 4.071 (Exact)` | yes |

So the must-form list forms as §5 asks, on the copies the tests use. What I could not check: the
real ds001734 run on the PC (`tests_pc`). One risk there: the reader streams every image to check
its length, counting one step per 4 KB decompressed; if the 432 BOLD files are float32 (their
gzipped sizes, 513–714 MB, suggest about 1.3 GB each decompressed), that is about 1.4 × 10^8 of
the 2 × 10^8 step budget, which leaves little room. Worth printing the step count in the PC run.

Overcorrections found: counts and shares cannot be compared or subtracted (17); consistent NIfTI-2
datasets are refused (23); a lone `magnitude1.json`, with no fieldmap image, makes B10 require the
fieldmap fields of the BOLD sidecar (seen in the probe `scratch\exp\bidsprobe\orphans.py`).
By design or scope (the author should decide which are overcorrection): no numeric selection (`age > 30`), no mean, no BIDS count of events or
recordings, no statement over all runs, units only as the standard gives them.

## (c) False versus nonsense

Where the documents lean on "false" for something the text shows:
- SPEC §2 item 1 ("The checker can't know about files that aren't listed") is right for omissions
  that leave no trace, and is used for ones that do: a dataset with no subject (02), rows without a
  folder, an `IntendedFor` naming a run that is not there (05). Those are visible in the text and so
  are nonsense if a claim forms over them.
- The spec's own fabrication sentence ("a dataset built in a standard's form in order to make a
  claim form") fits every manifest an author writes, so as worded it can absorb any selection.
  What should mark the false side is that the defect is invisible in the text, and the spec says
  that too ("No checker that sees only text can detect this"); I would delete the "in order to make
  a claim form" example or tie it to that condition.
- The manifest's sizes and extra entries are written values nobody checks (22); v2 neither checks
  them nor calls them stipulations.
- Mislabelling by manifest path (sub-002's events placed at sub-001's path) is invisible in the text
  and is correctly left to the false side.
- v2 does not use "false" as an excuse elsewhere: `is` mismatches are refused (V001), cells are
  bytes, decisions are never read as decisions, and the fabricated complete copy is called
  fabricated everywhere.

## (d) The judgement calls

| SPEC §2 | call | my verdict | what I would decide |
|---|---|---|---|
| 1 | a dataset is named by an author-made manifest; a subset can conform | **too loose** as a definition of "whole" (02, 05); fine as a naming device | refuse a dataset with no subject; make B11 symmetric (a row needs its folder); refuse `IntendedFor` paths outside the manifest; verify sizes and require every entry's bytes (22); state in README that a BIDS claim is about the listed set. Printing the subject count is a label, not a fix |
| 2 | `eq`/`key` byte strings are part of the subject, not parameters | **right**, with two holes | refuse literals no cell can hold (08); check the whole key column for lookalikes as §10.3 says (24) |
| 3 | `is` is a checked assertion | **right**: it never supplies a value, V001 refuses a mismatch, the printed value is always computed | fix P007 (26) |
| 4 | keys must be in K; `sub-001` is not a plain-TSV key | **consistent with §10.3**, mildly overcorrecting: `eq(1, "sub-001")` works where `key(1, "sub-001")` does not, so the strictness protects nothing for selections | keep for keys, as §10.3 requires |
| 6 | the TSV reader refuses CR, BOM, non-UTF-8, empty file or line, ragged rows | **right**; I found no other case with two readings. Cost: a one-column table cannot hold an empty cell | keep |
| 7 | the decimal grammar; `1.`, `+1`, `1e3`, `n/a` are not numbers; `007` is 7 | **right** as a grammar, **wrong** as implemented (01: an interpreter limit decides whether a valid decimal can be read) | parse without `int(str)` limits, with a Reality digit bound |
| 8 | Recorded is the top of the lattice; `widen` keeps Recorded | **right** | add reference events to time values (03) |
| 9 | BIDS: template match; inheritance order; float32 consistency; trailing bytes; `"` refused; `n/a` non-conformant; rows without folders allowed; unimplemented kinds refuse | mixed: template match right but incomplete (`phenotype/`, 12); **inheritance order too loose** (10); float32 right for NIfTI-1, **wrong for NIfTI-2** (23); trailing bytes, quotes, `n/a`, B14 right; **rows without folders: wrong direction** (02, 05) | order sidecars only by level, refuse same-level conflicts whatever the entity count; nearest float of the header's own type; symmetric B11; classify `phenotype/` |
| 11 | conformance reads are not the claim's support; the manifest hash in every BIDS sort names the set | **acceptable only if** the manifest is all checked bytes (22) and check 2 is independent for BIDS (20); as built, "names the whole set it was checked against" is not true | recompute the BIDS dependency set from the standard's rules; print the sidecar chain |
| 14 | empty programs are accepted | **fine**; but a program of declarations naming unsupplied bytes is also "accepted" (28) | print "accepted (no claims)" or check declared bytes exist |

## (e) One standard of accuracy

Places where v2 is strict in one aspect and lax in a neighbouring one:
1. **Idle parts:** a repeated condition is refused (S008); a condition that can never bear is not (08).
2. **Repeated column names:** refused for plain-TSV names (K002) and for `participant_id` (B11);
   accepted for BIDS `onset`/`duration` (09).
3. **Lookalike scope:** the whole column for BIDS participants (K003); only the written literal for
   plain-TSV keys and conditions (24). The ASCII table refuses even `Ai`/`Al` (through case folding),
   while a visually identical non-ASCII cell never triggers K002 in `eq` (principled by §10.3,
   because such cells are not keys and the output escapes them, but worth stating).
4. **Units versus references:** `difference` demands equal units exactly and ignores the reference
   event (03).
5. **Bounds:** bytes read are bounded exactly; time and memory are not (04, 06, 13–15).
6. **Numbers:** the decimal grammar is exact and strict, but whether a valid decimal can be read at
   all depends on an interpreter setting (01).
7. **BIDS rule coverage:** events need their BOLD (B07) but sidecars, magnitude images and
   `IntendedFor` targets need nothing; `phasediff.json` needs its images (B12) but `magnitude1.json`
   does not; BOLD sidecars need `RepetitionTime > 0` and a matching `TaskName` (B08), sbref sidecars
   do not (12-b); BIDS-defined JSON is read strictly, `phenotype/` JSON is not read (12). (The one
   asymmetry RULES-1.0.1.md justifies, that BOLD files need not have events because rest versus task
   is not in the files, is a fair call.)
8. **TR:** the header check tolerates float32 rounding (2 and 2.0000001 are both "consistent"),
   while the printed TR is exact and chosen by a precedence rule 1.0.1 does not state (10); the same
   tolerance is wrongly strict for NIfTI-2 (23).
9. **The manifest:** hashes are verified for files read; sizes and extra entries never (22).
10. **Check 2:** independent for plain-TSV reads, not for BIDS values (20).
11. **Run labels:** strict about form (digits only), lax about identity (`run-1` and `run-01`, 11).
12. **Exact values:** counts are the most exact values and the only ones that cannot cross a cutoff (17).
13. **§10.2 (ii), the mechanism the spec adopted for this guideline, is not implemented**, and SPEC
    §1 does not list it as missing. One program can use two tolerance profiles for one sort:
    `findings\e-tolerance-profiles.rl` (with `findings\24-keys.tsv`) forms both
    `Exceeds[Widened[Max[TSV[#1], col 3], tolerance = 0], c = 40] holds` and
    `Below[Widened[Max[TSV[#1], col 3], tolerance = 5], c = 50] holds`.
14. **Documents versus code:** README and SPEC state the guarantees without the exceptions the code
    has (28).

Lines that held up as principled: Recorded versus Exact (a file-level decimal is exact about bytes,
a BIDS onset is recorded about the world); standard names matched byte-exactly (as §10.3 says);
quotes literal in plain TSV but refused in BIDS TSV; the no-defaults rule (no species, no sex, units
only from the standard).

## (f) The verification claims

- **Lean** (19): the four theorems are true of a model in which the trace is defined as the sort's
  files, a `let` is a value, and there are no bounds, BIDS or manifests; they are not evidence about
  check 2, and "renaming never changes the output" is false of the checker (21). README does say
  "This is a model, not the Python code"; the overclaim is listing it under "What checks the trusted
  base". Not compiled here.
- **Second implementation** (18): it agrees with the checker on SPEC's decisions for the plain-TSV
  fragment without `is` (the suite's 16,000 claims pass here). It never runs `is` (with `is`, 51 of
  1,195 claims disagree, all from the reference's incomplete `is`), never compares sorts, and lacks
  `difference`, `size` and `bytes`. It cannot see spec-level gaps (08, 24), by construction.
- **Check 2** (20): catches a computation that forgets to name a file it read (the suite's test_03);
  cannot catch a BIDS reader that picks the wrong file.
- **Mismatches and failures found:** wrong answers (25, under concurrent change), crashes and
  tracebacks (01c, 07), X001 from valid inputs (01, 06, 16), non-deterministic verdicts across
  environments (01, 06, 07) and across call depths (16), slow or memory-heavy inputs (04, 13, 14, 15,
  06), and kernel/reference disagreements (18). The rest are in 28.

## (g) The v1 findings

| v1 # | v1 finding | in v2 |
|---|---|---|
| 1 | verdict depends on `PYTHONHASHSEED` | fixed for the hash seed (my probes: identical output for 4 seeds each); **the class came back**: `PYTHONINTMAXSTRDIGITS` (01), memory (06), the console encoding (07) |
| 2 | renaming flips the verdict | fixed in the language (no output depends on a name below the bound); **came back** at the byte bound (21) |
| 3 | support under-reported | fixed for plain TSV (check 2 refuses an unnamed read); for BIDS the support is the whole manifest, which over-reports, but check 2 there is not independent (20) and the manifest is not all checked bytes (22) |
| 4 | `ratio` casts kinds | no kinds in v2; **moved**: `difference` combines time values of different references, checking only the unit (03) |
| 5 | aliases give one test two decisions | fixed (values are computed); a related form: one run index, two recordings, two answers (11) |
| 6 | two individuals from one row | no form (P008); BIDS participants from `participants.tsv` |
| 7 | observation reads another row or column | fixed: cells by position or unique key, printed in the sort |
| 8 | lookalike keys | fixed for keys read with `key()` against the written key; the column-wide rule of §10.3 is not implemented for plain TSV (24) |
| 9 | stipulated test | no form (no tests in v2); cutoffs and tolerances are printed parameters |
| 10 | exclusion without `not` | fixed in the sense asked (`ne` ranges over the table's rows); the spelling-based check came back as S008 (08) |
| 11 | slow tests outside the step bound | **came back**: 04, 13, 14, 15 |
| 12 | memory | **came back**: bytes are bounded, memory is not (06) |
| 13 | internal error reachable | **came back**: X001 (01, 06, 16) and tracebacks (01c, 07) |
| 14 | `one` one level up | no form (no unit algebra) |
| 15 | a respect that ignores its arguments | **came back** as idle conditions (08) |
| 16 | `ref doi "TBD"` | no form (P008, P003) |
| 17 | df, permutations, junk arguments | fixed (S004, S005; no data slots) |
| 18 | refused re-declaration overwrites | fixed (`test_18` passes; first binding kept) |
| 19 | duplicate headers, empty key | fixed for plain TSV; **came back** in the BIDS events reader (09) |
| 20 | overcorrections (share of a group) | fixed for shares (F2); new overcorrections: 17, 23 |
| 21 | "significant" from a "No" cell | no form (cells are bytes) |
| 22 | an origin from any row | no form (no frames); the reference problem reappears for onsets (03) |

In the sense of N12 ("the v1 findings that formed, rewritten in the new syntax"), 08 is finding 15
rewritten, 09 is finding 19 moved into the BIDS reader, and 21 is finding 2 at a bound.

## What I checked that held up

- Determinism across `PYTHONHASHSEED` (four seeds on each of four of my BIDS and TSV probes;
  identical bytes).
- Renaming below the byte bound: the suite's rename fuzzer passes, and no formed line contains a name.
- No stated values: S001 for every literal outside a slot, position or `is`; `is` never supplies a
  value; unknown, repeated and empty slots refused (S004, S005).
- The key alphabet and lookalike table: the pinned file's SHA-256 matches, and its ASCII
  letter/digit entries are exactly the four in `keys.py`; v2's `rn → m` skeleton gives the same
  equivalence as UTS #39's `m → rn` for these entries.
- The plain-TSV reader's refusals (T001–T004), exact decimals, exact JSON numbers, strict JSON
  (duplicate keys, NaN, lone surrogates), the manifest grammar (sorted, unique, no `..`, no
  file/folder clash), interval propagation and V006.
- The acceptance table reproduces row for row; all 64 old programs are refused; the corpus tool needs
  `../v1`, which is not here, so I did not run it.
- The BIDS reader's pinned version (B01, B02), no species or sex sort, ExtraCell for columns
  1.0.1 does not define (in `where` and `extra`; not in `max`/`min`/`sum`, 27), events need BOLD (B07), TR and TaskName (B08), TR versus pixdim for NIfTI-1
  (B09), fieldmap case 1 from `phasediff` (B12), B14 for sessions, scans, dwi, beh, physio, stim and
  fieldmap cases 2–4, same-rank conflicts (B15), lookalike subject and task labels (K003), and the
  check 2 refusals C001/C002.
- Trusted-base size (1,873 lines; 1,612 without blank and comment lines) and the test count (187).
- The box manifest is byte-identical across Windows and the pinned Linux value.
