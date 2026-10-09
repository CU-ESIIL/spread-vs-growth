import FireProof.Assumptions

/-! # Potential and realized growth under an unresolved realization factor

`B` is deliberately abstract. It is not a suppression, barrier, fuel, or
management variable. The file formalizes only the algebra and the resulting
identifiability boundary.
-/

namespace FireProof.Realization

def potentialGrowth (K A23 : ℝ) : ℝ := K * A23

def realizedGrowth (B K A23 : ℝ) : ℝ := B * potentialGrowth K A23

def realizedCoupling (B K : ℝ) : ℝ := B * K

theorem realized_growth_nonnegative_and_bounded
    {B K A23 : ℝ} (hB0 : 0 ≤ B) (hB1 : B ≤ 1)
    (hK : 0 ≤ K) (hA : 0 ≤ A23) :
    0 ≤ realizedGrowth B K A23 ∧
      realizedGrowth B K A23 ≤ potentialGrowth K A23 := by
  constructor
  · exact mul_nonneg hB0 (mul_nonneg hK hA)
  · dsimp [realizedGrowth, potentialGrowth]
    nlinarith [mul_nonneg hK hA]

theorem unconstrained_recovers_potential (K A23 : ℝ) :
    realizedGrowth 1 K A23 = potentialGrowth K A23 := by
  simp [realizedGrowth]

theorem observed_rate_identifies_product
    {B K A23 M : ℝ} (hA : A23 ≠ 0)
    (hM : M = realizedGrowth B K A23) :
    M / A23 = realizedCoupling B K := by
  rw [hM]
  field_simp [realizedGrowth, potentialGrowth, realizedCoupling]
  ring

theorem equal_realized_coupling_equal_growth
    {B₁ K₁ B₂ K₂ A23 : ℝ}
    (hproduct : realizedCoupling B₁ K₁ = realizedCoupling B₂ K₂) :
    realizedGrowth B₁ K₁ A23 = realizedGrowth B₂ K₂ A23 := by
  simpa [realizedGrowth, potentialGrowth, realizedCoupling, mul_assoc] using
    congrArg (fun x : ℝ => x * A23) hproduct

theorem distinct_factor_counterexample :
    realizedCoupling (1 / 2 : ℝ) 2 = realizedCoupling 1 1 ∧
      (1 / 2 : ℝ) ≠ 1 ∧ (2 : ℝ) ≠ 1 := by
  norm_num [realizedCoupling]

theorem bounded_realization_narrows_upper_growth
    {bmin bmax K A23 : ℝ}
    (hbmin : 0 ≤ bmin) (hbmax : bmax ≤ 1)
    (hpot : 0 ≤ potentialGrowth K A23) :
    Set.Icc (bmin * potentialGrowth K A23) (bmax * potentialGrowth K A23) ⊆
      Set.Icc 0 (potentialGrowth K A23) := by
  intro value hvalue
  constructor
  · exact le_trans (mul_nonneg hbmin hpot) hvalue.1
  · exact le_trans hvalue.2 (by nlinarith)

theorem restoration_survives_bounded_shock
    {e lambda shock : ℝ} (hlambda : 0 < lambda) (he : e ≠ 0)
    (hshock : e * shock < lambda * e ^ 2) :
    e * (-lambda * e + shock) < 0 := by
  have he2 : 0 < e ^ 2 := sq_pos_of_ne_zero he
  nlinarith

end FireProof.Realization
