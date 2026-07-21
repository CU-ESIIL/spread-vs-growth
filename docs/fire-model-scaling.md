# Fire Model Scaling

This workflow tests whether classical local fire-spread mechanisms produce:

```text
P proportional to A^sigma
```

where `P` is exterior fire perimeter and `A` is burned area.

## Implemented Tier

Current Tier-1 implementations:

- exact expanding ellipse benchmark
- Huygens wavelet front-propagation emulator
- Eulerian level-set front-propagation emulator
- cellular-neighbor spread emulator

Actual-software status is recorded in `outputs/tables/actual_model_status.csv` and logs under `outputs/logs/`.

Current actual-software status:

- ELMFIRE: real tutorial 01 constant-wind case completed from `https://github.com/lautenberger/elmfire`. Raw outputs are copied to `outputs/raw/elmfire_constant_wind/`.
- Cell2Fire: native C++ build attempted from `https://github.com/cell2fire/Cell2Fire`; build failed because Boost headers were unavailable.

## Run

```bash
PYTHONPATH=src python -m unittest discover -s tests
python scripts/run_fire_model_scaling.py
```

## Outputs

- `outputs/metrics/fire_model_scaling_metrics.csv`
- `outputs/tables/scaling_fits.csv`
- `outputs/tables/fixed_exponent_scores.csv`
- `outputs/tables/local_slopes.csv`
- `outputs/figures/figure2_loglog_perimeter_area.png`
- `outputs/figures/figure3_sigma_by_model.png`
- `outputs/figures/presentation_fire_model_geometry.png`

## Interpretation Guardrail

A local front-propagation equation does not guarantee `sigma = 1/2` under all heterogeneous, anisotropic, fragmented, or time-varying conditions. `sigma = 1/2` is expected when growth is approximately self-similar or shape-preserving. The experiment tests whether each implementation retains that geometry or generates increasing boundary complexity.

The current Tier-1 fitted-scaling results should be read as mechanism-emulator results. The real ELMFIRE tutorial output exists, but it has not yet been wired into the same perimeter-area measurement workflow. Do not describe the Tier-1 fits as actual ELMFIRE, WRF-SFIRE, FARSITE, FlamMap, or Cell2Fire outputs.
