# FIRED Potential-To-Realization Gap

This analysis tests the hypothesis that perimeter-area geometry and dynamic state describe a persistent growth course, while fuel restriction, weather, barriers, and suppression determine how much of that course is realized.

## Persistent-Course Proxy

The day-7 persistent-course area forecast is fit only to development-period fires lasting at least 22 days and tuned only on calibration-period persistent fires. It is an empirical upper-course proxy. It is not a physical maximum, a mapped fuel-constrained capacity, or a counterfactual estimate of unsuppressed area.

The realization fraction is:

```text
observed final area / persistent-course final-area forecast
```

Among held-out high-confidence fires:

- 71 fires predicted to be persistent but ending early realized a median 40.8% of the persistent course.
- 46 fires predicted persistent and observed persistent realized a median 115.7%.
- The median difference was -75.0 percentage points, with bootstrap 95% CI -113.8 to -28.4 percentage points.
- The realization distributions differed strongly (`p = 1.58e-7`, Mann-Whitney test).

## Terminal Signatures

Terminal growth is the mean area increment during the final three mapped days divided by peak three-day smoothed growth.

- Gradual-decline-like: terminal growth at or below 10% of peak.
- Abrupt-truncation-like: terminal growth at or above 25% of peak.
- Intermediate: between those thresholds.

Early-ending candidates were 46.5% gradual, 16.9% intermediate, and 36.6% abrupt. High-confidence true persistent fires were 73.9% gradual, 17.4% intermediate, and 8.7% abrupt. The odds of an abrupt signature were 6.07 times higher among early-ending candidates (`p = 0.00093`, Fisher exact test), and the enrichment remained present across abrupt thresholds from 15% to 35% of peak growth.

## Interpretation

The results support a distinction between persistent growth potential and realized outcome. They also suggest more than one restriction mechanism:

- gradual decline is compatible with fuel exhaustion, progressive barriers, worsening weather, or sustained suppression;
- abrupt truncation is compatible with hard boundaries, abrupt weather change, decisive suppression, observation truncation, or model error.

FIRED alone cannot identify suppression or distinguish it causally from fuel restriction. The candidate events should be linked to fuel continuity, prior burns, roads and water, weather changes, and suppression-resource histories.

## Reproduction

```bash
PYTHONPATH=src .venv/bin/python scripts/run_fired_realization_gap.py
PYTHONPATH=src .venv/bin/python scripts/build_full_prediction_evidence_report.py
```

Machine-readable outputs are under `outputs/fired_realization_gap/`.
