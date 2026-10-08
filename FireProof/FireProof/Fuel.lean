import FireProof.Assumptions

/-! # Finite-fuel bookkeeping -/

namespace FireProof.Fuel

noncomputable section

def remaining (Amax A0 A : ℝ) : ℝ := (Amax - A) / (Amax - A0)

theorem remaining_at_initial {Amax A0 : ℝ} (h : Amax ≠ A0) :
    remaining Amax A0 A0 = 1 := by
  unfold remaining
  exact div_self (sub_ne_zero.mpr h)

theorem remaining_at_max {Amax A0 : ℝ} (h : Amax ≠ A0) :
    remaining Amax A0 Amax = 0 := by
  simp [remaining]

theorem remaining_mem_unit
    {Amax A0 A : ℝ} (hmax : A0 < Amax) (hlow : A0 ≤ A) (high : A ≤ Amax) :
    remaining Amax A0 A ∈ Set.Icc (0 : ℝ) 1 := by
  constructor
  · exact div_nonneg (sub_nonneg.mpr high) (sub_nonneg.mpr (le_of_lt hmax))
  · apply (div_le_one (sub_pos.mpr hmax)).2
    linarith

theorem remaining_derivative
    {A : ℝ → ℝ} {Amax A0 t A' : ℝ}
    (hden : Amax ≠ A0) (hA : HasDerivAt A A' t) :
    HasDerivAt (fun u => remaining Amax A0 (A u))
      (-A' / (Amax - A0)) t := by
  have hnum : HasDerivAt (fun u => Amax - A u) (-A') t :=
    by simpa using (hasDerivAt_const t Amax).sub hA
  simpa [remaining] using hnum.div_const (Amax - A0)

theorem cannot_cross_with_explicit_barrier_assumptions
    {A : ℝ → ℝ} {Amax t0 : ℝ}
    (hA0 : A t0 ≤ Amax)
    (hIntermediate : FireProof.HasIntermediateBarrierProperty A Amax t0)
    (hUniqueBarrier : FireProof.HasUpperBarrierUniqueness A Amax) :
    ∀ ⦃t : ℝ⦄, t0 ≤ t → A t ≤ Amax := by
  intro t ht
  by_contra hnot
  have hgt : Amax < A t := lt_of_not_ge hnot
  have htne : t ≠ t0 := by
    intro heq
    subst t
    linarith
  have hstrict : t0 < t := lt_of_le_of_ne ht (Ne.symm htne)
  obtain ⟨s, hs, hAs⟩ := hIntermediate (le_of_lt hstrict) hgt
  exact (not_lt_of_ge (hUniqueBarrier hs.2 hAs)) hgt

/-- A zero derivative at one instant does not imply a one-sided barrier. -/
example :
    let x : ℝ → ℝ := fun t => t ^ 3
    x 0 = 0 ∧ HasDerivAt x 0 0 ∧ x 1 > 0 := by
  dsimp
  constructor
  · norm_num
  constructor
  · convert (hasDerivAt_pow 3 (0 : ℝ)) using 1 <;> norm_num
  · norm_num

end
end FireProof.Fuel
