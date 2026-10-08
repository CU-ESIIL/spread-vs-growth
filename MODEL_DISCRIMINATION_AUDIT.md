# Model Discrimination Audit

## Scope and stopping point

This is the Stage 1 audit for testing whether the reduced fire-growth laws have predictive value relative to null and empirical models. It records the current scientific contract, reusable infrastructure, leakage risks, missing pieces, proposed architecture, exact experiments, expected cost, and decisions that must be locked before the 2016-2020 validation partition is evaluated with any new model.

No new model-discrimination result is reported here. The current computational SI and FIRED reports remain unchanged.

## Repository state inspected

The audit covered:

- the computational SI documentation, builder, symbolic checks, notebooks, worked examples, and 11-entry claim ledger;
- `geometry.py`, `kinematics.py`, `growth.py`, `energetics.py`, `residence.py`, `scaling.py`, `forecasting.py`, `synthetic.py`, diagnostics, figures, and their tests;
- FIRED ingestion, sequence reconstruction, rolling forecasts, outcome prediction, report generation, tests, and all current machine-readable summaries;
- Tier-1 fire-model emulators, actual-model status records, ELMFIRE tutorial output, Cell2Fire build logs, and external checkouts;
- local data inventory, including FIRED daily multipolygons and an adjacent 37 GB GridMET cache that is not yet a declared dependency of this repository.

The current suite has 98 passing tests. The computational SI correctly distinguishes identities and conditional predictions from empirical hypotheses.

## Locked scientific contract

The following definitions must not change silently:

| Item | Locked value |
| --- | --- |
| FIRED population | Natural-vegetation events, final area >= 10 km2, duration 8-60 days |
| Sequence reconciliation | Sum of daily increments within 1% of reported final area |
| Development | Ignition years 2001-2012, 2,316 events |
| Interval calibration | 2013-2015, 552 events |
| Held-out validation | 2016-2020, 1,164 events |
| Snapshot days | 3, 5, and 7 |
| Missing dates | Zero detected growth in the reconstructed daily sequence |
| Existing M2 benchmark | Ridge alpha 1.0 with the current explicit 17-column feature list |
| Primary final-area score | Mean absolute log error, averaged across events |
| Duration result | Separate from final-area prediction |

The separate rolling forecast analysis uses 2001-2015 for training and 2016-2020 for testing. It is a short-horizon trajectory experiment, not the final-outcome experiment. Its development-period sigma search selected sigma = 0 at one-, two-, and three-day horizons. That negative result is prior evidence that the two-thirds law may not win the direct trajectory test.

## Existing infrastructure that should be reused

### Mathematical implementation

- `growth.analytic_area` and `growth.constant_beta_area` implement the exact fixed-exponent solution for arbitrary sigma.
- `forecasting.calibrate_beta_two_thirds` and `forecasting.forecast_two_thirds` implement the two-thirds endpoint estimator and forecast.
- `fired_prediction.transformed_trend_forecast` already fits a nonnegative linear trend in `A^(1-sigma)` and anchors the forecast at the observed origin.
- `scaling.compare_scaling_models` provides a precedent for fixed one-half, fixed two-thirds, and free-exponent comparisons, although it addresses perimeter-area scaling rather than temporal area growth.
- `ForecastDesign` encodes a basic calibration/origin/horizon ordering constraint.

### FIRED data and benchmarks

- `load_fired_daily_attributes` reads the 548 MB GeoPackage through immutable SQLite without copying it.
- `reconstruct_daily_sequences` produces 58,034 gap-free daily rows for 4,032 complete events.
- `make_early_features` uses an explicit feature whitelist and snapshots at day 3, 5, or 7.
- `fit_standardized_ridge` reproduces the dependency-free M2 benchmark.
- Current outputs already preserve event-level predictions, interval calibration, summary metrics, bootstrap intervals, and source/run metadata.

### Spatial and conventional-model assets

- The FIRED GeoPackage contains daily `MULTIPOLYGON` geometries in a custom sinusoidal CRS with metre units. The current analysis reads attributes only.
- A real ELMFIRE tutorial run exists at 30 m resolution with a time-of-arrival raster and hourly isochrones.
- The ELMFIRE output is a synthetic tutorial case and is not linked to any FIRED event.
- Cell2Fire has not run; its native build stopped at a missing Boost dependency.
- Tier-1 Huygens, level-set, and cellular results are mechanism emulators and must not be labeled as conventional-model validation.

## Critical leakage and conditioning audit

### Direct predictor leakage

The current M2 result is exactly reproducible, but one predictor is not strictly origin-available: `lc_name` is the area-weighted dominant class computed from all daily polygons in the completed event. It is then copied to every reconstructed day and used in the ridge model. This is future-derived event information.

Recommended handling:

1. Preserve the existing M2 result as `M2_published` for exact reproduction.
2. Make a leakage-clean `M2_origin_clean` the primary empirical comparator by either omitting land cover or using only a class observed on or before the snapshot.
3. Quantify the difference on development data before locking the design. Do not choose between variants using 2016-2020 results.

### Future-conditioned cohort selection

The retained population is defined using final area, final duration, complete-event reconciliation, and eventual dominant land cover. Those variables are not passed to the current numerical predictor, but they condition which events exist in the experiment. Therefore the analysis estimates prediction within a retrospectively selected population; it is not an operational all-ignition forecast.

### Feature-frame hazard

`make_early_features` returns final-area and duration targets in the same table as predictors. The existing ridge model is protected by an explicit feature list. Every new estimator, especially a flexible model, must use an immutable predictor whitelist and reject unknown numeric columns.

### Repeated validation access

The 2016-2020 outcomes are already visible in the published benchmark. New model design must nevertheless be based only on mathematical commitments, development-only resampling, and the locked configuration. A new held-out run should be one-shot, written to a new immutable run directory, and never used for subsequent tuning.

### Observation-process conditioning

Zero-filled FIRED days represent no newly assigned MODIS burn pixels, not necessarily no physical fire growth. Daily increments are retrospective mapped increments. Every result must retain that interpretation.

## Central architectural ambiguity: final area requires termination

The reduced law

```text
dA/dt = beta A^sigma
```

predicts area at a specified future time. It does not determine when an event ends. Extrapolating to the observed final day would use future duration and leak outcome information.

The proposed solution separates two questions:

1. **Direct theory test:** estimate beta before the origin and predict cumulative area at fixed post-origin horizons. This is the cleanest test of transformed-area dynamics.
2. **Reduced-state outcome test:** use only the origin state `(A_snapshot, beta_hat)` in a minimal development-fitted outcome head for final area. This tests how much final-size information is retained by the reduced state without pretending that the growth equation contains a termination law.

An observed-duration forecast may be reported only as a clearly labeled oracle diagnostic, never as a primary model.

## Proposed package architecture

Add a focused subpackage rather than enlarging the current scripts:

```text
src/fire_metabolism/model_discrimination/
  schema.py              # partitions, snapshots, target and prediction records
  reduced.py             # beta estimation and fixed/free-sigma forecasts
  empirical.py           # exact M0/M1/M2 wrappers and optional M6
  evaluation.py          # common scores, event bootstrap, pairwise differences
  calibration.py         # split-conformal residual intervals
  beta_diagnostics.py    # interval-average beta and stability summaries
  failure_modes.py       # locked late-growth criteria and event summaries
  adapters.py            # common model interface and information manifest
```

Supporting files:

```text
config/fired_model_discrimination.yml
scripts/run_fired_model_discrimination.py
outputs/fired_model_discrimination/<run_id>/
```

The configuration should contain the input checksum, exact partitions, feature lists, sigma grid, internal development folds, snapshot days, horizons, interval level, bootstrap seed, model versions, and failure-mode thresholds. A SHA-256 design lock should be written before any new held-out prediction is allowed.

## Common model contract

Each model receives an origin-safe `ForecastRequest`:

```text
event_id
partition
origin_day and origin_date
area history through origin
optional origin-available covariates
requested future horizons
```

Each model returns a common `ForecastResult`:

```text
model_id and version
predicted cumulative area by horizon
predicted incremental growth by horizon
optional final-area prediction
estimated sigma and beta where applicable
input variables and data sources used
fit/runtime metadata
```

The evaluator, not the model, attaches future observations and computes errors. This is the strongest practical leakage barrier.

## Competing hypotheses

| ID | Scientific model | Origin inputs | Population-fitted quantities |
| --- | --- | --- | --- |
| M0 | No future growth | Current area | None |
| M1 | Historical remaining-growth baseline | Current area | One development median per snapshot |
| M2 | Generic early trajectory | Locked early features | Ridge coefficients and intercept |
| M3 | Smooth planar reduced law, sigma = 1/2 | Area history; current area and beta state | None for trajectory; minimal outcome head for final area |
| M4 | Two-thirds reduced law | Area history; current area and beta state | None for trajectory; minimal outcome head for final area |
| M5a | Development-selected common sigma | Area history; current area and beta state | One global sigma chosen within development |
| M5b | Per-event free sigma, exploratory | Area history | Event sigma and beta, with identifiability flags |
| M6 | Flexible empirical upper benchmark | Same origin-safe feature set as M2 | Development-tuned nonlinear model |

M5a should be the primary free-sigma comparison. M5b is exploratory because three early observations leave almost no information for separating sigma and beta, flat days create boundary solutions, and short-window estimates will often be weakly identified.

## Reduced-model estimation

For fixed sigma, define

```text
X = A^(1-sigma)
X(t) = X(0) + (1-sigma) beta t.
```

Estimate a nonnegative slope by ordinary least squares over all pre-origin calendar days and compute

```text
beta_hat = slope / (1-sigma).
```

Anchor forecasts at the observed origin area and use `growth.constant_beta_area` for the forward solution. This matches the existing transformed-trend implementation while exposing beta explicitly.

For M5a, select sigma from a locked grid on development-only forward prediction error. The existing grid result suggests sigma = 0 may be selected. Preserve that negative result if it recurs.

For M5b, profile a bounded sigma grid using pre-origin leave-last-day-out error, require at least five pre-origin observations for a primary estimate, and report profile width, boundary hits, and forecast instability. Day-3 M5b should be marked not identifiable rather than forced.

## Exact experiments

### Experiment 0: exact benchmark reproduction

- Re-run the existing M0/M1/M2 outcome script without code changes.
- Require exact counts and numerical agreement within machine tolerance for all published summary fields.
- Save a benchmark checksum before new model code is used.

### Experiment 1: direct transformed-area continuation

- Origins: days 3, 5, and 7.
- Models: M0, sigma 0, M3, M4, M5a, and M5b where identifiable.
- Fit only through the origin.
- Predict every available post-origin day, with primary common horizons 1, 2, and 3 days and secondary horizons through day 7 after origin.
- Score cumulative-area absolute log error, cumulative-area absolute error, incremental-growth MAE, and increment sMAPE where denominators are defined.
- Average repeated horizons within event before population inference.

### Experiment 2: final-area discrimination

- Evaluate M0, M1, published M2, origin-clean M2, and reduced-state M3/M4/M5 outcome heads on identical events.
- Minimal reduced-state head: intercept plus `log(A_snapshot)` and a documented transformed beta term. No land cover, final duration, future phase, or future geometry.
- M6 receives only the locked origin-safe M2 feature set.
- Report mean and median absolute log error, error factor, log-area R2, log bias, sMAPE, and 90% interval coverage.

### Experiment 3: beta stability

Use exact interval-average transformed rates, not instantaneous derivatives:

```text
beta_i = [A_i^(1-sigma) - A_(i-1)^(1-sigma)] / [(1-sigma) Delta t].
```

For sigma = 2/3 this is three times the daily cube-root-area difference. Report zero-beta fraction, active-interval median, robust MAD/median, early-to-late change, and lag-one persistence only where enough intervals exist. Stratify retrospectively by area fraction, duration fraction, before/after peak mapped growth, active/quiescent interval, final-size class, and land cover. Future-derived strata are interpretation fields only and must be absent from every request sent to a model.

### Experiment 4: explicit failure modes

Lock criteria before held-out scoring. Recommended criteria are:

- final area at least twice the day-5 prediction;
- less than 50% of final area present at day 5; and
- final area above the development-period 90th percentile.

Report all qualifying held-out events, not a hand-picked subset. Compare their beta change, burstiness, quiescent-to-active transitions, observation gaps, and land-cover composition with the remaining validation events.

### Experiment 5: complexity versus performance

For each model record input count, fitted population parameters, event-fitted state dimension, required data sources, fit time, prediction time, and held-out score. Flexible tree-model complexity should be represented by fitted leaves/nodes as well as feature count rather than by a misleading linear-parameter count.

## Fair inference and uncertainty

- All models must share the same event IDs and origins within a target/horizon comparison.
- Bootstrap whole events, never individual daily rows.
- Pairwise comparisons must bootstrap event-level error differences with the same resampled IDs for both models.
- Use deterministic seeds and store bootstrap replicates or sufficient quantiles.
- Use finite-sample split-conformal quantiles on 2013-2015 residuals for new 90% intervals.
- Development-only blocked temporal resampling is used for any hyperparameter or transformation choice.
- Calibration data set interval widths only; it does not choose models.

## Flexible empirical benchmark

No nonlinear machine-learning package is currently declared or installed. A controlled `HistGradientBoostingRegressor`-class benchmark is scientifically justified as M6, but it requires adding scikit-learn. Hyperparameters should be limited to a small predeclared grid and chosen by blocked development-year validation. The benchmark must use the same leakage-clean origin features as M2 and must not trigger a leaderboard-style search.

## Weather feasibility

No weather data are declared inside this repository. An adjacent project contains a 37 GB local GridMET cache for 2000-2021, including VPD, wind speed, precipitation, temperature, ERC, and 100/1000-hour fuel-moisture variables. It is potentially reusable without a new network download, but it is not yet a documented input here and the current environment lacks xarray/netCDF Python dependencies.

Before weather modeling:

1. add a source/license/citation manifest and checksums or a reproducible cache inventory;
2. define point versus footprint aggregation and local-day alignment;
3. permit only values available through the origin date;
4. extract development and calibration features before opening the held-out weather comparison;
5. compare `M2_origin_clean` with exactly the same model plus weather.

## Geometry feasibility

Daily FIRED multipolygons are available, so origin-time geometry is feasible in principle. However, the geometries appear to represent daily additions; cumulative snapshot geometry must be formed by unioning all polygons through the origin. Perimeter convention, holes, disconnected components, raster resolution, and the custom sinusoidal CRS must be fixed before use. GeoPandas, Shapely, and Rasterio are not currently installed, although GDAL command-line tools are present.

Geometry should be a later, separately locked experiment. It must not be approximated from area. Candidate origin-safe variables are exterior perimeter, total perimeter, `P/sqrt(A)`, excess perimeter, aspect ratio, and component count.

## Conventional-model feasibility

The current repository cannot yet make a fair FIRED-versus-ELMFIRE or FIRED-versus-Cell2Fire claim. It lacks event-matched fuels, topography, weather, model initialization, and a verified restart from the observed snapshot. The existing ELMFIRE tutorial run is useful only for adapter development. See `CONVENTIONAL_MODEL_COMPARISON_PLAN.md`.

## Output contract

The requested directory can be produced as:

```text
outputs/fired_model_discrimination/<run_id>/
  event_level_predictions.parquet
  model_summary.csv
  pairwise_model_comparisons.csv
  beta_stability.csv
  sigma_estimates.csv
  trajectory_forecast_scores.csv
  bootstrap_intervals.csv
  failure_mode_events.csv
  run_manifest.json
  claim_ledger.json
  figures/
  report/
```

PyArrow is not currently installed, so Parquet output requires one explicit dependency addition. Every figure and report number must be read from these outputs, never typed into a builder.

## Test plan

Add tests for arbitrary fixed-sigma solutions, one-half and two-thirds transforms, beta estimation, free-sigma boundary behavior, exact benchmark reproduction, partition disjointness, request/response schemas, deterministic bootstrap pairs, split-conformal quantiles, output schemas, complexity table completeness, and claim-ledger synchronization.

Adversarial leakage tests must mutate every post-origin daily increment and cumulative value. Every model request, feature, beta, sigma estimate, and prediction at that origin must remain bitwise or numerically unchanged, while the attached truth and error change. Repeat at days 3, 5, and 7 for every model class.

## Anticipated computational cost

| Stage | Expected cost on current machine |
| --- | --- |
| Attribute-only FIRED reconstruction | Seconds to about one minute from the 548 MB source; seconds from cached sequences |
| Fixed-sigma trajectory predictions | Under one minute for 58,034 daily rows |
| Development-only sigma grid | Minutes, depending on profile grid and bootstrap count |
| M0-M5 final-outcome comparison | Seconds to a few minutes |
| 2,000 event bootstraps and pairwise differences | Several minutes; batch to avoid large temporary arrays |
| M6 blocked development tuning | Minutes with a tightly bounded grid |
| Beta stability and failure-mode summaries | Under a few minutes |
| Full FIRED geometry union/measurement | Likely tens of minutes to hours and substantially larger intermediates |
| GridMET extraction from the 37 GB local cache | Tens of minutes after an indexed extractor is implemented |
| Event-matched ELMFIRE ensemble | Hours to days; not currently runnable from available inputs |

## Decisions requiring review before Stage 2

Recommended defaults are bold.

1. Final-area reduced model: **use a minimal development-fitted outcome head on `(A, beta)`**, while treating fixed-horizon continuation as the primary direct theory test.
2. M2 comparator: retain exact `M2_published` for reproduction and use **`M2_origin_clean` without future-derived dominant land cover** as the primary comparison.
3. Free sigma: use **development-selected common sigma as primary** and per-event sigma as exploratory/identifiability analysis.
4. Flexible model: **add one constrained scikit-learn histogram-gradient-boosting benchmark** after the design file is locked.
5. Parquet: **add PyArrow** so the requested event-level file is genuinely Parquet.
6. Weather: document and inventory the adjacent GridMET cache now, but **defer weather scoring to a separately locked extension**.
7. Geometry: **defer geometry prediction until cumulative-polygon semantics and perimeter conventions are verified**.
8. Conventional model: implement the interface and tutorial adapter first; **make no scientific ELMFIRE claim until event-matched inputs exist**.

Stage 2 should begin only after these choices are accepted or revised.
