import FireProof.Assumptions

/-!
# Geometric scaling

The general exponent elimination is stated in logarithmic form. This is
equivalent to positive power-law scaling and makes every positivity condition
visible. The special `4/3 -> 2/3` result is then exact arithmetic.
-/

namespace FireProof.Scaling

noncomputable section

theorem eliminate_shared_log_size
    {A P L cA cP DA Dh : ℝ}
    (hA : Real.log A = Real.log cA + DA * Real.log L)
    (hP : Real.log P = Real.log cP + Dh * Real.log L)
    (hDA : DA ≠ 0) :
    Real.log P =
      (Real.log cP - (Dh / DA) * Real.log cA) +
        (Dh / DA) * Real.log A := by
  rw [hA, hP]
  field_simp
  ring

theorem four_thirds_over_two : ((4 : ℝ) / 3) / 2 = (2 : ℝ) / 3 := by
  norm_num

theorem four_thirds_implies_two_thirds
    {A P L cA cP : ℝ}
    (hA : Real.log A = Real.log cA + 2 * Real.log L)
    (hP : Real.log P = Real.log cP + ((4 : ℝ) / 3) * Real.log L) :
    Real.log P =
      (Real.log cP - ((2 : ℝ) / 3) * Real.log cA) +
        ((2 : ℝ) / 3) * Real.log A := by
  convert eliminate_shared_log_size hA hP (by norm_num : (2 : ℝ) ≠ 0) using 1 <;>
    norm_num

/-- Explicit coefficient after eliminating the shared size in logarithmic form. -/
def eliminatedCoefficient (cA cP DA Dh : ℝ) : ℝ :=
  Real.exp (Real.log cP - (Dh / DA) * Real.log cA)

theorem eliminatedCoefficient_pos {cA cP DA Dh : ℝ} :
    0 < eliminatedCoefficient cA cP DA Dh := by
  exact Real.exp_pos _

theorem eliminatedCoefficient_eq_div_rpow
    {cA cP DA Dh : ℝ} (hcApos : 0 < cA) (hcPpos : 0 < cP) :
    eliminatedCoefficient cA cP DA Dh = cP / cA ^ (Dh / DA) := by
  unfold eliminatedCoefficient
  rw [Real.exp_sub, Real.exp_log hcPpos, Real.rpow_def_of_pos hcApos]
  congr 2
  ring

theorem eliminate_shared_positive
    {A P L cA cP DA Dh : ℝ}
    (hApos : 0 < A) (hPpos : 0 < P) (hLpos : 0 < L)
    (hcApos : 0 < cA) (hcPpos : 0 < cP)
    (hA : Real.log A = Real.log cA + DA * Real.log L)
    (hP : Real.log P = Real.log cP + Dh * Real.log L)
    (hDA : DA ≠ 0) :
    P = eliminatedCoefficient cA cP DA Dh * A ^ (Dh / DA) := by
  have hlog := eliminate_shared_log_size hA hP hDA
  rw [← Real.exp_log hPpos, hlog, Real.exp_add]
  unfold eliminatedCoefficient
  rw [Real.rpow_def_of_pos hApos]
  congr 1
  ring

theorem four_thirds_power_law
    {A P L cA cP : ℝ}
    (hApos : 0 < A) (hPpos : 0 < P) (hLpos : 0 < L)
    (hcApos : 0 < cA) (hcPpos : 0 < cP)
    (hA : Real.log A = Real.log cA + 2 * Real.log L)
    (hP : Real.log P = Real.log cP + ((4 : ℝ) / 3) * Real.log L) :
    P = eliminatedCoefficient cA cP 2 ((4 : ℝ) / 3) * A ^ ((2 : ℝ) / 3) := by
  convert eliminate_shared_positive hApos hPpos hLpos hcApos hcPpos hA hP
    (by norm_num : (2 : ℝ) ≠ 0) using 1 <;> norm_num

/-- Direct version of the proportionality argument. Here the assumptions are
the positive multiplicative power laws themselves, not their logarithms. -/
theorem eliminate_direct_power_laws
    {A P L cA cP DA Dh : ℝ}
    (hLpos : 0 < L) (hcApos : 0 < cA) (hcPpos : 0 < cP)
    (hA : A = cA * L ^ DA) (hP : P = cP * L ^ Dh)
    (hDA : DA ≠ 0) :
    P = (cP / cA ^ (Dh / DA)) * A ^ (Dh / DA) := by
  have hApos : 0 < A := by
    rw [hA]
    exact mul_pos hcApos (Real.rpow_pos_of_pos hLpos _)
  have hPpos : 0 < P := by
    rw [hP]
    exact mul_pos hcPpos (Real.rpow_pos_of_pos hLpos _)
  have hAlog : Real.log A = Real.log cA + DA * Real.log L := by
    rw [hA, Real.log_mul (ne_of_gt hcApos)
      (ne_of_gt (Real.rpow_pos_of_pos hLpos DA)), Real.log_rpow hLpos]
  have hPlog : Real.log P = Real.log cP + Dh * Real.log L := by
    rw [hP, Real.log_mul (ne_of_gt hcPpos)
      (ne_of_gt (Real.rpow_pos_of_pos hLpos Dh)), Real.log_rpow hLpos]
  rw [← eliminatedCoefficient_eq_div_rpow hcApos hcPpos]
  exact eliminate_shared_positive hApos hPpos hLpos hcApos hcPpos hAlog hPlog hDA

theorem four_thirds_direct_power_law
    {A P L cA cP : ℝ}
    (hLpos : 0 < L) (hcApos : 0 < cA) (hcPpos : 0 < cP)
    (hA : A = cA * L ^ (2 : ℝ))
    (hP : P = cP * L ^ ((4 : ℝ) / 3)) :
    P = (cP / cA ^ ((2 : ℝ) / 3)) * A ^ ((2 : ℝ) / 3) := by
  convert eliminate_direct_power_laws hLpos hcApos hcPpos hA hP
    (by norm_num : (2 : ℝ) ≠ 0) using 1 <;> norm_num

end
end FireProof.Scaling
