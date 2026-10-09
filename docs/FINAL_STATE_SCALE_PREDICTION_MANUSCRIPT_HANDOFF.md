# Final State, Scale, and Prediction Manuscript Handoff

## Section 3.2

FIRED mapped perimeter-area geometry is measurement- and scale-dependent.
Within-fire exterior-perimeter scaling is approximately `0.595` in held-out
fires, but rises under temporal thinning, differs for total perimeter, changes
across lifecycle and area, and depends on estimator and error scale. No
independent spatial-resolution experiment is available. Fixed normalized
geometry variables from `1/2` through `3/4` are predictively equivalent after
conditioning on area and recent area change; two-thirds is not privileged.
The phrase **mapped geometric state** is nevertheless warranted for the full
multivariate set of perimeter, excess perimeter, topology, and recent boundary
change because it predicts future outcomes beyond current size, dynamics, raw
perimeter, or one normalized coordinate. It does not identify latent
coherence, metabolism, fuel restriction, suppression, or another cause.

The locked contemporaneous deficit-detection task is weak. Recent dynamics
rank a rare three-day major deficit better than chance, but full geometry does
not improve average precision. The manuscript should not claim that geometry
reliably detects suppression or fuel limitation from FIRED trajectories.

## Section 3.3

Mapped geometric state reproducibly improves held-out future-area prediction.
Relative to area and recent dynamics, event-weighted skill is `7.4%` at one
day, peaks at `14.2%` at five days, is `13.3%` at seven days, and remains about
`10.5%` at 42 days. At seven days, mean absolute log-area error is `0.525` for
area plus dynamics, `0.504` after adding perimeter or any fixed normalized
coordinate, and `0.455` for full geometry. Full geometry also improves
realized-coupling and acceleration-sign forecasts. Near-term deficit and
termination probabilities improve more modestly, and termination becomes
uninformative at long horizons because nearly all fires have ended in the
mapped sequence.

Prior spatial reorganization adds predictive information in a smaller
matched subset, but this should remain an SI result pending broader coverage.
Longer-range operational prediction will require future environmental inputs,
especially reachable fuel, fire-scale weather, barriers, and suppression.

## Figure X

**Title:** Current mapped geometry predicts future fire growth but does not improve detection of current deficits

**Panel A:** Held-out precision-recall curves for contemporaneous detection of
the fixed major realized-growth deficit over event days 8-10. The endpoint
day-10 features are current observations, not prospective predictors. Recent
dynamics have average precision `0.154`; raw perimeter, development-normalized
geometry, and full geometry have `0.105`, `0.106`, and `0.086`.

**Panel B:** Event-weighted future mapped-area skill relative to area plus
recent dynamics. Raw perimeter and `Z_0.595` overlap. Full geometry reaches
`13.3%` skill at seven days and about `10.5%` at 42 days.

**Caption:** **Figure X. Current mapped geometry predicts future fire growth
but does not improve detection of current deficits.** (A) Precision-recall
curves for 773 held-out FIRED fires (2016-2020) detecting the locked major
negative realization residual over the three-day interval ending at event day
10. Models use endpoint area and recent dynamics, then add raw perimeter, the
development-locked `Z_0.595`, or full mapped geometry. Because endpoint
features include the measured interval, this is contemporaneous detection,
not prediction; the dashed line is held-out prevalence. (B) Held-out skill for
future mapped area at the ten prespecified horizons, calculated as one minus
event-weighted mean absolute log-area error relative to the area-plus-dynamics
model. Lines add raw perimeter, normalized geometry, or full geometry; bands
are 95% paired intervals from 1,000 whole-fire bootstrap replicates. All model
regularization and detection thresholds were selected using 2001-2015 data.
Spatial reorganization is excluded from the main panels because its coverage
is smaller; its contemporaneous and prospective roles are reported separately
in SI. Geometry provides predictive information but does not uniquely identify
a physical mechanism.

### Exact MAIN values

| Quantity | Value |
| --- | ---: |
| Detection prevalence | 0.0556 |
| Dynamics detection ROC AUC / average precision | 0.619 / 0.154 |
| Full-geometry detection ROC AUC / average precision | 0.611 / 0.086 |
| Seven-day area MAE: dynamics / perimeter / full geometry | 0.525 / 0.504 / 0.455 |
| Seven-day full-geometry skill | 13.3% |
| Seven-day full minus perimeter loss | -0.0487 (-0.0573 to -0.0394) |
| Forty-two-day full-geometry skill | 10.5% |

## SI

1. Full fixed-normalization comparison for every target and horizon.
2. Raw perimeter versus normalized geometry versus full state.
3. Detection ROC and precision-recall curves.
4. Detection calibration.
5. Prediction performance for every validated target and horizon.
6. Geometric scale-dependence audit.
7. Held-out fire and prediction-origin sample sizes.
8. Whole-fire bootstrap distributions for key paired improvements.
9. Matched-subset prior-OT comparisons, clearly separated from same-interval contemporaneous OT.
10. Machine-readable provenance for every plotted series.

