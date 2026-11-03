/-
Reality metatheory, a model of v3's intended design (copied from v2; codes renamed to the ones v3
raises): scope comes from sorts, names carry no meaning (v3 spec §2, §4, §10.1). It is not a proof
about the checker, and it does not model v4 (header corrected 26 Oct 2026, review finding 28).

What is modelled: v3's abstract scope, trace and renaming, in an idealised language. A program is
a list of declarations `file n = h` (a name for the file with hash h), `let n = e` and `claim e`.
Expressions are names, `read e` (one abstract reader applied to the bytes of a file) and `op a b`
(any computation from two values). Readers, computations, hashes, contents and values are abstract:
any types and any functions. A store maps hashes to contents, or to nothing, and is a pure
function. The meaning of an expression is either a file or a value together with its sort and the
trace of the files whose bytes were read; the sort names files by hash only. A refused `let` leaves
its name bound to nothing (later uses refuse, N003); a name declared twice is refused and the first
binding kept.

Not modelled, so nothing here is evidence about them: v4's three mechanisms (the W1/W2 witness
search and its candidate family, affine `widen` with value identity and S012, the cost, memory and
output bounds); one file read by two readers (CSV and TSV, JSON); the reader cache; BIDS; the
parser and the concrete readers; and kernel.py itself. v4's renaming independence rests on the
witness search's order (v4-fixes 03), which `check_rename` below cannot see.

What is proved (no `sorry`, only Lean's standard axioms; `#print axioms` at the end):
  1. `trace_eq_sort`: the files read while computing a value are exactly the files its sort
     names, in order (check 2 of §4 can never fail on the model; kernel.py checks it anyway).
  2. `scope`: a value is determined by the bytes of the files its sort names: two stores that
     agree on those files give the same meaning (scope comes from the sort).
  3. `check_rename`: renaming the names of a program by any injective map gives exactly the
     same output (outputs contain sorts, values, codes and positions, never names).
  4. `exceeds_sound`, `below_sound`: when a crossing forms for an interval [lo, hi], every
     value in the interval crosses (precision is part of the value; §10.1 C).

The Python checker is tested against 1-2 by its trace check and against 3 by the renaming
fuzzer (tests/test_rename.py): that is evidence, not proof.
-/

namespace RealityScope

set_option linter.unusedSectionVars false

inductive Expr (N : Type) where
  | var : N → Expr N
  | read : Expr N → Expr N
  | op : Expr N → Expr N → Expr N

inductive Srt (H : Type) where
  | read : H → Srt H
  | op : Srt H → Srt H → Srt H
deriving DecidableEq

def Srt.files {H : Type} : Srt H → List H
  | .read h => [h]
  | .op a b => a.files ++ b.files

inductive Meaning (H V : Type) where
  | file : H → Meaning H V
  | val : Srt H → V → List H → Meaning H V

inductive Code where
  | N001 | N002 | N003 | S007 | F001 | V005 | V003
deriving DecidableEq

/-- The world the checker is given: readers and computations are any functions. -/
structure World (H C V : Type) where
  store : H → Option C
  rd : C → Option V
  opf : V → V → Option V

variable {N H C V : Type} [DecidableEq N]

def look {α : Type} : List (N × α) → N → Option α
  | [], _ => none
  | (y, a) :: rest, x => if y = x then some a else look rest x

abbrev Env (N H V : Type) := List (N × Option (Meaning H V))

def eval (w : World H C V) (env : Env N H V) : Expr N → Except Code (Meaning H V)
  | .var n => match look env n with
    | none => .error .N001
    | some none => .error .N003
    | some (some m) => .ok m
  | .read e => match eval w env e with
    | .error c => .error c
    | .ok (.val _ _ _) => .error .S007
    | .ok (.file h) => match w.store h with
      | none => .error .F001   -- no supplied file has the hash (kernel: F001)
      | some c => match w.rd c with
        | none => .error .V005   -- the reader refuses the bytes; stands for the reader families (T, J, I, V005)
        | some v => .ok (.val (.read h) v [h])
  | .op a b => match eval w env a, eval w env b with
    | .error c, _ => .error c
    | .ok _, .error c => .error c
    | .ok (.val s v t), .ok (.val s' v' t') => match w.opf v v' with
      | none => .error .V003   -- the computation has no value; stands for the V family (V002-V004, V006, V008)
      | some u => .ok (.val (.op s s') u (t ++ t'))
    | .ok _, .ok _ => .error .S007

/-! ### 1. The trace is the sort -/

def Good : Meaning H V → Prop
  | .file _ => True
  | .val s _ t => t = s.files

def EnvGood (env : Env N H V) : Prop := ∀ n m, look env n = some (some m) → Good m

theorem trace_eq_sort (w : World H C V) (env : Env N H V) (hg : EnvGood env) :
    ∀ (e : Expr N) (m : Meaning H V), eval w env e = .ok m → Good m := by
  intro e
  induction e with
  | var n =>
    intro m h
    simp only [eval] at h
    split at h
    · cases h
    · cases h
    · rename_i m' hl; cases h; exact hg n _ hl
  | read e ih =>
    intro m h
    simp only [eval] at h
    split at h
    · cases h
    · cases h
    · split at h
      · cases h
      · split at h
        · cases h
        · cases h; simp [Good, Srt.files]
  | op a b iha ihb =>
    intro m h
    simp only [eval] at h
    split at h
    · cases h
    · cases h
    · rename_i s v t s' v' t' ha hb
      split at h
      · cases h
      · cases h
        have g1 := iha _ ha
        have g2 := ihb _ hb
        simp only [Good] at g1 g2 ⊢
        simp [Srt.files, g1, g2]
    · cases h

/-! ### 2. Scope comes from the sort -/

def Meaning.files : Meaning H V → List H
  | .file _ => []
  | .val s _ _ => s.files

theorem scope (w1 w2 : World H C V) (hr : w1.rd = w2.rd) (ho : w1.opf = w2.opf)
    (env : Env N H V) :
    ∀ (e : Expr N) (m : Meaning H V), eval w1 env e = .ok m →
      (∀ h ∈ m.files, w1.store h = w2.store h) → eval w2 env e = .ok m := by
  intro e
  induction e with
  | var n => intro m h _; simpa [eval] using h
  | read e ih =>
    intro m h hs
    simp only [eval] at h ⊢
    split at h
    · cases h
    · cases h
    · rename_i h0 he
      have e2 := ih (.file h0) he (by simp [Meaning.files])
      rw [e2]
      simp only
      split at h
      · cases h
      · rename_i c hc
        split at h
        · cases h
        · rename_i v hv
          cases h
          have : w2.store h0 = some c := by
            rw [← hs h0 (by simp [Meaning.files, Srt.files])]; exact hc
          rw [this]; simp only; rw [← hr, hv]
  | op a b iha ihb =>
    intro m h hs
    simp only [eval] at h ⊢
    split at h
    · cases h
    · cases h
    · rename_i s v t s' v' t' ha hb
      split at h
      · cases h
      · rename_i u hu
        cases h
        have ea := iha _ ha (fun x hx => hs x (by
          simp only [Meaning.files, Srt.files, List.mem_append] at hx ⊢; exact Or.inl hx))
        have eb := ihb _ hb (fun x hx => hs x (by
          simp only [Meaning.files, Srt.files, List.mem_append] at hx ⊢; exact Or.inr hx))
        rw [ea, eb]; simp only; rw [← ho, hu]
    · cases h

/-! ### 3. Names carry no meaning -/

inductive Decl (N H : Type) where
  | file : N → H → Decl N H
  | let_ : N → Expr N → Decl N H
  | claim : Expr N → Decl N H

inductive Line (H V : Type) where
  | refused : Nat → Code → Line H V
  | formed : Nat → Srt H → V → Line H V
  | named : Nat → Line H V

def bind (env : Env N H V) (n : N) (m : Option (Meaning H V)) (pos : Nat) :
    Env N H V × List (Line H V) :=
  match look env n with
  | some _ => (env, [.refused pos .N002])
  | none => (env ++ [(n, m)], match m with | none => [] | some _ => [.named pos])

def step (w : World H C V) (env : Env N H V) (pos : Nat) : Decl N H → Env N H V × List (Line H V)
  | .file n h => bind env n (some (.file h)) pos
  | .let_ n e => match eval w env e with
    | .ok m => bind env n (some m) pos
    | .error c => let r := bind env n none pos; (r.1, .refused pos c :: r.2)
  | .claim e => match eval w env e with
    | .ok (.val s v _) => (env, [.formed pos s v])
    | .ok (.file _) => (env, [.refused pos .S007])
    | .error c => (env, [.refused pos c])

def run (w : World H C V) : Env N H V → Nat → List (Decl N H) → List (Line H V)
  | _, _, [] => []
  | env, pos, d :: ds => let r := step w env pos d; r.2 ++ run w r.1 (pos + 1) ds

def check (w : World H C V) (p : List (Decl N H)) : List (Line H V) := run w [] 1 p

def Expr.ren (π : N → N) : Expr N → Expr N
  | .var n => .var (π n)
  | .read e => .read (e.ren π)
  | .op a b => .op (a.ren π) (b.ren π)

def Decl.ren (π : N → N) : Decl N H → Decl N H
  | .file n h => .file (π n) h
  | .let_ n e => .let_ (π n) (e.ren π)
  | .claim e => .claim (e.ren π)

def renEnv (π : N → N) (env : Env N H V) : Env N H V := env.map (fun p => (π p.1, p.2))

theorem look_ren (π : N → N) (hπ : Function.Injective π) {α : Type} (env : List (N × α)) (n : N) :
    look (env.map (fun p => (π p.1, p.2))) (π n) = look env n := by
  induction env with
  | nil => rfl
  | cons p rest ih =>
    obtain ⟨y, a⟩ := p
    simp only [List.map, look]
    by_cases hy : y = n
    · subst hy; simp
    · have : π y ≠ π n := fun h => hy (hπ h)
      simp [hy, this, ih]

theorem eval_ren (w : World H C V) (π : N → N) (hπ : Function.Injective π) (env : Env N H V) :
    ∀ e : Expr N, eval w (renEnv π env) (e.ren π) = eval w env e := by
  intro e
  induction e with
  | var n => simp only [Expr.ren, eval, renEnv, look_ren π hπ]
  | read e ih => simp only [Expr.ren, eval, ih]
  | op a b iha ihb => simp only [Expr.ren, eval, iha, ihb]

theorem bind_ren (π : N → N) (hπ : Function.Injective π) (env : Env N H V) (n : N)
    (m : Option (Meaning H V)) (pos : Nat) :
    bind (renEnv π env) (π n) m pos = (renEnv π (bind env n m pos).1, (bind env n m pos).2) := by
  unfold bind
  rw [show look (renEnv π env) (π n) = look env n from look_ren π hπ env n]
  split <;> simp [renEnv]

theorem step_ren (w : World H C V) (π : N → N) (hπ : Function.Injective π) (env : Env N H V)
    (pos : Nat) (d : Decl N H) :
    step w (renEnv π env) pos (d.ren π) = (renEnv π (step w env pos d).1, (step w env pos d).2) := by
  cases d with
  | file n h => simp only [Decl.ren, step, bind_ren π hπ]
  | let_ n e =>
    simp only [Decl.ren, step, eval_ren w π hπ]
    split <;> simp [bind_ren π hπ]
  | claim e =>
    simp only [Decl.ren, step, eval_ren w π hπ]
    split <;> rfl

theorem run_ren (w : World H C V) (π : N → N) (hπ : Function.Injective π) :
    ∀ (p : List (Decl N H)) (env : Env N H V) (pos : Nat),
      run w (renEnv π env) pos (p.map (Decl.ren π)) = run w env pos p := by
  intro p
  induction p with
  | nil => intro _ _; rfl
  | cons d ds ih =>
    intro env pos
    simp only [List.map, run, step_ren w π hπ, ih]

theorem check_rename (w : World H C V) (π : N → N) (hπ : Function.Injective π)
    (p : List (Decl N H)) : check w (p.map (Decl.ren π)) = check w p := by
  have := run_ren w π hπ p [] 1
  simpa [check, renEnv] using this

/-! ### 4. Crossings hold for every value the precision allows -/

/-- `exceeds(x, c)` forms on [lo, hi] only if lo > c; `below(x, c)` only if hi < c. -/
theorem exceeds_sound (lo hi c x : Rat) (hf : c < lo) (hx : lo ≤ x ∧ x ≤ hi) : c < x :=
  Std.lt_of_lt_of_le hf hx.1

theorem below_sound (lo hi c x : Rat) (hf : hi < c) (hx : lo ≤ x ∧ x ≤ hi) : x < c :=
  Std.lt_of_le_of_lt hx.2 hf

end RealityScope

#print axioms RealityScope.trace_eq_sort
#print axioms RealityScope.scope
#print axioms RealityScope.check_rename
#print axioms RealityScope.exceeds_sound
#print axioms RealityScope.below_sound
