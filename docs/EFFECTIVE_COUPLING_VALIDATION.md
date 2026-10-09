# Effective Coupling Validation

## Question and observable

The reduced growth factorization can be written

```text
M = K A^(2/3)
```

For each FIRED event-day after ignition, this analysis defines the observable
normalized mapped-growth coefficient

```text
K_obs(d) = daily mapped area(d) / start-of-day mapped area(d)^(2/3).
```

Under the latent-realization extension this is more precisely **realized
effective coupling**, `K_realized=B K`. FIRED observes the product; it does not
separately identify the realization factor `B` and endogenous coupling `K`.

`K_obs` is not an independent measurement of latent coherence `C`, reachable
fuel `F`, `beta_0`, active fireline, or chemical power. It is an observable
re-expression of mapped area growth whose value is tested prospectively.

## Design

The experiment reuses the same 4,032 FIRED events and locked temporal split as
the detection analysis. Models are developed on 2001-2012 fires,
regularization and normalization are chosen on 2013-2015 fires, and all main
performance estimates use 1,164 held-out 2016-2020 fires. Origin-time features
include current and recent `K_obs`, area dynamics, and mapped geometry.

The analysis compares:

- current-coupling persistence;
- coupling history;
- area and recent dynamics;
- area, dynamics, and mapped geometry; and
- a fixed flexible quadratic expansion.

Predicted coupling is then propagated through the growth identity to forecast
future area. This structured forecast is compared with the existing direct
geometry area model using paired whole-fire bootstrap intervals.

## Main results

The full run contains 54,002 event-days. At day 7, geometry improves
one-day coupling error from `0.260` for area dynamics to `0.222` in absolute
`log1p(K)` units; the paired difference is `-0.0376` with 95% interval
`[-0.0471, -0.0280]`. At three days the difference is `-0.0162`
`[-0.0226, -0.0095]`. By seven days the incremental geometry effect is small
and its interval includes zero (`-0.00149`, `[-0.00326, 0.00034]`).

The apparent raw coupling error becomes very small at long horizons because
most targets are post-terminal zero-growth days. This is not evidence of
precise long-range active-fire coupling prediction. Rank correlation declines
from `0.585` at one day to `0.026` at 49 days, while the fraction of active
targets falls from `0.808` to `0.00086`.

Despite that limitation, recursive structured area forecasts are modestly
better than the direct geometry-area model at every tested day-7 horizon. The
paired absolute-log-error advantage ranges from `-0.00745` at one day to about
`-0.0136` at 49 days; the seven-day difference is `-0.0125` with 95% interval
`[-0.0179, -0.00744]`. These are small but reproducible held-out improvements.

## Is the normalization specifically 2/3?

No. Calibration selected `sigma = 0.25`, with calibration error `0.2423`,
compared with `0.2442` at `2/3`. On held-out fires, `2/3` is numerically best
among the prespecified values (`0.2407` versus `0.2444` for the selected
`0.25`), but the differences are very small. This experiment supports a
predictable time-varying normalized-growth state, not unique identification of
the `2/3` exponent.

## Memory and heterogeneity

Within-fire coupling memory is short. Mean lag correlation is `0.234` at one
day, `0.156` at two days, and `0.105` at three days, with values near zero at
many longer lags. Both between-fire and within-fire variation remain large
after normalization. The coefficient is therefore a rapidly changing state,
not a constant fire-specific parameter.

## Area and transition prediction

The structured model improves future-area prediction slightly and often
classifies acceleration competitively with direct geometry. It does not make
termination a solved problem. Long-horizon fixed-origin performance includes
many already-ended events, while persistent-fire-only analyses have much
smaller samples and substantially larger errors. Updating the origin as new
geometry and coupling arrive is more reliable than extrapolating one early
state for many weeks.

For three-day acceleration from day 7, structured coupling reaches balanced
accuracy `0.811` and Brier score `0.144`. Direct geometry remains better
(`0.821` and `0.125`), while area dynamics is worse (`0.739` and `0.169`).
Predicted coupling therefore carries much of the geometry-associated
acceleration signal, but does not fully mediate it and is not a causal
mediation estimate.

## Fire-size transfer

The scale-transfer result is mixed and does not support a general advantage
for `A^(2/3)` normalization. With day-5 origins, normalized-coupling models
transfer worse than raw-growth models from small to large fires (`1.510`
versus `1.122` event-weighted absolute `log1p` growth error) and slightly worse
in the reverse direction (`0.660` versus `0.629`). At day 7, normalization is
better from small to large (`0.700` versus `0.793`) but slightly worse from
large to small (`0.525` versus `0.518`). Size classes use development-period
origin area only, never final fire size. The complete secondary experiment is
in `fire_size_transfer.csv`.

## Residual diagnostics

Structured area residual correlations with origin area and perimeter are
small (`rho = -0.017` and `-0.047`) compared with the direct geometry model
(`-0.113` and `-0.116`). Residual dependence on horizon remains (`rho =
0.092`). The decomposition organizes much of the scale dependence but does not
remove all temporal structure.

## Scientific interpretation

The positive result is practical and narrow:

> A time-varying normalized mapped-growth coefficient contains predictable
> information, mapped geometry improves its short-horizon prediction, and
> propagating that state through a structured area equation gives a small
> held-out improvement over a direct area model.

The result does not identify the theoretical factors inside `K`, validate an
energetic metabolism, or establish that `2/3` is the uniquely correct
normalization. The companion [geometric-attractor analysis](GEOMETRIC_ATTRACTOR_VALIDATION.md)
also shows that evolving mapped slope should not be replaced by a universal
restoring law centered at `2/3`.

## Evidence table

| Prediction | Verdict | Reason |
| --- | --- | --- |
| Effective coupling varies after controlling for area | SUPPORTED | Large within- and between-fire variance remains in every well-populated area bin. |
| Future effective coupling is predictable | SUPPORTED | History and state models beat current-coupling persistence on held-out fires. |
| Geometry improves short-horizon coupling prediction | SUPPORTED | Paired day-7 gains are clear at one and three days and fade by seven days. |
| Predicting coupling improves future-area prediction | SUPPORTED | Structured propagation gives small paired held-out gains through tested horizons. |
| Coupling explains all geometry-associated acceleration skill | NOT SUPPORTED | Structured coupling beats dynamics but remains below direct geometry. |
| `2/3` is uniquely better than `1/2` or a selected exponent | NOT SUPPORTED | Calibration selects `0.25`; held-out differences among normalizations are small. |
| Normalization improves transfer across fire size | PARTIALLY SUPPORTED | It helps only the day-7 small-to-large direction and hurts or ties the others. |
| `K_obs` identifies `C`, `F`, `beta_0`, or energetic metabolism | NOT IDENTIFIABLE | FIRED lacks independent measurements of those quantities. |

## Reproduction

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  .venv/bin/python scripts/run_effective_coupling_validation.py
```

Use `--smoke --output-dir outputs/effective_coupling_validation_smoke` for a
small deterministic check. Use `--reuse-primary` to resume downstream
summaries and figures from an existing primary prediction table. Complete
machine-readable outputs, the design lock, and PDF/SVG/high-resolution PNG
figures are under `outputs/effective_coupling_validation/`.
