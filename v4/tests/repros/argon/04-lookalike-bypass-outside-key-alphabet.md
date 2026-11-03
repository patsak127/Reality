# 04 — Restricted 4-rule `skeleton()` misses ASCII (`|`/`l`) and Unicode UTS #39 confusables whenever a comparand lies outside `K` (`column`, `key`, `where`, and BIDS `participants.tsv` / `acq` / `rec`)

- **Category:** **hit** (regression of v1 Finding 8)
- **Spec clauses:** Principle §1 item 1 (ambiguous identifiers/keys), §5 Must-not-form #14a (`N14a`), §10.3 (Lookalikes & pinned UTS #39 `confusables.txt`), `SPEC.md` §2 items 2, 4, 5 & §5 Finding 8
- **Code locations:** `src/reality2/keys.py:25–39` (`skeleton`), `src/reality2/kernel.py:226–230` (`column`), `src/reality2/kernel.py:288–300` (`no_lookalike`), `src/reality2/kernel.py:325–327` (`row` / `key`), `src/reality2/bids101.py:362–395`, `src/reality2/kernel.py:513`
- **Severity:** **high**
- **Confidence:** **high**

## Root cause

`keys.py` pins the SHA-256 of Unicode UTS #39 `confusables.txt` v18.0.0 (`6ed3ee8bb5...`), yet `skeleton(s)` (`keys.py:25–39`) does **not** load `confusables.txt` or fold general UTS #39 confusables. Instead, its docstring (`keys.py:26–29`) argues:

> *"Every key in Reality is restricted to K = [A-Za-z0-9] ... Within K, the UTS #39 confusable classes (after ASCII case folding) are: {1, l, I}, {0, O}, and m <-> rn."*

That reduction is mathematically sound **only when both strings being compared are already restricted to `K`**. In `kernel.py` and `bids101.py`, that precondition fails in **five** distinct places:

1. **Table headers in `column()` (`kernel.py:217–230`):** Only the *queried* header `name` is checked with `is_header(name)` (`K ∪ {'_'}`). The *other* headers in `tab.header` are unrestricted UTF-8!
   - If a TSV has headers `group` and `grоup` (with Cyrillic `о`, U+043E, mapped to `o` in `confusables.txt`), `skeleton("gr\u043eup")` leaves `\u043e` unchanged, so `eq("group", ...)` **forms**!
   - Even **purely within printable ASCII**, `confusables.txt` maps `|` (U+007C VERTICAL LINE) -> `l` (U+006C). If a TSV has headers `a|b` and `alb`, `cell(t, ..., "alb")` **forms** because `skeleton("a|b")` does not map `|` -> `l`!
2. **Other cells in a `key()` column (`kernel.py:321–327`):** `key(col, "al")` checks `is_key("al")`, but the *other* cells `r[k - 1]` in column `col` are unrestricted UTF-8:
   - `key(1, "al")` **forms** right next to `"a|"` (ASCII UTS #39 confusable `|` -> `l`)!
   - `key(1, "so1")` **forms** right next to `"s\u043e1"` (Cyrillic `о` -> `o` in UTS #39)!
   - Furthermore, `key(1, "al")` only checks `skeleton(r[k - 1]) == skeleton(s)` against the *single queried key* `s`, **not** pairwise across the key column — so `key(1, "al")` **forms** even when rows 5 and 6 of that very same key column hold `"sub001"` and `"subOO1"`, violating Principle §10.3 (*"The scope is every key column the derivation reads"*).
3. **`where(..., eq/ne(col, "bytes"))` (`kernel.py:276, 288–300`):** Neither `lit` nor `tab.rows[i][k - 1]` is restricted to `K`. Consequently, **v1 Finding 8's exact original reproducer** (`tests/old/opus-v1-08-unicode-lookalike-keys.rl`: `"sub-001"` vs `"sub\u2011001"` with U+2011 NON-BREAKING HYPHEN, mapped to `-` in `confusables.txt`, and `"equalRange"` vs `"\u0435qualRange"` with Cyrillic `е`, U+0435) **forms without refusal**!
4. **BIDS folderless `participants.tsv` labels (`kernel.py:513`):** `recording(b, "01", ...)` checks `check_lookalike_set(labs[0], ds.subjects, ...)` over *folder* subjects (`ds.subjects`), ignoring `ds.ptable_labels` when `participants.tsv` contains a folderless lookalike `sub-O1` (`findings\07-root\participants.tsv`).
5. **BIDS `acq` and `rec` labels (`bids101.py:280–315`):** `bids101` checks lookalikes on `sub`, `task`, and `run`, but never on `acq` or `rec` (`sub-01_task-x_acq-01_bold.nii` + `sub-01_task-x_acq-O1_bold.nii`).

## Minimal reproducing files and command

Saved in `findings\`:
- `findings\04-lookalike-bypass-outside-key-alphabet.rl`
- `findings\04-lookalike.tsv` (headers `id`, `group`, `gr\u043eup`, `a|b`, `alb`; column 1 rows `al`, `a|`, `so1`, `s\u043e1`, `sub001`, `subOO1`, `sub-001`, `sub\u2011001`)

`findings\04-lookalike-bypass-outside-key-alphabet.rl`:
```text
file f = sha256:22e0ef83e818b0a748fcb2f522d4744d0af0c9f39a9061e5251768aa436f451c
claim count(where(tsv(f), eq("group", "ok"))) is 3
claim cell(tsv(f), key(1, "al"), "alb") is "20"
claim cell(tsv(f), key(1, "so1"), 2) is "ok"
claim count(where(tsv(f), eq(1, "sub-001"))) is 1
```

### Command
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\04-lookalike-bypass-outside-key-alphabet.rl --files findings\04-lookalike.tsv
```

### Actual output (`rc = 0`)
```text
line 2: formed: Count[Rows[TSV[#1] where col 2 = "ok"]] = 3 (Exact)
  #1 = sha256:22e0ef83e818b0a748fcb2f522d4744d0af0c9f39a9061e5251768aa436f451c
line 3: formed: Cell[TSV[#1], row 1 (the row whose col 1 is "al"), col 5] = "20"
  #1 = sha256:22e0ef83e818b0a748fcb2f522d4744d0af0c9f39a9061e5251768aa436f451c
line 4: formed: Cell[TSV[#1], row 3 (the row whose col 1 is "so1"), col 2] = "ok"
  #1 = sha256:22e0ef83e818b0a748fcb2f522d4744d0af0c9f39a9061e5251768aa436f451c
line 5: formed: Count[Rows[TSV[#1] where col 1 = "sub-001"]] = 1 (Exact)
  #1 = sha256:22e0ef83e818b0a748fcb2f522d4744d0af0c9f39a9061e5251768aa436f451c
accepted
```

## Spec §5 demonstration

- **Formed text:** `findings\04-lookalike-bypass-outside-key-alphabet.rl` + `findings\04-lookalike.tsv` (`accepted`, 4 formed claims).
- **§5 demonstration:**
  1. **Principle §10.3 & Must-not-form `N14a` break:** Under the pinned UTS #39 `confusables.txt` (`context/sources/confusables.txt`, whose hash `keys.py` itself pins!), `"group"` and `"gr\u043eup"` have identical UTS #39 skeletons, `"a|b"` and `"alb"` have identical ASCII UTS #39 skeletons (`|` -> `l`), `"al"` and `"a|"` have identical ASCII UTS #39 skeletons, `"so1"` and `"s\u043e1"` have identical UTS #39 skeletons, `"sub001"` and `"subOO1"` collide in key column 1, and `"sub-001"` and `"sub\u2011001"` have identical UTS #39 skeletons.
  2. **Contradiction with `README.md:60` and `SPEC.md` §2 item 2:** `README.md:60` states *"no other header in the same row looks like it"*, and `SPEC.md:37` states `eq` and `key` strings are *"checked for lookalikes against every cell of that column (K002)"*. All four claims form anyway.
- **Why neither defence applies:** `reality2` accepts all four claims (`rc = 0`), and every confusable pair is present in the supplied TSV bytes and defined in the pinned `confusables.txt`.

## Fix direction

Compile the full UTS #39 `confusables.txt` mapping table (it is ~10,000 one-line entries, easily shipped as a compact stdlib-only table generated and verified at test time against `CONFUSABLES_SHA256`, including ASCII punctuation entries like `|` -> `l` and Unicode confusables like `\u043e` -> `o`, `\u2011` -> `-`), apply NFKD + UTS #39 `skeleton` + casefold uniformly across headers, key columns (pairwise across the entire key column per §10.3), `where` byte literals, all `participants.tsv` labels, and `acq`/`rec` labels.
