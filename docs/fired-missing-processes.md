# FIRED Missing-Process Tests

This analysis turns several proposed omissions from the perimeter-area theory into explicit held-out tests. It asks whether recent coarse weather, a satellite-derived active-front proxy, or the FIRED observation window explains the remaining persistent-fire prediction error.

## Design

The models use the same temporal split as the other FIRED analyses:

- development: 2001-2012;
- calibration: 2013-2015;
- held-out evaluation: 2016-2020.

All operational day-7 features use information available through day 7. Recent weather is extracted from gridMET at the nearest cell to each final-footprint centroid and includes vapor pressure deficit, 10 m wind speed, 100-hour fuel moisture, energy release component, and precipitation. The active-front proxy uses the exterior perimeter of newly detected daily burned polygons relative to cumulative exterior perimeter.

An additional model receives observed day-8 weather. This is an intentionally optimistic oracle diagnostic, not a deployable forecast.

## Results

Adding the active-front proxy and past weather produced modest gains:

- persistent-regime AUC increased from 0.801 to 0.822;
- final-area typical error changed from 1.405x to 1.398x;
- persistent-fire death-day MAE changed from 13.13 to 12.57 days.

Observed next-day weather did not close the gap: AUC was 0.820, final-area error was 1.396x, and persistent death-day MAE was 12.51 days. One extra weather day is therefore not sufficient to explain the long-fire tail.

Terminal changes in the five gridMET variables did not distinguish gradual from abrupt early-ending candidates after Holm correction. This negative result applies to daily, approximately 4-km centroid weather; it does not exclude fire-scale gusts, within-fire gradients, terrain-channelled winds, or subdaily transitions.

The abrupt-ending enrichment persisted under four definitions based on the last 2, 3, or 5 calendar days and the last 3 positive-detection days. Odds ratios ranged from 2.95 to 6.07, so the signal is not created by one arbitrary terminal window.

## What Remains Missing

- **Forward fuel connectivity:** reachable fuels, prior burns, roads, water, and topographic barriers.
- **Observed active fireline:** thermal fronts or incident-scale active-edge mapping rather than a burned-polygon proxy.
- **Fire-scale forcing:** spatial weather histories and genuine forecast weather.
- **Suppression exposure:** resource timing, tactics, treatment, and containment records.
- **Observation model:** explicit sensor detection likelihood and fusion across perimeter products.

Fuel restriction and suppression remain plausible explanations for the potential-to-realization gap, but FIRED cannot identify either cause by itself.

## Reproduction

```bash
/opt/homebrew/bin/python3 scripts/extract_fired_gridmet_sequences.py
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  .venv/bin/python scripts/run_fired_missing_process_tests.py
PYTHONPATH=src .venv/bin/python scripts/build_full_prediction_evidence_report.py
```

Machine-readable results and figures are under `outputs/fired_missing_processes/`. Data provenance and reuse uncertainty are recorded in `data/gridmet-source.yml`.
