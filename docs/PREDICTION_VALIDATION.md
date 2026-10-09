# Fire Critter Prediction Validation

> **Latent-constraint update.** Geometry and recent dynamics modestly improve
> the Brier score for lower-decile future growth deficits (`0.0866` versus
> `0.0905` for a constant hazard). Using that hazard as a point correction does
> not improve long horizons: at 42 days, mean absolute log-area error is `0.605`
> for the geometry mixture versus `0.559` for unadjusted expected growth.

## Question and information boundary

This analysis asks whether origin-time mapped geometry predicts subsequent
FIRED area growth and life-cycle transitions better than alternatives given
the same area and recent-growth history.

The empirical Fire Critter candidate is a **geometry proxy model**, not the
canonical latent two-state model. The canonical model requires independent
coherence and prospective reachable fuel, which FIRED does not provide.

No primary predictor uses final area, future perimeter, future weather,
observed duration, future phase, or the future-derived dominant land-cover
class. All models are developed on 2001-2012, regularization and thresholds are
chosen on 2013-2015, and scores use 2016-2020. The validation years have been
seen in earlier repository analyses, so this is a fixed external rerun rather
than a pristine first opening of the test set.

## Models

| Model | Origin information |
| --- | --- |
| No growth | Current cumulative area |
| Recent growth | Current area and trailing mean daily increment |
| Half-power | Pre-origin area history under `dA/dt = beta A^(1/2)` |
| Two-thirds | Pre-origin area history under `dA/dt = beta A^(2/3)` |
| Free exponent | Same history; one common exponent selected on calibration only |
| Area ridge | Area and coarse recent-growth summaries |
| Dynamics ridge | Area plus acceleration, quiescence, beta-history, and curvature summaries |
| Flexible dynamics | Fixed quadratic/interacting basis of the same dynamics predictors |
| Geometry proxy | The dynamics predictors plus mapped perimeter, excess perimeter, topology, and their changes |
| Geometric indicator | Dynamics predictors plus only the uncertainty-aware detector flags |
| Geometry plus weather | Geometry proxy plus past coarse weather and a new-boundary proxy at day 7 |

The weather sensitivity is not fully operational: gridMET was sampled at the
completed fire's centroid. Weather values are pre-origin, but the sampling
location uses future footprint information.

## Future-area prediction

The primary score is mean absolute log error, which can be interpreted as
typical multiplicative error after exponentiation. Every comparison uses the
same fires. Confidence intervals resample whole fires, and 90% prediction
intervals are calibrated only on 2013-2015 residuals.

### Day-7 origin

| Horizon | Recent growth | `A^(1/2)` | `A^(2/3)` | Dynamics ridge | Flexible dynamics | Geometry proxy | Past weather |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 day | 0.157 | 0.222 | 0.266 | 0.140 | 0.137 | **0.122** | 0.122 |
| 3 days | 0.347 | 0.472 | 0.596 | 0.281 | 0.280 | **0.217** | 0.216 |
| 5 days | 0.489 | 0.625 | 0.812 | 0.386 | 0.390 | 0.310 | **0.307** |
| 7 days | 0.578 | 0.732 | 0.988 | 0.443 | 0.443 | 0.366 | **0.365** |

The weather differences are numerically tiny and not resolved by paired
uncertainty. They should not be interpreted as a weather benefit.

### Paired geometry increment

Geometry-proxy error minus equally informed dynamics-ridge error is:

| Origin | Horizon | Mean paired difference | 95% event-bootstrap interval |
| ---: | ---: | ---: | ---: |
| Day 5 | 1 day | -0.039 | -0.050 to -0.029 |
| Day 5 | 3 days | -0.091 | -0.109 to -0.074 |
| Day 5 | 5 days | -0.114 | -0.141 to -0.088 |
| Day 5 | 7 days | -0.099 | -0.132 to -0.065 |
| Day 7 | 1 day | -0.017 | -0.023 to -0.011 |
| Day 7 | 3 days | -0.064 | -0.078 to -0.051 |
| Day 7 | 5 days | -0.076 | -0.095 to -0.057 |
| Day 7 | 7 days | -0.077 | -0.101 to -0.052 |

All intervals exclude zero. Mapped geometry therefore adds reproducible
short-horizon information beyond area and equally rich recent dynamics in this
retrospectively selected FIRED cohort.

This does **not** show that a `2/3` state was detected. The small geometric
indicator model is nearly tied with the dynamics baseline. At day 7 and seven
days ahead its gain is only 0.011 log-error units, compared with 0.077 for the
full geometry. Perimeter magnitude, topology, boundary change, and excess
perimeter contain information that a single exponent flag discards.

### Fixed exponent test

Calibration selects `sigma = 0` for every origin and horizon. The fixed
two-thirds temporal model is worse than the half-power model in every paired
comparison. At day 7 and seven days ahead, its error exceeds the half-power
error by 0.257 log units (95% interval 0.227-0.286) and exceeds recent-linear
prediction by 0.410 (0.344-0.474).

Thus `P proportional to A^(2/3)` and `dA/dt proportional to A^(2/3)` cannot be
treated as interchangeable empirical claims. The mapped geometric pattern can
coexist with temporal area dynamics that strongly reject a constant-forcing
two-thirds extrapolation.

### Interval calibration

At the day-7 origin, geometry-proxy 90% interval coverage is 87.6%, 90.8%,
87.7%, and 87.5% at one-, three-, five-, and seven-day horizons. The intervals
are slightly under-covering at most horizons. Point-error improvements should
not be presented as fully calibrated operational uncertainty.

## Future acceleration

Future acceleration is defined prospectively as mean mapped growth over the
next three days exceeding mean growth over the prior three days. This is an
observation-level sign target, not instantaneous physical acceleration.

At day 7:

| Model | Sensitivity | Specificity | Precision | Balanced accuracy | 95% interval | Brier score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Acceleration persistence | 0.367 | 0.798 | 0.552 | 0.583 | 0.550-0.615 | 0.233 |
| Area ridge | 0.579 | 0.796 | 0.658 | 0.688 | 0.655-0.718 | 0.197 |
| Dynamics ridge | 0.551 | 0.833 | 0.690 | 0.692 | 0.662-0.724 | 0.193 |
| Geometry proxy | 0.794 | 0.785 | 0.715 | **0.790** | 0.763-0.818 | 0.146 |
| Geometry plus weather | 0.845 | 0.755 | 0.701 | 0.800 | 0.773-0.828 | 0.141 |

The paired geometry improvement over dynamics is 0.098 balanced-accuracy
units (95% interval 0.063-0.134). The weather increment over geometry is 0.010
(-0.009 to 0.029), so it is unresolved.

Reliability bins show useful probability ordering but imperfect calibration,
especially for the persistence rule. Exact bins are in
`transition_calibration.csv`.

## Peak transition

An observed peak requires a positive-to-nonpositive sign change in the
three-day-smoothed mapped growth rate. The task predicts whether that crossing
will occur in the next three days; a stationary point without the sign change
is not counted.

At day 7, the event is rare: 67 of 1,058 fires have a qualifying crossing in
the next three days. The geometry proxy yields:

- sensitivity 0.761;
- specificity 0.821;
- precision 0.224;
- balanced accuracy 0.791 (95% interval 0.735-0.843); and
- Brier score 0.050.

Geometry improves balanced accuracy over dynamics by 0.062 (paired 95%
interval 0.005-0.114). However, it generates 177 false alarms for 51 true
positives. The model detects elevated transition risk; it does not predict
peak timing precisely enough for an unqualified claim.

## Termination

The existing state-survival analysis remains the appropriate endpoint test.
At day 7, held-out death-day MAE is:

- 4.83 days for the historical median;
- 3.81 days for the geometry/metabolic endpoint ridge; and
- 3.86 days for the geometry-state hazard.

For fires eventually lasting at least 22 days, the day-5 geometry endpoint MAE
is 13.13 days with a -13.12-day bias. At day 21 it improves to 4.60 days.
Termination is therefore updateable but not precisely inferable early,
especially for persistent fires.

FIRED's last positive mapped increment is an observation-product endpoint. It
does not distinguish smooth asymptotic decline, sensor disappearance,
containment, fuel barriers, suppression, or physical extinction.

## Subgroup behavior

At day 7 and seven days ahead, geometry's mean log-error reduction is largest
for the retrospectively defined large-fire group: 0.138 (95% interval
0.101-0.176). It is unresolved for small and medium final-size groups. The gain
is positive for low-, medium-, and high-VPD strata, fragmented and
single-component fires, and polygons with and without holes.

The subgroup sample contains only fires observable through day 14. Final-size,
duration, and ecosystem strata are retrospective explanations, not
origin-time selection rules.

## Prediction verdict

**Growth prediction: SUPPORTED for mapped geometry as a predictive input.**
Origin-time perimeter and topology improve held-out future-area predictions
beyond comparable area and recent-dynamics models.

**A fixed two-thirds temporal growth law: NOT SUPPORTED.** It consistently
overpredicts and loses to simpler alternatives.

**Life-cycle prediction: PARTIALLY SUPPORTED.** Geometry improves future
acceleration-sign and near-term peak-transition discrimination, but the peak
event is rare, precision is low, and the target is a satellite-derived proxy.

**Termination prediction: NOT SUPPORTED as precise early prediction.** Later
updates help substantially, but long-fire death remains badly underestimated
from early snapshots.

The machine-readable basis is in `outputs/adversarial_validation/`:
`forecast_metrics.csv`, `paired_model_comparisons.csv`,
`transition_metrics.csv`, `paired_transition_comparisons.csv`,
`transition_calibration.csv`, and the complete compressed prediction tables.
