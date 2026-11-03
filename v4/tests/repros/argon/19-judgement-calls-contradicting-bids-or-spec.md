# 19 — `B04` vs plain `tsv()` double-quote split: plain `tsv()` forms claims on quoted cells that have two standard TSV readings, while `B04` refuses BIDS 1.0.1 §4.2 tab-escaping

- **Category:** **judgement call** (and **hit** on plain `tsv()` under the two-readings rule if RFC-4180/BIDS TSV quoting is counted as a standard TSV reading; concerns `SPEC.md` §2 item 6 & item 9 bullet 5 and Principle §10.2)
- **Spec clauses:** Principle §1 item 2 (no two readings), §1 Reading rules, §10.2 (One standard of accuracy), BIDS 1.0.1 §4.2 (`context/sources/bids-1.0.1.txt:282–288`), `SPEC.md` §2 item 6 & item 9
- **Code locations:** `src/reality2/readers.py:248–260` (`tsv`), `src/reality2/bids101.py:67–76` (`bids_tsv`, `B04`)
- **Severity:** **medium**
- **Confidence:** **high**

## Root cause

Look side-by-side at how `bids101.bids_tsv` (`bids101.py:72–75`) and `readers.tsv` (`readers.py:248–260`) treat a double quote `"` inside a `.tsv` file:

1. In `bids101.py:74`, `B04` refuses **any** `"` in a BIDS TSV with the explicit justification:
   > *"participants.tsv line 2 holds a double quote; BIDS 1.0.1 §4.2 uses quotes to escape tabs but does not say how a quote itself is written, **so the cell has two readings (§4.2)**"*
2. Yet in `readers.py:248–260`, plain `tsv()` splits on `\n` and `\t` and **allows `"` without refusal**, treating `"quoted free text"` as an 18-byte literal string containing leading and trailing quote characters!

This creates a two-sided failure against Principle §1 item 2 and §10.2:

- **Inconsistency on plain `tsv()` (§1 item 2 & §10.2):** `readers.tsv` refuses CR (`T002`) and BOM (`T001`) because different mainstream TSV readers read them differently. By that **exact same criterion**, mainstream TSV readers disagree on `"quoted free text"`: Python `csv.reader(..., delimiter='\t')`, R `read.delim()`, pandas `read_csv(sep='\t')`, and LibreOffice/Excel strip outer quotes and read `quoted free text` (16 chars), whereas IANA `text/tab-separated-values` / `awk -F'\t'` read `"quoted free text"` (18 chars). Accepting `"quoted free text"` in plain `tsv()` while declaring in `B04` that `"quoted free text"` has *"two readings"* applies two incompatible standards of accuracy inside the same 400-line codebase!
- **Over-refusal on BIDS 1.0.1 §4.2 (`bids-1.0.1.txt:285–286`):** BIDS 1.0.1 §4.2 explicitly specifies:
  > *"Other files are saved as tab delimited values (.tsv) files, aka csv files where commas are replaced by tabs ... **String values containing tabs must be escaped using double quotes.**"*
  A cell `"tab\tescaped"` with **no interior quote characters** has **only one** reading under BIDS 1.0.1 §4.2 (a single quoted field containing a tab — only interior `""` vs `\"` has two readings!). Yet `bids101.bids_tsv` calls `readers.tsv` (splitting on the raw `\t` first and failing column-count `T004`/`B04`!) and also bans `"quoted free text"` even when there is no interior quote at all.

## Minimal reproducing files and command

Saved in `findings\`:
- `findings\19-judgement-calls-contradicting-bids-or-spec.rl`
- `findings\19-manifest.txt`
- `findings\19-root\` (`participants.tsv` has `participant_id\tnote\nsub-01\t"quoted free text"\n`)
- `findings\19-tab-escaped.tsv` (`participant_id\tnote\nsub-01\t"tab\tescaped"\n` — exact BIDS 1.0.1 §4.2 tab-escaping)

`findings\19-judgement-calls-contradicting-bids-or-spec.rl`:
```text
dataset d = sha256:49d460d586e18082803a7d1e153762538748aa86f60fb917bc7e65c4084c0052
file p = sha256:9ae996d8f1c85a95ea6596105e5f88d36b447659fabb63e4145616c4560f64d5
file qt = sha256:43707213916dea8844fd77840f1c35f79f430d1c0a325549be46708c8aa18d5f
claim cell(tsv(p), 1, 2) is "\"quoted free text\""
claim rows(participants(bids(d))) is 1
claim rows(tsv(qt)) is 1
```

### Command
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\19-judgement-calls-contradicting-bids-or-spec.rl --files findings\19-manifest.txt findings\19-root\participants.tsv findings\19-tab-escaped.tsv --root findings\19-root
```

### Actual output (`rc = 1` — line 4 forms on `p` as plain TSV, while line 5 refuses the exact same `p` as having "two readings"!)
```text
line 4: formed: Cell[TSV[#1], row 1, col 2] = "\"quoted free text\""
  #1 = sha256:9ae996d8f1c85a95ea6596105e5f88d36b447659fabb63e4145616c4560f64d5
line 5: refused [B00, reading rules]: the dataset does not conform to BIDS 1.0.1 (1 failures), so nothing BIDS-based forms from it (principle §1, whole-dataset conformance). B04 x1, first: participants.tsv line 2 holds a double quote; BIDS 1.0.1 §4.2 uses quotes to escape tabs but does not say how a quote itself is written, so the cell has two readings (§4.2)
line 6: refused [T004, item 1]: sha256:43707213916dea8844fd77840f1c35f79f430d1c0a325549be46708c8aa18d5f line 2 has 3 cells and the header has 2: the table's columns are not fixed by its bytes
refused (2 statements)
```

## Fix direction

Apply **one standard** across TSV readers:
- In plain `tsv()` (`readers.py`), refuse `"` (`T005`) for the exact same two-readings reason `T001`/`T002` refuse BOM and CR (pandas/R/csv strip quotes while IANA TSV keeps them).
- In `bids_tsv()` (`bids101.py`), either parse BIDS 1.0.1 §4.2 double-quoted fields when they contain **no interior quote/newline** (refusing `B04` only on interior quotes `""` / `\"` or unclosed quotes, where §4.2 genuinely leaves two readings!) or, if refusing all `"` in both `tsv()` and `bids_tsv()`, state uniformly that any `"` in TSV creates two readings across tools.
