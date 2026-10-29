# Fire Geometry Results Poster

The 36 x 24 inch landscape poster presents the repository's clearest current
empirical contrast in one page:

1. FIRED between-fire geometry has a fitted exponent of `0.646`, near the
   two-thirds reference and far from one-half.
2. The summer smooth-front model cloud has a fitted exponent of `0.506`.
   Exact-ellipse, Huygens-wavelet, normal-front level-set, and
   cellular-neighbor benchmarks all remain much closer to one-half than
   two-thirds.
3. Multivariate mapped geometry improves held-out future-area and acceleration
   prediction beyond area and recent dynamics.

The bottom evidence boundary distinguishes the smooth-front benchmark result
from a universal claim about every parameterized front. A deliberately
amplified heterogeneous level-set emulator can approach two-thirds, so the
exponent alone does not identify mechanism and still requires matched
prospective operational tests.

## Build

The builder reads the locked FIRED sequence/geometry tables and the model-run
handoff dataset, then draws both scaling panels directly as vector PDF
elements. The red one-half benchmark is normalized explicitly as
`log10(P) = 0.5 log10(A)`, with intercept fixed at zero. The black dotted lines
retain fitted intercepts and therefore remain visually distinct from that
normalization hypothesis.

```bash
/Users/tuff/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/build_results_poster.py
```

The final PDF is written to
`output/pdf/fire_geometry_state_prediction_poster.pdf`. Temporary figure crops
remain under `tmp/pdfs/results_poster/` and are ignored by git.

## Origin-anchored regression variant

The second poster emphasizes the visual argument in the talk: local-front
benchmarks remain near one-half while the FIRED between-fire population lies
near two-thirds, and mapped geometry then becomes a state for detection and
prediction. Its two scaling panels use dimensionless relative coordinates,
`log10(A/A0)` and `log10(P/P0)`, anchored at the low-scale fitted origin of
each cloud. Both reference laws and the fitted regression therefore visibly
begin at `(0,0)`, so the panel compares exponents without silently importing a
dimensional coefficient. The poster uses a white background and minimal rules
rather than tinted content panels.

```bash
/Users/tuff/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/build_scaling_prediction_poster_v2.py
```

This variant is written to
`output/pdf/fire_scaling_prediction_poster_v2.pdf`.

## Source panels

- `outputs/fired_prediction/fired_sequences.csv.gz`
- `outputs/fired_lifecycle_prediction/fired_geometry_sequences.csv.gz`
- `outputs/datasets/model_hexbin_handoff/model_runs_other_models.csv`
- `output/manuscript/figure_prediction.png`

Prediction panels use held-out FIRED years 2016-2020, and their uncertainty
intervals resample whole fires.
