"""Calibrate and render a grassland fire footprint with P ~ A^(2/3).

The simulation is deterministic for a saved seed. It builds a correlated
arrival-time field and renders the monotone burned masks through time. The
animation is a visual/scientific figure generator, not an operational fire model.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
import sys
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

TMP_DIR = PROJECT_ROOT / "tmp"
(TMP_DIR / "matplotlib").mkdir(parents=True, exist_ok=True)
(TMP_DIR / "cache").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(TMP_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(TMP_DIR / "cache"))

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from skimage import measure, morphology, transform

from fire_model_scaling.fit_scaling import ols_loglog


@dataclass(frozen=True)
class FireParams:
    seed: int
    roughness_amp: float
    island_amp: float
    island_density: float
    spot_count: int
    spot_strength: float
    smooth_sigma: float
    head_scale: float
    flank_scale: float
    rear_scale: float
    wind_wander_amp: float


@dataclass(frozen=True)
class FitResult:
    sigma: float
    intercept: float
    sigma_se: float
    ci_low: float
    ci_high: float
    r2: float
    rmse: float
    n: int
    area_min: float
    area_max: float
    area_range: float


def normalized(field: np.ndarray) -> np.ndarray:
    field = np.asarray(field, dtype=float)
    return (field - field.mean()) / max(field.std(), 1e-9)


def correlated_noise(rng: np.random.Generator, shape: tuple[int, int], sigmas: Iterable[float]) -> np.ndarray:
    out = np.zeros(shape, dtype=float)
    weights = np.array([1.0 / math.sqrt(sigma) for sigma in sigmas], dtype=float)
    weights = weights / weights.sum()
    for sigma, weight in zip(sigmas, weights):
        out += weight * normalized(ndi.gaussian_filter(rng.normal(size=shape), sigma=sigma, mode="reflect"))
    return normalized(out)


def scenario_name(params: FireParams) -> str:
    return (
        f"seed{params.seed}_rough{params.roughness_amp:.2f}"
        f"_island{params.island_amp:.2f}_spots{params.spot_count}"
    )


def make_arrival_field(width: int, height: int, params: FireParams) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    rng = np.random.default_rng(params.seed)
    yy, xx = np.mgrid[0:height, 0:width]
    cx = 0.24 * width
    cy = 0.52 * height
    along = xx - cx
    across = yy - cy

    forward = np.maximum(along, 0.0) / params.head_scale
    rear = np.maximum(-along, 0.0) / params.rear_scale
    cross = across / params.flank_scale
    base = np.sqrt((forward + rear) ** 2 + cross**2)
    theta = np.arctan2(cross, forward + rear + 1e-6)

    fuel = correlated_noise(rng, (height, width), sigmas=[9.0, 24.0, 70.0])
    wind = correlated_noise(rng, (height, width), sigmas=[18.0, 42.0, 115.0])
    instability = correlated_noise(rng, (height, width), sigmas=[5.0, 13.0, 32.0])
    lateral = np.sin((yy / height) * math.tau * 1.6 + params.wind_wander_amp * wind)
    angular = np.zeros_like(theta)
    for mode, weight in [(3, 0.55), (5, 0.42), (8, 0.35), (13, 0.25), (21, 0.16)]:
        angular += weight * np.cos(mode * theta + rng.uniform(0.0, math.tau))
    angular = normalized(angular)
    head_bias = 0.55 + 0.45 * np.clip((along / max(width * 0.7, 1.0)), -0.4, 1.0)
    fingering = normalized(0.75 * angular * head_bias + 0.5 * fuel + 0.55 * wind + 0.5 * instability + 0.25 * lateral)

    slow_field = correlated_noise(rng, (height, width), sigmas=[10.0, 28.0])
    slow_quantile = np.quantile(slow_field, 1.0 - params.island_density)
    slow_patches = ndi.gaussian_filter((slow_field > slow_quantile).astype(float), sigma=3.0, mode="reflect")
    slow_patches = slow_patches / max(float(slow_patches.max()), 1e-9)

    distance_factor = np.clip(base / np.percentile(base, 98), 0.0, 1.3)
    roughening = params.roughness_amp * fingering * (0.35 + 0.9 * distance_factor)
    island_delay = params.island_amp * slow_patches * (0.4 + 1.1 * distance_factor)
    arrival_multiplier = np.clip(1.0 - roughening + island_delay, 0.055, 3.2)
    arrival = base * arrival_multiplier

    ignition = np.sqrt(((xx - cx) / 7.0) ** 2 + ((yy - cy) / 5.0) ** 2)
    arrival = np.minimum(arrival, ignition)

    spot_field = np.full_like(arrival, np.inf)
    for _ in range(params.spot_count):
        sx = rng.uniform(0.44 * width, 0.74 * width)
        sy = cy + rng.normal(0.0, 0.13 * height)
        if sy < 0.12 * height or sy > 0.88 * height:
            continue
        spot_radius = rng.uniform(5.0, 12.0)
        spot_delay = rng.uniform(0.50, 0.86) * np.percentile(base, 82)
        spot = spot_delay + np.sqrt(((xx - sx) / (spot_radius * 1.7)) ** 2 + ((yy - sy) / spot_radius) ** 2)
        spot_field = np.minimum(spot_field, spot)
    arrival = np.minimum(arrival, spot_field * params.spot_strength)
    arrival = ndi.gaussian_filter(arrival, sigma=params.smooth_sigma, mode="reflect")
    arrival -= arrival.min()

    fields = {
        "fuel": fuel,
        "wind": wind,
        "instability": instability,
        "slow_patches": slow_patches,
        "arrival": arrival,
    }
    return arrival, fields


def coherent_fire_complex(mask: np.ndarray, max_detached_distance: float = 45.0) -> np.ndarray:
    labeled, count = ndi.label(mask)
    if count <= 1:
        return mask
    component_sizes = np.bincount(labeled.ravel())
    component_sizes[0] = 0
    largest_label = int(component_sizes.argmax())
    largest = labeled == largest_label
    distance_to_largest = ndi.distance_transform_edt(~largest)
    keep = largest.copy()
    for label in range(1, count + 1):
        if label == largest_label:
            continue
        component = labeled == label
        if not component.any():
            continue
        near_largest = float(distance_to_largest[component].min()) <= max_detached_distance
        large_enough = int(component.sum()) >= 180
        if near_largest and large_enough:
            keep |= component
    return keep


def contour_perimeter(mask: np.ndarray, pixel_size: float) -> float:
    padded = np.pad(mask.astype(float), 1, mode="constant", constant_values=0.0)
    contours = measure.find_contours(padded, level=0.5)
    perimeter = 0.0
    for contour in contours:
        contour = contour - 1.0
        diffs = np.diff(np.vstack([contour, contour[0]]), axis=0)
        perimeter += float(np.sum(np.sqrt(np.sum(diffs * diffs, axis=1))) * pixel_size)
    return perimeter


def grid_edge_perimeter(mask: np.ndarray, pixel_size: float) -> float:
    padded = np.pad(mask.astype(bool), 1, mode="constant", constant_values=False)
    vertical = np.logical_xor(padded[:, 1:], padded[:, :-1]).sum()
    horizontal = np.logical_xor(padded[1:, :], padded[:-1, :]).sum()
    return float((vertical + horizontal) * pixel_size)


def masks_and_metrics(
    arrival: np.ndarray,
    *,
    frames: int,
    final_fraction: float,
    pixel_size: float,
) -> tuple[list[np.ndarray], list[dict[str, float | int | bool]]]:
    flat = arrival.ravel()
    start_threshold = float(np.quantile(flat, 0.006))
    end_threshold = float(np.quantile(flat, final_fraction))
    thresholds = np.geomspace(max(start_threshold, 1e-6), end_threshold, frames)
    masks: list[np.ndarray] = []
    rows: list[dict[str, float | int | bool]] = []
    for frame, threshold in enumerate(thresholds):
        raw = arrival <= threshold
        mask = morphology.closing(raw, morphology.disk(1))
        mask = coherent_fire_complex(mask)
        edge_contact = bool(mask[0, :].any() or mask[-1, :].any() or mask[:, 0].any() or mask[:, -1].any())
        masks.append(mask)
        area = float(mask.sum() * pixel_size * pixel_size)
        perimeter = contour_perimeter(mask, pixel_size)
        grid_perimeter = grid_edge_perimeter(mask, pixel_size)
        rows.append(
            {
                "frame": frame,
                "time_seconds": frame / 30.0,
                "threshold": float(threshold),
                "area": area,
                "perimeter_contour": perimeter,
                "perimeter_grid_edge": grid_perimeter,
                "burned_fraction": float(mask.mean()),
                "domain_edge_contact": edge_contact,
                "valid_geometry": bool(area > 0.0 and perimeter > 0.0),
            }
        )
    return masks, rows


def fit_scaling(rows: list[dict[str, float | int | bool]], exclude_fraction: float = 0.05) -> FitResult:
    valid = [row for row in rows if row["valid_geometry"] and not row.get("domain_edge_contact", False)]
    if not valid:
        raise ValueError("No valid geometry rows.")
    first = int(math.ceil(len(valid) * exclude_fraction))
    fit_rows = valid[first:]
    area = np.array([float(row["area"]) for row in fit_rows])
    perimeter = np.array([float(row["perimeter_contour"]) for row in fit_rows])
    intercept, sigma, se, ci_low, ci_high, rmse = ols_loglog(area, perimeter)
    x = np.log10(area)
    y = np.log10(perimeter)
    yhat = intercept + sigma * x
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / max(ss_tot, 1e-12)
    return FitResult(
        sigma=sigma,
        intercept=intercept,
        sigma_se=se,
        ci_low=ci_low,
        ci_high=ci_high,
        r2=r2,
        rmse=rmse,
        n=len(fit_rows),
        area_min=float(area.min()),
        area_max=float(area.max()),
        area_range=float(area.max() / max(area.min(), 1e-12)),
    )


def calibrate(
    *,
    width: int,
    height: int,
    frames: int,
    pixel_size: float,
    seed: int,
    target_low: float,
    target_high: float,
    attempts: int,
) -> tuple[FireParams, np.ndarray, dict[str, np.ndarray], list[np.ndarray], list[dict[str, float | int | bool]], FitResult]:
    rng = np.random.default_rng(seed)
    candidates = [
        FireParams(
            seed=seed,
            roughness_amp=0.48,
            island_amp=1.25,
            island_density=0.16,
            spot_count=4,
            spot_strength=0.92,
            smooth_sigma=0.85,
            head_scale=1.78,
            flank_scale=0.88,
            rear_scale=0.46,
            wind_wander_amp=1.6,
        )
    ]
    for i in range(attempts):
        candidates.append(
            FireParams(
                seed=seed + i + 1,
                roughness_amp=float(rng.uniform(0.55, 1.05)),
                island_amp=float(rng.uniform(0.85, 1.9)),
                island_density=float(rng.uniform(0.10, 0.24)),
                spot_count=int(rng.integers(0, 7)),
                spot_strength=float(rng.uniform(0.82, 1.02)),
                smooth_sigma=float(rng.uniform(0.55, 1.2)),
                head_scale=float(rng.uniform(1.45, 2.05)),
                flank_scale=float(rng.uniform(0.78, 1.08)),
                rear_scale=float(rng.uniform(0.35, 0.62)),
                wind_wander_amp=float(rng.uniform(0.8, 2.2)),
            )
        )

    best = None
    accepted = None
    for params in candidates:
        arrival, fields = make_arrival_field(width, height, params)
        masks, rows = masks_and_metrics(arrival, frames=frames, final_fraction=0.35, pixel_size=pixel_size)
        try:
            fit = fit_scaling(rows)
        except ValueError:
            continue
        in_target = target_low <= fit.sigma <= target_high and fit.r2 > 0.95 and fit.area_range >= 10.0
        penalty = abs(fit.sigma - 2.0 / 3.0) + max(0.0, 0.95 - fit.r2) + max(0.0, 10.0 - fit.area_range) * 0.02
        candidate = (penalty, params, arrival, fields, masks, rows, fit)
        if best is None or penalty < best[0]:
            best = candidate
        if in_target:
            accepted = candidate
            break

    assert best is not None
    chosen = accepted or best
    _, params, arrival, fields, masks, rows, fit = chosen
    return params, arrival, fields, masks, rows, fit


def write_metrics(path: Path, rows: list[dict[str, float | int | bool]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def render_array_to_size(array: np.ndarray, shape: tuple[int, int], order: int = 1) -> np.ndarray:
    return transform.resize(
        array,
        shape,
        order=order,
        preserve_range=True,
        anti_aliasing=order > 0,
    )


def build_background(fields: dict[str, np.ndarray], main_size: tuple[int, int]) -> np.ndarray:
    main_w, main_h = main_size
    fuel = render_array_to_size(fields["fuel"], (main_h, main_w), order=1)
    fuel = normalized(fuel)
    grass = np.zeros((main_h, main_w, 3), dtype=np.float32)
    grass[..., 0] = 0.57 + 0.035 * fuel
    grass[..., 1] = 0.54 + 0.05 * fuel
    grass[..., 2] = 0.37 + 0.025 * fuel
    yy = np.linspace(0, 1, main_h)[:, None]
    grass *= (0.92 + 0.12 * (1 - yy))[..., None]
    return np.clip(grass, 0, 1)


def draw_diagnostic(
    draw: ImageDraw.ImageDraw,
    rows: list[dict[str, float | int | bool]],
    frame: int,
    fit: FitResult,
    box: tuple[int, int, int, int],
) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=14, fill=(247, 246, 241), outline=(170, 170, 165), width=2)
    pad_l, pad_r, pad_t, pad_b = 52, 22, 44, 56
    px0, py0, px1, py1 = x0 + pad_l, y0 + pad_t, x1 - pad_r, y1 - pad_b
    valid = rows[: frame + 1]
    valid = [row for row in valid if row["valid_geometry"] and row["area"] > 0 and row["perimeter_contour"] > 0]
    all_valid = [row for row in rows if row["valid_geometry"] and row["area"] > 0 and row["perimeter_contour"] > 0]
    if len(valid) < 2 or len(all_valid) < 2:
        return
    area_all = np.array([float(row["area"]) for row in all_valid])
    perim_all = np.array([float(row["perimeter_contour"]) for row in all_valid])
    lx_min, lx_max = np.log10(area_all.min()), np.log10(area_all.max())
    ly_min, ly_max = np.log10(perim_all.min()), np.log10(perim_all.max())
    lx_min -= 0.05 * (lx_max - lx_min)
    lx_max += 0.05 * (lx_max - lx_min)
    ly_min -= 0.10 * (ly_max - ly_min)
    ly_max += 0.10 * (ly_max - ly_min)

    def map_xy(area: float, perim: float) -> tuple[float, float]:
        xx = px0 + (np.log10(area) - lx_min) / (lx_max - lx_min) * (px1 - px0)
        yy = py1 - (np.log10(perim) - ly_min) / (ly_max - ly_min) * (py1 - py0)
        return float(xx), float(yy)

    draw.line([(px0, py1), (px1, py1), (px1, py0)], fill=(80, 80, 80), width=2)
    for frac in [0.25, 0.5, 0.75]:
        gx = px0 + frac * (px1 - px0)
        gy = py1 - frac * (py1 - py0)
        draw.line([(gx, py0), (gx, py1)], fill=(222, 222, 218), width=1)
        draw.line([(px0, gy), (px1, gy)], fill=(222, 222, 218), width=1)

    anchor_area = float(np.percentile(area_all, 12))
    anchor_perim = float(np.percentile(perim_all, 12))
    ref_x = np.logspace(lx_min, lx_max, 80)
    for exponent, color in [(2 / 3, (100, 149, 237)), (0.5, (178, 34, 34))]:
        pts = [map_xy(float(a), anchor_perim * (float(a) / anchor_area) ** exponent) for a in ref_x]
        draw.line(pts, fill=color, width=3)

    pts = [map_xy(float(row["area"]), float(row["perimeter_contour"])) for row in valid]
    draw.line(pts, fill=(55, 55, 55), width=2)
    for pt in pts[-20::3]:
        draw.ellipse((pt[0] - 2, pt[1] - 2, pt[0] + 2, pt[1] + 2), fill=(35, 35, 35))
    last = valid[-1]
    draw.ellipse((*np.subtract(pts[-1], 4), *np.add(pts[-1], 4)), fill=(255, 120, 30))

    font = ImageFont.load_default()
    draw.text((x0 + 16, y0 + 13), f"log P vs log A", fill=(35, 35, 35), font=font)
    draw.text((x0 + 16, y1 - 41), f"sigma={fit.sigma:.3f}  R2={fit.r2:.3f}", fill=(35, 35, 35), font=font)
    draw.text((x0 + 16, y1 - 24), f"A={float(last['area']):.1f}  P={float(last['perimeter_contour']):.1f}", fill=(35, 35, 35), font=font)


def render_fire_frame(
    mask: np.ndarray,
    previous_mask: np.ndarray,
    fields: dict[str, np.ndarray],
    background: np.ndarray,
    frame: int,
    *,
    main_size: tuple[int, int],
) -> np.ndarray:
    main_w, main_h = main_size
    mask_r = render_array_to_size(mask.astype(float), (main_h, main_w), order=0) > 0.5
    prev_r = render_array_to_size(previous_mask.astype(float), (main_h, main_w), order=0) > 0.5
    active = mask_r & ~morphology.erosion(mask_r, morphology.disk(5))
    new_active = mask_r & ~prev_r
    active = active | morphology.dilation(new_active, morphology.disk(4))
    active = morphology.dilation(active, morphology.disk(1))

    image = background.copy()
    burn_noise = render_array_to_size(fields["instability"], (main_h, main_w), order=1)
    burn = np.zeros_like(image)
    burn[..., 0] = 0.035 + 0.018 * normalized(burn_noise)
    burn[..., 1] = 0.030 + 0.014 * normalized(burn_noise)
    burn[..., 2] = 0.026 + 0.012 * normalized(burn_noise)
    image[mask_r] = np.clip(burn[mask_r], 0, 0.16)

    flame_noise = render_array_to_size(fields["wind"], (main_h, main_w), order=1)
    flicker = 0.65 + 0.35 * np.sin(0.26 * frame + 2.2 * flame_noise)
    flame = np.zeros_like(image)
    flame[..., 0] = 1.0
    flame[..., 1] = 0.22 + 0.42 * flicker
    flame[..., 2] = 0.02
    flame_alpha = active.astype(float) * (0.65 + 0.25 * flicker)
    flame_alpha = np.clip(ndi.gaussian_filter(flame_alpha, 0.55), 0, 0.92)
    image = image * (1 - flame_alpha[..., None]) + flame * flame_alpha[..., None]

    smoke_source = ndi.gaussian_filter(active.astype(float), sigma=4.0)
    smoke = np.zeros_like(smoke_source)
    for i, alpha in enumerate([0.28, 0.19, 0.12, 0.07], start=1):
        shifted = ndi.shift(smoke_source, shift=(-8 * i, 20 * i + 0.45 * frame), order=1, mode="constant", cval=0.0)
        smoke += alpha * shifted
    smoke = np.clip(ndi.gaussian_filter(smoke, 7.5), 0, 0.32)
    smoke_color = np.array([0.54, 0.55, 0.54], dtype=float)
    image = image * (1 - smoke[..., None]) + smoke_color * smoke[..., None]

    return np.clip(image * 255, 0, 255).astype(np.uint8)


def compose_frame(
    main: np.ndarray,
    rows: list[dict[str, float | int | bool]],
    frame: int,
    fit: FitResult,
    *,
    diagnostic: bool,
) -> np.ndarray:
    canvas = Image.new("RGB", (1920, 1080), (141, 132, 92))
    if diagnostic:
        main_img = Image.fromarray(main).resize((1536, 864), resample=Image.Resampling.BILINEAR)
        canvas.paste(main_img, (0, 108))
        draw = ImageDraw.Draw(canvas)
        draw_diagnostic(draw, rows, frame, fit, (1547, 228, 1905, 852))
    else:
        main_img = Image.fromarray(main).resize((1920, 1080), resample=Image.Resampling.BILINEAR)
        canvas.paste(main_img, (0, 0))
    return np.asarray(canvas)


def write_video(
    path: Path,
    masks: list[np.ndarray],
    fields: dict[str, np.ndarray],
    rows: list[dict[str, float | int | bool]],
    fit: FitResult,
    *,
    diagnostic: bool,
    fps: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    main_size = (1280, 720)
    background = build_background(fields, main_size)
    previous = np.zeros_like(masks[0], dtype=bool)
    with imageio.get_writer(
        path,
        fps=fps,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=1,
    ) as writer:
        for frame, mask in enumerate(masks):
            main = render_fire_frame(mask, previous, fields, background, frame, main_size=main_size)
            writer.append_data(compose_frame(main, rows, frame, fit, diagnostic=diagnostic))
            previous = mask


def write_scaling_plot(path: Path, rows: list[dict[str, float | int | bool]], fit: FitResult) -> None:
    valid = [row for row in rows if row["valid_geometry"]]
    area = np.array([float(row["area"]) for row in valid])
    perimeter = np.array([float(row["perimeter_contour"]) for row in valid])
    grid_perimeter = np.array([float(row["perimeter_grid_edge"]) for row in valid])
    x = np.logspace(np.log10(area.min()), np.log10(area.max()), 200)
    anchor_area = float(np.percentile(area, 12))
    anchor_perim = float(np.percentile(perimeter, 12))

    fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)
    ax.plot(area, perimeter, color="#333333", marker="o", markersize=2.5, linewidth=1.2, label="contour perimeter")
    ax.plot(area, grid_perimeter, color="#999999", linewidth=1.0, alpha=0.55, label="grid-edge diagnostic")
    ax.plot(x, anchor_perim * (x / anchor_area) ** (2 / 3), color="cornflowerblue", linewidth=2.2, label=r"$P \propto A^{2/3}$")
    ax.plot(x, anchor_perim * (x / anchor_area) ** 0.5, color="firebrick", linewidth=2.2, linestyle="--", label=r"$P \propto A^{1/2}$")
    ax.plot(x, 10 ** fit.intercept * x ** fit.sigma, color="#333333", linestyle=":", linewidth=2.0, label=f"fit: {fit.sigma:.3f}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Burned area")
    ax.set_ylabel("Perimeter")
    ax.grid(True, which="major", color="#dddddd")
    ax.legend(frameon=False)
    ax.set_title("Grass-fire perimeter-area scaling")
    fig.savefig(path, dpi=200)
    plt.close(fig)


def write_final_frame(path: Path, masks: list[np.ndarray], fields: dict[str, np.ndarray]) -> None:
    main_size = (1920, 1080)
    background = build_background(fields, main_size)
    final = render_fire_frame(masks[-1], masks[-2], fields, background, len(masks) - 1, main_size=main_size)
    imageio.imwrite(path, final)


def write_parameters(path: Path, params: FireParams, fit: FitResult, args: argparse.Namespace) -> None:
    payload = {
        "parameters": asdict(params),
        "fit": asdict(fit),
        "render": {
            "fps": args.fps,
            "duration_seconds": args.duration_seconds,
            "frames": int(args.fps * args.duration_seconds),
            "width": args.width,
            "height": args.height,
            "pixel_size": args.pixel_size,
        },
    }
    path.write_text(json.dumps(payload, indent=2))


def verify_video(path: Path) -> dict[str, object]:
    reader = imageio.get_reader(path)
    meta = reader.get_meta_data()
    frame0 = reader.get_data(0)
    reader.close()
    return {
        "path": str(path),
        "fps": meta.get("fps"),
        "duration": meta.get("duration"),
        "size": list(frame0.shape[:2][::-1]),
        "first_frame_mean": float(frame0.mean()),
    }


def write_readme(path: Path, params: FireParams, fit: FitResult, video_checks: list[dict[str, object]]) -> None:
    text = f"""# Grass Fire Two-Thirds Animation

This directory contains a deterministic Python-rendered animation of a shallow grassland wildfire footprint with measured perimeter-area scaling near `P proportional to A^(2/3)`.

## Spread Model

The model creates a two-dimensional arrival-time field over a flat grassland. A small ignition starts near the center-left. The base spread metric is wind-anisotropic, with faster head-fire advance to the right, slower rear spread, and intermediate flank spread. The final animation is made by thresholding this arrival field through time, so the burned footprint evolves monotonically and causally from earlier masks.

## Correlated Fields

Static fuel, wind, and instability fields are generated from Gaussian-filtered random noise at multiple spatial scales. These fields create broad fingers, lateral wandering, multiscale corrugation, slow patches, bypassed islands, and local acceleration/deceleration. Sparse ahead-of-front ignitions are added downwind and then folded back into the main complex as the threshold grows.

## Measurement

Area is measured from the binary burned mask. Perimeter is measured with a subpixel contour estimator from `skimage.measure.find_contours`; a grid-edge perimeter diagnostic is also included in `metrics.csv`.

## Fit

    The first 5% of frames are excluded from the fit. The accepted contour-perimeter fit is:

- sigma: `{fit.sigma:.4f}`
- 95% CI: `[{fit.ci_low:.4f}, {fit.ci_high:.4f}]`
- R^2: `{fit.r2:.4f}`
- fitted frames: `{fit.n}`
- area range: `{fit.area_range:.2f}x`
- seed: `{params.seed}`

## Reproduce

```bash
python scripts/animate_grass_fire_two_thirds.py
```

## Video Checks

```json
{json.dumps(video_checks, indent=2)}
```
"""
    path.write_text(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "outputs" / "grass_fire_two_thirds")
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=405)
    parser.add_argument("--pixel-size", type=float, default=1.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--duration-seconds", type=float, default=16.0)
    parser.add_argument("--seed", type=int, default=20260720)
    parser.add_argument("--calibration-attempts", type=int, default=24)
    parser.add_argument("--target-low", type=float, default=0.64)
    parser.add_argument("--target-high", type=float, default=0.69)
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    frames = int(args.fps * args.duration_seconds)
    sim_frames = min(frames, 240)
    params, arrival, fields, sim_masks, sim_rows, fit = calibrate(
        width=args.width,
        height=args.height,
        frames=sim_frames,
        pixel_size=args.pixel_size,
        seed=args.seed,
        target_low=args.target_low,
        target_high=args.target_high,
        attempts=args.calibration_attempts,
    )

    if sim_frames != frames:
        idx = np.linspace(0, sim_frames - 1, frames).round().astype(int)
        masks = [sim_masks[i] for i in idx]
        rows = []
        for frame, i in enumerate(idx):
            row = dict(sim_rows[i])
            row["frame"] = frame
            row["time_seconds"] = frame / args.fps
            rows.append(row)
        fit = fit_scaling(rows)
    else:
        masks = sim_masks
        rows = sim_rows

    write_metrics(output_dir / "metrics.csv", rows)
    write_parameters(output_dir / "accepted_parameters.json", params, fit, args)
    write_scaling_plot(output_dir / "perimeter_area_scaling.png", rows, fit)
    write_final_frame(output_dir / "grass_fire_final_frame.png", masks, fields)

    video_checks: list[dict[str, object]] = []
    if not args.skip_render:
        diagnostic_path = output_dir / "grass_fire_two_thirds_diagnostic.mp4"
        clean_path = output_dir / "grass_fire_two_thirds_clean.mp4"
        write_video(diagnostic_path, masks, fields, rows, fit, diagnostic=True, fps=args.fps)
        write_video(clean_path, masks, fields, rows, fit, diagnostic=False, fps=args.fps)
        video_checks = [verify_video(diagnostic_path), verify_video(clean_path)]
    write_readme(output_dir / "README.md", params, fit, video_checks)

    print(f"Wrote outputs to {output_dir}")
    print(
        "Fit: "
        f"sigma={fit.sigma:.4f}, CI=[{fit.ci_low:.4f}, {fit.ci_high:.4f}], "
        f"R2={fit.r2:.4f}, n={fit.n}, area_range={fit.area_range:.2f}x"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
