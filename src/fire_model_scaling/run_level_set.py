"""Eulerian level-set-style front propagation emulator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .geometry import Domain, initial_polygon
from .metrics import mask_to_polygon, measure_mask, rasterize_polygon, save_polygon_csv


def _arrival_field(
    domain: Domain,
    scenario: dict[str, Any],
    initial_shape: str,
    seed: int,
) -> np.ndarray:
    yy, xx = np.mgrid[0 : domain.height, 0 : domain.width]
    cx, cy = domain.origin_center
    theta = np.deg2rad(float(scenario.get("direction_degrees", 0.0)))
    along = (xx - cx) * np.cos(theta) + (yy - cy) * np.sin(theta)
    across = -(xx - cx) * np.sin(theta) + (yy - cy) * np.cos(theta)
    wind_factor = float(scenario.get("wind_factor", 1.0))
    distance = np.sqrt((along / wind_factor) ** 2 + across**2)

    ignition = rasterize_polygon(
        initial_polygon(initial_shape, domain, seed=seed), (domain.height, domain.width)
    )
    ignition_points = np.column_stack(np.nonzero(ignition))
    if len(ignition_points):
        # Approximate arrival by distance to ignition centroid plus anisotropic metric.
        center = ignition_points.mean(axis=0)
        distance = np.maximum(0.0, distance - np.sqrt(np.sum((center - np.array([cy, cx])) ** 2)))

    heterogeneity = float(scenario.get("heterogeneity", 0.0))
    if heterogeneity:
        rng = np.random.default_rng(seed)
        field = rng.normal(0.0, 1.0, size=(domain.height, domain.width))
        for _ in range(8):
            field = (
                field
                + np.roll(field, 1, 0)
                + np.roll(field, -1, 0)
                + np.roll(field, 1, 1)
                + np.roll(field, -1, 1)
            ) / 5.0
        field = (field - field.min()) / max(field.max() - field.min(), 1e-9)
        speed_multiplier = 1.0 + heterogeneity * (field - 0.5)
        distance = distance / np.clip(speed_multiplier, 0.25, None)

    return distance / float(scenario.get("spread_rate", 1.0))


def run_level_set(config: dict[str, Any], output_root: Path) -> list[dict[str, object]]:
    domain_cfg = config["domain"]
    domain = Domain(
        width=int(domain_cfg["width"]),
        height=int(domain_cfg["height"]),
        cell_size=float(domain_cfg["cell_size"]),
        center=tuple(domain_cfg["center"]),
    )
    rows: list[dict[str, object]] = []
    output_steps = int(config["experiment"]["output_steps"])
    seed_base = int(config["experiment"].get("random_seed", 42))

    for scenario in config["scenarios"]:
        reps = int(scenario.get("replicates", 1))
        for replicate in range(reps):
            for shape in config["initial_shapes"]:
                arrival = _arrival_field(domain, scenario, shape, seed_base + replicate)
                valid_times = np.geomspace(5.0, np.percentile(arrival, 35), output_steps)
                for step, time in enumerate(valid_times, start=1):
                    mask = arrival <= time
                    record = measure_mask(
                        mask,
                        model="level_set_emulator",
                        implementation_type="geometric_emulator",
                        scenario=scenario["name"],
                        replicate=replicate,
                        initial_shape=shape,
                        resolution=domain.cell_size,
                        time=float(time),
                    ).as_dict()
                    rows.append(record)
                    polygon = mask_to_polygon(mask, domain.cell_size)
                    save_polygon_csv(
                        output_root
                        / "perimeters"
                        / "level_set_emulator"
                        / scenario["name"]
                        / f"{shape}_rep{replicate}_step{step:03d}.csv",
                        polygon,
                    )
    return rows
