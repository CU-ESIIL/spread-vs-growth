"""Exact and rasterized ellipse benchmark."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

from .geometry import (
    Domain,
    ellipse_polygon,
    exact_ellipse_area,
    exact_ellipse_perimeter,
)
from .metrics import measure_mask, measure_polygon, rasterize_polygon, save_polygon_csv


def run_exact_ellipse(config: dict[str, Any], output_root: Path) -> list[dict[str, object]]:
    domain_cfg = config["domain"]
    model_cfg = config["models"]["exact_ellipse"]
    experiment_cfg = config["experiment"]
    domain = Domain(
        width=int(domain_cfg["width"]),
        height=int(domain_cfg["height"]),
        cell_size=float(domain_cfg["cell_size"]),
        center=tuple(domain_cfg["center"]),
    )
    center = domain.origin_center
    axis_ratio = float(model_cfg["axis_ratio"])
    max_radius = float(model_cfg["max_radius"])
    output_steps = int(experiment_cfg["output_steps"])

    rows: list[dict[str, object]] = []
    radii = np.geomspace(4.0, max_radius, output_steps)
    for step, minor_axis in enumerate(radii, start=1):
        major_axis = axis_ratio * minor_axis
        if major_axis > min(domain.width, domain.height) * 0.47:
            break
        polygon = ellipse_polygon(center, major_axis, minor_axis, angle_degrees=25, n=720)
        time = float(step)
        vector_record = measure_polygon(
            polygon,
            model="exact_ellipse",
            implementation_type="analytic_benchmark",
            scenario="isotropic",
            replicate=0,
            initial_shape="compact",
            resolution=domain.cell_size,
            time=time,
        ).as_dict()
        vector_record["area"] = exact_ellipse_area(major_axis, minor_axis) * domain.cell_size**2
        vector_record["exterior_perimeter"] = exact_ellipse_perimeter(major_axis, minor_axis) * domain.cell_size
        vector_record["total_perimeter"] = vector_record["exterior_perimeter"]
        rows.append(vector_record)

        mask = rasterize_polygon(polygon, (domain.height, domain.width))
        rows.append(
            measure_mask(
                mask,
                model="exact_ellipse",
                implementation_type="rasterized_benchmark",
                scenario="isotropic",
                replicate=0,
                initial_shape="compact",
                resolution=domain.cell_size,
                time=time,
            ).as_dict()
        )

        save_polygon_csv(
            output_root / "perimeters" / "exact_ellipse" / f"ellipse_step_{step:03d}.csv",
            polygon,
        )

    return rows


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
