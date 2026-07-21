"""Transparent Huygens wavelet front-propagation emulator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from skimage import draw, measure, morphology

from .geometry import Domain, initial_polygon
from .metrics import mask_to_polygon, measure_mask, rasterize_polygon, save_polygon_csv


def _draw_wavelet(
    mask: np.ndarray,
    center_rc: tuple[float, float],
    semi_major: float,
    semi_minor: float,
    angle_degrees: float,
) -> None:
    rr, cc = draw.ellipse(
        center_rc[0],
        center_rc[1],
        semi_minor,
        semi_major,
        rotation=np.deg2rad(angle_degrees),
        shape=mask.shape,
    )
    mask[rr, cc] = True


def _front_points(mask: np.ndarray, samples: int) -> np.ndarray:
    contours = measure.find_contours(mask.astype(float), level=0.5)
    if not contours:
        return np.empty((0, 2))
    contour = max(contours, key=len)
    if len(contour) <= samples:
        return contour
    indices = np.linspace(0, len(contour) - 1, samples).astype(int)
    return contour[indices]


def run_huygens(config: dict[str, Any], output_root: Path) -> list[dict[str, object]]:
    domain_cfg = config["domain"]
    model_cfg = config["models"]["huygens"]
    domain = Domain(
        width=int(domain_cfg["width"]),
        height=int(domain_cfg["height"]),
        cell_size=float(domain_cfg["cell_size"]),
        center=tuple(domain_cfg["center"]),
    )
    rows: list[dict[str, object]] = []
    output_steps = int(config["experiment"]["output_steps"])
    samples = int(model_cfg["perimeter_samples"])
    step_size = float(model_cfg["step_size"])
    seed_base = int(config["experiment"].get("random_seed", 42))

    for scenario in config["scenarios"]:
        reps = int(scenario.get("replicates", 1))
        for replicate in range(reps):
            for shape in config["initial_shapes"]:
                mask = rasterize_polygon(
                    initial_polygon(shape, domain, seed=seed_base + replicate),
                    (domain.height, domain.width),
                )
                direction = float(scenario.get("direction_degrees", 0.0))
                for step in range(1, output_steps + 1):
                    front = _front_points(mask, samples=samples)
                    grown = mask.copy()
                    wind_factor = float(scenario.get("wind_factor", 1.0))
                    heterogeneity = float(scenario.get("heterogeneity", 0.0))
                    local_step = step_size * float(scenario.get("spread_rate", 1.0))
                    if scenario.get("turn_degrees_per_step") is not None:
                        direction = float(scenario["direction_degrees"]) + step * float(
                            scenario["turn_degrees_per_step"]
                        )
                    rng = np.random.default_rng(seed_base + replicate + step)
                    for row, col in front:
                        multiplier = 1.0 + heterogeneity * rng.uniform(-0.5, 0.5)
                        _draw_wavelet(
                            grown,
                            (row, col),
                            semi_major=max(1.0, local_step * wind_factor * multiplier),
                            semi_minor=max(1.0, local_step * multiplier),
                            angle_degrees=direction,
                        )
                    mask = morphology.closing(grown, morphology.disk(1))
                    time = float(step * step_size)
                    record = measure_mask(
                        mask,
                        model="huygens_emulator",
                        implementation_type="geometric_emulator",
                        scenario=scenario["name"],
                        replicate=replicate,
                        initial_shape=shape,
                        resolution=domain.cell_size,
                        time=time,
                    ).as_dict()
                    rows.append(record)
                    polygon = mask_to_polygon(mask, domain.cell_size)
                    save_polygon_csv(
                        output_root
                        / "perimeters"
                        / "huygens_emulator"
                        / scenario["name"]
                        / f"{shape}_rep{replicate}_step{step:03d}.csv",
                        polygon,
                    )
                    if record["domain_edge_contact"]:
                        break
    return rows
