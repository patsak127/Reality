# Reality

Reality (https://github.com/patsak127/Reality) is a 691-line checker language, serving as the foundation to a future solution to several epistemic problems that hold humanity back. It doesn't accept plain English, instead using the floor we have, bytes. A foundation cannot be thrown out on opinion. The checker needs a conflict between two frames on real data. When it knocks down a foundation, Reality finds everything built on it. The old measurements aren't deleted, but merely marked as undermined (HOLDS-UNDERMINED). reality.py doesn't output English, every answer / failure mode comes from a fixed output language and Reality is silent by default.

The repo has two demos with no mismatches. Demo 1 uses NASA/JPL data, which knocks down the Earth foundation when comparing Mars seen from Earth vs. the Sun. It marks Jupiter's Earth observation as undermined, without checking Jupiter seen from the Sun. Demo 2 uses data from Apple's ICLR 2025 GSM-Symbolic paper. It knocks down the static GSM8K foundation and flags a claim about open-weights models built on it. Out of 25 models, 12 clear 80% on standard GSM8K. When an irrelevant sentence is added, 0 out of 25 clear.

Why build this? The spiral staircase. Ptolemy hardly was an idiot. He was certain of Earth as the center, because it was the reasonable thing for him to believe. We have a tendency to mistake features of our perception for fundamental features of reality. We have progressed since then, but up a spiral staircase. Instead of making steady progress, we keep having to overcome problems we have already overcome because we mistake the replacement of a false belief with the replacement of the foundation we built it on.

Today, AI grows up with this flaw, as we continue feeding it human language while treating it as if it were fed "objective facts." As AI-assisted research drives up the volume of published papers and benchmarks, it isn't serious to expect human prose review to keep up. Longer term, I see a world in which AGI will be trained on a yet-to-be-invented form of information. Let's call it "real data." Reality, a language built on mathematics instead of describing mathematics, could be humanity's and AGI's window to it.

---

## Quickstart

Needs Python 3.10+ (standard library only) and OpenSSH (`ssh-keygen`). Works on Windows, macOS, and Linux. Writes only into a fresh temporary folder.

```bash
# Run the interactive two-case demo (press Enter between steps)
python3 run_demo.py
# Or on Linux/macOS/WSL/Git Bash:
bash run-demo.sh
# Straight through without pausing (exits 0 iff every output line matches expected):
python3 run_demo.py --no-pause

# Run the full test suite (63 tests)
python3 -m unittest test_reality
```

On Windows, use `py` or `python` if `python3` is not on your PATH. If you would rather read a saved run first, see `demo-output.txt`.

---

## What the demo shows

Plain English is refused (`rule=F1`). Asking `"Is the Earth at the center?"` or `"Is consciousness special?"` is rejected—neither names exact bytes nor a countable measure.

Ptolemy (NASA/JPL Horizons, Mars & Jupiter, 2024–25).

Mars seen from Earth moves backward (`retrograde`) on `79/730` days (`HOLDS`, ≥ 1 in 10); seen from the Sun, `0/730` (`DOES-NOT-HOLD`). The two-frame comparison (`share-agrees`) returns `DOES-NOT-HOLD` (`79/730` vs `0/730`).

Jupiter seen from Earth—tagged on an `epicycles` foundation resting on `earth-frame`—moves backward on `167/730` days (`HOLDS`, ≥ 1 in 5).

Knocking down `earth-frame` (`undermine`) recounts the Earth-vs-Sun Mars comparison live on its named bytes and records the side the signer named (`side=1`). Running `impact` catches `epicycles` and Jupiter automatically—without ever fetching Jupiter from the Sun. Re-checking Jupiter returns `HOLDS-UNDERMINED` (exit `12`), preserving its exact `167/730` count.

Modern language-model evaluations (Mirzadeh et al., Apple, ICLR 2025, `arXiv:2410.05229v1` Table 1).

Across 25 evaluated models (2B to `o1-preview`), `12/25` clear 80% on static `GSM8K (100)` (`HOLDS`, ≥ 2 in 5), and `8/21` open-weights models tagged on `open-weights-math-readiness` (resting on `static-gsm8k-frame`) clear 80% (`HOLDS`, ≥ 1 in 3).

On `GSM-Symbolic-NoOp` (mean across 50 symbolic instantiations per template with one mathematically irrelevant sentence added), `0/25` clear 80% (`DOES-NOT-HOLD`, `12/25` vs `0/25`).

Knocking down `static-gsm8k-frame` with that live-recounted comparison cascades directly to the downstream open-weights readiness claim (`HOLDS-UNDERMINED`, `8/21` kept, exit `12`).

Byte integrity. Changing a single byte in the Earth table (`retrograde` → `petrograde`) produces `NOT-CHECKED file-1=other-bytes` (exit `2`)—no verdict at all.

---

## Outcomes & exit codes

Every answer is one closed line `outcome=KIND ...` (`impact` follows with one `DEPENDS` line per dependent), and the process exit code depends only on the first line's kind. Full grammar, rules `F1`–`F10`, and slots are in `SPEC.md`.

| outcome | exit | meaning |
|---|---:|---|
| `HOLDS` | 0 | verdict: the adopted question holds on the named bytes |
| `DOES-NOT-HOLD` | 1 | verdict: does not hold on the named bytes (carries `undermined-foundation=` if under a fallen foundation) |
| `NOT-CHECKED` | 2 | no verdict: adoption is valid, but given files are not the named bytes |
| `REFUSED` | 3 | refused under rules `F1`–`F10` (prose, missing column, unadopted, invalid witness, etc.) |
| `NOT-RUN` | 4 | usage error or OS I/O failure |
| `NOT-RECORDED` | 5 | `propose`/`adopt` stopped because the named bytes were not presented |
| `LEDGER-UNREADABLE` | 6 | ledger log or adopters file cannot be read as required |
| `FAILED` | 7 | unexpected failure |
| `PROPOSED` | 8 | proposal recorded; nothing adopted yet |
| `ADOPTED` | 9 | `ssh-keygen` verified a listed key's signature over the exact bytes; recorded |
| `NOT-DELIVERED` | 10 | check was recorded in the log, but its line could not be written to stdout |
| `UNDERMINED` | 11 | foundation knocked down after live-recounting a `DOES-NOT-HOLD` comparison |
| `HOLDS-UNDERMINED` | 12 | verdict: holds locally on the named bytes, but a foundation under them fell (counts kept) |
| `IMPACT` | 13 | lists all adopted foundations and measures resting on a foundation |

---

## What is built

reality.py, 691 lines, Python standard library only + OpenSSH `ssh-keygen`. 63 passing tests (`test_reality.py`), tested on Windows and Linux.

Two closed question forms (`share-at-least`, `share-agrees`), one predicate (`column-equals`), exact integer-ratio arithmetic.

Three isolated OpenSSH signature namespaces: `reality-adopt-1` (measures), `reality-foundation-1` (foundations and tags), and `reality-undermine-1` (knock-downs).

Acyclic foundation graphs (`rests-on` 0–3 earlier foundations in ascending hash order), signed table tags, live-recounted `undermine`, transitive `impact`, and `HOLDS-UNDERMINED`.

---

## Honest limits

Closed does not mean true. "Closed" means every recorded question is well-formed and can be asked of its named bytes; whether it is a good question is not decided here.

Foundations, tags, and sides are signed commitments. The program cannot verify whether a tag is true of the outside world, nor which side of a failed comparison is wrong—the signer explicitly names which side falls.

Explicit and signed, not pre-registration. Today you can inspect the data before signing—bars, names, and tags in the demo were chosen after seeing the tables. Binding a measure and foundation before the data exists is not built yet.

Plain-file ledger. `ledger/log` is an unprotected plain file. Deleting a line—including an `undermine` line—is not detected and silently un-flags dependents. There is no hash chain and no claim of tamper-evidence. Signed lines are re-verified on every read; unsigned lines (proposals, check records) are records only.

Demo key. The demo generates a throwaway key (`REALITY-TEST-KEY-NOT-PATSAK`) per run; nothing here is signed by `patsak127`.

Data floor. Reality only checks the exact bytes given. `convert.py` and `SOURCES.md` trace every table back to NASA/JPL Horizons and `arXiv:2410.05229v1` with SHA-256 checksums.

---

## Files

`reality.py` — the 691-line engine.

`test_reality.py` — 63-test `unittest` suite.

`run_demo.py`, `run-demo.sh`, `demo-output.txt` — runnable two-case demo and saved output.

`SPEC.md` — full technical specification and design limits.

`ONE-PAGER.md`, `CUE.md` — short overview and live talk track.

`source/`, `tables/`, `convert.py`, `SOURCES.md` — raw primary sources, deterministic conversion script, and SHA-256 checksums.

`LICENSE` — Apache License 2.0.

Contact: `patsak127` (`patsak127@users.noreply.github.com`)
