"""Common area and perimeter measurements for vector and raster fire output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from skimage import draw, measure, morphology

from .geometry import polygon_area, polygon_perimeter


@dataclass(frozen=True)
class MetricRecord:
    model: str
    implementation_type: str
    scenario: str
    replicate: int
    initial_shape: str
    resolution: float
    time: float
    area: float
    exterior_perimeter: float
    hole_perimeter: float
    total_perimeter: float
    component_count: int
    largest_component_fraction: float
    domain_edge_contact: bool
    valid_geometry: bool
    perimeter_estimator: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def rasterize_polygon(points: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Rasterize an x/y polygon into a boolean row/column mask."""
    mask = np.zeros(shape, dtype=bool)
    if len(points) < 3:
        return mask
    rr, cc = draw.polygon(points[:, 1], points[:, 0], shape=shape)
    mask[rr, cc] = True
    return mask


def domain_edge_contact(mask: np.ndarray) -> bool:
    return bool(mask[0, :].any() or mask[-1, :].any() or mask[:, 0].any() or mask[:, -1].any())


def largest_component(mask: np.ndarray) -> tuple[np.ndarray, int, float]:
    labeled = measure.label(mask.astype(bool), connectivity=2)
    regions = measure.regionprops(labeled)
    if not regions:
        return np.zeros_like(mask, dtype=bool), 0, 0.0
    largest = max(regions, key=lambda region: region.area)
    total = sum(region.area for region in regions)
    return labeled == largest.label, len(regions), float(largest.area / total)


def contour_perimeter(mask: np.ndarray, cell_size: float = 1.0) -> float:
    padded = np.pad(mask.astype(float), 1, mode="constant", constant_values=0.0)
    contours = measure.find_contours(padded, level=0.5)
    if not contours:
        return 0.0
    perimeter = 0.0
    for contour in contours:
        contour = contour - 1.0
        diffs = np.diff(np.vstack([contour, contour[0]]), axis=0)
        perimeter += float(np.sum(np.sqrt(np.sum(diffs * diffs, axis=1))) * cell_size)
    return perimeter


def crofton_perimeter(mask: np.ndarray, cell_size: float = 1.0) -> float:
    return float(measure.perimeter_crofton(mask.astype(bool), directions=4) * cell_size)


def mask_to_polygon(mask: np.ndarray, cell_size: float = 1.0) -> np.ndarray:
    padded = np.pad(mask.astype(float), 1, mode="constant", constant_values=0.0)
    contours = measure.find_contours(padded, level=0.5)
    if not contours:
        return np.empty((0, 2), dtype=float)
    contour = max(contours, key=len) - 1.0
    contour[:, 0] = np.clip(contour[:, 0], 0, mask.shape[0] - 1)
    contour[:, 1] = np.clip(contour[:, 1], 0, mask.shape[1] - 1)
    return np.column_stack([contour[:, 1], contour[:, 0]]) * cell_size


def measure_mask(
    mask: np.ndarray,
    *,
    model: str,
    implementation_type: str,
    scenario: str,
    replicate: int,
    initial_shape: str,
    resolution: float,
    time: float,
    estimator: str = "marching_squares",
    largest_only: bool = False,
) -> MetricRecord:
    mask = mask.astype(bool)
    component_mask, component_count, largest_fraction = largest_component(mask)
    primary_mask = component_mask if largest_only else mask
    area = float(primary_mask.sum() * resolution * resolution)
    if estimator == "crofton":
        exterior = crofton_perimeter(primary_mask, resolution)
    else:
        exterior = contour_perimeter(primary_mask, resolution)

    return MetricRecord(
        model=model,
        implementation_type=implementation_type,
        scenario=scenario,
        replicate=replicate,
        initial_shape=initial_shape,
        resolution=resolution,
        time=time,
        area=area,
        exterior_perimeter=exterior,
        hole_perimeter=0.0,
        total_perimeter=exterior,
        component_count=component_count,
        largest_component_fraction=largest_fraction,
        domain_edge_contact=domain_edge_contact(primary_mask),
        valid_geometry=area > 0 and exterior > 0,
        perimeter_estimator=estimator,
    )


def measure_polygon(
    points: np.ndarray,
    *,
    model: str,
    implementation_type: str,
    scenario: str,
    replicate: int,
    initial_shape: str,
    resolution: float,
    time: float,
) -> MetricRecord:
    area = polygon_area(points) * resolution * resolution
    perimeter = polygon_perimeter(points) * resolution
    return MetricRecord(
        model=model,
        implementation_type=implementation_type,
        scenario=scenario,
        replicate=replicate,
        initial_shape=initial_shape,
        resolution=resolution,
        time=time,
        area=area,
        exterior_perimeter=perimeter,
        hole_perimeter=0.0,
        total_perimeter=perimeter,
        component_count=1,
        largest_component_fraction=1.0,
        domain_edge_contact=False,
        valid_geometry=area > 0 and perimeter > 0,
        perimeter_estimator="analytic_vector",
    )


def save_polygon_csv(path: Path, polygon: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(path, polygon, delimiter=",", header="x,y", comments="")
