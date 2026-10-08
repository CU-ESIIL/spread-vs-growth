import FireProof.Scaling
import FireProof.Growth
import FireProof.Kinematics
import FireProof.ActiveBoundary
import FireProof.Fuel
import FireProof.Matching
import FireProof.Connectivity
import FireProof.Metabolism
import FireProof.Identifiability
import FireProof.Units

/-! # Machine-readable claim-status vocabulary -/

namespace FireProof.Audit

inductive Status where
  | proved
  | provedWithAdditionalAssumptions
  | definition
  | assumedAxiomatized
  | empirical
  | notProved
  | falseAsStated
  deriving Repr, DecidableEq

structure Claim where
  siClaim : String
  leanTheorem : String
  status : Status
  assumptions : String
  proofType : String
  scientificInterpretation : String
  deriving Repr

def coreClaims : List Claim := [
  ⟨"S15 shared-size exponent elimination", "Scaling.eliminate_direct_power_laws",
    .proved, "positive coefficients and shared size; DA nonzero", "algebra",
    "Does not establish that wildfire satisfies either scaling law."⟩,
  ⟨"S21 moving-boundary identity", "Kinematics.boundary_kinematic_identity",
    .assumedAxiomatized, "regular moving set and transport theorem", "named axiom",
    "Not disguised as a Lean-derived geometric-measure theorem."⟩,
  ⟨"S51 matching maximum", "Matching.eta_unique_global_max",
    .proved, "r > 0", "algebra",
    "The chosen function peaks at one; fire need not optimize it."⟩,
  ⟨"S58 fuel fraction bounds", "Fuel.remaining_mem_unit",
    .proved, "A0 < Amax and A in [A0,Amax]", "order algebra",
    "The interval for A is a premise, not yet a dynamical consequence."⟩,
  ⟨"S58 area cannot cross Amax", "Fuel.cannot_cross_with_explicit_barrier_assumptions",
    .provedWithAdditionalAssumptions,
    "intermediate-value crossing plus uniqueness/barrier property", "analysis",
    "Zero rate at Amax alone is insufficient."⟩,
  ⟨"S58 connectivity interval is invariant", "Connectivity.boundary_signs",
    .notProved, "ODE existence and uniqueness are absent", "boundary check only",
    "Boundary signs are necessary diagnostics, not an invariance theorem."⟩,
  ⟨"Observed two-thirds slope identifies sigma", "Identifiability.half_plus_one_sixth_counterexample",
    .falseAsStated, "counterexample uses drifting kappa", "formal counterexample",
    "A two-thirds trajectory slope does not identify a fixed geometric exponent."⟩,
  ⟨"The equations guarantee an initial acceleration phase", "Lifecycle.acceleration_sign_is_balance_sign",
    .falseAsStated, "the exact balance may have either sign", "sign theorem and numerical counterexample",
    "A rise-peak-decline sequence occupies only part of parameter space."⟩,
  ⟨"Metabolic peak condition", "Lifecycle.closed_peak_balance",
    .provedWithAdditionalAssumptions, "positive differentiable states and matching closure", "calculus and algebra",
    "The balance characterizes a peak but does not guarantee one exists."⟩,
  ⟨"Four latent growth factors are separately identified by area", "MechanismTests.area_only_product_rescaling",
    .falseAsStated, "none; explicit rescaling leaves the observable unchanged", "formal invariance",
    "Area identifies a product, not beta0, C, F, and eta separately."⟩,
  ⟨"The three headline power laws are independent", "MechanismTests.cubic_quadratic_headlines_are_dependent",
    .falseAsStated, "exact cubic and quadratic parameterization", "formal algebraic dependence",
    "The perimeter-time exponent follows from the other two exponents."⟩,
  ⟨"Matching equality maximizes total closed forcing", "MechanismTests.closedForcing_hasDerivAt_C",
    .falseAsStated, "positive C and F", "formal partial derivative",
    "Matching efficiency peaks at equality, but total forcing increases in either state."⟩,
  ⟨"Closed peak condition needs an independent eta derivative", "Dimensionless.peakBalance_eq_transitionBalance",
    .provedWithAdditionalAssumptions, "exact matching, fuel, and coherence closures", "algebraic reduction",
    "The dimensionless transition surface depends only on x, C, and parameters."⟩
]

end FireProof.Audit
