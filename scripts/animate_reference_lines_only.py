"""Animate reference perimeter-area scaling lines without data."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TMP_DIR = PROJECT_ROOT / "tmp"
(TMP_DIR / "matplotlib").mkdir(parents=True, exist_ok=True)
(TMP_DIR / "cache").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(TMP_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(TMP_DIR / "cache"))

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import numpy as np


def frame_array(fig: plt.Figure) -> np.ndarray:
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()


def write_reference_animation(
    output_path: Path,
    *,
    duration_seconds: float,
    fps: int,
    coefficient: float,
) -> dict[str, object]:
    frame_count = max(2, int(round(duration_seconds * fps)))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    x_min, x_max = 0.85, 420.0
    y_min, y_max = 2.4, 320.0
    x = np.logspace(np.log10(x_min), np.log10(x_max), 220)
    red_y = coefficient * x**0.5
    blue_y = coefficient * x ** (2.0 / 3.0)

    fig, ax = plt.subplots(figsize=(16, 9), dpi=120)
    fig.subplots_adjust(left=0.085, right=0.97, bottom=0.12, top=0.96)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_xlabel(r"Fire event area (km$^2$, log scale)", fontsize=18)
    ax.set_ylabel("Fire event perimeter (km, log scale)", fontsize=18)
    ax.tick_params(axis="both", which="major", labelsize=16, length=7, width=1.0)
    ax.tick_params(axis="both", which="minor", length=3.5, width=0.8)
    ax.grid(True, which="major", color="#d9d9d9", linewidth=0.8, alpha=0.75)
    ax.grid(False, which="minor")

    red_line, = ax.plot(
        x,
        red_y,
        color="#b22222",
        linestyle=(0, (8, 5)),
        linewidth=4.2,
        label=r"diffusion-like spread: $P \propto A^{1/2}$",
    )
    blue_line, = ax.plot(
        [],
        [],
        color="#5f87e9",
        linestyle="-",
        linewidth=4.2,
        label=r"organized growth: $P \propto A^{2/3}$",
    )
    ax.legend(frameon=False, fontsize=15, loc="lower right", handlelength=2.7)

    with imageio.get_writer(
        output_path,
        fps=fps,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=1,
    ) as writer:
        for frame in range(frame_count):
            progress = frame / (frame_count - 1)
            count = max(2, int(round(progress * (len(x) - 1))) + 1)
            blue_line.set_data(x[:count], blue_y[:count])
            writer.append_data(frame_array(fig))

    plt.close(fig)
    return {
        "output": str(output_path),
        "frames": frame_count,
        "fps": fps,
        "duration_seconds": frame_count / fps,
        "width": 1920,
        "height": 1080,
        "red_line": f"P = {coefficient:.6g} * A^0.5",
        "blue_line": f"P = {coefficient:.6g} * A^(2/3)",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "animations" / "reference_lines_red_blue_only.mp4",
    )
    parser.add_argument("--duration-seconds", type=float, default=6.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument(
        "--coefficient",
        type=float,
        default=4.107439,
        help="Shared coefficient so both references begin in the same visual location.",
    )
    args = parser.parse_args()

    metadata = write_reference_animation(
        args.output,
        duration_seconds=args.duration_seconds,
        fps=args.fps,
        coefficient=args.coefficient,
    )
    print(
        "Wrote {output} ({frames} frames, {width}x{height}, {fps} fps); "
        "{red_line}; {blue_line}".format(**metadata)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
