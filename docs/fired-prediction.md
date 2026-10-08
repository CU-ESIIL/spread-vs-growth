# FIRED Prediction Test

This workflow tests short-horizon cumulative-area forecasts against real daily fire sequences from the published FIRED CONUS+Alaska product.

## Question

Given the cumulative burned area observed through today, does a local growth law

```text
dA/dt = beta A^sigma
```

predict cumulative area one, two, or three days later? The comparison includes no growth, linear area (`sigma = 0`), diffusion-like spread (`sigma = 1/2`), organized growth (`sigma = 2/3`), and an exponent selected using training years only.

## Prediction Design

- Training events: ignition years 2001-2015.
- Held-out test events: ignition years 2016-2020.
- Calibration at each forecast origin: the previous four calendar days only.
- Forecast horizons: one, two, and three days.
- Primary score: mean absolute log prediction error, first averaged within event and then across events.
- Uncertainty: 95% bootstrap intervals resampling whole events.
- Sensitivity subsets: all targets, targets with observed future growth, and origins with detected growth on the forecast day.

The transformed trend is anchored at the observed area on the forecast day. For a fixed exponent, `A^(1-sigma)` is fit as a local linear trend and extrapolated without access to future observations. Missing observation dates within a FIRED event are inserted as zero detected growth before cumulative area is calculated.

## Event Filter

The default run retains events with:

- final mapped area of at least 10 square kilometers;
- duration from 8 to 60 calendar days;
- at least four detected growth days;
- a complete first event day; and
- daily increments that reproduce reported final area within 1%;
- an area-weighted dominant IGBP natural vegetation class (forest, shrubland, savanna, or grassland).

This removes cropland and urban classes but does not establish that every retained event is an unplanned wildfire.

## Run

Place the published daily GeoPackage at the path documented in `data/fired-source.yml`, set `FIRED_DAILY_GPKG`, or pass the source explicitly:

```bash
PYTHONPATH=src python scripts/run_fired_prediction_tests.py \
  --fired-gpkg /path/to/fired_conus-ak_daily_nov2001-march2021.gpkg
```

Outputs under `outputs/fired_prediction/` include the reconstructed sequences, all held-out forecasts, summary scores, exponent-selection curve, figures, and a source/checksum run report.

## Current Result

The reproducible run dated 2026-09-27 retained 4,032 complete event sequences: 2,868 training events and 1,164 held-out test events, yielding 167,220 test predictions across models and horizons. Training selected `sigma = 0` independently for the one-, two-, and three-day horizons.

Event-balanced mean absolute log errors on all held-out targets were:

| Model | 1 day | 2 days | 3 days |
| --- | ---: | ---: | ---: |
| No growth | **0.183** | 0.354 | 0.509 |
| Linear area (`sigma = 0`) | 0.187 | **0.328** | **0.448** |
| Diffusion-like (`sigma = 1/2`) | 0.218 | 0.393 | 0.556 |
| Organized growth (`sigma = 2/3`) | 0.240 | 0.446 | 0.650 |

Persistence is narrowly best at one day when all targets, including zero-detection days, are scored. Linear area is best at two and three days and is also best at every horizon when scoring only targets with observed future growth (0.210, 0.335, and 0.450). In this local temporal extrapolation test, the `sigma = 1/2` and `sigma = 2/3` models tend to overpredict and do not outperform linear area. This result tests cumulative-area trajectories through time; it does not directly test the perimeter-area exponent used elsewhere in this project.

Exact confidence intervals, alternative error metrics, and sensitivity subsets are in `outputs/fired_prediction/forecast_summary.csv`. The run report records the 548 MB source file's SHA-256 checksum as `added786e5741f835c4277b38478f446c1bb7269596998ad2ddda482cb59bf62`.

## Interpretation Boundary

This is a retrospective test of satellite-derived burned-area sequences, not an operational fire-spread forecast. FIRED derives day-to-day progression from MODIS MCD64A1 burned dates at approximately 500 m resolution. The short-horizon scores therefore reflect both fire dynamics and the observation process, including days with no newly assigned burned pixels.

Sources: [Balch et al. 2020](https://doi.org/10.3390/rs12213498), [Mahood et al. 2022](https://doi.org/10.1038/s41597-022-01572-3), and the [FIREDpy repository](https://github.com/earthlab/firedpy).
