"""Geometry helpers for fire perimeter scaling experiments."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import special


Array = np.ndarray


@dataclass(frozen=True)
class Domain:
    width: int
    height: int
    cell_size: float = 1.0
    center: tuple[float, float] | None = None

    @property
    def origin_center(self) -> tuple[float, float]:
        if self.center is not None:
            return self.center
        return (self.width / 2.0, self.height / 2.0)


def close_polygon(points: Array) -> Array:
    """Return points with the first vertex repeated at the end."""
    if len(points) == 0:
        return points
    if np.allclose(points[0], points[-1]):
        return points
    return np.vstack([points, points[0]])


def polygon_area(points: Array) -> float:
    closed = close_polygon(np.asarray(points, dtype=float))
    x = closed[:, 0]
    y = closed[:, 1]
    return float(abs(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])) / 2.0)


def polygon_perimeter(points: Array) -> float:
    closed = close_polygon(np.asarray(points, dtype=float))
    if len(closed) < 2:
        return 0.0
    diffs = np.diff(closed, axis=0)
    return float(np.sum(np.sqrt(np.sum(diffs * diffs, axis=1))))


def ellipse_polygon(
    center: tuple[float, float],
    semi_major: float,
    semi_minor: float,
    angle_degrees: float = 0.0,
    n: int = 256,
) -> Array:
    theta = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    xy = np.column_stack([semi_major * np.cos(theta), semi_minor * np.sin(theta)])
    angle = math.radians(angle_degrees)
    rotation = np.array(
        [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
    )
    return xy @ rotation.T + np.asarray(center, dtype=float)


def circle_polygon(center: tuple[float, float], radius: float, n: int = 160) -> Array:
    return ellipse_polygon(center, radius, radius, n=n)


def irregular_polygon(
    center: tuple[float, float],
    radius: float,
    n: int = 32,
    seed: int = 1,
) -> Array:
    rng = np.random.default_rng(seed)
    theta = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    multipliers = rng.uniform(0.65, 1.25, size=n)
    # Smooth enough to avoid pathological self-crossings while staying irregular.
    multipliers = (
        np.roll(multipliers, -1) + 2.0 * multipliers + np.roll(multipliers, 1)
    ) / 4.0
    points = np.column_stack(
        [
            center[0] + radius * multipliers * np.cos(theta),
            center[1] + radius * multipliers * np.sin(theta),
        ]
    )
    return points


def line_ignition(
    center: tuple[float, float],
    length: float,
    width: float,
    angle_degrees: float = 0.0,
) -> Array:
    x = length / 2.0
    y = width / 2.0
    points = np.array([[-x, -y], [x, -y], [x, y], [-x, y]], dtype=float)
    angle = math.radians(angle_degrees)
    rotation = np.array(
        [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
    )
    return points @ rotation.T + np.asarray(center, dtype=float)


def initial_polygon(name: str, domain: Domain, seed: int = 1) -> Array:
    center = domain.origin_center
    if name == "compact":
        return circle_polygon(center, radius=5.0, n=96)
    if name == "irregular":
        return irregular_polygon(center, radius=7.0, seed=seed)
    if name == "line":
        return line_ignition(center, length=22.0, width=3.0, angle_degrees=20.0)
    raise ValueError(f"Unknown initial shape: {name}")


def exact_ellipse_area(semi_major: float, semi_minor: float) -> float:
    return float(math.pi * semi_major * semi_minor)


def exact_ellipse_perimeter(semi_major: float, semi_minor: float) -> float:
    a = max(semi_major, semi_minor)
    b = min(semi_major, semi_minor)
    eccentricity_sq = 1.0 - (b * b) / (a * a)
    return float(4.0 * a * special.ellipe(eccentricity_sq))


def scaled_polygon(points: Array, scale: float, center: tuple[float, float] | None = None) -> Array:
    points = np.asarray(points, dtype=float)
    if center is None:
        center_arr = points.mean(axis=0)
    else:
        center_arr = np.asarray(center, dtype=float)
    return center_arr + scale * (points - center_arr)
