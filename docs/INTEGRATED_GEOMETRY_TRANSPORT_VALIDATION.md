# Integrated Geometry-Transport Validation

## Executive verdict

The complete proposed chain does not survive as one mechanism.

```text
departure from 2/3 -> spatial reorganization -> restoration toward 2/3
```

The first arrow is supported as a prospective held-out association. The
second is not supported overall and is strongly asymmetric. The earlier
attractor audit still rejects a universal two-thirds equilibrium.

```text
spatial reorganization -> future effective coupling -> future growth
```

Recent R adds a small, reproducible amount of held-out information beyond
existing geometry from approximately 5 days onward. The gain persists in the
interval-average coupling target at long leads, but absolute future-area error
continues to grow and the target increasingly averages over post-terminal
days. This is retained predictive information, not precise long-range fire
dynamics.

## 1. Attractor result

The locked full-cohort result remains negative for a specifically `2/3`
attractor. The held-out next-observation restoring slope is `-0.0448`, but the
free equilibrium is `-1.87` with interval `[-10.43, -0.72]`, only 30.7% of
transitions finish closer to `2/3`, and a matched measurement-error null is
more negative than the observed relationship. Total perimeter reverses the
sign. See the geometric-attractor validation for the full falsification set.

## 2. Does departure predict reorganization?

Yes, narrowly. In 1,366 held-out transitions from 221 sampled fires, the
coefficient of absolute departure from `2/3` in the prespecified R model is
`0.0129`, with whole-fire bootstrap interval `[0.0085, 0.0184]`, after
controlling for area, area added, and fire age. The model explains 33% of R
variance, mostly through size and interval-growth covariates.

This reaches evidence level 4: geometric departure prospectively predicts a
spatial-change measurement. It does not establish optimization or a preferred
state.

## 3. Does R predict restoration?

No overall. The focal R coefficient for restoring movement is `0.022`, with
whole-fire interval `[-0.238, 0.364]`. More R predicts positive raw slope
change, but that is restoring mainly for the many observations below `2/3`.
Above `2/3`, the descriptive association reverses. Binned held-out restoration
fractions remain below one half across the observed central R range.

The within-fire centered association is positive but small in explanatory
power (`R2=0.030`) and does not overcome the failed directional and
measurement-error tests. The proposed reorganization-restoration mechanism is
not supported.

## 4. Does R predict future K?

Yes, modestly. At a day-7 origin, geometry plus OT versus geometry alone has
paired whole-fire differences in held-out `log(1+K)` MAE of:

| Lead | MAE difference | 95% interval |
| ---: | ---: | ---: |
| 1 day | +0.0008 | [-0.0037, 0.0055] |
| 3 days | -0.0030 | [-0.0083, 0.0019] |
| 5 days | -0.0096 | [-0.0152, -0.0039] |
| 7 days | -0.0075 | [-0.0124, -0.0030] |
| 14 days | -0.0056 | [-0.0093, -0.0019] |
| 28 days | -0.0037 | [-0.0060, -0.0016] |
| 42 days | -0.0027 | [-0.0044, -0.0011] |

The one- and three-day increments are indistinguishable from zero. The
five-day and longer differences are small but reproducible. OT-only models do
not beat existing geometry; the positive result is incremental information in
combination with the established state.

## 5. Does the integrated model improve future area?

At day 7 and seven-day lead, median future-area percentage error is 16.0% for
geometry, 13.8% for geometry plus OT, and 14.9% for the full integrated model.
At 42 days those values are 21.5%, 21.0%, and 20.9%. Mean absolute error still
rises from roughly 3.4 square kilometers at one day to 24-25 square kilometers
at 42 days.

The decreasing K error with lead is partly mechanical: interval-average K
shrinks as more fires terminate. Rank correlations remain informative, but
this design does not condition primary forecasts on survival. The result is a
small improvement in eventual growth-course prediction, not accurate timing
of late growth or death.

## 6. Does the cube-root target help?

For the same day-7 geometry-plus-OT model, the exact `2/3` cube-root target has
the best standardized held-out error from five through 49 days among the
prespecified `2/3`, `1/2`, and calibration-selected `0.25` transformations.
At seven days, standardized MAE is `0.390`, versus `0.397` for `1/2` and
`0.397` for `0.25`. At one and three days the alternatives are slightly
better. This supports the cube-root target as a useful longer-interval
parameterization; it does not identify a geometric attractor or metabolism.

## 7. Does OT earn its complexity?

Partially. OT contributes in geometry-plus-OT models, while overlap, centroid,
and symmetric-difference metrics are highly correlated with R. Adding those
simple metrics to geometry did not yield a clear paired gain at any tested
day-7-origin lead; adding OT did from 5 through 49 days. This makes OT useful
in the locked predictor comparison, although it still does not justify a
literal-transport or uniquely mechanistic interpretation.

## 8. What does Lean establish?

Lean proves only the following unconditional mathematical consequences:

- R is nonnegative when its abstract distance is nonnegative.
- R is zero exactly at the simple-growth null only with identity of
  indiscernibles.
- Generic linear restoration with `0 < lambda < 2` decreases squared
  deviation from any specified equilibrium.

Lean also proves counterexamples: the same A and R can have different K; the
same R can have different future growth; large R need not restore geometry;
restoration can occur at R=0; and observing R does not identify latent C and F.

Observing R strictly narrows admissible future K only after adding an explicit,
empirically supplied finite interval closure `K_future in [L(R), U(R)]`. The
set-containment theorem is formal; the closure is scientific and remains only
partially supported by the held-out prediction result.

## Evidence ladder

| Level | Result |
| --- | --- |
| 1. Population slopes near `2/3` | Partially supported early, with lifecycle drift |
| 2. Within-fire restoration | Partially supported statistically; measurement error remains sufficient |
| 3. Specifically `2/3` attractor | Not supported |
| 4. Departure predicts R | Supported |
| 5. R predicts restoration | Not supported overall |
| 6. R predicts future K beyond geometry | Modestly supported from 5 days onward |
| 7. Integrated long-horizon utility | Partially supported; small gains, growing area error |
| 8. Formal narrowing of futures | Conditional on an empirical R-to-K bounds closure |

## Final synthesis

R is a useful additional observation, not the missing mechanism by itself.
The best surviving architecture is an empirical state model in which current
geometry and recent spatial change jointly help predict interval-average K.
The data do not support a universal two-thirds restoring geometry, a causal
reorganization-restoration chain, or identification of C, F, suppression, or
energetic metabolism.

## Latent realization update

The corrected outcome-blind sample contains 8,667 transport transitions from
941 fires. In the latent-constraint analysis, contemporaneous `R` was associated
with realization residual `q`, but prior `R` had almost no held-out association
with future `q` (`rho=0.0355`). OT currently behaves more like an at-onset
spatial detector than a demonstrated early warning of growth deficits. See
[Latent Constraint Validation](LATENT_CONSTRAINT_VALIDATION.md).
