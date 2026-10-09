import FireProof.Scaling

/-!
# Scaling normalization and origin anchoring

These lemmas distinguish a fixed power-law coefficient from a coefficient
chosen to pass through one observed origin. They are algebraic identifiability
results, not statistical claims about wildfire data.
-/

namespace FireProof.Normalization

noncomputable section

/-- The coefficient chosen to make exponent `sigma` pass through `(A0,P0)`. -/
def anchoredCoefficient (A0 P0 sigma : ℝ) : ℝ := P0 / A0 ^ sigma

/-- A power-law prediction conditioned to pass through `(A0,P0)`. -/
def anchoredPrediction (A0 P0 sigma A : ℝ) : ℝ :=
  P0 * (A / A0) ^ sigma

theorem anchoredCoefficient_prediction
    {A0 P0 sigma A : ℝ} (hA0 : 0 < A0) (hA : 0 < A) :
    anchoredCoefficient A0 P0 sigma * A ^ sigma =
      anchoredPrediction A0 P0 sigma A := by
  unfold anchoredCoefficient anchoredPrediction
  rw [Real.div_rpow (le_of_lt hA) (le_of_lt hA0)]
  field_simp [ne_of_gt (Real.rpow_pos_of_pos hA0 sigma)]

/-- Every exponent fits one positive anchor after its coefficient is adjusted. -/
theorem anchoredPrediction_at_origin
    {A0 P0 sigma : ℝ} (hA0 : 0 < A0) :
    anchoredPrediction A0 P0 sigma A0 = P0 := by
  unfold anchoredPrediction
  simp [div_self (ne_of_gt hA0)]

/-- Ratio of two candidate laws anchored at the same positive observation. -/
theorem anchored_candidate_ratio
    {A0 P0 A sigma1 sigma2 : ℝ}
    (hA0 : 0 < A0) (hP0 : 0 < P0) (hA : 0 < A) :
    anchoredPrediction A0 P0 sigma2 A /
        anchoredPrediction A0 P0 sigma1 A =
      (A / A0) ^ (sigma2 - sigma1) := by
  have hr : 0 < A / A0 := div_pos hA hA0
  unfold anchoredPrediction
  rw [Real.rpow_sub hr]
  field_simp [ne_of_gt hP0, ne_of_gt (Real.rpow_pos_of_pos hr sigma1)]
  ring

/-- For one-half versus two-thirds, anchored separation is the sixth root of
the area expansion ratio. -/
theorem half_two_thirds_anchored_ratio
    {A0 P0 A : ℝ} (hA0 : 0 < A0) (hP0 : 0 < P0) (hA : 0 < A) :
    anchoredPrediction A0 P0 ((2 : ℝ) / 3) A /
        anchoredPrediction A0 P0 ((1 : ℝ) / 2) A =
      (A / A0) ^ ((1 : ℝ) / 6) := by
  convert anchored_candidate_ratio hA0 hP0 hA using 1 <;> norm_num

/-- With no area expansion, all same-origin candidate ratios equal one. -/
theorem anchored_ratio_at_no_expansion
    {sigma1 sigma2 : ℝ} :
    (1 : ℝ) ^ (sigma2 - sigma1) = 1 := by
  simp

/-- A coefficient that is constant within one fire cancels from log
differences, leaving the shared exponent. -/
theorem fire_specific_constant_log_slope
    {A1 A2 P1 P2 k sigma : ℝ}
    (h1 : Real.log P1 = Real.log k + sigma * Real.log A1)
    (h2 : Real.log P2 = Real.log k + sigma * Real.log A2) :
    Real.log P2 - Real.log P1 =
      sigma * (Real.log A2 - Real.log A1) := by
  rw [h1, h2]
  ring

/-- If normalization may be chosen freely for each observation, every exponent
reconstructs the observation exactly. -/
theorem variable_normalization_reconstructs
    {A P sigma : ℝ} (hA : 0 < A) :
    (P / A ^ sigma) * A ^ sigma = P := by
  field_simp [ne_of_gt (Real.rpow_pos_of_pos hA sigma)]

/-- Explicit two-thirds coefficient from the rough-boundary construction. -/
theorem geometric_two_thirds_elimination
    {A P L cA cP : ℝ}
    (hLpos : 0 < L) (hcApos : 0 < cA) (hcPpos : 0 < cP)
    (hA : A = cA * L ^ (2 : ℝ))
    (hP : P = cP * L ^ ((4 : ℝ) / 3)) :
    P = (cP / cA ^ ((2 : ℝ) / 3)) * A ^ ((2 : ℝ) / 3) := by
  exact FireProof.Scaling.four_thirds_direct_power_law
    hLpos hcApos hcPpos hA hP

/-- Explicit one-half coefficient from planar geometric similarity. -/
theorem euclidean_one_half_elimination
    {A P L cA cP : ℝ}
    (hLpos : 0 < L) (hcApos : 0 < cA) (hcPpos : 0 < cP)
    (hA : A = cA * L ^ (2 : ℝ))
    (hP : P = cP * L ^ (1 : ℝ)) :
    P = (cP / cA ^ ((1 : ℝ) / 2)) * A ^ ((1 : ℝ) / 2) := by
  convert FireProof.Scaling.eliminate_direct_power_laws
    hLpos hcApos hcPpos hA hP (by norm_num : (2 : ℝ) ≠ 0) using 1 <;>
    norm_num

end
end FireProof.Normalization
