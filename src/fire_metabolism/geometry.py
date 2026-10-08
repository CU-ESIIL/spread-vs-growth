"""Geometric identities, constructions, and synthetic scaling families."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import special


Array = np.ndarray


def polygon_area(vertices: Array) -> float:
    """Return unsigned shoelace area for an open or closed polygon."""
    points = np.asarray(vertices, dtype=float)
    if len(points) < 3:
        return 0.0
    if not np.allclose(points[0], points[-1]):
        points = np.vstack((points, points[0]))
    return float(abs(np.sum(points[:-1, 0] * points[1:, 1] - points[1:, 0] * points[:-1, 1])) / 2)


def polygon_perimeter(vertices: Array) -> float:
    """Return Euclidean perimeter for an open or closed polygon."""
    points = np.asarray(vertices, dtype=float)
    if len(points) < 2:
        return 0.0
    if not np.allclose(points[0], points[-1]):
        points = np.vstack((points, points[0]))
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())


def similarity_boundary(content: float, n: int, c_n: float, b_n: float) -> float:
    """Evaluate S_(n-1) = b_n c_n^(-(n-1)/n) V_n^((n-1)/n)."""
    if content < 0 or n < 1 or c_n <= 0 or b_n <= 0:
        raise ValueError("content must be nonnegative; n, c_n, and b_n must be positive")
    exponent = (n - 1) / n
    return float(b_n * c_n ** (-exponent) * content**exponent)


def dimensional_ladder(length: float) -> dict[str, tuple[float, float]]:
    """Return content and boundary measure for canonical similar objects."""
    if length <= 0:
        raise ValueError("length must be positive")
    radius = length
    return {
        "interval": (length, 2.0),
        "square": (length**2, 4 * length),
        "circle": (math.pi * radius**2, 2 * math.pi * radius),
        "cube": (length**3, 6 * length**2),
        "sphere": ((4 / 3) * math.pi * radius**3, 4 * math.pi * radius**2),
    }


def ellipse_area(semi_major: float, semi_minor: float) -> float:
    if semi_major <= 0 or semi_minor <= 0:
        raise ValueError("ellipse semiaxes must be positive")
    return float(math.pi * semi_major * semi_minor)


def ellipse_perimeter(semi_major: float, semi_minor: float) -> float:
    if semi_major <= 0 or semi_minor <= 0:
        raise ValueError("ellipse semiaxes must be positive")
    a, b = max(semi_major, semi_minor), min(semi_major, semi_minor)
    return float(4 * a * special.ellipe(1 - (b / a) ** 2))


def ellipse_family(
    scales: Array,
    aspect_ratio: float = 2.0,
    aspect_power: float = 0.0,
) -> tuple[Array, Array, Array]:
    """Construct smooth ellipses, optionally with aspect ratio changing by size.

    ``aspect_power=0`` is the fixed-shape null.  Positive values deliberately
    elongate larger ellipses and can change the between-size apparent slope.
    """
    scales = np.asarray(scales, dtype=float)
    if np.any(scales <= 0) or aspect_ratio < 1:
        raise ValueError("scales must be positive and aspect_ratio at least one")
    ratios = aspect_ratio * (scales / scales[0]) ** aspect_power
    minor = scales
    major = scales * ratios
    area = np.array([ellipse_area(a, b) for a, b in zip(major, minor, strict=True)])
    perimeter = np.array([ellipse_perimeter(a, b) for a, b in zip(major, minor, strict=True)])
    return area, perimeter, ratios


@dataclass(frozen=True)
class RightAngleGeneration:
    generation: int
    base_length: float
    side_length: float
    pair_count: int
    feature_width: float
    feature_depth: float
    vertices: Array

    @property
    def expected_area(self) -> float:
        return self.base_length**2 * 64**self.generation

    @property
    def expected_perimeter(self) -> float:
        return 4 * self.base_length * 16**self.generation

    @property
    def smooth_perimeter(self) -> float:
        return 4 * self.side_length

    @property
    def excess_perimeter(self) -> float:
        return self.expected_perimeter / self.smooth_perimeter


def _deduplicate_consecutive(points: list[tuple[float, float]]) -> Array:
    result: list[tuple[float, float]] = []
    for point in points:
        if not result or point != result[-1]:
            result.append(point)
    return np.asarray(result, dtype=float)


def right_angle_polygon(generation: int, base_length: float = 1.0) -> RightAngleGeneration:
    """Construct the exact area-preserving SI tooth/notch polygon.

    The polygon is a finite, simple, rectilinear polygon.  Its between-size
    family has slope 2/3, while each member has fine-scale boundary dimension 1.
    """
    if generation < 0 or int(generation) != generation:
        raise ValueError("generation must be a nonnegative integer")
    if base_length <= 0:
        raise ValueError("base_length must be positive")
    j = int(generation)
    length = base_length * 8**j
    count = 8**j
    width = base_length / 4
    depth = base_length * (2**j - 1)
    gap = (length - 2 * count * width) / (count + 1)

    top: list[tuple[float, float]] = [(0.0, length)]
    x = 0.0
    for _ in range(count):
        x += gap
        top.append((x, length))
        top.extend(((x, length + depth), (x + width, length + depth)))
        x += width
        top.append((x, length))
        top.extend(((x, length - depth), (x + width, length - depth)))
        x += width
        top.append((x, length))
    top.append((length, length))
    top_array = _deduplicate_consecutive(top)
    vertices = np.vstack(
        (
            np.array([[0.0, 0.0], [length, 0.0], [length, length]]),
            top_array[-2::-1],
        )
    )
    return RightAngleGeneration(j, base_length, length, count, width, depth, vertices)


def connectivity(component_areas: Array) -> float:
    """Largest connected-component area divided by total patch area."""
    areas = np.asarray(component_areas, dtype=float)
    if areas.size == 0 or np.any(areas < 0) or areas.sum() <= 0:
        raise ValueError("component areas must be nonnegative with positive total")
    return float(areas.max() / areas.sum())


def box_count(points: Array, epsilon: float) -> int:
    """Count occupied axis-aligned boxes for sampled coordinates."""
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or epsilon <= 0:
        raise ValueError("points must have shape (n, 2) and epsilon must be positive")
    origin = points.min(axis=0)
    cells = np.floor((points - origin) / epsilon + 1e-12).astype(int)
    return int(np.unique(cells, axis=0).shape[0])


def sample_polygon_boundary(vertices: Array, spacing: float) -> Array:
    """Sample polygon edges at approximately fixed point spacing."""
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    points = np.asarray(vertices, dtype=float)
    closed = np.vstack((points, points[0])) if not np.allclose(points[0], points[-1]) else points
    samples: list[Array] = []
    for start, end in zip(closed[:-1], closed[1:], strict=True):
        length = np.linalg.norm(end - start)
        n = max(1, int(math.ceil(length / spacing)))
        samples.extend(start + (end - start) * (i / n) for i in range(n))
    return np.asarray(samples)
