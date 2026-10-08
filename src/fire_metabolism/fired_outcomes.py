"""Early-sequence prediction and grown-fire descriptors for FIRED events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from .fired_prediction import NATURAL_VEGETATION_CLASSES


BASE_FEATURE_COLUMNS = (
    "log_snapshot_area",
    "log_day1_area",
    "log_mean_daily_growth",
    "log_recent_growth",
    "growth_day_fraction",
    "recent_area_fraction",
    "log_peak_growth",
    "log_cumulative_slope",
)


def _landcover_column(name: str) -> str:
    return "lc_" + "_".join(name.lower().replace("-", " ").split())


LANDCOVER_FEATURE_COLUMNS = tuple(
    _landcover_column(name) for name in NATURAL_VEGETATION_CLASSES
)
EARLY_FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + LANDCOVER_FEATURE_COLUMNS


def _threshold_day(days: np.ndarray, cumulative: np.ndarray, threshold: float) -> int:
    index = int(np.searchsorted(cumulative, threshold, side="left"))
    return int(days[min(index, len(days) - 1)])


def describe_fire_outcomes(
    sequences: pd.DataFrame, *, snapshot_days: Sequence[int] = (3, 5, 7)
) -> pd.DataFrame:
    """Reduce each complete daily sequence to interpretable grown-fire statistics."""
    required = {
        "id",
        "ig_year",
        "lc_name",
        "event_day",
        "daily_area_km2",
        "cumulative_area_km2",
    }
    missing = required.difference(sequences.columns)
    if missing:
        raise ValueError(f"missing sequence columns: {sorted(missing)}")
    snapshots = tuple(sorted({int(day) for day in snapshot_days}))
    if not snapshots or snapshots[0] < 1:
        raise ValueError("snapshot days must be positive")

    rows: list[dict[str, object]] = []
    for event_id, event in sequences.groupby("id", sort=False):
        event = event.sort_values("event_day")
        days = event["event_day"].to_numpy(dtype=int)
        daily = event["daily_area_km2"].to_numpy(dtype=float)
        cumulative = event["cumulative_area_km2"].to_numpy(dtype=float)
        if len(event) < 2 or cumulative[-1] <= 0 or np.any(np.diff(cumulative) < -1e-12):
            continue
        duration = int(days[-1])
        final_area = float(cumulative[-1])
        active = daily > 0
        active_values = daily[active]
        peak_index = int(np.argmax(daily))
        half_day = _threshold_day(days, cumulative, 0.5 * final_area)
        ninety_day = _threshold_day(days, cumulative, 0.9 * final_area)
        mean_active = float(active_values.mean()) if active_values.size else 0.0
        row: dict[str, object] = {
            "id": int(event_id),
            "ig_year": int(event["ig_year"].iloc[0]),
            "lc_name": str(event["lc_name"].iloc[0]),
            "final_area_km2": final_area,
            "duration_days": duration,
            "active_growth_days": int(active.sum()),
            "active_growth_fraction": float(active.mean()),
            "peak_daily_growth_km2": float(daily[peak_index]),
            "peak_growth_day": int(days[peak_index]),
            "peak_growth_timing": float(days[peak_index] / duration),
            "half_area_day": half_day,
            "half_area_timing": float(half_day / duration),
            "ninety_area_day": ninety_day,
            "ninety_area_timing": float(ninety_day / duration),
            "area_weighted_growth_timing": float(np.sum(days * daily) / (duration * final_area)),
            "mean_active_daily_growth_km2": mean_active,
            "growth_burstiness": float(daily[peak_index] / mean_active) if mean_active > 0 else np.nan,
        }
        for snapshot in snapshots:
            column = f"area_fraction_day_{snapshot}"
            row[column] = (
                float(cumulative[snapshot - 1] / final_area)
                if snapshot <= len(cumulative)
                else np.nan
            )
        rows.append(row)
    if not rows:
        raise ValueError("no valid event outcomes could be described")
    return pd.DataFrame(rows)


def make_early_features(sequences: pd.DataFrame, snapshot_day: int) -> pd.DataFrame:
    """Construct predictors using observations through ``snapshot_day`` only."""
    if snapshot_day < 2:
        raise ValueError("snapshot_day must be at least two")
    outcomes = describe_fire_outcomes(sequences, snapshot_days=(snapshot_day,))
    rows: list[dict[str, object]] = []
    for event_id, event in sequences.groupby("id", sort=False):
        event = event.sort_values("event_day")
        history = event[event["event_day"] <= snapshot_day]
        if len(history) != snapshot_day or int(event["event_day"].max()) <= snapshot_day:
            continue
        daily = history["daily_area_km2"].to_numpy(dtype=float)
        cumulative = history["cumulative_area_km2"].to_numpy(dtype=float)
        if np.any(cumulative <= 0):
            continue
        recent = daily[-min(3, snapshot_day) :]
        slope = float(np.polyfit(np.arange(snapshot_day, dtype=float), np.log(cumulative), 1)[0])
        row: dict[str, object] = {
            "id": int(event_id),
            "ig_year": int(event["ig_year"].iloc[0]),
            "lc_name": str(event["lc_name"].iloc[0]),
            "snapshot_day": int(snapshot_day),
            "snapshot_area_km2": float(cumulative[-1]),
            "log_snapshot_area": float(np.log(cumulative[-1])),
            "log_day1_area": float(np.log(cumulative[0])),
            "log_mean_daily_growth": float(np.log1p(daily.mean())),
            "log_recent_growth": float(np.log1p(recent.sum())),
            "growth_day_fraction": float(np.mean(daily > 0)),
            "recent_area_fraction": float(recent.sum() / cumulative[-1]),
            "log_peak_growth": float(np.log1p(daily.max())),
            "log_cumulative_slope": slope,
        }
        for name, column in zip(
            NATURAL_VEGETATION_CLASSES, LANDCOVER_FEATURE_COLUMNS, strict=True
        ):
            row[column] = float(row["lc_name"] == name)
        rows.append(row)
    features = pd.DataFrame(rows)
    if features.empty:
        raise ValueError("no events extend beyond the requested snapshot day")
    return features.merge(
        outcomes[["id", "final_area_km2", "duration_days"]], on="id", how="left", validate="one_to_one"
    )


@dataclass(frozen=True)
class StandardizedRidge:
    """Small dependency-free ridge regression fitted on standardized columns."""

    feature_columns: tuple[str, ...]
    mean: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        values = frame.loc[:, self.feature_columns].to_numpy(dtype=float)
        standardized = (values - self.mean) / self.scale
        design = np.column_stack([np.ones(len(frame)), standardized])
        return design @ self.coefficients


def fit_standardized_ridge(
    frame: pd.DataFrame,
    target: Sequence[float] | np.ndarray,
    *,
    feature_columns: Sequence[str] = EARLY_FEATURE_COLUMNS,
    alpha: float = 1.0,
) -> StandardizedRidge:
    """Fit ridge regression with an unpenalized intercept."""
    columns = tuple(feature_columns)
    if not columns or alpha < 0:
        raise ValueError("feature columns cannot be empty and alpha must be nonnegative")
    missing = set(columns).difference(frame.columns)
    if missing:
        raise ValueError(f"missing feature columns: {sorted(missing)}")
    values = frame.loc[:, columns].to_numpy(dtype=float)
    response = np.asarray(target, dtype=float)
    if values.ndim != 2 or len(values) != len(response) or len(values) < 2:
        raise ValueError("features and target must contain matching observations")
    if not np.isfinite(values).all() or not np.isfinite(response).all():
        raise ValueError("features and target must be finite")
    mean = values.mean(axis=0)
    scale = values.std(axis=0)
    scale[scale < 1e-12] = 1.0
    design = np.column_stack([np.ones(len(values)), (values - mean) / scale])
    penalty = np.eye(design.shape[1]) * float(alpha)
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ response)
    return StandardizedRidge(columns, mean, scale, coefficients)
