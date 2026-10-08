import Mathlib

/-! # Lightweight dimensional audit -/

namespace FireProof.Units

@[ext] structure Dim where
  length : ℚ
  time : ℚ
  power : ℚ
  deriving DecidableEq, Repr

def mulDim (x y : Dim) : Dim := ⟨x.length + y.length, x.time + y.time, x.power + y.power⟩
def divDim (x y : Dim) : Dim := ⟨x.length - y.length, x.time - y.time, x.power - y.power⟩
def powDim (q : ℚ) (x : Dim) : Dim := ⟨q * x.length, q * x.time, q * x.power⟩

def lengthDim : Dim := ⟨1, 0, 0⟩
def timeDim : Dim := ⟨0, 1, 0⟩
def powerDim : Dim := ⟨0, 0, 1⟩
def areaDim : Dim := powDim 2 lengthDim
def perimeterDim : Dim := lengthDim
def velocityDim : Dim := divDim lengthDim timeDim
def areaRateDim : Dim := divDim areaDim timeDim

def betaDim (sigma : ℚ) : Dim := divDim areaRateDim (powDim sigma areaDim)
def perimeterCoefficientDim (sigma : ℚ) : Dim :=
  divDim perimeterDim (powDim sigma areaDim)

theorem beta_two_thirds : betaDim (2 / 3) = ⟨2 / 3, -1, 0⟩ := by
  ext <;> norm_num [betaDim, areaRateDim, areaDim, lengthDim, timeDim,
    divDim, powDim]

theorem k_two_thirds : perimeterCoefficientDim (2 / 3) = ⟨-1 / 3, 0, 0⟩ := by
  ext <;> norm_num [perimeterCoefficientDim, perimeterDim, areaDim,
    lengthDim, divDim, powDim]

theorem growth_law_dimensionally_consistent (sigma : ℚ) :
    mulDim (betaDim sigma) (powDim sigma areaDim) = areaRateDim := by
  ext <;> simp [mulDim, betaDim, divDim, powDim]

end FireProof.Units
