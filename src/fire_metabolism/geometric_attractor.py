"""Local geometric-state and attractor validation utilities.

All state estimates use only observations at or before their labeled event
day. Functions keep event identifiers so uncertainty can resample whole fires.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.stats import theilslopes


DEFAULT_SEED = 20261008
TWO_THIRDS = 2.0 / 3.0


@dataclass(frozen=True)
class LinearAttractor:
    """Discrete restoring model ``delta = intercept + slope * sigma``."""

    intercept: float
    slope: float

    @property
    def restoring_strength(self) -> float:
        return -self.slope

    @property
    def equilibrium(self) -> float:
        return float(-self.intercept / self.slope) if self.slope != 0 else np.nan


def _slope(x: np.ndarray, y: np.ndarray, method: str) -> tuple[float, float]:
    if len(x) < 2 or np.ptp(x) < 1e-10:
        return np.nan, np.nan
    if method == "theil_sen":
        estimate = float(theilslopes(y, x)[0])
        residual = y - (np.median(y - estimate * x) + estimate * x)
    else:
        design = np.column_stack([np.ones(len(x)), x])
        coefficient, *_ = np.linalg.lstsq(design, y, rcond=None)
        estimate = float(coefficient[1])
        residual = y - design @ coefficient
    centered = x - x.mean()
    denominator = float(np.dot(centered, centered))
    if len(x) <= 2 or denominator <= 0:
        standard_error = np.nan
    else:
        variance = float(np.dot(residual, residual) / (len(x) - 2))
        standard_error = float(np.sqrt(variance / denominator))
    return estimate, standard_error


def estimate_local_slopes(
    sequences: pd.DataFrame,
    *,
    perimeter_column: str = "exterior_perimeter_km",
    estimator: str = "rolling_ols_5",
    stride: int = 1,
) -> pd.DataFrame:
    """Estimate local log-perimeter/log-area slopes without future leakage."""
    required = {
        "id", "ig_year", "event_day", "daily_area_km2",
        "cumulative_area_km2", perimeter_column,
    }
    if missing := required.difference(sequences.columns):
        raise ValueError(f"missing local-slope columns: {sorted(missing)}")
    if stride < 1:
        raise ValueError("stride must be positive")
    if estimator == "adjacent":
        window, method = 2, "ols"
    elif estimator.startswith("rolling_ols_"):
        window, method = int(estimator.rsplit("_", 1)[1]), "ols"
    elif estimator.startswith("rolling_theil_sen_"):
        window, method = int(estimator.rsplit("_", 1)[1]), "theil_sen"
    else:
        raise ValueError(f"unknown estimator: {estimator}")
    if window < 2:
        raise ValueError("local slope window must contain at least two observations")

    rows: list[dict[str, object]] = []
    optional = ["component_count", "hole_count", "total_perimeter_km", "lc_name"]
    for event_id, event in sequences.groupby("id", sort=False):
        event = event.sort_values("event_day")
        observed = event[event.daily_area_km2 > 0].iloc[::stride]
        if len(observed) < window:
            continue
        for stop in range(window, len(observed) + 1):
            sample = observed.iloc[stop - window : stop]
            x = np.log(sample.cumulative_area_km2.to_numpy(dtype=float))
            y = np.log(sample[perimeter_column].to_numpy(dtype=float))
            sigma, sigma_se = _slope(x, y, method)
            current = sample.iloc[-1]
            if not np.isfinite(sigma):
                continue
            row: dict[str, object] = {
                "id": int(event_id),
                "ig_year": int(current.ig_year),
                "event_day": int(current.event_day),
                "estimator": estimator,
                "perimeter_definition": perimeter_column.replace("_perimeter_km", ""),
                "observation_stride": int(stride),
                "window_observations": int(window),
                "sigma": sigma,
                "sigma_se": sigma_se,
                "deviation_two_thirds": sigma - TWO_THIRDS,
                "area_km2": float(current.cumulative_area_km2),
                "perimeter_km": float(current[perimeter_column]),
                "daily_growth_km2": float(current.daily_area_km2),
            }
            for column in optional:
                if column in current.index:
                    row[column] = current[column]
            rows.append(row)
    return pd.DataFrame(rows)


def make_transitions(
    local: pd.DataFrame,
    *,
    leads: Iterable[int] = (1, 3, 5, 7, 10, 14, 21, 28, 35, 42, 49),
) -> pd.DataFrame:
    """Pair each local state with the first state at or after each target lead."""
    leads = tuple(sorted({int(value) for value in leads if int(value) > 0}))
    rows: list[dict[str, object]] = []
    for event_id, event in local.groupby("id", sort=False):
        event = event.sort_values("event_day").reset_index(drop=True)
        days = event.event_day.to_numpy(dtype=int)
        for origin_index, origin in event.iterrows():
            for lead in leads:
                future_index = int(np.searchsorted(days, int(origin.event_day) + lead))
                if future_index >= len(event):
                    continue
                future = event.iloc[future_index]
                actual_lead = int(future.event_day - origin.event_day)
                if actual_lead > lead + 2:
                    continue
                rows.append({
                    "id": int(event_id),
                    "ig_year": int(origin.ig_year),
                    "origin_day": int(origin.event_day),
                    "lead_days": int(lead),
                    "actual_lead_days": actual_lead,
                    "sigma": float(origin.sigma),
                    "future_sigma": float(future.sigma),
                    "delta_sigma": float(future.sigma - origin.sigma),
                    "deviation_two_thirds": float(origin.sigma - TWO_THIRDS),
                    "moved_toward_two_thirds": bool(
                        abs(future.sigma - TWO_THIRDS) < abs(origin.sigma - TWO_THIRDS)
                    ),
                    "crossed_two_thirds": bool(
                        (origin.sigma - TWO_THIRDS) * (future.sigma - TWO_THIRDS) < 0
                    ),
                    "area_km2": float(origin.area_km2),
                    "daily_growth_km2": float(origin.daily_growth_km2),
                    "sigma_se": float(origin.sigma_se),
                    "future_event_day": int(future.event_day),
                })
    return pd.DataFrame(rows)


def fit_free_attractor(frame: pd.DataFrame) -> LinearAttractor:
    """Fit an unconstrained linear equilibrium model."""
    x = frame.sigma.to_numpy(dtype=float)
    y = frame.delta_sigma.to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(x)), x])
    coefficient, *_ = np.linalg.lstsq(design, y, rcond=None)
    return LinearAttractor(float(coefficient[0]), float(coefficient[1]))


def fit_fixed_attractor(frame: pd.DataFrame, center: float) -> LinearAttractor:
    """Fit restoring strength while constraining the equilibrium to center."""
    x = frame.sigma.to_numpy(dtype=float) - float(center)
    y = frame.delta_sigma.to_numpy(dtype=float)
    denominator = float(np.dot(x, x))
    slope = float(np.dot(x, y) / denominator) if denominator > 0 else 0.0
    return LinearAttractor(intercept=-slope * float(center), slope=slope)


def predict_future_sigma(model: LinearAttractor, sigma: Sequence[float]) -> np.ndarray:
    values = np.asarray(sigma, dtype=float)
    return values + model.intercept + model.slope * values


def event_bootstrap_attractor(
    frame: pd.DataFrame,
    *,
    replicates: int = 2000,
    seed: int = DEFAULT_SEED,
) -> dict[str, float]:
    """Bootstrap free-attractor coefficients using whole events."""
    statistics = []
    for _, group in frame.groupby("id", sort=False):
        x = group.sigma.to_numpy(dtype=float)
        y = group.delta_sigma.to_numpy(dtype=float)
        statistics.append((len(x), x.sum(), y.sum(), np.dot(x, x), np.dot(x, y)))
    stats = np.asarray(statistics, dtype=float)
    generator = np.random.default_rng(seed)
    slopes, equilibria = [], []
    for _ in range(replicates):
        totals = stats[generator.integers(0, len(stats), size=len(stats))].sum(axis=0)
        n, sx, sy, sxx, sxy = totals
        denominator = sxx - sx * sx / n
        slope = (sxy - sx * sy / n) / denominator if denominator > 0 else np.nan
        intercept = (sy - slope * sx) / n
        slopes.append(slope)
        equilibria.append(-intercept / slope if slope != 0 else np.nan)
    model = fit_free_attractor(frame)
    return {
        "intercept": model.intercept,
        "slope": model.slope,
        "restoring_strength": model.restoring_strength,
        "equilibrium": model.equilibrium,
        "slope_ci95_lower": float(np.nanquantile(slopes, 0.025)),
        "slope_ci95_upper": float(np.nanquantile(slopes, 0.975)),
        "equilibrium_ci95_lower": float(np.nanquantile(equilibria, 0.025)),
        "equilibrium_ci95_upper": float(np.nanquantile(equilibria, 0.975)),
    }


def within_fire_restoration(frame: pd.DataFrame) -> LinearAttractor:
    """Estimate restoration from deviations around each fire's own mean state."""
    data = frame.copy()
    fire_mean = data.groupby("id").sigma.transform("mean")
    x = data.sigma.to_numpy(dtype=float) - fire_mean.to_numpy(dtype=float)
    y = data.delta_sigma.to_numpy(dtype=float)
    denominator = float(np.dot(x, x))
    slope = float(np.dot(x, y) / denominator) if denominator > 0 else np.nan
    return LinearAttractor(0.0, slope)


def half_life_days(restoring_strength: float, lead_days: float) -> float:
    """Return discrete half-life when 0 < lambda < 1."""
    if not 0 < restoring_strength < 1:
        return np.nan
    return float(np.log(0.5) / np.log(1.0 - restoring_strength) * lead_days)
