import FireProof.Assumptions

/-! # Transport-matching algebra -/

namespace FireProof.Matching

noncomputable section

def eta (r : ℝ) : ℝ := 4 * r / (1 + r) ^ 2

theorem one_sub_eta {r : ℝ} (h : r ≠ -1) :
    1 - eta r = ((1 - r) / (1 + r)) ^ 2 := by
  have hden : 1 + r ≠ 0 := by
    intro hzero
    apply h
    linarith
  unfold eta
  field_simp [hden]
  ring

theorem eta_pos {r : ℝ} (hr : 0 < r) : 0 < eta r := by
  unfold eta
  positivity

theorem eta_le_one {r : ℝ} (hr : 0 < r) : eta r ≤ 1 := by
  have hne : r ≠ -1 := by linarith
  rw [← sub_nonneg]
  rw [one_sub_eta hne]
  positivity

theorem eta_eq_one_iff {r : ℝ} (hr : 0 < r) : eta r = 1 ↔ r = 1 := by
  constructor
  · intro h
    have hne : r ≠ -1 := by linarith
    have hz : ((1 - r) / (1 + r)) ^ 2 = 0 := by
      rw [← one_sub_eta hne, h]
      norm_num
    have hfrac : (1 - r) / (1 + r) = 0 := sq_eq_zero_iff.mp hz
    have hden : 1 + r ≠ 0 := by linarith
    have hnum : 1 - r = 0 := (div_eq_zero_iff.mp hfrac).resolve_right hden
    linarith
  · rintro rfl
    norm_num [eta]

theorem eta_unique_global_max {r : ℝ} (hr : 0 < r) :
    eta r ≤ eta 1 ∧ (eta r = eta 1 ↔ r = 1) := by
  have hOne : eta 1 = 1 := by norm_num [eta]
  constructor
  · rw [hOne]
    exact eta_le_one hr
  · rw [hOne]
    exact eta_eq_one_iff hr

end
end FireProof.Matching
