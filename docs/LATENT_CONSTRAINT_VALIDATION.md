# Latent Constraint Validation

## Executive verdict

FIRED can detect that mapped growth fell unexpectedly below a prediction made
from the fire's earlier state. It cannot identify why. The analysis therefore
uses **negative realization residual** for the measured departure and
**constraint-like growth deficit** for a development-defined extreme event.
Neither term means suppression.

The origin-safe geometry/dynamics model was selected on 2001-2015 data and
evaluated on 1,164 fires from 2016-2020. The held-out median residual was
`q=-0.188`; its first percentile was `-4.890`. The locked lower-decile rule
classified 10.07% of held-out intervals as constraint-like.

## Potential and realized growth

The theory extension is

\[
M_{\rm pot}=K A^{2/3},\qquad
M_{\rm real}=B M_{\rm pot},\qquad 0\leq B\leq1.
\]

The empirical predictor is not a physical maximum. It is expected future growth
learned from past-only area, recent dynamics, mapped geometry, and topology. For
an interval of length `h`,

\[
q=\log(M_{\rm obs}+0.01)-\log(\widehat M_{\rm pot}+0.01).
\]

The selected model was geometry plus recent dynamics with ridge penalty 100.
Selection used calibration MAE only; held-out outcomes were not used. Under the
extension, `K_realized=M_obs/A^(2/3)=BK`; FIRED does not separately identify
`B` and endogenous `K`.

## Prospective deficit risk

| Hazard model | Held-out sample | Brier | Log score |
|---|---:|---:|---:|
| constant | 48,450 | 0.0905 | 0.3266 |
| age + area | 48,450 | 0.0887 | 0.3175 |
| recent dynamics | 48,450 | 0.0878 | 0.3148 |
| geometry + dynamics | 48,450 | 0.0866 | 0.3101 |
| geometry + OT | 9,790 matched | 0.0853 | 0.3035 |

The OT row is a matched-sample secondary analysis; the output also reports its
geometry-only matched comparator. Prior OT reorganization had almost no useful
association with future `q` in held-out fires (`rho=0.0355`), although
contemporaneous OT and `q` were associated (`rho=0.450`). OT therefore looks
more like an at-onset spatial detector than a demonstrated early warning.

## Prediction impact

The expected-growth model strongly beats carrying recent growth forward. A
latent-deficit mixture gives small short-horizon gains but not reliable long-
horizon gains. Geometry-hazard mean absolute log-area error was 0.223 versus
0.229 for the unadjusted model at one day, but 0.605 versus 0.559 at 42 days.

Constraint-like intervals are associated with approaching mapped termination.
At seven days, termination occurred in 90.8% of constraint-like intervals
versus 48.8% of other intervals. This is a retrospective association, not a
causal diagnosis.

## Attractor robustness

For matched held-out transitions, fixed 2/3 restoring strength was 0.143
naively, 0.013 with Huber weighting, and 0.161 after excluding
development-defined extreme deficits. This instability reinforces the earlier
conclusion: a universal dynamical 2/3 attractor is not robustly established.

| Question | Verdict |
|---|---|
| Coherent `B` extension | SUPPORTED formally |
| `B` and `K` separately identified | NOT IDENTIFIABLE |
| Unexpected growth deficits detectable after onset | SUPPORTED |
| Elevated deficit risk predictable beforehand | PARTIALLY SUPPORTED |
| OT provides an early warning | NOT SUPPORTED |
| Latent hazard improves long-horizon point prediction | NOT SUPPORTED |
| FIRED attributes a physical cause | NOT IDENTIFIABLE |
| Robust universal 2/3 restoration after shocks | NOT SUPPORTED |

## Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=src ../cubedynamics/.venv/bin/python \
  scripts/run_latent_constraint_validation.py
```

Outputs are in `outputs/latent_constraint_validation/`.

