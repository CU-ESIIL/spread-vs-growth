# spread-vs-growth

This repository supports figures, animations, and longer-running analyses for a talk comparing wildfire spread rate and growth rate.

The working question is:

> When are wildfire dynamics better understood as spread, and when are they better understood as growth?

The current talk storyboard is **ESA 2026 Fire Metabolism**, a 12-slide sequence that starts from the spread-vs-growth distinction and builds toward a metabolic view of extreme wildfire.

It also contains a reproducible Tier-1 experiment testing whether classical local fire-spread mechanisms generate a perimeter-area relationship:

```text
P ∝ A^sigma
```

The current implemented workflow includes an exact ellipse benchmark, a Huygens wavelet emulator, a level-set emulator, and a cellular-neighbor emulator. A real ELMFIRE constant-wind tutorial run has also been completed and archived under ignored outputs; Cell2Fire has been cloned but its native build is currently blocked by missing Boost headers.

## Repository Layout

```text
docs/                 MkDocs website and project notes
config/               Fire-model scaling experiment configuration
src/fire_model_scaling/ Tier-1 fire-model scaling workflow
src/fire_metabolism/  Mathematical SI companion and evidence-boundary APIs
src/spread_vs_growth/ Shared Python helpers for scripts and notebooks
FireProof/            Lean 4 + Mathlib formal audit of the SI mathematical kernel
scripts/              Reproducible figure and animation entry points
tests/                Geometry, metric, and scaling tests
notebooks/            Exploratory work and draft figure development
data/                 Local data workspace; large contents are ignored
outputs/              Rendered figures, frames, and animations; ignored by git
tmp/                  Temporary renders and inspection artifacts; ignored by git
AGENTS.md             Agent instructions for working in this repository
PROMPT_LOG.md         Prompt-to-change history for substantive agent work
```

Large data files, animation frames, and rendered outputs should stay out of git unless they are intentionally curated for the website under `docs/assets/`.

## Mathematical SI Companion

The `fire_metabolism` package reproduces the mathematical Supplementary Information as identities, conditional derivations, explicit constructions, counterexamples, and hypothetical worked examples. It deliberately does not treat passing algebra or numerical tests as evidence that wildfire has a `2/3` perimeter-area exponent or that wildfire is metabolic.

Run the full reproduction:

```bash
PYTHONPATH=src python scripts/reproduce_si.py
```

Run checks without regenerating the 15 figures:

```bash
PYTHONPATH=src python scripts/reproduce_si.py --check-only
```

The machine-readable evidence ledger is `claims/fire_metabolism_claims.json`; detailed documentation is in `docs/fire-metabolism-math.md`.

### Lean proof audit

`FireProof/` is a separate Lean 4 + Mathlib project that adversarially checks the SI's mathematical implication chain. It distinguishes definitions, empirical premises, named axioms, proved identities, stronger-assumption results, and false-as-stated inferences.

```bash
cd FireProof
lake build
bash scripts/audit.sh
```

The audit contains no `sorry` or `admit`. Its only custom scientific axiom is the explicitly named moving-boundary identity; the claims ledger and scientific interpretation are in `FireProof/CLAIMS_AUDIT.md` and `FireProof/SCIENTIFIC_SUMMARY.md`.

The second-stage adversarial analysis asks which predictions are unique and
falsifiable. It adds formal peak-balance, dimensionless-regime,
non-identifiability, and competing-mechanism results plus a deterministic
750-run stress test. Start with `FireProof/SECOND_STAGE_SUMMARY.md`; the full
prediction and empirical-test audits are in `FireProof/PREDICTIONS.md` and
`FireProof/EMPIRICAL_TESTS.md`.

The final synthesis is in `FireProof/SYNTHESIS.md`. Its authoritative model
specification, manuscript-ready language, evidence hierarchy, and section-level
SI handoff are `THEORY_CORE.md`, `MANUSCRIPT_CLAIMS.md`,
`PREDICTION_HIERARCHY.md`, and `SI_REVISION_MAP.md` in the same directory.

## FIRED Prediction Test

The repository also includes a leakage-resistant retrospective forecast test on published FIRED CONUS+Alaska daily sequences. It calibrates each forecast from the previous four calendar days, selects any free exponent on 2001-2015 events, and reports final performance only on held-out 2016-2020 events.

```bash
PYTHONPATH=src python scripts/run_fired_prediction_tests.py \
  --fired-gpkg /path/to/fired_conus-ak_daily_nov2001-march2021.gpkg
```

The raw GeoPackage stays outside git. Source, citation, reuse uncertainty, and product limitations are recorded in `data/fired-source.yml`; method details are in `docs/fired-prediction.md`.

The companion grown-fire validation predicts final area and duration from observations through event days 3, 5, and 7, with a later calibration period and untouched 2016-2020 test events:

```bash
PYTHONPATH=src python scripts/run_fired_outcome_validation.py
```

Results and interpretation are documented in `docs/fired-outcome-validation.md`.

The geometry-informed life-cycle workflow then measures cumulative FIRED perimeter and tests later-area, growth-peak, final-area, and death-day predictions using development, calibration, and held-out years:

```bash
/opt/homebrew/bin/python3 scripts/extract_fired_geometry_sequences.py \
  --fired-gpkg /path/to/fired_conus-ak_daily_nov2001-march2021.gpkg
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  python scripts/run_fired_lifecycle_prediction.py
```

Its day-5 acceleration test and prediction results are documented in `docs/fired-lifecycle-prediction.md`.

The follow-on state-survival experiment treats death as a daily terminal-transition hazard and produces calibrated predictive intervals:

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  python scripts/run_fired_state_survival.py
```

Results are documented in `docs/fired-state-survival.md`.

The current interpretation report can be rebuilt with `scripts/build_fired_prediction_report.py`. The staged next experiment is specified in `MODEL_DISCRIMINATION_AUDIT.md`, with conventional-spread feasibility in `CONVENTIONAL_MODEL_COMPARISON_PLAN.md`.

Rebuild the current manuscript figures as publication-size PNG, PDF, and SVG assets:

```bash
PYTHONPATH=src python scripts/remake_manuscript_figures.py
```

This produces four manuscript remakes and a fifth synthetic robustness/prediction diagnostic under `outputs/manuscript_figures/`. The workflow exports all Figure 4 trajectories and Figure 5 forecast records; see `docs/manuscript-figures.md` for the evidentiary labels and interpretation.

The Figure 4 two-thirds metabolic closure is derived and checked step by step in `notebooks/09_first_principles_fire_life_cycle.ipynb`.

Build the complete computational Supplementary Information as one PDF:

```bash
PYTHONPATH=src python scripts/build_computational_si_pdf.py
```

The resulting 32-page document is written to `output/pdf/fire_metabolism_computational_si.pdf`.

## Fire-Model Scaling Workflow

Run tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

Run the Tier-1 model-scaling workflow:

```bash
python scripts/run_fire_model_scaling.py
```

Primary outputs:

```text
outputs/metrics/fire_model_scaling_metrics.csv
outputs/tables/scaling_fits.csv
outputs/tables/fixed_exponent_scores.csv
outputs/tables/local_slopes.csv
outputs/tables/actual_model_status.csv
outputs/figures/figure2_loglog_perimeter_area.png
outputs/figures/figure3_sigma_by_model.png
outputs/figures/presentation_fire_model_geometry.png
outputs/logs/package_versions.json
outputs/logs/elmfire_attempt.log
outputs/logs/cell2fire_attempt.log
outputs/raw/elmfire_constant_wind/
```

The Tier-1 fitted-scaling results are mechanism-emulator outputs except for the exact ellipse benchmark. They test local propagation geometry, but they are not a substitute for actual ELMFIRE, WRF-SFIRE, FARSITE, FlamMap, or Cell2Fire software runs.

Actual-software tier status:

- ELMFIRE: real tutorial 01 constant-wind case completed from `https://github.com/lautenberger/elmfire`; outputs copied to `outputs/raw/elmfire_constant_wind/`.
- Cell2Fire: native C++ build attempted from `https://github.com/cell2fire/Cell2Fire`; build failed because Boost headers were unavailable.

Conceptual caveat: a local front-propagation equation does not mathematically guarantee `sigma = 1/2` under all heterogeneous, anisotropic, fragmented, or time-varying conditions. `sigma = 1/2` is the expected result when growth is approximately self-similar or shape-preserving. This experiment tests whether classical model implementations retain that geometry or generate increasing boundary complexity.

Current preliminary interpretation from the Tier-1 run: the exact ellipse, Huygens emulator, and cellular emulator cluster near `sigma = 1/2`; the level-set emulator is near `1/2` for homogeneous cases but can move toward higher apparent exponents in the deliberately heterogeneous scenario. Do not treat this as a claim about actual ELMFIRE or Cell2Fire until those software outputs are wired into the same perimeter-area measurement workflow.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Preview The Website

```bash
mkdocs serve
```

Then open:

```text
http://127.0.0.1:8000
```

The published site is configured for:

```text
https://cu-esiil.github.io/spread-vs-growth/
```
