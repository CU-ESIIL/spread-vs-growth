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
src/spread_vs_growth/ Shared Python helpers for scripts and notebooks
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
