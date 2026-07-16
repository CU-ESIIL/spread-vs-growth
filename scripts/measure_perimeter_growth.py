"""Measure perimeter and area growth from the ink and slime-mold videos."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MPLCONFIG_DIR = PROJECT_ROOT / "tmp" / "matplotlib"
XDG_CACHE_DIR = PROJECT_ROOT / "tmp" / "cache"
MPLCONFIG_DIR.mkdir(parents=True, exist_ok=True)
XDG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIG_DIR))
os.environ.setdefault("XDG_CACHE_HOME", str(XDG_CACHE_DIR))

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw
from skimage import color, filters, measure, morphology, transform
from tqdm import tqdm


DEFAULT_INK = PROJECT_ROOT / "data" / "raw" / "3024109-hd_1920_1080_25fps.mp4"
DEFAULT_SLIME = (
    PROJECT_ROOT / "data" / "raw" / "Australian_physarum_polycephalum_timelapse.webm"
)
DEFAULT_MEASUREMENTS = PROJECT_ROOT / "outputs" / "measurements"
DEFAULT_OVERLAYS = PROJECT_ROOT / "outputs" / "figures" / "perimeter_overlays"
DEFAULT_PLOT = PROJECT_ROOT / "outputs" / "figures" / "log_area_vs_perimeter.png"


@dataclass(frozen=True)
class VideoSpec:
    name: str
    path: Path
    mode: str
    outline_color: tuple[int, int, int]


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def resize_for_processing(frame: np.ndarray, max_dimension: int) -> tuple[np.ndarray, float]:
    height, width = frame.shape[:2]
    largest = max(height, width)
    if largest <= max_dimension:
        return frame, 1.0

    scale = max_dimension / largest
    resized = transform.resize(
        frame,
        (round(height * scale), round(width * scale)),
        preserve_range=True,
        anti_aliasing=True,
    ).astype(np.uint8)
    return resized, 1.0 / scale


def largest_component(mask: np.ndarray, min_size: int) -> np.ndarray:
    cleaned = morphology.remove_small_objects(mask.astype(bool), max_size=min_size)
    cleaned = morphology.remove_small_holes(cleaned, max_size=min_size)
    cleaned = morphology.closing(cleaned, morphology.disk(3))
    labeled = measure.label(cleaned)
    regions = measure.regionprops(labeled)
    if not regions:
        return np.zeros_like(mask, dtype=bool)

    largest = max(regions, key=lambda region: region.area)
    return labeled == largest.label


def segment_ink(frame: np.ndarray, min_size: int) -> np.ndarray:
    rgb = frame.astype(np.float32) / 255.0
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    gray = rgb.mean(axis=2)

    blue_excess = np.clip(blue - np.maximum(red, green), 0, 1)
    darkness = np.clip(1.0 - gray, 0, 1)
    score = 0.55 * darkness + 0.45 * blue_excess
    threshold = filters.threshold_otsu(score)
    mask = score > max(threshold, 0.14)
    return largest_component(mask, min_size=min_size)


def segment_slime(frame: np.ndarray, min_size: int) -> np.ndarray:
    rgb = frame.astype(np.float32) / 255.0
    hsv = color.rgb2hsv(rgb)
    hue = hsv[:, :, 0]
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]

    yellow_green = (hue >= 0.11) & (hue <= 0.28)
    mask = yellow_green & (saturation >= 0.28) & (value >= 0.28)
    return largest_component(mask, min_size=min_size)


def contour_metrics(mask: np.ndarray, pixel_scale: float) -> tuple[list[list[float]], float, float]:
    padded_mask = np.pad(mask.astype(bool), pad_width=1, mode="constant", constant_values=False)
    contours = measure.find_contours(padded_mask.astype(float), level=0.5)
    if not contours:
        return [], 0.0, 0.0

    contour = max(contours, key=len) - 1.0
    contour[:, 0] = np.clip(contour[:, 0], 0, mask.shape[0] - 1)
    contour[:, 1] = np.clip(contour[:, 1], 0, mask.shape[1] - 1)
    # find_contours returns row, col. Store polygons as x, y in source-pixel units.
    xy = np.column_stack([contour[:, 1], contour[:, 0]]) * pixel_scale
    closed = np.vstack([xy, xy[0]])
    perimeter = float(np.sum(np.sqrt(np.sum(np.diff(closed, axis=0) ** 2, axis=1))))
    area = float(mask.sum() * pixel_scale * pixel_scale)
    polygon = [[round(float(x), 3), round(float(y), 3)] for x, y in xy]
    return polygon, area, perimeter


def draw_overlay(
    frame: np.ndarray,
    mask: np.ndarray,
    polygon: list[list[float]],
    pixel_scale: float,
    color_rgb: tuple[int, int, int],
    label: str,
    output_path: Path,
) -> None:
    image = Image.fromarray(frame).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    mask_image = Image.fromarray((mask.astype(np.uint8) * 85), mode="L")
    tint = Image.new("RGBA", image.size, (*color_rgb, 0))
    tint.putalpha(mask_image)
    overlay.alpha_composite(tint)

    draw = ImageDraw.Draw(overlay)
    scaled_polygon = [(x / pixel_scale, y / pixel_scale) for x, y in polygon]
    if len(scaled_polygon) > 1:
        draw.line(scaled_polygon + [scaled_polygon[0]], fill=(*color_rgb, 255), width=4)

    draw.rectangle((12, 12, 370, 58), fill=(255, 255, 255, 215))
    draw.text((24, 24), label, fill=(0, 0, 0, 255))
    image.alpha_composite(overlay)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path)


def reader_fps(reader: Any) -> float:
    fps = reader.get_meta_data().get("fps")
    if fps and math.isfinite(float(fps)) and float(fps) > 0:
        return float(fps)
    return 25.0


def reader_frame_count(reader: Any) -> int:
    try:
        count = reader.count_frames()
    except Exception as exc:
        raise ValueError("Could not count video frames") from exc

    if not math.isfinite(count) or count <= 0:
        raise ValueError("Video reports an invalid frame count")
    return int(count)


def sample_indices(frame_count: int, stages: int) -> list[tuple[int, float]]:
    if stages == 1:
        return [(frame_count - 1, 1.0)]
    progress_values = np.linspace(0.05, 0.95, stages)
    return [
        (min(frame_count - 1, max(0, round(float(progress) * (frame_count - 1)))), float(progress))
        for progress in progress_values
    ]


def process_video(
    spec: VideoSpec,
    stages: int,
    max_dimension: int,
    min_size: int,
    overlay_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    reader = imageio.get_reader(spec.path)
    rows: list[dict[str, Any]] = []
    polygons: list[dict[str, Any]] = []

    try:
        fps = reader_fps(reader)
        frame_count = reader_frame_count(reader)
        samples = sample_indices(frame_count, stages)

        for stage_number, (frame_index, progress) in enumerate(
            tqdm(samples, desc=f"Tracing {spec.name}"), start=1
        ):
            source_frame = reader.get_data(frame_index)
            frame, pixel_scale = resize_for_processing(source_frame, max_dimension)

            if spec.mode == "ink":
                mask = segment_ink(frame, min_size=min_size)
            elif spec.mode == "slime":
                mask = segment_slime(frame, min_size=min_size)
            else:
                raise ValueError(f"Unknown segmentation mode: {spec.mode}")

            polygon, area_px, perimeter_px = contour_metrics(mask, pixel_scale)
            time_s = frame_index / fps
            overlay_path = (
                overlay_dir / f"{spec.name}_stage_{stage_number:02d}_frame_{frame_index:04d}.png"
            )
            label = (
                f"{spec.name} stage {stage_number} | "
                f"t={time_s:.2f}s | area={area_px:.0f}px2 | perimeter={perimeter_px:.0f}px"
            )
            draw_overlay(
                frame=frame,
                mask=mask,
                polygon=polygon,
                pixel_scale=pixel_scale,
                color_rgb=spec.outline_color,
                label=label,
                output_path=overlay_path,
            )

            processed_h, processed_w = frame.shape[:2]
            source_h, source_w = source_frame.shape[:2]
            rows.append(
                {
                    "subject": spec.name,
                    "source_video": str(spec.path),
                    "stage": stage_number,
                    "progress": round(progress, 4),
                    "frame_index": frame_index,
                    "time_s": round(time_s, 4),
                    "source_width_px": source_w,
                    "source_height_px": source_h,
                    "processed_width_px": processed_w,
                    "processed_height_px": processed_h,
                    "pixel_scale_to_source": round(pixel_scale, 6),
                    "area_px2_est": round(area_px, 3),
                    "perimeter_px_est": round(perimeter_px, 3),
                    "area_fraction": round(float(mask.sum() / mask.size), 8),
                    "polygon_vertex_count": len(polygon),
                    "overlay_path": str(overlay_path),
                }
            )
            polygons.append(
                {
                    "subject": spec.name,
                    "stage": stage_number,
                    "progress": progress,
                    "frame_index": frame_index,
                    "time_s": time_s,
                    "pixel_scale_to_source": pixel_scale,
                    "coordinates_source_px": polygon,
                }
            )
    finally:
        reader.close()

    return rows, polygons


def fit_log_slope(rows: list[dict[str, Any]]) -> tuple[float, float] | None:
    area = np.array([float(row["area_px2_est"]) for row in rows])
    perimeter = np.array([float(row["perimeter_px_est"]) for row in rows])
    keep = (area > 0) & (perimeter > 0)
    if keep.sum() < 2:
        return None

    slope, intercept = np.polyfit(np.log10(area[keep]), np.log10(perimeter[keep]), 1)
    return float(slope), float(intercept)


def plot_log_area_vs_perimeter(rows: list[dict[str, Any]], output_path: Path) -> None:
    subjects = ["ink_diffusion", "slime_mold"]
    colors = {
        "ink_diffusion": "#1450dc",
        "slime_mold": "#e6501e",
    }
    titles = {
        "ink_diffusion": "Ink diffusion",
        "slime_mold": "Slime mold",
    }

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    for axis, subject in zip(axes, subjects, strict=True):
        subject_rows = [row for row in rows if row["subject"] == subject]
        area = np.array([float(row["area_px2_est"]) for row in subject_rows])
        perimeter = np.array([float(row["perimeter_px_est"]) for row in subject_rows])
        stages = [int(row["stage"]) for row in subject_rows]

        axis.plot(area, perimeter, color=colors[subject], linewidth=1.6, alpha=0.75)
        axis.scatter(area, perimeter, color=colors[subject], s=46, zorder=3)
        for x_value, y_value, stage in zip(area, perimeter, stages, strict=True):
            axis.annotate(
                str(stage),
                (x_value, y_value),
                xytext=(5, 4),
                textcoords="offset points",
                fontsize=8,
            )

        fit = fit_log_slope(subject_rows)
        title = titles[subject]
        if fit is not None:
            slope, intercept = fit
            x_fit = np.linspace(area[area > 0].min(), area.max(), 100)
            y_fit = 10 ** (intercept + slope * np.log10(x_fit))
            axis.plot(x_fit, y_fit, color="black", linestyle="--", linewidth=1.0)
            title = f"{title} | slope={slope:.2f}"

        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_title(title)
        axis.set_xlabel("Area (px^2, log scale)")
        axis.set_ylabel("Perimeter (px, log scale)")
        axis.grid(True, which="both", color="#d9d9d9", linewidth=0.6)

    fig.suptitle("Log Area vs. Perimeter Across Sampled Growth Stages", fontsize=14)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trace perimeter polygons and area/perimeter metrics from source videos."
    )
    parser.add_argument("--ink-video", type=Path, default=DEFAULT_INK)
    parser.add_argument("--slime-video", type=Path, default=DEFAULT_SLIME)
    parser.add_argument("--stages", type=positive_int, default=8)
    parser.add_argument("--max-dimension", type=positive_int, default=900)
    parser.add_argument("--min-size", type=positive_int, default=300)
    parser.add_argument("--measurements-dir", type=Path, default=DEFAULT_MEASUREMENTS)
    parser.add_argument("--overlay-dir", type=Path, default=DEFAULT_OVERLAYS)
    parser.add_argument("--plot-path", type=Path, default=DEFAULT_PLOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    specs = [
        VideoSpec("ink_diffusion", args.ink_video, "ink", (20, 80, 220)),
        VideoSpec("slime_mold", args.slime_video, "slime", (230, 80, 30)),
    ]

    try:
        all_rows: list[dict[str, Any]] = []
        all_polygons: list[dict[str, Any]] = []
        for spec in specs:
            rows, polygons = process_video(
                spec=spec,
                stages=args.stages,
                max_dimension=args.max_dimension,
                min_size=args.min_size,
                overlay_dir=args.overlay_dir,
            )
            all_rows.extend(rows)
            all_polygons.extend(polygons)

        args.measurements_dir.mkdir(parents=True, exist_ok=True)
        csv_path = args.measurements_dir / "perimeter_area_timeseries.csv"
        json_path = args.measurements_dir / "perimeter_polygons.json"

        with csv_path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(all_rows[0].keys()))
            writer.writeheader()
            writer.writerows(all_rows)

        with json_path.open("w") as file:
            json.dump({"polygons": all_polygons}, file, indent=2)

        plot_log_area_vs_perimeter(all_rows, args.plot_path)

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote overlays to {args.overlay_dir}")
    print(f"Wrote plot to {args.plot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
