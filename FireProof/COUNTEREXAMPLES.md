# Counterexamples And Assumption Stress Tests

## A two-thirds observed slope does not identify a two-thirds fixed exponent

Lean theorem: `FireProof.Identifiability.half_plus_one_sixth_counterexample`.

For positive area,

```text
a^(1/2) * a^(1/6) = a^(2/3).
```

Thus a model with fixed `sigma = 1/2` and `kappa(a) proportional to a^(1/6)` has observed trajectory slope `2/3`. The SI's warning is correct: the slope alone does not identify the underlying exponent or mechanism.

## Zero rate at a ceiling does not establish no crossing

Lean example: `FireProof.Fuel` contains the differentiable path `x(t)=t^3`, with `x(0)=0`, `x'(0)=0`, and `x(1)>0`.

This is not offered as a solution of the manuscript ODE. It breaks the inference rule “derivative zero at one boundary point, therefore no crossing.” A valid ODE barrier result additionally needs continuity and forward uniqueness (or an equivalent explicit barrier theorem).

## Boundary signs do not by themselves prove `[0,1]` invariance

Lean proves

```text
f(0) = 0
f(1) = -mu <= 0
```

for the connectivity vector field when `mu >= 0`. The conditional theorem `unit_interval_invariant_with_barrier_assumptions` also compiles, but it requires intermediate-value and uniqueness/barrier premises. The manuscript's boundary calculation is a useful diagnostic, not a complete invariance proof.

## A positive coherence equilibrium can disappear

Lean proves that

```text
C* = 1 - mu/(alpha F) > 0  iff  mu < alpha F
```

when `alpha>0` and `F>0`. At or below threshold (`alpha F <= mu`), the candidate nonzero equilibrium is nonpositive and therefore not biologically admissible.

## The cube-root cancellation is conditional but exact

Lean proves the cancellation only with `A>0`, differentiability, and the exact growth closure. Removing positivity makes the fractional-power derivative problematic at zero; allowing a source term or time-varying exponent introduces extra terms. Within the stated closure, however, the cancellation is exact rather than asymptotic.

## The matching maximum does not select wildfire geometry

Lean proves only that the chosen algebraic function `eta(r)=4r/(1+r)^2` has a unique global maximum at `r=1` for `r>0`. No theorem maps a wildfire boundary dimension to `r`, and no theorem says a fire optimizes `eta`. Any such statement remains empirical or requires a separately justified objective and mapping.

## Dimensional validity does not imply mechanism

The units layer proves that `beta A^sigma` has area/time units when `beta` has dimension `L^(2-2sigma) T^-1`, and that `k` has dimension `L^(1-2sigma)`. This blocks dimensionally invalid formulas, but dimensional consistency alone cannot derive a physical law.
