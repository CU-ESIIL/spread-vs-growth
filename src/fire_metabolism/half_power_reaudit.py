"""Utilities for auditing fixed-exponent perimeter-area comparisons.

The central distinction is between a population normalization learned before
evaluation, a fire-conditioned normalization, and a prediction-origin anchor.
All functions operate in log coordinates and retain event identifiers so that
uncertainty can be computed by resampling whole fires.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd


DEFAULT_SEED = 20261009


def fit_fixed_intercept(frame: pd.DataFrame, exponent: float) -> float:
    """Fit ``log(P) = alpha + exponent * log(A)`` with fixed exponent."""
    return float((frame.log_perimeter - float(exponent) * frame.log_area).mean())


def make_geometry_transitions(
    panel: pd.DataFrame,
    *,
    leads: Iterable[int] = (1, 3, 5, 7, 14, 21, 28),
    tolerance_days: int = 2,
) -> pd.DataFrame:
    """Pair each geometry state with the first state at or after each lead."""
    leads = tuple(sorted({int(value) for value in leads if int(value) > 0}))
    rows: list[dict[str, object]] = []
    for event_id, event in panel.groupby("id", sort=False):
        event = event.sort_values("event_day").reset_index(drop=True)
        days = event.event_day.to_numpy(dtype=int)
        for origin_index, origin in event.iloc[:-1].iterrows():
            for lead in leads:
                future_index = int(np.searchsorted(days, int(origin.event_day) + lead))
                if future_index >= len(event):
                    continue
                future = event.iloc[future_index]
                actual_lead = int(future.event_day - origin.event_day)
                if actual_lead > lead + tolerance_days:
                    continue
                rows.append(
                    {
                        "id": int(event_id),
                        "ig_year": int(origin.ig_year),
                        "partition": str(origin.partition),
                        "origin_day": int(origin.event_day),
                        "future_day": int(future.event_day),
                        "lead_days": int(lead),
                        "actual_lead_days": actual_lead,
                        "origin_log_area": float(origin.log_area),
                        "origin_log_perimeter": float(origin.log_perimeter),
                        "future_log_area": float(future.log_area),
                        "future_log_perimeter": float(future.log_perimeter),
                        "origin_area_km2": float(origin.cumulative_area_km2),
                        "future_area_km2": float(future.cumulative_area_km2),
                    }
                )
    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError("no geometry transitions could be constructed")
    result["area_ratio"] = result.future_area_km2 / result.origin_area_km2
    result["log_area_ratio"] = np.log(result.area_ratio)
    result["half_vs_two_thirds_ratio"] = result.area_ratio ** (1.0 / 6.0)
    return result


def add_history_intercepts(
    transitions: pd.DataFrame,
    panel: pd.DataFrame,
    exponents: Mapping[str, float],
) -> pd.DataFrame:
    """Add fire-specific intercepts estimated only through each origin."""
    history = panel.sort_values(["id", "event_day"]).copy()
    keys = ["id", "event_day"]
    columns = keys.copy()
    for name, exponent in exponents.items():
        residual = history.log_perimeter - float(exponent) * history.log_area
        history[f"history_alpha_{name}"] = residual.groupby(history.id).expanding().mean().reset_index(level=0, drop=True)
        history[f"full_fire_alpha_{name}"] = residual.groupby(history.id).transform("mean")
        columns.extend([f"history_alpha_{name}", f"full_fire_alpha_{name}"])
    return transitions.merge(
        history[columns],
        left_on=["id", "origin_day"],
        right_on=keys,
        how="left",
        validate="many_to_one",
    ).drop(columns="event_day")


def score_intercept_treatments(
    transitions: pd.DataFrame,
    exponents: Mapping[str, float],
    development_intercepts: Mapping[str, float],
    calibration_intercepts: Mapping[str, float],
) -> pd.DataFrame:
    """Score fixed exponents under four explicit normalization treatments."""
    rows: list[pd.DataFrame] = []
    for name, exponent in exponents.items():
        predictions = {
            "population_locked": float(development_intercepts[name]) + exponent * transitions.future_log_area,
            "calibration_locked": float(calibration_intercepts[name]) + exponent * transitions.future_log_area,
            "fire_specific_full": transitions[f"full_fire_alpha_{name}"] + exponent * transitions.future_log_area,
            "fire_specific_history": transitions[f"history_alpha_{name}"] + exponent * transitions.future_log_area,
            "origin_anchored": transitions.origin_log_perimeter + exponent * (
                transitions.future_log_area - transitions.origin_log_area
            ),
        }
        for treatment, prediction in predictions.items():
            part = transitions[
                [
                    "id", "ig_year", "partition", "origin_day", "future_day",
                    "lead_days", "actual_lead_days", "origin_log_area",
                    "future_log_area", "origin_log_perimeter",
                    "future_log_perimeter", "area_ratio", "log_area_ratio",
                    "half_vs_two_thirds_ratio",
                ]
            ].copy()
            part["candidate"] = name
            part["exponent"] = float(exponent)
            part["intercept_treatment"] = treatment
            part["predicted_log_perimeter"] = np.asarray(prediction, dtype=float)
            part["error"] = part.predicted_log_perimeter - part.future_log_perimeter
            part["absolute_error"] = np.abs(part.error)
            part["squared_error"] = part.error**2
            rows.append(part)
    return pd.concat(rows, ignore_index=True)


def summarize_scores(scores: pd.DataFrame, *, include_horizons: bool = True) -> pd.DataFrame:
    """Summarize absolute and squared log error on a common score table."""
    groups = ["intercept_treatment", "candidate", "exponent"]
    frames = []
    overall = (
        scores.groupby(groups, as_index=False)
        .agg(n=("id", "size"), n_fires=("id", "nunique"), mae_log=("absolute_error", "mean"), mse_log=("squared_error", "mean"))
    )
    overall["lead_days"] = "all"
    frames.append(overall)
    if include_horizons:
        by_horizon = (
            scores.groupby(groups + ["lead_days"], as_index=False)
            .agg(n=("id", "size"), n_fires=("id", "nunique"), mae_log=("absolute_error", "mean"), mse_log=("squared_error", "mean"))
        )
        frames.append(by_horizon)
    result = pd.concat(frames, ignore_index=True)
    result["rmse_log"] = np.sqrt(result.mse_log)
    return result.drop(columns="mse_log")


def event_bootstrap_difference(
    frame: pd.DataFrame,
    value_a: str,
    value_b: str,
    *,
    replicates: int = 1000,
    seed: int = DEFAULT_SEED,
) -> dict[str, float]:
    """Bootstrap a paired mean difference after averaging within each fire."""
    event = frame.groupby("id")[[value_a, value_b]].mean().dropna()
    difference = (event[value_a] - event[value_b]).to_numpy(dtype=float)
    if not len(difference):
        return {"difference": np.nan, "ci95_lower": np.nan, "ci95_upper": np.nan, "n_fires": 0}
    generator = np.random.default_rng(seed)
    draws = generator.choice(difference, size=(replicates, len(difference)), replace=True).mean(axis=1)
    return {
        "difference": float(difference.mean()),
        "ci95_lower": float(np.quantile(draws, 0.025)),
        "ci95_upper": float(np.quantile(draws, 0.975)),
        "n_fires": int(len(difference)),
    }


def fit_fixed_attractor_center(frame: pd.DataFrame, center: float) -> tuple[float, float]:
    """Fit one-step restoring dynamics constrained to a fixed center."""
    x = frame.sigma.to_numpy(dtype=float) - float(center)
    y = frame.future_sigma.to_numpy(dtype=float) - frame.sigma.to_numpy(dtype=float)
    denominator = float(np.dot(x, x))
    slope = float(np.dot(x, y) / denominator) if denominator > 0 else 0.0
    prediction = frame.sigma.to_numpy(dtype=float) + slope * x
    return slope, float(np.mean(np.abs(prediction - frame.future_sigma.to_numpy(dtype=float))))


def predict_fixed_attractor(frame: pd.DataFrame, center: float, slope: float) -> np.ndarray:
    """Predict a future local slope from a fixed-center restoring model."""
    return frame.sigma.to_numpy(dtype=float) + float(slope) * (frame.sigma.to_numpy(dtype=float) - float(center))
