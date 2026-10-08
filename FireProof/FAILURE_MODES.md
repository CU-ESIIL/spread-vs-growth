# Failure Modes

The entries below intentionally search for behavior that weakens the intuitive
fire-life-cycle narrative.

| Failure mode | Label | Result |
| --- | --- | --- |
| Monotonic decline from ignition | **NUMERICAL RESULT** | 312 of 750 parameter-grid trajectories declined monotonically. Example: `gamma=0.01`, `delta=0.1`, `x0=0.7`, `C0=0.9`. |
| No interior metabolic peak | **COUNTEREXAMPLE** | A global maximum may occur at the initial state; some slow cases were still increasing at the finite horizon. The equations do not guarantee an interior peak. |
| Multiple metabolic peaks | **NUMERICAL RESULT** | No multiple peaks were found in the 750-run closed two-state sweep. Arbitrary latent `eta(t)` can create multiple peaks in the factorized law, so uniqueness remains unproved. |
| Connectivity loss before substantial growth | **NUMERICAL RESULT** | 203 runs lost half their initial `C` before burning 10% of available area. This includes high-`delta` initial states above the moving connectivity equilibrium. |
| Fuel depletion without matching loss | **NUMERICAL RESULT** | 219 runs reached `F<0.1` while `eta>0.8`. Fuel exhaustion and matching loss are not synonymous. |
| Matching loss with abundant fuel | **NUMERICAL RESULT** | 345 runs reached `eta<0.1` while `F>0.5`. Poor matching can occur long before fuel depletion. |
| Nearly identical area, different latent state | **NUMERICAL RESULT** | One pair had area RMSE `9.39e-7` and connectivity RMSE `0.140`. Area alone can be practically uninformative about `C`. |
| Apparent `2/3` without proposed geometry | **COUNTEREXAMPLE** | `A^(1/2)` times a coefficient proportional to `A^(1/6)` is exactly `A^(2/3)`. |
| All three headline powers without metabolism | **COUNTEREXAMPLE** | A kinematic construction with `L~t^(3/2)`, `A~L^2`, and `P~L^(4/3)` gives all three slopes. |
| Abrupt finite extinction | **MODEL PREDICTION** | Positive `C` and `F` approach their zero boundaries asymptotically. Abrupt stops require a threshold, exogenous forcing, barrier, suppression, or observation process. |

## Why monotone decline is allowed

**THEOREM.** The sign of `M'` is the sign of the exact balance

```text
B = C'/C + F'/F + eta'/eta + (2/3)M/A.
```

The positive geometric term does not dominate by necessity. Large initial
area fraction, high connectivity relative to fuel, rapid fragmentation, or
fast fuel consumption can make the other terms negative enough that `B<0` at
ignition.

## Why finite extinction is not produced

In dimensionless form,

```text
F' = -gamma/(1-x0) [2CF/(C+F)]^2 x^(2/3),
C' = C[(1-C)F-delta].
```

**CONDITIONAL THEOREM.** On the biological state space, `F' >= -K F^2` for a
finite constant `K`, and `C'=C q(t)` with bounded `q`. Positive initial `F` and
`C` therefore remain positive at every finite time. The modeled metabolic rate
can become arbitrarily small but does not hit exactly zero in finite time.

This matters empirically: a sharp terminal day in FIRED cannot, by itself, be
called model-predicted death. It may represent detection limits, daily
aggregation, cloud/smoke gaps, barriers, weather, fuel discontinuity, or
suppression.

## Numerical scope

The deterministic sweep spans:

```text
gamma: 0.01, 0.05, 0.2, 1, 5
delta: 0.02, 0.1, 0.3, 0.7, 1, 1.5
x0:    0.001, 0.05, 0.3, 0.7, 0.9
C0:    0.005, 0.03, 0.15, 0.5, 0.9
tau:   0 to 200
```

The complete records are in `results/lifecycle_parameter_sweep.csv`; the
summary and representative cases are in
`results/lifecycle_adversarial_summary.json`. These are **NUMERICAL RESULTS**,
not phase-space theorems.
