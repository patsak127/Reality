# Sources

## 1. Astronomy: NASA/JPL Horizons, Mars and Jupiter, 2024-Jan-01 to 2025-Dec-31, daily

Horizons is the Jet Propulsion Laboratory's ephemeris service (https://ssd.jpl.nasa.gov/horizons/).
Observer table, quantity 31 (ecliptic longitude and latitude), one row per day at 00:00 UT:

| saved as | body | observer | exact query URL |
|---|---|---|---|
| source/horizons-mars-from-earth.txt | Mars (`499`) | Earth's center (`500@399`) | `https://ssd.jpl.nasa.gov/api/horizons.api?format=text&COMMAND='499'&OBJ_DATA='NO'&MAKE_EPHEM='YES'&EPHEM_TYPE='OBSERVER'&CENTER='500@399'&START_TIME='2024-01-01'&STOP_TIME='2025-12-31'&STEP_SIZE='1 d'&QUANTITIES='31'&CSV_FORMAT='YES'` |
| source/horizons-mars-from-sun.txt | Mars (`499`) | Sun's center (`500@10`) | the same URL with `CENTER='500@10'` |
| source/horizons-jupiter-from-earth.txt | Jupiter (`599`) | Earth's center (`500@399`) | the first URL with `COMMAND='599'` |

- Mars files retrieved 2026-11-20 at about 00:52 CET (`Thu Nov 19 15:52:10` and `15:52:14 2026 Pasadena`); ephemeris sources: `mar099` (Mars), `DE441` (Earth and Sun).
- Jupiter file retrieved directly from the Horizons API (`Thu Nov 19 16:23:04 2026 Pasadena`; ephemeris source `jup365_merged`).
- **Frames:** For the Earth observer Horizons reports ecliptic-of-date longitude; for the Sun observer it reports J2000 ecliptic longitude. Each table uses one frame throughout, and `motion` compares consecutive days *within* one table only; daily precession drift (~0.00004°/day) is more than 100× smaller than the smallest daily step (0.0052°) and cannot flip a direction.
- **`convert.py` derivation:** Compares consecutive days' longitudes (handling the 360-to-0 wrap): `prograde` if step > 0, `retrograde` if step < 0. The last day (`2025-Dec-31`) has no next day and is dropped -> 730 rows per table:
  - Mars seen from Earth: **79 retrograde days** (`2024-Dec-07` .. `2025-Feb-23`).
  - Mars seen from the Sun: **0 retrograde days**.
  - Jupiter seen from Earth: **167 retrograde days** in two spells (`2024-Oct-09` .. `2025-Feb-03` and `2025-Nov-12` .. `2025-Dec-30`).

## 2. Language-model evals: Mirzadeh et al. (Apple, ICLR 2025)

- **Paper:** Iman Mirzadeh, Keivan Alizadeh, Hooman Shahrokhi, Oncel Tuzel, Samy Bengio, Mehrdad Farajtabar, *"GSM-Symbolic: Understanding the Limitations of Mathematical Reasoning in Large Language Models"* (`arXiv:2410.05229`, ICLR 2025).
- **Source URL:** `https://arxiv.org/html/2410.05229v1` (Appendix Table 1: *"Full 8-shot results of all models on GSM8K and different variants of GSM-Symbolic"*).
- **Saved file:** `source/arxiv-2410.05229v1-table1.html` — verbatim `<figure>` element for Table 1 covering all 25 evaluated models (ranging from 2B open models like `Gemma2b` and `Phi-3-mini` up to `o1-preview`).
- **Honest frame disclosure:** `GSM8K (100)` is a single evaluation on 100 static GSM8K test questions; `GSM-Symbolic-NoOp` is the mean accuracy across 50 symbolic instantiations per NoOp-augmented template (adding one mathematically irrelevant sentence). These are two different evaluation frames/question sets, which is why the demo treats them as two distinct foundations (`static-gsm8k-frame` vs. `gsm-noop-frame`).
- **`convert.py` derivation:** Extracts `GSM8K (100)` (column 3) and `Symbolic-NoOp` mean accuracy (column 8), marks `meets_80pct = yes` if accuracy ≥ 80.0 else `no`, and separates `weights = proprietary` (`GPT-4o-mini`, `GPT-4o`, `o1-mini`, `o1-preview`) vs. `open` (remaining 21 models):
  - `tables/llm-gsm8k-100.tsv`: 25 rows, **12** at ≥ 80%.
  - `tables/llm-gsm-noop.tsv`: 25 rows, **0** at ≥ 80% (highest is `o1-preview` at 77.4%).
  - `tables/llm-gsm8k-100-open.tsv`: 21 open-weights rows, **8** at ≥ 80% (0 on `Symbolic-NoOp`, where highest is `Gemma2-27b-it` at 30.0%).

## 3. File SHA-256 Checksums

| file | bytes | sha256 |
|---|---:|---|
| source/horizons-mars-from-earth.txt | 39875 | `b5e9e4c8cdec1a2d9caf78892f53f28eb850e502fabf7edcd8a0452dcaa9ca3c` |
| source/horizons-mars-from-sun.txt | 39821 | `76a44680df8148c395b49b3f561b2c78e31cc377b2066d46152d403ba4094764` |
| source/horizons-jupiter-from-earth.txt | 40942 | `9dbb80bb452722f56bb9f4a3b270d7228a7d34fdb644f47fc5e029d7c4faffd3` |
| source/arxiv-2410.05229v1-table1.html | 43424 | `bf81ba1ba2039450fc0c2ecc2ccba063387be0b1256d47908795542c8fcc96fd` |
| tables/mars-seen-from-earth.tsv | 28515 | `ca65570db21954b7c3c002c0d43c3ee7cef22aa929fce7965bd35252107b5283` |
| tables/mars-seen-from-sun.tsv | 26858 | `ac15aaffcb4bb153c69bf2a261904d5b8a75a8d1a1f62015ebb16786f2e9fff7` |
| tables/jupiter-seen-from-earth.tsv | 28278 | `a0ddb7efb264a82a1e16253b35cb4dc6b82c37f4dbe18a54552bf5b4d94ba0ed` |
| tables/llm-gsm8k-100.tsv | 1038 | `c5dc9c3ac1daa88578cb506b17c551ae2df633deb2d2b3c4757172517ea3147d` |
| tables/llm-gsm-noop.tsv | 1221 | `ce5622d6a5f2ffe2510de61f85bdf46237b225e6361ccc2ebf8d4abe5e62b561` |
| tables/llm-gsm8k-100-open.tsv | 876 | `5b8d504b47a6279fbc872094bb0b193284af3dd270b5aa17643f30067bcbe57c` |
| reality.py | 32359 (691 lines) | `964801d00040d7dbf6d9b95c3cd6e7d003e364e77828c11709090a746d185f95` |
