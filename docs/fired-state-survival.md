# FIRED State-Survival Prediction

This experiment tests whether a state-conditioned survival model improves prediction of the FIRED last-growth day. It preserves the life-cycle theory's `A^(2/3)` geometry while treating fire death as a daily terminal-transition probability rather than a directly regressed endpoint.

## Design

- Development: ignition years 2001-2012.
- Hazard and interval calibration: 2013-2015.
- Untouched test: 2016-2020.
- Landmark snapshots: days 3, 5, 7, 10, 14, and 21.
- Eligible source sequences: FIRED events lasting 8-60 days with at least four detection days, matching the existing prediction dataset.
- Death: last day with a positive FIRED detected-area increment.
- Long fire: death on or after day 22, the development-period 90th percentile.
- Extreme duration: death on or after day 29, the development-period 95th percentile.

Every event contributes one at-risk row for each future day through its observed death. Ridge-regularized logistic hazards are fitted on development fires. The ridge penalty and one global hazard-logit shift are selected using calibration years. A split-conformal absolute-error radius from those same calibration years supplies nominal 90% death-day intervals.

## Observed States

States are past-only observation proxies:

- accelerating: detected growth on the snapshot day with positive recent smoothed acceleration;
- declining: detected growth without positive recent acceleration;
- quiescent: no detected growth on the snapshot day, but the event remains in the at-risk sequence; and
- reactivated: detected growth immediately after a zero-growth day.

These are not independently measured combustion states. They test whether a modest state representation helps before adding weather, active-fireline observations, or forward fuel connectivity.

Because the source prediction dataset excludes fires shorter than eight days, this experiment addresses medium-to-long FIRED events rather than all detected fires. At snapshots after day 7, evaluation is additionally conditional on the event still being in the FIRED risk set.

At day 5, accelerating fires have a median 10 remaining days and an 18.9% probability of entering the development-defined long-fire group. Declining fires have a median 6 remaining days and a 9.6% long-fire probability. Reactivated fires are intermediate at 8 days and 15.3%. State therefore contains real prognostic information, but the classes overlap strongly.

## Held-Out Results

| Day-5 model | Death-day MAE | Bias | Within 2 days | 90% interval coverage | Median interval width |
| --- | ---: | ---: | ---: | ---: | ---: |
| Historical median endpoint | 4.83 d | -2.58 d | 38.1% | n/a | n/a |
| Geometry endpoint ridge | **4.04 d** | -1.26 d | 40.2% | n/a | n/a |
| State empirical survival | 4.77 d | -2.68 d | 43.0% | 90.3% | 17 d |
| State hazard | 4.71 d | -2.49 d | 42.7% | 89.4% | 17 d |
| Geometry + state hazard | 4.26 d | -1.86 d | **49.3%** | 90.2% | 15 d |

The geometry-state hazard does not beat endpoint regression on overall day-5 MAE. It does produce a complete predictive distribution, valid marginal coverage, and substantially more predictions within two days.

For fires lasting at least 22 days, the day-5 geometry-state median has 15.12 days MAE, versus 13.13 days for endpoint regression. Its distribution mean reduces that to 12.57 days, showing that the survival distribution contains some long-tail probability even when its median remains too early.

By day 21, the geometry-state hazard becomes the strongest tested long-fire point predictor:

| Day-21 long-fire model | Death-day MAE | Within 2 days |
| --- | ---: | ---: |
| Geometry endpoint ridge | 4.60 d | 37.2% |
| Geometry + state hazard | **4.23 d** | **60.7%** |

## Long-Fire Discrimination

Using the survival distribution's mean as a risk score, the geometry-state model discriminates fires lasting at least 22 days with AUC `0.71` at day 5 and `0.80` at day 7. For the 29-day tail, AUC is `0.72` at day 5 and `0.88` by day 21. Early geometry contains a moderate ranking signal, but not enough separation for a precise early death date.

The nominal 90% intervals also expose the missing regime. Day-5 coverage is 90.2% overall but only 24.1% among 22-day fires and 0% among 29-day fires. Split-conformal calibration is marginal, not subgroup-conditional; ordinary fires dominate the calibration distribution.

## Interpretation

Changing the statistical target from endpoint regression to survival does not solve early long-fire prediction by itself. It improves uncertainty representation, near-death decisions, and within-two-day accuracy, but the day-5 long-fire tail remains systematically underestimated.

This result narrows the missing physics. The next state model needs variables that separate future trajectories at the same observed area and perimeter:

1. active-edge length reconstructed from consecutive daily polygons rather than cumulative mapped perimeter;
2. burnable fuel and barriers immediately ahead of that active edge;
3. time-varying wind and fuel-moisture forcing in the theoretical `eta(t)` term;
4. component births and spotting as a source or reactivation process; and
5. suppression and an explicit observation model for satellite non-detection.

## Reproduce

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  python scripts/run_fired_state_survival.py
```

Outputs under `outputs/fired_state_survival/` include all held-out predictive distributions, tuning records, state prognosis, duration-discrimination summaries, aggregate metrics, three QA figures, and a machine-readable run report.
