# FIRED Grown-Fire Outcome Validation

This workflow asks whether the first few days of a real FIRED sequence describe the fire it ultimately becomes. It predicts final mapped area and total mapped duration using observations available through event day 3, 5, or 7.

## Validation Design

- Model development: ignition years 2001-2012 (2,316 events).
- Prediction-interval calibration: 2013-2015 (552 events).
- Untouched validation: 2016-2020 (1,164 events).
- Point models: no future growth, a historical median multiplier, and ridge regression on early trajectory features.
- Uncertainty: 90% residual intervals calibrated on later events than those used to fit the models.
- Event filters and sequence reconstruction are identical to the [short-horizon FIRED test](fired-prediction.md).

The early-trajectory predictors are cumulative area, first-day area, mean and recent growth, fraction of active days, recent growth as a fraction of observed area, peak growth, log-area slope, and dominant land-cover class. No measurement after the snapshot day is included in a predictor.

## Held-Out Results

The early-trajectory model outperformed both baselines at every snapshot.

| Information through | Final-area mean absolute log error | Typical area error factor | Log-area R2 | Duration MAE |
| --- | ---: | ---: | ---: | ---: |
| Day 3 | 0.706 | 2.03x | 0.21 | 4.32 days |
| Day 5 | 0.563 | 1.76x | 0.43 | 4.24 days |
| Day 7 | 0.412 | 1.51x | 0.64 | 4.06 days |

For comparison, the historical-median final-area errors were 1.33, 1.04, and 0.65 at days 3, 5, and 7. Day-5 early-trajectory area intervals covered 85.2% of test events against a nominal 90%, so they are modestly under-dispersed. Duration interval coverage was 90.8%, but duration R2 remained only 0.15: duration is weakly predictable even when average absolute error improves.

## Description of the Grown Fires

Among the held-out fires, median final mapped area was 23.4 square kilometers and median duration was 13 days. The median fire had accumulated 9% of final area by day 3, 37% by day 5, and 69% by day 7. Half of final mapped area was typically accumulated by 50% of event duration, 90% by 75% of duration, and peak daily growth occurred at 46% of duration. Peak daily growth was typically 3.66 times mean growth on active days, demonstrating strongly pulsed rather than smooth daily accumulation.

These statistics describe the filtered FIRED population: natural-vegetation events lasting 8-60 days and reaching at least 10 square kilometers. They should not be generalized to all ignitions without accounting for that conditioning.

## Reproduce

First create the reconstructed sequence file, then run:

```bash
PYTHONPATH=src python scripts/run_fired_outcome_validation.py
```

Outputs under `outputs/fired_outcome_validation/` include every held-out prediction and interval, event-level grown-fire statistics, grouped descriptive summaries, validation metrics, figures, and a machine-readable run report.
