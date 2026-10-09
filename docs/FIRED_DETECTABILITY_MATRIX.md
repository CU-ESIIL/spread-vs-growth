# FIRED Detectability Matrix

| Process or state | Direct | Derived | Before onset | At onset | Retrospective | Cause identifiable | External data needed |
|---|---|---|---|---|---|---|---|
| Mapped area growth | yes | no | forecastable | yes | yes | n/a | no |
| Mapped perimeter geometry | yes | local slope | partial | yes | yes | no | active-boundary data |
| Compatibility with 2/3 | no | model-dependent | weak | yes | yes | no | active perimeter and forcing |
| Geometric restoration | no | estimator-dependent | weak | partial | yes | no | repeated high-resolution boundaries |
| Realized coupling `BK` | no | yes | forecastable | yes | yes | no | no for the product |
| Endogenous coupling `K` | no | not separately | no | no | no | no | independent realization data |
| Coherence `C` | no | latent | no | no | no | no | coherence observations |
| Reachable fuel `F` | no | latent | no | no | no | no | fuels/connectivity layers |
| Spatial reorganization `R` | footprint-derived | yes | weak | yes | yes | no | no for mapped `R` |
| Negative realization residual | no | predictor-dependent | probabilistic | partial | yes | no | no for detection |
| Realization factor `B` | no | not identified | no | no | no | no | independent constraint data |
| Generic constraint-like event | no | statistical label | modest risk skill | partial | yes | no | independent validation layers |
| Suppression | no | no | no | no | no | no | incident/resource records |
| Water barrier | no | no | no | no | no | no | surface-water layers |
| Urban barrier | no | no | no | no | no | no | impervious/urban layers |
| Mapped termination | yes after ending | hazard-derived | partial | partial | yes | cause no | active-fire/incident data |

The correct endpoint for FIRED-only inference is usually **constraint-like**.
Attribution requires independent spatial or incident evidence.

