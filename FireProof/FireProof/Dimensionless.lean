import FireProof.Lifecycle

/-!
# Dimensionless two-state system

Use `x=A/Amax`, `x0=A0/Amax`, and `tau=alpha*t`. The canonical groups are
`gamma=beta0/(alpha*Amax^(1/3))` and `delta=mu/alpha`; `x0` remains as a
dimensionless geometric initial condition.
-/

namespace FireProof.Dimensionless

noncomputable section

def fuel (x0 x : ℝ) : ℝ := (1 - x) / (1 - x0)

def areaField (gamma x0 x C : ℝ) : ℝ :=
  let F := fuel x0 x
  gamma * C * F * FireProof.Matching.eta (C / F) * x ^ ((2 : ℝ) / 3)

def connectivityField (delta x0 x C : ℝ) : ℝ :=
  C * ((1 - C) * fuel x0 x - delta)

/-- Dimensionless relative-growth balance after eliminating `eta'`. The
transition surface is `transitionBalance = 0`; its sign determines the sign of
the metabolic acceleration when the relative-derivative identity holds. -/
def transitionBalance (delta x0 x C m : ℝ) : ℝ :=
  let F := fuel x0 x
  (2 * F / (F + C)) * ((1 - C) * F - delta) -
    (2 * C / (F + C)) * (m / ((1 - x0) * F)) +
    ((2 : ℝ) / 3) * m / x

theorem peakBalance_eq_transitionBalance
    {delta x0 x C m Cdot Fdot etadot eta : ℝ}
    (hC : C ≠ 0) (hF : fuel x0 x ≠ 0)
    (hSum : C + fuel x0 x ≠ 0) (hRange : 1 - x0 ≠ 0) (hx : x ≠ 0)
    (hCdot : Cdot = C * ((1 - C) * fuel x0 x - delta))
    (hFdot : Fdot = -m / (1 - x0))
    (hEtaRel : etadot / eta =
      ((fuel x0 x - C) / (fuel x0 x + C)) *
        (Cdot / C - Fdot / fuel x0 x)) :
    FireProof.Lifecycle.peakBalance
      Cdot C Fdot (fuel x0 x) etadot eta m x =
        transitionBalance delta x0 x C m := by
  have hCdot' :
      Cdot = (1 : ℝ) * C * (1 - C) * fuel x0 x - delta * C := by
    rw [hCdot]
    ring
  have h := FireProof.Lifecycle.closed_peak_balance
    (alpha := (1 : ℝ)) (mu := delta) (C := C) (F := fuel x0 x)
    (M := m) (deltaA := 1 - x0) (A := x)
    hC hF hSum hRange hx
    hCdot' hFdot hEtaRel
  simpa [transitionBalance] using h

theorem connectivity_positive_iff
    {delta x0 x C : ℝ} (hC : 0 < C) :
    0 < connectivityField delta x0 x C ↔
      delta < (1 - C) * fuel x0 x := by
  unfold connectivityField
  rw [mul_pos_iff_of_pos_left hC]
  constructor <;> intro h <;> linarith

theorem connectivity_zero_iff
    {delta x0 x C : ℝ} (hC : C ≠ 0) :
    connectivityField delta x0 x C = 0 ↔
      (1 - C) * fuel x0 x = delta := by
  unfold connectivityField
  rw [mul_eq_zero]
  simp only [hC, false_or]
  constructor <;> intro h <;> linarith

/-- Analytic extinction-dominated boundary: if `delta >= 1`, recruitment is
impossible anywhere in the biological unit square. -/
theorem no_connectivity_recruitment_of_one_le_delta
    {delta x0 x C : ℝ} (hdelta : 1 ≤ delta)
    (hC0 : 0 ≤ C) (hC1 : C ≤ 1)
    (hF0 : 0 ≤ fuel x0 x) (hF1 : fuel x0 x ≤ 1) :
    connectivityField delta x0 x C ≤ 0 := by
  unfold connectivityField
  have hOneC : 0 ≤ 1 - C := sub_nonneg.mpr hC1
  have hprod : (1 - C) * fuel x0 x ≤ 1 := by nlinarith
  exact mul_nonpos_of_nonneg_of_nonpos hC0 (by linarith)

theorem fuel_threshold_for_positive_equilibrium
    {delta F Cstar : ℝ}
    (hdef : Cstar = 1 - delta / F) (hF : 0 < F) :
    0 < Cstar ↔ delta < F := by
  rw [hdef, sub_pos, div_lt_one hF]

end
end FireProof.Dimensionless
