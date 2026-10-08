# Figure And Animation Workflow

Use the repository as the reproducible control layer and keep large generated artifacts local.

## Local Workspaces

| Path | Purpose | Git policy |
| --- | --- | --- |
| `data/raw/` | Source data and large external inputs | ignored |
| `data/interim/` | Intermediate tables, rasters, arrays, caches | ignored |
| `data/processed/` | Analysis-ready derived data | ignored |
| `external/` | Local clones/builds of external model software | ignored except `.gitkeep` |
| `outputs/raw/` | Raw outputs from model runs and other heavy workflows | ignored |
| `outputs/figures/` | Static figure exports | ignored |
| `outputs/animations/` | Frames, clips, and rendered animations | ignored |
| `tmp/` | Temporary render checks and scratch artifacts | ignored |

## Recommended Pattern

1. Prototype visual ideas in `notebooks/`.
2. Move repeatable work into `scripts/` once a figure or animation starts to stabilize.
3. Put shared path and utility code in `src/spread_vs_growth/`.
4. Save heavy outputs to `outputs/`.
5. Promote only final, web-sized assets to `docs/assets/`.

## Long Runs

- Make scripts restartable by writing checkpoints or frame batches.
- Record data source, access method, license, and citation needs before adding new data.
- Keep random seeds and major parameter choices visible near the script entry point.
- Prefer small preview renders before committing to full-resolution animation runs.

## Current Animation Utilities

- `scripts/make_side_by_side_video.py` combines the ink diffusion video and slime-mold growth video into one side-by-side, presentation-friendly H.264 MP4 under `outputs/animations/`.
- `scripts/measure_perimeter_growth.py` samples each source video, traces perimeter polygons, and writes area/perimeter time series, log area-vs-perimeter plots, and visual overlays under `outputs/`.
- `scripts/run_fire_model_scaling.py` runs Tier-1 fire-model perimeter-area scaling experiments and writes metrics, fitted exponents, figures, and actual-model status logs under `outputs/`.
- `scripts/make_model_hexbin_plot.py` generates a denser model-output cloud and renders a reference-style log-log hexbin plot under `outputs/figures/`.
- `scripts/animate_grass_fire_two_thirds.py` calibrates and renders a reproducible shallow grass-fire animation with perimeter-area scaling near `P proportional to A^(2/3)`.
- `scripts/reproduce_si.py` verifies the mathematical SI companion, reproduces the seven hypothetical worked examples, and generates explicitly labeled analytical/synthetic figures under `outputs/si_reproduction/`.
- `scripts/run_fired_prediction_tests.py` reconstructs real FIRED daily cumulative-area sequences and runs a training-period/held-out-period short-horizon prediction test under `outputs/fired_prediction/`.
- `scripts/run_fired_outcome_validation.py` predicts final area and duration from early FIRED sequences using separate development, interval-calibration, and held-out periods, and writes grown-fire descriptors under `outputs/fired_outcome_validation/`.
- `scripts/run_fired_lifecycle_prediction.py` adds cumulative polygon geometry, phase, long-fire stratification, and rolling later-area and death-day forecasts under `outputs/fired_lifecycle_prediction/`.
- `scripts/run_fired_state_survival.py` fits state-conditioned terminal-growth hazards and calibrated death-time distributions under `outputs/fired_state_survival/`.
- `scripts/run_fired_persistence_damage.py` tests persistent-regime detection, regime-specific death prediction, growth-derived damage features, and external-termination-like residuals under `outputs/fired_persistence_damage/`.
- `scripts/run_fired_realization_gap.py` compares day-7 persistent-course area forecasts with realized final area and tests gradual versus abrupt terminal-growth signatures under `outputs/fired_realization_gap/`.
- `scripts/extract_fired_gridmet_sequences.py` extracts daily gridMET weather for FIRED event centroids from the documented local cache.
- `scripts/run_fired_missing_process_tests.py` tests past weather, a newly burned-boundary active-front proxy, observed next-day weather as an oracle diagnostic, terminal weather changes, and observation-window sensitivity under `outputs/fired_missing_processes/`.
- `scripts/build_full_prediction_evidence_report.py` assembles the complete empirical and synthetic prediction evidence into `output/pdf/fire_prediction_evidence_report.pdf`.

The SI reproduction layer uses no external wildfire observations. Its claim ledger explicitly separates mathematical checks from empirical hypotheses.

The FIRED prediction layer is the corresponding empirical test. Its raw GeoPackage remains outside git, and `data/fired-source.yml` records the official source, citations, format, access date, reuse uncertainty, and known product limitations.

The first real ELMFIRE constant-wind tutorial output is archived under `outputs/raw/elmfire_constant_wind/`. Cell2Fire has been cloned under `external/Cell2Fire`, but the native build is currently blocked by missing Boost headers.
