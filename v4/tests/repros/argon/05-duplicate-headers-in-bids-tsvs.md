# 05 — Duplicate column headers in BIDS `events.tsv` (`onset\tduration\tonset`) and case-duplicate headers in `participants.tsv` pass `B06`/`B11` and form claims

- **Category:** **hit** (regression of v1 Finding 19)
- **Spec clauses:** Principle §1 item 1 (*"a column name that occurs twice"* — explicit example in §1!), §1 item 2 (two readings), §1 Whole-dataset conformance, §10.3, `bids/RULES-1.0.1.md` (`B06`, `B11`), `SPEC.md` §5 Finding 19
- **Code locations:** `src/reality2/bids101.py:336` (`events.tsv` header check), `src/reality2/bids101.py:365` (`participants.tsv` header check), `src/reality2/kernel.py:559` (`event` hardcoded column index)
- **Severity:** **high**
- **Confidence:** **high**

## Root cause

Principle §1 item 1 names **"a column name that occurs twice"** as a canonical instance of nonsense, and `SPEC.md` §5 #19 claims duplicate/lookalike headers are fixed (`K002`). That check exists in `kernel.column()` when a user addresses a plain TSV column by name, **but `bids101.py` and `kernel.event()` bypass `kernel.column()` completely**:

1. **Duplicate `onset` or `duration` in `events.tsv` (`bids101.py:336`, `kernel.py:559`):**
   `bids101.py:336` checks only:
   ```python
   if len(t.header) < 2 or t.header[0] != "onset" or t.header[1] != "duration":
   ```
   It never checks whether `"onset"` or `"duration"` (or any other header in `events.tsv`) appears a second time in `t.header[2:]`! Then `c_onset` and `c_duration` (`kernel.py:562–566`) hardcode `col = 0` and `col = 1` without calling `self.column()`. Thus an `events.tsv` with header `onset\tduration\tonset` and row `4.071\t1\t99.9` passes `B06`, and `claim onset(r, 1) is 4.071 s` **forms**, silently reading column 1 (`4.071`) and ignoring column 3 (`99.9`).
2. **Case-duplicate / lookalike headers in `participants.tsv` (`bids101.py:365`):**
   `bids101.py:365` checks `if "participant_id" not in pt.header` and `pt.header.count("participant_id") > 1` by exact string equality, without case-folding or `skeleton()`. A `participants.tsv` with header `participant_id\tPARTICIPANT_ID` (or duplicate extra columns `age\tage`) passes `B11`, and `claim rows(participants(b)) is 1` (or addressing by position) **forms** on a BIDS dataset with duplicate headers!

## Minimal reproducing files and command

Saved in `findings\`:
- `findings\05-duplicate-headers-in-bids-tsvs.rl`
- `findings\05-manifest.txt`
- `findings\05-root\` (`sub-01/func/sub-01_task-x_events.tsv` has `onset\tduration\tonset\n4.071\t1\t99.9\n`; `participants.tsv` has `participant_id\tPARTICIPANT_ID\nsub-01\tshadow\n`)

`findings\05-duplicate-headers-in-bids-tsvs.rl`:
```text
dataset d = sha256:56b2b3a2bca3b96d01abcc6d603e5437b83e6ddb6ba3426a8da9cac9207f5b42
let b = bids(d)
claim onset(recording(b, "01", "x"), 1) is 4.071 s
claim rows(participants(b)) is 1
```

### Command
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\05-duplicate-headers-in-bids-tsvs.rl --files findings\05-manifest.txt --root findings\05-root
```

### Actual output (`rc = 0`)
```text
line 3: formed: EventOnset[BOLDRecording[BIDS-1.0.1[#1], sub 01 task x: #2], #3 row 1] is recorded as 4.071 s (Recorded[s])
  #1 = sha256:56b2b3a2bca3b96d01abcc6d603e5437b83e6ddb6ba3426a8da9cac9207f5b42
  #2 = sha256:35045e26af8ad0d01e4c6c2e9061de0e76fe5208a738f23df3606ecd101143a2
  #3 = sha256:28d68596fb58f78d852570cd83ed5ea04cd56a472b102a71ba6d6a5462f293ea
line 4: formed: RowCount[Participants[BIDS-1.0.1[#1] from #2]] = 1 (Exact)
  #1 = sha256:56b2b3a2bca3b96d01abcc6d603e5437b83e6ddb6ba3426a8da9cac9207f5b42
  #2 = sha256:ca2e804b8a0007c1f1b527d81189aeaae8d46147d2719ba5b415af57c1327aae
accepted
```

## Spec §5 demonstration

- **Formed text:** `findings\05-duplicate-headers-in-bids-tsvs.rl` + `05-manifest.txt` + `05-root\` (`accepted`, 2 formed claims).
- **§5 demonstration:**
  1. **Explicit Principle §1 item 1 violation:** §1 item 1 explicitly states that a text with *"a column name that occurs twice"* is nonsense. Here `"onset"` occurs twice in `sub-01_task-x_events.tsv` (`col 1 = 4.071`, `col 3 = 99.9`), and `participant_id` / `PARTICIPANT_ID` look alike in `participants.tsv`.
  2. **Two readings (§1 item 2):** Standard dict/dataframe readers (`csv.DictReader`, R, Python dict comprehension) overwrite duplicate keys with the *last* column (`99.9`), whereas positional indexing reads the *first* column (`4.071`). `EventOnset[..., #3 row 1]` names row 1's `onset` without disambiguating which `onset` column of `#3` was read.
- **Why neither defence applies:** Both BIDS claims form (`rc = 0`), and the duplicate column headers are directly in the supplied `.tsv` bytes.

## Fix direction

In `bids101.bids_tsv` (so it applies to every BIDS TSV in the dataset: `participants.tsv`, `events.tsv`, `phenotype/*.tsv`), reject any header row where two columns are equal or confusable (`skeleton(h1) == skeleton(h2)`).
