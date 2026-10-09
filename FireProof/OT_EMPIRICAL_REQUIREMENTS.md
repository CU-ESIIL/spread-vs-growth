# OT Empirical Requirements

This file is the handoff between held-out FIRED tests and candidate Lean
closures. A convenient closure is not promoted into the core theory unless the
corresponding empirical result supports it.

| Candidate closure | Why needed | FIRED test | Result | Status |
| --- | --- | --- | --- | --- |
| `R >= 0` | Definition-level order result | Numerical QA | All primary R values nonnegative | Supported mathematically and computationally |
| `R=0 iff actual=null` | Identifies exact simple growth | Synthetic identity and raster QA | Near-zero rather than exact zero after rasterization | Mathematical under separating distance; approximate empirically |
| Larger `|sigma-2/3|` predicts larger R | First mechanistic arrow | Held-out regression with area, growth, age controls | coefficient 0.0129, 95% interval [0.0085, 0.0184] | Supported association |
| Larger R predicts restoration | Second mechanistic arrow | Held-out whole-fire bootstrap and within-fire model | overall coefficient 0.022, interval [-0.238, 0.364]; asymmetric | Not supported overall |
| `K_future = H(K,R)` | Point predictive closure | Held-out ridge models | R adds small information but residual uncertainty remains large | Not supported as deterministic equality |
| `K_future in [L(R),U(R)]` | Strictly narrows admissible futures | Paired held-out models and interval calibration still required | mean prediction improves from 5 days onward | Partially supported; interval coverage not yet formalized |
| R adds beyond current geometry | Makes spatial extension nonredundant | Geometry plus OT versus geometry alone | no gain at 1-3 days; small paired gain at 5-49 days | Partially supported |
| OT adds beyond simple spatial metrics | Justifies Wasserstein complexity | Geometry+OT versus geometry+simple metrics | simple-metric intervals span zero; OT gains are clear from 5 days onward | Partially supported predictively |
| R identifies C or F | Resolves latent mechanism | Structural counterexamples; no independent FIRED C/F data | impossible with current observables | Not identifiable |

## Exact closure statement for future work

The most defensible next formal-empirical target is not a point equation. It is
a calibrated conditional interval:

```text
P(K_future in [L(K_current, geometry, R), U(K_current, geometry, R)]) >= 1-alpha
```

paired with a strict width comparison against the same interval without R.
FIRED can test marginal and subgroup coverage using whole-fire resampling.
Only if R reduces width while preserving held-out coverage should the Model 2
closure be promoted beyond an experimental namespace.

## Required data not present in FIRED

The current analysis cannot identify latent C, reachable fuel F, suppression
effort, active flame-front geometry, energetic flux, or a causal intervention
on reorganization. Those variables require independent fuel, weather,
incident-action, or active-fire observations. R must not be used as a circular
name for any of them.
