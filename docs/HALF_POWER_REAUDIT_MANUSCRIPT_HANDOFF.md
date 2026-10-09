# One-Half Re-audit Manuscript Handoff

This handoff does not edit the manuscript or SI. It separates statements that
survive from statements whose empirical meaning depends on intercept treatment.

## Safe as written

### Within-between distinction

Locate text equivalent to:

> FIRED perimeter-area scaling depended on the estimand. The cross-fire
> exponent was near two-thirds, whereas the within-fire exponent was
> approximately 0.59.

This remains supported. Held-out estimates reproduce the distinction:
between-fire `0.643`, within-fire `0.595`.

### Temporal forecasts are not geometric tests

Locate text equivalent to:

> This result tests cumulative-area trajectories through time; it does not
> directly test the perimeter-area exponent.

Retain. The one-half and two-thirds transformed-area forecasts are category F.

### Mechanism non-identification

Locate text equivalent to:

> Observing a two-thirds slope does not uniquely identify boundary geometry or
> metabolism.

Retain. The normalization audit strengthens this qualification.

## Safe with rewording

### “One-half is competitive”

Replace unqualified wording with:

> A one-half center was competitive as a shrinkage target for noisy future
> rolling perimeter-area slopes at several multi-day horizons. This category E
> result does not test a common one-half perimeter-area normalization.

### “One-half predicts better”

Replace with the exact task, for example:

> Under retrospective fire-specific intercept fitting, fixed one-half
> trajectories had lower repeated-transition log-perimeter loss than fixed
> two-thirds trajectories. Under a development-locked population coefficient,
> one-half was worse on independent held-out geometry observations.

### “Diffusion-like one-half”

Replace with:

> smooth shape-preserving one-half geometric reference

unless an independent diffusion process model is introduced and tested.

### Figure slope guides

The current empirical caption says:

> lines show mapped exterior perimeter against cumulative mapped area, with
> one-half and two-thirds slope guides centered on each trajectory.

Recommended replacement:

> Lines are event-conditioned visual slope guides anchored to a fitted point on
> each trajectory. They illustrate local divergence after conditioning and do
> not compare common population normalizations.

### Constraint result

The current heading and summary “Why Does One-Half Sometimes Beat
Two-Thirds?” should be replaced by:

> Realization deficits do not explain relative performance of one-half versus
> two-thirds local-slope shrinkage targets.

This preserves the result and names category E correctly.

## Must change

### Universal-law inference from an anchored forecast

Any statement equivalent to:

> Because anchored one-half forecasts well, fires follow
> `P proportional to A^(1/2)`.

must change to:

> Origin-anchored one-half extrapolation can forecast locally after conditioning
> on current geometry. This does not establish a common one-half normalization.

### Collapse of all “one-half models”

Any table or paragraph combining temporal area growth, perimeter-area scaling,
future rolling slopes, and anchored perimeter forecasts under one label must
separate categories B-F. Suggested labels are:

- population one-half law;
- fire-conditioned one-half scaling;
- origin-anchored one-half extrapolation;
- one-half local-slope shrinkage;
- one-half temporal area-growth model.

### Unqualified figure reference lines

Every perimeter-area figure caption must state whether each line uses a common
coefficient, fitted coefficient, chosen-point anchor, event-specific anchor, or
unclear historical raster normalization. The machine-readable mapping is in
`figure_intercept_audit.csv`.

## No longer supported

### “Wildfires do not follow diffusion” from perimeter-area slope alone

The storyboard wording

> Wildfires do not follow diffusion.

is not established by this analysis. Recommended replacement:

> Wildfire perimeter-area geometry is inconsistent with an exact common
> one-half normalization in the locked FIRED cohort; this geometric result does
> not by itself identify or exclude every diffusion mechanism.

### “One-half state” or “one-half regime” as a mechanism

Proximity of a rolling slope to one-half does not identify a physical state,
diffusion, suppression, or fuel limitation. Use:

> local rolling slope near one-half

and keep causal explanations as untested alternatives.

### A universal exact within-fire two-thirds law

The held-out within-fire exponent is `0.595` (`0.591-0.600`) and normalization
under two-thirds drifts downward. Do not state that individual mapped fire
perimeters generally grow at exact two-thirds.

## New result

Suggested Results text:

> We re-audited fixed one-half and two-thirds perimeter-area comparisons under
> explicit normalization treatments. With candidate coefficients estimated on
> development fires and locked before evaluation, one-half had held-out
> log-perimeter MAE 0.276 versus 0.247 for two-thirds and 0.231 for the
> development-estimated exponent 0.595. Weighting fires equally, one-half
> exceeded two-thirds loss by 0.0226 (95% whole-fire bootstrap interval
> 0.0157-0.0291). In contrast, fitting one retrospective intercept per fire
> reduced repeated-transition MAE to 0.143 for one-half and 0.196 for
> two-thirds; the intercept-adaptation gain was 0.0344 larger for one-half
> (0.0270-0.0422). Thus fire-specific conditioning explains substantial
> apparent one-half competitiveness, but does not support a common population
> one-half law.

Suggested geometric-leverage text:

> Under common-origin anchoring, the two-thirds to one-half prediction ratio is
> `(A_future/A_0)^(1/6)`. Held-out comparisons had little leverage at low area
> expansion, where one-half sometimes forecast better. At high and extreme
> expansion the candidates separated and two-thirds performed better. A
> short-horizon tie therefore indicates limited discrimination rather than
> exponent equivalence.

Suggested within-between text:

> The exponent removing within-fire normalization drift was 0.595 in both
> development and held-out years. One-half normalization drifted upward by
> 0.095, whereas two-thirds normalization drifted downward by 0.072. The
> between-fire exponent remained 0.643, supporting distinct longitudinal and
> cross-fire geometric relationships.

Suggested formal qualification:

> The geometric elimination from `A=c_A L^2` and `P=c_P L^(4/3)` retains the
> coefficient `k=c_P/c_A^(2/3)`. The algebra is pointwise. Interpreting it as a
> scaling law over growth requires `k` to remain fixed over the stated domain;
> allowing arbitrary `k(A)` makes the exponent non-identifying.

## Figure guidance

Use the six-panel audit figure as a supporting or SI figure. Its caption should
state:

> (A) Held-out population geometry with coefficients learned on development
> fires. (B) Same-origin candidate curves for one reproducible held-out fire.
> (C) Relative one-half versus two-thirds loss under explicit intercept
> treatments. (D) Anchored relative loss versus prospectively binned area
> expansion. (E) held-out within-fire normalization drift. (F) calibrated true
> two-thirds synthetic controls crossed with intercept treatment. Negative loss
> difference favors one-half. Fire-specific fits are retrospective diagnostics;
> population and origin-anchored fits are prospective with respect to future
> geometry.

## Data and code

- Analysis: `scripts/run_half_power_reaudit.py`
- Utilities: `src/fire_metabolism/half_power_reaudit.py`
- Outputs: `outputs/half_power_reaudit/`
- Formal audit: `FireProof/HALF_POWER_NORMALIZATION_FORMAL_AUDIT.md`
- Formal dependencies: `FireProof/HALF_POWER_NORMALIZATION_DEPENDENCIES.md`
- Lean checks: `FireProof/FireProof/Normalization.lean`

