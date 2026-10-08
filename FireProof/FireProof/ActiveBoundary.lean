import FireProof.Growth

/-! # Active-boundary substitution -/

namespace FireProof.ActiveBoundary

theorem active_boundary_substitution
    {A23 Pa veff k C v0 F eta beta0 areaRate : ℝ}
    (hPa : Pa = k * C * A23)
    (hveff : veff = v0 * F * eta)
    (hbeta : beta0 = v0 * k)
    (hkin : areaRate = veff * Pa) :
    areaRate = beta0 * C * F * eta * A23 := by
  rw [hkin, hveff, hPa, hbeta]
  ring

/-- Cubed transformed state. This polynomial version isolates the exact chain
rule without any ambiguity about fractional powers. -/
theorem cube_transform_derivative
    {A X : ℝ → ℝ} {t X' beta0 C F eta : ℝ}
    (hX : HasDerivAt X X' t)
    (hCube : A = fun u => (X u) ^ 3)
    (hXpos : 0 < X t)
    (hGrowth : HasDerivAt A (beta0 * C * F * eta * (X t) ^ 2) t) :
    X' = (beta0 / 3) * C * F * eta := by
  have hCubeDeriv : HasDerivAt A (3 * (X t) ^ 2 * X') t := by
    rw [hCube]
    convert hX.pow 3 using 1 <;> ring
  have heq := hCubeDeriv.unique hGrowth
  have hsq : (X t) ^ 2 ≠ 0 := pow_ne_zero _ (ne_of_gt hXpos)
  apply (mul_left_cancel₀ hsq)
  field_simp at heq ⊢
  nlinarith

theorem cube_of_positive_rpow_one_third {a : ℝ} (ha : 0 < a) :
    (a ^ ((1 : ℝ) / 3)) ^ 3 = a := by
  convert Real.rpow_inv_natCast_pow (n := 3) (le_of_lt ha) (by norm_num) using 1 <;>
    norm_num

/-- Direct formulation with `X = A^(1/3)`: the explicit area factor cancels
exactly, rather than approximately. -/
theorem cube_root_removes_explicit_area
    {A : ℝ → ℝ} {t A' beta0 C F eta : ℝ}
    (hA : HasDerivAt A A' t) (hApos : 0 < A t)
    (hGrowth : A' = beta0 * C * F * eta * A t ^ ((2 : ℝ) / 3)) :
    HasDerivAt (fun u => A u ^ ((1 : ℝ) / 3))
      ((beta0 / 3) * C * F * eta) t := by
  convert FireProof.Growth.transformed_derivative
    (sigma := (2 : ℝ) / 3) hA hApos hGrowth using 1 <;> ring

end FireProof.ActiveBoundary
