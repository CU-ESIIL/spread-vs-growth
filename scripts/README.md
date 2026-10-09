# Scripts

Put repeatable figure and animation entry points here.

Scripts should write bulky renders to `outputs/` and keep final web-ready assets under `docs/assets/` only when they are intentionally part of the website.

## Side-by-side source video

```bash
python scripts/make_side_by_side_video.py
```

The default render places the ink diffusion clip on the left and the slime-mold timelapse on the right, writing `outputs/animations/ink_vs_slime_mold.mp4`.

By default, the script renders a standard `1920x1080` H.264 MP4 for better compatibility with QuickTime, browsers, and presentation software.

## Perimeter and area measurements

```bash
python scripts/measure_perimeter_growth.py
```

The script samples stages from the ink diffusion and slime-mold videos, traces the largest foreground perimeter polygon, and writes:

- `outputs/measurements/perimeter_area_timeseries.csv`
- `outputs/measurements/perimeter_polygons.json`
- overlay PNGs in `outputs/figures/perimeter_overlays/`
- log area-vs-perimeter graph at `outputs/figures/log_area_vs_perimeter.png`

## Fire-model scaling experiments

```bash
PYTHONPATH=src python -m unittest discover -s tests
python scripts/run_fire_model_scaling.py
```

The workflow runs the exact ellipse benchmark plus Huygens, level-set, and cellular emulators. It writes perimeter-area metrics, scaling fits, comparison figures, and status logs for actual ELMFIRE and Cell2Fire attempts.

## Dense model hexbin plot

```bash
python scripts/make_model_hexbin_plot.py
```

This longer figure run generates a dense cloud of homogeneous and anisotropic model outputs, then renders a reference-style log-log hexbin plot at `outputs/figures/model_outputs_hexbin.png`. Use `--reuse-metrics` to redraw from `outputs/metrics/model_hexbin_metrics.csv` without rerunning the emulators.

To add rougher model-output variance, include explicit heterogeneity strengths and write a separate figure:

```bash
python scripts/make_model_hexbin_plot.py \
  --output-name model_outputs_hexbin_more_heterogeneity \
  --heterogeneity-levels 0.25 0.5 0.75
```

To isolate one model from an existing dense metrics table:

```bash
python scripts/make_model_hexbin_plot.py \
  --output-name level_set_hexbin_more_heterogeneity \
  --input-metrics outputs/metrics/model_outputs_hexbin_more_heterogeneity_metrics.csv \
  --heterogeneity-levels 0.25 0.5 0.75 \
  --reuse-metrics \
  --models level_set_emulator
```

To compare everything except the level-set emulator, list the other model ids:

```bash
python scripts/make_model_hexbin_plot.py \
  --output-name no_level_set_hexbin_more_heterogeneity \
  --input-metrics outputs/metrics/model_outputs_hexbin_more_heterogeneity_metrics.csv \
  --heterogeneity-levels 0.25 0.5 0.75 \
  --reuse-metrics \
  --models exact_ellipse huygens_emulator cellular_emulator
```

Add `--hide-high-reference-lines` to omit the `2/3` and `3/4` reference lines while keeping the `1/2` and fitted-slope lines.

## Model hexbin reveal animation

```bash
python scripts/animate_model_hexbin_reveal.py
```

This renders the no-level-set heterogeneous model outputs as a left-to-right reveal animation, starting with no visible model data and ending with the full model cloud. The default output is `outputs/animations/no_level_set_hexbin_reveal.mp4`, a `1920x1080`, 30 fps, 8-second H.264 MP4 that keeps only the `1/2` reference line and fitted model-cloud slope.

## Reference-line-only animation

```bash
python scripts/animate_reference_lines_only.py
```

This renders a data-free log-log reference animation with only the red `P proportional to A^(1/2)` and blue `P proportional to A^(2/3)` lines. The red line is present from the first frame, and the blue line draws on from left to right. The default output is `outputs/animations/reference_lines_red_blue_only.mp4`, a `1920x1080`, 30 fps, 6-second H.264 MP4.

## Add two-thirds line to event image

```bash
python scripts/add_two_thirds_line_to_image.py --source path/to/event_hexbin.png
```

This overlays the blue `P proportional to A^(2/3)` reference line onto an existing log-log event-hexbin PNG. The default output is `outputs/figures/event_hexbin_with_blue_two_thirds.png`.

## Model-run handoff dataset

```bash
python scripts/export_model_run_dataset.py
```

This packages the dense heterogeneous model outputs into `outputs/datasets/model_hexbin_handoff/`, including one complete CSV, separate level-set and non-level-set CSVs, a fit summary, data dictionary, manifest, and zip archive for handoff to another plotting workflow.

## Grass-fire two-thirds animation

```bash
python scripts/animate_grass_fire_two_thirds.py
```

This calibrates and renders a deterministic grassland fire animation whose measured perimeter-area scaling is near `P proportional to A^(2/3)`. Outputs are written to `outputs/grass_fire_two_thirds/`, including diagnostic and clean MP4s, a final frame, scaling plot, metrics CSV, accepted parameters JSON, and an output README.

## Fire context explainer animation

```bash
python scripts/animate_fire_contexts_explainer.py
```

This reuses the accepted two-thirds fire-growth footprint and renders a flatter perspective explainer across grassland, forest, and WUI ground planes. The default output is `outputs/grass_fire_two_thirds/grass_forest_wui_growth_explainer.mp4`, with a final frame and metadata JSON beside it.

## Mathematical SI reproduction

```bash
PYTHONPATH=src python scripts/reproduce_si.py
```

This checks the mathematical companion, reproduces all seven hypothetical Section S19 examples, and generates 15 figures under `outputs/si_reproduction/`. Every figure is visibly labeled as analytical, synthetic, or hypothetical. Use `--check-only` to run the checks and update the machine-readable report without regenerating figures.

Build the complete computational Supplementary Information as one PDF:

```bash
PYTHONPATH=src python scripts/build_computational_si_pdf.py
```

The combined PDF is written to `output/pdf/fire_metabolism_computational_si.pdf` and includes the full mathematical chain, all figures, worked examples, counterexamples, claim ledger, and reproducibility appendix.

## FIRED held-out prediction tests

```bash
PYTHONPATH=src python scripts/run_fired_prediction_tests.py \
  --fired-gpkg /path/to/fired_conus-ak_daily_nov2001-march2021.gpkg
```

This reconstructs gap-free cumulative burned-area sequences from the published FIRED daily product, selects any free exponent on 2001-2015 events, and evaluates one- to three-day forecasts on held-out 2016-2020 events. Outputs are written to `outputs/fired_prediction/`, including compressed sequence and prediction tables, bootstrap summaries, figures, and a source-checksum report.

## FIRED grown-fire outcome validation

```bash
PYTHONPATH=src python scripts/run_fired_outcome_validation.py
```

This uses the reconstructed sequences to predict final area and duration from event days 3, 5, and 7. Models are developed on 2001-2012 events, prediction intervals are calibrated on 2013-2015 events, and accuracy is evaluated on untouched 2016-2020 events. Event-level grown-fire descriptors and validation outputs are written to `outputs/fired_outcome_validation/`.

Build the interpreted seven-page validation report:

```bash
PYTHONPATH=src python scripts/build_fired_prediction_report.py
```

The report is written to `output/pdf/fired_prediction_validation_report.pdf` and reads every reported value from the machine-readable validation outputs.

## FIRED geometry and life-cycle prediction

Extract cumulative polygon area, total perimeter, exterior perimeter, components, and holes for the eligible FIRED sequences:

```bash
/opt/homebrew/bin/python3 scripts/extract_fired_geometry_sequences.py \
  --fired-gpkg /path/to/fired_conus-ak_daily_nov2001-march2021.gpkg
```

Then test the day-5 acceleration hypothesis and compare area-only, geometry/metabolic, empirical-analog, and phase-calibrated life-cycle forecasts:

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  python scripts/run_fired_lifecycle_prediction.py
```

The workflow preserves development (2001-2012), calibration (2013-2015), and held-out test (2016-2020) partitions. Outputs under `outputs/fired_lifecycle_prediction/` include complete geometry, features, predictions, tuning curves, event outcomes, duration-stratified summaries, QA figures including long-fire failure modes, and a run report.

## FIRED state-survival prediction

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  python scripts/run_fired_state_survival.py
```

This converts endpoint death prediction into a discrete-time terminal-transition hazard conditioned on accelerating, declining, quiescent, and reactivated states. It compares state-only and geometry-plus-state hazards with the existing endpoint models on the same temporal partitions, then exports full death-time distributions, split-conformal 90% intervals, long-fire discrimination, summaries, and QA figures under `outputs/fired_state_survival/`.

## FIRED missing-process tests

Extract the local gridMET time series, then test weather, active-front, and observation-process additions:

```bash
/opt/homebrew/bin/python3 scripts/extract_fired_gridmet_sequences.py
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  .venv/bin/python scripts/run_fired_missing_process_tests.py
```

The held-out comparison preserves the 2001-2012 development, 2013-2015 calibration, and 2016-2020 evaluation split. It compares geometry plus state with a newly burned-boundary proxy, past gridMET weather, both additions, and an explicitly non-operational observed next-day-weather oracle. Retrospective diagnostics test terminal weather changes and sensitivity to the definition of abrupt termination. Outputs are written to `outputs/fired_missing_processes/`.

## Adversarial FIRED validation

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  .venv/bin/python scripts/run_adversarial_validation.py
```

This reuses the cached FIRED sequences, cumulative geometry, and weather
features to test geometric regime stability, future-area forecasts,
acceleration sign, sign-changing peak transitions, termination evidence, and
synthetic counterexamples. Predictor whitelists exclude future-derived land
cover and outcome columns. The full run uses 2,000 whole-event bootstrap
replicates and exports machine-readable predictions, metrics, calibration,
subgroup robustness, an evidence classification, and six figures under
`outputs/adversarial_validation/`.

For a deterministic end-to-end check:

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  .venv/bin/python scripts/run_adversarial_validation.py \
  --smoke --output-dir outputs/adversarial_validation_smoke
```

## Effective coupling validation

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  .venv/bin/python scripts/run_effective_coupling_validation.py
```

This constructs the start-of-day observable coefficient
`K_obs = daily_area / prior_area^(2/3)`, compares coupling-history,
area-dynamics, mapped-geometry, and flexible models on the locked temporal
split, and recursively propagates predicted coupling into future area. Use
`--reuse-primary` to resume downstream summaries from a completed primary
prediction table. Outputs are written to
`outputs/effective_coupling_validation/`.

## Geometric attractor validation

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  .venv/bin/python scripts/run_geometric_attractor_validation.py
```

This selects a local perimeter-area slope estimator on development/calibration
data and tests held-out restoring dynamics toward `2/3` against persistence,
`1/2`, population-mean, free-equilibrium, flexible, measurement-error,
random-walk, within-fire, and observation-rule alternatives. It exports all
local states, transitions, model and null results, long-fire return summaries,
coupling and boundary associations, and PDF/SVG/400-dpi PNG figures under
`outputs/geometric_attractor_validation/`. Add `--smoke` for a deterministic
300-fire end-to-end check.

## Integrated geometry and transport validation

Run the restartable geospatial extraction in an environment containing
GeoPandas, Shapely, Rasterio, and PyArrow, then run the statistical integration:

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  ../cubedynamics/.venv/bin/python scripts/extract_fired_transport_metrics.py

MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  ../cubedynamics/.venv/bin/python scripts/run_integrated_geometry_transport.py
```

The extractor reads the existing cached FIRED daily polygon GeoPackage without
copying it into this repository. It constructs area-matched isotropic-dilation
nulls, computes balanced sliced and KL-relaxed unbalanced transport, records
ordinary shape metrics, and writes a Parquet transition table. The integration
stage reuses the locked attractor outputs and temporal split, tests the proposed
geometry-to-R-to-restoration chain, evaluates future coupling and area through
49 days, runs paired whole-fire comparisons, and builds the primary and
long-fire figures under `outputs/integrated_geometry_transport/`.

## Within-between geometric scaling validation

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  ../cubedynamics/.venv/bin/python scripts/run_geometric_manifold_validation.py
```

This separates population, between-fire, within-fire, fire-specific, and local
perimeter-area scaling in the locked FIRED cohort. It includes whole-fire
bootstrap intervals, a random-intercept/random-slope meta-analytic model,
candidate-normalization tests, flexible power-law checks, perimeter and cadence
sensitivities, synthetic reconciliation, normalized-state prediction, and
algorithmically selected held-out examples. Outputs are written to
`outputs/geometric_manifold_validation/`; use `--smoke` for a small end-to-end
check.

## Latent constraints and exponent discrimination

```bash
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=src \
  ../cubedynamics/.venv/bin/python scripts/run_latent_constraint_validation.py

MPLCONFIGDIR=/tmp/mpl PYTHONPATH=src \
  ../cubedynamics/.venv/bin/python scripts/run_half_vs_two_thirds_constraint_test.py
```

The first command learns expected future growth from past-only development and
calibration states, detects negative realization residuals, evaluates deficit
hazards, termination association, OT timing, and shock-robust attractor fits.
The second performs the held-out falsification test asking whether those
residuals explain one-half's advantage over two-thirds. Both write Parquet/CSV
data, design locks, reports, and PDF/SVG/400-dpi PNG figures.

## Empirical detection and prediction figures

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  .venv/bin/python scripts/build_detection_prediction_figures.py
```

This presentation-only build reads the locked adversarial-validation CSVs and
cached past trajectories; it does not refit models. It writes the detection
and prediction figures to `output/manuscript/` as 600-dpi PNG, vector PDF, and
SVG files. The same directory receives publication-ready captions, exact
plotted source-data tables, the reproducibly selected trajectory examples,
and a manifest with all input SHA-256 checksums. Use `--dpi` or `--output-dir`
to override the publication raster resolution or destination.

## Manuscript figure remakes

```bash
PYTHONPATH=src python scripts/remake_manuscript_figures.py
```

This rebuilds the four figures in the current *Fire Critter* manuscript and adds a fifth synthetic life-cycle validation panel. Outputs are written to `outputs/manuscript_figures/` as 400-dpi PNG, vector PDF, and SVG files. Figure 4 derives area, active perimeter, metabolic rate, fuel, connectivity, matching efficiency, and edge coupling from the two-thirds closure `dA/dt = beta_0 C F eta A^(2/3)` and a mass-action connectivity equation. The same run exports complete trajectory and forecast CSVs plus a reproducibility manifest.

Use `--dpi`, `--validation-runs`, and `--seed` to change the raster resolution, ensemble size, or deterministic seed.

Build the first-principles Figure 4 proof and validation handoff as one SI-ready PDF:

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  python scripts/build_first_principles_si_handoff_pdf.py
```

The 25-page report is written to `output/pdf/first_principles_fire_life_cycle_si_handoff.pdf`. It contains the complete derivation, canonical parameters and stages, exact closure checks, five QA plots, phase-specific forecast statistics, a 1,000-run robustness and sensitivity analysis, SI-ready Methods and Results text, every notebook code cell, the production model implementation, the QA routines, and the defining tests.
