# spread-vs-growth

This project supports figures, animations, and longer-running analyses for comparing wildfire spread rate and growth rate.

[View Storyboard](storyboard.md){ .md-button .md-button--primary }
[Figure Workflow](workflow.md){ .md-button }

<div class="grid cards" markdown>

- **Spread**

  ---

  Motion through space: fronts, diffusion, advection, and local rate of advance.

- **Growth**

  ---

  Expansion of area, exchange surface, transport networks, and emergent form.

- **Figures**

  ---

  Reproducible static figures, animation frames, and talk-ready rendered outputs.

</div>

!!! note "Current focus"
    The first target is the ESA 2026 Fire Metabolism storyboard: explain why extreme wildfire may require growth-rate thinking in addition to spread-rate thinking.

## Current empirical verdict

The adversarial FIRED validation finds that origin-time mapped perimeter and
topology improve held-out future-growth and transition prediction beyond area
and recent dynamics. A fitted `2/3` slope alone does not identify a coherent
state, fixed `2/3` temporal growth forecasts poorly, and latent coherence,
prospective fuel limitation, energetic metabolism, and physical termination
remain unmeasured. Start with the [detection audit](DETECTION_PREDICTION_AUDIT.md),
[prediction results](PREDICTION_VALIDATION.md), and
[mechanism verdict](MECHANISM_DISCRIMINATION.md).

The follow-on [effective-coupling validation](EFFECTIVE_COUPLING_VALIDATION.md)
finds a predictable time-varying normalized-growth coefficient and small
held-out gains from structured area propagation, without uniquely identifying
the `2/3` normalization. The adversarial
[geometric-attractor test](GEOMETRIC_ATTRACTOR_VALIDATION.md) does not support
a universal restoring state at `2/3`: apparent mean reversion is sensitive to
measurement error and perimeter definition, and flexible dynamics predict
future mapped geometry better.

The [integrated geometry-transport experiment](INTEGRATED_GEOMETRY_TRANSPORT_VALIDATION.md)
adds real FIRED footprint distances against area-matched isotropic-growth
nulls. Departure from `2/3` predicts more spatial reorganization, but
reorganization does not consistently restore geometry toward `2/3`. Recent OT
adds a small held-out future-coupling gain beyond geometry from about five days
onward; it remains an empirical spatial descriptor, not literal transport or a
latent coherence measurement.

The [latent-constraint validation](LATENT_CONSTRAINT_VALIDATION.md) separates
model-implied expected growth from realized growth. Geometry modestly improves
prospective deficit-risk scores, but the mixture does not improve long-horizon
point forecasts and FIRED cannot attribute causes. The focused
[one-half versus two-thirds test](HALF_VS_TWO_THIRDS_CONSTRAINT_TEST.md) rejects
the proposed rescue: one-half remains competitive when growth is near
model-implied potential, so negative realization deficits are not a sufficient
explanation for its performance.

The [within-between geometric scaling analysis](GEOMETRIC_MANIFOLD_VALIDATION.md)
resolves the pooled-versus-longitudinal question. In the locked FIRED cohort,
the between-fire exponent is `0.646`, while the within-fire exponent is
`0.594` and reproduces in held-out years. Two-thirds is thus closer to how
fires of different characteristic sizes compare than to the average path an
individual mapped fire follows. Normalized geometry remains useful for
prediction, but it is neither constant nor mechanism-specific.

The [one-half normalization re-audit](HALF_POWER_REAUDIT.md) separates a
population law from fire-conditioned scaling, origin-anchored extrapolation,
local-slope shrinkage, and temporal area growth. One-half is worse than
two-thirds under a development-locked population normalization, but benefits
more from retrospective fire-specific intercept fitting and can be locally
competitive where anchored candidates have little area-expansion leverage.
The development-estimated within-fire exponent near `0.595` remains the best
general geometric candidate. The corresponding FireProof audit preserves the
existing algebra while making the required fixed-normalization assumption
explicit.

The [final state, scale, detection, and prediction audit](FINAL_STATE_SCALE_PREDICTION_AUDIT.md)
closes the major FIRED analysis pass. Fixed `1/2`, `2/3`, `3/4`, and
development `0.595` normalizations are predictively indistinguishable after
conditioning on area, whereas full multivariate geometry adds reproducible
future-area skill. The primary current-deficit detection task remains weak and
does not improve with geometry. The separate
[geometric scale audit](GEOMETRIC_SCALE_AUDIT.md) records which scale
sensitivities are empirical and why true spatial multi-resolution scaling
remains unresolved.
