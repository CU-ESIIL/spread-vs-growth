import FireProof.Metabolism
import FireProof.Matching

/-!
# Fire life-cycle logic

These are pointwise consequences of the relative-derivative identity. They do
not assert that the balance changes sign, changes sign only once, or reaches
zero in finite time.
-/

namespace FireProof.Lifecycle

noncomputable section

def peakBalance (Cdot C Fdot F etadot eta M A : ℝ) : ℝ :=
  Cdot / C + Fdot / F + etadot / eta + ((2 : ℝ) / 3) * M / A

theorem derivative_eq_metabolism_mul_balance
    {M Mdot B : ℝ} (hM : M ≠ 0) (hrel : Mdot / M = B) :
    Mdot = M * B := by
  have h := (div_eq_iff hM).mp hrel
  nlinarith

theorem peak_iff_balance_zero
    {M Mdot B : ℝ} (hM : M ≠ 0) (hrel : Mdot / M = B) :
    Mdot = 0 ↔ B = 0 := by
  rw [derivative_eq_metabolism_mul_balance hM hrel]
  exact mul_eq_zero.trans (or_iff_right hM)

theorem acceleration_sign_is_balance_sign
    {M Mdot B : ℝ} (hM : 0 < M) (hrel : Mdot / M = B) :
    (0 < Mdot ↔ 0 < B) ∧ (Mdot < 0 ↔ B < 0) := by
  have heq := derivative_eq_metabolism_mul_balance (ne_of_gt hM) hrel
  rw [heq]
  constructor
  · constructor <;> intro h <;> nlinarith
  · constructor <;> intro h <;> nlinarith

theorem matching_relative_derivative
    {C F : ℝ → ℝ} {t Cdot Fdot : ℝ}
    (hCderiv : HasDerivAt C Cdot t) (hFderiv : HasDerivAt F Fdot t)
    (hCpos : 0 < C t) (hFpos : 0 < F t) :
    let etaPath := fun u => FireProof.Matching.eta (C u / F u)
    ∃ etadot, HasDerivAt etaPath etadot t ∧
      etadot / etaPath t =
        ((F t - C t) / (F t + C t)) *
          (Cdot / C t - Fdot / F t) := by
  let r := C t / F t
  have hF0 : F t ≠ 0 := ne_of_gt hFpos
  have hrpos : 0 < r := div_pos hCpos hFpos
  have hOneR : 1 + r ≠ 0 := by positivity
  have hrderiv : HasDerivAt (fun u => C u / F u)
      ((Cdot * F t - C t * Fdot) / (F t) ^ 2) t := by
    convert hCderiv.div hFderiv hF0 using 1 <;> ring
  have hnum : HasDerivAt (fun z : ℝ => 4 * z) 4 r := by
    simpa using (hasDerivAt_id r).const_mul 4
  have hbase : HasDerivAt (fun z : ℝ => 1 + z) 1 r := by
    simpa using (hasDerivAt_const r 1).add (hasDerivAt_id r)
  have hden : HasDerivAt (fun z : ℝ => (1 + z) ^ 2) (2 * (1 + r)) r := by
    convert hbase.pow 2 using 1 <;> ring
  have heta : HasDerivAt FireProof.Matching.eta
      (4 * (1 - r) / (1 + r) ^ 3) r := by
    unfold FireProof.Matching.eta
    convert hnum.div hden (pow_ne_zero 2 hOneR) using 1
    field_simp [hOneR]
    ring
  let etadot :=
    (4 * (1 - r) / (1 + r) ^ 3) *
      ((Cdot * F t - C t * Fdot) / (F t) ^ 2)
  refine ⟨etadot, ?_, ?_⟩
  · exact heta.comp t hrderiv
  · dsimp [etadot, r]
    unfold FireProof.Matching.eta
    have hC0 : C t ≠ 0 := ne_of_gt hCpos
    have hSum : F t + C t ≠ 0 := ne_of_gt (add_pos hFpos hCpos)
    field_simp [hC0, hF0, hSum]
    ring

/-- For `eta(r)=4r/(1+r)^2` and `r=C/F`, the matching contribution can be
written without differentiating a quotient explicitly. -/
theorem matching_balance_reduction
    {C F Cdot Fdot etadot eta M A : ℝ}
    (hC : C ≠ 0) (hF : F ≠ 0) (hSum : C + F ≠ 0) (hA : A ≠ 0)
    (hEtaRel : etadot / eta =
      ((F - C) / (F + C)) * (Cdot / C - Fdot / F)) :
    peakBalance Cdot C Fdot F etadot eta M A =
      (2 * F / (F + C)) * (Cdot / C) +
      (2 * C / (F + C)) * (Fdot / F) +
      ((2 : ℝ) / 3) * M / A := by
  have hSum' : F + C ≠ 0 := by simpa [add_comm] using hSum
  unfold peakBalance
  rw [hEtaRel]
  field_simp [hC, hF, hSum, hSum', hA]
  ring

theorem closed_peak_balance
    {alpha mu C F M deltaA A Cdot Fdot etadot eta : ℝ}
    (hC : C ≠ 0) (hF : F ≠ 0) (hSum : C + F ≠ 0)
    (hDelta : deltaA ≠ 0) (hA : A ≠ 0)
    (hCdot : Cdot = alpha * C * (1 - C) * F - mu * C)
    (hFdot : Fdot = -M / deltaA)
    (hEtaRel : etadot / eta =
      ((F - C) / (F + C)) * (Cdot / C - Fdot / F)) :
    peakBalance Cdot C Fdot F etadot eta M A =
      (2 * F / (F + C)) * (alpha * (1 - C) * F - mu) -
      (2 * C / (F + C)) * (M / (deltaA * F)) +
      ((2 : ℝ) / 3) * M / A := by
  have hSum' : F + C ≠ 0 := by simpa [add_comm] using hSum
  rw [matching_balance_reduction hC hF hSum hA hEtaRel, hCdot, hFdot]
  field_simp [hC, hF, hSum, hSum', hDelta, hA]
  ring

/-- The relative-derivative identity alone permits perpetual acceleration. -/
example (t : ℝ) :
    HasDerivAt Real.exp (Real.exp t) t ∧ Real.exp t ≠ 0 := by
  exact ⟨Real.hasDerivAt_exp t, ne_of_gt (Real.exp_pos t)⟩

/-- It also permits decline from the initial instant, with no interior peak. -/
example (t : ℝ) :
    HasDerivAt (fun u => Real.exp (-u)) (-Real.exp (-t)) t := by
  convert (Real.hasDerivAt_exp (-t)).comp t (hasDerivAt_neg t) using 1 <;> ring

end
end FireProof.Lifecycle
