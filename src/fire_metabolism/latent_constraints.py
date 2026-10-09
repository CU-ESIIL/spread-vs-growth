"""Origin-safe utilities for unresolved fire-growth realization deficits.

The routines in this module deliberately separate a prospective prediction of
expected growth from the retrospective residual observed after an interval.
They do not attribute a negative residual to suppression or any other cause.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
import pandas as pd

from .fired_outcomes import fit_standardized_ridge
from .fired_survival import fit_logistic_hazard


DEFAULT_SEED = 20261009
DEFAULT_LEADS = (1, 3, 5, 7, 10, 14, 21, 28, 35, 42)


def assign_partition(year: pd.Series) -> pd.Series:
    """Return the locked development/calibration/held-out split."""
    return pd.Series(
        np.select(
            [year.to_numpy() <= 2012, year.to_numpy() <= 2015],
            ["development", "calibration"],
            default="held_out",
        ),
        index=year.index,
    )


def build_interval_table(
    snapshots: pd.DataFrame,
    sequences: pd.DataFrame,
    *,
    leads: Iterable[int] = DEFAULT_LEADS,
) -> pd.DataFrame:
    """Attach future growth outcomes to past-only landmark features."""
    leads = tuple(sorted({int(value) for value in leads if int(value) > 0}))
    lookup = {
        int(event_id): event.sort_values("event_day").set_index("event_day")
        for event_id, event in sequences.groupby("id", sort=False)
    }
    rows: list[dict[str, float | int | bool]] = []
    for origin in snapshots.itertuples(index=False):
        event = lookup[int(origin.id)]
        origin_day = int(origin.snapshot_day)
        origin_area = float(origin.snapshot_area_km2)
        death_day = int(origin.death_day)
        final_area = float(origin.final_area_km2)
        for lead in leads:
            target_day = origin_day + lead
            available = event.index[event.index <= target_day]
            target_area = float(event.loc[available.max(), "cumulative_area_km2"]) if len(available) else origin_area
            target_area = max(target_area, origin_area)
            total_growth = target_area - origin_area
            average_growth = total_growth / lead
            rows.append(
                {
                    "id": int(origin.id),
                    "ig_year": int(origin.ig_year),
                    "origin_day": origin_day,
                    "lead_days": lead,
                    "target_day": target_day,
                    "origin_area_km2": origin_area,
                    "observed_future_area_km2": target_area,
                    "observed_total_growth_km2": total_growth,
                    "observed_mean_growth_km2_day": average_growth,
                    "log1p_observed_mean_growth": float(np.log1p(average_growth)),
                    "realized_coupling": float(average_growth / max(origin_area ** (2 / 3), 1e-12)),
                    "terminated_within_horizon": bool(death_day <= target_day),
                    "remaining_area_km2": max(final_area - origin_area, 0.0),
                }
            )
    result = snapshots.rename(columns={"snapshot_day": "origin_day"}).merge(
        pd.DataFrame(rows), on=["id", "ig_year", "origin_day"], how="inner"
    )
    result["partition"] = assign_partition(result.ig_year)
    result["log1p_lead"] = np.log1p(result.lead_days)
    result["lead_scaled"] = result.lead_days / 42.0
    result["log_origin_area"] = np.log(result.origin_area_km2.clip(lower=1e-12))
    result["origin_age_scaled"] = result.origin_day / 42.0
    return result


def tune_ridge(
    frame: pd.DataFrame,
    *,
    target: str,
    feature_sets: dict[str, Sequence[str]],
    alphas: Sequence[float] = (0.1, 1.0, 10.0, 100.0),
) -> tuple[object, dict[str, object], pd.DataFrame]:
    """Select a feature family and ridge penalty without held-out outcomes."""
    dev = frame[frame.partition.eq("development")]
    cal = frame[frame.partition.eq("calibration")]
    rows = []
    for name, columns in feature_sets.items():
        columns = tuple(columns)
        for alpha in alphas:
            model = fit_standardized_ridge(dev, dev[target], feature_columns=columns, alpha=float(alpha))
            prediction = model.predict(cal)
            rows.append(
                {
                    "model": name,
                    "alpha": float(alpha),
                    "calibration_mae": float(np.mean(np.abs(prediction - cal[target]))),
                    "features": ";".join(columns),
                }
            )
    tuning = pd.DataFrame(rows).sort_values(["calibration_mae", "model", "alpha"])
    selected = tuning.iloc[0].to_dict()
    columns = tuple(str(selected["features"]).split(";"))
    train = frame[frame.partition.ne("held_out")]
    model = fit_standardized_ridge(
        train,
        train[target],
        feature_columns=columns,
        alpha=float(selected["alpha"]),
    )
    return model, selected, tuning


def add_realization_residuals(
    frame: pd.DataFrame,
    predicted_log_growth: Sequence[float],
    *,
    epsilon: float = 0.01,
) -> pd.DataFrame:
    """Add model-implied expected growth and retrospective residuals."""
    result = frame.copy()
    predicted_log = np.asarray(predicted_log_growth, dtype=float)
    potential_mean = np.maximum(np.expm1(predicted_log), 0.0)
    observed = result.observed_mean_growth_km2_day.to_numpy(dtype=float)
    result["predicted_log1p_mean_growth"] = predicted_log
    result["model_implied_mean_growth_km2_day"] = potential_mean
    result["model_implied_total_growth_km2"] = potential_mean * result.lead_days.to_numpy(dtype=float)
    result["model_implied_future_area_km2"] = (
        result.origin_area_km2.to_numpy(dtype=float)
        + result.model_implied_total_growth_km2.to_numpy(dtype=float)
    )
    result["realization_residual_q"] = np.log(observed + epsilon) - np.log(potential_mean + epsilon)
    result["realization_ratio_Q"] = (observed + epsilon) / (potential_mean + epsilon)
    result["predicted_potential_coupling"] = potential_mean / np.maximum(
        result.origin_area_km2.to_numpy(dtype=float) ** (2 / 3), 1e-12
    )
    result["future_area_log_error_potential"] = np.abs(
        np.log1p(result.model_implied_future_area_km2)
        - np.log1p(result.observed_future_area_km2)
    )
    return result


def development_thresholds(frame: pd.DataFrame, quantile: float = 0.10) -> pd.DataFrame:
    """Lock lead-specific deficit thresholds using development/calibration rows."""
    train = frame[frame.partition.ne("held_out")]
    rows = []
    for lead, group in train.groupby("lead_days"):
        rows.append(
            {
                "lead_days": int(lead),
                "constraint_threshold_q": float(group.realization_residual_q.quantile(quantile)),
                "quantile": float(quantile),
            }
        )
    return pd.DataFrame(rows)


def attach_constraint_indicator(frame: pd.DataFrame, thresholds: pd.DataFrame) -> pd.DataFrame:
    """Apply prespecified lead-specific thresholds to all partitions."""
    result = frame.merge(thresholds, on="lead_days", how="left", validate="many_to_one")
    result["constraint_like"] = (
        result.realization_residual_q <= result.constraint_threshold_q
    ).astype(int)
    return result


def fit_constraint_hazards(
    frame: pd.DataFrame,
    feature_sets: dict[str, Sequence[str]],
    *,
    alpha: float = 1.0,
) -> tuple[dict[str, object], pd.DataFrame]:
    """Fit prospective binary deficit-risk models on pre-held-out rows."""
    train = frame[frame.partition.ne("held_out")].copy()
    train["terminal_transition"] = train.constraint_like.astype(float)
    models: dict[str, object] = {}
    rows = []
    for name, columns in feature_sets.items():
        if name == "H0_constant":
            probability = float(train.constraint_like.mean())
            models[name] = probability
            rows.append({"model": name, "alpha": 0.0, "features": "", "train_event_rate": probability})
            continue
        model = fit_logistic_hazard(train, feature_columns=columns, alpha=alpha)
        models[name] = model
        rows.append(
            {
                "model": name,
                "alpha": alpha,
                "features": ";".join(columns),
                "train_event_rate": float(train.constraint_like.mean()),
            }
        )
    return models, pd.DataFrame(rows)


def predict_constraint_probability(model: object, frame: pd.DataFrame) -> np.ndarray:
    """Predict a constant or fitted hazard probability."""
    if isinstance(model, (float, np.floating)):
        return np.full(len(frame), float(model))
    return np.asarray(model.predict_hazard(frame), dtype=float)


def binary_scores(observed: Sequence[int], probability: Sequence[float]) -> dict[str, float]:
    """Return proper binary scores and a simple calibration intercept/slope."""
    y = np.asarray(observed, dtype=float)
    p = np.clip(np.asarray(probability, dtype=float), 1e-6, 1 - 1e-6)
    logits = np.log(p / (1 - p))
    x = np.column_stack([np.ones(len(y)), logits])
    coefficient, *_ = np.linalg.lstsq(x, y, rcond=None)
    return {
        "brier": float(np.mean((p - y) ** 2)),
        "log_score": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
        "calibration_intercept_linear": float(coefficient[0]),
        "calibration_slope_linear": float(coefficient[1]),
        "mean_probability": float(p.mean()),
        "event_rate": float(y.mean()),
    }


def event_bootstrap_mean_ci(
    frame: pd.DataFrame,
    value: str,
    *,
    replicates: int = 1000,
    seed: int = DEFAULT_SEED,
) -> tuple[float, float]:
    """Bootstrap a mean while resampling whole fires."""
    by_event = frame.groupby("id")[value].mean().dropna().to_numpy(dtype=float)
    if len(by_event) == 0:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    draws = rng.choice(by_event, size=(replicates, len(by_event)), replace=True).mean(axis=1)
    return float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def fixed_center_prediction(train: pd.DataFrame, evaluation: pd.DataFrame, center: float) -> np.ndarray:
    """Fit one fixed-equilibrium restoring coefficient and predict future slope."""
    x = train.sigma.to_numpy(dtype=float) - float(center)
    y = train.delta_sigma.to_numpy(dtype=float)
    denominator = float(np.dot(x, x))
    coefficient = float(np.dot(x, y) / denominator) if denominator > 0 else 0.0
    return evaluation.sigma.to_numpy(dtype=float) + coefficient * (
        evaluation.sigma.to_numpy(dtype=float) - float(center)
    )


def robust_fixed_restoring(frame: pd.DataFrame, center: float = 2 / 3) -> float:
    """Huber-weighted fixed-center restoring coefficient."""
    x = frame.sigma.to_numpy(dtype=float) - center
    y = frame.delta_sigma.to_numpy(dtype=float)
    coefficient = float(np.dot(x, y) / max(np.dot(x, x), 1e-12))
    for _ in range(50):
        residual = y - coefficient * x
        scale = max(float(np.median(np.abs(residual - np.median(residual))) * 1.4826), 1e-8)
        weight = np.minimum(1.0, 1.345 * scale / np.maximum(np.abs(residual), 1e-12))
        updated = float(np.dot(weight * x, y) / max(np.dot(weight * x, x), 1e-12))
        if abs(updated - coefficient) < 1e-10:
            break
        coefficient = updated
    return coefficient
