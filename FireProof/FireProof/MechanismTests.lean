import FireProof.Matching

/-!
# Structural identifiability and competing-mechanism tests
-/

namespace FireProof.MechanismTests

noncomputable section

theorem area_only_product_rescaling
    {beta0 C F eta lambda : ℝ} (hlambda : lambda ≠ 0) :
    (lambda * beta0) * (C / lambda) * F * eta = beta0 * C * F * eta := by
  field_simp [hlambda]
  ring

theorem area_perimeter_joint_rescaling
    {beta0 k C F eta A23 lambda : ℝ} (hlambda : lambda ≠ 0) :
    (lambda * k) * (C / lambda) * A23 = k * C * A23 ∧
    (lambda * beta0) * (C / lambda) * F * eta * A23 =
      beta0 * C * F * eta * A23 := by
  constructor <;> field_simp [hlambda] <;> ring

theorem matching_reciprocal_symmetry {r : ℝ} (hr : 0 < r) :
    FireProof.Matching.eta (1 / r) = FireProof.Matching.eta r := by
  have hr0 : r ≠ 0 := ne_of_gt hr
  have hsum : 1 + r ≠ 0 := by linarith
  have hrecip : 1 + 1 / r ≠ 0 := by positivity
  unfold FireProof.Matching.eta
  field_simp [hr0, hsum, hrecip]
  ring

def matchedForcing (C F : ℝ) : ℝ :=
  C * F * FireProof.Matching.eta (C / F)

def closedForcing (C F : ℝ) : ℝ := 4 * C ^ 2 * F ^ 2 / (C + F) ^ 2

theorem matchedForcing_closed_form
    {C F : ℝ} (hC : 0 < C) (hF : 0 < F) :
    matchedForcing C F = 4 * C ^ 2 * F ^ 2 / (C + F) ^ 2 := by
  have hF0 : F ≠ 0 := ne_of_gt hF
  have hSum : C + F ≠ 0 := ne_of_gt (add_pos hC hF)
  have hRewrite : 1 + C / F = (C + F) / F := by
    field_simp [hF0]
    ring
  unfold matchedForcing FireProof.Matching.eta
  rw [hRewrite]
  field_simp [hF0, hSum]
  ring

theorem matchedForcing_eq_closedForcing
    {C F : ℝ} (hC : 0 < C) (hF : 0 < F) :
    matchedForcing C F = closedForcing C F := by
  exact matchedForcing_closed_form hC hF

theorem closedForcing_at_match (s : ℝ) (hs : s ≠ 0) :
    closedForcing s s = s ^ 2 := by
  unfold closedForcing
  field_simp [hs]
  ring

theorem matchedForcing_le_product
    {C F : ℝ} (hC : 0 < C) (hF : 0 < F) :
    matchedForcing C F ≤ C * F := by
  unfold matchedForcing
  have heta := FireProof.Matching.eta_le_one (div_pos hC hF)
  nlinarith [mul_pos hC hF]

theorem closedForcing_normalized_by_C_sq
    {C F : ℝ} (hC : C ≠ 0) (hSum : C + F ≠ 0) :
    closedForcing C F / C ^ 2 = 4 * F ^ 2 / (C + F) ^ 2 := by
  unfold closedForcing
  field_simp [hC, hSum]
  ring

theorem closedForcing_normalized_by_F_sq
    {C F : ℝ} (hF : F ≠ 0) (hSum : C + F ≠ 0) :
    closedForcing C F / F ^ 2 = 4 * C ^ 2 / (C + F) ^ 2 := by
  unfold closedForcing
  field_simp [hF, hSum]
  ring

theorem closedForcing_hasDerivAt_C
    {C F : ℝ} (hSum : C + F ≠ 0) :
    HasDerivAt (fun z => closedForcing z F)
      (8 * C * F ^ 3 / (C + F) ^ 3) C := by
  have hnum : HasDerivAt (fun z : ℝ => 4 * z ^ 2 * F ^ 2)
      (8 * C * F ^ 2) C := by
    convert ((hasDerivAt_id C).pow 2).const_mul (4 * F ^ 2) using 1
    · funext z
      simp only [id_eq]
      ring
    · simp only [id_eq]
      ring
  have hbase : HasDerivAt (fun z : ℝ => z + F) 1 C := by
    simpa using (hasDerivAt_id C).add_const F
  have hden : HasDerivAt (fun z : ℝ => (z + F) ^ 2) (2 * (C + F)) C := by
    convert hbase.pow 2 using 1 <;> ring
  unfold closedForcing
  convert hnum.div hden (pow_ne_zero 2 hSum) using 1
  field_simp [hSum]
  ring

theorem closedForcing_strictly_increases_in_C_locally
    {C F : ℝ} (hC : 0 < C) (hF : 0 < F) :
    0 < 8 * C * F ^ 3 / (C + F) ^ 3 := by
  positivity

theorem matchedForcing_symmetric
    {C F : ℝ} (hC : 0 < C) (hF : 0 < F) :
    matchedForcing C F = matchedForcing F C := by
  rw [matchedForcing_closed_form hC hF]
  rw [matchedForcing_closed_form hF hC]
  ring

/-- Exact cubic area and quadratic perimeter laws already force one algebraic
perimeter-area relation; they are not three independent predictions. -/
theorem cubic_quadratic_headlines_are_dependent
    {x A P k : ℝ} (hA : A = x ^ 3) (hP : P = k * x ^ 2) :
    P ^ 3 = k ^ 3 * A ^ 2 := by
  rw [hA, hP]
  ring

/-- A purely kinematic construction reproduces all three headline powers,
without assigning any metabolic interpretation to `x`. -/
theorem kinematic_alternative_all_three (t k : ℝ) :
    let A := t ^ 3
    let P := k * t ^ 2
    A = t ^ 3 ∧ P = k * t ^ 2 ∧ P ^ 3 = k ^ 3 * A ^ 2 := by
  dsimp
  constructor
  · rfl
  constructor
  · rfl
  · ring

end
end FireProof.MechanismTests
