import FireProof.Assumptions

/-! # Connectivity/coherence equation -/

namespace FireProof.Connectivity

noncomputable section

def vectorField (alpha mu F C : ℝ) : ℝ := alpha * C * (1 - C) * F - mu * C

theorem vectorField_zero (alpha mu F : ℝ) : vectorField alpha mu F 0 = 0 := by
  simp [vectorField]

theorem vectorField_one (alpha mu F : ℝ) : vectorField alpha mu F 1 = -mu := by
  simp [vectorField]

def positiveEquilibrium (alpha mu F : ℝ) : ℝ := 1 - mu / (alpha * F)

theorem positiveEquilibrium_is_equilibrium
    {alpha mu F : ℝ} (h : alpha * F ≠ 0) :
    vectorField alpha mu F (positiveEquilibrium alpha mu F) = 0 := by
  unfold vectorField positiveEquilibrium
  field_simp
  ring

theorem positiveEquilibrium_pos_iff
    {alpha mu F : ℝ} (ha : 0 < alpha) (hF : 0 < F) :
    0 < positiveEquilibrium alpha mu F ↔ mu < alpha * F := by
  unfold positiveEquilibrium
  rw [sub_pos, div_lt_one (mul_pos ha hF)]

theorem threshold_form
    {alpha mu F : ℝ} (ha : 0 < alpha) :
    mu < alpha * F ↔ mu / alpha < F := by
  constructor <;> intro h
  · exact (div_lt_iff₀ ha).2 (by simpa [mul_comm] using h)
  · have h' := (div_lt_iff₀ ha).1 h
    simpa [mul_comm] using h'

theorem no_positive_equilibrium_at_or_below_threshold
    {alpha mu F : ℝ} (ha : 0 < alpha) (hmu : 0 ≤ mu) (hF : 0 < F)
    (hthreshold : alpha * F ≤ mu) :
    positiveEquilibrium alpha mu F ≤ 0 := by
  unfold positiveEquilibrium
  rw [sub_nonpos]
  exact (one_le_div (mul_pos ha hF)).2 hthreshold

/-- Boundary signs are algebraic checks; an ODE invariance theorem additionally
needs a well-posed trajectory (normally continuity plus uniqueness). -/
theorem boundary_signs
    {alpha mu F : ℝ} (hmu : 0 ≤ mu) :
    vectorField alpha mu F 0 = 0 ∧ vectorField alpha mu F 1 ≤ 0 := by
  constructor
  · exact vectorField_zero _ _ _
  · rw [vectorField_one]
    linarith

theorem unit_interval_invariant_with_barrier_assumptions
    {C : ℝ → ℝ} {t0 : ℝ}
    (hC0 : C t0 ∈ Set.Icc (0 : ℝ) 1)
    (hUpperHit : FireProof.HasIntermediateBarrierProperty C 1 t0)
    (hUpperUnique : FireProof.HasUpperBarrierUniqueness C 1)
    (hLowerHit : FireProof.HasLowerIntermediateBarrierProperty C 0 t0)
    (hLowerUnique : FireProof.HasLowerBarrierUniqueness C 0) :
    ∀ ⦃t : ℝ⦄, t0 ≤ t → C t ∈ Set.Icc (0 : ℝ) 1 := by
  intro t ht
  constructor
  · by_contra hnot
    have hlt : C t < 0 := lt_of_not_ge hnot
    have htne : t ≠ t0 := by
      intro heq
      subst t
      linarith [hC0.1]
    obtain ⟨s, hs, hCs⟩ := hLowerHit
      (le_of_lt (lt_of_le_of_ne ht (Ne.symm htne))) hlt
    exact (not_lt_of_ge (hLowerUnique hs.2 hCs)) hlt
  · by_contra hnot
    have hgt : 1 < C t := lt_of_not_ge hnot
    have htne : t ≠ t0 := by
      intro heq
      subst t
      linarith [hC0.2]
    obtain ⟨s, hs, hCs⟩ := hUpperHit
      (le_of_lt (lt_of_le_of_ne ht (Ne.symm htne))) hgt
    exact (not_lt_of_ge (hUpperUnique hs.2 hCs)) hgt

end
end FireProof.Connectivity
