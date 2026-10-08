import FireProof.Assumptions

/-! # Local slopes and the exponent-identifiability counterexample -/

namespace FireProof.Identifiability

noncomputable section

/-- Use `x = log a`. Then `p = kappa * exp (sigma*x)`, and this theorem is
exactly the SI's derivative with respect to `log a`. -/
theorem local_log_slope
    {kappa sigma : ℝ → ℝ} {x kappa' sigma' : ℝ}
    (hk : HasDerivAt kappa kappa' x) (hs : HasDerivAt sigma sigma' x)
    (hkpos : 0 < kappa x) :
    let p := fun y => kappa y * Real.exp (sigma y * y)
    ∃ p', HasDerivAt p p' x ∧
      p' / p x = sigma x + kappa' / kappa x + x * sigma' := by
  let e := fun y => Real.exp (sigma y * y)
  have hinner : HasDerivAt (fun y => sigma y * y) (sigma' * x + sigma x) x := by
    simpa [id] using hs.mul (hasDerivAt_id x)
  have he : HasDerivAt e (Real.exp (sigma x * x) * (sigma' * x + sigma x)) x := by
    simpa [e] using hinner.exp
  let p := fun y => kappa y * e y
  let p' := kappa' * e x + kappa x *
    (Real.exp (sigma x * x) * (sigma' * x + sigma x))
  refine ⟨p', ?_, ?_⟩
  · exact hk.mul he
  · dsimp [p, p', e]
    have hexp : Real.exp (sigma x * x) ≠ 0 := ne_of_gt (Real.exp_pos _)
    field_simp [ne_of_gt hkpos, hexp]
    ring

theorem half_plus_one_sixth_counterexample {a : ℝ} (ha : 0 < a) :
    a ^ ((1 : ℝ) / 2) * a ^ ((1 : ℝ) / 6) = a ^ ((2 : ℝ) / 3) := by
  rw [← Real.rpow_add ha]
  congr 1
  norm_num

theorem counterexample_log_slope :
    let sigma : ℝ := (1 : ℝ) / 2
    let kappa := fun x : ℝ => Real.exp (((1 : ℝ) / 6) * x)
    let p := fun x : ℝ => kappa x * Real.exp (sigma * x)
    ∀ x, p x = Real.exp (((2 : ℝ) / 3) * x) := by
  intro sigma kappa p x
  dsimp [p, kappa, sigma]
  rw [← Real.exp_add]
  congr 1
  ring

end
end FireProof.Identifiability
