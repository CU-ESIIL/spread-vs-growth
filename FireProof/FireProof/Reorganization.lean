import FireProof.Assumptions

/-!
# Abstract spatial reorganization

This module deliberately does not formalize Wasserstein distance. It records
only the properties used by downstream theorems, so the same interface can be
instantiated by OT or by a simpler empirically validated spatial metric.
-/

namespace FireProof.Reorganization

universe u

structure SpatialDistance (Footprint : Type u) where
  distance : Footprint → Footprint → ℝ
  nonnegative : ∀ x y, 0 ≤ distance x y

structure SeparatingDistance (Footprint : Type u) extends SpatialDistance Footprint where
  zero_iff_equal : ∀ x y, distance x y = 0 ↔ x = y

def simpleGrowthNull {Footprint : Type u}
    (D : Footprint → ℝ → Footprint) (current : Footprint) (deltaArea : ℝ) : Footprint :=
  D current deltaArea

def reorganization {Footprint : Type u}
    (W : SpatialDistance Footprint) (actual nullFootprint : Footprint) : ℝ :=
  W.distance actual nullFootprint

theorem reorganization_nonnegative {Footprint : Type u}
    (W : SpatialDistance Footprint) (actual nullFootprint : Footprint) :
    0 ≤ reorganization W actual nullFootprint := by
  exact W.nonnegative actual nullFootprint

theorem reorganization_zero_iff {Footprint : Type u}
    (W : SeparatingDistance Footprint) (actual nullFootprint : Footprint) :
    reorganization W.toSpatialDistance actual nullFootprint = 0 ↔
      actual = nullFootprint := by
  exact W.zero_iff_equal actual nullFootprint

end FireProof.Reorganization
