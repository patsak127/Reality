# Reality: stop running up spiral staircases (patsak127)

## The problem

I want humans to stop running up spiral staircases. This is what holds science, engineering, and research back.

Human ingenuity anchored in misconception led to me writing this in the first place—that part isn't the problem, and should probably be kept around intentionally. We *are* moving upwards, just on a spiral staircase. We waste decades repeating the same mistakes because we confuse erasing a false belief with erasing its foundation.

Ptolemy didn't put Earth at the center because he was an idiot. From where he stood, it was completely reasonable: Mars visibly stops and moves backward against the stars for weeks before going forward again. His error was not bad observation—it was mistaking a feature of his perspective for a fundamental feature of reality. We threw out the geocentric model; we didn't throw out the habit that produced it.

My hunch is that we are doing it again. Today it feels completely reasonable to treat human consciousness as something fundamentally special, or to take free will as given. Those may not age well, for the same reason: a feature of how things look from inside us, read as a feature of the world. That is a hunch, not something Reality proves. What Reality does is narrower and already built.

## What Reality does today

Reality is a small, closed epistemic engine (`reality.py`, 691 lines, Python standard library + OpenSSH).

1. **Perspective can't hide inside prose.** Unframed English questions (`"Is the Earth at the center?"`, `"Is consciousness special?"`) are refused (`rule=F1`). Every question must name exact data bytes (by SHA-256) and an exact rational measure.
2. **Foundations are explicit, signed commitments.** Signed `foundation` records can `rests-on` earlier foundations (forming an acyclic graph), and signed `tag` records state which foundation a table rests on.
3. **When a foundation falls, everything resting on it cascades—without erasing the observations.** Knocking down a foundation (`undermine`) requires an adopted two-table comparison (`share-agrees`) recounted live on its named bytes and returning `DOES-NOT-HOLD`. Running `impact` surfaces every dependent foundation and adopted claim. Re-checking a holding claim returns `HOLDS-UNDERMINED` (exit 12 instead of 0) with its exact local counts kept; a failing claim stays `DOES-NOT-HOLD`, now carrying `undermined-foundation=`.

Both cases run locally in one command (`python3 run_demo.py --no-pause`) on public primary data:

- **Ptolemy (NASA/JPL Horizons, 2024–25, Mars & Jupiter):** Mars seen from Earth moves retrograde 79/730 days (`HOLDS`); Jupiter seen from Earth, tagged on `epicycles` resting on `earth-frame`, moves retrograde 167/730 days (`HOLDS`). Mars seen from the Sun moves retrograde 0/730 days (`DOES-NOT-HOLD`). The Earth-vs-Sun comparison fails (`79/730` vs `0/730`). Knocking down `earth-frame` with that live-recounted witness immediately flags **Jupiter** via `impact`—without ever fetching Jupiter from the Sun—and re-checking Jupiter returns `HOLDS-UNDERMINED` (`167/730` kept, exit 12).
- **Modern language-model evals (Mirzadeh et al., Apple, ICLR 2025, `arXiv:2410.05229v1` Table 1):** Across 25 evaluated models (2B to `o1-preview`), 12/25 clear 80% on static `GSM8K (100)` (`HOLDS`), and 8/21 open-weights models tagged on `open-weights-math-readiness` (resting on `static-gsm8k-frame`) clear 80% (`HOLDS`). On `GSM-Symbolic-NoOp` (50 symbolic instantiations per template with one mathematically irrelevant sentence added), **0/25** clear 80% (`DOES-NOT-HOLD`, `12/25` vs `0/25`). Knocking down `static-gsm8k-frame` cascades directly to the open-weights readiness claim (`HOLDS-UNDERMINED`, `8/21` kept, exit 12).

## What is built vs. what is next

**Built and runnable today:**
- `reality.py` (691 lines, stdlib Python + `ssh-keygen`), 63 passing tests (`test_reality.py`), cross-platform demo (`run_demo.py`), full technical spec (`SPEC.md`), and raw sources with SHA-256 checksums (`SOURCES.md`).
- Closed input/output grammar, exact rational arithmetic, separate OpenSSH signing namespaces (`reality-adopt-1`, `reality-foundation-1`, `reality-undermine-1`), live-recounted witness checks, transitive `impact` queries, and `HOLDS-UNDERMINED`.

**Honest limits today:**
- **The signer decides which side falls.** A failed `share-agrees` proves the two tables differ; the signer explicitly names which side to knock down. Foundations and tags are signed commitments, not verified against the outside world.
- **Explicit and signed, not pre-registration.** Today you can see the data before signing—bars, names, and tags in the demo were set after seeing the tables. Binding a measure before data exists is not built yet.
- **Plain-file log.** The log is an unprotected plain file (deleting a line is not detected; signed lines are re-verified on every read).

## What backing buys

I'm not owed anything—I just believe this is a missing layer under how science and engineering handle assumptions. Backing buys focused time to:
1. Add pre-registration so claims bind both their foundation and their bar *before* running an experiment or eval.
2. Build direct adapters for real evaluation harnesses and empirical pipelines (moving beyond single-column exact equality).
3. Get real external adoption on live benchmarks and datasets.
