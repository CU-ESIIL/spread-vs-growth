"""Overlay a blue two-thirds reference line on an existing log-log PNG."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def affine_from_ticks(ticks: dict[float, float]) -> tuple[float, float]:
    values = [math.log10(value) for value in ticks]
    pixels = list(ticks.values())
    mean_value = sum(values) / len(values)
    mean_pixel = sum(pixels) / len(pixels)
    slope = sum((value - mean_value) * (pixel - mean_pixel) for value, pixel in zip(values, pixels)) / sum(
        (value - mean_value) ** 2 for value in values
    )
    intercept = mean_pixel - slope * mean_value
    return intercept, slope


def overlay_line(
    source: Path,
    output: Path,
    *,
    coefficient: float,
    exponent: float,
    line_width: int,
    alpha: int,
) -> None:
    image = Image.open(source).convert("RGBA")

    # Defaults are calibrated to the pasted event-hexbin figure screenshot.
    plot_left = 184.0
    plot_right = 1710.0
    plot_top = 68.0
    plot_bottom = 1002.0
    x_intercept, x_slope = affine_from_ticks({1.0: 424.0, 10.0: 767.0, 100.0: 1110.0, 1000.0: 1453.0})
    y_intercept, y_slope = affine_from_ticks({10.0: 732.0, 100.0: 461.0, 1000.0: 191.0})

    def x_to_pixel(area: float) -> float:
        return x_intercept + x_slope * math.log10(area)

    def y_to_pixel(perimeter: float) -> float:
        return y_intercept + y_slope * math.log10(perimeter)

    area_min = 10 ** ((plot_left - x_intercept) / x_slope)
    area_max = 10 ** ((plot_right - x_intercept) / x_slope)
    points = []
    for index in range(900):
        area = 10 ** (math.log10(area_min) + (math.log10(area_max) - math.log10(area_min)) * index / 899)
        perimeter = coefficient * area**exponent
        x = x_to_pixel(area)
        y = y_to_pixel(perimeter)
        if plot_left <= x <= plot_right and plot_top <= y <= plot_bottom:
            points.append((x, y))

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if len(points) >= 2:
        draw.line(points, fill=(100, 149, 237, alpha), width=line_width, joint="curve")

    output.parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(image, overlay).convert("RGB").save(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "figures" / "event_hexbin_with_blue_two_thirds.png",
    )
    parser.add_argument(
        "--coefficient",
        type=float,
        default=1.3,
        help="Coefficient in P = coefficient * A^exponent; lower values visually continue from the lower-left origin.",
    )
    parser.add_argument("--exponent", type=float, default=2.0 / 3.0)
    parser.add_argument("--line-width", type=int, default=12)
    parser.add_argument("--alpha", type=int, default=150)
    args = parser.parse_args()

    overlay_line(
        args.source,
        args.output,
        coefficient=args.coefficient,
        exponent=args.exponent,
        line_width=args.line_width,
        alpha=args.alpha,
    )
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
