# Optimal-Transport Validation

## Question

This experiment asks whether footprint change contains information beyond the
amount of area added. It does not treat burned material as physically moving.
For each observed transition, the analysis constructs an area-matched simple
growth null by isotropically dilating the actual starting footprint to the
observed final area. Spatial reorganization is

```text
R = sliced-W2(actual final footprint, area-matched dilation) / sqrt(final area).
```

The numerator is balanced sliced Wasserstein distance on a common metric
raster. The normalization is prespecified and dimensionless. Geographic and
translation-normalized variants, a KL-relaxed unbalanced distance, and simpler
spatial metrics are retained as sensitivity analyses.

## Locked design

The run reuses the established FIRED cohort and year split. OT is computed for
an outcome-blind random sample of 300 eligible fires per partition, with all
42+ day fires added only to the descriptive long-fire analysis. The resulting
table contains 9,035 real transitions from 935 fires; 900 fires belong to the
primary sample. No held-out outcome was used to select the sample, resolution,
distance, or null.

The primary raster scale is 500 m. Very large extents are coarsened to a
maximum of 320 cells per side, and the effective resolution is recorded for
every row. Balanced OT uses 16 fixed projections and 128 quantiles. The
unbalanced sensitivity uses a squared ground cost, entropic regularization
`epsilon=0.05`, KL mass penalty `rho=1`, and convergence tolerance `1e-6`.
Convergence was 99.97%. Median area mismatch in the vector dilation null was
`3.7e-8` in relative terms.

## Does R respond to known spatial changes?

Yes, with qualifications. In synthetic checks the isotropic case had nearly
zero R (`0.013`, residual rasterization error), while directional expansion,
finger formation, component merging, fragmented growth, and translated growth
ranged from `0.23` to `0.33`. The examples show that equal or similar area
addition can produce different R.

The benchmark is not exhaustive. Hole filling is almost identical to its
dilation null in the current construction, and therefore has near-zero R. R is
a departure from this particular null, not a universal measure of all
topological change.

## Does OT add information beyond simpler metrics?

Not uniquely. Held-out transition-level rank correlations with primary R are:

| Metric | Spearman correlation with R |
| --- | ---: |
| Translation-normalized sliced W2 | 0.950 |
| IoU | -0.726 |
| Centroid displacement | 0.698 |
| Symmetric-difference area | 0.529 |
| Hausdorff distance | 0.484 |
| Perimeter difference | 0.470 |

Primary R has a `0.232` rank correlation with geometric restoration. The
translation-normalized variant is `0.239`, while IoU reaches `-0.244` and
centroid displacement `0.224`. Thus OT summarizes useful spatial information,
but inexpensive overlap and displacement metrics capture much of the same
signal. In prediction, adding the simple metrics to geometry produced intervals
that overlapped zero at every tested day-7-origin lead, whereas adding OT gave
clear gains from 5 through 49 days. OT therefore earns some predictive value
in this design, without establishing a uniquely physical interpretation.

## Resolution and temporal sensitivity

R is fairly stable around the native-scale choice but not scale invariant.
Against 500 m estimates, rank correlations are `0.882` at 250 m, `0.857` at
1 km, and `0.700` at 2 km across 188 transitions. Median R rises as the grid is
coarsened. Claims therefore apply to mapped FIRED footprints at the tested
scales, not to an active flame front.

Median R is `0.036` for one-day transitions and `0.129` for three-day
transitions. Longer gaps have much smaller samples and larger values. Temporal
resolution is part of the measurement definition and must be controlled in
all models.

## Interpretation

The defensible interpretation is:

> R measures departure of a mapped final footprint from an area-matched
> isotropic expansion of its observed starting footprint.

It is not literal fire transport, coherence, metabolism, energetic flux, or
evidence that the boundary optimizes an objective.

## Reproduction

```bash
MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  ../cubedynamics/.venv/bin/python scripts/extract_fired_transport_metrics.py

MPLCONFIGDIR=tmp/matplotlib-cache PYTHONPATH=src \
  ../cubedynamics/.venv/bin/python scripts/run_integrated_geometry_transport.py
```

The first command requires GeoPandas, Shapely, Rasterio, and PyArrow. The data
source, solver settings, sampled event IDs, numerical diagnostics, and all
machine-readable results are under `outputs/integrated_geometry_transport/`.
