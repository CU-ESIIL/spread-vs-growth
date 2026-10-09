# Geometric Scale Audit

## Authority and scope

This is the authority for manuscript statements about scale dependence in the
locked FIRED geometry analysis. It consolidates existing prespecified
analyses; it does not search for a preferred exponent. The inferential cohort
contains 4,032 fires, split into development (2001-2012), calibration
(2013-2015), and held-out (2016-2020) years. Repeated-observation uncertainty
resamples whole fires.

The established held-out exterior-perimeter within-fire slope is `0.5950`
(`0.5906-0.5995`). That value is a longitudinal summary for this observation
operator, not a universal exponent.

## Scale inventory

| Scale dimension | Empirically varied? | Result | Supports scale dependence? | Manuscript-safe interpretation |
| --- | --- | --- | --- | --- |
| Temporal cadence | Yes | Held-out exterior `sigma_W` rises from `0.595` at every observation to `0.616` every second and `0.628` every third; intervals do not overlap the every-observation estimate | Yes | Estimated geometry depends on temporal sampling cadence |
| Rolling-window duration | No | The local estimator uses a fixed seven-observation window | UNRESOLVED | Do not claim window-duration invariance |
| Window area span | Naturally, not experimentally | Held-out local-slope absolute error decreases strongly as log-area span grows (`rho=-0.692`) | Yes, for estimator reliability | Short-span local derivatives are noisy and should not be treated as stable states |
| Area scale | Yes, through a development-fitted cubic | Implied derivative is `0.750`, `0.537`, `0.472`, `0.450`, and `0.480` at area quantiles 0.10, 0.25, 0.50, 0.75, and 0.90 | Yes | A flexible relationship changes with area; these derivatives are not new universal regimes |
| Fire size | Naturally | In held-out eligible fires, event slope decreases modestly with characteristic area (`rho=-0.199`; regression coefficient `-0.0117`) | Partially | Larger fires have somewhat lower longitudinal slopes, but size is entangled with lifecycle and observation span |
| Lifecycle position | Yes, fixed early/middle/late partition | Held-out slopes are `0.700`, `0.519`, and `0.138` | Yes | Geometry flattens across the mapped lifecycle; the late estimate is especially sensitive to small remaining increments |
| Boundary definition | Yes | Held-out within slope is `0.595` for exterior perimeter and `0.623` for total perimeter | Yes | Perimeter convention changes the estimand |
| Estimator choice | Yes | Held-out exterior OLS, Deming, and SMA estimates are `0.595`, `0.606`, and `0.616` | Yes | Conditional prediction and symmetric association answer different questions |
| Error scale | Yes | Held-out multiplicative/lognormal estimate is `0.595`; additive original-scale profiling gives `0.375` | Yes | The assumed error process materially affects the exponent |
| Independent spatial resolution | No | Only the approximately 500 m FIRED source product is available | UNRESOLVED | **TRUE SPATIAL MULTI-RESOLUTION SCALING REMAINS UNRESOLVED.** |

## What is demonstrated

The data demonstrate observation and lifecycle dependence. Cadence, boundary
definition, estimator, error scale, area scale, and lifecycle position all
change the estimated relationship. These are empirical sensitivities within
one satellite-derived polygon product. They do not establish how the law
changes under genuinely independent spatial resolutions.

Rerasterizing the same polygons would vary a numerical representation, not the
independent observation operator, so it is not used as a spatial-resolution
experiment.

## Source tables

The consolidated machine-readable inventory is
`outputs/final_state_audit/scale_dependence_summary.csv`. Original estimates
remain in `outputs/geometric_manifold_validation/`, principally
`temporal_thinning_sensitivity.csv`, `lifecycle_scaling.csv`,
`powerlaw_adequacy.csv`, `perimeter_definition_sensitivity.csv`,
`measurement_error_sensitivity.csv`, `log_vs_original_scale.csv`, and
`local_vs_longitudinal_slope.csv`.

