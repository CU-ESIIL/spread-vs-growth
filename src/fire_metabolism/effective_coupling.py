"""Origin-safe effective-coupling analysis for FIRED trajectories.

The observable quantity in this module is a normalized mapped-growth
coefficient. It is not an independent measurement of latent coherence, fuel,
physical coupling, active fireline, or energetic metabolism.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from .adversarial_validation import (
    AREA_GEOMETRY_PREDICTORS,
    DYNAMICS_PREDICTORS,
    GEOMETRY_PREDICTORS,
    add_quadratic_features,
    tune_ridge_alpha,
)


DEFAULT_SIGMA = 2.0 / 3.0
COUPLING_HISTORY_PREDICTORS = (
    "log1p_current_coupling",
    "log1p_recent_mean_coupling",
    "recent_log_coupling_trend",
    "recent_log_coupling_curvature",
    "recent_coupling_active_fraction",
)
COUPLING_DYNAMICS_PREDICTORS = tuple(
    dict.fromkeys(COUPLING_HISTORY_PREDICTORS + DYNAMICS_PREDICTORS)
)
COUPLING_GEOMETRY_PREDICTORS = tuple(
    dict.fromkeys(COUPLING_DYNAMICS_PREDICTORS + GEOMETRY_PREDICTORS)
)
COUPLING_PREDICTION_COLUMNS = (
    "id",
    "ig_year",
    "snapshot_day",
    "partition",
    "lead_days",
    "target_day",
    "snapshot_area_km2",
    "future_area_km2",
    "future_growth_km2",
    "future_effective_coupling",
    "log1p_future_effective_coupling",
    "observable_at_target",
    "current_coupling",
    "log1p_current_coupling",
    "model",
    "predicted_log1p_coupling",
    "predicted_effective_coupling",
    "coupling_error",
    "absolute_coupling_error",
    "log1p_coupling_error",
    "absolute_log1p_coupling_error",
)


@dataclass(frozen=True)
class CouplingModelSet:
    """Lead-specific coupling models and their fixed feature columns."""

    models: dict[int, object]
    columns: tuple[str, ...]
    tuning: pd.DataFrame


def partition_years(year: pd.Series) -> pd.Series:
    """Apply the locked development/calibration/held-out split."""

    return pd.Series(
        np.select(
            [year <= 2012, year.between(2013, 2015), year >= 2016],
            ["development", "calibration", "held_out"],
            default="excluded",
        ),
        index=year.index,
    )


def coupling_series(event: pd.DataFrame, sigma: float = DEFAULT_SIGMA) -> pd.DataFrame:
    """Calculate discrete start-of-day normalized mapped growth.

    Day 1 is excluded because its pre-interval mapped area is zero. For day
    ``d>=2``, ``K[d] = daily_area[d] / cumulative_area[d-1]**sigma``.
    """

    if not 0 <= sigma < 1:
        raise ValueError("sigma must lie in [0, 1)")
    event = event.sort_values("event_day")
    required = {"event_day", "daily_area_km2", "cumulative_area_km2"}
    if missing := required.difference(event.columns):
        raise ValueError(f"missing coupling columns: {sorted(missing)}")
    if len(event) < 2:
        return pd.DataFrame(
            columns=[
                "event_day",
                "start_area_km2",
                "daily_growth_km2",
                "effective_coupling",
                "log1p_effective_coupling",
            ]
        )
    start_area = event.cumulative_area_km2.to_numpy(dtype=float)[:-1]
    growth = event.daily_area_km2.to_numpy(dtype=float)[1:]
    if np.any(start_area <= 0) or np.any(growth < 0):
        raise ValueError("coupling requires positive prior area and nonnegative growth")
    coupling = growth / np.maximum(start_area**sigma, 1e-12)
    return pd.DataFrame(
        {
            "event_day": event.event_day.to_numpy(dtype=int)[1:],
            "start_area_km2": start_area,
            "daily_growth_km2": growth,
            "effective_coupling": coupling,
            "log1p_effective_coupling": np.log1p(coupling),
        }
    )


def coupling_observations(
    sequences: pd.DataFrame, sigma: float = DEFAULT_SIGMA
) -> pd.DataFrame:
    """Create event-day coupling observations for the complete FIRED cohort."""

    rows: list[pd.DataFrame] = []
    for event_id, event in sequences.groupby("id", sort=False):
        part = coupling_series(event, sigma=sigma)
        if part.empty:
            continue
        part.insert(0, "id", int(event_id))
        part.insert(1, "ig_year", int(event.ig_year.iloc[0]))
        part.insert(2, "lc_name", str(event.lc_name.iloc[0]))
        part["duration_days"] = int(event.event_day.max())
        part["life_fraction"] = part.event_day / part.duration_days
        rows.append(part)
    if not rows:
        raise ValueError("no effective-coupling observations were available")
    result = pd.concat(rows, ignore_index=True)
    result["partition"] = partition_years(result.ig_year)
    result["sigma"] = float(sigma)
    return result


def add_coupling_history_features(
    features: pd.DataFrame,
    coupling: pd.DataFrame,
    *,
    lookback: int = 3,
) -> pd.DataFrame:
    """Attach coupling-history features available through each snapshot."""

    if lookback < 2:
        raise ValueError("lookback must be at least two days")
    lookup = {
        int(event_id): event.sort_values("event_day")
        for event_id, event in coupling.groupby("id", sort=False)
    }
    rows = []
    for row in features.itertuples(index=False):
        history = lookup.get(int(row.id))
        if history is None:
            continue
        history = history[history.event_day <= int(row.snapshot_day)]
        if history.empty:
            continue
        recent = history.tail(lookback)
        log_values = recent.log1p_effective_coupling.to_numpy(dtype=float)
        raw_values = recent.effective_coupling.to_numpy(dtype=float)
        trend = float(np.polyfit(np.arange(len(log_values)), log_values, 1)[0])
        curvature = (
            float(log_values[-1] - 2 * log_values[-2] + log_values[-3])
            if len(log_values) >= 3
            else 0.0
        )
        rows.append(
            {
                "id": int(row.id),
                "snapshot_day": int(row.snapshot_day),
                "current_coupling": float(raw_values[-1]),
                "log1p_current_coupling": float(log_values[-1]),
                "recent_mean_coupling": float(raw_values.mean()),
                "log1p_recent_mean_coupling": float(np.log1p(raw_values.mean())),
                "recent_log_coupling_trend": trend,
                "recent_log_coupling_curvature": curvature,
                "recent_coupling_active_fraction": float(np.mean(raw_values > 0)),
            }
        )
    history_features = pd.DataFrame(rows)
    if history_features.empty:
        raise ValueError("no coupling histories matched snapshot features")
    result = features.merge(
        history_features,
        on=["id", "snapshot_day"],
        how="inner",
        validate="one_to_one",
    )
    result["partition"] = partition_years(result.ig_year)
    return result


def future_coupling_targets(
    features: pd.DataFrame,
    sequences: pd.DataFrame,
    *,
    leads: Iterable[int],
    sigma: float = DEFAULT_SIGMA,
) -> pd.DataFrame:
    """Attach lead-specific coupling targets with zero post-terminal growth."""

    lead_values = tuple(sorted({int(lead) for lead in leads}))
    if not lead_values or lead_values[0] < 1:
        raise ValueError("leads must be positive")
    lookup = {
        int(event_id): event.sort_values("event_day")
        for event_id, event in sequences.groupby("id", sort=False)
    }
    rows: list[dict[str, object]] = []
    for origin in features.itertuples(index=False):
        event = lookup[int(origin.id)]
        daily = event.daily_area_km2.to_numpy(dtype=float)
        cumulative = event.cumulative_area_km2.to_numpy(dtype=float)
        snapshot = int(origin.snapshot_day)
        if snapshot > len(event):
            continue
        for lead in lead_values:
            target_day = snapshot + lead
            if target_day <= len(event):
                start_area = float(cumulative[target_day - 2])
                growth = float(daily[target_day - 1])
                target_area = float(cumulative[target_day - 1])
                target_observable = True
            else:
                start_area = float(cumulative[-1])
                growth = 0.0
                target_area = float(cumulative[-1])
                target_observable = False
            coupling = growth / max(start_area**sigma, 1e-12)
            rows.append(
                {
                    "id": int(origin.id),
                    "snapshot_day": snapshot,
                    "lead_days": lead,
                    "target_day": target_day,
                    "future_start_area_km2": start_area,
                    "future_growth_km2": growth,
                    "future_area_km2": target_area,
                    "future_effective_coupling": coupling,
                    "log1p_future_effective_coupling": float(np.log1p(coupling)),
                    "observable_at_target": target_observable,
                }
            )
    return pd.DataFrame(rows)


def fit_lead_coupling_models(
    frame: pd.DataFrame,
    *,
    model_name: str,
    feature_columns: Sequence[str],
    leads: Iterable[int],
) -> CouplingModelSet:
    """Fit calibration-tuned lead-specific normalized-growth regressions."""

    models: dict[int, object] = {}
    tuning_rows: list[pd.DataFrame] = []
    for lead in sorted({int(value) for value in leads}):
        data = frame[frame.lead_days.eq(lead)]
        development = data[data.partition.eq("development")]
        calibration = data[data.partition.eq("calibration")]
        if min(len(development), len(calibration)) < 40:
            continue
        model, curve = tune_ridge_alpha(
            development,
            calibration,
            target_column="log1p_future_effective_coupling",
            feature_columns=feature_columns,
        )
        models[lead] = model
        curve["model"] = model_name
        curve["lead_days"] = lead
        tuning_rows.append(curve)
    if not models:
        raise ValueError(f"no lead-specific models could be fitted for {model_name}")
    return CouplingModelSet(
        models=models,
        columns=tuple(feature_columns),
        tuning=pd.concat(tuning_rows, ignore_index=True),
    )


def predict_coupling(
    frame: pd.DataFrame,
    model_sets: dict[str, CouplingModelSet],
    *,
    partitions: Sequence[str] = ("development", "calibration", "held_out"),
) -> pd.DataFrame:
    """Predict lead-specific coupling from fixed origin information."""

    selected = frame[frame.partition.isin(partitions)]
    rows: list[pd.DataFrame] = []
    persistence = selected.copy()
    persistence["model"] = "coupling_persistence"
    persistence["predicted_log1p_coupling"] = persistence.log1p_current_coupling
    persistence["predicted_effective_coupling"] = persistence.current_coupling
    rows.append(persistence)
    for name, model_set in model_sets.items():
        for lead, model in model_set.models.items():
            data = selected[selected.lead_days.eq(lead)].copy()
            if data.empty:
                continue
            predicted_log = model.predict(data)
            data["model"] = name
            data["predicted_log1p_coupling"] = predicted_log
            data["predicted_effective_coupling"] = np.maximum(
                np.expm1(predicted_log), 0.0
            )
            rows.append(data)
    result = pd.concat(rows, ignore_index=True)
    result["coupling_error"] = (
        result.predicted_effective_coupling - result.future_effective_coupling
    )
    result["absolute_coupling_error"] = result.coupling_error.abs()
    result["log1p_coupling_error"] = (
        result.predicted_log1p_coupling
        - result.log1p_future_effective_coupling
    )
    result["absolute_log1p_coupling_error"] = result.log1p_coupling_error.abs()
    return result.loc[:, COUPLING_PREDICTION_COLUMNS]


def recursive_area_forecasts(
    coupling_predictions: pd.DataFrame,
    *,
    sigma: float = DEFAULT_SIGMA,
) -> pd.DataFrame:
    """Reconstruct future area using predicted coupling and predicted area only."""

    rows: list[dict[str, object]] = []
    keys = ["id", "snapshot_day", "partition", "model"]
    for key, group in coupling_predictions.groupby(keys, sort=False):
        group = group.sort_values("lead_days")
        area = float(group.snapshot_area_km2.iloc[0])
        previous_lead = 0
        for row in group.itertuples(index=False):
            lead = int(row.lead_days)
            if lead != previous_lead + 1:
                raise ValueError("recursive coupling predictions must contain consecutive leads")
            increment = float(row.predicted_effective_coupling) * area**sigma
            area = area + max(increment, 0.0)
            rows.append(
                {
                    "id": int(row.id),
                    "ig_year": int(row.ig_year),
                    "partition": row.partition,
                    "snapshot_day": int(row.snapshot_day),
                    "lead_days": lead,
                    "model": row.model,
                    "origin_area_km2": float(row.snapshot_area_km2),
                    "observed_area_km2": float(row.future_area_km2),
                    "predicted_area_km2": area,
                    "predicted_increment_km2": max(increment, 0.0),
                    "observed_at_target": bool(row.observable_at_target),
                }
            )
            previous_lead = lead
    result = pd.DataFrame(rows)
    result["signed_log_error"] = np.log(
        result.predicted_area_km2 / result.observed_area_km2
    )
    result["absolute_log_error"] = result.signed_log_error.abs()
    return result


def fixed_quadratic_coupling_frame(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    """Apply the existing fixed nonlinear basis to the K3 feature set."""

    return add_quadratic_features(frame, COUPLING_GEOMETRY_PREDICTORS)


def observed_area_at_lead(
    event: pd.DataFrame, snapshot_day: int, lead: int
) -> float:
    """Return cumulative area at a lead, extending terminal area as a plateau."""

    target_day = snapshot_day + lead
    observed = event[event.event_day <= target_day]
    if observed.empty:
        raise ValueError("target precedes event")
    return float(observed.cumulative_area_km2.iloc[-1])


def exact_growth_change_decomposition(
    area_start: Sequence[float],
    coupling_now: Sequence[float],
    coupling_next: Sequence[float],
    *,
    sigma: float = DEFAULT_SIGMA,
) -> pd.DataFrame:
    """Decompose one-step growth change into coupling and scale terms.

    With ``M_t=K_t A_t^sigma`` and ``A_{t+1}=A_t+M_t``, the exact identity is

    ``M_{t+1}-M_t = (K_{t+1}-K_t)A_t^sigma
                    + K_{t+1}(A_{t+1}^sigma-A_t^sigma)``.
    """

    area = np.asarray(area_start, dtype=float)
    first = np.asarray(coupling_now, dtype=float)
    second = np.asarray(coupling_next, dtype=float)
    if not (area.shape == first.shape == second.shape):
        raise ValueError("decomposition arrays must have matching shapes")
    growth_now = first * area**sigma
    area_next = area + growth_now
    coupling_term = (second - first) * area**sigma
    scale_term = second * (area_next**sigma - area**sigma)
    total_change = second * area_next**sigma - growth_now
    return pd.DataFrame(
        {
            "coupling_change_term": coupling_term,
            "scale_change_term": scale_term,
            "total_growth_change": total_change,
            "identity_residual": total_change - coupling_term - scale_term,
        }
    )
