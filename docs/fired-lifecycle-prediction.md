# FIRED Life-Cycle Prediction

This workflow tests whether observed perimeter-area geometry and the two-thirds metabolic framing improve prediction of later burned area, peak-growth timing, and fire death in real FIRED sequences.

## Validation Design

- Development: ignition years 2001-2012 (2,316 events).
- Hyperparameter and phase calibration: 2013-2015 (552 events).
- Untouched test: 2016-2020 (1,164 events).
- Snapshot days: 3, 5, 7, 10, 14, and 21.
- Later-area horizons: 1, 3, 5, and 7 days after each snapshot, plus final area.
- Largest fires: final area above `126.54 km2`, the 90th percentile estimated from development years only.
- Death: the last day with a positive FIRED detected-area increment.
- Acceleration-cessation proxy: the day of maximum three-day-smoothed detected daily growth.

The growth-peak definition is deliberately an observation-level proxy. It is not a claim that MODIS detects instantaneous physical acceleration or that the last assigned burn date is an incident-control declaration.

## Observed Geometry

Daily FIRED multipolygons are cumulatively unioned in their projected sinusoidal coordinate system. The workflow measures:

- total boundary length, including interior holes;
- exterior boundary length;
- component and hole counts; and
- cumulative polygon area for reconciliation with FIRED's area attributes.

The median absolute polygon/attribute area difference is `0.25%`. Perimeter remains resolution- and convention-dependent because the source is derived from approximately 500 m MODIS pixels. Cumulative mapped perimeter is also not equivalent to independently observed active fireline length.

## Mechanism Features

The geometry/metabolic models receive only data available through the snapshot day. Features include:

- early cumulative-area and daily-growth summaries;
- observed log perimeter-area slopes;
- excess perimeter relative to a circle;
- `dA/dt / A^(2/3)` and `dA/dt / A^(1/2)` diagnostics;
- detected area growth per unit cumulative boundary;
- recent perimeter contraction or expansion;
- component and hole changes;
- recent acceleration, curvature, active-day fraction, and time since detected growth; and
- dominant natural-vegetation land-cover class.

These are empirical predictors motivated by the reduced life-cycle equations. The workflow does not assume the cumulative FIRED perimeter is active perimeter or force the exponent to equal `2/3`.

## Day-5 Hypothesis

The largest-fire result replicates across the temporal partitions:

| Partition | Events above development top-decile cutoff | Median growth-peak day | Fraction peaking after day 5 | 95% interval |
| --- | ---: | ---: | ---: | ---: |
| Development | 232 | 6 | 55.6% | 49.2-61.9% |
| Calibration | 47 | 7 | 61.7% | 47.4-74.2% |
| Held-out test | 141 | 6 | 62.4% | 54.2-70.0% |

Thus most of the largest held-out fires peak after day 5, but day 5 is not a deterministic transition. In the held-out top decile, the 25th, 75th, and 90th percentiles of the smoothed peak day are 4, 10, and 22 days.

## Held-Out Prediction

At the day-5 snapshot, the best tested model varies by target.

| Target | Best tested model | Held-out result |
| --- | --- | ---: |
| Area 1 day later | Day-5 phase ridge | Typical error factor 1.33x |
| Area 3 days later | Day-5 phase ridge | Typical error factor 1.40x |
| Area 5 days later | Geometry/metabolic ridge | Typical error factor 1.42x |
| Area 7 days later | Geometry/metabolic ridge | Typical error factor 1.46x |
| Final area | Geometry/metabolic ridge | Typical error factor 1.58x |
| Growth-peak day | Geometry/metabolic analog | 2.31 days MAE; 86.9% day-5 classification accuracy |
| Death day | Geometry/metabolic ridge | 4.04 days MAE; 40.2% within two days |

The geometry/metabolic ridge improves day-5 final-area prediction over the area-only ridge (`1.58x` versus `1.76x` typical error factor). A recent constant-`2/3` cube-root extrapolation overpredicts badly at longer horizons, showing that the time-varying prefactor or phase state matters more than the exponent alone.

## Largest-Fire Limitation

The phase-calibrated model helps the largest fires but does not solve them. For the held-out top decile at day 5:

- final-area typical error factor is `2.81x`;
- death-day MAE is `7.92` days;
- death is underpredicted by `6.81` days on average.

Large, long-lived fires therefore remain the critical failure set. Weather, fuel moisture, suppression, topography, and explicit active-fire observations are likely necessary to make death timing operationally precise.

## Much Longer Fires

Fire duration is even more diagnostic than final size. Duration groups are defined from the development period rather than the held-out data: the 75th, 90th, and 95th percentiles of last-growth day are days 17, 22, and 29. The held-out results are:

| Observed last-growth day | Events | Median growth-peak day | Peak after day 5 | Median final area | Day-5 death MAE | Day-5 final-area error factor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Through day 17 | 889 | 5 | 45.6% | 20.18 km2 | 2.46 days | 1.42x |
| Days 18-21 | 130 | 9 | 84.6% | 29.73 km2 | 4.69 days | 1.64x |
| Days 22-28 | 96 | 12 | 93.8% | 52.81 km2 | 8.67 days | 2.47x |
| Day 29 or later | 49 | 22 | 93.9% | 148.54 km2 | 21.86 days | 4.50x |

The last two columns use the geometry/metabolic ridge. Its death forecasts for the longest group are biased early by `21.86` days on average. This is not a small calibration miss: at day 5 these fires resemble more ordinary fires closely enough that a pooled model regresses them toward ordinary lifetimes.

The useful distinction is forecast horizon. For fires lasting at least 29 days, day-5 geometry predicts area seven days later with a `1.92x` typical error factor, while eventual final area has a `4.50x` factor. Geometry therefore retains near-term trajectory information, but a fixed day-5 snapshot does not identify eventual death. Long-fire prediction should be reframed as a rolling survival or hazard problem that updates daily and permits renewed acceleration, ideally with weather, fuel moisture, suppression, and active-fire observations.

The rolling-snapshot test confirms that recommendation. For the 145 held-out fires lasting at least 22 days, geometry/metabolic death-day MAE falls from `13.13` days at day 5 to `4.60` days at day 21, while final-area error falls from `3.03x` to `1.29x`. For the 49 fires lasting at least 29 days, death-day MAE falls from `21.86` to `8.95` days and final-area error from `4.50x` to `1.59x`. Long fires are not intrinsically unpredictable, but their eventual outcome is not identifiable from day 5 alone.

## Reproduce

Extract cumulative geometry with the GDAL-enabled Python installed by Homebrew:

```bash
/opt/homebrew/bin/python3 scripts/extract_fired_geometry_sequences.py \
  --fired-gpkg /path/to/fired_conus-ak_daily_nov2001-march2021.gpkg
```

Then run the temporally held-out prediction experiment:

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  python scripts/run_fired_lifecycle_prediction.py
```

Outputs under `outputs/fired_lifecycle_prediction/` include complete geometry, feature, prediction, calibration, outcome, duration-stratified, rolling-update, and summary tables; six QA figures; and a machine-readable run report.

Sources: [Balch et al. 2020](https://doi.org/10.3390/rs12213498), [Mahood et al. 2022](https://doi.org/10.1038/s41597-022-01572-3), and the [FIREDpy repository](https://github.com/earthlab/firedpy).
