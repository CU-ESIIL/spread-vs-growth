# Fire Critter Mechanism Discrimination

## Purpose

This report asks how much of Fire Critter survives comparison with plausible
alternatives. Mathematical verification establishes what follows from the
assumptions; it does not show that wildfires instantiate those assumptions.

## 1. Does a two-thirds exponent identify the mechanism?

**No.** The held-out median exterior-perimeter slope is 0.650 at day 7, and
42.2% of eligible fires satisfy the uncertainty-aware geometric rule. The
pattern is real enough to study but is not mechanism-specific.

The synthetic negative control

```text
A(t) = A0 + vt,
P(t) = k A(t)^(2/3)
```

has an exact two-thirds perimeter-area slope, linear non-metabolic area growth,
and no interior life-cycle peak. The detector accepts its geometry but cannot
identify a coherence-fuel mechanism. A separate observation-distortion control
starts from a cubic area path but changes mapped perimeter by a scale-dependent
factor, causing the geometry detector to reject an otherwise compatible
growth process.

**Classification: PARTIALLY SUPPORTED as geometry; NOT IDENTIFYING as
mechanism.**

## 2. Does geometry improve future-growth prediction?

**Yes, within the retained FIRED cohort.** The geometry proxy receives the
same area and recent-dynamics information as the dynamics ridge, then adds
mapped perimeter and topology. At day 7, its paired mean absolute log-error
improvements are:

- 0.017 at one day (95% interval 0.011-0.023);
- 0.064 at three days (0.051-0.078);
- 0.076 at five days (0.057-0.095); and
- 0.077 at seven days (0.052-0.101).

The gain is also present from day 5 and against the fixed nonlinear dynamics
benchmark. This is the strongest positive empirical result.

The binary geometric detector contributes much less than the full geometry.
Thus the supported claim is that origin-time mapped geometry contains
predictive information, not that a coherent state is detected by a two-thirds
threshold.

**Classification: SUPPORTED as predictive association.**

## 3. Does coherence-fuel coupling improve prediction beyond geometry?

**Not tested independently.** The canonical closure is

```text
A' / A^(2/3) = beta0 [2 C F / (C + F)]^2.
```

FIRED supplies neither independently measured active coherence `C` nor a
prospectively defined connected-fuel ceiling for `F`. Reconstructing either
from realized growth would reuse the outcome and would not validate the
mechanism.

The fitted geometry proxy is not the canonical model. It is an observable
predictor motivated by the theory. Its success cannot be attributed uniquely
to coherence-fuel coupling because ordinary morphology, fire size,
fragmentation, holes, fuel pattern, and observation process can all contribute.

**Classification: NOT IDENTIFIABLE.**

## 4. Can coherence be independently identified?

**No.** Cumulative mapped perimeter includes inactive, interior, and
extinguished edges. The formal identifiability analysis already shows that
area and perimeter identify products such as `kC`, not `C` itself, unless
active perimeter and `k` are independently known.

The closed forcing is symmetric in `C` and `F`. The synthetic state-swap
control confirms that instantaneous forcing is identical after swapping the
states. Existing numerical observational twins also produce nearly identical
area trajectories with materially different latent coherence.

Required new measurements are active fireline, an independent coherence
metric, and a prefire reachable-fuel mask.

**Classification: NOT IDENTIFIABLE.**

## 5. Does the model predict life-cycle transitions before they occur?

**Observable geometry predicts transition proxies, but the canonical
transition equation is untested.**

At day 7, the geometry proxy predicts the sign of three-day future mapped
acceleration with balanced accuracy 0.790 (95% interval 0.763-0.818), improving
on the equally informed dynamics model by 0.098 (paired interval 0.063-0.134).

For a positive-to-nonpositive growth-rate crossing in the next three days,
balanced accuracy is 0.791 (0.735-0.843), a paired improvement of 0.062
(0.005-0.114). But precision is only 0.224 because the crossing is rare.

These tests establish prospective morphology-transition association. They do
not evaluate `sign(M') = sign(Psi)` because `C`, prospective `F`, and the
calibrated canonical parameters are unavailable.

**Classification: PARTIALLY SUPPORTED.**

## 6. Are observed failures consistent with reduced-model limitations?

**Yes, but consistency is not causal attribution.**

- Fixed two-thirds growth overpredicts strongly, indicating a rapidly varying
  forcing coefficient or a wrong temporal closure.
- Persistent fires are systematically terminated too early by pooled models,
  consistent with missing fuel connectivity, weather evolution, suppression,
  barriers, spotting, and observation state.
- Past coarse weather gives no resolved area-forecast improvement beyond
  geometry, so one centroid weather history does not explain the missing tail.
- Abrupt FIRED endpoints are enriched among early-ending realization-gap
  candidates, but FIRED cannot separate suppression, fuel restriction,
  physical barriers, weather change, and sensor disappearance.

These failures match processes omitted from the reduced model. They do not
prove that any particular omitted process caused an event.

## 7. What would directly falsify the mechanism?

The strongest feasible falsification requires data absent from FIRED:

1. delineate reachable connected fuel before the forecast, defining `Amax`;
2. independently measure active perimeter and coherent active-front structure;
3. estimate parameters on development fires only;
4. predict held-out normalized growth, coherence change, acceleration sign,
   and transition time; and
5. compare against area-history, weather-fuel, and process-spread alternatives
   receiving the same future forcing information.

Repeated wrong acceleration signs or structured forcing-surface residuals
after the lower measurement levels pass would falsify the proposed closed
mechanism. Failure of a two-thirds mapped slope alone would only reject its
geometric entry point.

## Alternative explanations

| Alternative | Can explain `P-A` slope? | Can explain geometry prediction? | Current discrimination |
| --- | --- | --- | --- |
| Ordinary rough or fragmented perimeter | Yes | Yes | Not separated from coherence |
| Scale-dependent shape or elongation | Yes | Yes | Partly represented by topology features |
| Linear/recent trajectory persistence | Not required | Partly | Beaten by full geometry, beats fixed `2/3` |
| Free-exponent area growth | Not mechanism-specific | Partly | Calibration selects `sigma=0` |
| Flexible recent-dynamics regression | Not required | Partly | Beaten by full geometry at all tested horizons |
| Past coarse weather | Not required | Possibly | No resolved increment beyond geometry |
| Operational fire-spread model | Possibly | Possibly | Not event-matched; NOT YET TESTED |
| Suppression or fuel barriers | Can alter observed geometry | Yes, especially termination | Cause not observed |

## Synthetic audit outcome

The negative controls demonstrate that the validation code does not
automatically favor Fire Critter:

- a non-metabolic process passes the `2/3` detector;
- distorted observation causes a compatible process to fail geometric
  detection;
- a linear-area alternative forecasts a linear process better than the
  two-thirds model; and
- swapped latent states produce identical closed forcing.

The controls are software and construct-validity tests. They are clearly
labeled synthetic and are not counted as wildfire evidence.

## Evidence classification

| Prediction | Classification |
| --- | --- |
| Mapped perimeter-area scaling near `2/3` | PARTIALLY SUPPORTED |
| Independent coherent-state detection | NOT IDENTIFIABLE |
| Geometry adds future-growth information | SUPPORTED |
| Fixed two-thirds temporal growth improves forecasts | NOT SUPPORTED |
| Coupled coherence-fuel forcing closure | NOT IDENTIFIABLE |
| Prospective acceleration and peak proxies | PARTIALLY SUPPORTED |
| Past coarse weather adds beyond geometry | NOT SUPPORTED |
| Precise early termination prediction | NOT SUPPORTED |
| Abrupt physical termination mechanism | NOT IDENTIFIABLE |
| Energetic metabolism | NOT YET TESTED |
| Superiority to operational spread models | NOT YET TESTED |

## Bottom line

The part of Fire Critter that survives is narrower and more useful than a
blanket confirmation. Mapped geometry is predictively informative, and it
helps identify elevated near-term acceleration and peak-transition risk.
Neither a fitted `2/3` exponent nor predictive geometry uniquely identifies
the proposed coherence-fuel mechanism. The fixed two-thirds temporal growth
law fails, early termination remains weak, and energetic metabolism is still
untested.

The machine-readable audit is in
`outputs/adversarial_validation/evidence_classification.csv` and
`synthetic_counterexamples.csv`. Figure 5 presents the held-out model
comparison; Figure 6 maps where geometry helps or fails.
