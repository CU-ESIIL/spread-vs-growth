"""Render a flat perspective fire-growth explainer across landscape contexts."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
from typing import NamedTuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

TMP_DIR = PROJECT_ROOT / "tmp"
(TMP_DIR / "matplotlib").mkdir(parents=True, exist_ok=True)
(TMP_DIR / "cache").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(TMP_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(TMP_DIR / "cache"))

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from skimage import measure, morphology

from animate_grass_fire_two_thirds import (
    FireParams,
    calibrate,
    fit_scaling,
    make_arrival_field,
    masks_and_metrics,
)


class Panel(NamedTuple):
    name: str
    center: tuple[float, float]
    width: float
    height: float
    ground: tuple[int, int, int]
    edge: tuple[int, int, int]


class Feature(NamedTuple):
    kind: str
    u: float
    v: float
    size: float
    angle: float


PANELS = [
    Panel("Grassland", (455, 625), 520, 305, (212, 201, 135), (86, 83, 56)),
    Panel("Forest", (960, 625), 520, 305, (182, 194, 133), (52, 78, 52)),
    Panel("WUI", (1465, 625), 520, 305, (194, 187, 151), (82, 78, 68)),
]


def iso_point(panel: Panel, u: float, v: float) -> tuple[float, float]:
    x = panel.center[0] + (u - v) * panel.width * 0.5
    y = panel.center[1] + (u + v - 1.0) * panel.height * 0.5
    return x, y


def mask_value(mask: np.ndarray, u: float, v: float) -> bool:
    h, w = mask.shape
    row = int(np.clip(round(v * (h - 1)), 0, h - 1))
    col = int(np.clip(round(u * (w - 1)), 0, w - 1))
    return bool(mask[row, col])


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_line(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], fill: tuple[int, int, int], width: int) -> None:
    if len(points) >= 2:
        draw.line([(round(x), round(y)) for x, y in points], fill=fill, width=width, joint="curve")


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    fill: tuple[int, int, int],
    width: int = 2,
) -> None:
    sx, sy = start
    ex, ey = end
    draw.line([(sx, sy), (ex, ey)], fill=fill, width=width)
    angle = math.atan2(ey - sy, ex - sx)
    head = 8.0
    spread = 0.55
    p1 = (ex - head * math.cos(angle - spread), ey - head * math.sin(angle - spread))
    p2 = (ex - head * math.cos(angle + spread), ey - head * math.sin(angle + spread))
    draw.polygon([(ex, ey), p1, p2], fill=fill)


def generate_features() -> dict[str, list[Feature]]:
    rng = np.random.default_rng(20260720)
    features: dict[str, list[Feature]] = {"Grassland": [], "Forest": [], "WUI": []}

    for _ in range(120):
        features["Grassland"].append(
            Feature("grass", float(rng.uniform(0.06, 0.94)), float(rng.uniform(0.08, 0.92)), float(rng.uniform(5, 13)), float(rng.uniform(-0.8, 0.8)))
        )

    for _ in range(88):
        features["Forest"].append(
            Feature("tree", float(rng.uniform(0.06, 0.94)), float(rng.uniform(0.08, 0.92)), float(rng.uniform(9, 18)), 0.0)
        )

    for i in range(42):
        kind = "house" if i % 3 else "tree"
        features["WUI"].append(
            Feature(kind, float(rng.uniform(0.08, 0.92)), float(rng.uniform(0.10, 0.90)), float(rng.uniform(10, 18)), float(rng.uniform(-0.6, 0.6)))
        )
    return features


def draw_plane(draw: ImageDraw.ImageDraw, panel: Panel) -> None:
    corners = [iso_point(panel, 0, 0), iso_point(panel, 1, 0), iso_point(panel, 1, 1), iso_point(panel, 0, 1)]
    draw.polygon(corners, fill=panel.ground, outline=panel.edge)
    draw.line(corners + [corners[0]], fill=panel.edge, width=2)


def draw_grass_tuft(draw: ImageDraw.ImageDraw, panel: Panel, feature: Feature, burned: bool) -> None:
    x, y = iso_point(panel, feature.u, feature.v)
    color = (68, 86, 50) if not burned else (65, 58, 46)
    size = feature.size
    for offset in [-0.5, 0.0, 0.5]:
        angle = feature.angle + offset
        end = (x + math.sin(angle) * size * 0.35, y - math.cos(angle) * size * 0.65)
        draw.line([(x, y), end], fill=color, width=1)


def draw_tree(draw: ImageDraw.ImageDraw, panel: Panel, feature: Feature, burned: bool) -> None:
    x, y = iso_point(panel, feature.u, feature.v)
    size = feature.size
    if burned:
        draw.line([(x, y - size * 0.42), (x, y + size * 0.45)], fill=(55, 48, 40), width=2)
        draw.ellipse((x - size * 0.22, y - size * 0.20, x + size * 0.22, y + size * 0.20), fill=(74, 66, 54))
        return
    draw.line([(x, y - size * 0.28), (x, y + size * 0.48)], fill=(94, 67, 42), width=3)
    draw.ellipse((x - size * 0.55, y - size * 0.78, x + size * 0.55, y + size * 0.18), fill=(42, 98, 57), outline=(31, 75, 44))
    draw.ellipse((x - size * 0.34, y - size * 1.02, x + size * 0.34, y - size * 0.34), fill=(50, 119, 66))


def draw_house(draw: ImageDraw.ImageDraw, panel: Panel, feature: Feature, burned: bool) -> None:
    x, y = iso_point(panel, feature.u, feature.v)
    size = feature.size
    wall = (221, 216, 199) if not burned else (84, 76, 67)
    roof = (151, 69, 52) if not burned else (54, 49, 46)
    outline = (83, 76, 65)
    body = [(x - size * 0.55, y - size * 0.15), (x + size * 0.55, y - size * 0.15), (x + size * 0.55, y + size * 0.45), (x - size * 0.55, y + size * 0.45)]
    roof_poly = [(x - size * 0.68, y - size * 0.15), (x, y - size * 0.70), (x + size * 0.68, y - size * 0.15)]
    draw.polygon(body, fill=wall, outline=outline)
    draw.polygon(roof_poly, fill=roof, outline=outline)


def draw_wui_roads(draw: ImageDraw.ImageDraw, panel: Panel) -> None:
    roads = [
        [(0.04, 0.72), (0.32, 0.58), (0.65, 0.52), (0.96, 0.36)],
        [(0.26, 0.10), (0.42, 0.38), (0.49, 0.88)],
    ]
    for road in roads:
        pts = [iso_point(panel, u, v) for u, v in road]
        draw_line(draw, pts, (128, 126, 120), 9)
        draw_line(draw, pts, (226, 222, 207), 3)


def draw_context_features(
    draw: ImageDraw.ImageDraw,
    panel: Panel,
    features: list[Feature],
    mask: np.ndarray,
) -> None:
    if panel.name == "WUI":
        draw_wui_roads(draw, panel)
    for feature in sorted(features, key=lambda item: item.u + item.v):
        burned = mask_value(mask, feature.u, feature.v)
        if feature.kind == "grass":
            draw_grass_tuft(draw, panel, feature, burned)
        elif feature.kind == "tree":
            draw_tree(draw, panel, feature, burned)
        elif feature.kind == "house":
            draw_house(draw, panel, feature, burned)


def largest_contours(mask: np.ndarray, min_points: int = 12) -> list[np.ndarray]:
    contours = measure.find_contours(np.pad(mask.astype(float), 1), 0.5)
    result = []
    for contour in contours:
        contour = contour - 1.0
        if len(contour) >= min_points:
            result.append(contour)
    result.sort(key=len, reverse=True)
    return result[:6]


def contour_points(panel: Panel, contour: np.ndarray, shape: tuple[int, int], every: int = 2) -> list[tuple[float, float]]:
    h, w = shape
    pts = []
    for row, col in contour[::every]:
        pts.append(iso_point(panel, float(col) / max(w - 1, 1), float(row) / max(h - 1, 1)))
    return pts


def draw_fire_footprint(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    panel: Panel,
    mask: np.ndarray,
    previous: np.ndarray,
    frame: int,
) -> None:
    contours = largest_contours(mask)
    if not contours:
        return

    overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for contour in contours:
        pts = contour_points(panel, contour, mask.shape)
        if len(pts) >= 3:
            odraw.polygon(pts, fill=(94, 142, 205, 74))
            odraw.line(pts + [pts[0]], fill=(78, 124, 188, 98), width=2)

    active = mask & ~morphology.erosion(mask, morphology.disk(2))
    active |= mask & ~previous
    active = morphology.dilation(active, morphology.disk(1))
    active_contours = largest_contours(active, min_points=5)
    for contour in active_contours:
        pts = contour_points(panel, contour, active.shape)
        draw_line(odraw, pts, (186, 36, 34), 4)
        draw_line(odraw, pts, (255, 133, 34), 2)

    smoke_source = ndi.gaussian_filter(active.astype(float), sigma=3.0)
    if smoke_source.max() > 0:
        rng_shift = 0.2 * math.sin(frame * 0.09)
        smoke_mask = ndi.shift(smoke_source, (-8, 17 + rng_shift), order=1, mode="constant", cval=0.0)
        for contour in largest_contours(smoke_mask > np.quantile(smoke_mask, 0.986), min_points=5):
            pts = contour_points(panel, contour, smoke_mask.shape, every=3)
            if len(pts) >= 3:
                odraw.polygon(pts, fill=(112, 116, 118, 32))

    image = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    canvas.paste(image)

    main_contour = contours[0]
    pts = contour_points(panel, main_contour, mask.shape, every=max(8, len(main_contour) // 18))
    if len(pts) > 2:
        cx = sum(x for x, _ in pts) / len(pts)
        cy = sum(y for _, y in pts) / len(pts)
        for x, y in pts[::2]:
            dx, dy = x - cx, y - cy
            mag = math.hypot(dx, dy)
            if mag < 1:
                continue
            start = (x + dx / mag * 4, y + dy / mag * 4)
            end = (x + dx / mag * 18, y + dy / mag * 18)
            draw_arrow(draw, start, end, fill=(185, 38, 36), width=2)


def draw_panel_label(draw: ImageDraw.ImageDraw, panel: Panel, font: ImageFont.ImageFont) -> None:
    text = panel.name
    bbox = draw.textbbox((0, 0), text, font=font)
    x = panel.center[0] - (bbox[2] - bbox[0]) / 2
    y = panel.center[1] + panel.height * 0.5 + 46
    draw.text((x, y), text, fill=(37, 37, 34), font=font)


def build_masks(
    *,
    output_dir: Path,
    width: int,
    height: int,
    frames: int,
    pixel_size: float,
    seed: int,
    calibration_attempts: int,
) -> tuple[list[np.ndarray], list[dict[str, float | int | bool]], dict[str, object]]:
    accepted_path = output_dir / "accepted_parameters.json"
    sim_frames = min(frames, 240)
    if accepted_path.exists():
        payload = json.loads(accepted_path.read_text())
        params = FireParams(**payload["parameters"])
        arrival, _ = make_arrival_field(width, height, params)
        sim_masks, sim_rows = masks_and_metrics(arrival, frames=sim_frames, final_fraction=0.35, pixel_size=pixel_size)
    else:
        params, _, _, sim_masks, sim_rows, _ = calibrate(
            width=width,
            height=height,
            frames=sim_frames,
            pixel_size=pixel_size,
            seed=seed,
            target_low=0.64,
            target_high=0.69,
            attempts=calibration_attempts,
        )

    if sim_frames == frames:
        rows = sim_rows
        masks = sim_masks
    else:
        idx = np.linspace(0, sim_frames - 1, frames).round().astype(int)
        masks = [sim_masks[i] for i in idx]
        rows = []
        for frame, i in enumerate(idx):
            row = dict(sim_rows[i])
            row["frame"] = frame
            row["time_seconds"] = frame / 30.0
            rows.append(row)

    fit = fit_scaling(rows)
    metadata = {
        "parameters": params.__dict__,
        "fit": fit.__dict__,
        "frames": frames,
    }
    return masks, rows, metadata


def render_frame(
    mask: np.ndarray,
    previous: np.ndarray,
    features: dict[str, list[Feature]],
    frame: int,
    *,
    display_area: float,
    display_perimeter: float,
) -> np.ndarray:
    canvas = Image.new("RGB", (1920, 1080), (247, 247, 244))
    draw = ImageDraw.Draw(canvas)
    label_font = load_font(34)
    metric_font = load_font(30)
    small_font = load_font(20)

    draw.text((820, 72), "Area A (km²)", fill=(26, 26, 24), font=metric_font)
    draw.text((783, 123), f"{display_area:,.1f}", fill=(184, 32, 32), font=metric_font)
    draw.line([(958, 114), (958, 158)], fill=(26, 26, 24), width=3)
    draw.text((990, 123), f"{display_area:,.1f}", fill=(91, 145, 220), font=metric_font)

    draw.text((790, 207), "Perimeter P (km)", fill=(26, 26, 24), font=metric_font)
    draw.text((802, 258), f"{display_perimeter:,.1f}", fill=(184, 32, 32), font=metric_font)
    draw.line([(958, 249), (958, 293)], fill=(26, 26, 24), width=3)
    draw.text((990, 258), f"{display_perimeter:,.1f}", fill=(91, 145, 220), font=metric_font)

    for panel in PANELS:
        draw_plane(draw, panel)
        draw_context_features(draw, panel, features[panel.name], mask)
        draw_fire_footprint(canvas, draw, panel, mask, previous, frame)
        draw_panel_label(draw, panel, label_font)

    draw.text((731, 971), "same fire-growth footprint, three familiar landscapes", fill=(76, 76, 70), font=small_font)
    return np.asarray(canvas)


def verify_video(path: Path) -> dict[str, object]:
    reader = imageio.get_reader(path)
    meta = reader.get_meta_data()
    frame0 = reader.get_data(0)
    reader.close()
    return {
        "path": str(path),
        "codec": meta.get("codec"),
        "fps": meta.get("fps"),
        "duration": meta.get("duration"),
        "size": list(frame0.shape[:2][::-1]),
        "first_frame_mean": float(frame0.mean()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "outputs" / "grass_fire_two_thirds")
    parser.add_argument("--output-name", default="grass_forest_wui_growth_explainer")
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=405)
    parser.add_argument("--pixel-size", type=float, default=1.0)
    parser.add_argument("--display-km-per-pixel", type=float, default=0.05)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--duration-seconds", type=float, default=15.0)
    parser.add_argument("--seed", type=int, default=20260720)
    parser.add_argument("--calibration-attempts", type=int, default=24)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    frames = int(round(args.fps * args.duration_seconds))
    masks, rows, metadata = build_masks(
        output_dir=args.output_dir,
        width=args.width,
        height=args.height,
        frames=frames,
        pixel_size=args.pixel_size,
        seed=args.seed,
        calibration_attempts=args.calibration_attempts,
    )
    features = generate_features()
    output_path = args.output_dir / f"{args.output_name}.mp4"
    final_frame_path = args.output_dir / f"{args.output_name}_final_frame.png"

    previous = np.zeros_like(masks[0], dtype=bool)
    with imageio.get_writer(
        output_path,
        fps=args.fps,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=1,
    ) as writer:
        for frame, mask in enumerate(masks):
            row = rows[frame]
            rendered = render_frame(
                mask,
                previous,
                features,
                frame,
                display_area=float(row["area"]) * args.display_km_per_pixel**2,
                display_perimeter=float(row["perimeter_contour"]) * args.display_km_per_pixel,
            )
            writer.append_data(rendered)
            previous = mask

    imageio.imwrite(final_frame_path, rendered)
    checks = verify_video(output_path)
    metadata["render"] = {
        "output": str(output_path),
        "final_frame": str(final_frame_path),
        "fps": args.fps,
        "duration_seconds": args.duration_seconds,
        "width": 1920,
        "height": 1080,
        "style": "flat perspective landscape contexts",
        "display_km_per_pixel": args.display_km_per_pixel,
        "video_check": checks,
    }
    (args.output_dir / f"{args.output_name}_metadata.json").write_text(json.dumps(metadata, indent=2))
    print(f"Wrote {output_path}")
    print(json.dumps(checks, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
