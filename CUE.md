# Reality: live demo cue card (patsak127)

**Open with.** "We're moving upward in science and engineering, just on a spiral staircase. We erase a false belief and leave its foundation standing. Ptolemy wasn't an idiot—from where he stood, Earth at the center was completely reasonable. His mistake was taking a feature of his perspective for a feature of reality. Reality makes you write down where you're standing, keeps the real observations around intentionally, and cascades automatically when a foundation falls."

Run: `python3 run_demo.py` (Enter between steps; `--no-pause` runs straight through and exits 1 if any program line differs).

## What each step shows

1. **"Is the Earth at the center?"** `REFUSED rule=F1`, exit 3. No bytes, no measure: not a question here.
2. **"Is consciousness special?"** Refused the same way. Say plainly: Reality does not answer this. It says what an answer would have to name. The parallel to Ptolemy is a hunch, not a result.
3. **The right shape about the wrong thing.** `predicate column-equals center Earth` on the Earth table: `REFUSED rule=F8 file-1=no-such-column`. The data has no `center`; it has `seen_from`.
4. **What Ptolemy actually saw, pinned down (Mars, NASA/JPL Horizons 2024–25).**
   - Seen from Earth (`motion = retrograde`, ≥ 1 day in 10): **HOLDS, 79 of 730** (2024-Dec-07 to 2025-Feb-23).
   - Seen from the Sun: **DOES-NOT-HOLD, 0 of 730**.
   - `share-agrees` across both: **DOES-NOT-HOLD, 79/730 vs 0/730**.
   Adoption uses a throwaway key (`REALITY-TEST-KEY-NOT-PATSAK`).
5. **One byte changed** (`retrograde` → `petrograde`): `NOT-CHECKED file-1=other-bytes`, exit 2.
6. **Foundations + Jupiter.** `earth-frame`, `sun-frame`, and `epicycles` resting on `earth-frame`, each signed (`reality-foundation-1`); signed tags bind tables to foundations. Jupiter from Earth (≥ 1 day in 5): **HOLDS, 167 of 730**.
7. **Knock down `earth-frame` via Mars → Jupiter cascades.**
   - `undermine` recounts the Earth-vs-Sun Mars comparison live on the spot (`79/730` vs `0/730`, `DOES-NOT-HOLD`), and the signer names side 1 (`earth-frame`).
   - `impact` lists `epicycles` and three adopted measures (including **Jupiter**, never fetched from the Sun).
   - Re-checking Jupiter: **HOLDS-UNDERMINED, still 167/730**, exit 12. Real observation preserved; foundation flagged.
8. **The same spiral staircase today (25 evaluated language models, 2B to o1-preview, Mirzadeh et al. ICLR 2025).**
   - Static `GSM8K (100)`: **12/25** clear 80% (`HOLDS`), and **8/21** open-weights models on `open-weights-math-readiness` (resting on `static-gsm8k-frame`) clear 80% (`HOLDS`).
   - `GSM-Symbolic-NoOp` (50 symbolic instantiations per template + 1 irrelevant sentence): **0/25** clear 80% (`DOES-NOT-HOLD`, `12/25` vs `0/25`).
   - Undermine `static-gsm8k-frame` (live recount) → `impact` catches `open-weights-math-readiness`, and re-checking the open-weights claim returns **HOLDS-UNDERMINED, 8/21**, exit 12.

## Say the limits before they do

- **Closed** means every recorded question is well-formed and can be asked of its named bytes—not that it's a good question.
- **Explicit and signed, not pre-registration:** bars, names, and tags in this demo were chosen after seeing the data; binding a measure before data exists is not built yet.
- **Signer chooses the side:** `share-agrees` only proves the two frames disagree; the same witness would let a key holder knock down the other side.
- **Plain-file log:** deleting an undermine line silently un-flags dependents; there is no hash chain and no claim of tamper-evidence.
