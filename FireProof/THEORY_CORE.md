# Authoritative Mathematical Core

This document is the smallest complete specification of the proposed reduced
fire-growth theory. It distinguishes the two-state generative model from the
geometric and kinematic factorization used to interpret it.

## 1. Domain and primitive quantities

**ASSUMPTION T0 (parameter domain).**

```text
Amax > A0 > 0,
beta0 > 0, alpha > 0, mu > 0,
A(t0)=A0, 0 < C(t0) <= 1.
```

`A` is cumulative burned area. `C` is the latent coherence state in the
two-state construction, not automatically the measured patch-connectivity
statistic or the active fraction. `Amax` is a prospectively defined reachable
area, not final realized burned area.

## 2. Irreducible generative model

**DEFINITION T1 (remaining fuel).**

```text
F(A) = (Amax-A)/(Amax-A0).
```

**DEFINITION T2 (closed matched forcing).** For `C+F>0`,

```text
H(C,F) = 2CF/(C+F),
G(C,F) = H(C,F)^2.
```

Set `G(0,0)=0` by continuous extension. The original matching variables are
not required to evaluate `G`.

**EMPIRICAL CLOSURE T3 (area growth).**

```text
A' = beta0 G(C,F(A)) A^(2/3).
```

**EMPIRICAL CLOSURE T4 (coherence dynamics).**

```text
C' = alpha C(1-C)F(A) - mu C.
```

Equations T1-T4, parameter values, and initial conditions are the complete
two-state generative model. Only `A` and `C` are dynamic states.

## 3. Equivalent matching representation

**DEFINITION T5 (ratio and matching index).** For `F>0`,

```text
r = C/F,
eta(r) = 4r/(1+r)^2.
```

**DERIVED IDENTITY T6 (canonical closure).** For `C,F>0`,

```text
C F eta(C/F)
  = 4C^2F^2/(C+F)^2
  = [2CF/(C+F)]^2
  = G(C,F).
```

Lean: `MechanismTests.matchedForcing_closed_form`.

Consequently T3 is exactly equivalent to

```text
A' = beta0 C F eta A^(2/3).
```

The `r,eta` representation is useful for interpreting mismatch. The `G`
representation is the canonical closed form because it removes a redundant
intermediate variable, extends naturally to the zero boundary, exposes
symmetry, and states the observable forcing surface directly.

## 4. What the closed form reveals

**DERIVED IDENTITY T7 (symmetry).**

```text
G(C,F) = G(F,C).
```

**DERIVED IDENTITY T8 (matched state).**

```text
G(s,s) = s^2.
```

**CONDITIONAL THEOREM T9 (limiting states).** For fixed positive state,

```text
C/F -> 0:  G(C,F) ~ 4C^2,
F/C -> 0:  G(C,F) ~ 4F^2.
```

Thus the smaller state controls the leading quadratic suppression, but the
instantaneous forcing alone cannot identify which state is smaller.

**CONDITIONAL THEOREM T10 (bounds).** For `C,F>0`,

```text
min(C,F)^2 <= G(C,F) <= C F <= max(C,F)^2,
G(C,F) <= 4 min(C,F)^2.
```

The middle bound follows from `eta<=1`; the outer bounds follow from the
harmonic-mean inequalities.

**CONDITIONAL THEOREM T11 (monotonicity and saturation).**

```text
partial G/partial C = 8 C F^3/(C+F)^3 > 0,
partial G/partial F = 8 F C^3/(C+F)^3 > 0.
```

For fixed `F`, `G -> 4F^2` as `C -> infinity`, and symmetrically for fixed
`C`. Therefore `eta` is maximized at `C=F`, but the complete forcing `G` is not:
it increases in either state and saturates as the other becomes abundant.
Lean verifies the first derivative in
`MechanismTests.closedForcing_hasDerivAt_C`.

## 5. Geometric origin of the exponent

These equations motivate T3 but are not additional dynamic states.

**EMPIRICAL CLOSURE G1 (shared-size geometry).**

```text
A = cA L^2,
P = cP L^(4/3),
cA,cP,L>0.
```

**DERIVED IDENTITY G2 (perimeter-area closure).**

```text
P = k A^(2/3),
k = cP/cA^(2/3).
```

Lean: `Scaling.four_thirds_direct_power_law`.

G1 is not required to integrate T3-T4. It supplies a proposed geometric reason
for the `2/3` factor and an independently testable mapped-perimeter prediction.

## 6. Kinematic and active-boundary factorization

**ASSUMPTION K1 (moving-boundary regularity).** The advancing set has a
rectifiable, oriented active boundary with integrable normal velocity; area is
differentiable almost everywhere; collisions use union geometry; and any
untracked recruitment is either absent or represented separately.

**DERIVED IDENTITY / NAMED AXIOM K2 (boundary transport).**

```text
A' = integral_Gamma_a v_n ds.
```

This is the sole custom scientific axiom in Lean:
`Kinematics.boundary_kinematic_identity`.

**DEFINITION K3 (coarse-grained speed).** For `Pa>0`,

```text
v_eff = (1/Pa) integral_Gamma_a v_n ds.
```

**DERIVED IDENTITY K3b (coarse-grained kinematics).** K2 and K3 give

```text
A' = v_eff Pa.
```

Defining `v_eff=A'/Pa` from the same area data would make this identity
circular and would not test boundary kinematics.

**EMPIRICAL CLOSURE K4 (active boundary).**

```text
Pa = k C A^(2/3).
```

**EMPIRICAL CLOSURE K5 (effective velocity).**

```text
v_eff = v0 F eta(C/F).
```

**DEFINITION K6 (combined coefficient).**

```text
beta0 = v0 k.
```

**DERIVED IDENTITY K7 (growth factorization).** K3-K6 imply T3:

```text
A' = beta0 C F eta A^(2/3)
   = beta0 G(C,F) A^(2/3).
```

Lean: `ActiveBoundary.active_boundary_substitution` and
`MechanismTests.matchedForcing_closed_form`.

K3-K6 are unnecessary for numerical generation once T3 is supplied, but they
are necessary for the proposed mechanistic interpretation and its separate
falsification tests.

## 7. Metabolic rate and transition surface

**DEFINITION L1 (model metabolic rate).**

```text
M = A'.
```

Within the two-state construction, `M` is an area-growth rate. Calling it
chemical metabolic power additionally requires an independently tested
energy-per-area closure.

**DERIVED IDENTITY L2 (relative acceleration).** For positive differentiable
states,

```text
M'/M = C'/C + F'/F + eta'/eta + (2/3)M/A.
```

**DERIVED IDENTITY L3 (matching derivative).**

```text
eta'/eta = [(F-C)/(F+C)] [C'/C-F'/F].
```

Lean: `Lifecycle.matching_relative_derivative`.

**DERIVED IDENTITY L4 (closed transition balance).** Let

```text
Psi(A,C) =
    [2F/(F+C)] [alpha(1-C)F-mu]
  - [2C/(F+C)] M/[(Amax-A0)F]
  + (2/3)M/A,

F = F(A),
M = beta0 G(C,F) A^(2/3).
```

Then

```text
M' = M Psi,
M'>0 iff Psi>0,
M'=0 iff Psi=0,
M'<0 iff Psi<0.
```

Lean: `Lifecycle.closed_peak_balance`, `peak_iff_balance_zero`, and
`acceleration_sign_is_balance_sign`.

`Psi=0` is a transition surface in `(A,C)` for fixed parameters. It is a peak
nullcline only in the sense of instantaneous metabolic acceleration; a local
maximum additionally requires a crossing from `Psi>0` to `Psi<0`.

## 8. Dimensionless canonical system

**DEFINITION D1.**

```text
x = A/Amax,
x0 = A0/Amax,
tau = alpha t,
f = (1-x)/(1-x0),
gamma = beta0/[alpha Amax^(1/3)],
delta = mu/alpha.
```

**DERIVED IDENTITY D2 (dimensionless dynamics).**

```text
dx/dtau = m = gamma G(C,f) x^(2/3),
dC/dtau = C[(1-C)f-delta].
```

The independent dimensionless controls are `gamma`, `delta`, and `x0`, plus
the initial state `C0`.

**DERIVED IDENTITY D3 (dimensionless transition surface).**

```text
Psi_d(x,C) =
    [2f/(f+C)] [(1-C)f-delta]
  - [2C/(f+C)] m/[(1-x0)f]
  + (2/3)m/x.
```

The signs of `dM/dtau` and `Psi_d` agree. Lean:
`Dimensionless.peakBalance_eq_transitionBalance`.

**CONDITIONAL THEOREM D4 (connectivity boundaries).**

```text
C increases iff (1-C)f > delta,
C is stationary iff (1-C)f = delta,
positive frozen-f equilibrium exists iff f > delta.
```

If `delta>=1`, connectivity cannot increase anywhere in the biological unit
square. Lean: `Dimensionless.connectivity_positive_iff` and related theorems.

## 9. Dependency graph

```text
G1 shared-size geometry
  -> G2 exponent and coefficient k
       -> K4 active-boundary closure

K1 regular moving boundary
  -> K2 transport identity -> K3 coarse-grained kinematics

T1 fuel definition -> F --------------------------+
T4 coherence ODE  -> C -----------------------+    |
T5 matching definition -> eta(C/F) -----------|----+
G2/K4 + K5 + K6 + K3 -> K7/T3 area-growth ODE
T3 + T4 + initial conditions -> trajectory (A,C)
T3 + T4 + T1 + T5 -> L4/D3 transition surface
```

## 10. Redundant quantities and equations

- `M` is an alias for `A'`, not an independent state.
- `F` is algebraically determined by `A` and prospectively defined `Amax`.
- `r` and `eta` can be eliminated in favor of `G(C,F)`.
- `P`, `Pa`, and `v_eff` are diagnostic or mechanistic outputs, not required to
  integrate the canonical two-state ODE.
- `L`, `cA`, and `cP` motivate the exponent but disappear after eliminating
  shared size.
- `A~t^3` and `P~t^2` are consequences of a constant-forcing special case, not
  defining equations of the lifecycle model.

Removing `C` would collapse the theory to an unconstrained time-varying rate
coefficient and remove the connectivity nullcline, transition surface, and
main mechanism-discrimination tests. Removing the separately named `F`, `r`,
`eta`, `M`, `Pa`, or `v_eff` from the state vector loses no generative content,
provided their definitions and observational roles remain documented.
