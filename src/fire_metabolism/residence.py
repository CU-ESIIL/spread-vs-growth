"""Cohort residence-time models for delayed fuel consumption."""

from __future__ import annotations

import numpy as np
from scipy.integrate import trapezoid


def exponential_kernel(age, residence_time: float):
    age = np.asarray(age, dtype=float)
    if residence_time <= 0:
        raise ValueError("residence_time must be positive")
    return np.where(age >= 0, np.exp(-age / residence_time) / residence_time, 0.0)


def cohort_consumption_rate(times, recruitment_rate, loading, kernel, preexisting_rate=None):
    """Numerically evaluate the SI cohort convolution on an arbitrary grid."""
    times = np.asarray(times, dtype=float)
    recruitment = np.asarray(recruitment_rate, dtype=float)
    loads = np.asarray(loading, dtype=float)
    if times.ndim != 1 or recruitment.shape != times.shape or loads.shape != times.shape:
        raise ValueError("times, recruitment_rate, and loading must be matching vectors")
    if np.any(np.diff(times) <= 0):
        raise ValueError("times must be strictly increasing")
    pre = np.zeros_like(times) if preexisting_rate is None else np.asarray(preexisting_rate, dtype=float)
    result = pre.copy()
    for index, current in enumerate(times):
        ages = current - times[: index + 1]
        result[index] += trapezoid(loads[: index + 1] * recruitment[: index + 1] * kernel(ages), times[: index + 1])
    return result


def finite_recruitment_exponential_rate(t, growth_rate: float, loading: float, stop_time: float, residence_time: float):
    t = np.asarray(t, dtype=float)
    if growth_rate < 0 or loading < 0 or stop_time < 0 or residence_time <= 0:
        raise ValueError("invalid residence-time parameters")
    before = loading * growth_rate * (1 - np.exp(-t / residence_time))
    after = loading * growth_rate * (1 - np.exp(-stop_time / residence_time)) * np.exp(-(t - stop_time) / residence_time)
    return np.where(t <= stop_time, before, after)


def total_consumed_mass(times, consumption_rate) -> float:
    return float(trapezoid(np.asarray(consumption_rate, dtype=float), np.asarray(times, dtype=float)))
