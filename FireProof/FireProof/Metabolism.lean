import FireProof.Assumptions

/-! # Relative-derivative decompositions -/

namespace FireProof.Metabolism

noncomputable section

theorem rpow_relative_derivative
    {A : ℝ → ℝ} {t A' p : ℝ}
    (hA : HasDerivAt A A' t) (hpos : 0 < A t) :
    let q := fun u => A u ^ p
    ∃ q', HasDerivAt q q' t ∧ q' / q t = p * A' / A t := by
  let q := fun u => A u ^ p
  let q' := A' * p * A t ^ (p - 1)
  refine ⟨q', ?_, ?_⟩
  · exact hA.rpow_const (Or.inl (ne_of_gt hpos))
  · dsimp [q, q']
    rw [Real.rpow_sub hpos, Real.rpow_one]
    have hq : A t ^ p ≠ 0 := ne_of_gt (Real.rpow_pos_of_pos hpos p)
    field_simp
    ring

theorem metabolic_relative_derivative
    {C F eta A : ℝ → ℝ} {t C' F' eta' A' beta0 : ℝ}
    (hC : HasDerivAt C C' t) (hF : HasDerivAt F F' t)
    (hEta : HasDerivAt eta eta' t) (hA : HasDerivAt A A' t)
    (hCpos : 0 < C t) (hFpos : 0 < F t) (hEtapos : 0 < eta t)
    (hApos : 0 < A t) (hBeta : beta0 ≠ 0) :
    let M := fun u => beta0 * C u * F u * eta u * A u ^ ((2 : ℝ) / 3)
    ∃ M', HasDerivAt M M' t ∧
      M' / M t = C' / C t + F' / F t + eta' / eta t +
        ((2 : ℝ) / 3) * A' / A t := by
  let q := fun u => A u ^ ((2 : ℝ) / 3)
  obtain ⟨q', hq, hqrel⟩ :=
    rpow_relative_derivative (p := (2 : ℝ) / 3) hA hApos
  let M := fun u => beta0 * C u * F u * eta u * q u
  let M' := beta0 *
    (C' * F t * eta t * q t + C t * F' * eta t * q t +
      C t * F t * eta' * q t + C t * F t * eta t * q')
  refine ⟨M', ?_, ?_⟩
  · dsimp [M, M']
    convert (((hC.const_mul beta0).mul hF).mul hEta).mul hq using 1 <;> ring
  · dsimp [M, M']
    have hqpos : 0 < q t := Real.rpow_pos_of_pos hApos _
    have hqne : q t ≠ 0 := ne_of_gt hqpos
    calc
      beta0 * (C' * F t * eta t * q t + C t * F' * eta t * q t +
          C t * F t * eta' * q t + C t * F t * eta t * q') /
          (beta0 * C t * F t * eta t * q t) =
          C' / C t + F' / F t + eta' / eta t + q' / q t := by
            field_simp [ne_of_gt hCpos, ne_of_gt hFpos, ne_of_gt hEtapos,
              hqne, hBeta]
            ring
      _ = C' / C t + F' / F t + eta' / eta t +
          (2 / 3) * A' / A t := by rw [hqrel]

theorem active_perimeter_relative_derivative
    {C A : ℝ → ℝ} {t C' A' k : ℝ}
    (hC : HasDerivAt C C' t) (hA : HasDerivAt A A' t)
    (hCpos : 0 < C t) (hApos : 0 < A t) (hk : k ≠ 0) :
    let Pa := fun u => k * C u * A u ^ ((2 : ℝ) / 3)
    ∃ Pa', HasDerivAt Pa Pa' t ∧
      Pa' / Pa t = C' / C t + ((2 : ℝ) / 3) * A' / A t := by
  let q := fun u => A u ^ ((2 : ℝ) / 3)
  obtain ⟨q', hq, hqrel⟩ :=
    rpow_relative_derivative (p := (2 : ℝ) / 3) hA hApos
  let Pa := fun u => k * C u * q u
  let Pa' := k * (C' * q t + C t * q')
  refine ⟨Pa', ?_, ?_⟩
  · dsimp [Pa, Pa']
    convert (hC.const_mul k).mul hq using 1 <;> ring
  · dsimp [Pa, Pa']
    have hqne : q t ≠ 0 := ne_of_gt (Real.rpow_pos_of_pos hApos _)
    calc
      k * (C' * q t + C t * q') / (k * C t * q t) =
          C' / C t + q' / q t := by
            field_simp [ne_of_gt hCpos, hqne, hk]
            ring
      _ = C' / C t + (2 / 3) * A' / A t := by rw [hqrel]

end
end FireProof.Metabolism
