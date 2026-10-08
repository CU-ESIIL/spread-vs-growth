"""Geometry-informed life-cycle features and predictors for FIRED sequences.

The functions in this module keep the empirical and mechanistic layers
separate. FIRED supplies daily burned area and cumulative polygon geometry.
The mechanistic features are diagnostics implied by perimeter-area scaling and
the two-thirds growth closure; they are predictors, not assumed truths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from .fired_outcomes import (
    BASE_FEATURE_COLUMNS,
    LANDCOVER_FEATURE_COLUMNS,
    fit_standardized_ridge,
)
from .fired_prediction import NATURAL_VEGETATION_CLASSES


GEOMETRY_FEATURE_COLUMNS = (
    "log_total_perimeter",
    "log_exterior_perimeter",
    "log_total_excess_perimeter",
    "log_exterior_excess_perimeter",
    "total_perimeter_area_slope",
    "exterior_perimeter_area_slope",
    "log_recent_beta_two_thirds",
    "log_recent_beta_one_half",
    "log_recent_boundary_speed",
    "recent_beta_trend",
    "recent_growth_acceleration",
    "latest_growth_fraction_of_peak",
    "days_since_observed_peak",
    "log_component_count",
    "log1p_hole_count",
    "recent_log_total_perimeter_change",
    "recent_log_exterior_perimeter_change",
    "recent_component_change",
    "recent_hole_change",
    "days_since_last_detected_growth",
    "recent_active_fraction",
    "smoothed_growth_curvature",
    "log_area_per_component",
)
AREA_FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + LANDCOVER_FEATURE_COLUMNS
LIFECYCLE_FEATURE_COLUMNS = (
    BASE_FEATURE_COLUMNS + GEOMETRY_FEATURE_COLUMNS + LANDCOVER_FEATURE_COLUMNS
)


def merge_geometry_sequences(
    sequences: pd.DataFrame, geometry: pd.DataFrame
) -> pd.DataFrame:
    """Join detection-day geometry and carry it through zero-growth gaps."""
    keys = {"id", "event_day"}
    geometry_columns = {
        "polygon_area_km2",
        "total_perimeter_km",
        "exterior_perimeter_km",
        "component_count",
        "hole_count",
    }
    if missing := keys.difference(sequences.columns):
        raise ValueError(f"missing sequence columns: {sorted(missing)}")
    if missing := (keys | geometry_columns).difference(geometry.columns):
        raise ValueError(f"missing geometry columns: {sorted(missing)}")
    merged = sequences.merge(
        geometry[list(keys | geometry_columns)],
        on=["id", "event_day"],
        how="left",
        validate="one_to_one",
    ).sort_values(["id", "event_day"])
    ordered_geometry = sorted(geometry_columns)
    merged[ordered_geometry] = merged.groupby("id", sort=False)[
        ordered_geometry
    ].ffill()
    if merged[ordered_geometry].isna().any().any():
        raise ValueError("geometry is missing at the start of at least one event")
    if (merged[["total_perimeter_km", "exterior_perimeter_km"]] <= 0).any().any():
        raise ValueError("perimeter measurements must be positive")
    return merged.reset_index(drop=True)


def smooth_daily_growth(values: Sequence[float], window: int = 3) -> np.ndarray:
    """Return a centered triangular smoother for daily detected growth."""
    daily = np.asarray(values, dtype=float)
    if daily.ndim != 1 or daily.size < 2 or np.any(daily < 0):
        raise ValueError("daily growth must be a nonnegative one-dimensional sequence")
    if window not in {1, 3, 5}:
        raise ValueError("smoothing window must be 1, 3, or 5 days")
    if window == 1:
        return daily.copy()
    weights = np.arange(1, window // 2 + 2, dtype=float)
    weights = np.r_[weights, weights[-2::-1]]
    weights /= weights.sum()
    return np.convolve(daily, weights, mode="same")


def describe_lifecycle_outcomes(
    sequences: pd.DataFrame, *, smoothing_window: int = 3
) -> pd.DataFrame:
    """Describe observed growth peak, death, and final size for each event.

    ``growth_peak_day`` is the day of maximum smoothed detected daily growth.
    It is used as a noise-tolerant proxy for the transition from positive to
    nonpositive growth acceleration. ``death_day`` is the last day with a
    positive FIRED area increment, not an incident-control declaration.
    """
    required = {
        "id",
        "ig_year",
        "lc_name",
        "event_day",
        "daily_area_km2",
        "cumulative_area_km2",
    }
    if missing := required.difference(sequences.columns):
        raise ValueError(f"missing sequence columns: {sorted(missing)}")
    rows = []
    for event_id, event in sequences.groupby("id", sort=False):
        event = event.sort_values("event_day")
        days = event["event_day"].to_numpy(dtype=int)
        daily = event["daily_area_km2"].to_numpy(dtype=float)
        cumulative = event["cumulative_area_km2"].to_numpy(dtype=float)
        if daily.size < 2 or cumulative[-1] <= 0:
            continue
        smoothed = smooth_daily_growth(daily, smoothing_window)
        peak_index = int(np.argmax(smoothed))
        active_days = days[daily > 0]
        death_day = int(active_days[-1]) if active_days.size else int(days[0])
        rows.append(
            {
                "id": int(event_id),
                "ig_year": int(event["ig_year"].iloc[0]),
                "lc_name": str(event["lc_name"].iloc[0]),
                "final_area_km2": float(cumulative[-1]),
                "event_duration_days": int(days[-1]),
                "death_day": death_day,
                "growth_peak_day": int(days[peak_index]),
                "growth_peak_after_day5": bool(days[peak_index] > 5),
                "smoothed_peak_growth_km2_per_day": float(smoothed[peak_index]),
                "active_growth_days": int(np.sum(daily > 0)),
            }
        )
    if not rows:
        raise ValueError("no life-cycle outcomes could be described")
    return pd.DataFrame(rows)


def _safe_log_slope(area: np.ndarray, perimeter: np.ndarray) -> float:
    keep = (area > 0) & (perimeter > 0)
    x = np.log(area[keep])
    y = np.log(perimeter[keep])
    if len(x) < 2 or np.ptp(x) < 1e-10:
        return 0.5
    return float(np.polyfit(x, y, 1)[0])


def _future_area(event: pd.DataFrame, target_day: int) -> float:
    observed = event[event["event_day"] <= target_day]
    if observed.empty:
        raise ValueError("target day precedes the event")
    return float(observed["cumulative_area_km2"].iloc[-1])


def make_lifecycle_features(
    sequences: pd.DataFrame,
    snapshot_day: int,
    *,
    horizons: Sequence[int] = (1, 3, 5, 7),
    smoothing_window: int = 3,
) -> pd.DataFrame:
    """Construct past-only area, geometry, and metabolic features."""
    if snapshot_day < 3:
        raise ValueError("snapshot_day must be at least three")
    horizons = tuple(sorted({int(value) for value in horizons}))
    if not horizons or horizons[0] < 1:
        raise ValueError("forecast horizons must be positive")
    outcomes = describe_lifecycle_outcomes(
        sequences, smoothing_window=smoothing_window
    ).set_index("id")
    required_geometry = {
        "total_perimeter_km",
        "exterior_perimeter_km",
        "component_count",
        "hole_count",
    }
    if missing := required_geometry.difference(sequences.columns):
        raise ValueError(f"missing geometry columns: {sorted(missing)}")

    rows = []
    for event_id, event in sequences.groupby("id", sort=False):
        event = event.sort_values("event_day")
        history = event[event["event_day"] <= snapshot_day]
        if len(history) != snapshot_day or int(event["event_day"].max()) <= snapshot_day:
            continue
        area = history["cumulative_area_km2"].to_numpy(dtype=float)
        daily = history["daily_area_km2"].to_numpy(dtype=float)
        total_perimeter = history["total_perimeter_km"].to_numpy(dtype=float)
        exterior_perimeter = history["exterior_perimeter_km"].to_numpy(dtype=float)
        if np.any(area <= 0) or np.any(total_perimeter <= 0):
            continue
        recent_size = min(3, snapshot_day)
        recent_daily = daily[-recent_size:]
        recent_area = area[-recent_size:]
        recent_total_growth = float(recent_daily.sum())
        beta_two_thirds = recent_daily / np.maximum(
            recent_area ** (2.0 / 3.0), 1e-12
        )
        beta_one_half = recent_daily / np.maximum(recent_area**0.5, 1e-12)
        smoothed = smooth_daily_growth(daily, smoothing_window)
        observed_peak = int(np.argmax(smoothed))
        previous = daily[-min(6, snapshot_day) : -recent_size]
        previous_total = float(previous.sum()) if previous.size else 0.0
        recent_beta_x = np.arange(beta_two_thirds.size, dtype=float)
        beta_trend = (
            float(np.polyfit(recent_beta_x, beta_two_thirds, 1)[0])
            if beta_two_thirds.size >= 2
            else 0.0
        )
        growth_acceleration = (
            float(smoothed[-1] - smoothed[-2]) if smoothed.size >= 2 else 0.0
        )
        growth_curvature = (
            float(smoothed[-1] - 2 * smoothed[-2] + smoothed[-3])
            if smoothed.size >= 3
            else 0.0
        )
        recent_start = max(0, snapshot_day - recent_size)
        component = history["component_count"].to_numpy(dtype=float)
        holes = history["hole_count"].to_numpy(dtype=float)
        active_indices = np.flatnonzero(daily > 0)
        days_since_last_growth = (
            float(snapshot_day - active_indices[-1] - 1)
            if active_indices.size
            else float(snapshot_day)
        )
        circle_perimeter = 2.0 * np.sqrt(np.pi * area[-1])
        recent = daily[-recent_size:]
        row: dict[str, object] = {
            "id": int(event_id),
            "ig_year": int(event["ig_year"].iloc[0]),
            "lc_name": str(event["lc_name"].iloc[0]),
            "snapshot_day": int(snapshot_day),
            "snapshot_area_km2": float(area[-1]),
            "log_snapshot_area": float(np.log(area[-1])),
            "log_day1_area": float(np.log(area[0])),
            "log_mean_daily_growth": float(np.log1p(daily.mean())),
            "log_recent_growth": float(np.log1p(recent_total_growth)),
            "growth_day_fraction": float(np.mean(daily > 0)),
            "recent_area_fraction": float(recent_total_growth / area[-1]),
            "log_peak_growth": float(np.log1p(daily.max())),
            "log_cumulative_slope": float(
                np.polyfit(np.arange(snapshot_day, dtype=float), np.log(area), 1)[0]
            ),
            "log_total_perimeter": float(np.log(total_perimeter[-1])),
            "log_exterior_perimeter": float(np.log(exterior_perimeter[-1])),
            "log_total_excess_perimeter": float(
                np.log(total_perimeter[-1] / circle_perimeter)
            ),
            "log_exterior_excess_perimeter": float(
                np.log(exterior_perimeter[-1] / circle_perimeter)
            ),
            "total_perimeter_area_slope": _safe_log_slope(area, total_perimeter),
            "exterior_perimeter_area_slope": _safe_log_slope(
                area, exterior_perimeter
            ),
            "log_recent_beta_two_thirds": float(
                np.log1p(recent_total_growth / np.maximum(area[-1] ** (2 / 3), 1e-12))
            ),
            "log_recent_beta_one_half": float(
                np.log1p(recent_total_growth / np.maximum(area[-1] ** 0.5, 1e-12))
            ),
            "log_recent_boundary_speed": float(
                np.log1p(recent_total_growth / np.maximum(total_perimeter[-1], 1e-12))
            ),
            "recent_beta_trend": beta_trend,
            "recent_growth_acceleration": growth_acceleration,
            "latest_growth_fraction_of_peak": float(
                smoothed[-1] / max(float(smoothed.max()), 1e-12)
            ),
            "days_since_observed_peak": float(snapshot_day - observed_peak - 1),
            "log_component_count": float(
                np.log(max(float(history["component_count"].iloc[-1]), 1.0))
            ),
            "log1p_hole_count": float(
                np.log1p(max(float(history["hole_count"].iloc[-1]), 0.0))
            ),
            "recent_log_total_perimeter_change": float(
                np.log(total_perimeter[-1])
                - np.log(total_perimeter[recent_start])
            ),
            "recent_log_exterior_perimeter_change": float(
                np.log(exterior_perimeter[-1])
                - np.log(exterior_perimeter[recent_start])
            ),
            "recent_component_change": float(
                component[-1] - component[recent_start]
            ),
            "recent_hole_change": float(holes[-1] - holes[recent_start]),
            "days_since_last_detected_growth": days_since_last_growth,
            "recent_active_fraction": float(np.mean(recent > 0)),
            "smoothed_growth_curvature": growth_curvature,
            "log_area_per_component": float(
                np.log(area[-1] / max(component[-1], 1.0))
            ),
            "recent_to_previous_growth_ratio": float(
                recent_total_growth / max(previous_total, 1e-12)
            ),
        }
        for name, column in zip(
            NATURAL_VEGETATION_CLASSES,
            LANDCOVER_FEATURE_COLUMNS,
            strict=True,
        ):
            row[column] = float(row["lc_name"] == name)
        outcome = outcomes.loc[int(event_id)]
        row.update(
            {
                "final_area_km2": float(outcome["final_area_km2"]),
                "death_day": int(outcome["death_day"]),
                "growth_peak_day": int(outcome["growth_peak_day"]),
                "growth_peak_after_day5": bool(
                    outcome["growth_peak_after_day5"]
                ),
            }
        )
        for horizon in horizons:
            row[f"area_horizon_{horizon}_km2"] = _future_area(
                event, snapshot_day + horizon
            )
        rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("no lifecycle features could be constructed")
    feature_values = frame.loc[:, LIFECYCLE_FEATURE_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(feature_values).all():
        raise ValueError("lifecycle features must be finite")
    return frame


@dataclass(frozen=True)
class StandardizedNeighborIndex:
    """Reusable nearest-neighbor index for nonlinear empirical analogs."""

    feature_columns: tuple[str, ...]
    mean: np.ndarray
    scale: np.ndarray
    training: np.ndarray

    def neighbor_indices(self, frame: pd.DataFrame, max_neighbors: int) -> np.ndarray:
        if max_neighbors < 1 or max_neighbors > len(self.training):
            raise ValueError("invalid neighbor count")
        values = frame.loc[:, self.feature_columns].to_numpy(dtype=float)
        standardized = (values - self.mean) / self.scale
        result = np.empty((len(values), max_neighbors), dtype=int)
        for index, query in enumerate(standardized):
            distance = np.sum((self.training - query) ** 2, axis=1)
            nearest = np.argpartition(distance, max_neighbors - 1)[:max_neighbors]
            result[index] = nearest[np.argsort(distance[nearest])]
        return result


def fit_neighbor_index(
    frame: pd.DataFrame, feature_columns: Sequence[str] = LIFECYCLE_FEATURE_COLUMNS
) -> StandardizedNeighborIndex:
    columns = tuple(feature_columns)
    values = frame.loc[:, columns].to_numpy(dtype=float)
    if values.ndim != 2 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("neighbor features must be a finite two-dimensional table")
    mean = values.mean(axis=0)
    scale = values.std(axis=0)
    scale[scale < 1e-12] = 1.0
    return StandardizedNeighborIndex(columns, mean, scale, (values - mean) / scale)


def neighbor_predict(
    training_target: Sequence[float], neighbor_indices: np.ndarray, neighbors: int
) -> np.ndarray:
    target = np.asarray(training_target, dtype=float)
    if neighbor_indices.ndim != 2 or not 1 <= neighbors <= neighbor_indices.shape[1]:
        raise ValueError("neighbor index shape or requested count is invalid")
    return np.median(target[neighbor_indices[:, :neighbors]], axis=1)


def tune_ridge_alpha(
    development: pd.DataFrame,
    calibration: pd.DataFrame,
    target: Sequence[float],
    calibration_target: Sequence[float],
    *,
    feature_columns: Sequence[str],
    candidates: Sequence[float] = (0.1, 1.0, 10.0, 100.0),
) -> tuple[float, pd.DataFrame]:
    """Select ridge strength by calibration mean absolute transformed error."""
    rows = []
    calibration_target = np.asarray(calibration_target, dtype=float)
    for alpha in candidates:
        model = fit_standardized_ridge(
            development,
            target,
            feature_columns=feature_columns,
            alpha=float(alpha),
        )
        prediction = model.predict(calibration)
        rows.append(
            {
                "hyperparameter": float(alpha),
                "calibration_mae": float(
                    np.mean(np.abs(prediction - calibration_target))
                ),
            }
        )
    curve = pd.DataFrame(rows)
    best = float(curve.loc[curve["calibration_mae"].idxmin(), "hyperparameter"])
    return best, curve


def tune_neighbor_count(
    training_target: Sequence[float],
    calibration_target: Sequence[float],
    calibration_neighbors: np.ndarray,
    *,
    candidates: Sequence[int] = (10, 25, 50, 100),
) -> tuple[int, pd.DataFrame]:
    """Select empirical-analog count on the calibration partition."""
    calibration_target = np.asarray(calibration_target, dtype=float)
    rows = []
    for neighbors in candidates:
        prediction = neighbor_predict(
            training_target, calibration_neighbors, int(neighbors)
        )
        rows.append(
            {
                "hyperparameter": int(neighbors),
                "calibration_mae": float(
                    np.mean(np.abs(prediction - calibration_target))
                ),
            }
        )
    curve = pd.DataFrame(rows)
    best = int(curve.loc[curve["calibration_mae"].idxmin(), "hyperparameter"])
    return best, curve
