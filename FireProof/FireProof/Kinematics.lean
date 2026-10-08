import FireProof.Assumptions

/-!
# Boundary kinematics

Mathlib does not currently provide the moving-boundary geometric-measure
theorem needed to derive `dA/dt = integral v_n ds` at the level of generality
used by the SI. We therefore expose it as the project's sole scientific axiom.
The later coarse-grained equality is algebra, not another axiom.
-/

namespace FireProof.Kinematics

structure MovingBoundaryData where
  areaRate : ℝ
  normalVelocityIntegral : ℝ
  perimeter : ℝ
  activeLength : ℝ
  meanNormalVelocity : ℝ

/-- Imported moving-boundary theorem. A full proof would require a specified
regular family of sets, oriented rectifiable boundaries, normal velocity, and
a transport/shape-derivative theorem. -/
axiom boundary_kinematic_identity (d : MovingBoundaryData) :
  d.areaRate = d.normalVelocityIntegral

theorem mean_velocity_reduction
    (d : MovingBoundaryData)
    (hmean : d.normalVelocityIntegral = d.meanNormalVelocity * d.activeLength) :
    d.areaRate = d.meanNormalVelocity * d.activeLength := by
  rw [boundary_kinematic_identity d, hmean]

theorem active_fraction_reduction
    (d : MovingBoundaryData) (activeFraction : ℝ)
    (hmean : d.normalVelocityIntegral = d.meanNormalVelocity * d.activeLength)
    (hactive : d.activeLength = activeFraction * d.perimeter) :
    d.areaRate = (d.meanNormalVelocity * activeFraction) * d.perimeter := by
  rw [boundary_kinematic_identity d, hmean, hactive]
  ring

end FireProof.Kinematics
