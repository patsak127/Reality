# 12 — Idle/contradictory `where` predicates, vacuous `sum` on prose columns, `widen(..., tolerance = 0)`, unchecked manifest `<size>` fields, negative/unreduced `share` literals, and conflicting precision profiles all form

- **Category:** **hit**
- **Spec clauses:** Principle §1 item 1 (no missing or idle parts), §1 item 6 (no self-contradictions), §6.4 b2 (`share` ratio form), §10.2 (ii) (one precision profile per sort and computation), `README.md:75`, `SPEC.md` §1 & §5 Finding 15
- **Code locations:** `src/reality2/readers.py:300–329` (`parse_manifest`), `src/reality2/bids101.py:259` (`load`), `src/reality2/kernel.py:268–286` (`c_where`), `src/reality2/kernel.py:381–397` (`c_sum`), `src/reality2/kernel.py:419–426` (`c_widen`), `src/reality2/kernel.py:610–615` (`check_is` for `share`), `src/reality2/kernel.py:648` (`file` / `dataset` declarations), `src/reality2/syntax.py:236–242` (`parse_ratio`)
- **Severity:** **medium**
- **Confidence:** **high**

## Root cause

Six closely related checks omit idle-part, self-contradiction, or profile-consistency validation and allow malformed or self-contradictory texts to **form**:

1. **Manifest `<size>` column is 100% dead and unchecked (`readers.py:300–329`, `bids101.py:259`):**
   Every line of a Reality manifest has the form `<sha256>\t<size>\t<path>`. `parse_manifest` parses `int(sz)` into `man[path] = (h, sz)`, **and no line of code anywhere in `reality2` ever checks `sz == len(bytes)`**! Thus a manifest asserting `dataset_description.json` has size `0` and `participants.tsv` has size `999999999` — directly contradicting the supplied 41-byte and 53-byte files — **forms BIDS claims without refusal** (§1 item 1 idle field + §1 item 6 self-contradiction in the text).
2. **Contradictory and strictly redundant `where` predicates (`kernel.py:273–285`):**
   `S008` (`SPEC.md` §5 #15: *"a condition that doesn't bear (written twice) is refused (S008)"*) checks only exact tuple equality `(a.fn, k, lit) in seen`.
   - `where(t, eq(1, "a"), ne(1, "b"))` **forms**, even though `ne(1, "b")` is strictly entailed by `eq(1, "a")` and can **never** bear on the selected row set (§1 item 1 idle part).
   - `where(t, eq(1, "x"), ne(1, "x"))` (a logical contradiction on column 1) **forms** an always-empty selection!
3. **Vacuous `sum` on non-numeric prose columns + smuggling unrelated file hashes into a claim's sort (`kernel.py:381–397`):**
   `c_sum` parses `R.decimal(tab.rows[i][k - 1])` **only for rows in `idx`**. When `idx` is empty (`where(tsv(prose), eq(1, "x"), ne(1, "x"))`), `sum(..., 2)` **forms as `0 (Exact)` even though column 2 contains `"hello"` / `"world"` (non-numeric prose)**! Composing `difference(val, sum(where(tsv(prose), eq(1, "x"), ne(1, "x")), 2))` then **forms** while adding `prose`'s SHA-256 to both `trace` and `m.sort`, smuggling an arbitrary unrelated file into the claim's printed support whose contents cannot affect the answer (§1 item 1).
4. **Idle `widen(x, tolerance = 0)` (`kernel.py:422`):**
   `c_widen` checks `if q < 0:` instead of `if q <= 0:`. Passing `tolerance = 0` performs zero widening, leaves precision `(Exact)` rather than an interval, and carries an idle parameter `tolerance = 0` in the sort.
5. **Unused `file` / `dataset` declarations pointing to non-existent bytes (`kernel.py:648`):**
   `file ghost = sha256:ffff...` is accepted without verifying `F001`, leaving an idle declaration and directly contradicting `README.md:75` (*"A name that points to bytes nobody supplied is refused (F001)"*).
6. **Negative / cancelled `share` literals (`syntax.py:240`, `kernel.py:610`) & conflicting precision profiles (Principle §10.2 ii):**
   - `parse_ratio` checks `if int(d) == 0:` instead of `int(d) <= 0` and allows `-` in the denominator, so `claim share(where(t, eq(1, "z"))) is 0/-5` **forms** (`= 0/2 (Exact)`)! And `claim share(where(t, eq(1, "a"))) is 54/108` **forms** on a **2-row** table (`= 1/2 (Exact)`), discarding Principle §6.4 b2's unreduced `num/den` semantics.
   - Principle §10.2 (ii) requires: *"Inside one text, every claim of the same sort and computation uses the same precision profile, or the checker refuses the text."* `SPEC.md` §1 never lists §10.2 (ii) as out of scope, yet two claims in the same `.rl` file can apply `tolerance = 0.05` and `tolerance = 5` to the identical `Decimal[Cell[TSV[#1], row 1, col 2]]` inside `Exceeds`.

## Minimal reproducing files and command

Saved in `findings\`:
- `findings\12-idle-parts-and-unchecked-manifest-sizes.rl`
- `findings\12-manifest.txt` (`dataset_description.json` listed as size `0`; `participants.tsv` listed as size `999999999`)
- `findings\12-root\`, `findings\12-num.tsv`, `findings\12-prose.tsv`

`findings\12-idle-parts-and-unchecked-manifest-sizes.rl`:
```text
dataset d = sha256:f407ec30d56ee1931deeae21bf67d184ad8bfb892c5df5931f5e2fb441f1aa03
file ghost = sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
file nums = sha256:433a36369cf140e6e22538705b8a6f0c198462f8fd57b667783bbd37768b3985
file prose = sha256:6802d2152377833c0b76f1de88a3406b12eaa1d93dcf92351e460450ee157fbf
claim rows(participants(bids(d))) is 2
claim count(where(tsv(nums), eq(1, "a"), ne(1, "b"))) is 1
claim sum(where(tsv(prose), eq(1, "x"), ne(1, "x")), 2) is 0
claim difference(number(cell(tsv(nums), 1, 2)), sum(where(tsv(prose), eq(1, "x"), ne(1, "x")), 2)) is 10
claim widen(number(cell(tsv(nums), 1, 2)), tolerance = 0) is 10
claim share(where(tsv(nums), eq(1, "z"))) is 0/-5
claim share(where(tsv(nums), eq(1, "a"))) is 54/108
claim exceeds(widen(number(cell(tsv(nums), 1, 2)), tolerance = 0.05), c = 9.9)
claim exceeds(widen(number(cell(tsv(nums), 1, 2)), tolerance = 5), c = 4)
```

### Command
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\12-idle-parts-and-unchecked-manifest-sizes.rl --files findings\12-manifest.txt findings\12-num.tsv findings\12-prose.tsv --root findings\12-root
```

### Actual output (`rc = 0`, all 9 claims form!)
```text
line 5: formed: RowCount[Participants[BIDS-1.0.1[#1] from #2]] = 2 (Exact)
  #1 = sha256:f407ec30d56ee1931deeae21bf67d184ad8bfb892c5df5931f5e2fb441f1aa03
  #2 = sha256:416e7b27774222182069e4e8c4bfa834cda4592eb6e920c6a553d5b2ae2f594b
line 6: formed: Count[Rows[TSV[#1] where col 1 = "a" and col 1 != "b"]] = 1 (Exact)
  #1 = sha256:433a36369cf140e6e22538705b8a6f0c198462f8fd57b667783bbd37768b3985
line 7: formed: Sum[Rows[TSV[#1] where col 1 = "x" and col 1 != "x"], col 2] = 0 (Exact)
  #1 = sha256:6802d2152377833c0b76f1de88a3406b12eaa1d93dcf92351e460450ee157fbf
line 8: formed: Difference[Decimal[Cell[TSV[#1], row 1, col 2]], Sum[Rows[TSV[#2] where col 1 = "x" and col 1 != "x"], col 2]] = 10 (Exact)
  #1 = sha256:433a36369cf140e6e22538705b8a6f0c198462f8fd57b667783bbd37768b3985
  #2 = sha256:6802d2152377833c0b76f1de88a3406b12eaa1d93dcf92351e460450ee157fbf
line 9: formed: Widened[Decimal[Cell[TSV[#1], row 1, col 2]], tolerance = 0] = 10 (Exact)
  #1 = sha256:433a36369cf140e6e22538705b8a6f0c198462f8fd57b667783bbd37768b3985
line 10: formed: Share[Rows[TSV[#1] where col 1 = "z"] of TSV[#1]] = 0/2 (Exact)
  #1 = sha256:433a36369cf140e6e22538705b8a6f0c198462f8fd57b667783bbd37768b3985
line 11: formed: Share[Rows[TSV[#1] where col 1 = "a"] of TSV[#1]] = 1/2 (Exact)
  #1 = sha256:433a36369cf140e6e22538705b8a6f0c198462f8fd57b667783bbd37768b3985
line 12: formed: Exceeds[Widened[Decimal[Cell[TSV[#1], row 1, col 2]], tolerance = 0.05], c = 9.9] holds
  #1 = sha256:433a36369cf140e6e22538705b8a6f0c198462f8fd57b667783bbd37768b3985
line 13: formed: Exceeds[Widened[Decimal[Cell[TSV[#1], row 1, col 2]], tolerance = 5], c = 4] holds
  #1 = sha256:433a36369cf140e6e22538705b8a6f0c198462f8fd57b667783bbd37768b3985
accepted
```

## Spec §5 demonstration

- **Formed text:** `findings\12-idle-parts-and-unchecked-manifest-sizes.rl` + supplied files (`accepted`, 9 formed claims).
- **§5 demonstration:**
  1. **Self-contradiction (§1 item 6):** `12-manifest.txt` states `dataset_description.json` is `0` bytes and `participants.tsv` is `999999999` bytes while naming their SHA-256 hashes whose supplied bytes have lengths `41` and `53`.
  2. **Idle parts (§1 item 1):** `file ghost` is unused and missing; `ne(1, "b")` after `eq(1, "a")` is dead; `sum` on `where(tsv(prose), eq(1, "x"), ne(1, "x"))` smuggles `#2 = 12-prose.tsv` into line 8's sort without any byte of column 2 bearing on the value `10`; `tolerance = 0` is a no-op; `0/-5` has a negative denominator; and lines 12–13 violate §10.2 (ii) by giving two tolerance profiles (`0.05` vs `5`) to the same sort and computation.
- **Why neither defence applies:** Every claim forms (`rc = 0`), and every defect is visible from the text and supplied bytes alone.

## Fix direction

Verify `os.path.getsize(p) == sz` for every manifest entry read (`M002`/`C002`); reject contradictory (`eq(k, a)` + `eq(k, b)` for $a \ne b$, or `eq(k, a)` + `ne(k, a)`) and redundant (`eq(k, a)` + `ne(k, b)`) single-column predicates in `S008`; require `sum` (like `min`/`max`) either to reject empty selections (`V003`) or to validate numeric syntax across the column; require `tolerance > 0` in `widen`; check `F001` at `file`/`dataset` declaration time (and optionally flag unused declarations); require `0 <= num <= den` and `den > 0` (matching `(num, den)` directly) in `share`; and record `(inner_sort, outer_op) -> tolerance` per program to enforce §10.2 (ii).
