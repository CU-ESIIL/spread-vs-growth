# Fire Critter Detection Validation

> **Realization update.** Under `M_real=B K A^(2/3)`, the normalized
> observable is realized coupling `BK`. FIRED can detect a negative realization
> residual after onset and has modest prospective risk skill, but cannot
> attribute the event to suppression, water, urban land, fuel gaps, or another
> cause. See [Latent Constraint Validation](LATENT_CONSTRAINT_VALIDATION.md) and
> the [FIRED Detectability Matrix](FIRED_DETECTABILITY_MATRIX.md).

## Scientific question

Can FIRED observations identify when a wildfire enters a coherent whole-fire
growth state?

The answer must be split in two. FIRED can identify a recurring mapped
perimeter-area pattern, but it has no independent whole-fire coherence label,
active-fireline measurement, or prospective connected-fuel domain. The
analysis therefore evaluates geometric detection, stability, and dynamical
construct validity. It does not report sensitivity or specificity for a latent
biological-style state that was never observed.

## Data and held-out design

The analysis reuses 4,032 complete FIRED sequences:

- development: ignition years 2001-2012;
- calibration: 2013-2015; and
- held-out evaluation: 2016-2020.

FIRED supplies retrospective MODIS-derived daily burned-area additions and
mapped polygons at approximately 500 m resolution. Cumulative polygons are
formed by unioning additions only through each forecast origin. Exterior and
total mapped perimeter, components, and holes are measured in the source
projected coordinate system.

The cohort is retrospectively conditioned on final size, duration, natural
vegetation, sequence completeness, and agreement between reconstructed and
reported final area. Results apply to that retained cohort, not to all
ignitions.

## Operational geometric indicator

At event days 5, 7, 10, 14, and 21, the detector fits

```text
log(P) = intercept + sigma log(A)
```

using distinct positive-detection days available through the snapshot. A
window is called geometrically compatible with `2/3` only when:

1. at least five perimeter observations are available;
2. mapped area spans at least a factor of two;
3. the 95% slope interval contains `2/3`; and
4. the fixed `2/3` residual sum of squares does not exceed the fixed `1/2`
   residual sum of squares.

Persistence requires detection at the current and preceding prespecified
snapshot. The rule was not tuned on held-out events.

## Held-out results

| Snapshot | Eligible fires | Median exterior slope | Geometric indicator | Persistent indicator | Mean agreement across variants |
| ---: | ---: | ---: | ---: | ---: | ---: |
| Day 5 | 792 | 0.676 | 26.6% | 0.0% | 18.1% |
| Day 7 | 1,058 | 0.650 | 42.2% | 15.4% | 28.8% |
| Day 10 | 760 | 0.647 | 49.2% | 26.1% | 41.6% |
| Day 14 | 435 | 0.631 | 54.7% | 36.1% | 56.5% |
| Day 21 | 145 | 0.622 | 55.2% | 40.7% | 60.2% |

The median slope is near `2/3` early and drifts downward with age. That is
evidence for a common geometric pattern, not a discrete universal transition.
Only 15.4% of eligible held-out fires have persistent detections by day 7.

Development, calibration, and held-out medians are similar, so the broad slope
pattern is temporally reproducible. Detection frequency, however, depends
strongly on having enough polygon observations and on the exact observation
rule.

## Robustness

### Perimeter convention

At day 7, held-out detection is 42.2% with exterior perimeter and 44.2% with
total perimeter. Their median slopes are 0.650 and 0.673, respectively. Total
perimeter therefore moves the result toward `2/3`, partly because it includes
holes and interior edges that need not be active fireline.

### Temporal sampling

Every-other-observation fits cannot meet the five-observation rule at days 5
or 7 and yield no detections. At day 10, only 23.8% are detected after
thinning, versus 49.2% using all observations. By day 21 the thinned estimate
rises to 68.3%, illustrating survivorship and observation-count effects.

This is not a nuisance detail: apparent regime entry depends on how often the
boundary is observed. A day-7 indicator cannot be transported to sparser
sensors without recalibration and a new minimum-information rule.

### Size, duration, topology, ecosystem, and weather

Subgroup analyses use the day-7 origin and a seven-day forecast target, so
they include only fires still observable through day 14. Future-size,
duration, and dominant-ecosystem strata are retrospective descriptions and
are never model inputs.

- Detection is 42.6% among the large final-size group, 43.9% among medium
  fires, and 28.0% among small fires.
- Detection is 50.2% when mapped holes are present and 27.4% without holes.
- Persistent detection is 18.3% with holes and 5.1% without holes.
- Detection varies from 27.9% in the low-VPD group to 46.3% in the high-VPD
  group, but weather was sampled at a future-footprint centroid and this is a
  sensitivity analysis rather than an operational comparison.
- Geometry's predictive improvement is positive in forests and grasslands but
  uncertain in savannas and woody savannas. Those ecosystem labels are
  future-derived dominant classes and are retrospective only.

The association with holes and fragmentation shows that the detector responds
to polygon topology. That may contain useful growth information, but it also
prevents interpretation as a clean active-boundary coherence measurement.

### Spatial resolution

True resolution sensitivity is **NOT YET TESTED**. All FIRED polygons derive
from the same approximate 500 m product. Perimeter convention and temporal
subsampling are tested; real multiresolution geometry is not. Synthetic
coarsening would not substitute for independent higher-resolution fireline
observations.

## Can the indicator be scored as a classifier?

No. No independent reference label exists. Defining ground truth from the same
`2/3` exponent would be circular. Consequently:

- sensitivity, specificity, precision, recall, and balanced accuracy for
  “coherent whole-fire state” are **NOT IDENTIFIABLE**;
- reported quantities are detector frequency, cross-rule agreement,
  persistence, and future-dynamics construct validity; and
- mapped geometric compatibility must not be called detected latent
  coherence.

## Detection verdict

**Geometric detection: PARTIALLY SUPPORTED.** A near-`2/3` mapped
perimeter-area relationship appears frequently and reproducibly, but it is not
universal, stable at early times, or independent of perimeter convention,
sampling frequency, and topology.

**Dynamical detection: PARTIALLY SUPPORTED.** The full origin-time geometry
contains future-growth and transition information beyond area and recent
dynamics. The binary `2/3` indicator itself contributes little, so the useful
signal is not equivalent to crossing a single exponent threshold.

**Mechanistic detection: NOT IDENTIFIABLE.** FIRED does not independently
measure active coherence `C`, prospective reachable fuel `F`, active perimeter,
or physical termination.

Machine-readable results are in
`outputs/adversarial_validation/detection_windows.csv.gz`,
`detection_summary.csv`, `detection_robustness.csv`, and
`subgroup_robustness.csv`. Figure 1 shows accepted and rejected trajectories;
Figure 2 shows sensitivity to observation rules.
