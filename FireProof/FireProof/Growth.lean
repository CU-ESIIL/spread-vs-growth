import FireProof.Assumptions

/-! # Constant-coefficient growth law and rigorous late-time statements -/

open Filter Set
open scoped Topology

namespace FireProof.Growth

noncomputable section

theorem transformed_derivative
    {A : ℝ → ℝ} {t A' beta sigma : ℝ}
    (hA : HasDerivAt A A' t) (hpos : 0 < A t)
    (hGrowth : A' = beta * A t ^ sigma) :
    HasDerivAt (fun u => A u ^ (1 - sigma)) ((1 - sigma) * beta) t := by
  have hpow := hA.rpow_const (p := 1 - sigma) (Or.inl (ne_of_gt hpos))
  have hcancel : A t ^ sigma * A t ^ ((1 - sigma) - 1) = 1 := by
    rw [← Real.rpow_add hpos]
    norm_num
  convert hpow using 1
  calc
    (1 - sigma) * beta = beta * (1 - sigma) *
        (A t ^ sigma * A t ^ (1 - sigma - 1)) := by rw [hcancel]; ring
    _ = A' * (1 - sigma) * A t ^ (1 - sigma - 1) := by rw [hGrowth]; ring

theorem constant_beta_solution_on_interval
    {A : ℝ → ℝ} {t0 t A0 beta sigma : ℝ}
    (ht : t0 ≤ t) (hInit : A t0 = A0)
    (hpos : ∀ u ∈ Icc t0 t, 0 < A u)
    (hGrowth : ∀ u ∈ Icc t0 t,
      HasDerivAt A (beta * A u ^ sigma) u) :
    A t ^ (1 - sigma) =
      A0 ^ (1 - sigma) + (1 - sigma) * beta * (t - t0) := by
  let Y : ℝ → ℝ := fun u => A u ^ (1 - sigma)
  let G : ℝ → ℝ := fun u => A0 ^ (1 - sigma) + (1 - sigma) * beta * (u - t0)
  have hYderiv : ∀ u ∈ Icc t0 t, HasDerivAt Y ((1 - sigma) * beta) u := by
    intro u hu
    exact transformed_derivative (hGrowth u hu) (hpos u hu) rfl
  have hGderiv : ∀ u : ℝ, HasDerivAt G ((1 - sigma) * beta) u := by
    intro u
    dsimp [G]
    convert (hasDerivAt_id u).sub_const t0 |>.const_mul ((1 - sigma) * beta)
      |>.const_add (A0 ^ (1 - sigma)) using 1 <;> ring
  have hYcont : ContinuousOn Y (Icc t0 t) :=
    continuousOn_of_forall_continuousAt fun u hu => (hYderiv u hu).continuousAt
  have hGcont : ContinuousOn G (Icc t0 t) :=
    continuousOn_of_forall_continuousAt fun u _ => (hGderiv u).continuousAt
  have hEq := eq_of_has_deriv_right_eq
    (f := Y) (g := G) (f' := fun _ => (1 - sigma) * beta)
    (fun u hu => (hYderiv u (mem_Icc_of_Ico hu)).hasDerivWithinAt)
    (fun u _ => (hGderiv u).hasDerivWithinAt)
    hYcont hGcont
    (by simp [Y, G, hInit])
  simpa [Y, G] using hEq t (right_mem_Icc.mpr ht)

theorem two_thirds_transformed_solution
    {A : ℝ → ℝ} {t0 t A0 beta : ℝ}
    (ht : t0 ≤ t) (hInit : A t0 = A0)
    (hpos : ∀ u ∈ Icc t0 t, 0 < A u)
    (hGrowth : ∀ u ∈ Icc t0 t,
      HasDerivAt A (beta * A u ^ ((2 : ℝ) / 3)) u) :
    A t ^ ((1 : ℝ) / 3) = A0 ^ ((1 : ℝ) / 3) +
      (beta / 3) * (t - t0) := by
  convert constant_beta_solution_on_interval ht hInit hpos hGrowth using 1 <;>
    ring

theorem shifted_cubic_exact
    {x0 beta t t0 : ℝ} (hbeta : beta ≠ 0) :
    (x0 + (beta / 3) * (t - t0)) ^ 3 =
      (beta / 3) ^ 3 * (t + (3 * x0 / beta - t0)) ^ 3 := by
  field_simp
  ring

theorem shifted_cubic_ratio_limit (x0 b : ℝ) :
    Tendsto (fun t : ℝ => (x0 + b * t) ^ 3 / t ^ 3) atTop (𝓝 (b ^ 3)) := by
  have hsmall : Tendsto (fun t : ℝ => x0 / t) atTop (𝓝 0) :=
    tendsto_const_nhds.div_atTop tendsto_id
  have hpow : Tendsto (fun t : ℝ => (x0 / t + b) ^ 3) atTop (𝓝 (b ^ 3)) := by
    simpa using (hsmall.add tendsto_const_nhds).pow 3
  apply hpow.congr'
  filter_upwards [eventually_ne_atTop (0 : ℝ)] with t ht
  field_simp

theorem shifted_quadratic_ratio_limit (x0 b k : ℝ) :
    Tendsto (fun t : ℝ => k * (x0 + b * t) ^ 2 / t ^ 2) atTop
      (𝓝 (k * b ^ 2)) := by
  have hsmall : Tendsto (fun t : ℝ => x0 / t) atTop (𝓝 0) :=
    tendsto_const_nhds.div_atTop tendsto_id
  have hpow : Tendsto (fun t : ℝ => k * (x0 / t + b) ^ 2) atTop
      (𝓝 (k * b ^ 2)) := by
    simpa using tendsto_const_nhds.mul ((hsmall.add tendsto_const_nhds).pow 2)
  apply hpow.congr'
  filter_upwards [eventually_ne_atTop (0 : ℝ)] with t ht
  field_simp

end
end FireProof.Growth
