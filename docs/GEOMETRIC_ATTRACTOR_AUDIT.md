# Geometric Attractor Validation: Locked Design

## Question

This analysis tests whether mapped wildfire perimeter-area geometry shows
within-fire restoring dynamics. A population distribution centered near
`2/3` is not sufficient evidence. The prospective claim is that a departure
of the local state

```text
sigma(t) = d log(P) / d log(A)
```

predicts a subsequent change back toward a preferred state.

## Cohort and split

The analysis reuses the 4,032-event FIRED cohort and the existing temporal
split without alteration:

- development: 2001-2012;
- calibration: 2013-2015; and
- held-out evaluation: 2016-2020.

Geometry is the cumulative union available through each event day. The
primary perimeter is exterior mapped perimeter. Total perimeter and
every-other positive-area observation are observation-operator checks.

## Local-state estimators

Four estimators are prespecified:

1. adjacent-observation finite difference;
2. five-observation rolling ordinary least squares;
3. seven-observation rolling ordinary least squares; and
4. five-observation rolling Theil-Sen slope.

All use positive mapped-area observation days only. Finite differences are
local but high variance. Longer rolling windows reduce variance while mixing
more of the lifecycle. Theil-Sen limits leverage from one unusual mapped
increment but is less efficient under approximately Gaussian noise.

The primary estimator is selected using development/calibration one-step
future-slope prediction error and coverage only. Distance of its mean or
equilibrium from `2/3` is not a selection criterion. The selected estimator is
then frozen for held-out tests.

## Primary model and inference

For each valid transition,

```text
delta_sigma = a + b (sigma_t - 2/3) + error.
```

Restoration requires `b < 0`. Confidence intervals resample whole fires, not
event-days. The report gives the ordinary interval only as a diagnostic; the
event-bootstrap interval is the inferential result.

The free-equilibrium form is fit as `delta_sigma = alpha + b sigma_t`. When
`b < 0`, the implied equilibrium is `-alpha / b` and restoring strength is
`lambda = -b`. Fixed-attractor models constrain the intercept through centers
of `1/2`, `2/3`, and the development population mean.

## Prospective comparison

All model forms and features are fixed before held-out evaluation:

- persistence;
- population-mean reversion;
- fixed `1/2` attraction;
- fixed `2/3` attraction;
- free empirical attraction; and
- flexible ridge dynamics using current slope, age, area, recent observed
  growth, components, holes, and current effective coupling.

Model coefficients are fit on development data, hyperparameters are chosen on
calibration data, and final locked coefficients use development plus
calibration before one held-out evaluation.

## Prespecified threats and robustness checks

- measurement-error null with event-specific latent states and observed slope
  uncertainty;
- within-fire shuffled-time null;
- matched random-walk null without a preferred equilibrium;
- within-fire centered model separating event means from excursions;
- exterior versus total perimeter;
- full versus every-other positive observation;
- lifecycle-, area-, and effective-coupling-dependent equilibrium diagnostics;
- long-fire excursion, return, crossing, and overshoot summaries; and
- boundary reorganization and effective-coupling associations.

Synthetic nulls use fixed seed `20261008`. No spatial-resolution robustness is
possible from the cached FIRED product. Results apply to mapped FIRED geometry
at its available observation scale, not automatically to active flame-front
geometry.

## Interpretation boundary

The analysis can distinguish a recurring population location from a
within-fire restoring association and can compare prospective predictions. It
cannot prove literal optimization, energetic metabolism, causal boundary
reorganization, independently active fireline, or scale invariance.
