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
