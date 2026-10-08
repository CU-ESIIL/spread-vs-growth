# FIRED Persistence, Damage, And Early Termination

This analysis asks whether a persistent fire regime can be detected from past-only geometry and state, whether regime separation improves death-day prediction, whether a biological accumulated-damage analogy adds information, and whether unusually early termination can be identified for later data linkage.

## Design

- Development years: 2001-2012.
- Calibration years: 2013-2015.
- Held-out years: 2016-2020.
- Persistent regime: death day at or above day 22, the development-period 90th percentile.
- High confidence: predicted persistence at or above the calibration-period 90th percentile.
- Death: last day with positive FIRED detected-area increment, not physical extinction or an incident-control declaration.

## Main Results

- Geometry plus state distinguishes persistent fires with held-out AUC 0.704 on day 5 and 0.801 on day 7.
- High-confidence precision rises from 28.6% on day 5 to 84.0% on day 14, while sensitivity remains below 32% at each snapshot.
- Among true persistent fires, the pooled day-5 death model has 13.13-day MAE. A retrospective persistent-only model reduces this to 6.33 days, showing that regime recognition is the main bottleneck.
- An operational probability blend improves persistent-fire day-5 MAE to 11.10 days but cannot realize the oracle gain because early regime classification is imperfect.
- Damage features based only on the observed growth law add almost no independent discrimination or death-timing skill.

## Damage Interpretation

For `dA/dt = beta A^(2/3)`, several natural exposure integrals are transformed versions of the existing area trajectory:

- cumulative metabolism is proportional to area gained;
- specific metabolic exposure is proportional to `log(A/A0)`;
- integrated `beta` is proportional to `A^(1/3) - A0^(1/3)`.

The biological analogy may still be useful, but a predictive damage state must add information not already contained in area growth, such as fuel depletion, heat exposure, weather stress, active-edge loss, suppression, or forward fuel connectivity.

## Suppression-Like Residuals

The workflow exports fires predicted to be persistent that terminate substantially earlier than the persistent-course model expects. These are candidates for linkage to incident and suppression records, not suppression labels. Weather transitions, barriers, fuel discontinuity, observation error, and model misspecification remain viable explanations.

## Reproduction

```bash
PYTHONPATH=src .venv/bin/python scripts/run_fired_persistence_damage.py
PYTHONPATH=src .venv/bin/python scripts/build_full_prediction_evidence_report.py
```

Machine-readable outputs and figures are under `outputs/fired_persistence_damage/`.
