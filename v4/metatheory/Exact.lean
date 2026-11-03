/-
Exact.lean: the integer step of v4's exact decision procedure (plans/exact-decision-procedure.md,
v4/SPEC-EXACT.md section 4), in core Lean 4 (no Mathlib, no Batteries).

What is proved here (no `sorry`, only Lean's standard axioms; `#print axioms` at the end):
  decide_correct    for every choice function `pick`, `decideTop pick S = true` exactly when the
                    conjunction S of linear atoms (`f ≥ 0`, `m ∣ f`, integer coefficients) has a
                    solution in the naturals. Its steps: holds_tighten (normal form of an atom),
                    ground and hopeless atoms, pos_rule and neg_rule (one-signed variables),
                    lower_rule (the least solution is pinned by a lower atom: Cooper's step over ℕ),
                    enum_rule (a variable with an explicit range 0..B, from a ge atom whose other
                    coefficients are ≤ 0, is tried at each value; used when B + 1 ≤ Cooper's branches).
  merge_columns     region grouping: two variables with equal coefficient columns merge into one.
  abstraction       (L1) counts of selections over all row lists = the same over all multiplicity
                    vectors of row types.
  real_abstraction  the same over all inputs a reader accepts, given two reader hypotheses.
  Q.elim_step, Q.elim_correct, Q.elim_nat
                    rational elimination (SPEC-EXACT 4.1): Fourier–Motzkin over ℚ with strict and
                    non-strict atoms decides whether rational values for the named cells exist, for
                    any natural values of the row counts. Q.atom_scale, Q.atom_int: clearing
                    denominators and `F > 0` as `F − 1 ≥ 0` give the integer step's atoms.
  L4.kth            (L4) the k-th smallest of a list of rationals is u iff fewer than k values are
                    below u and at least k at or below it (max, min, median as instances).
  Var.sample_le, Var.population_le, Var.reach
                    the largest sample (population) variance of values in [L, U] is (U − L)²/2
                    ((U − L)²/4), reached by the two values L and U (Bhatia–Davis).
What is assumed, not proved here: the reader facts H1-H3 (SPEC-EXACT.md section 7), which
real_abstraction takes as hypotheses; that the Python solver computes this `decide` (a reviewed
correspondence: same steps, same order; tests/test_exact_proto.py checks it against brute force);
that the statement-to-system translation (SPEC-EXACT.md sections 3 and 5) matches the kernel's
semantics; and the share questions' polynomial-identity step (SPEC-EXACT.md 5.4, argued on paper).
-/
namespace Exact

/-! ## Linear forms and atoms over the naturals -/

/-- `dot l ρ` is the sum of `l[i] * ρ i`. Variable i is position i. -/
def dot : List Int → (Nat → Nat) → Int
  | [], _ => 0
  | a :: as, ρ => a * (ρ 0 : Int) + dot as (fun i => ρ (i + 1))

/-- A linear form: coefficients and a constant. -/
structure Lin where
  c : List Int
  k : Int
deriving DecidableEq

def Lin.eval (f : Lin) (ρ : Nat → Nat) : Int := dot f.c ρ + f.k

inductive Atom where
  | ge (f : Lin)
  | dvd (m : Nat) (f : Lin)
deriving DecidableEq

def Atom.form : Atom → Lin
  | .ge f => f
  | .dvd _ f => f

def Atom.holds : Atom → (Nat → Nat) → Prop
  | .ge f, ρ => 0 ≤ f.eval ρ
  | .dvd m f, ρ => (m : Int) ∣ f.eval ρ

def Sat (S : List Atom) (ρ : Nat → Nat) : Prop := ∀ A ∈ S, A.holds ρ

/-! ## Inserting and removing variable j -/

/-- `ins j v ρ`: the valuation with v at j and ρ's values shifted up from j on. -/
def ins : Nat → Nat → (Nat → Nat) → Nat → Nat
  | 0, v, _, 0 => v
  | 0, _, ρ, i + 1 => ρ i
  | _ + 1, _, ρ, 0 => ρ 0
  | j + 1, v, ρ, i + 1 => ins j v (fun i => ρ (i + 1)) i

/-- `del j ρ`: ρ without position j. -/
def del : Nat → (Nat → Nat) → Nat → Nat
  | 0, ρ, i => ρ (i + 1)
  | _ + 1, ρ, 0 => ρ 0
  | j + 1, ρ, i + 1 => del j (fun i => ρ (i + 1)) i

theorem ins_del (j : Nat) : ∀ (ρ : Nat → Nat), ins j (ρ j) (del j ρ) = ρ := by
  induction j with
  | zero => intro ρ; funext i; cases i <;> rfl
  | succ j ih =>
    intro ρ; funext i
    cases i with
    | zero => rfl
    | succ i =>
      show ins j (ρ (j + 1)) (fun i => del j (fun i => ρ (i + 1)) i) i = ρ (i + 1)
      have := ih (fun i => ρ (i + 1))
      exact congrFun this i

theorem ins_at (j : Nat) : ∀ (v : Nat) (ρ : Nat → Nat), ins j v ρ j = v := by
  induction j with
  | zero => intro v ρ; rfl
  | succ j ih => intro v ρ; exact ih v _

theorem dot_ins (l : List Int) : ∀ (j v : Nat) (ρ : Nat → Nat),
    dot l (ins j v ρ) = l.getD j 0 * (v : Int) + dot (l.eraseIdx j) ρ := by
  induction l with
  | nil => intro j v ρ; simp [dot]
  | cons a as ih =>
    intro j v ρ
    cases j with
    | zero =>
      simp only [dot, List.getD_cons_zero, List.eraseIdx_cons_zero]
      rfl
    | succ j =>
      simp only [dot, List.getD_cons_succ, List.eraseIdx_cons_succ]
      have h : (fun i => ins (j + 1) v ρ (i + 1)) = ins j v (fun i => ρ (i + 1)) := by
        funext i; rfl
      rw [h, ih j v]
      show a * (ρ 0 : Int) + (as.getD j 0 * v + dot (as.eraseIdx j) fun i => ρ (i + 1))
        = as.getD j 0 * v + (a * (ρ 0 : Int) + dot (as.eraseIdx j) fun i => ρ (i + 1))
      omega

/-! ## Linear combinations -/

def ladd : List Int → List Int → List Int
  | [], l => l
  | a :: as, [] => a :: as
  | a :: as, b :: bs => (a + b) :: ladd as bs

theorem dot_ladd : ∀ (l m : List Int) (ρ : Nat → Nat), dot (ladd l m) ρ = dot l ρ + dot m ρ
  | [], m, ρ => by simp [ladd, dot]
  | a :: as, [], ρ => by simp [ladd, dot]
  | a :: as, b :: bs, ρ => by
    simp only [ladd, dot]
    rw [dot_ladd as bs]
    rw [Int.add_mul]
    omega

theorem dot_smul (c : Int) : ∀ (l : List Int) (ρ : Nat → Nat), dot (l.map (c * ·)) ρ = c * dot l ρ
  | [], ρ => by simp [dot]
  | a :: as, ρ => by
    simp only [List.map, dot]
    rw [dot_smul c as, Int.mul_add, Int.mul_assoc]

def Lin.add (f g : Lin) : Lin := ⟨ladd f.c g.c, f.k + g.k⟩
def Lin.smul (c : Int) (f : Lin) : Lin := ⟨f.c.map (c * ·), c * f.k⟩
def Lin.const (k : Int) : Lin := ⟨[], k⟩

theorem eval_add (f g : Lin) (ρ) : (f.add g).eval ρ = f.eval ρ + g.eval ρ := by
  simp only [Lin.add, Lin.eval, dot_ladd]; omega

theorem eval_smul (c : Int) (f : Lin) (ρ) : (f.smul c).eval ρ = c * f.eval ρ := by
  simp only [Lin.smul, Lin.eval, dot_smul, Int.mul_add]

theorem eval_const (k : Int) (ρ) : (Lin.const k).eval ρ = k := by
  simp [Lin.const, Lin.eval, dot]

/-- The coefficient of variable j, and the form without it. -/
def Lin.cj (f : Lin) (j : Nat) : Int := f.c.getD j 0
def Lin.rest (f : Lin) (j : Nat) : Lin := ⟨f.c.eraseIdx j, f.k⟩

theorem eval_ins (f : Lin) (j v ρ) : f.eval (ins j v ρ) = f.cj j * (v : Int) + (f.rest j).eval ρ := by
  simp only [Lin.eval, Lin.cj, Lin.rest, dot_ins]; omega


/-! ## Atoms with variable j substituted -/

def Atom.map (g : Lin → Lin) : Atom → Atom
  | .ge f => .ge (g f)
  | .dvd m f => .dvd m (g f)

theorem form_map (g : Lin → Lin) (A : Atom) : (A.map g).form = g A.form := by cases A <;> rfl

/-- `y := v`: the form without j, constant plus `c_j * v`. -/
def substL (j : Nat) (v : Nat) (f : Lin) : Lin := (f.rest j).add (Lin.const (f.cj j * (v : Int)))
def subst (j : Nat) (v : Nat) (A : Atom) : Atom := A.map (substL j v)

theorem eval_substL (f : Lin) (j : Nat) (v : Nat) (ρ) : (substL j v f).eval ρ = f.eval (ins j v ρ) := by
  simp only [substL, eval_add, eval_const, eval_ins]; omega

theorem holds_subst (A : Atom) (j v ρ) : (subst j v A).holds ρ ↔ A.holds (ins j v ρ) := by
  cases A <;> simp only [subst, Atom.map, Atom.holds, eval_substL]

theorem eval_cj0 (f : Lin) (j : Nat) (h : f.cj j = 0) (v w ρ) : f.eval (ins j v ρ) = f.eval (ins j w ρ) := by
  rw [eval_ins, eval_ins, h]; simp

theorem holds_cj0 (A : Atom) (j : Nat) (h : A.form.cj j = 0) (v w ρ) :
    A.holds (ins j v ρ) ↔ A.holds (ins j w ρ) := by
  cases A with
  | ge f => simp only [Atom.holds]; rw [eval_cj0 f j h v w ρ]
  | dvd m f => simp only [Atom.holds]; rw [eval_cj0 f j h v w ρ]

def sumN (S : List Atom) (F : Atom → Nat) : Nat := (S.map F).foldr (· + ·) 0

theorem le_sumN (F : Atom → Nat) : ∀ (S : List Atom) (A : Atom), A ∈ S → F A ≤ sumN S F
  | [], _, h => by cases h
  | B :: S, A, h => by
    simp only [sumN, List.map, List.foldr] at *
    cases h with
    | head => omega
    | tail _ h => have := le_sumN F S A h; simp only [sumN] at this; omega

/-! ## One-signed variables -/

/-- Rule `pos`: no dvd atom has j and every coefficient of j is ≥ 0. Drop the atoms with j. -/
theorem pos_rule (S : List Atom) (j : Nat)
    (hd : ∀ m f, Atom.dvd m f ∈ S → f.cj j = 0) (hp : ∀ A ∈ S, 0 ≤ A.form.cj j) :
    (∃ ρ, Sat S ρ) ↔ ∃ ρ, Sat ((S.filter (fun A => A.form.cj j == 0)).map (subst j 0)) ρ := by
  constructor
  · rintro ⟨ρ, h⟩
    refine ⟨del j ρ, ?_⟩
    intro B hB
    simp only [List.mem_map, List.mem_filter, beq_iff_eq] at hB
    obtain ⟨A, ⟨hA, h0⟩, rfl⟩ := hB
    rw [holds_subst, holds_cj0 A j h0 0 (ρ j), ins_del]
    exact h A hA
  · rintro ⟨ρ, h⟩
    let y := sumN S (fun A => (-((A.form.rest j).eval ρ)).toNat)
    refine ⟨ins j y ρ, ?_⟩
    intro A hA
    by_cases h0 : A.form.cj j = 0
    · have := h (subst j 0 A) (List.mem_map.2 ⟨A, List.mem_filter.2 ⟨hA, by simp [h0]⟩, rfl⟩)
      rw [holds_subst, holds_cj0 A j h0 0 y] at this
      exact this
    · have hpos : 0 < A.form.cj j := by have := hp A hA; omega
      have hy : (-((A.form.rest j).eval ρ)).toNat ≤ y := le_sumN (fun A => (-((A.form.rest j).eval ρ)).toNat) S A hA
      have h1 := Int.self_le_toNat (-((A.form.rest j).eval ρ))
      have h2 : ((y : Nat) : Int) ≤ A.form.cj j * (y : Int) := by
        have := Int.mul_le_mul_of_nonneg_right (show (1 : Int) ≤ A.form.cj j by omega) (Int.natCast_nonneg y)
        simpa using this
      cases A with
      | ge f =>
        simp only [Atom.holds, eval_ins]
        simp only [Atom.form] at h2 h1 hy
        omega
      | dvd m f => exact absurd (hd m f hA) h0

/-- Rule `neg`: no dvd atom has j and every coefficient of j is ≤ 0. Then j := 0. -/
theorem neg_rule (S : List Atom) (j : Nat)
    (hd : ∀ m f, Atom.dvd m f ∈ S → f.cj j = 0) (hn : ∀ A ∈ S, A.form.cj j ≤ 0) :
    (∃ ρ, Sat S ρ) ↔ ∃ ρ, Sat (S.map (subst j 0)) ρ := by
  constructor
  · rintro ⟨ρ, h⟩
    refine ⟨del j ρ, ?_⟩
    intro B hB
    obtain ⟨A, hA, rfl⟩ := List.mem_map.1 hB
    rw [holds_subst]
    have hA' := h A hA
    rw [← ins_del j ρ] at hA'
    cases A with
    | ge f =>
      simp only [Atom.holds, eval_ins] at hA' ⊢
      have := Int.mul_nonneg (show 0 ≤ -f.cj j by have := hn _ hA; simp only [Atom.form] at this; omega)
        (Int.natCast_nonneg (ρ j))
      rw [Int.neg_mul] at this
      simp only [Int.ofNat_zero, Int.mul_zero]
      omega
    | dvd m f => exact (holds_cj0 (.dvd m f) j (hd m f hA) _ _ _).1 hA'
  · rintro ⟨ρ, h⟩
    exact ⟨ins j 0 ρ, fun A hA => (holds_subst A j 0 ρ).1 (h _ (List.mem_map.2 ⟨A, hA, rfl⟩))⟩

/-! ## The general step: the least solution is pinned by a lower atom -/

def lcmL : List Nat → Nat := List.foldr Nat.lcm 1

theorem dvd_lcmL : ∀ (l : List Nat) (m : Nat), m ∈ l → m ∣ lcmL l
  | [], _, h => by cases h
  | a :: l, m, h => by
    simp only [lcmL, List.foldr] at *
    cases h with
    | head => exact Nat.dvd_lcm_left _ _
    | tail _ h => exact Nat.dvd_trans (dvd_lcmL l m h) (Nat.dvd_lcm_right _ _)

theorem lcmL_pos : ∀ (l : List Nat), (∀ m ∈ l, 0 < m) → 0 < lcmL l
  | [], _ => by simp [lcmL]
  | a :: l, h => by
    simp only [lcmL, List.foldr]
    exact Nat.lcm_pos (h a (List.mem_cons_self ..)) (lcmL_pos l (fun m hm => h m (List.mem_cons_of_mem _ hm)))

/-- The moduli of the dvd atoms in which j occurs. -/
def modsAt (j : Nat) : List Atom → List Nat
  | [] => []
  | .dvd m f :: S => if f.cj j = 0 then modsAt j S else m :: modsAt j S
  | .ge _ :: S => modsAt j S

theorem mem_modsAt (j : Nat) : ∀ (S : List Atom) (m : Nat) (f : Lin), Atom.dvd m f ∈ S → f.cj j ≠ 0 → m ∈ modsAt j S
  | [], _, _, h, _ => by cases h
  | B :: S, m, f, h, hc => by
    cases h with
    | head => simp [modsAt, hc]
    | tail _ h =>
      have := mem_modsAt j S m f h hc
      cases B with
      | ge g => simpa [modsAt] using this
      | dvd m' g => unfold modsAt; split <;> simp [this]

theorem modsAt_mem (j : Nat) : ∀ (S : List Atom) (m : Nat), m ∈ modsAt j S → ∃ f, Atom.dvd m f ∈ S
  | [], _, h => by cases h
  | B :: S, m, h => by
    cases B with
    | ge g => obtain ⟨f, hf⟩ := modsAt_mem j S m (by simpa [modsAt] using h); exact ⟨f, List.mem_cons_of_mem _ hf⟩
    | dvd m' g =>
      unfold modsAt at h
      split at h
      · obtain ⟨f, hf⟩ := modsAt_mem j S m h; exact ⟨f, List.mem_cons_of_mem _ hf⟩
      · cases h with
        | head => exact ⟨g, List.mem_cons_self ..⟩
        | tail _ h => obtain ⟨f, hf⟩ := modsAt_mem j S m h; exact ⟨f, List.mem_cons_of_mem _ hf⟩

def delta (S : List Atom) (j : Nat) : Nat := lcmL (modsAt j S)

/-- t = k - (A without j): with a*y + e = k, t is a*y. -/
def tOf (A : Atom) (j k : Nat) : Lin := (Lin.const k).add ((A.form.rest j).smul (-1))

/-- Atom B multiplied by a, with a*y replaced by t. -/
def pinA (j a : Nat) (t : Lin) : Atom → Atom
  | .ge g => .ge ((t.smul (g.cj j)).add ((g.rest j).smul a))
  | .dvd m g => .dvd (m * a) ((t.smul (g.cj j)).add ((g.rest j).smul a))

def lowerCoef (A : Atom) (j : Nat) : Nat := (A.form.cj j).toNat

def isLower (A : Atom) (j : Nat) : Bool :=
  match A with
  | .ge f => decide (0 < f.cj j)
  | .dvd _ _ => false

/-- The system with a*y + e = k for the lower atom A (a its coefficient of j). -/
def pin (S : List Atom) (j : Nat) (A : Atom) (k : Nat) : List Atom :=
  let a := lowerCoef A j
  let t := tOf A j k
  .dvd a t :: .ge t :: S.map (pinA j a t)

theorem pinA_holds (B : Atom) (j a y : Nat) (t : Lin) (ρ) (ha : 0 < a) (ht : t.eval ρ = (a : Int) * y) :
    (pinA j a t B).holds ρ ↔ B.holds (ins j y ρ) := by
  have key : ∀ g : Lin, ((t.smul (g.cj j)).add ((g.rest j).smul a)).eval ρ = (a : Int) * g.eval (ins j y ρ) := by
    intro g
    rw [eval_add, eval_smul, eval_smul, ht, eval_ins, Int.mul_add, ← Int.mul_assoc, ← Int.mul_assoc,
      Int.mul_comm (g.cj j) (a : Int)]
  have ha' : (0 : Int) < a := by omega
  cases B with
  | ge g =>
    simp only [pinA, Atom.holds, key]
    constructor
    · intro h
      apply Classical.byContradiction
      intro hn
      have := Int.mul_neg_of_pos_of_neg ha' (show g.eval (ins j y ρ) < 0 by omega)
      omega
    · intro h; exact Int.mul_nonneg (by omega) h
  | dvd m g =>
    simp only [pinA, Atom.holds, key]
    rw [Int.natCast_mul, Int.mul_comm (m : Int) (a : Int)]
    exact Int.mul_dvd_mul_iff_left (by omega)

theorem lower_rule (S : List Atom) (j : Nat) (hm : ∀ m f, Atom.dvd m f ∈ S → 0 < m) :
    (∃ ρ, Sat S ρ) ↔
      (∃ v, v < delta S j ∧ ∃ ρ, Sat (S.map (subst j v)) ρ) ∨
      (∃ A ∈ S, isLower A j = true ∧ ∃ k, k < lowerCoef A j * delta S j ∧ ∃ ρ, Sat (pin S j A k) ρ) := by
  have hδ : 0 < delta S j := lcmL_pos _ (fun m h => by obtain ⟨f, hf⟩ := modsAt_mem j S m h; exact hm m f hf)
  constructor
  · rintro ⟨ρ0, h0⟩
    -- strong induction on the value of j
    suffices H : ∀ y ρ, Sat S (ins j y ρ) → _ from by
      have := H (ρ0 j) (del j ρ0) (by rw [ins_del]; exact h0); exact this
    intro y
    induction y using Nat.strongRecOn with
    | _ y ih =>
    intro ρ h
    by_cases hy : y < delta S j
    · exact Or.inl ⟨y, hy, ρ, fun B hB => by
        obtain ⟨A, hA, rfl⟩ := List.mem_map.1 hB
        exact (holds_subst A j y ρ).2 (h A hA)⟩
    by_cases h2 : Sat S (ins j (y - delta S j) ρ)
    · exact ih (y - delta S j) (by omega) ρ h2
    -- some atom fails at y - delta: it is a lower atom, and pins y
    have : ∃ B ∈ S, ¬ B.holds (ins j (y - delta S j) ρ) :=
      Classical.byContradiction fun hn => h2 fun B hB => Classical.byContradiction fun hb => hn ⟨B, hB, hb⟩
    obtain ⟨B, hB, hfail⟩ := this
    have hyd : ((y - delta S j : Nat) : Int) = (y : Int) - (delta S j : Int) := by omega
    cases B with
    | dvd m g =>
      exfalso
      apply hfail
      have hy0 := h _ hB
      simp only [Atom.holds, eval_ins] at hy0 ⊢
      by_cases hc : g.cj j = 0
      · rw [hc] at hy0 ⊢; simpa using hy0
      · have hmd : (m : Int) ∣ (delta S j : Int) :=
          Int.natCast_dvd_natCast.2 (dvd_lcmL _ m (mem_modsAt j S m g hB hc))
        have : g.cj j * ((y - delta S j : Nat) : Int) + (g.rest j).eval ρ
            = (g.cj j * (y : Int) + (g.rest j).eval ρ) - g.cj j * (delta S j : Int) := by
          rw [hyd, Int.mul_sub]; omega
        rw [this]
        exact Int.dvd_sub hy0 (Int.dvd_trans hmd (Int.dvd_mul_left _ _))
    | ge g =>
      have hy0 := h _ hB
      simp only [Atom.holds, eval_ins] at hy0 hfail
      have hsub : g.cj j * ((y - delta S j : Nat) : Int) = g.cj j * (y : Int) - g.cj j * (delta S j : Int) := by
        rw [hyd, Int.mul_sub]
      have hc : 0 < g.cj j := by
        apply Classical.byContradiction
        intro hc
        have := Int.mul_nonneg (show 0 ≤ -g.cj j by omega) (Int.natCast_nonneg (delta S j))
        rw [Int.neg_mul] at this
        omega
      refine Or.inr ⟨.ge g, hB, by simp [isLower, hc], (g.eval (ins j y ρ)).toNat, ?_, ρ, ?_⟩
      · have : ((lowerCoef (.ge g) j * delta S j : Nat) : Int) = g.cj j * (delta S j : Int) := by
          simp only [lowerCoef, Atom.form, Int.natCast_mul, Int.toNat_of_nonneg (show 0 ≤ g.cj j by omega)]
        have e1 := eval_ins g j y ρ
        omega
      · have ha : 0 < lowerCoef (.ge g) j := by simp only [lowerCoef, Atom.form]; omega
        have hav : ((lowerCoef (.ge g) j : Nat) : Int) = g.cj j := by
          simp only [lowerCoef, Atom.form]; exact Int.toNat_of_nonneg (by omega)
        have ht : (tOf (.ge g) j (g.eval (ins j y ρ)).toNat).eval ρ = (lowerCoef (.ge g) j : Int) * y := by
          simp only [tOf, eval_add, eval_const, eval_smul, Atom.form]
          rw [Int.toNat_of_nonneg (by rw [eval_ins]; omega), eval_ins, hav]
          omega
        intro C hC
        simp only [pin] at hC
        cases hC with
        | head => simp only [Atom.holds]; rw [ht]; exact Int.dvd_mul_right _ _
        | tail _ hC =>
          cases hC with
          | head => simp only [Atom.holds]; rw [ht]; exact Int.mul_nonneg (by omega) (by omega)
          | tail _ hC =>
            obtain ⟨D, hD, rfl⟩ := List.mem_map.1 hC
            exact (pinA_holds D j _ y _ ρ ha ht).2 (h D hD)
  · rintro (⟨v, _, ρ, h⟩ | ⟨A, hA, hl, k, _, ρ, h⟩)
    · exact ⟨ins j v ρ, fun A hA => (holds_subst A j v ρ).1 (h _ (List.mem_map.2 ⟨A, hA, rfl⟩))⟩
    · have ha : 0 < lowerCoef A j := by
        cases A with
        | ge f => simp [isLower] at hl; simp only [lowerCoef, Atom.form]; omega
        | dvd _ _ => simp [isLower] at hl
      have hd := h _ (List.mem_cons_self ..)
      have hg := h _ (List.mem_cons_of_mem _ (List.mem_cons_self ..))
      simp only [Atom.holds] at hd hg
      let t := tOf A j k
      let y := (t.eval ρ / (lowerCoef A j : Int)).toNat
      have ht : t.eval ρ = (lowerCoef A j : Int) * y := by
        have h1 := Int.mul_ediv_cancel' hd
        have h2 : 0 ≤ t.eval ρ / (lowerCoef A j : Int) := Int.ediv_nonneg hg (by omega)
        simp only [y, Int.toNat_of_nonneg h2]
        exact h1.symm
      refine ⟨ins j y ρ, fun B hB => (pinA_holds B j _ y t ρ ha ht).1 ?_⟩
      exact h _ (List.mem_cons_of_mem _ (List.mem_cons_of_mem _ (List.mem_map.2 ⟨B, hB, rfl⟩)))

/-! ## Normal form of an atom (each step is an equivalence) -/

/-- Trailing zero coefficients dropped (the prototype's sparse forms have none). -/
def trimZ : List Int → List Int
  | [] => []
  | a :: as => if a = 0 ∧ trimZ as = [] then [] else a :: trimZ as

theorem dot_trimZ : ∀ (l : List Int) (ρ : Nat → Nat), dot (trimZ l) ρ = dot l ρ
  | [], _ => rfl
  | a :: as, ρ => by
    unfold trimZ
    split
    · rename_i h
      obtain ⟨h1, h2⟩ := h
      have := dot_trimZ as (fun i => ρ (i + 1))
      rw [h2] at this
      simp only [dot, h1] at this ⊢
      omega
    · simp only [dot]; rw [dot_trimZ as]

theorem length_trimZ : ∀ (l : List Int), (trimZ l).length ≤ l.length
  | [] => Nat.le_refl _
  | a :: as => by
    unfold trimZ; split
    · simp
    · simp only [List.length_cons]; have := length_trimZ as; omega

def gcdL : List Int → Nat
  | [] => 0
  | c :: cs => Nat.gcd c.natAbs (gcdL cs)

theorem gcdL_dvd : ∀ (l : List Int) (c : Int), c ∈ l → ((gcdL l : Nat) : Int) ∣ c
  | [], _, h => by cases h
  | a :: l, c, h => by
    cases h with
    | head => exact Int.ofNat_dvd_left.2 (Nat.gcd_dvd_left _ _)
    | tail _ h =>
      exact Int.dvd_trans (Int.natCast_dvd_natCast.2 (Nat.gcd_dvd_right _ _)) (gcdL_dvd l c h)

theorem dot_div (g : Int) : ∀ (l : List Int), (∀ c ∈ l, g ∣ c) → ∀ ρ, dot l ρ = g * dot (l.map (· / g)) ρ
  | [], _, ρ => by simp [dot]
  | a :: as, h, ρ => by
    simp only [List.map, dot]
    rw [dot_div g as (fun c hc => h c (List.mem_cons_of_mem _ hc)), Int.mul_add, ← Int.mul_assoc,
      Int.mul_ediv_cancel' (h a (List.mem_cons_self ..))]

theorem dot_mod (m : Int) : ∀ (l : List Int) ρ, dot l ρ = dot (l.map (· % m)) ρ + m * dot (l.map (· / m)) ρ
  | [], ρ => by simp [dot]
  | a :: as, ρ => by
    simp only [List.map, dot]
    rw [dot_mod m as]
    have := Int.mul_ediv_add_emod a m
    have e : a * (ρ 0 : Int) = (a % m) * ρ 0 + m * (a / m) * ρ 0 := by
      conv => lhs; rw [← this]
      rw [Int.add_mul, Int.add_comm]
    rw [e, Int.mul_add, Int.mul_assoc]
    omega

/-- One atom's normal form, a list of atoms holding exactly when it holds.
  ge: coefficients divided by their gcd g (when g ≥ 2), constant floored.
  dvd 0: f = 0, as f ≥ 0 and -f ≥ 0.
  dvd m (m ≥ 1): coefficients and constant mod m, then m, they and the constant divided by their
  common gcd g; modulus 1 becomes 0 ≥ 0.
  Then trailing zero coefficients are dropped. -/
def tighten : Atom → List Atom
  | .ge f =>
    let g := gcdL f.c
    if g ≤ 1 then [.ge ⟨trimZ f.c, f.k⟩]
    else [.ge ⟨trimZ (f.c.map (· / (g : Int))), f.k / (g : Int)⟩]
  | .dvd 0 f => [.ge ⟨trimZ f.c, f.k⟩, .ge ⟨trimZ (f.c.map ((-1) * ·)), -f.k⟩]
  | .dvd (m + 1) f =>
    let d := f.c.map (· % ((m + 1 : Nat) : Int))
    let c0 := f.k % ((m + 1 : Nat) : Int)
    let g := Nat.gcd (m + 1) (gcdL (c0 :: d))
    if (m + 1) / g = 1 then [.ge ⟨[], 0⟩]
    else [.dvd ((m + 1) / g) ⟨trimZ (d.map (· / (g : Int))), c0 / (g : Int)⟩]

theorem ge_tighten (s k : Int) (g : Int) (hg : 0 < g) : 0 ≤ g * s + k ↔ 0 ≤ s + k / g := by
  have e := Int.mul_ediv_add_emod k g
  have r0 := Int.emod_nonneg k (show g ≠ 0 by omega)
  have r1 := Int.emod_lt_of_pos k hg
  constructor
  · intro h
    apply Classical.byContradiction
    intro hn
    have := Int.mul_le_mul_of_nonneg_left (show s + k / g ≤ -1 by omega) (show 0 ≤ g by omega)
    rw [Int.mul_add] at this
    omega
  · intro h
    have := Int.mul_nonneg (show 0 ≤ g by omega) h
    rw [Int.mul_add] at this
    omega

theorem holds_tighten (A : Atom) (ρ) : (∀ B ∈ tighten A, B.holds ρ) ↔ A.holds ρ := by
  cases A with
  | ge f =>
    simp only [tighten]
    split
    · simp [Atom.holds, Lin.eval, dot_trimZ]
    · rename_i hg
      simp only [List.mem_singleton, forall_eq, Atom.holds, Lin.eval, dot_trimZ]
      rw [dot_div (gcdL f.c : Int) f.c (gcdL_dvd f.c) ρ]
      exact (ge_tighten _ _ _ (by omega)).symm
  | dvd m f =>
    cases m with
    | zero =>
      simp only [tighten, List.mem_cons, List.mem_nil_iff, or_false, forall_eq_or_imp, forall_eq,
        Atom.holds, Lin.eval, dot_trimZ, dot_smul, Int.natCast_zero, Int.zero_dvd]
      omega
    | succ m =>
      simp only [tighten]
      have hM : (0 : Int) < ((m + 1 : Nat) : Int) := by omega
      let M : Int := ((m + 1 : Nat) : Int)
      have hmod : (M ∣ f.eval ρ) ↔ M ∣ dot (f.c.map (· % M)) ρ + f.k % M := by
        simp only [Lin.eval]
        rw [dot_mod M f.c ρ]
        have e := Int.mul_ediv_add_emod f.k M
        have : dot (List.map (fun x => x % M) f.c) ρ + M * dot (List.map (fun x => x / M) f.c) ρ + f.k
            = M * (dot (List.map (fun x => x / M) f.c) ρ + f.k / M) + (dot (List.map (fun x => x % M) f.c) ρ + f.k % M) := by
          rw [Int.mul_add]; omega
        rw [this]
        exact Int.dvd_add_right (Int.dvd_mul_right _ _)
      let d := f.c.map (· % M)
      let c0 := f.k % M
      let g := Nat.gcd (m + 1) (gcdL (c0 :: d))
      have hg : 0 < g := Nat.gcd_pos_of_pos_left _ (by omega)
      have hgm : g ∣ m + 1 := Nat.gcd_dvd_left _ _
      have hgd : ∀ c ∈ c0 :: d, (g : Int) ∣ c := fun c hc =>
        Int.dvd_trans (Int.natCast_dvd_natCast.2 (Nat.gcd_dvd_right _ _)) (gcdL_dvd _ c hc)
      have hgc0 : (g : Int) ∣ c0 := hgd c0 (List.mem_cons_self ..)
      have hgdd : ∀ c ∈ d, (g : Int) ∣ c := fun c hc => hgd c (List.mem_cons_of_mem _ hc)
      have hdiv : (M ∣ dot d ρ + c0) ↔ (((m + 1) / g : Nat) : Int) ∣ dot (d.map (· / (g : Int))) ρ + c0 / (g : Int) := by
        have e1 : M = (g : Int) * (((m + 1) / g : Nat) : Int) := by
          simp only [M]; rw [← Int.natCast_mul, Nat.mul_div_cancel' hgm]
        have e2 : dot d ρ + c0 = (g : Int) * (dot (d.map (· / (g : Int))) ρ + c0 / (g : Int)) := by
          rw [Int.mul_add, ← dot_div (g : Int) d hgdd ρ, Int.mul_ediv_cancel' hgc0]
        rw [e1, e2]
        exact Int.mul_dvd_mul_iff_left (by omega)
      split
      · rename_i h1
        have key : M ∣ f.eval ρ := hmod.2 (hdiv.2 (by rw [show (m + 1) / g = 1 from h1]; exact Int.one_dvd _))
        constructor
        · intro _; exact key
        · intro _ B hB
          simp only [List.mem_singleton] at hB
          subst hB
          simp [Atom.holds, Lin.eval, dot]
      · constructor
        · intro h
          have := h _ (List.mem_singleton_self _)
          simp only [Atom.holds, Lin.eval, dot_trimZ] at this
          exact hmod.2 (hdiv.2 this)
        · intro h B hB
          simp only [List.mem_singleton] at hB
          subst hB
          simp only [Atom.holds, Lin.eval, dot_trimZ]
          exact hdiv.1 (hmod.1 h)

/-- Repeats dropped, first occurrences kept in order. -/
def dedupGo : List Atom → List Atom → List Atom
  | [], acc => acc.reverse
  | a :: as, acc => if a ∈ acc then dedupGo as acc else dedupGo as (a :: acc)

theorem mem_dedupGo : ∀ (l acc : List Atom) (x : Atom), x ∈ dedupGo l acc ↔ x ∈ l ∨ x ∈ acc
  | [], acc, x => by simp [dedupGo]
  | a :: as, acc, x => by
    unfold dedupGo
    split
    · rename_i h
      rw [mem_dedupGo as acc x, List.mem_cons]
      constructor
      · rintro (h1 | h1)
        · exact Or.inl (Or.inr h1)
        · exact Or.inr h1
      · rintro ((rfl | h1) | h1)
        · exact Or.inr h
        · exact Or.inl h1
        · exact Or.inr h1
    · rw [mem_dedupGo as (a :: acc) x]
      simp only [List.mem_cons]
      constructor
      · rintro (h1 | h1 | h1)
        · exact Or.inl (Or.inr h1)
        · exact Or.inl (Or.inl h1)
        · exact Or.inr h1
      · rintro ((h1 | h1) | h1)
        · exact Or.inr (Or.inl h1)
        · exact Or.inl h1
        · exact Or.inr (Or.inr h1)

def normalize (S : List Atom) : List Atom := dedupGo (S.flatMap tighten) []

theorem mem_normalize (S : List Atom) (B : Atom) : B ∈ normalize S ↔ ∃ A ∈ S, B ∈ tighten A := by
  simp [normalize, mem_dedupGo, List.mem_flatMap]

theorem sat_normalize (S : List Atom) (ρ) : Sat (normalize S) ρ ↔ Sat S ρ := by
  constructor
  · intro h A hA
    exact (holds_tighten A ρ).1 (fun B hB => h B ((mem_normalize S B).2 ⟨A, hA, hB⟩))
  · intro h B hB
    obtain ⟨A, hA, hB⟩ := (mem_normalize S B).1 hB
    exact (holds_tighten A ρ).2 (h A hA) B hB

theorem tighten_len (A : Atom) (n : Nat) (h : A.form.c.length ≤ n) : ∀ B ∈ tighten A, B.form.c.length ≤ n := by
  intro B hB
  cases A with
  | ge f =>
    simp only [tighten] at hB
    split at hB <;> simp only [List.mem_singleton] at hB <;> subst hB <;> simp only [Atom.form] at h ⊢
    · exact Nat.le_trans (length_trimZ _) h
    · exact Nat.le_trans (length_trimZ _) (by simpa using h)
  | dvd m f =>
    cases m with
    | zero =>
      simp only [tighten, List.mem_cons, List.mem_nil_iff, or_false] at hB
      simp only [Atom.form] at h
      rcases hB with rfl | rfl
      · exact Nat.le_trans (length_trimZ _) h
      · exact Nat.le_trans (length_trimZ _) (by simpa using h)
    | succ m =>
      simp only [tighten] at hB
      split at hB <;> simp only [List.mem_singleton] at hB <;> subst hB <;> simp only [Atom.form] at h ⊢
      · exact Nat.zero_le _
      · exact Nat.le_trans (length_trimZ _) (by simpa using h)

theorem tighten_mod (A : Atom) : ∀ m f, Atom.dvd m f ∈ tighten A → 0 < m := by
  intro m' f' hB
  cases A with
  | ge f => simp only [tighten] at hB; split at hB <;> simp at hB
  | dvd m f =>
    cases m with
    | zero => simp [tighten] at hB
    | succ m =>
      simp only [tighten] at hB
      split at hB
      · simp at hB
      · simp only [List.mem_singleton, Atom.dvd.injEq] at hB
        obtain ⟨rfl, -⟩ := hB
        apply Nat.div_pos (Nat.le_of_dvd (by omega) (Nat.gcd_dvd_left _ _)) (Nat.gcd_pos_of_pos_left _ (by omega))

/-! ## The decision procedure -/

def ground (A : Atom) : Bool := A.form.c.isEmpty

def groundOK : Atom → Bool
  | .ge f => decide (0 ≤ f.k)
  | .dvd m f => decide ((m : Int) ∣ f.k)

/-- A ge atom no naturals satisfy: every coefficient ≤ 0 and the constant < 0. -/
def hopeless : Atom → Bool
  | .ge f => decide (f.k < 0) && f.c.all (fun c => decide (c ≤ 0))
  | .dvd _ _ => false

def noDvdAt (S : List Atom) (j : Nat) : Bool :=
  S.all (fun A => match A with
    | .dvd _ f => f.cj j == 0
    | .ge _ => true)

def allNonneg (S : List Atom) (j : Nat) : Bool := S.all (fun A => decide (0 ≤ A.form.cj j))
def allNonpos (S : List Atom) (j : Nat) : Bool := S.all (fun A => decide (A.form.cj j ≤ 0))

def branches (S : List Atom) (j : Nat) : Nat :=
  delta S j * (1 + S.foldr (fun A acc => if isLower A j then (A.form.cj j).toNat + acc else acc) 0)

/-- An explicit bound on j from one atom: a ge atom whose coefficient of j is < 0 and none > 0, so
j ≤ k / -c in the naturals. -/
def ubA (j : Nat) : Atom → Option Nat
  | .ge f => if f.cj j < 0 ∧ f.c.all (fun c => decide (c ≤ 0)) = true then some (f.k / (-(f.cj j))).toNat else none
  | .dvd _ _ => none

def omin : Option Nat → Option Nat → Option Nat
  | some a, some b => some (min a b)
  | some a, none => some a
  | none, b => b

/-- The least explicit bound on j over the atoms, if any. -/
def ub (S : List Atom) (j : Nat) : Option Nat := S.foldr (fun A acc => omin (ubA j A) acc) none

/-- The enumeration rule applies: j has an explicit range no larger than Cooper's branches. -/
def enumOK (S : List Atom) (j : Nat) : Bool :=
  match ub S j with
  | some B => decide (B + 1 ≤ branches S j)
  | none => false

/-- `decideN pick n S`: is there a solution in the naturals? (correct when every coefficient list has
length ≤ n; `pick` chooses the variable to eliminate and may be any function.) -/
def decideN (pick : List Atom → Nat) : Nat → List Atom → Bool
  | 0, S => (normalize S).all groundOK
  | n + 1, S =>
    let S1 := normalize S
    if !((S1.filter ground).all groundOK) then false
    else
      let S2 := S1.filter (fun A => !ground A)
      if S2.isEmpty then true
      else if S2.any hopeless then false
      else
        let j := min (pick S2) n
        if noDvdAt S2 j && allNonneg S2 j then
          decideN pick n ((S2.filter (fun A => A.form.cj j == 0)).map (subst j 0))
        else if noDvdAt S2 j && allNonpos S2 j then
          decideN pick n (S2.map (subst j 0))
        else if enumOK S2 j then
          (List.range ((ub S2 j).getD 0 + 1)).any (fun v => decideN pick n (S2.map (subst j v)))
        else
          (List.range (delta S2 j)).any (fun v => decideN pick n (S2.map (subst j v))) ||
          S2.any (fun A => isLower A j &&
            (List.range (lowerCoef A j * delta S2 j)).any (fun k => decideN pick n (pin S2 j A k)))

def maxLen (S : List Atom) : Nat := S.foldr (fun A m => max A.form.c.length m) 0

/-- The procedure: n is the longest coefficient list. -/
def decideTop (pick : List Atom → Nat) (S : List Atom) : Bool := decideN pick (maxLen S) S

/-! ## The checker's choice of variable (SPEC-EXACT 4 step 5; any choice is correct, see decide_correct) -/

def present (S : List Atom) (j : Nat) : Bool := S.any (fun A => A.form.cj j != 0)

def lowerRule (S : List Atom) (j : Nat) : Bool := !(noDvdAt S j && (allNonneg S j || allNonpos S j))

/-- Cooper's branches for j, or j's explicit range when that is fewer (the enumeration rule). -/
def cost (S : List Atom) (j : Nat) : Nat :=
  match ub S j with
  | some B => min (B + 1) (branches S j)
  | none => branches S j

/-- `(lowerRule, branches, j)` of j is lexicographically below that of i. -/
def better (S : List Atom) (j i : Nat) : Bool :=
  let rj := if lowerRule S j then 1 else 0
  let ri := if lowerRule S i then 1 else 0
  rj < ri || (rj == ri && cost S j < cost S i)

/-- Among the variables present: a one-signed one if any, then the fewest branches (cost), then the smallest. -/
def pickStd (S : List Atom) : Nat :=
  match (List.range (S.foldr (fun A m => max A.form.c.length m) 0)).filter (present S) with
  | [] => 0
  | j :: js => js.foldl (fun best i => if better S i best then i else best) j

/-! ## Correctness of decide -/

theorem ground_holds (A : Atom) (hA : ground A = true) (ρ) : A.holds ρ ↔ groundOK A = true := by
  have hc : A.form.c = [] := by simpa [ground] using hA
  cases A with
  | ge f => simp only [Atom.form] at hc; simp [Atom.holds, groundOK, Lin.eval, hc, dot]
  | dvd m f => simp only [Atom.form] at hc; simp [Atom.holds, groundOK, Lin.eval, hc, dot]

theorem dot_nonpos : ∀ (l : List Int), (∀ c ∈ l, c ≤ 0) → ∀ ρ, dot l ρ ≤ 0
  | [], _, _ => by simp [dot]
  | a :: as, h, ρ => by
    simp only [dot]
    have h1 := Int.mul_nonneg (show 0 ≤ -a by have := h a (List.mem_cons_self ..); omega) (Int.natCast_nonneg (ρ 0))
    have h2 := dot_nonpos as (fun c hc => h c (List.mem_cons_of_mem _ hc)) (fun i => ρ (i + 1))
    rw [Int.neg_mul] at h1
    omega

theorem hopeless_not (A : Atom) (hA : hopeless A = true) (ρ) : ¬ A.holds ρ := by
  cases A with
  | ge f =>
    simp only [hopeless, Bool.and_eq_true, decide_eq_true_eq, List.all_eq_true] at hA
    simp only [Atom.holds, Lin.eval]
    have := dot_nonpos f.c (fun c hc => hA.2 c hc) ρ
    omega
  | dvd _ _ => simp [hopeless] at hA

theorem length_ladd : ∀ (l m : List Int), (ladd l m).length = max l.length m.length
  | [], m => by simp [ladd]
  | a :: as, [] => by simp [ladd]
  | a :: as, b :: bs => by simp only [ladd, List.length_cons, length_ladd as bs]; omega

theorem len_erase (l : List Int) (j n : Nat) (h : l.length ≤ n + 1) (hj : j ≤ n) : (l.eraseIdx j).length ≤ n := by
  rw [List.length_eraseIdx]; split <;> omega

theorem len_subst (A : Atom) (j v n : Nat) (h : A.form.c.length ≤ n + 1) (hj : j ≤ n) :
    (subst j v A).form.c.length ≤ n := by
  rw [subst, form_map]
  simp only [substL, Lin.add, Lin.const, Lin.rest, length_ladd, List.length_nil]
  have := len_erase _ j n h hj
  omega

theorem len_pin (S : List Atom) (j n : Nat) (A : Atom) (k : Nat) (hS : ∀ B ∈ S, B.form.c.length ≤ n + 1)
    (hA : A.form.c.length ≤ n + 1) (hj : j ≤ n) : ∀ B ∈ pin S j A k, B.form.c.length ≤ n := by
  have ht : (tOf A j k).c.length ≤ n := by
    simp only [tOf, Lin.add, Lin.const, Lin.smul, Lin.rest, length_ladd, List.length_nil, List.length_map]
    have := len_erase _ j n hA hj; omega
  intro B hB
  simp only [pin, List.mem_cons, List.mem_map] at hB
  rcases hB with rfl | rfl | ⟨C, hC, rfl⟩
  · exact ht
  · exact ht
  · have := len_erase _ j n (hS C hC) hj
    cases C with
    | ge g =>
      simp only [pinA, Atom.form, Lin.add, Lin.smul, Lin.rest, length_ladd, List.length_map] at this ⊢; omega
    | dvd m g =>
      simp only [pinA, Atom.form, Lin.add, Lin.smul, Lin.rest, length_ladd, List.length_map] at this ⊢; omega

/-! ## The enumeration rule: a variable with an explicit range is tried at each value -/

theorem dot_nonpos' : ∀ (l : List Int), l.all (fun c => decide (c ≤ 0)) = true → ∀ ρ, dot l ρ ≤ 0 :=
  fun l h ρ => dot_nonpos l (fun c hc => by have := List.all_eq_true.1 h c hc; simpa using this) ρ

theorem ubA_le (j : Nat) (A : Atom) (b : Nat) (hb : ubA j A = some b) (ρ : Nat → Nat) (h : A.holds ρ) :
    ρ j ≤ b := by
  cases A with
  | dvd m f => simp [ubA] at hb
  | ge f =>
    simp only [ubA] at hb
    split at hb
    · rename_i hc
      obtain ⟨hneg, hall⟩ := hc
      simp only [Option.some.injEq] at hb
      subst hb
      have hr : (f.rest j).eval (del j ρ) ≤ f.k := by
        have : ((f.c.eraseIdx j).all (fun c => decide (c ≤ 0))) = true :=
          List.all_eq_true.2 (fun c hc => List.all_eq_true.1 hall c (List.mem_of_mem_eraseIdx hc))
        have := dot_nonpos' _ this (del j ρ)
        simp only [Lin.eval, Lin.rest]; omega
      have he : f.eval ρ = f.cj j * (ρ j : Int) + (f.rest j).eval (del j ρ) := by
        have := eval_ins f j (ρ j) (del j ρ); rw [ins_del] at this; exact this
      simp only [Atom.holds] at h
      have hm : (ρ j : Int) * (-(f.cj j)) ≤ f.k := by
        rw [Int.mul_neg, Int.mul_comm]; omega
      have hd : (ρ j : Int) ≤ f.k / (-(f.cj j)) := (Int.le_ediv_iff_mul_le (by omega)).2 hm
      have := Int.self_le_toNat (f.k / (-(f.cj j)))
      omega
    · simp at hb

theorem ub_le (j : Nat) : ∀ (S : List Atom) (B : Nat), ub S j = some B → ∀ ρ, Sat S ρ → ρ j ≤ B
  | [], B, h, _, _ => by simp [ub] at h
  | A :: S, B, h, ρ, hs => by
    have hA := hs A (List.mem_cons_self ..)
    have hS : Sat S ρ := fun C hC => hs C (List.mem_cons_of_mem _ hC)
    have ih := ub_le j S
    simp only [ub, List.foldr] at h
    change omin (ubA j A) (ub S j) = some B at h
    cases ha : ubA j A with
    | none => rw [ha] at h; exact ih B h ρ hS
    | some a =>
      cases hu : ub S j with
      | none => rw [ha, hu] at h; simp only [omin, Option.some.injEq] at h; subst h; exact ubA_le j A a ha ρ hA
      | some c =>
        rw [ha, hu] at h; simp only [omin, Option.some.injEq] at h; subst h
        have := ubA_le j A a ha ρ hA; have := ih c hu ρ hS; omega

theorem enum_rule (S : List Atom) (j B : Nat) (hB : ub S j = some B) :
    (∃ ρ, Sat S ρ) ↔ ∃ v, v < B + 1 ∧ ∃ ρ, Sat (S.map (subst j v)) ρ := by
  constructor
  · rintro ⟨ρ, h⟩
    refine ⟨ρ j, by have := ub_le j S B hB ρ h; omega, del j ρ, ?_⟩
    intro C hC
    obtain ⟨A, hA, rfl⟩ := List.mem_map.1 hC
    rw [holds_subst, ins_del]; exact h A hA
  · rintro ⟨v, _, ρ, h⟩
    exact ⟨ins j v ρ, fun A hA => (holds_subst A j v ρ).1 (h _ (List.mem_map.2 ⟨A, hA, rfl⟩))⟩

theorem decideN_correct (pick : List Atom → Nat) :
    ∀ n S, (∀ A ∈ S, A.form.c.length ≤ n) → (decideN pick n S = true ↔ ∃ ρ, Sat S ρ) := by
  intro n
  induction n with
  | zero =>
    intro S hS
    have hg : ∀ B ∈ normalize S, ground B = true := by
      intro B hB
      obtain ⟨A, hA, hB⟩ := (mem_normalize S B).1 hB
      have := tighten_len A 0 (hS A hA) B hB
      simp only [ground, List.isEmpty_iff]
      exact List.eq_nil_of_length_eq_zero (by omega)
    simp only [decideN, List.all_eq_true]
    constructor
    · intro h
      exact ⟨fun _ => 0, (sat_normalize S _).1 fun B hB => (ground_holds B (hg B hB) _).2 (h B hB)⟩
    · rintro ⟨ρ, h⟩ B hB
      exact (ground_holds B (hg B hB) ρ).1 ((sat_normalize S ρ).2 h B hB)
  | succ n ih =>
    intro S hS
    have hS1 : ∀ B ∈ normalize S, B.form.c.length ≤ n + 1 := by
      intro B hB; obtain ⟨A, hA, hB⟩ := (mem_normalize S B).1 hB; exact tighten_len A _ (hS A hA) B hB
    have hm1 : ∀ m f, Atom.dvd m f ∈ normalize S → 0 < m := by
      intro m f hB; obtain ⟨A, hA, hB⟩ := (mem_normalize S _).1 hB; exact tighten_mod A m f hB
    have e1 : (∃ ρ, Sat S ρ) ↔ ∃ ρ, Sat (normalize S) ρ :=
      ⟨fun ⟨ρ, h⟩ => ⟨ρ, (sat_normalize S ρ).2 h⟩, fun ⟨ρ, h⟩ => ⟨ρ, (sat_normalize S ρ).1 h⟩⟩
    rw [e1]
    simp only [decideN]
    generalize normalize S = S1 at hS1 hm1 ⊢
    split
    · rename_i hbad
      simp only [Bool.not_eq_true', List.all_eq_false, List.mem_filter] at hbad
      obtain ⟨B, ⟨hB, hgB⟩, hok⟩ := hbad
      simp only [Bool.false_eq_true, false_iff, not_exists]
      intro ρ h
      have := (ground_holds B hgB ρ).1 (h B hB)
      simp [hok] at this
    rename_i hok
    have hok : ∀ B, B ∈ S1 ∧ ground B = true → groundOK B = true := by
      have h' : (S1.filter ground).all groundOK = true := by
        cases h : (S1.filter ground).all groundOK <;> simp_all
      intro B hB
      exact List.all_eq_true.1 h' B (List.mem_filter.2 hB)
    have e2 : (∃ ρ, Sat S1 ρ) ↔ ∃ ρ, Sat (S1.filter (fun A => !ground A)) ρ := by
      constructor
      · rintro ⟨ρ, h⟩; exact ⟨ρ, fun B hB => h B (List.mem_filter.1 hB).1⟩
      · rintro ⟨ρ, h⟩
        refine ⟨ρ, fun B hB => ?_⟩
        by_cases hg : ground B = true
        · exact (ground_holds B hg ρ).2 (hok B ⟨hB, hg⟩)
        · exact h B (List.mem_filter.2 ⟨hB, by simpa using hg⟩)
    rw [e2]
    have hS2 : ∀ B ∈ S1.filter (fun A => !ground A), B.form.c.length ≤ n + 1 :=
      fun B hB => hS1 B (List.mem_filter.1 hB).1
    have hm2 : ∀ m f, Atom.dvd m f ∈ S1.filter (fun A => !ground A) → 0 < m :=
      fun m f hB => hm1 m f (List.mem_filter.1 hB).1
    generalize S1.filter (fun A => !ground A) = S2 at hS2 hm2 ⊢
    split
    · rename_i he
      simp only [List.isEmpty_iff] at he
      subst he
      simp only [true_iff]
      exact ⟨fun _ => 0, fun B hB => by cases hB⟩
    split
    · rename_i hh
      obtain ⟨B, hB, hb⟩ := List.any_eq_true.1 hh
      simp only [Bool.false_eq_true, false_iff, not_exists]
      exact fun ρ h => hopeless_not B hb ρ (h B hB)
    have hj : min (pick S2) n ≤ n := Nat.min_le_right _ _
    generalize min (pick S2) n = j at hj ⊢
    have hnd : noDvdAt S2 j = true → ∀ m f, Atom.dvd m f ∈ S2 → f.cj j = 0 := by
      intro h m f hf
      have := List.all_eq_true.1 h _ hf
      simpa using this
    split
    · rename_i hp
      simp only [Bool.and_eq_true] at hp
      rw [ih _ (fun B hB => by
        obtain ⟨A, hA, rfl⟩ := List.mem_map.1 hB
        exact len_subst A j 0 n (hS2 A (List.mem_filter.1 hA).1) hj)]
      exact (pos_rule S2 j (hnd hp.1) (fun A hA => by simpa using List.all_eq_true.1 hp.2 A hA)).symm
    split
    · rename_i _ hp
      simp only [Bool.and_eq_true] at hp
      rw [ih _ (fun B hB => by
        obtain ⟨A, hA, rfl⟩ := List.mem_map.1 hB
        exact len_subst A j 0 n (hS2 A hA) hj)]
      exact (neg_rule S2 j (hnd hp.1) (fun A hA => by simpa using List.all_eq_true.1 hp.2 A hA)).symm
    split
    · rename_i _ _ he
      obtain ⟨B, hB⟩ : ∃ B, ub S2 j = some B := by
        unfold enumOK at he; split at he
        · rename_i B hB; exact ⟨B, hB⟩
        · simp at he
      rw [hB, enum_rule S2 j B hB]
      simp only [Option.getD_some, List.any_eq_true, List.mem_range]
      constructor
      · rintro ⟨v, hv, hd⟩
        exact ⟨v, hv, (ih _ (fun C hC => by
          obtain ⟨A, hA, rfl⟩ := List.mem_map.1 hC
          exact len_subst A j v n (hS2 A hA) hj)).1 hd⟩
      · rintro ⟨v, hv, hd⟩
        exact ⟨v, hv, (ih _ (fun C hC => by
          obtain ⟨A, hA, rfl⟩ := List.mem_map.1 hC
          exact len_subst A j v n (hS2 A hA) hj)).2 hd⟩
    rw [lower_rule S2 j hm2]
    simp only [Bool.or_eq_true, List.any_eq_true, List.mem_range, Bool.and_eq_true]
    apply or_congr
    · constructor
      · rintro ⟨v, hv, hd⟩
        exact ⟨v, hv, (ih _ (fun B hB => by
          obtain ⟨A, hA, rfl⟩ := List.mem_map.1 hB
          exact len_subst A j v n (hS2 A hA) hj)).1 hd⟩
      · rintro ⟨v, hv, hd⟩
        exact ⟨v, hv, (ih _ (fun B hB => by
          obtain ⟨A, hA, rfl⟩ := List.mem_map.1 hB
          exact len_subst A j v n (hS2 A hA) hj)).2 hd⟩
    · constructor
      · rintro ⟨A, hA, hl, k, hk, hd⟩
        exact ⟨A, hA, hl, k, hk, (ih _ (len_pin S2 j n A k hS2 (hS2 A hA) hj)).1 hd⟩
      · rintro ⟨A, hA, hl, k, hk, hd⟩
        exact ⟨A, hA, hl, k, hk, (ih _ (len_pin S2 j n A k hS2 (hS2 A hA) hj)).2 hd⟩

theorem le_maxLen : ∀ (S : List Atom) (A : Atom), A ∈ S → A.form.c.length ≤ maxLen S
  | [], _, h => by cases h
  | B :: S, A, h => by
    simp only [maxLen, List.foldr] at *
    cases h with
    | head => omega
    | tail _ h => have := le_maxLen S A h; simp only [maxLen] at this; omega

/-- **The integer step is decided exactly**: for every way of choosing the variable to eliminate,
`decideTop` answers true exactly when the atoms have a common solution in the naturals. -/
theorem decide_correct (pick : List Atom → Nat) (S : List Atom) :
    decideTop pick S = true ↔ ∃ ρ : Nat → Nat, ∀ A ∈ S, A.holds ρ :=
  decideN_correct pick (maxLen S) S (le_maxLen S)

/-- The checker's procedure: `decideTop pickStd`. -/
theorem decide_std (S : List Atom) : decideTop pickStd S = true ↔ ∃ ρ : Nat → Nat, ∀ A ∈ S, A.holds ρ :=
  decide_correct pickStd S


/-! ## Region grouping: two variables with the same coefficient column merge into one -/

def setZ : List Int → Nat → List Int
  | [], _ => []
  | _ :: as, 0 => 0 :: as
  | a :: as, i + 1 => a :: setZ as i

def upd (ρ : Nat → Nat) (i v : Nat) : Nat → Nat := fun x => if x = i then v else ρ x

theorem dot_upd : ∀ (l : List Int) (i v : Nat) (ρ : Nat → Nat),
    dot l (upd ρ i v) = dot l ρ + l.getD i 0 * ((v : Int) - ρ i)
  | [], _, _, _ => by simp [dot]
  | a :: as, 0, v, ρ => by
    simp only [dot, List.getD_cons_zero]
    have : (fun x => upd ρ 0 v (x + 1)) = fun x => ρ (x + 1) := by funext x; simp [upd]
    rw [this]
    simp only [upd, ite_true]
    rw [Int.mul_sub]; omega
  | a :: as, i + 1, v, ρ => by
    simp only [dot, List.getD_cons_succ]
    have : (fun x => upd ρ (i + 1) v (x + 1)) = upd (fun x => ρ (x + 1)) i v := by
      funext x; simp [upd]
    rw [this, dot_upd as i v]
    have h0 : upd ρ (i + 1) v 0 = ρ 0 := by simp [upd]
    rw [h0]
    omega

theorem dot_setZ : ∀ (l : List Int) (i : Nat) (ρ : Nat → Nat), dot (setZ l i) ρ + l.getD i 0 * ρ i = dot l ρ
  | [], _, _ => by simp [setZ, dot]
  | a :: as, 0, ρ => by simp [setZ, dot]; omega
  | a :: as, i + 1, ρ => by
    simp only [setZ, dot, List.getD_cons_succ]
    have := dot_setZ as i (fun x => ρ (x + 1))
    omega

theorem getD_setZ_ne : ∀ (l : List Int) (i i' : Nat), i ≠ i' → (setZ l i').getD i 0 = l.getD i 0
  | [], _, _, _ => by simp [setZ]
  | a :: as, 0, 0, h => absurd rfl h
  | a :: as, i + 1, 0, _ => by simp [setZ]
  | a :: as, 0, i' + 1, _ => by simp [setZ]
  | a :: as, i + 1, i' + 1, h => by
    simp only [setZ, List.getD_cons_succ]; exact getD_setZ_ne as i i' (by omega)

theorem getD_setZ_eq : ∀ (l : List Int) (i : Nat), (setZ l i).getD i 0 = 0
  | [], _ => by simp [setZ]
  | a :: as, 0 => by simp [setZ]
  | a :: as, i + 1 => by simp only [setZ, List.getD_cons_succ]; exact getD_setZ_eq as i

def zeroCol (i' : Nat) (A : Atom) : Atom := A.map (fun f => ⟨setZ f.c i', f.k⟩)

theorem holds_of_eval (A : Atom) (g : Lin → Lin) (ρ σ) (h : (g A.form).eval σ = A.form.eval ρ) :
    (A.map g).holds σ ↔ A.holds ρ := by
  cases A <;> simp only [Atom.map, Atom.holds] <;> simp only [Atom.form] at h <;> rw [h]

/-- **Region grouping is exact**: when variables i and i' have the same coefficient in every atom,
dropping i' (its column set to 0; x_i stands for x_i + x_i') keeps the system's satisfiability. -/
theorem merge_columns (S : List Atom) (i i' : Nat) (hne : i ≠ i')
    (hcol : ∀ A ∈ S, A.form.c.getD i 0 = A.form.c.getD i' 0) :
    (∃ ρ, Sat S ρ) ↔ ∃ ρ, Sat (S.map (zeroCol i')) ρ := by
  constructor
  · rintro ⟨ρ, h⟩
    refine ⟨upd ρ i (ρ i + ρ i'), fun B hB => ?_⟩
    obtain ⟨A, hA, rfl⟩ := List.mem_map.1 hB
    refine (holds_of_eval A _ ρ _ ?_).2 (h A hA)
    simp only [Lin.eval]
    rw [dot_upd, getD_setZ_ne _ i i' hne, hcol A hA]
    have := dot_setZ A.form.c i' ρ
    rw [Int.natCast_add, Int.mul_sub, Int.mul_add] at *
    omega
  · rintro ⟨ρ, h⟩
    refine ⟨upd ρ i' 0, fun A hA => ?_⟩
    refine (holds_of_eval A (fun f => ⟨setZ f.c i', f.k⟩) (upd ρ i' 0) ρ ?_).1 (h _ (List.mem_map.2 ⟨A, hA, rfl⟩))
    simp only [Lin.eval]
    have h1 := dot_setZ A.form.c i' (upd ρ i' 0)
    have h2 := dot_upd (setZ A.form.c i') i' 0 ρ
    rw [getD_setZ_eq] at h2
    have h3 : upd ρ i' 0 i' = 0 := by simp [upd]
    rw [h3] at h1
    simp only [Int.zero_mul, Int.add_zero, Int.natCast_zero, Int.mul_zero] at h1 h2
    omega

/-! ## Row types: counts depend only on how many rows have each type -/

section Abstraction
variable {α : Type} [DecidableEq α]

omit [DecidableEq α] in
theorem sum_zero : ∀ (l : List α) (f : α → Nat), (∀ t ∈ l, f t = 0) → (l.map f).sum = 0
  | [], _, _ => rfl
  | t :: ts, f, h => by
    simp only [List.map, List.sum_cons, h t (List.mem_cons_self ..),
      sum_zero ts f (fun u hu => h u (List.mem_cons_of_mem _ hu))]

theorem sum_single (f : α → Nat) : ∀ (types : List α) (r : α), types.Nodup → r ∈ types →
    (types.map (fun t => if r = t then f t else 0)).sum = f r
  | [], _, _, h => by cases h
  | t :: ts, r, hn, hr => by
    rw [List.nodup_cons] at hn
    simp only [List.map, List.sum_cons]
    by_cases h : r = t
    · subst h
      have : (ts.map (fun u => if r = u then f u else 0)).sum = 0 := by
        apply sum_zero
        intro u hu
        have hru : r ≠ u := by intro e; subst e; exact hn.1 hu
        simp [hru]
      simp [this]
    · simp only [h, ite_false, Nat.zero_add]
      exact sum_single f ts r hn.2 (by cases hr with | head => exact absurd rfl h | tail _ h' => exact h')

omit [DecidableEq α] in
theorem sum_map_add (f g : α → Nat) : ∀ (l : List α), (l.map (fun t => f t + g t)).sum = (l.map f).sum + (l.map g).sum
  | [] => by simp
  | t :: ts => by simp only [List.map, List.sum_cons, sum_map_add f g ts]; omega

/-- A selection's count is the sum of the multiplicities of the types it selects. -/
theorem count_by_types (types : List α) (P : α → Bool) (hn : types.Nodup) :
    ∀ rows : List α, (∀ r ∈ rows, r ∈ types) →
      (rows.filter P).length = (types.map (fun t => if P t then rows.count t else 0)).sum
  | [], _ => by simp only [List.filter_nil, List.length_nil, List.count_nil, ite_self]; exact (sum_zero _ _ (fun _ _ => rfl)).symm
  | r :: rs, hr => by
    have ih := count_by_types types P hn rs (fun x hx => hr x (List.mem_cons_of_mem _ hx))
    have pt : ∀ t, (if P t then (r :: rs).count t else 0)
        = (if P t then rs.count t else 0) + (if r = t then (if P t then 1 else 0) else 0) := by
      intro t
      rw [List.count_cons]
      by_cases hp : P t = true <;> by_cases hrt : r = t <;> simp [hp, hrt]
    rw [List.map_congr_left (fun t _ => pt t), sum_map_add, ← ih,
      sum_single (fun t => if P t then 1 else 0) types r hn (hr r (List.mem_cons_self ..))]
    by_cases hp : P r = true <;> simp [hp]

/-- Every multiplicity vector is realised by some list of rows (for real tables this is reader fact
H1 with H2: rows are accepted one by one, and every type has fresh spellings). -/
theorem realise (types : List α) (hn : types.Nodup) (m : α → Nat) :
    ∃ rows : List α, (∀ r ∈ rows, r ∈ types) ∧ ∀ t ∈ types, rows.count t = m t := by
  refine ⟨types.flatMap (fun t => List.replicate (m t) t), ?_, ?_⟩
  · intro r hr
    obtain ⟨t, ht, hr⟩ := List.mem_flatMap.1 hr
    rw [(List.eq_of_mem_replicate hr)]; exact ht
  · intro t ht
    rw [List.count_flatMap]
    have : ∀ u ∈ types, (List.count t ∘ fun t => List.replicate (m t) t) u = if t = u then m u else 0 := by
      intro u _
      simp only [Function.comp, List.count_replicate]
      by_cases h : t = u
      · subst h; simp
      · have : (u == t) = false := by simp; exact fun e => h e.symm
        simp [this, h]
    rw [List.map_congr_left this, sum_single m types t hn ht]

/-- **Abstraction (L1)**: a question about the counts of finitely many selections, over all row lists,
is the same question over all multiplicity vectors. -/
theorem abstraction (types : List α) (hn : types.Nodup) (Ps : List (α → Bool)) (Q : List Nat → Prop) :
    (∃ rows : List α, (∀ r ∈ rows, r ∈ types) ∧ Q (Ps.map (fun P => (rows.filter P).length))) ↔
    (∃ m : α → Nat, Q (Ps.map (fun P => (types.map (fun t => if P t then m t else 0)).sum))) := by
  constructor
  · rintro ⟨rows, hr, hq⟩
    refine ⟨fun t => rows.count t, ?_⟩
    rw [List.map_congr_left (fun P _ => count_by_types types P hn rows hr)] at hq
    exact hq
  · rintro ⟨m, hq⟩
    obtain ⟨rows, hr, hc⟩ := realise types hn m
    refine ⟨rows, hr, ?_⟩
    have : ∀ P ∈ Ps, (rows.filter P).length = (types.map (fun t => if P t then m t else 0)).sum := by
      intro P _
      rw [count_by_types types P hn rows hr]
      congr 1
      apply List.map_congr_left
      intro t ht
      rw [hc t ht]
    rw [List.map_congr_left this]
    exact hq

/-- **Composition with the readers**: let `read` give, for an input it accepts, the row types of its
rows. If (soundness) every accepted input's rows have types in `types`, and (H1 with H2) every list
of rows over `types` is what some accepted input reads as, then a question about the counts of
selections over all accepted inputs is the same question over all multiplicity vectors. The two
hypotheses are the reader facts; Lean does not check the readers. -/
theorem real_abstraction {β : Type} (read : β → Option (List α)) (types : List α) (hn : types.Nodup)
    (hsound : ∀ b rows, read b = some rows → ∀ r ∈ rows, r ∈ types)
    (hall : ∀ rows : List α, (∀ r ∈ rows, r ∈ types) → ∃ b, read b = some rows)
    (Ps : List (α → Bool)) (Q : List Nat → Prop) :
    (∃ b rows, read b = some rows ∧ Q (Ps.map (fun P => (rows.filter P).length))) ↔
    (∃ m : α → Nat, Q (Ps.map (fun P => (types.map (fun t => if P t then m t else 0)).sum))) := by
  rw [← abstraction types hn Ps Q]
  constructor
  · rintro ⟨b, rows, hb, hq⟩; exact ⟨rows, hsound b rows hb, hq⟩
  · rintro ⟨rows, hr, hq⟩; obtain ⟨b, hb⟩ := hall rows hr; exact ⟨b, rows, hb, hq⟩

end Abstraction

/-! ## Rational elimination (SPEC-EXACT 4.1): Fourier–Motzkin over ℚ, keeping strictness

Named cell values are rationals; they are eliminated before the integer step. `elim_step` is one step
(exact: a value of the variable exists iff the eliminated atoms hold), `elim_correct` the whole list,
`elim_nat` the form the decision uses (the other variables are row counts, natural numbers), and
`atom_scale`/`atom_int` the passage to the integer step's atoms (denominators cleared; a strict atom
over integers loses 1). Phase 4 of exact-decision; carried from phase 1. -/
namespace Q

def dot : List Rat → (Nat → Rat) → Rat
  | [], _ => 0
  | a :: l, ρ => a * ρ 0 + dot l (fun i => ρ (i + 1))

def upd (ρ : Nat → Rat) (j : Nat) (v : Rat) : Nat → Rat := fun i => if i = j then v else ρ i

def coef (l : List Rat) (j : Nat) : Rat := l.getD j 0

theorem dot_upd : ∀ (l : List Rat) (ρ : Nat → Rat) (j : Nat) (v : Rat),
    dot l (upd ρ j v) = dot l ρ + coef l j * (v - ρ j)
  | [], ρ, j, v => by simp only [dot, coef, List.getD_nil]; grind
  | a :: l, ρ, 0, v => by
    simp only [dot, coef, List.getD_cons_zero, upd]
    grind
  | a :: l, ρ, j + 1, v => by
    have h : (fun i => upd ρ (j + 1) v (i + 1)) = upd (fun i => ρ (i + 1)) j v := by
      funext i; simp [upd]
    have h0 : upd ρ (j + 1) v 0 = ρ 0 := by simp [upd]
    simp only [dot, h, h0, coef, List.getD_cons_succ]
    rw [dot_upd l _ j v]
    simp only [coef]
    grind


def ladd : List Rat → List Rat → List Rat
  | [], m => m
  | l, [] => l
  | a :: l, b :: m => (a + b) :: ladd l m

theorem dot_ladd : ∀ (l m : List Rat) (ρ : Nat → Rat), dot (ladd l m) ρ = dot l ρ + dot m ρ
  | [], m, ρ => by simp only [ladd, dot]; grind
  | a :: l, [], ρ => by simp only [ladd, dot]; grind
  | a :: l, b :: m, ρ => by simp only [ladd, dot]; rw [dot_ladd l m]; grind

theorem dot_smul (c : Rat) : ∀ (l : List Rat) (ρ : Nat → Rat), dot (l.map (c * ·)) ρ = c * dot l ρ
  | [], ρ => by simp only [List.map, dot]; grind
  | a :: l, ρ => by simp only [List.map, dot]; rw [dot_smul c l]; grind

/-- A rational atom: `dot c ρ + k > 0` when strict, else `≥ 0`. -/
structure Atom where
  c : List Rat
  k : Rat
  strict : Bool

def Atom.eval (A : Atom) (ρ : Nat → Rat) : Rat := dot A.c ρ + A.k

def Atom.holds (A : Atom) (ρ : Nat → Rat) : Prop := if A.strict then 0 < A.eval ρ else 0 ≤ A.eval ρ

def Sat (S : List Atom) (ρ : Nat → Rat) : Prop := ∀ A ∈ S, A.holds ρ

theorem eval_upd (A : Atom) (ρ j v) : A.eval (upd ρ j v) = A.eval ρ + coef A.c j * (v - ρ j) := by
  simp only [Atom.eval, dot_upd]; grind

/-- b·p + a·q with a = coefficient of j in p (> 0) and b = minus that in q (> 0): j cancels. -/
def comb (j : Nat) (p q : Atom) : Atom :=
  ⟨ladd (p.c.map ((-coef q.c j) * ·)) (q.c.map ((coef p.c j) * ·)),
   (-coef q.c j) * p.k + coef p.c j * q.k, p.strict || q.strict⟩

theorem eval_comb (j : Nat) (p q : Atom) (ρ) :
    (comb j p q).eval ρ = (-coef q.c j) * p.eval ρ + coef p.c j * q.eval ρ := by
  simp only [comb, Atom.eval, dot_ladd, dot_smul]; grind


theorem pos_mul_iff {a X : Rat} (h : 0 < a) : 0 < a * X ↔ 0 < X := Rat.mul_pos_iff_of_pos_left h

theorem nonneg_mul_iff {a X : Rat} (h : 0 < a) : 0 ≤ a * X ↔ 0 ≤ X := by
  constructor
  · intro hx
    by_cases hX : 0 ≤ X
    · exact hX
    · have := Rat.mul_pos h (show 0 < -X by grind)
      grind
  · intro hx; exact Rat.mul_nonneg (by grind) hx

/-- `v` above the lower bound `b` (strictly when `s`). -/
def satLo (b : Rat) (s : Bool) (v : Rat) : Prop := if s then b < v else b ≤ v
/-- `v` below the upper bound `b` (strictly when `s`). -/
def satHi (b : Rat) (s : Bool) (v : Rat) : Prop := if s then v < b else v ≤ b

theorem satLo_mono {b s v w} (h : satLo b s v) (hw : v ≤ w) : satLo b s w := by
  unfold satLo at *; split <;> simp_all <;> grind
theorem satHi_mono {b s v w} (h : satHi b s v) (hw : w ≤ v) : satHi b s w := by
  unfold satHi at *; split <;> simp_all <;> grind

/-- An atom whose coefficient of j is a > 0 holds at `upd ρ j v` iff v is above its bound. -/
theorem holds_lower (A : Atom) (ρ j v) (ha : 0 < coef A.c j) :
    A.holds (upd ρ j v) ↔ satLo (ρ j - A.eval ρ / coef A.c j) A.strict v := by
  have key : A.eval (upd ρ j v) = coef A.c j * (v - (ρ j - A.eval ρ / coef A.c j)) := by
    rw [eval_upd]
    have : coef A.c j * (A.eval ρ / coef A.c j) = A.eval ρ := by grind
    grind
  unfold Atom.holds satLo
  rw [key]
  cases A.strict
  · simp only [Bool.false_eq_true, ite_false]; rw [nonneg_mul_iff ha]; grind
  · simp only [ite_true]; rw [pos_mul_iff ha]; grind

/-- An atom whose coefficient of j is −b < 0 holds at `upd ρ j v` iff v is below its bound. -/
theorem holds_upper (A : Atom) (ρ j v) (hb : coef A.c j < 0) :
    A.holds (upd ρ j v) ↔ satHi (ρ j - A.eval ρ / coef A.c j) A.strict v := by
  have hb' : 0 < -coef A.c j := by grind
  have key : A.eval (upd ρ j v) = (-coef A.c j) * ((ρ j - A.eval ρ / coef A.c j) - v) := by
    rw [eval_upd]
    have : coef A.c j * (A.eval ρ / coef A.c j) = A.eval ρ := by grind
    grind
  unfold Atom.holds satHi
  rw [key]
  cases A.strict
  · simp only [Bool.false_eq_true, ite_false]; rw [nonneg_mul_iff hb']; grind
  · simp only [ite_true]; rw [pos_mul_iff hb']; grind


/-- A lower bound and an upper bound leave room. -/
def compat (l : Rat × Bool) (u : Rat × Bool) : Prop := if l.2 || u.2 then l.1 < u.1 else l.1 ≤ u.1

theorem comb_holds (p q : Atom) (ρ j) (ha : 0 < coef p.c j) (hb : coef q.c j < 0) :
    (comb j p q).holds ρ ↔ compat (ρ j - p.eval ρ / coef p.c j, p.strict) (ρ j - q.eval ρ / coef q.c j, q.strict) := by
  have hab : 0 < coef p.c j * -coef q.c j := Rat.mul_pos ha (by grind)
  have key : (comb j p q).eval ρ = (coef p.c j * -coef q.c j) *
      ((ρ j - q.eval ρ / coef q.c j) - (ρ j - p.eval ρ / coef p.c j)) := by
    rw [eval_comb]
    have h1 : coef p.c j * (p.eval ρ / coef p.c j) = p.eval ρ := by grind
    have h2 : coef q.c j * (q.eval ρ / coef q.c j) = q.eval ρ := by grind
    grind
  unfold Atom.holds compat
  rw [key]
  have hst : (comb j p q).strict = (p.strict || q.strict) := rfl
  by_cases hs : (p.strict || q.strict) = true
  · have hs' : (comb j p q).strict = true := hst ▸ hs
    simp only [hs, hs', ↓reduceIte]; rw [pos_mul_iff hab]; grind
  · have hs' : ¬ (comb j p q).strict = true := hst ▸ hs
    simp only [hs, hs', ↓reduceIte]; rw [nonneg_mul_iff hab]; grind

/-- Some value is below every upper bound. -/
theorem below_all : ∀ (U : List (Rat × Bool)), ∃ v, ∀ u ∈ U, satHi u.1 u.2 v
  | [] => ⟨0, by simp⟩
  | u :: U => by
    obtain ⟨w, hw⟩ := below_all U
    refine ⟨if w ≤ u.1 - 1 then w else u.1 - 1, ?_⟩
    intro x hx
    rcases List.mem_cons.1 hx with rfl | hx
    · unfold satHi; split <;> split <;> grind
    · exact satHi_mono (hw x hx) (by split <;> grind)

/-- Some value is above one lower bound and below every upper bound it is compatible with. -/
theorem above_one (l : Rat × Bool) : ∀ (U : List (Rat × Bool)), (∀ u ∈ U, compat l u) →
    ∃ v, satLo l.1 l.2 v ∧ ∀ u ∈ U, satHi u.1 u.2 v
  | [], _ => ⟨l.1 + 1, by unfold satLo; split <;> grind, by simp⟩
  | u :: U, h => by
    obtain ⟨w, hl, hw⟩ := above_one l U (fun x hx => h x (List.mem_cons_of_mem _ hx))
    have hu := h u List.mem_cons_self
    unfold compat at hu
    by_cases hs : l.2 = true
    · -- strict lower bound: go half way to u
      have hlt : l.1 < u.1 := by simp [hs] at hu; exact hu
      refine ⟨if w ≤ (l.1 + u.1) / 2 then w else (l.1 + u.1) / 2, ?_, ?_⟩
      · unfold satLo at *; simp only [hs, ite_true] at *; split <;> grind
      · intro x hx
        rcases List.mem_cons.1 hx with rfl | hx
        · unfold satHi; split <;> split <;> grind
        · exact satHi_mono (hw x hx) (by split <;> grind)
    · -- non-strict lower bound: l.1 itself is below every upper bound
      refine ⟨l.1, by unfold satLo; simp [hs], ?_⟩
      intro x hx
      have hc := h x hx
      unfold compat satHi at *
      cases hx2 : x.2 <;> simp_all <;> grind

/-- **The step of Fourier–Motzkin**: pairwise compatible lower and upper bounds have a common value. -/
theorem between : ∀ (L U : List (Rat × Bool)), (∀ l ∈ L, ∀ u ∈ U, compat l u) →
    ∃ v, (∀ l ∈ L, satLo l.1 l.2 v) ∧ ∀ u ∈ U, satHi u.1 u.2 v
  | [], U, _ => by obtain ⟨v, hv⟩ := below_all U; exact ⟨v, by simp, hv⟩
  | l :: L, U, h => by
    obtain ⟨v, hL, hU⟩ := between L U (fun x hx => h x (List.mem_cons_of_mem _ hx))
    obtain ⟨w, hl, hw⟩ := above_one l U (h l List.mem_cons_self)
    refine ⟨if v ≤ w then w else v, ?_, ?_⟩
    · intro x hx
      rcases List.mem_cons.1 hx with rfl | hx
      · exact satLo_mono hl (by split <;> grind)
      · exact satLo_mono (hL x hx) (by split <;> grind)
    · intro x hx
      split
      · exact hw x hx
      · exact hU x hx


theorem compat_of {l u : Rat × Bool} {v : Rat} (hl : satLo l.1 l.2 v) (hu : satHi u.1 u.2 v) : compat l u := by
  unfold satLo satHi compat at *
  cases h1 : l.2 <;> cases h2 : u.2 <;> simp_all <;> grind

theorem holds_zero (A : Atom) (ρ j v) (h0 : coef A.c j = 0) : A.holds (upd ρ j v) ↔ A.holds ρ := by
  unfold Atom.holds; rw [eval_upd, h0, Rat.zero_mul, Rat.add_zero]

def lowers (j : Nat) (S : List Atom) : List Atom := S.filter (fun A => decide (0 < coef A.c j))
def uppers (j : Nat) (S : List Atom) : List Atom := S.filter (fun A => decide (coef A.c j < 0))
def zeros (j : Nat) (S : List Atom) : List Atom := S.filter (fun A => decide (coef A.c j = 0))

/-- One Fourier–Motzkin step on variable j: the atoms without j, and each lower atom combined with each
upper atom (SPEC-EXACT 4.1). -/
def elim (j : Nat) (S : List Atom) : List Atom :=
  zeros j S ++ (lowers j S).flatMap (fun p => (uppers j S).map (comb j p))

def bound (ρ : Nat → Rat) (j : Nat) (A : Atom) : Rat × Bool := (ρ j - A.eval ρ / coef A.c j, A.strict)

/-- **elim_step**: a value of variable j that satisfies S exists exactly when the eliminated system holds. -/
theorem elim_step (S : List Atom) (j : Nat) (ρ : Nat → Rat) :
    (∃ v, Sat S (upd ρ j v)) ↔ Sat (elim j S) ρ := by
  constructor
  · rintro ⟨v, h⟩ A hA
    rcases List.mem_append.1 hA with hz | hc
    · have ⟨hS, h0⟩ := List.mem_filter.1 hz
      exact (holds_zero A ρ j v (of_decide_eq_true h0)).1 (h A hS)
    · obtain ⟨p, hp, hc2⟩ := List.mem_flatMap.1 hc
      obtain ⟨q, hq, rfl⟩ := List.mem_map.1 hc2
      have ⟨hpS, hpa⟩ := List.mem_filter.1 hp
      have ⟨hqS, hqb⟩ := List.mem_filter.1 hq
      have ha := of_decide_eq_true hpa
      have hb := of_decide_eq_true hqb
      rw [comb_holds p q ρ j ha hb]
      exact compat_of ((holds_lower p ρ j v ha).1 (h p hpS)) ((holds_upper q ρ j v hb).1 (h q hqS))
  · intro h
    have hc : ∀ l ∈ (lowers j S).map (bound ρ j), ∀ u ∈ (uppers j S).map (bound ρ j), compat l u := by
      intro l hl u hu
      obtain ⟨p, hp, rfl⟩ := List.mem_map.1 hl
      obtain ⟨q, hq, rfl⟩ := List.mem_map.1 hu
      have hpa := of_decide_eq_true (List.mem_filter.1 hp).2
      have hqb := of_decide_eq_true (List.mem_filter.1 hq).2
      have := h (comb j p q) (List.mem_append_right _ (List.mem_flatMap.2 ⟨p, hp, List.mem_map.2 ⟨q, hq, rfl⟩⟩))
      exact (comb_holds p q ρ j hpa hqb).1 this
    obtain ⟨v, hL, hU⟩ := between _ _ hc
    refine ⟨v, fun A hA => ?_⟩
    by_cases hpos : 0 < coef A.c j
    · exact (holds_lower A ρ j v hpos).2 (hL _ (List.mem_map.2 ⟨A, List.mem_filter.2 ⟨hA, decide_eq_true hpos⟩, rfl⟩))
    by_cases hneg : coef A.c j < 0
    · exact (holds_upper A ρ j v hneg).2 (hU _ (List.mem_map.2 ⟨A, List.mem_filter.2 ⟨hA, decide_eq_true hneg⟩, rfl⟩))
    have hz : coef A.c j = 0 := by grind
    exact (holds_zero A ρ j v hz).2 (h A (List.mem_append_left _ (List.mem_filter.2 ⟨hA, decide_eq_true hz⟩)))


/-- Fourier–Motzkin over a list of variables, first to last. -/
def elimAll : List Nat → List Atom → List Atom
  | [], S => S
  | j :: js, S => elimAll js (elim j S)

/-- **elim_correct**: the eliminated system holds at ρ exactly when S holds at some ρ' that agrees
with ρ on every variable not eliminated. -/
theorem elim_correct : ∀ (js : List Nat) (S : List Atom) (ρ : Nat → Rat),
    Sat (elimAll js S) ρ ↔ ∃ ρ', (∀ i, i ∉ js → ρ' i = ρ i) ∧ Sat S ρ'
  | [], S, ρ => by
    constructor
    · intro h; exact ⟨ρ, fun _ _ => rfl, h⟩
    · rintro ⟨ρ', h1, h2⟩
      have : ρ' = ρ := funext fun i => h1 i (by simp)
      exact this ▸ h2
  | j :: js, S, ρ => by
    simp only [elimAll]
    rw [elim_correct js (elim j S) ρ]
    constructor
    · rintro ⟨ρ1, h1, h2⟩
      obtain ⟨v, hv⟩ := (elim_step S j ρ1).2 h2
      refine ⟨upd ρ1 j v, fun i hi => ?_, hv⟩
      have hij : i ≠ j := fun h => hi (h ▸ List.mem_cons_self)
      simp only [upd, hij, ↓reduceIte]
      exact h1 i (fun h => hi (List.mem_cons_of_mem _ h))
    · rintro ⟨ρ', h1, h2⟩
      refine ⟨upd ρ' j (ρ j), fun i hi => ?_, (elim_step S j _).1 ⟨ρ' j, ?_⟩⟩
      · by_cases hij : i = j
        · simp [upd, hij]
        · simp only [upd, hij, ↓reduceIte]
          exact h1 i (fun h => by rcases List.mem_cons.1 h with h | h <;> contradiction)
      · have : upd (upd ρ' j (ρ j)) j (ρ' j) = ρ' := by
          funext i; by_cases hij : i = j <;> simp [upd, hij]
        rw [this]; exact h2

/-- **elim_nat**: with the other variables natural numbers (the row counts), S has a solution with the
eliminated variables rational exactly when the eliminated system has a solution. -/
theorem elim_nat (js : List Nat) (S : List Atom) :
    (∃ ρ : Nat → Rat, (∀ i, i ∉ js → ∃ n : Nat, ρ i = n) ∧ Sat S ρ) ↔
    (∃ ρ : Nat → Rat, (∀ i, i ∉ js → ∃ n : Nat, ρ i = n) ∧ Sat (elimAll js S) ρ) := by
  constructor
  · rintro ⟨ρ, hn, h⟩
    exact ⟨ρ, hn, (elim_correct js S ρ).2 ⟨ρ, fun _ _ => rfl, h⟩⟩
  · rintro ⟨ρ, hn, h⟩
    obtain ⟨ρ', h1, h2⟩ := (elim_correct js S ρ).1 h
    exact ⟨ρ', fun i hi => by rw [h1 i hi]; exact hn i hi, h2⟩

/-! ### From rational atoms to the integer step's atoms -/

theorem dot_cast : ∀ (l : List Int) (ρ : Nat → Nat),
    dot (l.map (fun (a : Int) => (a : Rat))) (fun i => ((ρ i : Nat) : Rat)) = ((Exact.dot l ρ : Int) : Rat)
  | [], ρ => by simp [dot, Exact.dot]
  | a :: l, ρ => by
    simp only [List.map, dot, Exact.dot]
    rw [dot_cast l (fun i => ρ (i + 1))]
    push_cast; rfl

/-- A rational atom with integer coefficients, at natural values, is the integer step's atom
`f ≥ 0`, or `f − 1 ≥ 0` when strict (SPEC-EXACT 4.1: strict integer atoms lose 1). -/
theorem atom_int (f : Exact.Lin) (s : Bool) (ρ : Nat → Nat) :
    (⟨f.c.map (fun (a : Int) => (a : Rat)), f.k, s⟩ : Atom).holds (fun i => ((ρ i : Nat) : Rat)) ↔
    (Exact.Atom.ge ⟨f.c, f.k - (if s then 1 else 0)⟩).holds ρ := by
  have he : (⟨f.c.map (fun (a : Int) => (a : Rat)), f.k, s⟩ : Atom).eval (fun i => ((ρ i : Nat) : Rat)) = ((f.eval ρ : Int) : Rat) := by
    simp only [Atom.eval, Exact.Lin.eval]; rw [dot_cast]; push_cast; rfl
  simp only [Atom.holds, Exact.Atom.holds, Exact.Lin.eval, he]
  cases s
  · simp only [Bool.false_eq_true, ↓reduceIte]
    constructor
    · intro h; have : 0 ≤ f.eval ρ := by exact_mod_cast h
      simp only [Exact.Lin.eval] at this; omega
    · intro h; have : 0 ≤ f.eval ρ := by simp only [Exact.Lin.eval]; omega
      exact_mod_cast this
  · simp only [↓reduceIte]
    constructor
    · intro h; have : 0 < f.eval ρ := by exact_mod_cast h
      simp only [Exact.Lin.eval] at this; omega
    · intro h; have : 0 < f.eval ρ := by simp only [Exact.Lin.eval]; omega
      exact_mod_cast this

/-- Multiplying an atom by m > 0 does not change where it holds (the code clears denominators so). -/
theorem atom_scale (A : Atom) (m : Rat) (hm : 0 < m) (ρ : Nat → Rat) :
    A.holds ρ ↔ (⟨A.c.map (m * ·), m * A.k, A.strict⟩ : Atom).holds ρ := by
  have he : (⟨A.c.map (m * ·), m * A.k, A.strict⟩ : Atom).eval ρ = m * A.eval ρ := by
    simp only [Atom.eval, dot_smul]; grind
  unfold Atom.holds
  rw [he]
  cases A.strict
  · simp only [Bool.false_eq_true, ↓reduceIte]; rw [nonneg_mul_iff hm]
  · simp only [↓reduceIte]; rw [pos_mul_iff hm]

end Q

/-! ## L4: order statistics by counting (SPEC-EXACT 3.5; carried from phase 1, done in phase 4)

The k-th smallest value of a list is u exactly when fewer than k values are below u and at least k are
at or below u. The decision encodes max, min, order and median this way (max: k = n; min: k = 1; median of
2m + 1 values: k = m + 1), with the counts per region and piece. The kernel computes `sorted(qs)[k-1]`;
`List.mergeSort` is the sorted copy here. -/
namespace L4

/-- In a sorted list, every element before index i is at most s[i]. -/
theorem le_of_lt_idx {s : List Rat} (hs : s.Pairwise (· ≤ ·)) {i j : Nat} (hij : j < i) (hi : i < s.length) :
    s[j]'(by omega) ≤ s[i] := by
  exact List.pairwise_iff_getElem.1 hs j i (by omega) hi hij

/-- countP over the first i+1 elements and the rest. -/
theorem countP_split (p : Rat → Bool) (s : List Rat) (i : Nat) :
    s.countP p = (s.take (i + 1)).countP p + (s.drop (i + 1)).countP p := by
  rw [← List.countP_append, List.take_append_drop]

theorem all_take {s : List Rat} {P : Rat → Prop} (i : Nat) (hi : i < s.length)
    (h : ∀ j (_hj : j ≤ i), P (s[j]'(by omega))) : ∀ x ∈ s.take (i + 1), P x := by
  intro x hx
  obtain ⟨j, hj, rfl⟩ := List.getElem_of_mem hx
  simp only [List.length_take] at hj
  rw [List.getElem_take]
  exact h j (by omega)

theorem all_drop {s : List Rat} {P : Rat → Prop} (i : Nat)
    (h : ∀ j (hj : i ≤ j) (hj' : j < s.length), P (s[j])) : ∀ x ∈ s.drop i, P x := by
  intro x hx
  obtain ⟨j, hj, rfl⟩ := List.getElem_of_mem hx
  simp only [List.length_drop] at hj
  rw [List.getElem_drop]
  exact h (i + j) (by omega) (by omega)

/-- **L4, sorted form**: s[i] = u exactly when fewer than i + 1 elements are below u and more than i
are at or below it. -/
theorem kth_sorted (s : List Rat) (hs : s.Pairwise (· ≤ ·)) (i : Nat) (hi : i < s.length) (u : Rat) :
    s[i] = u ↔ s.countP (fun x => decide (x < u)) ≤ i ∧ i < s.countP (fun x => decide (x ≤ u)) := by
  constructor
  · intro h
    constructor
    · -- no element from i on is below u
      have h0 : (s.drop i).countP (fun x => decide (x < u)) = 0 := by
        rw [List.countP_eq_zero]
        intro x hx
        have := all_drop (P := fun x => u ≤ x) i (fun j hj hj' => by
          rcases Nat.lt_or_eq_of_le hj with hlt | heq
          · have := le_of_lt_idx hs hlt hj'; grind
          · subst heq; grind) x hx
        simp only [decide_eq_true_eq]; grind
      have := List.countP_le_length (p := fun x => decide (x < u)) (l := s.take i)
      have hs' := List.take_append_drop i s
      rw [← hs', List.countP_append, h0]
      simp only [List.length_take] at this
      omega
    · have h1 : (s.take (i + 1)).countP (fun x => decide (x ≤ u)) = i + 1 := by
        rw [List.countP_eq_length.2]
        · simp only [List.length_take]; omega
        · intro x hx
          have := all_take (P := fun x => x ≤ u) i hi (fun j hj => by
            rcases Nat.lt_or_eq_of_le hj with hlt | heq
            · have := le_of_lt_idx hs hlt hi; grind
            · subst heq; grind) x hx
          simp only [decide_eq_true_eq]; exact this
      rw [countP_split _ s i, h1]; omega
  · rintro ⟨h1, h2⟩
    by_cases hlt : s[i] < u
    · -- s[0..i] all below u: at least i + 1 below
      have : (s.take (i + 1)).countP (fun x => decide (x < u)) = i + 1 := by
        rw [List.countP_eq_length.2]
        · simp only [List.length_take]; omega
        · intro x hx
          have := all_take (P := fun x => x < u) i hi (fun j hj => by
            rcases Nat.lt_or_eq_of_le hj with hl | heq
            · have := le_of_lt_idx hs hl hi; grind
            · subst heq; grind) x hx
          simp only [decide_eq_true_eq]; exact this
      rw [countP_split _ s i, this] at h1; omega
    · by_cases heq : s[i] = u
      · exact heq
      have hgt : u < s[i] := by grind
      · -- s[i..] all above u: at most i at or below u
        have h0 : (s.drop i).countP (fun x => decide (x ≤ u)) = 0 := by
          rw [List.countP_eq_zero]
          intro x hx
          have := all_drop (P := fun x => u < x) i (fun j hj hj' => by
            rcases Nat.lt_or_eq_of_le hj with hl | heq
            · have := le_of_lt_idx hs hl hj'; grind
            · subst heq; grind) x hx
          simp only [decide_eq_true_eq]; grind
        have := List.countP_le_length (p := fun x => decide (x ≤ u)) (l := s.take i)
        have hs' := List.take_append_drop i s
        rw [← hs', List.countP_append, h0] at h2
        simp only [List.length_take] at this
        omega

/-- **L4**: the (i+1)-th smallest of any list of rationals (its sorted copy at index i) is u exactly when
at most i of its values are below u and more than i are at or below u. max is index n − 1, min index 0,
the median of 2m + 1 values index m; SPEC-EXACT 3.5's atoms for order statistics are these counts. -/
theorem kth (l : List Rat) (i : Nat) (hi : i < l.length) (u : Rat) :
    (l.mergeSort (fun a b => decide (a ≤ b)))[i]'(by rw [List.length_mergeSort]; exact hi) = u ↔
      l.countP (fun x => decide (x < u)) ≤ i ∧ i < l.countP (fun x => decide (x ≤ u)) := by
  have hp := List.mergeSort_perm l (fun a b => decide (a ≤ b))
  have hs : (l.mergeSort (fun a b => decide (a ≤ b))).Pairwise (· ≤ ·) := by
    have := List.pairwise_mergeSort (le := fun a b => decide (a ≤ b))
      (fun a b c hab hbc => by simp only [decide_eq_true_eq] at *; grind)
      (fun a b => by simp only [Bool.or_eq_true, decide_eq_true_eq]; exact Rat.le_total) l
    exact this.imp (fun h => by simpa using h)
  rw [kth_sorted _ hs, hp.countP_eq, hp.countP_eq]

end L4

/-! ## Variances: the largest value (variance phase, SPEC-EXACT 3.7)

For values in [L, U] the sample variance (n ≥ 2) is at most (U − L)²/2 and the population variance (n ≥ 1) at
most (U − L)²/4 (Bhatia–Davis), and the two values L, U reach both. `var` is the kernel's Σ(x − m)²/(n − ddof)
written as (n·Σx² − S²)/(n·(n − ddof)) (the same number for n ≥ 1, by algebra not checked here). -/
namespace Var

def sum : List Rat → Rat
  | [] => 0
  | x :: l => x + sum l

def sumsq : List Rat → Rat
  | [] => 0
  | x :: l => x * x + sumsq l

/-- Σ (U − x)(x − L) over the list. -/
def bd (L U : Rat) : List Rat → Rat
  | [] => 0
  | x :: l => (U - x) * (x - L) + bd L U l

theorem bd_nonneg (L U : Rat) : ∀ (l : List Rat), (∀ x ∈ l, L ≤ x ∧ x ≤ U) → 0 ≤ bd L U l
  | [], _ => by simp [bd]
  | x :: l, h => by
    have hx := h x List.mem_cons_self
    have ih := bd_nonneg L U l (fun y hy => h y (List.mem_cons_of_mem _ hy))
    have : 0 ≤ (U - x) * (x - L) := Rat.mul_nonneg (by grind) (by grind)
    simp only [bd]; grind

theorem bd_eq (L U : Rat) : ∀ (l : List Rat), bd L U l = (U + L) * sum l - sumsq l - (l.length : Rat) * U * L
  | [] => by simp only [bd, sum, sumsq, List.length_nil]; grind
  | x :: l => by
    simp only [bd, sum, sumsq, List.length_cons]
    rw [bd_eq L U l]
    push_cast
    grind

/-- **Bhatia–Davis, summed**: for N values in [L, U] with sum S, N·Σx² − S² ≤ N²·(U − L)²/4, i.e. N times the sum of
squared deviations from the mean is at most (N(U − L)/2)². -/
theorem spread_le (L U : Rat) (l : List Rat) (h : ∀ x ∈ l, L ≤ x ∧ x ≤ U) :
    (l.length : Rat) * sumsq l - sum l * sum l ≤ ((l.length : Rat) * (U - L)) * ((l.length : Rat) * (U - L)) / 4 := by
  have h0 := bd_nonneg L U l h
  rw [bd_eq] at h0
  have sq : 0 ≤ ((l.length : Rat) * (U + L) - 2 * sum l) * ((l.length : Rat) * (U + L) - 2 * sum l) := by
    by_cases h1 : 0 ≤ (l.length : Rat) * (U + L) - 2 * sum l
    · exact Rat.mul_nonneg h1 h1
    · have := Rat.mul_nonneg (show 0 ≤ -((l.length : Rat) * (U + L) - 2 * sum l) by grind) (show 0 ≤ -((l.length : Rat) * (U + L) - 2 * sum l) by grind)
      grind
  have hn : (0 : Rat) ≤ (l.length : Rat) := by exact_mod_cast Nat.zero_le _
  have := Rat.mul_nonneg hn h0
  grind

/-- The kernel's variances: Σ (x − m)² / (n − ddof) with m the mean, as (n·Σx² − S²) / (n·(n − ddof)). -/
def var (ddof : Nat) (l : List Rat) : Rat :=
  ((l.length : Rat) * sumsq l - sum l * sum l) / ((l.length : Rat) * ((l.length : Rat) - ddof))

theorem div_le_of_le_mul {a b c : Rat} (hb : 0 < b) (h : a ≤ c * b) : a / b ≤ c := by
  by_cases hc : c < a / b
  · have := (Rat.lt_div_iff hb).1 hc; grind
  · grind

/-- **Sample variance bound**: values in [L, U], n ≥ 2: at most (U − L)²/2. -/
theorem sample_le (L U : Rat) (l : List Rat) (h : ∀ x ∈ l, L ≤ x ∧ x ≤ U) (hn : 2 ≤ l.length) :
    var 1 l ≤ (U - L) * (U - L) / 2 := by
  have sp := spread_le L U l h
  have hN : (2 : Rat) ≤ (l.length : Rat) := by exact_mod_cast hn
  have hb : 0 < (l.length : Rat) * ((l.length : Rat) - 1) := Rat.mul_pos (by grind) (by grind)
  unfold var
  have h1 : ((1 : Nat) : Rat) = 1 := rfl
  rw [h1]
  apply div_le_of_le_mul hb
  have w2 : 0 ≤ (U - L) * (U - L) := by
    by_cases hw : 0 ≤ U - L
    · exact Rat.mul_nonneg hw hw
    · have := Rat.mul_nonneg (show 0 ≤ -(U - L) by grind) (show 0 ≤ -(U - L) by grind); grind
  -- n²w²/4 ≤ (w²/2)·n(n − 1) because n² ≤ 2n(n − 1) for n ≥ 2
  have key : (l.length : Rat) * (l.length : Rat) ≤ 2 * ((l.length : Rat) * ((l.length : Rat) - 1)) := by
    have := Rat.mul_nonneg (show (0 : Rat) ≤ l.length by grind) (show (0 : Rat) ≤ (l.length : Rat) - 2 by grind)
    grind
  have := Rat.mul_le_mul_of_nonneg_left key w2
  grind

/-- **Population variance bound**: values in [L, U], n ≥ 1: at most (U − L)²/4. -/
theorem population_le (L U : Rat) (l : List Rat) (h : ∀ x ∈ l, L ≤ x ∧ x ≤ U) (hn : 1 ≤ l.length) :
    var 0 l ≤ (U - L) * (U - L) / 4 := by
  have sp := spread_le L U l h
  have hN : (1 : Rat) ≤ (l.length : Rat) := by exact_mod_cast hn
  have h0 : ((0 : Nat) : Rat) = 0 := rfl
  have hb : 0 < (l.length : Rat) * ((l.length : Rat) - ((0 : Nat) : Rat)) := by
    rw [h0]; exact Rat.mul_pos (by grind) (by grind)
  unfold var
  apply div_le_of_le_mul hb
  rw [h0]
  grind

/-- The two-row table [L, U] reaches both bounds. -/
theorem reach (L U : Rat) : var 1 [L, U] = (U - L) * (U - L) / 2 ∧ var 0 [L, U] = (U - L) * (U - L) / 4 := by
  simp only [var, sum, sumsq, List.length_cons, List.length_nil]
  push_cast
  constructor <;> grind

end Var

end Exact

#print axioms Exact.decide_correct
#print axioms Exact.decide_std
#print axioms Exact.lower_rule
#print axioms Exact.pos_rule
#print axioms Exact.enum_rule
#print axioms Exact.neg_rule
#print axioms Exact.holds_tighten
#print axioms Exact.merge_columns
#print axioms Exact.abstraction
#print axioms Exact.real_abstraction
#print axioms Exact.Q.elim_step
#print axioms Exact.Q.elim_correct
#print axioms Exact.Q.elim_nat
#print axioms Exact.Q.atom_int
#print axioms Exact.Q.atom_scale
#print axioms Exact.L4.kth_sorted
#print axioms Exact.L4.kth
#print axioms Exact.Var.spread_le
#print axioms Exact.Var.sample_le
#print axioms Exact.Var.population_le
#print axioms Exact.Var.reach
