# Effective Coupling Validation Audit

## Reusable design

The effective-coupling experiment can reuse the existing 4,032-event FIRED
cohort, cumulative geometry, development/calibration/held-out year partitions,
snapshot feature construction, immutable predictor whitelists, standardized
ridge models, fixed quadratic expansion, binary transition models, regression
metrics, and whole-event bootstrap comparisons. In particular,
`merge_geometry_sequences`, `make_lifecycle_features`,
`fit_standardized_ridge`, `tune_ridge_alpha`, `tune_binary_model`,
`regression_metrics`, and `paired_event_bootstrap` already implement most of
the required origin-safe machinery.

The existing area and geometry feature tables contain future outcome columns
and future-derived land-cover indicators. They may be retained as outcomes or
descriptive metadata, but they must not enter a predictor matrix. The new
pipeline will use the same explicit `AREA_PREDICTORS`,
`DYNAMICS_PREDICTORS`, and `GEOMETRY_PREDICTORS` whitelists used by the
adversarial validation.

## Observable definition

For a mapped increment during day `d`, the discrete normalized growth
coefficient is prespecified as

```text
K_obs[d] = (A[d] - A[d-1]) / A[d-1]^sigma,
```

with primary `sigma=2/3`. Day 1 is excluded because no positive pre-ignition
mapped area is available. This start-of-interval convention matches the
prospective recursion

```text
A_hat[d] = A_hat[d-1] + K_hat[d] A_hat[d-1]^sigma.
```

`K_obs` is an observable normalized growth coefficient. It is not an
independent observation of latent coherence, connected fuel, physical
coupling, or energetic metabolism. The identity used to calculate it cannot
validate the exponent or the canonical latent model.

## Prespecified prospective target

Future coupling is predicted one daily lead at a time. At an origin day `t`,
the lead-`j` target is `log1p(K_obs[t+j])`. If mapped growth has terminated,
the observed trajectory is extended at its final cumulative area and the
subsequent coupling target is zero. This defines an operational trajectory
forecast for every fire observable at the origin and does not condition the
primary analysis on future survival.

Each lead-specific coupling model uses only the fixed origin snapshot. The
area forecast is then generated recursively from predicted coupling and
predicted area; observed future area is never inserted into the recursion.
No forecasted geometry or future state is used as a predictor.

## Leakage and circularity risks

1. Using `K_obs[t+j]`, future area, future geometry, final size, duration, or
   dominant future-footprint land cover as predictors would leak outcomes.
2. Conditioning the primary long-horizon cohort on being observable at
   `t+j` would leak future survival. Such subsets are reserved for a labeled
   persistent-fire trajectory analysis.
3. Showing that growth varies with area after conditioning on same-day
   `K_obs=M/A^sigma` is algebraic decomposition, not independent validation.
4. Using observed future area in `K_hat A^(2/3)` would make the structured
   area forecast nonprospective. Only recursively predicted area is allowed.
5. Mapped perimeter is cumulative geometry, not active fireline. Geometry can
   predict future normalized growth without identifying `C`, `F`, or
   `beta_0`.

## Locked extensions

- Forecast origins: days 5 and 7 for the primary comparison; days 10, 14,
  and 21 for updating forecasts when every temporal partition contains at
  least 40 fires. Later origins are omitted under this prespecified rule.
- Leads: 1, 3, 5, 7, 10, 14, 21, 28, 35, 42, and 49 days.
- Primary minimum sample: 100 held-out fires. Because terminal plateaus remain
  outcomes, the day-5 and day-7 operational cohorts retain all origin-eligible
  fires. Persistent-fire conditional summaries require at least 40 held-out
  fires at the target day.
- Independent unit: fire. Bootstrap resampling and aggregate errors operate
  on fire-level records, never pooled event-days.
- Normalization exponent selection: candidate exponents are fixed before
  held-out evaluation and selected by day-7, seven-day calibration area error.
- Geometry predictability horizon: the largest consecutive lead at which the
  calibration error of geometry-informed coupling is at least 2% lower than
  coupling persistence. The held-out result is reported at that locked lead;
  it is not reselected on test data.

This audit fixes the analysis contract before inspecting new held-out
effective-coupling performance.
