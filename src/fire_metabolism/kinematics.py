"""Boundary-advance identities and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BoundaryRate:
    tracked_rate: float
    source_rate: float
    total_rate: float
    active_length: float
    mapped_perimeter: float
    active_fraction: float
    mean_normal_speed: float | None


def boundary_area_rate(
    segment_lengths,
    normal_speeds,
    active=None,
    source_rate: float = 0.0,
) -> BoundaryRate:
    """Discretize integral_Gamma v_n ds without counting a source twice."""
    lengths = np.asarray(segment_lengths, dtype=float)
    speeds = np.asarray(normal_speeds, dtype=float)
    if lengths.shape != speeds.shape or lengths.ndim != 1:
        raise ValueError("segment_lengths and normal_speeds must be matching vectors")
    if np.any(lengths < 0) or source_rate < 0:
        raise ValueError("lengths and source_rate must be nonnegative")
    mask = np.ones_like(lengths, dtype=bool) if active is None else np.asarray(active, dtype=bool)
    if mask.shape != lengths.shape:
        raise ValueError("active must match segment arrays")
    tracked = float(np.sum(lengths[mask] * speeds[mask]))
    active_length = float(np.sum(lengths[mask]))
    perimeter = float(np.sum(lengths))
    active_fraction = active_length / perimeter if perimeter > 0 else 0.0
    mean_speed = tracked / active_length if active_length > 0 else None
    return BoundaryRate(tracked, source_rate, tracked + source_rate, active_length, perimeter, active_fraction, mean_speed)


def swept_area_first_order(segment_lengths, normal_speeds, dt: float, active=None) -> float:
    if dt < 0:
        raise ValueError("dt must be nonnegative")
    return boundary_area_rate(segment_lengths, normal_speeds, active).tracked_rate * dt


def area_rate_residual(observed_rate: float, active_fraction: float, mean_speed: float, perimeter: float) -> float:
    return observed_rate - active_fraction * mean_speed * perimeter


def aggregate_components(components: list[dict[str, np.ndarray]], source_rate: float = 0.0) -> BoundaryRate:
    lengths = np.concatenate([np.asarray(component["lengths"]) for component in components])
    speeds = np.concatenate([np.asarray(component["speeds"]) for component in components])
    active = np.concatenate([np.asarray(component.get("active", np.ones_like(component["lengths"])), dtype=bool) for component in components])
    return boundary_area_rate(lengths, speeds, active, source_rate)
