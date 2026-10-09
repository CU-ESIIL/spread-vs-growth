# SI Empirical Handoff

## Purpose

This document identifies exactly which adversarial-validation results can be
incorporated into the Supplementary Information. It distinguishes held-out
empirical evidence, retrospective diagnostics, synthetic controls, and
currently untestable claims.

The SI should cite the fixed design and machine-readable files under
`outputs/adversarial_validation/`. It should not describe the geometry proxy as
the canonical latent coherence-fuel model.

## Methods paragraph ready for adaptation

We evaluated 4,032 complete daily FIRED sequences using ignition years
2001-2012 for development, 2013-2015 for calibration, and 2016-2020 for fixed
held-out evaluation. Geometric indicators used only mapped area and cumulative
polygon geometry available through prespecified event-day snapshots. Forecast
models excluded final area, duration, future perimeter, future weather,
future-derived dominant land cover, and reconstructed latent coherence.
Continuous errors and pairwise differences were bootstrapped by whole event.
Probability thresholds, free exponents, regularization, and 90% interval
widths were selected using pretest years only. FIRED endpoints and growth rates
were interpreted as retrospective satellite-mapping quantities rather than
physical combustion or incident-control states.

## Claims that can be added

### Claim SI-E1: a near-two-thirds mapped geometric pattern is recurrent

- **Claim:** Exterior mapped perimeter-area trajectories frequently have
  slopes compatible with `2/3`, but compatibility is neither universal nor a
  discrete coherent-state label.
- **Supporting analysis:** uncertainty-aware rolling log-log fits; fixed
  `1/2` versus `2/3` residual comparison.
- **Figure/table:** Figure 1; `detection_summary.csv`.
- **Numerical result:** At day 7, 42.2% of 1,058 eligible held-out fires meet
  the geometric rule; median slope is 0.650. Only 15.4% have detections at both
  day 5 and day 7.
- **Assumptions:** Mapped exterior perimeter is measured consistently; at
  least five positive-detection polygons and a twofold area span are required.
- **Limitations:** Cumulative mapped perimeter is not active fireline;
  sensitivity and specificity for latent coherence cannot be calculated.
- **Evidence classification:** **PARTIALLY SUPPORTED**.

### Claim SI-E2: geometric detection depends on the observation operator

- **Claim:** Apparent two-thirds regime identification is sensitive to
  perimeter convention and temporal sampling.
- **Supporting analysis:** exterior versus total perimeter and every-other
  observation fits.
- **Figure/table:** Figure 2; `detection_robustness.csv`.
- **Numerical result:** Day-7 held-out detection is 42.2% using exterior and
  44.2% using total perimeter. Thinning leaves too few observations for the
  five-point rule at day 7; at day 10 detection falls from 49.2% to 23.8%.
- **Assumptions:** The minimum-information rule is held fixed.
- **Limitations:** All polygons originate from one approximate 500 m product;
  true spatial-resolution sensitivity remains untested.
- **Evidence classification:** **SUPPORTED** as an observation-sensitivity
  result.

### Claim SI-E3: origin-time mapped geometry improves future-area prediction

- **Claim:** Perimeter and topology add future-growth information beyond the
  same mapped area and recent-growth history.
- **Supporting analysis:** paired held-out geometry-proxy versus dynamics-ridge
  forecasts.
- **Figure/table:** Figures 3 and 5; `forecast_metrics.csv` and
  `paired_model_comparisons.csv`.
- **Numerical result:** From day 7, geometry reduces mean absolute log error by
  0.017, 0.064, 0.076, and 0.077 at one-, three-, five-, and seven-day
  horizons. Paired 95% intervals are 0.011-0.023, 0.051-0.078, 0.057-0.095,
  and 0.052-0.101, respectively.
- **Assumptions:** Predictor whitelists are origin-safe; all models share
  identical event-horizon samples.
- **Limitations:** The cohort is retrospectively selected; mapped morphology
  is not uniquely attributable to coherence.
- **Evidence classification:** **SUPPORTED** as predictive association.

### Claim SI-E4: a single two-thirds detector flag is not the predictive signal

- **Claim:** The full mapped geometry predicts better than reducing geometry
  to a binary two-thirds regime indicator.
- **Supporting analysis:** geometry-indicator, geometry-proxy, and
  dynamics-ridge comparison.
- **Figure/table:** Figure 5; `paired_model_comparisons.csv`.
- **Numerical result:** At day 7 and seven days ahead, the full geometry gain
  is 0.077 log-error units, while the binary indicator gain is 0.011.
- **Assumptions:** Both candidate models share the same recent-dynamics input.
- **Limitations:** The richer model cannot isolate which morphological feature
  carries causal information.
- **Evidence classification:** **SUPPORTED**.

### Claim SI-E5: fixed two-thirds temporal growth is rejected as a forecast

- **Claim:** Constant-forcing `dA/dt proportional to A^(2/3)` does not provide
  the best short-horizon continuation of FIRED mapped area.
- **Supporting analysis:** fixed `1/2`, fixed `2/3`, recent-linear, and
  calibration-selected free-exponent forecasts.
- **Figure/table:** Figure 5; `forecast_metrics.csv`.
- **Numerical result:** Calibration selects `sigma=0` at every origin and
  horizon. At day 7 and seven days ahead, two-thirds error is 0.988 versus
  0.732 for one-half and 0.578 for recent-linear prediction. Its paired excess
  over one-half is 0.257 (95% interval 0.227-0.286).
- **Assumptions:** Event-specific transformed trends use only pre-origin area.
- **Limitations:** This rejects the constant-local-forcing temporal forecast,
  not the perimeter-area geometry or a time-varying two-state model.
- **Evidence classification:** **NOT SUPPORTED**.

### Claim SI-E6: geometry predicts future mapped acceleration sign

- **Claim:** Origin-time mapped geometry improves three-day acceleration-sign
  prediction beyond recent trajectory dynamics.
- **Supporting analysis:** held-out ridge-logistic classification with paired
  event bootstrap.
- **Figure/table:** Figure 4; `transition_metrics.csv` and
  `paired_transition_comparisons.csv`.
- **Numerical result:** At day 7, geometry balanced accuracy is 0.790 (95%
  interval 0.763-0.818), sensitivity 0.794, specificity 0.785, and precision
  0.715. The paired improvement over dynamics is 0.098 (0.063-0.134).
- **Assumptions:** Future acceleration means next-three-day mean mapped growth
  exceeds prior-three-day mean mapped growth.
- **Limitations:** This is not instantaneous physical acceleration or a test of
  the canonical `Psi` equation.
- **Evidence classification:** **PARTIALLY SUPPORTED**.

### Claim SI-E7: geometry detects elevated near-term peak-transition risk

- **Claim:** Geometry improves discrimination of a positive-to-nonpositive
  smoothed growth-rate crossing in the next three days.
- **Supporting analysis:** explicitly sign-changing peaks; no stationary point
  is counted without a sign change.
- **Figure/table:** Figure 4; transition metric and paired comparison tables.
- **Numerical result:** At day 7, balanced accuracy is 0.791 (0.735-0.843), a
  paired improvement of 0.062 (0.005-0.114). Precision is only 0.224 because
  there are 67 positives among 1,058 fires.
- **Assumptions:** Three-day smoothing and lead window are fixed before held-out
  scoring.
- **Limitations:** There are 177 false alarms for 51 true positives; this is a
  risk indicator, not precise peak timing.
- **Evidence classification:** **PARTIALLY SUPPORTED**.

### Claim SI-E8: early termination remains a major failure

- **Claim:** Geometry and state models modestly improve ordinary-fire endpoint
  prediction but do not predict persistent-fire termination precisely from
  early snapshots.
- **Supporting analysis:** existing endpoint ridge and state-survival models.
- **Figure/table:** Figure 4 right panel; existing
  `state_survival_summary.csv`.
- **Numerical result:** Day-7 all-fire death MAE is 3.81 days for the geometry
  endpoint ridge versus 4.83 for the historical median. For fires eventually
  lasting at least 22 days, day-5 geometry death MAE is 13.13 days with a
  -13.12-day bias; updating at day 21 lowers MAE to 4.60 days.
- **Assumptions:** Death is the final positive FIRED mapped increment.
- **Limitations:** Outcome-defined persistent-fire subsets are retrospective;
  the endpoint is not physical extinction.
- **Evidence classification:** **NOT SUPPORTED** for precise early
  termination.

### Claim SI-E9: coarse past weather does not resolve the remaining gap

- **Claim:** Adding the available coarse past weather does not materially
  improve area forecasts beyond mapped geometry.
- **Supporting analysis:** geometry versus geometry-plus-weather paired
  comparison at day 7.
- **Figure/table:** `paired_model_comparisons.csv`.
- **Numerical result:** At seven days ahead the weather error difference is
  -0.001, with 95% interval -0.015 to 0.013. Acceleration balanced accuracy
  improves by 0.010, with interval -0.009 to 0.029.
- **Assumptions:** Weather variables use only dates through the origin.
- **Limitations:** Weather is sampled at a future-footprint centroid and is
  therefore a sensitivity analysis, not a clean operational weather model.
- **Evidence classification:** **NOT SUPPORTED**.

## Claims that must not be added as empirical support

### Independent coherence detection

**Classification: NOT IDENTIFIABLE.** FIRED does not contain an independent
whole-fire coherence label or true active perimeter. Do not report geometric
detector sensitivity, specificity, or accuracy against a label derived from
the same exponent.

### Canonical forcing closure

**Classification: NOT IDENTIFIABLE.** `C` and prospective `Amax` are absent.
Do not reconstruct them from realized growth and call the result validation.

### Suppression or fuel-restriction attribution

**Classification: NOT IDENTIFIABLE.** Abrupt and unrealized-growth signatures
are compatible with both explanations plus weather, barriers, observation
error, and model misspecification.

### Energetic metabolism

**Classification: NOT YET TESTED.** Area growth is not chemical power. No
independent fuel consumption, heat release, or radiative-energy record is used
here.

### Operational spread-model superiority

**Classification: NOT YET TESTED.** No event-matched ELMFIRE or Cell2Fire
forecasts exist. Existing emulators and tutorial output are not operational
comparisons.

## Proposed SI placement

1. Add the geometric detector and observation-operator sensitivity after the
   perimeter-area section.
2. Add the leakage-resistant forecast comparison after the reduced growth-law
   derivation.
3. Add acceleration, sign-changing peak, and termination results to the
   life-cycle section.
4. Add mechanism identifiability and missing measurements before the empirical
   claims summary.
5. Place synthetic counterexamples in a validation appendix, clearly labeled
   as software and construct tests.

## Reproducibility manifest

- Pipeline: `scripts/run_adversarial_validation.py`
- Reusable functions: `src/fire_metabolism/adversarial_validation.py`
- Tests: `tests/test_fire_metabolism_adversarial_validation.py`
- Locked design: `outputs/adversarial_validation/design_lock.json`
- Run summary: `outputs/adversarial_validation/run_report.json`
- Evidence table: `outputs/adversarial_validation/evidence_classification.csv`
- Figures: `outputs/adversarial_validation/figure1_detection.*` through
  `figure6_theory_failure_map.*`

All six figures are exported as PDF, SVG, and publication-resolution PNG.
