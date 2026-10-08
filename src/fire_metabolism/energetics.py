"""Conditional bridges from front recruitment to fuel consumption and power."""

from __future__ import annotations

import numpy as np


def front_consumption_rate(segment_lengths, normal_speeds, consumed_loadings):
    lengths = np.asarray(segment_lengths, dtype=float)
    speeds = np.asarray(normal_speeds, dtype=float)
    loadings = np.asarray(consumed_loadings, dtype=float)
    if not (lengths.shape == speeds.shape == loadings.shape):
        raise ValueError("segment arrays must have matching shapes")
    return float(np.sum(lengths * speeds * loadings))


def front_power(segment_lengths, normal_speeds, heat_yields, consumed_loadings):
    lengths = np.asarray(segment_lengths, dtype=float)
    speeds = np.asarray(normal_speeds, dtype=float)
    heat = np.asarray(heat_yields, dtype=float)
    loadings = np.asarray(consumed_loadings, dtype=float)
    if not (lengths.shape == speeds.shape == heat.shape == loadings.shape):
        raise ValueError("segment arrays must have matching shapes")
    return float(np.sum(lengths * speeds * heat * loadings))


def effective_energy_per_area(area_growth_segments, energy_per_area_segments):
    growth = np.asarray(area_growth_segments, dtype=float)
    energy = np.asarray(energy_per_area_segments, dtype=float)
    if growth.shape != energy.shape or np.any(growth < 0) or growth.sum() <= 0:
        raise ValueError("growth weights must match energies and have positive total")
    return float(np.sum(growth * energy) / np.sum(growth))


def power_components(front_associated: float, residual: float) -> float:
    if front_associated < 0 or residual < 0:
        raise ValueError("power components must be nonnegative")
    return front_associated + residual


def conditional_power(area, heat_yield, consumed_loading, k, active_fraction, mean_speed, sigma):
    """Evaluate SI Eq. S44 only after the caller supplies every closure factor."""
    return heat_yield * consumed_loading * k * active_fraction * mean_speed * np.asarray(area) ** sigma


def conditional_power_slope(sigma: float, prefactor_log_slope: float, closure_error_log_slope: float = 0.0) -> float:
    return sigma + prefactor_log_slope + closure_error_log_slope


def growth_exponent_from_factors(perimeter_exponent: float, active_fraction_exponent: float = 0.0, speed_exponent: float = 0.0) -> float:
    return perimeter_exponent + active_fraction_exponent + speed_exponent


def turbulent_trace_dimension(surface_dimension: float) -> float:
    """Conditional generic-intersection model D_trace = D_s - 1."""
    return surface_dimension - 1
