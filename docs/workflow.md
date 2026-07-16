# Figure And Animation Workflow

Use the repository as the reproducible control layer and keep large generated artifacts local.

## Local Workspaces

| Path | Purpose | Git policy |
| --- | --- | --- |
| `data/raw/` | Source data and large external inputs | ignored |
| `data/interim/` | Intermediate tables, rasters, arrays, caches | ignored |
| `data/processed/` | Analysis-ready derived data | ignored |
| `outputs/figures/` | Static figure exports | ignored |
| `outputs/animations/` | Frames, clips, and rendered animations | ignored |
| `tmp/` | Temporary render checks and scratch artifacts | ignored |

## Recommended Pattern

1. Prototype visual ideas in `notebooks/`.
2. Move repeatable work into `scripts/` once a figure or animation starts to stabilize.
3. Put shared path and utility code in `src/spread_vs_growth/`.
4. Save heavy outputs to `outputs/`.
5. Promote only final, web-sized assets to `docs/assets/`.

## Long Runs

- Make scripts restartable by writing checkpoints or frame batches.
- Record data source, access method, license, and citation needs before adding new data.
- Keep random seeds and major parameter choices visible near the script entry point.
- Prefer small preview renders before committing to full-resolution animation runs.

## Current Animation Utilities

- `scripts/make_side_by_side_video.py` combines the ink diffusion video and slime-mold growth video into one side-by-side, presentation-friendly H.264 MP4 under `outputs/animations/`.
- `scripts/measure_perimeter_growth.py` samples each source video, traces perimeter polygons, and writes area/perimeter time series, log area-vs-perimeter plots, and visual overlays under `outputs/`.
