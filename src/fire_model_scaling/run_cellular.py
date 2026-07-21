"""Cellular-neighbor spread emulator."""

from __future__ import annotations

import heapq
import math
from pathlib import Path
from typing import Any

import numpy as np

from .geometry import Domain, initial_polygon
from .metrics import mask_to_polygon, measure_mask, rasterize_polygon, save_polygon_csv


def _neighbors(connectivity: int) -> list[tuple[int, int, float]]:
    base = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0)]
    if connectivity == 4:
        return base
    diag = 1.0 / math.sqrt(2.0)
    return base + [(-1, -1, diag), (-1, 1, diag), (1, -1, diag), (1, 1, diag)]


def _arrival_times(
    domain: Domain,
    ignition: np.ndarray,
    scenario: dict[str, Any],
    seed: int,
    connectivity: int,
) -> np.ndarray:
    arrival = np.full((domain.height, domain.width), np.inf)
    queue: list[tuple[float, int, int]] = []
    for row, col in np.column_stack(np.nonzero(ignition)):
        arrival[row, col] = 0.0
        heapq.heappush(queue, (0.0, int(row), int(col)))

    theta = math.radians(float(scenario.get("direction_degrees", 0.0)))
    wind_vec = np.array([math.sin(theta), math.cos(theta)])
    wind_factor = float(scenario.get("wind_factor", 1.0))
    heterogeneity = float(scenario.get("heterogeneity", 0.0))
    rng = np.random.default_rng(seed)
    rate_field = np.ones_like(arrival)
    if heterogeneity:
        rate_field += heterogeneity * rng.uniform(-0.5, 0.5, size=arrival.shape)
        rate_field = np.clip(rate_field, 0.2, None)

    for row, col in list(np.column_stack(np.nonzero(ignition))):
        rate_field[row, col] = 1.0

    neighbor_steps = _neighbors(connectivity)
    while queue:
        time, row, col = heapq.heappop(queue)
        if time > arrival[row, col]:
            continue
        for drow, dcol, inv_distance in neighbor_steps:
            nr = row + drow
            nc = col + dcol
            if nr < 0 or nr >= domain.height or nc < 0 or nc >= domain.width:
                continue
            direction = np.array([drow, dcol], dtype=float)
            direction = direction / max(np.linalg.norm(direction), 1e-9)
            anisotropy = 1.0 + (wind_factor - 1.0) * max(0.0, float(direction @ wind_vec))
            speed = float(scenario.get("spread_rate", 1.0)) * anisotropy * rate_field[nr, nc]
            delay = 1.0 / (max(speed, 1e-6) * inv_distance)
            new_time = time + delay
            if new_time < arrival[nr, nc]:
                arrival[nr, nc] = new_time
                heapq.heappush(queue, (new_time, nr, nc))
    return arrival


def run_cellular(config: dict[str, Any], output_root: Path) -> list[dict[str, object]]:
    domain_cfg = config["domain"]
    model_cfg = config["models"]["cellular"]
    domain = Domain(
        width=int(domain_cfg["width"]),
        height=int(domain_cfg["height"]),
        cell_size=float(domain_cfg["cell_size"]),
        center=tuple(domain_cfg["center"]),
    )
    output_steps = int(config["experiment"]["output_steps"])
    connectivity = int(model_cfg.get("connectivity", 8))
    seed_base = int(config["experiment"].get("random_seed", 42))
    rows: list[dict[str, object]] = []

    for scenario in config["scenarios"]:
        reps = int(scenario.get("replicates", 1))
        for replicate in range(reps):
            for shape in config["initial_shapes"]:
                ignition = rasterize_polygon(
                    initial_polygon(shape, domain, seed=seed_base + replicate),
                    (domain.height, domain.width),
                )
                arrival = _arrival_times(
                    domain, ignition, scenario, seed_base + replicate, connectivity=connectivity
                )
                finite = arrival[np.isfinite(arrival)]
                times = np.geomspace(max(1.0, finite.min() + 1.0), np.percentile(finite, 35), output_steps)
                for step, time in enumerate(times, start=1):
                    mask = arrival <= time
                    record = measure_mask(
                        mask,
                        model="cellular_emulator",
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
                        / "cellular_emulator"
                        / scenario["name"]
                        / f"{shape}_rep{replicate}_step{step:03d}.csv",
                        polygon,
                    )
    return rows
