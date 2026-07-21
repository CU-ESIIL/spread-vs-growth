# Scripts

Put repeatable figure and animation entry points here.

Scripts should write bulky renders to `outputs/` and keep final web-ready assets under `docs/assets/` only when they are intentionally part of the website.

## Side-by-side source video

```bash
python scripts/make_side_by_side_video.py
```

The default render places the ink diffusion clip on the left and the slime-mold timelapse on the right, writing `outputs/animations/ink_vs_slime_mold.mp4`.

By default, the script renders a standard `1920x1080` H.264 MP4 for better compatibility with QuickTime, browsers, and presentation software.

## Perimeter and area measurements

```bash
python scripts/measure_perimeter_growth.py
```

The script samples stages from the ink diffusion and slime-mold videos, traces the largest foreground perimeter polygon, and writes:

- `outputs/measurements/perimeter_area_timeseries.csv`
- `outputs/measurements/perimeter_polygons.json`
- overlay PNGs in `outputs/figures/perimeter_overlays/`
- log area-vs-perimeter graph at `outputs/figures/log_area_vs_perimeter.png`

## Fire-model scaling experiments

```bash
PYTHONPATH=src python -m unittest discover -s tests
python scripts/run_fire_model_scaling.py
```

The workflow runs the exact ellipse benchmark plus Huygens, level-set, and cellular emulators. It writes perimeter-area metrics, scaling fits, comparison figures, and status logs for actual ELMFIRE and Cell2Fire attempts.

## Dense model hexbin plot

```bash
python scripts/make_model_hexbin_plot.py
```

This longer figure run generates a dense cloud of homogeneous and anisotropic model outputs, then renders a reference-style log-log hexbin plot at `outputs/figures/model_outputs_hexbin.png`. Use `--reuse-metrics` to redraw from `outputs/metrics/model_hexbin_metrics.csv` without rerunning the emulators.

To add rougher model-output variance, include explicit heterogeneity strengths and write a separate figure:

```bash
python scripts/make_model_hexbin_plot.py \
  --output-name model_outputs_hexbin_more_heterogeneity \
  --heterogeneity-levels 0.25 0.5 0.75
```

To isolate one model from an existing dense metrics table:

```bash
python scripts/make_model_hexbin_plot.py \
  --output-name level_set_hexbin_more_heterogeneity \
  --input-metrics outputs/metrics/model_outputs_hexbin_more_heterogeneity_metrics.csv \
  --heterogeneity-levels 0.25 0.5 0.75 \
  --reuse-metrics \
  --models level_set_emulator
```

To compare everything except the level-set emulator, list the other model ids:

```bash
python scripts/make_model_hexbin_plot.py \
  --output-name no_level_set_hexbin_more_heterogeneity \
  --input-metrics outputs/metrics/model_outputs_hexbin_more_heterogeneity_metrics.csv \
  --heterogeneity-levels 0.25 0.5 0.75 \
  --reuse-metrics \
  --models exact_ellipse huygens_emulator cellular_emulator
```

Add `--hide-high-reference-lines` to omit the `2/3` and `3/4` reference lines while keeping the `1/2` and fitted-slope lines.

## Model hexbin reveal animation

```bash
python scripts/animate_model_hexbin_reveal.py
```

This renders the no-level-set heterogeneous model outputs as a left-to-right reveal animation, starting with no visible model data and ending with the full model cloud. The default output is `outputs/animations/no_level_set_hexbin_reveal.mp4`, a `1920x1080`, 30 fps, 8-second H.264 MP4 that keeps only the `1/2` reference line and fitted model-cloud slope.

## Reference-line-only animation

```bash
python scripts/animate_reference_lines_only.py
```

This renders a data-free log-log reference animation with only the red `P proportional to A^(1/2)` and blue `P proportional to A^(2/3)` lines. The red line is present from the first frame, and the blue line draws on from left to right. The default output is `outputs/animations/reference_lines_red_blue_only.mp4`, a `1920x1080`, 30 fps, 6-second H.264 MP4.

## Add two-thirds line to event image

```bash
python scripts/add_two_thirds_line_to_image.py --source path/to/event_hexbin.png
```

This overlays the blue `P proportional to A^(2/3)` reference line onto an existing log-log event-hexbin PNG. The default output is `outputs/figures/event_hexbin_with_blue_two_thirds.png`.

## Model-run handoff dataset

```bash
python scripts/export_model_run_dataset.py
```

This packages the dense heterogeneous model outputs into `outputs/datasets/model_hexbin_handoff/`, including one complete CSV, separate level-set and non-level-set CSVs, a fit summary, data dictionary, manifest, and zip archive for handoff to another plotting workflow.

## Grass-fire two-thirds animation

```bash
python scripts/animate_grass_fire_two_thirds.py
```

This calibrates and renders a deterministic grassland fire animation whose measured perimeter-area scaling is near `P proportional to A^(2/3)`. Outputs are written to `outputs/grass_fire_two_thirds/`, including diagnostic and clean MP4s, a final frame, scaling plot, metrics CSV, accepted parameters JSON, and an output README.

## Fire context explainer animation

```bash
python scripts/animate_fire_contexts_explainer.py
```

This reuses the accepted two-thirds fire-growth footprint and renders a flatter perspective explainer across grassland, forest, and WUI ground planes. The default output is `outputs/grass_fire_two_thirds/grass_forest_wui_growth_explainer.mp4`, with a final frame and metadata JSON beside it.
