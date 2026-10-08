"""Scaling relations, diagnostics, and deliberately negative examples."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import box_count


def loglog_slope(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 2 or x.shape != y.shape or np.any(x <= 0) or np.any(y <= 0):
        raise ValueError("x and y must be matching positive arrays with at least two values")
    return float(np.polyfit(np.log(x), np.log(y), 1)[0])


def boundary_bridge(area_dimension: float, boundary_dimension: float) -> float:
    """Conditional bridge sigma = D_h / D_A; not a dimension measurement."""
    if area_dimension <= 0 or boundary_dimension < 0:
        raise ValueError("area_dimension must be positive and boundary_dimension nonnegative")
    return boundary_dimension / area_dimension


def smooth_perimeter(area: np.ndarray | float, coefficient: float = 2 * np.sqrt(np.pi)):
    if coefficient <= 0 or np.any(np.asarray(area) < 0):
        raise ValueError("area must be nonnegative and coefficient positive")
    return coefficient * np.sqrt(area)


def excess_perimeter(perimeter, area, smooth_coefficient: float = 2 * np.sqrt(np.pi)):
    return np.asarray(perimeter, dtype=float) / smooth_perimeter(area, smooth_coefficient)


def excess_ratio_change(area_ratio: float, sigma: float) -> float:
    if area_ratio <= 0:
        raise ValueError("area_ratio must be positive")
    return float(area_ratio ** (sigma - 0.5))


def dimensional_k_length_power(sigma: float) -> float:
    """Return length exponent in [k] = length^(1 - 2 sigma)."""
    return 1 - 2 * sigma


def normalized_perimeter(area_ratio, kappa, sigma):
    return np.asarray(kappa) * np.asarray(area_ratio) ** np.asarray(sigma)


def local_slope_decomposition(sigma, dlogkappa_dloga, loga, dsigma_dloga):
    return sigma + dlogkappa_dloga + loga * dsigma_dloga


@dataclass(frozen=True)
class BoxCountingResult:
    experiment: str
    slope: float
    predictor: np.ndarray
    response: np.ndarray
    metadata: dict[str, object]


def box_count_resolution_experiment(points: np.ndarray, epsilons: np.ndarray) -> BoxCountingResult:
    """Vary ruler resolution on one fixed object."""
    eps = np.asarray(epsilons, dtype=float)
    counts = np.array([box_count(points, value) for value in eps], dtype=float)
    slope = loglog_slope(1 / eps, counts)
    return BoxCountingResult("fixed_object_vary_resolution", slope, 1 / eps, counts, {"n_points": len(points)})


def between_size_experiment(areas: np.ndarray, perimeters: np.ndarray, resolution: float) -> BoxCountingResult:
    """Compare differently sized objects at one stated resolution."""
    slope = loglog_slope(areas, perimeters)
    return BoxCountingResult("different_objects_fixed_resolution", slope, np.asarray(areas), np.asarray(perimeters), {"resolution": resolution})


def trajectory_experiment(times: np.ndarray, areas: np.ndarray, perimeters: np.ndarray) -> BoxCountingResult:
    """Measure one changing object through time."""
    slope = loglog_slope(areas, perimeters)
    return BoxCountingResult("one_object_through_time", slope, np.asarray(areas), np.asarray(perimeters), {"times": np.asarray(times)})


def apparent_two_thirds_from_changing_intercept(area_ratio):
    """Counterexample: model sigma=1/2 and kappa proportional to a^(1/6)."""
    a = np.asarray(area_ratio, dtype=float)
    return a ** (1 / 6) * a**0.5


PERCOLATION_REFERENCES = {
    "full_critical_hull": 7 / 4,
    "accessible_external_perimeter": 4 / 3,
}


def compare_perimeter_hypotheses(measured: float, convention: str) -> dict[str, float | str]:
    if not convention.strip():
        raise ValueError("perimeter convention is required")
    return {"measured": measured, "convention": convention, **{k: measured - v for k, v in PERCOLATION_REFERENCES.items()}}


def matching_efficiency(r):
    r = np.asarray(r, dtype=float)
    if np.any(r <= 0):
        raise ValueError("r must be positive")
    return 4 * r / (1 + r) ** 2


def matching_ratio(boundary_dimension, preferred_dimension, sensitivity=1.0):
    return np.exp(sensitivity * (np.asarray(boundary_dimension) - preferred_dimension))


def series_flux(delta_x: float, resistance_1: float, resistance_2: float) -> float:
    if resistance_1 <= 0 or resistance_2 <= 0:
        raise ValueError("resistances must be positive")
    return delta_x / (resistance_1 + resistance_2)


def fit_within_event(records: list[dict[str, float | str]]) -> dict[str, float]:
    """Fit one event only; callers must choose an event and perimeter convention."""
    event_ids = {str(record["event_id"]) for record in records}
    conventions = {str(record["perimeter_convention"]) for record in records}
    if len(event_ids) != 1 or len(conventions) != 1:
        raise ValueError("within-event fitting requires one event and one perimeter convention")
    area = np.array([float(record["area"]) for record in records])
    perimeter = np.array([float(record["perimeter"]) for record in records])
    slope, intercept = np.polyfit(np.log(area), np.log(perimeter), 1)
    return {"sigma": float(slope), "log_intercept": float(intercept), "n": float(len(records))}


def fit_between_events(records: list[dict[str, float | str]]) -> dict[str, float]:
    """Fit final sizes across events without pooling within-event observations."""
    by_event: dict[str, dict[str, float | str]] = {}
    for record in records:
        event = str(record["event_id"])
        if event in by_event:
            raise ValueError("between-event input must contain one final record per event")
        by_event[event] = record
    if len(by_event) < 2:
        raise ValueError("between-event fitting requires at least two events")
    area = np.array([float(record["area"]) for record in by_event.values()])
    perimeter = np.array([float(record["perimeter"]) for record in by_event.values()])
    slope, intercept = np.polyfit(np.log(area), np.log(perimeter), 1)
    return {"sigma": float(slope), "log_intercept": float(intercept), "n": float(len(by_event))}


def compare_scaling_models(area, perimeter) -> list[dict[str, float | str]]:
    """Compare free, one-half, and two-thirds log-space models.

    This is a descriptive model comparison. It does not represent complete
    uncertainty because area and perimeter may have correlated measurement
    errors inherited from the same mapped geometry.
    """
    area = np.asarray(area, dtype=float)
    perimeter = np.asarray(perimeter, dtype=float)
    if area.shape != perimeter.shape or area.size < 3 or np.any(area <= 0) or np.any(perimeter <= 0):
        raise ValueError("area and perimeter must be matching positive arrays")
    x, y = np.log(area), np.log(perimeter)
    models: list[dict[str, float | str]] = []
    for name, fixed_sigma in (("sigma_free", None), ("sigma_one_half", 0.5), ("sigma_two_thirds", 2 / 3)):
        if fixed_sigma is None:
            sigma, intercept = np.polyfit(x, y, 1)
            parameters = 2
        else:
            sigma = fixed_sigma
            intercept = float(np.mean(y - sigma * x))
            parameters = 1
        residuals = y - (intercept + sigma * x)
        sse = float(np.sum(residuals**2))
        aic = float(area.size * np.log(max(sse / area.size, np.finfo(float).tiny)) + 2 * parameters)
        models.append({"model": name, "sigma": float(sigma), "log_intercept": float(intercept), "sse": sse, "aic": aic})
    return models


def rolling_scaling_slopes(area, perimeter, window: int) -> np.ndarray:
    """Estimate changing exponents over explicit contiguous windows."""
    area = np.asarray(area, dtype=float)
    perimeter = np.asarray(perimeter, dtype=float)
    if area.shape != perimeter.shape or window < 3 or window > area.size:
        raise ValueError("window must span at least three matching observations")
    return np.array([loglog_slope(area[start : start + window], perimeter[start : start + window]) for start in range(area.size - window + 1)])
