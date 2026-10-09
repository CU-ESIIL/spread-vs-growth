# Half-Power Normalization Formal Audit

## Verdict

**NORMALIZATION ASSUMPTION MUST BE MADE EXPLICIT.**

The existing Lean proofs are algebraically sound. They do not discard the
normalization: `Scaling.eliminate_direct_power_laws` and
`Scaling.four_thirds_direct_power_law` retain the coefficient

\[
k=\frac{c_P}{c_A^{D_h/D_A}},
\qquad
k_{2/3}=\frac{c_P}{c_A^{2/3}}.
\]

The gap is one level above the algebra. The theorems are pointwise statements
with scalar parameters. A coefficient is fixed during one theorem invocation,
but no existing `ScalingLaw` object quantifies over a domain and requires the
same coefficient across areas, times, fires, or candidate exponents. Reusing a
pointwise theorem with different coefficients is legal. Consequently, the
formal theorem alone does not establish a universal, population, within-fire,
or origin-anchored scaling law.

The required correction is interpretive and structural, not a repair to an
invalid proof. The minimal additive formal checks are isolated in
`FireProof.Normalization`; the original theory modules and theorem statements
remain unchanged.

## What the existing theory means

FireProof represents a positive power-law observation through premises such as

```text
A = cA * L ^ DA
P = cP * L ^ Dh
```

and proves the consequence

```text
P = (cP / cA ^ (Dh / DA)) * A ^ (Dh / DA).
```

This says: for the values supplied to this theorem, elimination of one shared
positive size `L` preserves both the exponent and normalization. It does not
say `exists c, forall A in domain, P A = c * A^sigma`, because `A`, `P`, `cA`,
and `cP` are scalar theorem arguments rather than functions over a domain.

Thus current FireProof implements an exact **pointwise conditional identity**.
A fixed-normalization scaling law over a trajectory follows only after adding
the external premise that the same `cA` and `cP`, or at least their relevant
ratio, applies throughout that trajectory.

## Four distinct hypotheses

### H1. Common-normalization scaling law

For a specified domain `D`, one coefficient and one exponent satisfy

\[
\exists c>0,\ \forall A\in D,\quad P(A)=cA^\sigma.
\]

Both `c` and `sigma` are fixed over `D`. A population law additionally requires
the same `c` for every evaluated fire. This is not currently represented by a
dedicated Lean structure or predicate.

### H2. Fire-specific normalization

For every fire `i`, there is a coefficient fixed within that fire:

\[
\forall i,\ \exists c_i>0,\ \forall A\in D_i,\quad P_i(A)=c_iA^\sigma.
\]

This predicts parallel log-log trajectories with slope `sigma`; intercepts may
differ among fires. Existing pointwise scaling theorems are compatible with
this hypothesis but do not enforce the within-fire constancy of `c_i`.

### H3. Variable normalization

\[
P(t)=c(t)A(t)^\sigma.
\]

With unrestricted `c(t)`, every positive trajectory has this representation
for every exponent by defining `c(t)=P(t)/A(t)^sigma`. The representation is
then algebraically true but exponent-nonidentifying. The existing
`Identifiability.local_log_slope` theorem already exposes the derivative term
from a changing coefficient, but the main scaling API does not name this as a
separate hypothesis class.

### H4. Origin-anchored extrapolation

Given one positive observed point `(A0,P0)`, define

\[
P_\sigma(A)=P_0(A/A_0)^\sigma,
\qquad
c_{\sigma,0}=P_0/A_0^\sigma.
\]

The normalization depends explicitly on the candidate exponent. In general,
`c_(1/2),0 != c_(2/3),0`, even though both curves pass through `(A0,P0)`.
Agreement at the anchor is therefore not evidence that either candidate is a
common-normalization law.

## Formal object inventory

| Lean object | Source | Mathematical statement | Normalization status | Indexing/anchoring | Geometry or dynamics | Audit |
|---|---|---|---|---|---|---|
| `Scaling.eliminate_shared_log_size` | `FireProof/Scaling.lean` | eliminates `log L` and retains an additive intercept | `cA,cP` explicit and scalar | no fire/time/domain index | geometry | SAFE WITH EXPLICIT ASSUMPTION: a law requires stable coefficients over its domain |
| `Scaling.four_thirds_implies_two_thirds` | same | `DA=2,Dh=4/3` gives log slope `2/3` | intercept is `log cP-(2/3)log cA` | pointwise | geometry | SAFE WITH EXPLICIT ASSUMPTION |
| `Scaling.eliminatedCoefficient` | same | `exp(log cP-(Dh/DA)log cA)` | explicitly defined | pointwise | geometry | SAFE |
| `Scaling.eliminatedCoefficient_eq_div_rpow` | same | coefficient equals `cP/cA^(Dh/DA)` | explicit | pointwise | geometry | SAFE |
| `Scaling.eliminate_shared_positive` | same | positive log laws imply a direct power law | explicit coefficient | pointwise | geometry | SAFE WITH EXPLICIT ASSUMPTION |
| `Scaling.four_thirds_power_law` | same | direct `2/3` consequence in positive variables | coefficient preserved | pointwise | geometry | SAFE WITH EXPLICIT ASSUMPTION |
| `Scaling.eliminate_direct_power_laws` | same | eliminates a shared positive `L` | explicit `cP/cA^(Dh/DA)` | pointwise | geometry | SAFE WITH EXPLICIT ASSUMPTION |
| `Scaling.four_thirds_direct_power_law` | same | `P=(cP/cA^(2/3))A^(2/3)` | explicit | pointwise | geometry | SAFE WITH EXPLICIT ASSUMPTION |
| `Identifiability.local_log_slope` | `FireProof/Identifiability.lean` | observed log slope equals exponent plus coefficient and exponent drift | `kappa(x)` may vary | area/log-area indexed | geometry/identifiability | SAFE; directly warns against exponent-only interpretation |
| `Identifiability.half_plus_one_sixth_counterexample` | same | `A^(1/2)A^(1/6)=A^(2/3)` | variable factor supplies missing `1/6` | area dependent | geometry | SAFE; normalization variation is the point |
| `Identifiability.counterexample_log_slope` | same | varying `kappa` with nominal `1/2` yields observed `2/3` | explicitly variable | log-area indexed | geometry | SAFE |
| `Growth.transformed_derivative` | `FireProof/Growth.lean` | if `A'=beta A^sigma`, transformed area has derivative `(1-sigma)beta` | temporal coefficient `beta` fixed at the point | no perimeter normalization | dynamics | SAFE; category F, not geometric scaling |
| `Growth.constant_beta_solution_on_interval` | same | transformed area is affine under constant `beta` | `beta` fixed over interval | time interval | dynamics | SAFE WITH EXPLICIT ASSUMPTION |
| `Growth.two_thirds_transformed_solution` | same | cube-root area is affine under a `2/3` temporal growth law | constant `beta` | time interval | dynamics | SAFE; not a perimeter theorem |
| `Growth.shifted_quadratic_ratio_limit` | same | `k(x0+bt)^2/t^2 -> kb^2` | scalar `k` fixed | time asymptotic | dynamics | SAFE WITH EXPLICIT ASSUMPTION |
| `ActiveBoundary.active_boundary_substitution` | `FireProof/ActiveBoundary.lean` | `Pa=k C A^(2/3)` and velocity closure imply area-rate closure | scalar `k`; `C` can vary | no mapped-perimeter law | dynamics/active geometry | SAFE; the effective normalization `kC` is state varying |
| `ActiveBoundary.cube_root_removes_explicit_area` | same | exact `2/3` temporal growth removes explicit area in cube-root state | composite forcing may vary by point | time indexed | dynamics | SAFE |
| `Metabolism.active_perimeter_relative_derivative` | `FireProof/Metabolism.lean` | slope of `Pa=k C A^(2/3)` includes `C'/C` | `k` fixed; `C(t)` variable | time indexed through `C,A` | active-boundary dynamics | SAFE; explicitly does not imply local slope exactly `2/3` |
| `Metabolism.metabolic_relative_derivative` | same | growth-rate slope includes derivatives of `C,F,eta` plus `2/3` | `beta0` fixed, state factors variable | time indexed | dynamics | SAFE |
| `MechanismTests.area_perimeter_joint_rescaling` | `FireProof/MechanismTests.lean` | latent rescaling leaves area/perimeter products invariant | `k` and latent `C` confounded | parameter rescaling | identifiability | SAFE |
| `MechanismTests.cubic_quadratic_headlines_are_dependent` | same | exact time powers imply one perimeter-area polynomial relation | fixed scalar `k` | no fitted intercept | dynamics/geometry | SAFE |
| `Attractor.restores` and related theorems | `FireProof/Attractor.lean` | generic contraction toward `sigmaStar` under an assumed update | normalization absent | generic slope state | dynamics | SAFE; does not select `1/2` or `2/3` |
| `Attractor.attraction_math_does_not_select_two_thirds` | same | restates that attraction algebra is generic in `sigmaStar` | irrelevant | generic target | dynamics | SAFE |
| `Units.perimeterCoefficientDim` | `FireProof/Units.lean` | units of coefficient depend on exponent | normalization explicit dimensionally | no indexing | units | SAFE; also means coefficients at different exponents are not the same physical quantity |
| `Units.k_two_thirds` | same | `k` at `2/3` has length dimension `-1/3` | explicit | no indexing | units | SAFE |

## Audit of every formal use of one-half

| Lean object | Meaning of `1/2` | Normalization assumption | Dynamical claim? | Mechanistic claim? | Status |
|---|---|---|---:|---:|---|
| `Identifiability.half_plus_one_sixth_counterexample` | reference geometric exponent in a factorization | area-dependent factor allowed | no | no | SAFE |
| `Identifiability.counterexample_log_slope` | nominal exponent whose variable coefficient produces slope `2/3` | `kappa` deliberately varies | no | no | SAFE |
| `Scaling` with `DA=2,Dh=1` | not previously specialized by name | would require `cP/cA^(1/2)` fixed for a law | no | geometric similarity only | MISSING SPECIALIZATION; added in `Normalization.euclidean_one_half_elimination` |
| `Growth` instantiated with `sigma=1/2` | temporal area-growth exponent | constant or fitted temporal `beta` according to theorem use | yes | no diffusion theorem | SAFE if labeled category F |
| `Attractor` instantiated with `sigmaStar=1/2` | local-slope shrinkage target | not a perimeter intercept | yes | no | SAFE if labeled category E |

No Lean theorem proves `one-half exponent -> diffusion`. FireProof contains no
formal diffusion process, heat equation, Brownian model, or stochastic front
whose solution is identified by the perimeter-area exponent. Calling `1/2`
“diffusion-like” is therefore interpretive shorthand, not a formal result.

## Geometric derivations and normalization

For the proposed rough-boundary construction,

\[
A=c_A L^2,\qquad P=c_P L^{4/3}
\]

implies

\[
P=\frac{c_P}{c_A^{2/3}}A^{2/3}.
\]

FireProof preserves this coefficient exactly. The theorem does not state
whether `cA` or `cP` is universal, fire-specific, or state-specific. If both
are constant during one fire's growth, their ratio is constant and the pure
within-fire slope is `2/3`. If their ratio changes with area, the effective
normalization changes and the observed slope need not be `2/3`.

The Euclidean-similarity construction,

\[
A=c_A L^2,\qquad P=c_P L,
\]

similarly implies

\[
P=\frac{c_P}{c_A^{1/2}}A^{1/2}.
\]

This is a geometric similarity statement. Variation in the coefficient among
fires is compatible with fire-specific similarity; arbitrary variation through
time removes exponent identification. Neither version implies diffusion.

## Variable k and the empirical 0.59 slope

If

\[
P(A)=k(A)A^{2/3},
\]

then

\[
\log P=\log k(A)+\frac23\log A
\]

and, where positive differentiable quantities permit,

\[
\frac{d\log P}{d\log A}=\frac23+
\frac{d\log k}{d\log A}.
\]

This is already represented structurally by
`Identifiability.local_log_slope`. A within-fire slope near `0.595` is
consistent with a two-thirds algebraic factor only if `k` declines
systematically with area at roughly `-0.072` on the log-log scale. That is a
new empirical requirement, not a formal rescue: with unrestricted `k(A)`, the
representation is tautological.

The active-boundary closure is even more explicit:

\[
P_a=kC(t)A^{2/3}.
\]

Here `k` is scalar but the effective normalization `kC(t)` is designed to
vary. `Metabolism.active_perimeter_relative_derivative` proves that the active
perimeter's local slope contains the additional `C'/C` term. Therefore this
closure does not imply that mapped cumulative perimeter has a local or
longitudinal slope exactly equal to `2/3`.

## Within-fire and between-fire implications

The current theory does not by itself choose either empirical estimand.

- **Within-fire `2/3`:** follows from the shared-size construction only when
  `cP/cA^(2/3)` is constant during the fire and the measured perimeter is the
  theoretical perimeter. It does not follow for the active closure when `C`
  varies, nor for cumulative mapped perimeter without a mapping theorem.
- **Between-fire `2/3`:** requires a cross-fire restriction on coefficient
  variation. Fire-specific `k_i` that correlates with characteristic fire area
  can change the between-fire slope. No current theorem imposes independence,
  equality, or a hierarchical distribution for `k_i`.
- **Population `2/3`:** requires still stronger common-normalization or
  coefficient-distribution assumptions. It is not a consequence of the
  pointwise elimination theorem.
- **Local `2/3` attractor:** is not implied. `FireProof.Attractor` is generic in
  `sigmaStar`, and explicitly states that attraction mathematics does not
  select two-thirds.

## Claims reconciliation

| Claim | Formal status | Required normalization assumption | Empirical test |
|---|---|---|---|
| `P proportional to A^(2/3)` | conditional pointwise theorem | fixed `cP/cA^(2/3)` over the stated domain | development-locked coefficient and held-out residual/drift test |
| Individual fires grow geometrically at `2/3` | not implied unconditionally | constant fire-specific `k_i`; correct perimeter object | within-fire centered slope and normalization drift |
| Fires share a common `2/3` normalization | not formalized | one common `k` across fires | population-locked intercept test |
| Fires may have different constant `k_i` but common `2/3` slope | mathematically coherent, not encoded as a structure | `k_i` fixed within each fire | fire-specific intercept model plus within-fire slope |
| Local slopes should equal `2/3` | not implied by active closure | all coefficient/state derivatives vanish | rolling-slope estimates with uncertainty |
| Local slopes should return to `2/3` | not implied | independent dynamical restoration closure | held-out attractor test; current result does not support a special `2/3` attractor |
| `P proportional to A^(1/2)` | Euclidean elimination is conditional | fixed `cP/cA^(1/2)` over domain | common and fire-specific normalization tests |
| `1/2` implies Euclidean similarity | converse is not proved | shared size and stable shape coefficients are needed | shape/coefficient measurements beyond exponent alone |
| `1/2` implies diffusion | not proved; no formal diffusion model exists | would require an independent mechanistic theorem | diffusion/front model with process-specific observations |
| Anchored `1/2` prediction supports a `1/2` scaling law | false implication | anchoring changes normalization with exponent | compare population-locked, fire-specific, and anchored tests separately |

## Fair comparison of one-half and two-thirds

FireProof previously had no theorem comparing fitted `1/2` and `2/3`
perimeter laws. Its generic scaling theorem accepts whatever `cA,cP,DA,Dh`
are supplied. Therefore it represented none of these statistical choices by
default: same numerical coefficient, separately fitted coefficients,
common-origin anchoring, or independently theory-derived coefficients.

The new isolated normalization module makes common-origin anchoring explicit.
It proves that the candidate-specific coefficients differ in general, that all
candidate exponents hit the same anchor, and that subsequent candidate
separation depends only on area expansion and exponent difference.

## Theorem checks

The additive `FireProof.Normalization` module verifies:

1. `anchoredPrediction_at_origin`: every candidate exponent fits one positive
   anchor exactly.
2. `anchored_candidate_ratio`: two anchored candidates differ by
   `(A/A0)^(sigma2-sigma1)`.
3. `half_two_thirds_anchored_ratio`: the exact specialization is
   `(A/A0)^(1/6)`.
4. `fire_specific_constant_log_slope`: a constant fire coefficient cancels
   from log differences and leaves slope `sigma`.
5. `variable_normalization_reconstructs`: unrestricted normalization
   reconstructs any positive-area observation for every exponent.
6. `geometric_two_thirds_elimination`: the coefficient is explicitly
   `cP/cA^(2/3)`.
7. `euclidean_one_half_elimination`: the coefficient is explicitly
   `cP/cA^(1/2)`.

`anchored_ratio_at_no_expansion` supplies the exact low-leverage statement:
at area ratio one, the candidate ratio is one. The general ratio theorem is
the formal priority; no unnecessary limit machinery is introduced.

## Proposed minimal hierarchy

A future API may define, without replacing the current algebra:

- `ScalingLaw`: one exponent and one coefficient fixed on a stated domain;
- `FireScalingLaw`: shared exponent and coefficient indexed by fire but fixed
  over each fire's domain;
- `AnchoredScalingPrediction`: exponent plus observed `(A0,P0)`;
- `VariableNormalizationRepresentation`: exponent plus unrestricted `k(A)`.

The implication direction is one-way. A common law can be specialized to each
fire. A fire law can be evaluated at an origin. Neither an anchored prediction
nor an unrestricted variable-normalization representation implies a common
law. A large refactor is not needed for the present audit.

## Direct answers

1. **Does current Lean distinguish exponent from normalization?** Algebraically
   yes; as domain-level hypothesis classes, no.
2. **Is `k` fixed, fire-specific, or variable?** It is scalar and fixed within
   one theorem invocation. Its constancy across observations, fires, or times
   was not encoded. In the active-perimeter closure, effective normalization
   `kC(t)` explicitly varies.
3. **Does the `2/3` derivation require constant `k`?** The pointwise identity
   does not. Interpreting it as one scaling law over growth does.
4. **Does the `1/2` comparator use the same assumptions?** No formal geometric
   comparator previously specified them. Temporal and attractor uses of `1/2`
   are different hypotheses.
5. **Can any exponent fit one point after intercept adjustment?** Yes, exactly.
6. **Does anchoring reduce short-interval discrimination?** Yes. The exact
   ratio is `(A/A0)^(sigma2-sigma1)`, equal to one at no expansion.
7. **Does the formal theory imply within-fire `2/3`?** Only under an additional
   constant-normalization and measurement-object assumption.
8. **Does it imply between-fire `2/3`?** No; cross-fire coefficient behavior is
   unconstrained.
9. **Does it imply a local `2/3` attractor?** No.
10. **Are some empirical/manuscript phrasings stronger?** Yes whenever they
    turn a pointwise conditional theorem, an anchored forecast, or a local
    slope target into evidence for a universal law or diffusion mechanism.
11. **Minimal formal change?** Keep all core proofs; add explicit normalization
    and anchoring lemmas, and require every empirical claim to name its
    coefficient domain and indexing.

