"""Conditional growth laws, bounds, acceleration, and termination examples."""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq


def analytic_area(t, area0: float, sigma: float, integrated_beta):
    """Solve dA/dt = beta(t) A^sigma from an supplied beta integral."""
    if area0 <= 0:
        raise ValueError("area0 must be positive")
    integral = np.asarray(integrated_beta, dtype=float)
    if np.isclose(sigma, 1.0):
        return area0 * np.exp(integral)
    base = area0 ** (1 - sigma) + (1 - sigma) * integral
    if np.any(base <= 0):
        raise ValueError("solution leaves its real positive domain")
    return base ** (1 / (1 - sigma))


def constant_beta_area(t, area0: float, beta: float, sigma: float, t0: float = 0.0):
    delta = np.asarray(t, dtype=float) - t0
    return analytic_area(t, area0, sigma, beta * delta)


def variable_beta_area(t, area0: float, sigma: float, beta: Callable[[float], float], t0: float = 0.0):
    values = np.atleast_1d(np.asarray(t, dtype=float))
    integrals = np.array([quad(beta, t0, value)[0] for value in values])
    result = analytic_area(values, area0, sigma, integrals)
    return float(result[0]) if np.ndim(t) == 0 else result


def normalized_area(theta, sigma: float):
    theta = np.asarray(theta, dtype=float)
    if np.isclose(sigma, 1.0):
        return np.exp(theta)
    base = 1 + (1 - sigma) * theta
    if np.any(base <= 0):
        raise ValueError("normalized trajectory leaves its positive domain")
    return base ** (1 / (1 - sigma))


def area_acceleration(area, beta, beta_dot, sigma):
    area = np.asarray(area, dtype=float)
    return beta_dot * area**sigma + sigma * beta**2 * area ** (2 * sigma - 1)


def two_thirds_accelerates(area: float, beta: float, beta_dot: float) -> bool:
    return beta_dot > -(2 / 3) * beta**2 * area ** (-1 / 3)


def logarithmic_growth_rate(beta: float, beta_dot: float, area: float, area_dot: float, sigma: float) -> float:
    if beta <= 0 or area <= 0 or area_dot <= 0:
        raise ValueError("beta, area, and area_dot must be positive")
    return beta_dot / beta + sigma * area_dot / area


def finite_speed_bound(t, radius0: float, max_speed: float, t0: float = 0.0):
    delta = np.asarray(t, dtype=float) - t0
    if radius0 < 0 or max_speed < 0 or np.any(delta < 0):
        raise ValueError("radius, speed, and elapsed time must be nonnegative")
    return np.pi * (radius0 + max_speed * delta) ** 2


def finite_speed_crossing(area0: float, beta: float, radius0: float, max_speed: float, horizon: float = 1e6) -> float:
    """First positive crossing of constant-beta sigma=2/3 area and reachability bound."""
    difference = lambda t: float(constant_beta_area(t, area0, beta, 2 / 3) - finite_speed_bound(t, radius0, max_speed))
    grid = np.geomspace(1e-9, horizon, 2000)
    previous_t, previous_value = 0.0, difference(0.0)
    for current_t in grid:
        current_value = difference(current_t)
        if previous_value == 0 and previous_t > 0:
            return previous_t
        if current_value * previous_value < 0:
            return float(brentq(difference, previous_t, current_t))
        previous_t, previous_value = current_t, current_value
    raise ValueError("no positive crossing found inside horizon")


def cube_root_rate(area: float, beta: float, source_rate: float) -> float:
    if area <= 0:
        raise ValueError("area must be positive")
    return (beta + source_rate / area ** (2 / 3)) / 3


def apply_area_jumps(times, continuous_area, jump_times, jump_sizes):
    times = np.asarray(times, dtype=float)
    result = np.asarray(continuous_area, dtype=float).copy()
    if len(jump_times) != len(jump_sizes):
        raise ValueError("jump times and sizes must match")
    for jump_time, jump_size in zip(jump_times, jump_sizes, strict=True):
        if jump_size < 0:
            raise ValueError("cumulative burned-area jumps must be nonnegative")
        result[times >= jump_time] += jump_size
    return result


def late_stage_fraction(exponent: float, fraction_of_duration: float) -> float:
    if exponent <= 0 or not 0 <= fraction_of_duration <= 1:
        raise ValueError("exponent must be positive and duration fraction in [0, 1]")
    return 1 - (1 - fraction_of_duration) ** exponent


def exponential_lifetime_exceedance(area_threshold: float, coefficient: float, exponent: float, rate: float) -> float:
    if area_threshold < 0 or coefficient <= 0 or exponent <= 0 or rate <= 0:
        raise ValueError("invalid termination-model parameters")
    return math.exp(-rate * (area_threshold / coefficient) ** (1 / exponent))


def rate_change_ratio(start_area: float, beta: float, factor: float, horizon: float) -> float:
    if start_area <= 0 or beta < 0 or factor < 0 or horizon < 0:
        raise ValueError("invalid rate-change parameters")
    numerator = start_area ** (1 / 3) + factor * beta * horizon / 3
    denominator = start_area ** (1 / 3) + beta * horizon / 3
    return (numerator / denominator) ** 3


def beta_for_target(start_area: float, target_area: float, horizon: float) -> float:
    if start_area <= 0 or target_area < start_area or horizon <= 0:
        raise ValueError("target must be reachable cumulative area and horizon positive")
    return 3 * (target_area ** (1 / 3) - start_area ** (1 / 3)) / horizon
