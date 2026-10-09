# Geometric manifold manuscript handoff

This is a validation handoff. It does not edit the MAIN or SI.

## Safe for the MAIN

1. In 4,032 locked FIRED events, the pooled daily perimeter-area exponent was 0.614 (fire-bootstrap 95% interval 0.610-0.617).
2. A within-between decomposition separated a between-fire exponent of 0.646 (0.639-0.652) from a within-fire exponent of 0.594 (0.592-0.597).
3. Held-out 2016-2020 estimates were 0.643 between fires and 0.595 within fires.
4. Thus the near-two-thirds appearance is stronger across fires of different characteristic sizes than along the average individual trajectory.
5. `Z_2/3` retained held-out predictive information, but it drifted with area and did not behave as a constant coefficient.

Suggested MAIN wording:

> FIRED perimeter-area scaling depended on the estimand. The cross-fire exponent was practically close to two-thirds, whereas the within-fire exponent was approximately 0.59 and reproduced in held-out years. Two-thirds therefore described differences among fires more closely than the mean longitudinal growth trajectory. Normalized geometry remained predictively useful, but neither its predictive value nor a pooled slope uniquely identified a metabolic mechanism.

## Technical results for the SI

- Eligibility: seven observations, factor-of-two area range, seven-day duration; 3,540 events.
- Event-slope median 0.593; IQR 0.531-0.641; random-slope SD 0.088.
- Random-slope early-history shrinkage did not beat the common development slope prospectively.
- Held-out `Z_2/3` drift: -0.0716 per unit `log A`.
- Total perimeter increased held-out within slope from 0.595 to 0.623.
- Every-third-observation thinning increased it to 0.628.
- Deming and SMA exterior sensitivities were 0.606 and 0.616.
- A flexible development curve beat every fixed exponent in held-out anchored prediction and implied declining local exponent with size.
- None of four calibrated synthetic fixed-manifold models reproduced the joint observed summary.
- `Z_2/3` improved origin-safe held-out prediction more than local slope alone, but full geometry performed best.

## Claims to remove

- “The pooled 0.66 exponent demonstrates that individual fires grow at two-thirds.”
- “Two-thirds is an observation-invariant perimeter-area law.”
- “`P/A^(2/3)` is constant during fire growth.”
- “A local slope near two-thirds is a stable or restoring state.”
- “A two-thirds slope identifies metabolism, coherence, or an active boundary.”

## Claims that can be strengthened

- Population, between-fire, and within-fire scaling are distinct estimands and must be reported separately.
- Cross-fire geometry is practically close to two-thirds under the locked exterior-perimeter definition.
- Normalized geometry is a useful empirical predictor even when its candidate coefficient is not constant.
- Short-window derivatives are unstable when the log-area denominator is small.
- Perimeter definition and observation cadence are first-order parts of the scientific hypothesis.

## Equations requiring qualification

Replace an unconditional `P=kA^(2/3)` claim with either:

\[
P=kA^{\sigma},\qquad \hat\sigma_W\approx0.595
\]

for the locked empirical exterior-perimeter summary, or retain

\[
P=k(A,t,r,\mathcal P)A^{2/3}
\]

as a candidate closure while acknowledging coefficient dependence on area, time, resolution `r`, and perimeter convention `mathcal P`. Then state the identity

\[
d\log P/d\log A=2/3+d\log k/d\log A.
\]

Do not interpret `k` as coherence without an independent measurement model.

## Recommended figure panels

Use `figure1_geometric_manifold_validation` as the main six-panel result: population cloud, within-versus-between estimates, event-slope distribution, normalization drift, local-versus-longitudinal comparison, and synthetic discrepancy. Use `figure2_held_out_examples` in SI to show algorithmically selected held-out examples.

## Verified methodological citations

- Pélabon et al. 2013, *American Naturalist* 181:195-212, doi:10.1086/668820.
- Mundlak 1978, *Econometrica* 46:69-85, doi:10.2307/1913646.
- Bell et al. 2019, *Quality & Quantity* 53:1051-1074, doi:10.1007/s11135-018-0802-x.
- Warton et al. 2006, *Biological Reviews* 81:259-291, doi:10.1017/S1464793106007007.
- Xiao et al. 2011, *Ecology* 92:1887-1894, doi:10.1890/11-0538.1.

## Unresolved limitations

- The exact source table/script for the earlier 237,235-event figure is not in the repository.
- Genuine multi-resolution perimeter observations are unavailable.
- Mapped cumulative exterior perimeter is not independently observed active fireline.
- Area and perimeter errors are shared, correlated, and heteroscedastic.
- Lifecycle phase estimates become unstable when remaining area change is small.
- Predictive utility of `Z_2/3` does not establish that two-thirds is the uniquely useful normalization.
- Fuel, suppression, weather, and detection processes remain incompletely observed.
