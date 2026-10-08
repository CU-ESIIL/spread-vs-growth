"""Synthetic demonstrations and staged spatial-model experiment metadata."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .scaling import excess_perimeter, loglog_slope


EXPERIMENT_STAGES = (
    "documented_ignition_geometry",
    "uniform_fuel",
    "flat_terrain",
    "zero_wind_control",
    "uniform_wind",
    "fixed_aspect_ratio_ellipse_control",
    "heterogeneous_fuel",
    "terrain",
    "spatially_varying_wind",
    "temporally_varying_wind",
    "spotting",
    "mergers",
    "full_configuration",
)


@dataclass(frozen=True)
class SpatialRunMetadata:
    stage: str
    replicate: int
    spatial_resolution: float
    perimeter_point_spacing: float
    mechanisms: tuple[str, ...]

    def __post_init__(self):
        if self.stage not in EXPERIMENT_STAGES:
            raise ValueError(f"unknown stage: {self.stage}")
        if self.replicate < 0 or self.spatial_resolution <= 0 or self.perimeter_point_spacing <= 0:
            raise ValueError("invalid run metadata")


def summarize_spatial_run(area, perimeter, times, smooth_coefficient=2 * np.sqrt(np.pi)):
    area = np.asarray(area, dtype=float)
    perimeter = np.asarray(perimeter, dtype=float)
    times = np.asarray(times, dtype=float)
    if not (area.shape == perimeter.shape == times.shape) or len(area) < 2:
        raise ValueError("area, perimeter, and times must be matching trajectories")
    return {
        "area": area,
        "perimeter": perimeter,
        "excess_perimeter": excess_perimeter(perimeter, area, smooth_coefficient),
        "perimeter_area_slope": loglog_slope(area, perimeter),
        "area_rate": np.gradient(area, times),
    }


def factorial_design(mechanisms: list[str]) -> list[tuple[str, ...]]:
    """Return every mechanism-removal combination, including the null control."""
    combinations: list[tuple[str, ...]] = []
    for mask in range(2 ** len(mechanisms)):
        combinations.append(tuple(name for index, name in enumerate(mechanisms) if mask & (1 << index)))
    return combinations


def rough_surface_projection(grid_size: int = 101, roughness: float = 0.2):
    """Synthetic rough graph over a disk whose projected boundary remains circular."""
    axis = np.linspace(-1, 1, grid_size)
    x, y = np.meshgrid(axis, axis)
    mask = x**2 + y**2 <= 1
    z = roughness * (np.sin(13 * x) * np.cos(11 * y) + 0.5 * np.sin(31 * (x + y)))
    return x, y, np.where(mask, z, np.nan), mask
