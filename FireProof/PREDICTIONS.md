# Second-Stage Prediction Audit

Labels in this report are literal: **THEOREM**, **CONDITIONAL THEOREM**,
**COUNTEREXAMPLE**, **NUMERICAL RESULT**, **MODEL PREDICTION**, and
**EMPIRICAL HYPOTHESIS** are not interchangeable.

## Exact closed system

Let

```text
M = A' = beta0 C F eta A^(2/3)
F = (Amax-A)/(Amax-A0)
C' = alpha C(1-C)F - mu C
r = C/F
eta(r) = 4r/(1+r)^2.
```

**THEOREM.** For positive `C` and `F`,

```text
C F eta(C/F) = 4 C^2 F^2/(C+F)^2 = [2CF/(C+F)]^2.
```

Thus the full growth closure is more restrictive than an arbitrary product of
four latent factors:

```text
M/A^(2/3) = beta0 [2CF/(C+F)]^2.
```

Lean: `MechanismTests.matchedForcing_closed_form`.

## Exact peak condition

Define

```text
B = C'/C + F'/F + eta'/eta + (2/3)M/A.
```

**THEOREM.** Whenever `M>0`,

```text
M' = M B,
M'=0 iff B=0,
sign(M') = sign(B).
```

Lean: `Lifecycle.peak_iff_balance_zero` and
`Lifecycle.acceleration_sign_is_balance_sign`.

For the matching function,

```text
eta'/eta = [(F-C)/(F+C)] [C'/C-F'/F].
```

Therefore the peak condition reduces exactly to

```text
0 = [2F/(F+C)] [alpha(1-C)F-mu]
    - [2C/(F+C)] M/[(Amax-A0)F]
    + (2/3)M/A.
```

**THEOREM.** This is algebraically equivalent to the original logarithmic
balance under positive, differentiable states. Lean:
`Lifecycle.closed_peak_balance`.

## Does the system guarantee a life cycle?

| Narrative claim | Status | Finding |
| --- | --- | --- |
| Initial acceleration | **COUNTEREXAMPLE** | The balance can be negative at the initial state. The numerical sweep includes monotone decline from `tau=0`. |
| At least one interior maximum | **CONDITIONAL THEOREM** | It follows if `M` is continuous, initially increasing, remains positive, and tends to zero. Without initial increase the global maximum may be at ignition. |
| Unique maximum | **NUMERICAL RESULT** | No multiple peaks appeared in the finite two-state sweep. The derivative identity does not enforce one sign crossing, so this numerical absence is not proof. |
| Eventual decline | **CONDITIONAL THEOREM** | It follows after a finite interior maximum if the positive rate tends to zero and no later equal maximum occurs. It is not implied by the factorization alone. |
| `M -> 0` | **CONDITIONAL THEOREM** | For a global solution confined to `x in [x0,1]`, `C in [0,1]`, with `x0>0`, positive parameters, and the smooth closed forcing, bounded monotone area plus uniform continuity of the autonomous rate gives `M -> 0`. |
| Finite-time extinction | **COUNTEREXAMPLE** | Positive `C` and `F` cannot reach zero in finite time in the smooth exact ODE. Both equations vanish multiplicatively at their boundaries. |
| Asymptotic extinction | **MODEL PREDICTION** | Under the global-solution and invariant-set assumptions above, extinction is asymptotic. Abrupt observed termination requires thresholding, observation loss, suppression, barriers, weather change, or another process. |

The derivative identity alone permits `M(t)=exp(t)` and `M(t)=exp(-t)`, so it
cannot manufacture a rise-peak-decline sequence. Lean includes both examples
in `Lifecycle.lean`.

## Sufficient life-cycle conditions

**CONDITIONAL THEOREM.** A rise-peak-decline trajectory is guaranteed if all
of the following are supplied:

1. `M` is positive and continuously differentiable on its lifetime.
2. `B>0` on an initial interval.
3. There is a finite `tp` with `B(tp)=0`.
4. `B<0` after `tp`.
5. `M(t)->0` as `t->infinity`.

These conditions are sufficient, not necessary. Conditions 2-4 are exactly
the sign pattern that needs scientific explanation; restating them is not a
derivation of that pattern from the model parameters.

## Can the peak be predicted from observations?

| Quantity | Status from common fire products |
| --- | --- |
| `A`, `M=A'`, and `(2/3)M/A` | Inferable from a sufficiently resolved area sequence; derivatives amplify noise. |
| `F` and `F'/F` | Inferable only after defining and measuring event-specific `Amax`; final realized area cannot be substituted prospectively without leakage. |
| `C` and `C'/C` | Latent unless active connected boundary is independently measured and calibrated. Ordinary mapped perimeter is not automatically `Pa`. |
| `eta` and `eta'/eta` | Model-derived from `C/F`; not an independent observation. |
| `alpha`, `mu`, `beta0` | Require calibration; they are not identified by one instantaneous balance. |

**MODEL PREDICTION.** With independently defined `Amax`, active-boundary
connectivity, and parameters fitted on earlier fires, the sign of the reduced
balance predicts whether metabolic rate should increase or decrease next.

**EMPIRICAL HYPOTHESIS.** That sign will predict held-out wildfire peak timing
better than persistence, flexible trajectory models, weather-aware spread
models, or conventional spread simulators.

## Dimensionless form

Set

```text
x = A/Amax,          x0 = A0/Amax,
tau = alpha t,       F = (1-x)/(1-x0),
gamma = beta0/[alpha Amax^(1/3)],
delta = mu/alpha.
```

The unchanged system becomes

```text
dx/dtau = gamma C F eta(C/F) x^(2/3)
        = gamma 4C^2F^2/(C+F)^2 x^(2/3),
dC/dtau = C[(1-C)F-delta].
```

**THEOREM.** After choosing `Amax` and `1/alpha` as scales, the differential
equations contain three dimensionless inputs: `gamma`, `delta`, and `x0`, plus
the initial state `C0`. Other time scalings can move a coefficient but cannot
remove both rate ratios and `x0` generically.

Analytic boundaries, without invented cutoffs:

- **THEOREM:** connectivity recruits exactly when `(1-C)F > delta`.
- **THEOREM:** if `delta>=1`, connectivity cannot recruit anywhere in the unit square.
- **THEOREM:** the positive fixed-`F` equilibrium exists exactly when `F>delta`.
- **THEOREM:** matching is optimal at `C=F`; whether matching is improving depends on the sign of `(F-C)(C'/C-F'/F)`.
- **THEOREM:** growth changes from acceleration to decline on the exact balance surface `B=0`.

Terms such as “growth-dominated” or “fuel-limited” are useful descriptions of
continuous contribution balances, but the equations provide no additional
sharp regime boundaries. Any cutoff based on relative term magnitude must be
labeled a numerical classification choice.

## Joint and competing predictions

**THEOREM.** Exact `A=x^3` and `P=kx^2` imply `P^3=k^3A^2`. Consequently,

```text
P ~ A^(2/3),  A ~ t^3,  P ~ t^2
```

are constrained by `2 = (2/3)*3`. They provide at most two independent
exponent constraints, not three. Lean:
`MechanismTests.cubic_quadratic_headlines_are_dependent`.

The full life-cycle model has variable `CFeta`, so cube-root area is generally
not linear and the cubic/quadratic time laws are not global predictions. They
are exact only under constant forcing and asymptotic under the constant-beta
special case.

### Alternative mechanisms

| Pattern | Simple alternative | Distinguishing observation |
| --- | --- | --- |
| `P~A^(2/3)` | `P=kappa(A)A^(1/2)` with `kappa~A^(1/6)` | Independently track shape coefficient, active fraction, and local slope. |
| `A~t^3` | Any kinematic front with characteristic length `L~t^(3/2)` and compact area `A~L^2` | Direct normal spread speed and forcing history. |
| `P~t^2` | Quadratic branching or edge-production process unrelated to burned-area metabolism | Co-registered perimeter topology and active-line turnover. |
| All three | `L~t^(3/2)`, `A~L^2`, `P~L^(4/3)` | Test the `C`, `F`, matching, and peak-balance closures, not the dependent exponents. |

The last construction is formalized by
`MechanismTests.kinematic_alternative_all_three`. It reproduces the headline
powers without asserting a metabolic mechanism.

## Prediction categories

| Prediction | Category | Qualification |
| --- | --- | --- |
| `M/A^(2/3)=beta0[2CF/(C+F)]^2` | Exact instantaneous identity | Conditional on every closure and the matching definition. |
| Peak balance `B=0` | Exact instantaneous identity | Characterizes a differentiable positive peak; does not ensure one exists. |
| `A^(1/3)` linear in time | Finite-time dynamical prediction | Exact only for constant `beta=beta0CFeta`. |
| `P~A^(2/3)` | Finite-range scaling prediction | Requires stable coefficient and measurement object. |
| `A~t^3`, `P~t^2` | Asymptotic prediction | Constant-beta special case only. |
| Rise-peak-decline life cycle | Qualitative prediction | Occurs only for a subset of states and parameters. |
| `F>delta` connectivity threshold | Instantaneous/quasi-equilibrium prediction | Exact for fixed `F`; moving `F` makes the equilibrium time-dependent. |
| `M->0` | Asymptotic prediction | Requires a global bounded solution and unchanged closed dynamics. |
| Abrupt finite extinction | Not predicted | Requires an added process or an observation threshold. |

## Numerical stress test

**NUMERICAL RESULT.** A deterministic grid of 750 unchanged dimensionless
systems gave:

- 442 initial acceleration cases;
- 312 monotone-decline cases;
- 412 interior global peaks;
- 203 cases losing half of initial connectivity before 10% of available area burned;
- 219 cases reaching `F<0.1` while `eta>0.8`;
- 345 cases reaching `eta<0.1` while `F>0.5`;
- zero multiple metabolic peaks detected on this finite grid;
- 531 cases below `10^-4` of peak rate by `tau=200`.

The result is reproducible with `scripts/adversarial_lifecycle.py`. The finite
grid and horizon cannot prove peak uniqueness or asymptotic extinction.
