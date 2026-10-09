# Geometric Attractor Validation

## Executive verdict

The held-out FIRED analysis does **not** support the strong claim that mapped
wildfire geometry is dynamically restored toward a universal `2/3`
perimeter-area state.

There is a weak negative association between current exterior-perimeter slope
and the next local slope change, and the same-fire centered association is
negative. Those facts alone look like mean reversion. The stronger tests fail:

- the freely estimated equilibrium is not near `2/3` and is unstable;
- only 30.7% of next-observation transitions end closer to `2/3`;
- matched measurement error creates more negative apparent reversion than the
  observed association;
- switching from exterior to total mapped perimeter reverses the restoring
  slope; and
- a flexible empirical dynamics model predicts held-out future slope better
  than fixed `2/3` attraction.

The defensible result is therefore a mixture of noisy within-fire geometric
fluctuation, lifecycle drift, observation-operator sensitivity, and some
predictable slope dynamics. It is not evidence for a fixed physical
two-thirds attractor.

## Design and data

The analysis reuses the locked 4,032-fire FIRED cohort and temporal split:

| Partition | Ignition years | Role |
| --- | --- | --- |
| Development | 2001-2012 | estimator and model development |
| Calibration | 2013-2015 | estimator and regularization selection |
| Held out | 2016-2020 | one final evaluation |

Local state uses positive mapped-area observation days. Four candidate
estimators were fixed before evaluation: adjacent finite differences,
five- and seven-observation rolling OLS, and five-observation Theil-Sen. The
seven-observation rolling OLS estimator had the lowest calibration future-slope
MAE (`0.188`) and was locked without considering proximity to `2/3`.

The primary estimator produced 21,655 local states. Whole fires, rather than
daily rows, are the bootstrap unit. All origin features are available at or
before the labeled event day.

## 1. Do individual fires show restoring dynamics?

For the next observed state, the held-out regression was

```text
delta_sigma = a + b sigma_t
b = -0.0448
event-bootstrap 95% interval: [-0.0822, -0.00825]
```

The within-fire centered slope was `-0.0935` with event-bootstrap interval
`[-0.1327, -0.0526]`. This establishes a negative within-fire association.
It does not establish attraction toward `2/3`: only 30.7% of next transitions
finished closer to `2/3`, well below one half.

The discrepancy is possible because a negative change-versus-state slope can
reflect generic regression to a fire-specific mean, overlapping rolling
windows, measurement error, lifecycle drift, or overshoot. Direction of change
and distance to a proposed equilibrium are different tests.

## 2. Where is the empirical equilibrium?

The next-observation free model implies an equilibrium of `-1.87`, with a 95%
bootstrap interval from `-10.43` to `-0.72`. This is not physically plausible
as a universal perimeter-area exponent and is not compatible with `2/3` or
`1/2`.

At longer leads, estimated equilibria also vary substantially. Such ratios are
unstable when the fitted restoring slope is weak or when the intercept contains
lifecycle drift. The data therefore do not identify a single equilibrium.

## 3. Is the empirical equilibrium compatible with 2/3?

No for the primary held-out next-observation fit. The free-equilibrium interval
does not contain `2/3`. Development and calibration estimates are much less
stable, which is additional evidence against a universal fixed point rather
than a reason to select a favorable partition.

## 4. Does 2/3 outperform alternatives?

At the next observation, mean absolute future-slope errors were:

| Model | Held-out MAE |
| --- | ---: |
| Flexible dynamics | 0.1957 |
| Free attractor | 0.1960 |
| Fixed `2/3` | 0.2172 |
| Persistence | 0.2205 |
| Population-mean reversion | 0.2205 |
| Fixed `1/2` | 0.2207 |

The fixed `2/3` model improves MAE over persistence by only `0.0033`. At three,
seven, and fourteen days, the fixed `1/2` model is more accurate than fixed
`2/3`, and the flexible model remains best among the prespecified comparisons.
The free model is competitive but its equilibrium is not interpretable as
`2/3`.

## 5. Can measurement error explain restoration?

Yes. Under an event-specific latent-state measurement-error null, the median
apparent slope was `-0.135` with a 95% range from `-0.145` to `-0.126`, more
negative than the observed `-0.0448`. Every simulated measurement-error
replicate was at least as negative as the observed association.

A variance- and lag-autocorrelation-matched random-walk null was mildly
positive (median `0.028`) and did not reproduce the negative slope. A
shuffled-time null produced very strong negative regression
because independently pairing values from a bounded within-fire distribution
mathematically creates regression to its mean. Together, these nulls show that
temporal ordering contains structure but do not rescue a two-thirds center.

## 6. Is restoration visible within fires?

The centered within-fire coefficient is negative at 1, 3, 7, and 14 days.
However, this result is compatible with return toward fire-specific states and
with rolling-estimator error. It is evidence for within-fire mean reversion in
the statistical sense, but not for a shared `2/3` attractor.

## 7. Is the attractor fixed or lifecycle dependent?

Neither a stable fixed equilibrium nor a defensible moving equilibrium was
identified. Age-, area-, and effective-coupling strata yield widely varying,
often implausible free equilibria. This instability rejects the simple fixed
model but does not provide enough support to estimate a scientifically useful
moving attractor.

## 8. How quickly do fires return?

Among 20 held-out fires lasting at least 40 days, repeated crossings are
common: observed counts range from 2 to 9. Return fractions to within `0.1` of
`2/3` range from 0 to 1, and event-level median return times range from 1.5 to
17.5 days where a return occurs. The heterogeneity is too large for one
universal relaxation time.

## 9. Is restoration associated with boundary reorganization?

Associations are modest. At one day, restoration correlates `0.149` with log
perimeter change, `-0.075` with component change, and `0.161` with hole change.
Some correlations strengthen at 3-7 days, but the variables are cumulative
mapped-boundary proxies measured by the same observation process. They are
consistent with boundary reorganization, not causal proof of optimization.

## 10. Is restoration associated with effective coupling?

Current deviation is associated with future observable effective coupling
(`rho = 0.448` at one day), while absolute deviation is negatively associated
with it (`rho = -0.370`). The association with change in coupling is near zero
at one day (`rho = -0.015`). Restoration itself has a modest positive
association with future coupling (`rho = 0.239`). These are descriptive links
between mapped geometry and realized growth; they do not identify latent `C`,
fuel `F`, `beta_0`, active fireline, or energetic metabolism.

## 11. Does attraction improve prediction?

Only marginally for the next geometric state, and not enough to beat flexible
dynamics. Adding a forecast geometric state to current geometry is also
largely redundant for future coupling and area because the locked linear
attractor forecast is itself a deterministic linear transform of current
state. The downstream comparison is retained in
`attractor_downstream_prediction_metrics.csv`; it does not justify treating
attraction as a new operational predictor.

## 12. Observation-rule robustness

The primary exterior-perimeter slope is `-0.0448`. With total mapped perimeter
it becomes `+0.0683` with a wholly positive bootstrap interval, implying
divergence rather than restoration. Every-other-observation exterior geometry
gives `-0.0264` with an interval spanning zero. This sensitivity is strong
evidence against a robust physical-attractor interpretation.

No multi-resolution geometry is available. The test concerns mapped FIRED
geometry at the product's available scale and must not be generalized to an
active flame front or claimed as scale invariant.

## Evidence table

| Prediction | Verdict | Reason |
| --- | --- | --- |
| Population slopes recur near `2/3` | PARTIALLY SUPPORTED | Existing held-out medians are near `2/3` early and drift downward. |
| Individual fires show negative within-fire slope feedback | PARTIALLY SUPPORTED | Centered coefficients are negative, but rolling-window error is a major alternative. |
| The free equilibrium is compatible with `2/3` | NOT SUPPORTED | Primary held-out equilibrium and interval exclude `2/3` and are physically implausible. |
| `2/3` outpredicts `1/2` and generic mean reversion | NOT SUPPORTED | Tiny one-step advantage does not persist; `1/2` is better at longer tested leads. |
| Restoration survives measurement-error nulls | NOT SUPPORTED | Matched measurement error produces stronger apparent reversion. |
| Long fires repeatedly cross the same neighborhood | PARTIALLY SUPPORTED | Crossings occur, but return fractions and times are highly heterogeneous. |
| A stable lifecycle-dependent attractor is identified | NOT SUPPORTED | Stratified free equilibria are unstable and often implausible. |
| Departures precede mapped boundary change | PARTIALLY SUPPORTED | Modest associations exist but share an observation operator and are noncausal. |
| Geometry is associated with future observable coupling | SUPPORTED | Held-out rank associations are moderate, especially at short leads. |
| Attractor dynamics add operational prediction beyond current geometry | NOT SUPPORTED | Flexible current-state dynamics are better and attractor forecasts are largely redundant. |
| Literal boundary optimization | NOT IDENTIFIABLE | No optimization objective or active-boundary energy measurement exists. |
| Scale-invariant active flame-front attraction | NOT IDENTIFIABLE | Only one coarse mapped observation scale is available. |

## Final answers

**Do wildfire geometries exhibit genuine within-fire mean-reverting dynamics?**
There is a negative within-fire statistical association, but it does not
survive the strongest interpretation because measurement error can explain it
and most transitions do not finish closer to `2/3`.

**Is the empirical attractor statistically consistent with `2/3`?** No. The
free equilibrium is unstable and the primary held-out interval excludes
`2/3`.

**Does `2/3` predict held-out evolution better than `1/2`, generic mean
reversion, and flexible alternatives?** It has a tiny next-step advantage over
persistence and `1/2`, but this does not persist and it loses clearly to the
flexible model.

**Does modeling attraction improve future fire-dynamics prediction?** Not in a
materially distinct way beyond current mapped geometry and flexible dynamics.

The subsequent [integrated geometry-transport validation](INTEGRATED_GEOMETRY_TRANSPORT_VALIDATION.md)
does not overturn this verdict. Absolute departure from `2/3` predicts more
spatial reorganization, but R does not consistently predict movement back
toward `2/3`.

## Reproduction

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  .venv/bin/python scripts/run_geometric_attractor_validation.py
```

Machine-readable results and PDF/SVG/high-resolution PNG figures are written
to `outputs/geometric_attractor_validation/`. The prespecified design is in
`docs/GEOMETRIC_ATTRACTOR_AUDIT.md` and `design_lock.json`.
