"""Numerical spatial-reorganization metrics for the FIRED experiment.

The primary distance is sliced Wasserstein, an efficient optimal-transport
metric obtained by averaging exact one-dimensional transports over fixed
directions. The unbalanced implementation uses KL-relaxed entropic transport.
Neither quantity is interpreted as literal movement of burned material.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage


@dataclass(frozen=True)
class UnbalancedTransportResult:
    distance: float
    iterations: int
    converged: bool
    marginal_error: float


def _validate_support(points: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    points = np.asarray(points, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("points must have shape (n, 2)")
    if len(points) == 0 or weights.shape != (len(points),):
        raise ValueError("weights must contain one value per support point")
    if np.any(weights < 0) or not np.isfinite(points).all() or not np.isfinite(weights).all():
        raise ValueError("transport supports and weights must be finite and nonnegative")
    if weights.sum() <= 0:
        raise ValueError("transport mass must be positive")
    return points, weights


def deterministic_support(
    mask: np.ndarray,
    *,
    pixel_size: float = 1.0,
    origin: tuple[float, float] = (0.0, 0.0),
    max_points: int = 128,
) -> tuple[np.ndarray, np.ndarray]:
    """Return an evenly thinned support from occupied raster-cell centers."""
    occupied = np.argwhere(np.asarray(mask, dtype=bool))
    if len(occupied) == 0:
        raise ValueError("mask has no occupied cells")
    if max_points < 2:
        raise ValueError("max_points must be at least two")
    if len(occupied) > max_points:
        indices = np.linspace(0, len(occupied) - 1, max_points).round().astype(int)
        occupied = occupied[indices]
    x0, y0 = origin
    points = np.column_stack(
        [x0 + (occupied[:, 1] + 0.5) * pixel_size,
         y0 + (occupied[:, 0] + 0.5) * pixel_size]
    )
    weights = np.full(len(points), pixel_size**2, dtype=float)
    return points, weights


def _weighted_quantiles(values: np.ndarray, weights: np.ndarray, q: np.ndarray) -> np.ndarray:
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    cumulative = np.cumsum(weights) - 0.5 * weights
    cumulative /= weights.sum()
    return np.interp(q, cumulative, values, left=values[0], right=values[-1])


def sliced_wasserstein(
    points_a: np.ndarray,
    weights_a: np.ndarray,
    points_b: np.ndarray,
    weights_b: np.ndarray,
    *,
    order: int = 2,
    directions: int = 16,
    quantiles: int = 128,
    translation_normalized: bool = False,
) -> float:
    """Compute deterministic sliced W1 or W2 in the coordinate units."""
    points_a, weights_a = _validate_support(points_a, weights_a)
    points_b, weights_b = _validate_support(points_b, weights_b)
    if order not in (1, 2):
        raise ValueError("only sliced W1 and W2 are implemented")
    if directions < 2 or quantiles < 8:
        raise ValueError("directions and quantiles are too small")
    if translation_normalized:
        points_a = points_a - np.average(points_a, axis=0, weights=weights_a)
        points_b = points_b - np.average(points_b, axis=0, weights=weights_b)
    q = (np.arange(quantiles, dtype=float) + 0.5) / quantiles
    powers = []
    for angle in np.linspace(0.0, np.pi, directions, endpoint=False):
        direction = np.array([np.cos(angle), np.sin(angle)])
        qa = _weighted_quantiles(points_a @ direction, weights_a, q)
        qb = _weighted_quantiles(points_b @ direction, weights_b, q)
        powers.append(np.mean(np.abs(qa - qb) ** order))
    return float(np.mean(powers) ** (1.0 / order))


def _kl_divergence(x: np.ndarray, y: np.ndarray) -> float:
    positive = x > 0
    value = np.sum(x[positive] * np.log(x[positive] / np.maximum(y[positive], 1e-300)))
    return float(value - x.sum() + y.sum())


def unbalanced_sinkhorn_distance(
    points_a: np.ndarray,
    weights_a: np.ndarray,
    points_b: np.ndarray,
    weights_b: np.ndarray,
    *,
    epsilon: float = 0.05,
    mass_penalty: float = 1.0,
    scale: float | None = None,
    max_iterations: int = 200,
    tolerance: float = 1e-7,
) -> UnbalancedTransportResult:
    """KL-relaxed entropic unbalanced transport with squared ground cost."""
    points_a, weights_a = _validate_support(points_a, weights_a)
    points_b, weights_b = _validate_support(points_b, weights_b)
    if epsilon <= 0 or mass_penalty <= 0:
        raise ValueError("epsilon and mass_penalty must be positive")
    if scale is None:
        scale = float(np.linalg.norm(np.ptp(np.vstack([points_a, points_b]), axis=0)))
    scale = max(float(scale), 1e-12)
    delta = (points_a[:, None, :] - points_b[None, :, :]) / scale
    cost = np.sum(delta * delta, axis=2)
    kernel = np.maximum(np.exp(-np.minimum(cost / epsilon, 700.0)), 1e-300)
    common_scale = max(weights_a.sum(), weights_b.sum())
    a = weights_a / common_scale
    b = weights_b / common_scale
    exponent = mass_penalty / (mass_penalty + epsilon)
    u = np.ones_like(a)
    v = np.ones_like(b)
    converged = False
    error = np.inf
    for iteration in range(1, max_iterations + 1):
        old_u = u.copy()
        u = (a / np.maximum(kernel @ v, 1e-300)) ** exponent
        v = (b / np.maximum(kernel.T @ u, 1e-300)) ** exponent
        error = float(np.max(np.abs(np.log(np.maximum(u, 1e-300) / np.maximum(old_u, 1e-300)))))
        if error < tolerance:
            converged = True
            break
    plan = (u[:, None] * kernel) * v[None, :]
    objective = (
        float(np.sum(plan * cost))
        + mass_penalty * _kl_divergence(plan.sum(axis=1), a)
        + mass_penalty * _kl_divergence(plan.sum(axis=0), b)
    )
    return UnbalancedTransportResult(
        distance=float(np.sqrt(max(objective, 0.0)) * scale),
        iterations=iteration,
        converged=converged,
        marginal_error=error,
    )


def binary_shape_metrics(actual: np.ndarray, reference: np.ndarray, *, pixel_size: float = 1.0) -> dict[str, float]:
    """Simple spatial metrics against which transport must earn complexity."""
    actual = np.asarray(actual, dtype=bool)
    reference = np.asarray(reference, dtype=bool)
    if actual.shape != reference.shape or not actual.any() or not reference.any():
        raise ValueError("nonempty masks with matching shapes are required")
    intersection = np.logical_and(actual, reference).sum()
    union = np.logical_or(actual, reference).sum()
    symmetric = np.logical_xor(actual, reference).sum()
    ca = np.mean(np.argwhere(actual), axis=0)
    cb = np.mean(np.argwhere(reference), axis=0)
    boundary_a = np.logical_xor(actual, ndimage.binary_erosion(actual))
    boundary_b = np.logical_xor(reference, ndimage.binary_erosion(reference))
    da = ndimage.distance_transform_edt(~boundary_a)
    db = ndimage.distance_transform_edt(~boundary_b)
    hausdorff = max(float(da[boundary_b].max(initial=0)), float(db[boundary_a].max(initial=0)))
    return {
        "iou": float(intersection / union),
        "symmetric_difference_area": float(symmetric * pixel_size**2),
        "centroid_displacement": float(np.linalg.norm(ca - cb) * pixel_size),
        "hausdorff_distance": float(hausdorff * pixel_size),
    }


def area_matched_dilation(mask: np.ndarray, target_cells: int) -> np.ndarray:
    """Deterministically dilate a binary footprint to an approximate target area."""
    result = np.asarray(mask, dtype=bool).copy()
    if target_cells < int(result.sum()):
        raise ValueError("target area cannot be smaller than the starting footprint")
    structure = ndimage.generate_binary_structure(2, 1)
    while int(result.sum()) < target_cells:
        expanded = ndimage.binary_dilation(result, structure=structure)
        if expanded.sum() == result.sum():
            break
        result = expanded
    return result
