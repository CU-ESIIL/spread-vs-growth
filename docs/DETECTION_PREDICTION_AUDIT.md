# Detection and Prediction Audit

## Scope

This document is the pre-implementation audit for the adversarial validation of
Fire Critter detection and prediction. It records what the repository already
tests, what those tests can establish, and what remains missing. The purpose is
to avoid duplicating validated code or converting mathematical verification
into empirical support.

## Existing evidence chain

### Mathematical and conceptual work

The formal and scientific core is already documented in:

- `FireProof/THEORY_CORE.md`;
- `FireProof/SYNTHESIS.md`;
- `FireProof/PREDICTION_HIERARCHY.md`;
- `FireProof/EMPIRICAL_TESTS.md`;
- `FireProof/PREDICTIONS.md`;
- `FireProof/CLAIMS_AUDIT.md`;
- `FireProof/IDENTIFIABILITY.md`; and
- `FireProof/FAILURE_MODES.md`.

Lean verifies the algebraic closure and conditional consequences. It does not
verify that mapped wildfire observations satisfy the closures. In particular,
the formal proof does not identify latent coherence, prospective reachable
fuel, active perimeter, or energetic throughput from FIRED observations.

### Existing FIRED analyses

The repository already contains a common cohort of 4,032 FIRED events and a
stable temporal split: 2001-2012 development, 2013-2015 calibration, and
2016-2020 held-out evaluation. Existing workflows provide:

| Existing workflow | Completed test | Main limitation for this audit |
| --- | --- | --- |
| `fired_prediction` | Rolling one- to three-day area forecasts for fixed and development-selected exponents | Tests temporal area laws, not coherent-state detection |
| `fired_outcome_validation` | Day 3/5/7 final-area and duration prediction | Published ridge includes a future-derived dominant land-cover label |
| `fired_lifecycle_prediction` | Geometry features, later area, peak day, and death day | Uses cumulative mapped perimeter, not independently observed active fireline |
| `fired_state_survival` | State-conditioned death-time distributions | States are past-only trajectory labels, not latent coherence measurements |
| `fired_persistence_damage` | Persistent-regime and damage proxies | Outcome-defined regime analyses are retrospective diagnostics |
| `fired_realization_gap` | Persistent-course potential versus realized outcome | Cannot attribute the gap to suppression or fuel restriction |
| `fired_missing_processes` | Past weather and newly burned boundary proxies | Weather is coarse; active-front variable is a satellite proxy |

These analyses already show a difficult negative result: local `sigma=2/3`
forecasts do not beat no-growth or linear-area forecasts at one- to three-day
horizons. Geometry-informed regressions improve some longer-horizon and
final-area predictions, but long-fire termination remains poorly predicted.

### Existing computational and conventional-model work

The computational SI and model-scaling experiments test algebra, synthetic
counterexamples, and perimeter-area behavior in simplified spread models.
`MODEL_DISCRIMINATION_AUDIT.md` specifies a fair comparison design.
`CONVENTIONAL_MODEL_COMPARISON_PLAN.md` correctly concludes that an
event-matched ELMFIRE or Cell2Fire comparison is not yet available. Emulator
outputs must not be represented as operational spread-model validation.

## Leakage and conditioning audit

The adversarial pipeline must preserve the existing event-level temporal
partitions and add the following barriers.

1. **Future-derived land cover.** The stored `lc_name` is the area-weighted
   dominant class over all daily polygons in the completed fire. It must be
   excluded from every primary prospective comparator. Existing results using
   it remain reproducibility benchmarks, not the primary clean result.
2. **Retrospectively selected cohort.** Minimum final area, final duration,
   complete-sequence reconciliation, and eventual natural land cover define
   the cohort. Results therefore apply to this retrospectively selected set of
   mapped fires and are not all-ignition operational forecasts.
3. **Target columns beside predictors.** Snapshot tables contain final area,
   death day, peak day, and future area targets. Every fitted model must use an
   immutable predictor whitelist.
4. **Prospective fuel ceiling.** Final realized area cannot be used as
   `Amax`. No primary FIRED test may claim to evaluate the canonical
   coherence-fuel forcing surface without a prospectively delineated reachable
   fuel domain.
5. **Latent coherence.** Coherence cannot be reconstructed from the target
   growth trajectory and then treated as independent evidence. Cumulative
   mapped perimeter is not active perimeter.
6. **Repeated access to 2016-2020.** The held-out period has been inspected in
   prior work. This audit is a fixed external validation of a predeclared
   design, not a pristine first use. No threshold or model choice may be tuned
   on its results.
7. **Within-fire dependence.** Uncertainty and pairwise comparisons must
   resample whole fires, not daily records.

## Operational meaning of detection

FIRED contains no independent label saying that a fire entered a coherent
whole-fire state. Classification sensitivity and specificity are therefore
not identifiable. The audit will report three narrower quantities.

### Geometric regime indicator

A geometric indicator requires a rolling log-log perimeter-area slope whose
uncertainty is compatible with `2/3`, whose fit is at least as good as the
fixed `1/2` alternative, and which persists across consecutive prespecified
windows. This is a geometric pattern indicator, not a mechanistic state label.

### Dynamical construct validity

The indicator has dynamical value only if it predicts future growth,
acceleration sign, or transition timing beyond area and recent-growth history
on the same held-out fires. Incremental value, paired uncertainty, calibration,
and failure subsets are the relevant evidence.

### Mechanistic identification

The canonical mechanism requires independent active coherence and a
prospective reachable-fuel fraction. FIRED lacks both. The latent
coherence-fuel mechanism is therefore **NOT IDENTIFIABLE** from this data set.
Only observable consequences and geometry-informed predictors can be tested.

## Existing tests to reuse

- Attribute-only FIRED sequence reconstruction and checksums from
  `fire_metabolism.fired_prediction`.
- Cumulative polygon unions and perimeter conventions from
  `extract_fired_geometry_sequences.py`.
- Past-only area and geometry features from
  `fire_metabolism.fired_lifecycle`.
- Standardized ridge and logistic fitting utilities from the existing outcome
  and survival modules.
- Event-level bootstrap conventions and fixed temporal partitions.
- Existing weather and active-front features for a separate day-7 comparison.
- Formal counterexamples and numerical observational twins in `FireProof/`.

## Tests that are incomplete or absent

1. Uncertainty-aware and persistent geometric regime detection.
2. Direct comparison of fixed `1/2`, fixed `2/3`, and free-exponent geometry
   over prespecified observation windows.
3. Detector stability to perimeter convention, temporal subsampling, window
   length, fragmentation, holes, fire size, and duration.
4. A leakage-clean estimate of geometry's incremental future-growth value.
5. Held-out acceleration-sign and peak-transition prediction with explicit
   sign-change requirements.
6. Paired event-bootstrap comparisons across all candidate models.
7. Synthetic negative controls proving that the detector does not equate a
   `2/3` slope with the proposed life cycle or mechanism.
8. A single machine-readable evidence classification and SI handoff.

True spatial-resolution sensitivity, independent active-fireline validation,
prospective `Amax`, suppression attribution, energetic throughput, and an
event-matched operational spread-model comparison cannot be completed from the
current repository data. They must be reported as **NOT IDENTIFIABLE** or
**NOT YET TESTED**, not filled with synthetic substitutes.

## Locked validation plan

The new pipeline will use the existing cached FIRED sequences and geometry,
fixed temporal partitions, immutable origin-safe predictor lists, deterministic
seeds, whole-event bootstrap intervals, and paired held-out comparisons. It
will produce six figures, machine-readable metrics, synthetic negative
controls, and the four remaining required reports. A small smoke mode will run
on a deterministic event subset; the full mode will use all retained events.

The primary Fire Critter empirical candidate is the observable
geometry-informed model. It must be labeled as a proxy test. The canonical
latent two-state model will not be scored as independently validated because
its required states are absent.
