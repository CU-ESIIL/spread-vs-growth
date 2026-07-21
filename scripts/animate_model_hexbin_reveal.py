"""Animate the non-level-set model hexbin cloud appearing left to right."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

TMP_DIR = PROJECT_ROOT / "tmp"
(TMP_DIR / "matplotlib").mkdir(parents=True, exist_ok=True)
(TMP_DIR / "cache").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(TMP_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(TMP_DIR / "cache"))

import imageio.v2 as imageio
import matplotlib.cm as cm
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

from fire_model_scaling.fit_scaling import ols_loglog
from make_model_hexbin_plot import add_power_law_line, read_csv, valid_xy


DEFAULT_MODELS = ["exact_ellipse", "huygens_emulator", "cellular_emulator"]
DEFAULT_HETEROGENEITY_LEVELS = [0.25, 0.5, 0.75]


def filter_rows(rows: list[dict[str, object]], models: list[str]) -> list[dict[str, object]]:
    model_set = set(models)
    return [row for row in rows if str(row["model"]) in model_set]


def final_hexbin_max(area: np.ndarray, perimeter: np.ndarray, gridsize: int) -> int:
    fig, ax = plt.subplots()
    hexbin = ax.hexbin(
        area,
        perimeter,
        xscale="log",
        yscale="log",
        gridsize=gridsize,
        mincnt=1,
    )
    counts = hexbin.get_array()
    plt.close(fig)
    return max(1, int(np.max(counts)))


def render_frame_array(fig: plt.Figure) -> np.ndarray:
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()


def write_reveal_animation(
    rows: list[dict[str, object]],
    output_path: Path,
    *,
    models: list[str],
    heterogeneity_levels: list[float],
    duration_seconds: float,
    fps: int,
    gridsize: int,
) -> dict[str, float | int | str]:
    area, perimeter, valid_rows = valid_xy(rows)
    if len(area) < 10:
        raise ValueError("Not enough valid model outputs to animate.")

    fit_alpha, fit_sigma, _, _, _, _ = ols_loglog(area, perimeter)
    x_min = float(np.percentile(area, 0.5))
    x_max = float(np.percentile(area, 99.5))
    y_min = float(np.percentile(perimeter, 0.5))
    y_max = float(np.percentile(perimeter, 99.5))
    lx_min = float(np.log10(np.min(area)))
    lx_max = float(np.log10(np.max(area)))
    line_x = np.logspace(np.log10(x_min), np.log10(x_max), 200)
    max_count = final_hexbin_max(area, perimeter, gridsize)

    frame_count = max(2, int(round(duration_seconds * fps)))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(16, 9), dpi=120)
    fig.subplots_adjust(left=0.085, right=0.885, bottom=0.12, top=0.96)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(x_min * 0.85, x_max * 1.15)
    ax.set_ylim(y_min * 0.85, y_max * 1.3)
    ax.set_xlabel(r"Model fire area (km$^2$, log scale)", fontsize=18)
    ax.set_ylabel("Model fire perimeter (km, log scale)", fontsize=18)
    ax.tick_params(axis="both", which="major", labelsize=16, length=7, width=1.0)
    ax.tick_params(axis="both", which="minor", length=3.5, width=0.8)
    ax.grid(True, which="major", color="#d9d9d9", linewidth=0.8, alpha=0.75)
    ax.grid(False, which="minor")
    ax.set_axisbelow(True)

    add_power_law_line(
        ax,
        line_x,
        coefficient=10.0**fit_alpha,
        exponent=0.5,
        color="#b22222",
        linestyle=(0, (8, 5)),
        label=r"diffusion-like spread: $P \propto A^{1/2}$",
    )
    add_power_law_line(
        ax,
        line_x,
        coefficient=10.0**fit_alpha,
        exponent=fit_sigma,
        color="#555555",
        linestyle=":",
        label=fr"model fit: slope {fit_sigma:.2f}",
        linewidth=1.8,
    )
    ax.legend(frameon=False, fontsize=14, loc="lower right", handlelength=2.7)

    mappable = cm.ScalarMappable(norm=LogNorm(vmin=1, vmax=max_count), cmap="magma_r")
    colorbar = fig.colorbar(mappable, ax=ax, pad=0.012)
    colorbar.set_label("Model outputs per hexbin", fontsize=17)
    colorbar.ax.tick_params(labelsize=14)

    summary = ax.text(
        0.02,
        0.96,
        "",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=12,
        color="#333333",
        zorder=5,
    )

    hexbin_artist = None
    log_area = np.log10(area)
    model_summary = ", ".join(models)
    heterogeneity_summary = ", ".join(f"{level:g}" for level in heterogeneity_levels)

    with imageio.get_writer(
        output_path,
        fps=fps,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=1,
    ) as writer:
        for frame_index in range(frame_count):
            if hexbin_artist is not None:
                hexbin_artist.remove()
                hexbin_artist = None

            progress = frame_index / (frame_count - 1)
            if frame_index == 0:
                visible = np.zeros_like(area, dtype=bool)
            elif frame_index == frame_count - 1:
                visible = np.ones_like(area, dtype=bool)
            else:
                threshold = lx_min + progress * (lx_max - lx_min)
                visible = log_area <= threshold

            shown = int(np.count_nonzero(visible))
            if shown:
                hexbin_artist = ax.hexbin(
                    area[visible],
                    perimeter[visible],
                    xscale="log",
                    yscale="log",
                    gridsize=gridsize,
                    mincnt=1,
                    linewidths=0.0,
                    cmap="magma_r",
                    norm=LogNorm(vmin=1, vmax=max_count),
                    zorder=1,
                )

            summary.set_text(
                f"shown={shown:,} / {len(valid_rows):,}\n"
                f"model cloud fit: {fit_sigma:.2f}\n"
                f"{model_summary}\n"
                f"heterogeneity: {heterogeneity_summary}"
            )
            writer.append_data(render_frame_array(fig))

    plt.close(fig)
    return {
        "output": str(output_path),
        "frames": frame_count,
        "fps": fps,
        "duration_seconds": frame_count / fps,
        "valid_outputs": len(valid_rows),
        "fit_slope": float(fit_sigma),
        "max_hexbin_count": max_count,
        "width": 1920,
        "height": 1080,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-metrics",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "metrics" / "model_outputs_hexbin_more_heterogeneity_metrics.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "animations" / "no_level_set_hexbin_reveal.mp4",
    )
    parser.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    parser.add_argument("--heterogeneity-levels", nargs="*", type=float, default=DEFAULT_HETEROGENEITY_LEVELS)
    parser.add_argument("--duration-seconds", type=float, default=8.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--gridsize", type=int, default=64)
    args = parser.parse_args()

    rows = filter_rows(read_csv(args.input_metrics), args.models)
    metadata = write_reveal_animation(
        rows,
        args.output,
        models=args.models,
        heterogeneity_levels=args.heterogeneity_levels,
        duration_seconds=args.duration_seconds,
        fps=args.fps,
        gridsize=args.gridsize,
    )

    print(
        "Wrote {output} ({frames} frames, {width}x{height}, {fps} fps); "
        "valid outputs={valid_outputs:,}, fit slope={fit_slope:.4f}".format(**metadata)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
