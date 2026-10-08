"""Leakage-resistant forecasts from FIRED daily burned-area sequences.

The reader intentionally uses only GeoPackage attribute columns. FIRED's
``dy_ar_km2`` field records newly detected burned area on observation days;
missing calendar days are reconstructed as zero detected growth before the
cumulative-area trajectory is formed.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

import numpy as np
import pandas as pd


NATURAL_VEGETATION_CLASSES = (
    "Grasslands",
    "Woody Savannas",
    "Savannas",
    "Evergreen Needleleaf Forests",
    "Deciduous Broadleaf Forests",
    "Open Shrublands",
    "Evergreen Broadleaf Forests",
    "Closed Shrublands",
    "Mixed Forests",
)


def _feature_table(connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        "SELECT table_name FROM gpkg_contents WHERE data_type = 'features'"
    ).fetchall()
    if len(rows) != 1:
        raise ValueError(f"expected one GeoPackage feature table, found {len(rows)}")
    return str(rows[0][0])


def load_fired_daily_attributes(
    path: str | Path,
    *,
    min_duration: int = 8,
    max_duration: int = 60,
    min_final_area_km2: float = 10.0,
    start_year: int = 2001,
    end_year: int = 2020,
    landcover_classes: Sequence[str] = NATURAL_VEGETATION_CLASSES,
    min_detection_days: int = 4,
) -> pd.DataFrame:
    """Load analysis attributes from a FIRED daily GeoPackage.

    The GeoPackage is opened in SQLite immutable mode, which permits reading a
    WAL-enabled cache without creating sidecar files next to the source.
    Events whose first available observation is not event day one are removed
    because their initial cumulative area cannot be reconstructed reliably.
    """
    source = Path(path).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    if min_duration < 2 or max_duration < min_duration:
        raise ValueError("duration limits are invalid")
    if min_final_area_km2 <= 0 or min_detection_days < 1:
        raise ValueError("area and detection-day thresholds must be positive")
    if not landcover_classes:
        raise ValueError("at least one land-cover class is required")

    connection = sqlite3.connect(f"file:{source}?immutable=1", uri=True)
    try:
        table = _feature_table(connection)
        query = f'''\
            SELECT id, date, ig_date, event_day, event_dur, dy_ar_km2,
                   tot_ar_km2, ig_year, lc_name
            FROM "{table}"
            WHERE event_dur BETWEEN ? AND ?
              AND tot_ar_km2 >= ?
              AND ig_year BETWEEN ? AND ?
            ORDER BY id, event_day
        '''
        params = (
            min_duration,
            max_duration,
            min_final_area_km2,
            start_year,
            end_year,
        )
        records = pd.read_sql_query(query, connection, params=params)
    finally:
        connection.close()

    if records.empty:
        raise ValueError("no FIRED rows satisfy the requested filters")
    event_quality = records.groupby("id", sort=False).agg(
        first_event_day=("event_day", "min"),
        detection_days=("event_day", "nunique"),
    )
    landcover_area = (
        records.groupby(["id", "lc_name"], dropna=False, as_index=False)["dy_ar_km2"]
        .sum()
        .sort_values(["id", "dy_ar_km2"], ascending=[True, False])
        .drop_duplicates("id")
        .set_index("id")["lc_name"]
    )
    event_quality["dominant_lc_name"] = landcover_area
    eligible = event_quality.index[
        (event_quality["first_event_day"] == 1)
        & (event_quality["detection_days"] >= min_detection_days)
        & (event_quality["dominant_lc_name"].isin(landcover_classes))
    ]
    records = records[records["id"].isin(eligible)].copy()
    records["dominant_lc_name"] = records["id"].map(
        event_quality["dominant_lc_name"]
    )
    if records.empty:
        raise ValueError("no FIRED events pass the sequence-quality filters")
    return records.reset_index(drop=True)


def reconstruct_daily_sequences(
    records: pd.DataFrame, *, final_area_relative_tolerance: float = 0.01
) -> pd.DataFrame:
    """Expand FIRED observation rows into gap-free cumulative-area sequences.

    Events are omitted when summed daily increments do not reconcile with the
    reported final area. Such rows are incomplete sequences for forecasting.
    """
    if not 0 <= final_area_relative_tolerance < 1:
        raise ValueError("final-area tolerance must lie in [0, 1)")
    required = {
        "id",
        "ig_date",
        "event_day",
        "event_dur",
        "dy_ar_km2",
        "tot_ar_km2",
        "ig_year",
        "lc_name",
        "dominant_lc_name",
    }
    missing = required.difference(records.columns)
    if missing:
        raise ValueError(f"missing FIRED columns: {sorted(missing)}")

    frames: list[pd.DataFrame] = []
    for event_id, event in records.groupby("id", sort=False):
        duration = int(event["event_dur"].iloc[0])
        increments = np.zeros(duration, dtype=float)
        for day, area in event.groupby("event_day", sort=False)["dy_ar_km2"].sum().items():
            day_index = int(day) - 1
            if 0 <= day_index < duration:
                increments[day_index] += float(area)
        cumulative = np.cumsum(increments)
        if cumulative[0] <= 0 or np.any(np.diff(cumulative) < -1e-12):
            continue
        reported_final_area = float(event["tot_ar_km2"].iloc[0])
        relative_difference = abs(cumulative[-1] - reported_final_area) / reported_final_area
        if relative_difference > final_area_relative_tolerance:
            continue
        ignition = pd.Timestamp(event["ig_date"].iloc[0])
        frame = pd.DataFrame(
            {
                "id": int(event_id),
                "ig_year": int(event["ig_year"].iloc[0]),
                "lc_name": str(event["dominant_lc_name"].iloc[0]),
                "event_day": np.arange(1, duration + 1, dtype=int),
                "date": ignition + pd.to_timedelta(np.arange(duration), unit="D"),
                "daily_area_km2": increments,
                "cumulative_area_km2": cumulative,
                "reported_final_area_km2": reported_final_area,
                "reconstructed_final_area_km2": float(cumulative[-1]),
            }
        )
        frames.append(frame)
    if not frames:
        raise ValueError("no valid cumulative-area sequences could be reconstructed")
    return pd.concat(frames, ignore_index=True)


def transformed_trend_forecast(area_history, horizon: int, sigma: float) -> float:
    """Forecast cumulative area from an anchored local transformed trend.

    For ``dA/dt = beta A**sigma`` with constant beta, ``A**(1-sigma)``
    is linear in time. The slope is estimated from history only, constrained
    nonnegative, and the extrapolation is anchored at the observed origin.
    """
    area = np.asarray(area_history, dtype=float)
    if area.ndim != 1 or area.size < 2 or np.any(area <= 0):
        raise ValueError("area history must contain at least two positive values")
    if horizon < 1:
        raise ValueError("horizon must be at least one day")
    if not 0 <= sigma < 1:
        raise ValueError("sigma must lie in [0, 1)")
    transformed = area ** (1 - sigma)
    x = np.arange(area.size, dtype=float)
    slope = max(0.0, float(np.polyfit(x, transformed, 1)[0]))
    future = transformed[-1] + slope * horizon
    return float(future ** (1 / (1 - sigma)))


def rolling_predictions(
    sequences: pd.DataFrame,
    sigmas: Mapping[str, float],
    *,
    lookback_days: int = 4,
    horizons: Iterable[int] = (1, 2, 3),
) -> pd.DataFrame:
    """Generate rolling-origin forecasts without using post-origin values."""
    if lookback_days < 2:
        raise ValueError("lookback_days must be at least two")
    horizons = tuple(sorted({int(value) for value in horizons}))
    if not horizons or horizons[0] < 1:
        raise ValueError("forecast horizons must be positive")
    for name, sigma in sigmas.items():
        if not name or not 0 <= float(sigma) < 1:
            raise ValueError("model names and sigma values must be valid")

    rows: list[dict[str, object]] = []
    for event_id, event in sequences.groupby("id", sort=False):
        event = event.sort_values("event_day")
        area = event["cumulative_area_km2"].to_numpy(dtype=float)
        increments = event["daily_area_km2"].to_numpy(dtype=float)
        days = event["event_day"].to_numpy(dtype=int)
        dates = pd.to_datetime(event["date"]).to_numpy()
        metadata = {
            "id": int(event_id),
            "ig_year": int(event["ig_year"].iloc[0]),
            "lc_name": str(event["lc_name"].iloc[0]),
        }
        for origin_index in range(lookback_days - 1, len(event) - 1):
            history = area[origin_index - lookback_days + 1 : origin_index + 1]
            if np.any(history <= 0):
                continue
            for horizon in horizons:
                target_index = origin_index + horizon
                if target_index >= len(event):
                    continue
                observed = float(area[target_index])
                origin_area = float(area[origin_index])
                common = {
                    **metadata,
                    "origin_day": int(days[origin_index]),
                    "origin_date": pd.Timestamp(dates[origin_index]),
                    "horizon_days": horizon,
                    "origin_area_km2": origin_area,
                    "observed_area_km2": observed,
                    "origin_active": bool(increments[origin_index] > 0),
                    "target_growth": bool(observed > origin_area + 1e-12),
                }
                rows.append({**common, "model": "no_growth", "sigma": np.nan, "predicted_area_km2": origin_area})
                for model, sigma in sigmas.items():
                    predicted = transformed_trend_forecast(history, horizon, float(sigma))
                    rows.append(
                        {
                            **common,
                            "model": model,
                            "sigma": float(sigma),
                            "predicted_area_km2": predicted,
                        }
                    )

    predictions = pd.DataFrame(rows)
    if predictions.empty:
        raise ValueError("no rolling forecasts could be generated")
    predicted = predictions["predicted_area_km2"].to_numpy(dtype=float)
    observed = predictions["observed_area_km2"].to_numpy(dtype=float)
    predictions["log_ratio"] = np.log(predicted / observed)
    predictions["absolute_log_ratio"] = np.abs(predictions["log_ratio"])
    predictions["absolute_error_km2"] = np.abs(predicted - observed)
    predictions["smape"] = 2 * np.abs(predicted - observed) / (predicted + observed)
    return predictions


def select_sigma_by_training_error(
    sequences: pd.DataFrame,
    candidate_sigmas: Iterable[float],
    *,
    lookback_days: int = 4,
    horizons: Iterable[int] = (1, 2, 3),
) -> pd.DataFrame:
    """Select one sigma per horizon using event-balanced training error."""
    candidates = sorted({float(value) for value in candidate_sigmas})
    if not candidates:
        raise ValueError("candidate_sigmas cannot be empty")
    curve_parts = []
    batch_size = 4
    for start in range(0, len(candidates), batch_size):
        batch = candidates[start : start + batch_size]
        models = {f"sigma_{sigma:.6f}": sigma for sigma in batch}
        predictions = rolling_predictions(
            sequences, models, lookback_days=lookback_days, horizons=horizons
        )
        predictions = predictions[predictions["model"] != "no_growth"]
        event_error = (
            predictions.groupby(["id", "horizon_days", "model", "sigma"], as_index=False)
            ["absolute_log_ratio"]
            .mean()
        )
        curve_parts.append(
            event_error.groupby(["horizon_days", "model", "sigma"], as_index=False)
            .agg(
                mean_event_absolute_log_ratio=("absolute_log_ratio", "mean"),
                n_events=("id", "nunique"),
            )
        )
    curve = pd.concat(curve_parts, ignore_index=True).sort_values(
        ["horizon_days", "sigma"]
    )
    best_indices = curve.groupby("horizon_days")["mean_event_absolute_log_ratio"].idxmin()
    curve["selected"] = False
    curve.loc[best_indices, "selected"] = True
    return curve.reset_index(drop=True)


def summarize_predictions(
    predictions: pd.DataFrame,
    *,
    subset: str = "all",
    bootstrap_replicates: int = 2000,
    seed: int = 20260927,
) -> pd.DataFrame:
    """Summarize event-balanced forecast errors with event bootstrap intervals."""
    if subset not in {"all", "growth_only", "active_origin"}:
        raise ValueError("unknown prediction subset")
    selected = predictions
    if subset == "growth_only":
        selected = selected[selected["target_growth"]]
    elif subset == "active_origin":
        selected = selected[selected["origin_active"]]
    if selected.empty:
        raise ValueError(f"prediction subset {subset!r} is empty")

    event_metrics = (
        selected.groupby(["id", "horizon_days", "model"], as_index=False)
        .agg(
            absolute_log_ratio=("absolute_log_ratio", "mean"),
            absolute_error_km2=("absolute_error_km2", "mean"),
            smape=("smape", "mean"),
            log_ratio=("log_ratio", "mean"),
        )
    )
    rng = np.random.default_rng(seed)
    rows = []
    for (horizon, model), group in event_metrics.groupby(["horizon_days", "model"], sort=False):
        values = group["absolute_log_ratio"].to_numpy(dtype=float)
        if bootstrap_replicates > 0:
            indices = rng.integers(0, values.size, size=(bootstrap_replicates, values.size))
            boot = values[indices].mean(axis=1)
            lower, upper = np.quantile(boot, [0.025, 0.975])
        else:
            lower = upper = np.nan
        matching = selected[
            (selected["horizon_days"] == horizon) & (selected["model"] == model)
        ]
        sigma_values = matching["sigma"].dropna().unique()
        rows.append(
            {
                "subset": subset,
                "horizon_days": int(horizon),
                "model": model,
                "sigma": float(sigma_values[0]) if len(sigma_values) == 1 else np.nan,
                "n_events": int(group["id"].nunique()),
                "n_forecasts": int(len(matching)),
                "mean_event_absolute_log_ratio": float(values.mean()),
                "ci95_lower": float(lower),
                "ci95_upper": float(upper),
                "mean_event_absolute_error_km2": float(group["absolute_error_km2"].mean()),
                "mean_event_smape": float(group["smape"].mean()),
                "mean_event_log_bias": float(group["log_ratio"].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values(["subset", "horizon_days", "model"]).reset_index(drop=True)
