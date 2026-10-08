"""Leakage-resistant calibration, forecasting, and back-transform uncertainty."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ForecastDesign:
    calibration_start: float
    calibration_end: float
    forecast_origin: float
    horizon: float

    def __post_init__(self):
        if self.calibration_end <= self.calibration_start:
            raise ValueError("calibration interval must have positive duration")
        if self.forecast_origin < self.calibration_end:
            raise ValueError("forecast origin cannot precede calibration end")
        if self.horizon <= 0:
            raise ValueError("forecast horizon must be positive")


def calibrate_beta_two_thirds(area_start: float, area_end: float, time_start: float, time_end: float) -> float:
    if area_start <= 0 or area_end <= 0 or time_end <= time_start:
        raise ValueError("areas must be positive and calibration interval ordered")
    return 3 * (area_end ** (1 / 3) - area_start ** (1 / 3)) / (time_end - time_start)


def forecast_two_thirds(origin_area: float, beta_hat: float, horizon: float) -> float:
    if origin_area <= 0 or horizon < 0:
        raise ValueError("origin area must be positive and horizon nonnegative")
    transformed = origin_area ** (1 / 3) + beta_hat * horizon / 3
    if transformed <= 0:
        raise ValueError("forecast leaves positive-area domain")
    return transformed**3


def transformed_moments_to_mean_area(mean_x: float, variance_x: float, third_central_moment_x: float) -> float:
    return mean_x**3 + 3 * mean_x * variance_x + third_central_moment_x


def forecast_beta_sensitivity(origin_area: float, beta: float, horizon: float) -> float:
    return horizon * (origin_area ** (1 / 3) + beta * horizon / 3) ** 2


def monte_carlo_mean_area(samples_x) -> float:
    samples = np.asarray(samples_x, dtype=float)
    return float(np.mean(samples**3))
