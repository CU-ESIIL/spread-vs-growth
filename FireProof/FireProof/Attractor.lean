import FireProof.Assumptions

/-! # Generic geometric-attractor algebra -/

namespace FireProof.Attractor

def deviation (sigma sigmaStar : ℝ) : ℝ := sigma - sigmaStar

def restores (sigma sigmaNext sigmaStar : ℝ) : Prop :=
  deviation sigma sigmaStar * (sigmaNext - sigma) < 0

def lyapunov (sigma sigmaStar : ℝ) : ℝ := (sigma - sigmaStar) ^ 2

theorem linear_step_restores
    {sigma sigmaNext sigmaStar lambda : ℝ}
    (hlambda : 0 < lambda) (hne : sigma ≠ sigmaStar)
    (hstep : sigmaNext - sigma = -lambda * (sigma - sigmaStar)) :
    restores sigma sigmaNext sigmaStar := by
  unfold restores deviation
  rw [hstep]
  have hsquare : 0 < (sigma - sigmaStar) ^ 2 := sq_pos_of_ne_zero (sub_ne_zero.mpr hne)
  nlinarith

theorem linear_step_decreases_lyapunov
    {sigma sigmaNext sigmaStar lambda : ℝ}
    (hlambda0 : 0 < lambda) (hlambda2 : lambda < 2)
    (hne : sigma ≠ sigmaStar)
    (hstep : sigmaNext = sigma - lambda * (sigma - sigmaStar)) :
    lyapunov sigmaNext sigmaStar < lyapunov sigma sigmaStar := by
  unfold lyapunov
  rw [hstep]
  have hsquare : 0 < (sigma - sigmaStar) ^ 2 := sq_pos_of_ne_zero (sub_ne_zero.mpr hne)
  nlinarith [mul_pos hlambda0 (sub_pos.mpr hlambda2)]

theorem attraction_math_does_not_select_two_thirds
    (sigma sigmaNext sigmaStar : ℝ) :
    restores sigma sigmaNext sigmaStar =
      (deviation sigma sigmaStar * (sigmaNext - sigma) < 0) := by
  rfl

end FireProof.Attractor
