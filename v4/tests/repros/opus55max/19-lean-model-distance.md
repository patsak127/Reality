# 19. The Lean theorems hold by construction of a model that leaves out where the defects are

**Category:** docs overclaim (verification claim).
**Spec clause:** README "What checks the trusted base" (`metatheory/Scope.lean` "proves on a model
of the evaluator that the files a value reads are exactly the files its sort names; that a value
is determined by those files' bytes; that renaming never changes the output; and that crossings on
intervals hold for every value in the interval. This is a model, not the Python code."); SPEC §5
rows 2 and 3 (`check_rename`, `trace_eq_sort` cited as tests of findings 2 and 3).
**Severity:** medium. **Confidence:** high on what the file states; I could not run Lean here
(no `lean`/`elan` on this machine), so I have not confirmed that it checks under Lean 4.35.0.

## Program

The finding is about `metatheory\Scope.lean`; no program runs Lean. The behaviours the model
cannot show are reproduced in findings 04 (a `let` is re-evaluated at each use), 20 (check 2
cannot see a reader bug) and 21 (renaming changes the verdict). `findings\19-lean-model-distance.rl`
(with `findings\08-table.tsv`) is a program inside the model's own fragment (`file`, `let`, a
reader, a name) whose output differs from the model's:

```
file f = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
let t = tsv(f)
let t = tsv(undeclared)
claim rows(t)
```

```
> set PYTHONPATH=src
> set PYTHONIOENCODING=utf-8
> python -m reality2 check findings\19-lean-model-distance.rl --files findings\08-table.tsv
line 3: refused [N002, item 1]: the name is already declared on line 2; a name stands for one thing
line 4: formed: RowCount[TSV[#1]] = 3 (Exact)
  #1 = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
refused (1 statement)
```

The model's `step` for line 3 evaluates the expression first, gets `N001`, then binds the name and
gets `N002` (`Scope.lean` lines 207–209): two refusal lines where the checker prints one. The
difference is harmless, but it is in the very part (`run`, `step`) that `check_rename` is about.

## What the file proves, read line by line

- **`trace_eq_sort`** (lines 98–134). The model's `eval` *builds* the trace from the sort: `read`
  returns `.val (.read h) v [h]` and `op` returns `.val (.op s s') u (t ++ t')` (lines 81, 87).
  The theorem shows that this definition is consistent with itself. The file says so: "check 2 of
  §4 can never fail on the model". In `kernel.py` the trace is a separate side channel
  (`Store.note` calls spread over the readers, including explicit `note`/`touch_bold` calls made
  only so that the trace matches the sort, `kernel.py:454`, `:522`, `:525-526`), and the sort is a
  string; nothing in the model corresponds to that, so the theorem is not evidence about check 2.
- **`scope`** (lines 142–185). The only place a world is consulted is `w.store h` inside `read`,
  which also puts `h` into the sort, so the result holds by construction. The Python values that do
  depend on more than their named files are BIDS values (the manifest, gate reads, inheritance
  losers) and anything that depends on the interpreter (findings 01, 06, 07, 16); none is in the
  model.
- **`check_rename`** (lines 189–285). Output lines contain no names, so renaming is equivariant.
  True of the model; false of the checker at its byte bound (finding 21), which the model has no
  counterpart for.
- **`exceeds_sound`, `below_sound`** (lines 290–294): `c < lo ≤ x` gives `c < x`. Correct and
  trivial.

## How far the model is from `kernel.py`

| in `kernel.py` | in the model |
|---|---|
| `let` binds an expression, re-evaluated at every use (`kernel.py:151`, `:658`) | `let` binds a meaning computed once |
| a refused `let` whose name exists gives one line (N002) | gives two (the error and N002) |
| readers that refuse (T, J, I, M, B, K, V codes), parameters, positions, byte literals, lookalikes, `is`, units, precision | one abstract reader `rd : C → Option V`, one binary `op` |
| BIDS, manifests, gate reads, check 2 on BIDS sorts | absent |
| bounds (R001 in bytes, R002, R003–R005), interpreter limits | absent |

## Assessment

README is right that this is "a model, not the Python code", and the axioms check is careful. But
the four results are properties the model was defined to have, the model is far from `kernel.py`
exactly where the findings of this review are, and README lists it under "What checks the trusted
base", which it does not do for any line of the trusted base. A model that would carry weight here:
a `let` as in the code; the trace as a separate store effect; the BIDS reader's gate/value split;
and a statement that the program's verdict is invariant under renaming *including* the bounds.
