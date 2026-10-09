import FireProof.Reorganization

/-!
# Prediction sets under an empirical reorganization closure

The interval closure below is an explicit scientific premise. The strict
narrowing theorem is mathematical once that closure supplies finite bounds.
-/

namespace FireProof.OTPrediction

def StrictlyNarrows {α : Type} (restricted baseline : Set α) : Prop :=
  restricted ⊆ baseline ∧ ∃ x, x ∈ baseline ∧ x ∉ restricted

def boundedFutureK (lower upper : ℝ) : Set ℝ := Set.Icc lower upper

theorem observed_R_strictly_narrows_unconstrained_K
    {lower upper : ℝ} (horder : lower ≤ upper) :
    Set.Nonempty (boundedFutureK lower upper) ∧
      StrictlyNarrows (boundedFutureK lower upper) Set.univ := by
  constructor
  · exact ⟨lower, le_rfl, horder⟩
  · constructor
    · exact Set.subset_univ _
    · refine ⟨upper + 1, Set.mem_univ _, ?_⟩
      simp only [boundedFutureK, Set.mem_Icc, not_and]
      intro _
      linarith

theorem coupling_interval_gives_growth_interval
    {lowerK upperK K areaPower growth : ℝ}
    (harea : 0 ≤ areaPower) (hlower : lowerK ≤ K) (hupper : K ≤ upperK)
    (hgrowth : growth = K * areaPower) :
    lowerK * areaPower ≤ growth ∧ growth ≤ upperK * areaPower := by
  constructor <;> rw [hgrowth] <;> nlinarith

/-- This is the candidate empirical closure, not a theorem about fires. -/
def RBoundsFutureK (Hlower Hupper : ℝ → ℝ) (R futureK : ℝ) : Prop :=
  futureK ∈ Set.Icc (Hlower R) (Hupper R)

end FireProof.OTPrediction
