# 17 — `README.md` and `SPEC.md` overstate what `metatheory/Scope.lean`, Check 2 (`C001`), `F001`, and the fuzzer/test suite guarantee

- **Category:** **docs overclaim**
- **Spec clauses:** `REVIEW.md` (f) (verification claims & SPEC/README-code mismatches), Principle §10.2 (One standard of accuracy — including claims made in documentation), `README.md:72–75, 108–132`, `SPEC.md` §1, §2 item 11, §5
- **Code locations:** `metatheory/Scope.lean:1–302`, `src/reality2/kernel.py:525–588, 648, 682`, `src/reality2/__main__.py:54`
- **Severity:** **medium**
- **Confidence:** **high**

## Summary of verification gaps and documentation overclaims

`README.md:130` adds the honest caveat *"This is a model, not the Python code"*, which is commendable. Even with that caveat, however, **every major property `README.md` and `SPEC.md` cite `Scope.lean`, Check 2, and `tests/` as establishing has a concrete failure in the Python implementation** precisely where the Python code departs from the model or where the docs state an unqualified invariant:

1. **`Scope.lean` models call-by-value `let`; `kernel.py` implements call-by-name `let` (`Scope.lean:183` vs `kernel.py:155, 659`):**
   In `Scope.lean:183`, `Stmt.let_` evaluates `e` once and stores the resulting `Val` in `Env`. In `kernel.py:659`, `let_stmt` stores the raw AST `Expr` in `self.lets` and re-evaluates it on every reference without ticking `Steps`, directly causing Finding 09's $O(2^k)$ blowup (`steps.n == 3`).
2. **`Scope.lean` models `Srt` as an inductive tree; `kernel.py` uses regex `HASH_RE` over flat strings (`Scope.lean:45` vs `kernel.py:22, 580, 710`):**
   `Scope.lean`'s `trace_eq_sort` (`Scope.lean:155`) proves on inductive `Srt` trees that `trace` equals `Srt.hashes`. Because `kernel.py` serializes `M.sort` to a single string and runs `@([0-9a-f]{64})` across quoted byte literals too, `kernel.py` **violates `trace_eq_sort` in both directions** (Finding 01: colliding distinct sorts when the hash is in `trace`, and falsely failing `C001` when the hash is not in `trace`).
3. **`Scope.lean`'s `check_rename` omits raw byte bounds (`Scope.lean:273` vs `syntax.py:293`):**
   `Scope.lean` proves `check_rename` over abstract `Prog` ASTs without byte limits, whereas `syntax.py` checks `len(raw) > 1_000_000` before lexing, causing 1-to-1 identifier renaming to flip `accepted` -> `refused [R001]` (Finding 08).
4. **`Scope.lean` models `Store := Hash -> Option Nat` (`Scope.lean:64`) as pure and stateless:**
   In `readers.py:85–116`, `Store.locate` skips `--root` when `hint is None` and mutates `self._verified` on `hint` lookups, violating both `--files` vs `--root` invariance and statement-isolation (Finding 02). Furthermore, `Scope.lean` omits `dataset`, `bids`, manifests, and `gate=True` reads altogether.
5. **`Scope.lean`'s interval theorems (`exceeds_sound`, `below_sound`, `Scope.lean:288–301`) do not model evaluator expressions:**
   Both theorems are 3-line lemmas over `Rat` (`v.lo ≤ x ∧ x ≤ v.hi → c < v.lo → c < x` via `Rat.lt_of_lt_of_le`). They do **not** model `difference`, `widen`, `sum`, `min`, `max`, or `Recorded` precision propagation.
6. **Check 2 (`C001`) is partially theatrical on BIDS recordings (`README.md:73`, `SPEC.md` §2 item 11 vs `kernel.py:525–545`):**
   `README.md:73` states: *"The store records every file whose bytes a value read. If that set differs from the files named in the sort, the claim is refused (C001), even if the value is right."* In reality, `bids101.load` reads every dataset file with `gate=True` (which **suppresses `store.trace`**) and caches `r.val.header` and `r.val.meta["RepetitionTime"]` in memory. Then `c_volumes` (`kernel.py:532`) reads `r.val.header` from memory and calls `self.touch_bold(r)` (`self.store.path(...)`, discarding the return value!) solely to append `r.val.h` to `trace`; similarly `c_tr` (`kernel.py:543–545`) reads `r.val.meta["RepetitionTime"]` from memory and calls `self.store.json(h, p, gate=False)` (discarding the return value!) solely to make `trace` match `from @{h}` — which is why Check 2 could not catch Finding 06's equal-rank JSON tie-break!
7. **Direct `README.md` / `SPEC.md` factual mismatches:**
   - `README.md:75`: *"A name that points to bytes nobody supplied is refused (F001)."* — False: unused `file` and `dataset` declarations pointing to missing hashes are accepted with `rc = 0`.
   - `README.md:109–120`: *"The trusted base is everything a verdict depends on"* (listing 5 files, excluding `__main__.py`). — False: CLI verdicts and output bytes depend on `__main__.py`, which crashes on `§` under ASCII/CP437 and emits `0xa7` + CRLF on Windows (Finding 11).
   - `README.md:128` & `SPEC.md` §5 #1, #13: Claims 187 passing tests, byte-identical output, and no crashes. — Out of the box on Windows, `pytest` fails `test_01_hash_seed_does_not_change_output`, and `reality2 check` crashes with uncaught `ValueError` (`10-crash.rl`) and `UnicodeEncodeError` (`11-locale-encoding-dependence-and-crash.rl`).

## Minimal reproducing files and command

Saved in `findings\`:
- `findings\17-lean-metatheory-and-docs-overclaims.rl`
- `findings\17-sample.tsv`

`findings\17-lean-metatheory-and-docs-overclaims.rl`:
```text
file missing_unused = sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
file f = sha256:93f3b31a5f42fa86eb996d544f42897156f9bd247e4f21265083010606b6088b
claim count(where(tsv(f), eq(1, "@bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"))) is 0
```

### Command
```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m reality2 check findings\17-lean-metatheory-and-docs-overclaims.rl --files findings\17-sample.tsv
```

### Actual output (`rc = 1` — line 1's missing `file` is silently accepted without `F001`, while line 3's valid TSV filter fails `C001`, contradicting `Scope.lean`'s `trace_eq_sort`)
```text
line 3: refused [C001, floor]: check 2: the claim's sort names sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb, but its value was not computed from it; the sort and the dependency set disagree (a refusal, and a bug report against one of them)
refused (1 statement)
```

## Fix direction

Align the Python implementation with `Scope.lean` (call-by-value `let`, structured `Sort` AST instead of `HASH_RE`, pure `Store`, renaming-invariant token bounds), prove interval soundness over actual `Expr` evaluation (`difference`, `widen`), make `c_volumes`/`c_tr` compute from traced reads rather than dummy `store` touches (and record all equal-rank metadata dependencies cleanly), and tighten `README.md`/`SPEC.md` claims so they state no more than what is actually checked.
