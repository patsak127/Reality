# Review of Reality v2 (commit e46b604): findings index

Reviewer: Claude Opus 5.5, 24 Oct 2026. Machine: Windows 11, Python 3.14.7 (`.venv`). Lean is not
installed, so `metatheory/Scope.lean` was reviewed by reading only. `tests_pc/` was not run (no
real BOLD data here).

Every program is in `findings/` next to its write-up. `findings/gen/run_all.sh` re-runs all of them
and rewrites the `NN.out` files that the write-ups quote. Some need the fabricated complete copy at
`scratch/cmp`; the command that builds it is in the script's header.

## Summary table (ordered by severity)

| # | finding | category | spec clause | severity | confidence |
|---|---|---|---|---|---|
| 01 | [A subset manifest makes the box copy conform; N17's text forms](01-subset-manifest-conforms.md) | **hit** | reading rules, whole-dataset conformance; N17 | high | high (repro) / medium-high (class) |
| 02 | [`"@<hash>"` in a literal prints as `#1`: one printed claim, two values](02-hash-in-literal-prints-as-file.md) | **hit** | items 6, 2; §10.1 printed identity | high | high |
| 04 | [`let` chains grow exponentially, uncounted; memory decides the verdict](04-let-doubling-memory-decides-verdict.md) | **hit** | item 4 | high | high |
| 09 | [`difference()` subtracts onsets from two reference events](09-onsets-from-two-frames.md) | **hit** | item 1 (frame, reference event) | medium-high | medium-high |
| 05 | [A 5 000-digit cell: PYTHONINTMAXSTRDIGITS decides the verdict](05-int-max-str-digits-decides-verdict.md) | **hit** (+ X001 bug) | item 4 | medium | high |
| 10 | [A refused statement, or `--root` vs `--files`, changes a later verdict](10-refused-statement-changes-later-verdict.md) | **hit** (+ bug) | item 4 | medium | medium |
| 11 | [Non-ASCII lookalikes pass: `key("S1")` with a Cyrillic "Ѕ1" in the key column](11-non-ascii-lookalikes-pass.md) | **hit** (key); accuracy issue (eq, headers) | §10.3, N12 (v1 #8) | medium | medium |
| 03 | [Manifest sizes and extra-file hashes are never checked](03-manifest-sizes-and-extra-hashes-unchecked.md) | **hit** | item 5, "written value that differs from the file"; floor | medium | medium |
| 07 | [Quadratic, uncounted lookalike scan](07-quadratic-lookalike-scan.md) | bug (slow) | item 4 (speed), SPEC §2.12 | medium | high |
| 12 | [NIfTI-2 BOLD with a float64 TR always fails B09](12-nifti2-tr-never-consistent.md) | must-form refused | §10.2 C, BIDS §8.4 | medium | high |
| 16 | [IntendedFor, SliceTiming and events-within-run unchecked; fabricated copy contradicts itself](16-unchecked-machine-checkable-rules.md) | judgement call / design | §10.2 C; false vs nonsense | medium | medium |
| 17 | [Check 2 for BIDS values is written by the sort code](17-check2-for-bids-is-written-by-the-sort-code.md) | docs overclaim / design | §1 floor, "independent check" | medium | high |
| 18 | [`reality2_ref` disagrees on `share … is` and row 0; untested](18-reference-implementation-gaps.md) | docs overclaim / bug | README verification table | medium | high |
| 14 | [Idle parts form: `difference(x, x)`, `tolerance = 0`, implied/contradictory conditions](14-idle-parts-form.md) | **hit** | item 1 | low-medium | medium |
| 06 | [Output bytes depend on the console encoding; suite fails on Windows](06-output-bytes-depend-on-locale.md) | bug | item 4 (locale) | low-medium | high |
| 15 | [TSV: CR/BOM refused, U+2028 / form feed / quotes accepted](15-tsv-second-readings-not-refused.md) | design (accuracy) | §10.2; SPEC §2.6 | low-medium | high |
| 08 | [Renaming a name across the 1 MB byte bound flips the verdict](08-renaming-crosses-the-byte-bound.md) | **hit** | item 3 | low | high |
| 13 | [Deep JSON reaches X001 (RecursionError)](13-deep-json-internal-error.md) | bug | SPEC §2.13 | low | high |

**Number of hits: 10** (01, 02, 03, 04, 05, 08, 09, 10, 11, 14). Under the protocol (§5) each one is a
language failure, so **v2 does not pass**. Grouped by cause:

- **Scope chosen outside the reader (01, 03).** The manifest is an author-written file that the
  language reads as structure, and it is only partly checked.
- **Printed form not separated from data (02).**
- **Bounds that count the wrong thing (04, 05, 08; 07 is the same cause without a verdict
  change).** Bytes and table steps are counted, but not work, memory, digits or names.
- **Types too coarse for what the standard defines (09, 11, 14).** A unit without a frame, an ASCII-only
  skeleton, and idle-part detection for one pattern only.
- **Stateful store (10).**

My own ranking: 01, 02 and 04 are clear and serious; 05, 08 and 09 are clear; 03, 10, 11 and 14
are hits under the spec's letter that reasonable people could argue about. My confidence for each is
in its file.

## (b) Must-form texts

On the fabricated complete copy (`tests/bidsfix.py`) and the box copy I re-ran F1, F2, F3, F8, F11,
F12, N3b, N14b and N16b (`tools/acceptance_table.py`, plus my own runs). All form, and their sorts
are what §5 asks for:

- F1 and N14b are `Count[Rows[Participants[BIDS-1.0.1[#1] from #2] where ExtraCell col k = …]]`.
- F2 is the exact share 54/108.
- F3 is `EventOnset[BOLDRecording[…: #2], #3 row 1] is recorded as 4.071 s`, and it names the BOLD
  file by hash.
- F11 is "recorded as 1 s", taken from the root sidecar.
- F12 and N16b are plain-TSV only, with no unit.

Caveats:

- F3/F8/F11 form on a copy whose own files contradict each other (finding 16). They show that the
  forming path works, not that the reader would refuse an inconsistent dataset.
- The column is printed as `col 2`, not `group`. That keeps names out of the output, but a reader
  needs the file to see which column was meant.
- **Overcorrections found:**
  - every NIfTI-2 dataset with a non-dyadic TR (finding 12);
  - plain-TSV rows cannot be keyed by the most common ID shapes (`sub-001`, `4735_50GV`), because
    composite keys ("a tuple of keys", §10.3) are not implemented. Only positions are left.
  - Whether the real ds001734 conforms is still unknown (tests_pc). I checked that its root sidecar
    has the B10 fields (EchoTime, EffectiveEchoSpacing, PhaseEncodingDirection), so B10 should pass.
    B09 depends on the real headers' `xyzt_units`.

## (c) False versus nonsense

v2 uses "fabrication" as a defence in two places where the text alone shows the defect:

- **Subset manifests (01).** No content is chosen, only the scope. 108 described participants with
  no folders are visible in the text.
- **The fabricated complete copy (16).** 3-volume recordings with events at 441 s, 64 slice times for
  2 slices, and an IntendedFor that points at nothing. These are visible from the named files.

The rule "only defects that need the world are false" is right. What is missing is checks for the
defects the text can show. Mislabelling paths in a manifest (assigning sub-002's events to
`sub-001/...`) is equivalent to renaming files on disk, and I agree it is false. The manifest is the
author's statement of paths, though. The SPEC should say this explicitly, because the manifest makes
mislabelling cost nothing.

## (d) The judgement calls

| SPEC §2 | call | verdict | what I would decide |
|---|---|---|---|
| 1 | dataset named by an author-made manifest; subsets may conform | **wrong as it stands** | Selection is a reading choice, not fabrication (finding 01). Make participants rows ↔ subject folders a two-way rule, check every manifest entry (03), and print subject, recording and file counts in each BIDS sort. Printing only the number of subjects would not settle it: in finding 01 it stays 108. |
| 2 | byte literals in `eq`/`key` are part of the subject | right in principle, **badly implemented** | Keep them as subject, but keep them out of the sort's syntax (02). Apply one lookalike rule to the literal *and* to every cell of the column, non-ASCII included (11). |
| 3 | `is` is a checked assertion | right | Echo the written literal in the output, so a reader sees what was asserted, and not only what was computed. |
| 4 | keys in K; `sub-001` is not a plain key | consistent with §10.3, **overcorrects** | Implement the composite keys §10.3 already allows (`sub`, `001` as a tuple split at a fixed ASCII separator set). Otherwise most real ID columns can only be reached by position. |
| 6 | TSV refusal list = "the cases with two readings" | **inconsistent** | U+2028, NEL, FF, VT and quotes have two readings by the same argument (15). Refuse them, or drop the argument. |
| 7 | decimal syntax; `007` is 7 | right | But bound the digits in the language (05). |
| 8 | Recorded is top of the lattice; `widen` keeps Recorded | right as far as it goes | A unit is not a frame. Onsets need their reference event in the type (09). |
| 9 | BIDS: exact template, else extra; inheritance order; float32 B09; trailing bytes; `"` refused; `n/a` refused; rows without folders; unimplemented kinds refuse | mixed | **Inheritance order:** matches 1.0.1 §8.4 ("the one corresponding to a particular participant, task and run takes precedence"); right. **B09:** right for NIfTI-1, wrong for NIfTI-2 (12). **Quotes, n/a:** right. **Rows without folders:** wrong (01). **"Else extra":** too loose. A BIDS-named file in the wrong subject folder (`sub-02/func/sub-01_task-x_bold.nii`), with entities out of order, or with an upper-case extension, is silently extra rather than a failure. `phenotype/*.tsv`, which 1.0.1 §8.11 defines, is silently extra instead of B14. And `anat/` accepts any suffix as an image, not just 1.0.1's modality table. |
| 11 | conformance reads kept apart from value reads | acceptable **only if** the manifest is fully checked (03) | Then admit that check 2 for BIDS is not independent (17). |
| 14 | empty programs accepted | harmless | Print "accepted: nothing claimed", so that corpus statistics like "8 accepted" are not read as successes. |

## (e) One standard of accuracy

Places where v2 is strict in one aspect and lax in a neighbouring one:

1. **Lookalikes:** `I`/`l`/`1`, `0`/`O` and `m`/`rn` are refused; Cyrillic а/a, Ѕ/S and о/o are not,
   though the pinned UTS #39 file maps them too (11). The same applies to headers.
2. **"Two readings" in TSV:** CR and BOM refused; U+2028, FF and quotes accepted. The BIDS TSV refuses
   `"`, the plain TSV does not (15).
3. **JSON:** duplicate keys are refused as two readings, but lookalike keys (`RepetitionTime` next to
   `RepetitionTlme`) are not. TSV headers that look alike are refused (K002).
4. **Idle parts:** a condition written twice is refused (S008); `difference(x, x)`, `tolerance = 0`,
   and implied or contradictory conditions are not (14).
5. **Bounds:** bytes read and table rows are counted exactly. `let` re-evaluation, sort building,
   lookalike scans, digits and memory are not counted at all (04, 05, 07).
6. **The manifest:** hashes are checked for files that are read; sizes are never checked, and extra
   files not at all (03).
7. **Units versus frames:** units are checked strictly (U001/U002); the reference event of a time in
   seconds is not checked at all (09).
8. **BIDS cross-file rules:** TR against pixdim[4] and SliceEncodingDirection against slice_dim are
   checked; IntendedFor targets, SliceTiming length and events-within-run are not (16).
9. **Tolerance in B09:** byte-exact everywhere else, but "nearest float32" here. That is principled
   for float32 headers, but it is applied to float64 headers as well (12).
10. **Docs:** README says "a verdict never depends on a path, the order of supply" (false, 10); "a file
    that changes while it is being read (F002)" (true only for whole-file text reads: `bytes()`,
    `size()` and the NIfTI reader read from the path without re-hashing); "X001 never occurs" (false,
    05 and 13).

## (f) Verification claims

**Lean (`metatheory/Scope.lean`, read, not compiled).** The proofs look sound for what they state,
but they show less than the README suggests:

- `trace_eq_sort` holds by construction. The model builds the trace and the sort side by side
  (`[h]`, `t ++ t'`), so it proves that the model is internally consistent, and nothing about
  `kernel.py`. There, the trace and the sort are written by separate code that can disagree (the
  regex in 02), or written together by hand (17).
- `scope` assumes readers that are pure functions of one file's content. Python's BIDS values depend
  on the manifest and on gate reads of every file. The model has no datasets, manifests or gates.
- `check_rename` covers a model with no parser and no bounds. In Python, the byte bound breaks it (08).
- **Semantic gap:** the model binds `let` to its *meaning* once (`bind env n (some m)`), while Python
  stores the *expression* and re-evaluates it at every use (`kernel.py:658`, `:151`). Finding 04
  exists because of this gap, and so does finding 10's history dependence.
- The model's codes `C003` and `V009` do not exist in the Python code. The model's traces keep
  duplicates; Python's do not.
- `exceeds_sound` and `below_sound` are one-line order lemmas. They are correct, and not where the
  risk is.
- I could not confirm that Lean 4.35.0 is a real release, or that `Std.lt_of_lt_of_le` exists for
  `Rat` in it.

**Second implementation.** It covers what it says (plain TSV). But the differential test never uses
`is` or row positions below 1, and on both the reference is wrong (18). It does not compare printed
forms, `difference`, `size` or `bytes`. It shares the ASCII-only skeleton and the unbounded `int()`
parse with the checker. 16 000 agreements show that two codings of the same reading agree. They
cannot show that the reading is right.

**Fuzzers.** The mutation fuzzer mutates programs only. Every X001 I reached (05, 13) comes from file
contents. The renaming fuzzer stays far from the bounds (08). Tests 11 and 12 monkeypatch the bounds
down, which shows that the bound code exists, not that work is bounded (04, 07).

**Other.** The suite fails 1 of 187 tests on Windows (06). It takes about 120 s here, against "about
11 s" in the README, which is not a problem. The README's line counts (1 873) are exact.
`tools/corpus.py` was not run (the v1 corpus is not here).

## (g) The 22 v1 findings

| v1 # | status in v2 | came back elsewhere? |
|---|---|---|
| 1 hash seed | holds (I re-ran 3 seeds: identical bytes) | determinism now leaks through the environment (05), the console encoding (06) and memory (04) |
| 2 renaming | holds inside the language | the byte bound (08) |
| 3 support under-reported | holds for TSV/bytes | for BIDS, the trace is written by hand (17); the manifest's unchecked fields (03) |
| 4 ratio cast | no form | — |
| 5 aliases, two decisions | holds | one printed claim with two values via `@hash` literals (02) |
| 6 one row, many individuals | no form | — |
| 7 other row or column | holds | — |
| 8 lookalike keys | fixed for ASCII | **returns** through non-ASCII cells in a key column (11), the very U+2011 mechanism |
| 9 stipulated test | holds (no tests yet) | — |
| 10 exclusion without `not` | holds (`ne` over the table) | — |
| 11 per-test work | moved | uncounted quadratic scan (07); exponential `let` (04) |
| 12 memory | moved | bytes are bounded, memory is not (04) |
| 13 internal error | moved | X001 from file contents (05, 13) |
| 14 `one` | no form | — |
| 15 idle respect | partly | only the duplicate condition is refused (14) |
| 16 `ref doi` | no form | — |
| 17 slots and junk arguments | holds | — |
| 18 refused statement leaves something | holds for names | the store's cache (10) |
| 19 duplicate headers, empty key | holds | — |
| 20 overcorrection (share) | share forms | new overcorrections: NIfTI-2 (12), hyphenated keys |
| 21 decision cells | holds (bytes only) | — |
| 22 anchors from rows | no frames | the frame problem returns through onsets (09) |

## What I checked that held up

- All N items (N1–N17, N8 via `tests/old`) are refused with the codes SPEC §4 lists, and the F/N table
  reproduces exactly.
- With the full manifest, the box copy refuses with B00 (648 failures: B07 ×432, B12 ×216).
- Output is identical under PYTHONHASHSEED 0, 1 and 99, and under a different order of `--files` and
  `--root`.
- Program names never appear in the output; files are printed as `#k` plus the full hash.
- The UTS #39 18.0.0 ASCII restriction has exactly the four entries claimed. `keys.py`'s pinned hash
  matches `context/sources/confusables.txt`.
- Unknown and empty slots (S004/S005), a written value in a value position (S001), unit mismatches
  (U001/U002), straddling intervals (V006), and `is` mismatches (V001) are all refused as documented.
- JSON duplicate keys, NaN and lone surrogates are refused. Sessions, dwi, beh, physio and fieldmap
  cases 2–4 are refused with B14.
- Inheritance follows 1.0.1 §8.4's precedence sentence.
- A one-line refused `let` gives N003 downstream, and a refused re-declaration keeps the first binding.

## Smaller notes (not filed)

- TOCTOU: `bytes()`, `size()` and NIfTI reads open the path again without re-hashing (README's F002
  claim is narrower than stated).
- `--root` joins manifest paths with `os.path.join`. On Windows a segment like `C:x` escapes the root.
  It is harmless, because the bytes are hash-checked.
- With more than one program, the output header `== <path>` puts a path into the output.
- R001 is printed as `item 1` on `line 0`. A BOM in JSON gets T001's TSV message ("part of the first
  cell").
