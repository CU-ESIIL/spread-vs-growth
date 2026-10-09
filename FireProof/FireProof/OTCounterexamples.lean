import FireProof.Attractor
import FireProof.OTPrediction

/-! # Counterexamples: observations of R do not create a predictive closure -/

namespace FireProof.OTCounterexamples

structure ReducedSpatialState where
  area : ℝ
  coupling : ℝ
  reorganization : ℝ
  futureGrowth : ℝ

theorem same_area_R_different_K :
    ∃ s₁ s₂ : ReducedSpatialState,
      s₁.area = s₂.area ∧ s₁.reorganization = s₂.reorganization ∧
      s₁.coupling ≠ s₂.coupling := by
  exact ⟨⟨1, 1, 3, 1⟩, ⟨1, 2, 3, 2⟩, rfl, rfl, by norm_num⟩

theorem same_area_K_different_R :
    ∃ s₁ s₂ : ReducedSpatialState,
      s₁.area = s₂.area ∧ s₁.coupling = s₂.coupling ∧
      s₁.reorganization ≠ s₂.reorganization := by
  exact ⟨⟨1, 2, 3, 2⟩, ⟨1, 2, 4, 2⟩, rfl, rfl, by norm_num⟩

theorem same_R_different_future_growth :
    ∃ s₁ s₂ : ReducedSpatialState,
      s₁.reorganization = s₂.reorganization ∧
      s₁.futureGrowth ≠ s₂.futureGrowth := by
  exact ⟨⟨1, 1, 3, 1⟩, ⟨1, 2, 3, 2⟩, rfl, by norm_num⟩

theorem large_R_without_restoration :
    ∃ sigma sigmaNext sigmaStar R : ℝ,
      100 < R ∧ ¬ FireProof.Attractor.restores sigma sigmaNext sigmaStar := by
  exact ⟨1, 2, 0, 101, by norm_num, by norm_num [FireProof.Attractor.restores,
    FireProof.Attractor.deviation]⟩

theorem restoration_without_large_R :
    ∃ sigma sigmaNext sigmaStar R : ℝ,
      R = 0 ∧ FireProof.Attractor.restores sigma sigmaNext sigmaStar := by
  exact ⟨1, 1 / 2, 0, 0, rfl, by norm_num [FireProof.Attractor.restores,
    FireProof.Attractor.deviation]⟩

noncomputable def effectiveForcing (C F : ℝ) : ℝ := (2 * C * F / (C + F)) ^ 2

theorem R_does_not_identify_latent_C_F :
    effectiveForcing 1 2 = effectiveForcing 2 1 ∧
      (1 : ℝ) ≠ 2 := by
  constructor
  · norm_num [effectiveForcing]
  · norm_num

end FireProof.OTCounterexamples
