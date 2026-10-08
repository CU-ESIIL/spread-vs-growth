import Mathlib

/-!
# Shared assumptions and evidence boundary

This file contains only mathematical vocabulary. No declaration says that an
observed wildfire satisfies any closure used by the theory.
-/

namespace FireProof

/-- Exact proportionality with an explicit, strictly positive coefficient. -/
def PosProportional (x y : ℝ) : Prop := ∃ c : ℝ, 0 < c ∧ x = c * y

/-- A predicate marking a premise supplied by observations rather than proof. -/
structure EmpiricalPremise (statement : Prop) : Prop where
  supplied : statement

/-- A trajectory cannot jump across a barrier without attaining it first.
Continuity plus a suitable interval hypothesis is the usual source. -/
def HasIntermediateBarrierProperty (x : ℝ → ℝ) (barrier t0 : ℝ) : Prop :=
  ∀ ⦃t : ℝ⦄, t0 ≤ t → barrier < x t →
    ∃ s ∈ Set.Icc t0 t, x s = barrier

/-- Once a trajectory reaches a barrier, it remains on the permitted side.
For an ODE this normally comes from existence and uniqueness (for example,
local Lipschitz continuity of the vector field), not merely the sign at one
point. -/
def HasUpperBarrierUniqueness (x : ℝ → ℝ) (barrier : ℝ) : Prop :=
  ∀ ⦃s t : ℝ⦄, s ≤ t → x s = barrier → x t ≤ barrier

def HasLowerIntermediateBarrierProperty (x : ℝ → ℝ) (barrier t0 : ℝ) : Prop :=
  ∀ ⦃t : ℝ⦄, t0 ≤ t → x t < barrier →
    ∃ s ∈ Set.Icc t0 t, x s = barrier

def HasLowerBarrierUniqueness (x : ℝ → ℝ) (barrier : ℝ) : Prop :=
  ∀ ⦃s t : ℝ⦄, s ≤ t → x s = barrier → barrier ≤ x t

end FireProof
