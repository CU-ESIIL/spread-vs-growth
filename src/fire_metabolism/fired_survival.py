"""State-conditioned discrete-time survival models for FIRED fire death."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit


STATE_NAMES = ("accelerating", "declining", "quiescent", "reactivated")
STATE_FEATURE_COLUMNS = (
    "state_accelerating",
    "state_quiescent",
    "state_reactivated",
)
MECHANISTIC_SURVIVAL_FEATURE_COLUMNS = (
    "log_snapshot_area",
    "log_mean_daily_growth",
    "log_recent_growth",
    "growth_day_fraction",
    "recent_area_fraction",
    "log_peak_growth",
    "log_cumulative_slope",
    "log_total_perimeter",
    "log_exterior_perimeter",
    "log_total_excess_perimeter",
    "log_exterior_excess_perimeter",
    "total_perimeter_area_slope",
    "exterior_perimeter_area_slope",
    "log_recent_beta_two_thirds",
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
TIME_FEATURE_COLUMNS = (
    "log1p_forecast_horizon",
    "forecast_horizon_scaled",
    "horizon_after_3",
    "horizon_after_7",
    "horizon_after_14",
    "accelerating_log_horizon",
    "quiescent_log_horizon",
    "reactivated_log_horizon",
)
STATE_SURVIVAL_FEATURE_COLUMNS = STATE_FEATURE_COLUMNS + TIME_FEATURE_COLUMNS
GEOMETRY_STATE_SURVIVAL_FEATURE_COLUMNS = (
    MECHANISTIC_SURVIVAL_FEATURE_COLUMNS
    + STATE_FEATURE_COLUMNS
    + TIME_FEATURE_COLUMNS
)
DAMAGE_FEATURE_COLUMNS = (
    "log_cumulative_beta_exposure",
    "log_cumulative_squared_beta_damage",
    "log_beta_decline_damage",
    "log_beta_volatility_damage",
    "log_squared_damage_rho_80",
    "log_squared_damage_rho_90",
    "log_squared_damage_rho_97",
    "log_damage_to_cube_root_capacity",
)


def add_observed_states(
    features: pd.DataFrame, sequences: pd.DataFrame
) -> pd.DataFrame:
    """Classify each snapshot using only growth observed through that day."""
    required = {"id", "event_day", "daily_area_km2"}
    if missing := required.difference(sequences.columns):
        raise ValueError(f"missing sequence columns: {sorted(missing)}")
    required_features = {"id", "snapshot_day", "recent_growth_acceleration"}
    if missing := required_features.difference(features.columns):
        raise ValueError(f"missing feature columns: {sorted(missing)}")

    daily_lookup = {
        int(event_id): event.sort_values("event_day")["daily_area_km2"].to_numpy(
            dtype=float
        )
        for event_id, event in sequences.groupby("id", sort=False)
    }
    states = []
    for row in features.itertuples(index=False):
        daily = daily_lookup[int(row.id)][: int(row.snapshot_day)]
        if daily.size != int(row.snapshot_day):
            raise ValueError("snapshot history is incomplete")
        if daily[-1] <= 0:
            state = "quiescent"
        elif daily.size > 1 and daily[-2] <= 0:
            state = "reactivated"
        elif float(row.recent_growth_acceleration) > 0:
            state = "accelerating"
        else:
            state = "declining"
        states.append(state)

    result = features.copy()
    result["observed_state"] = states
    for state in STATE_NAMES:
        result[f"state_{state}"] = (result.observed_state == state).astype(float)
    return result


def add_metabolic_damage_features(
    features: pd.DataFrame, sequences: pd.DataFrame
) -> pd.DataFrame:
    """Add past-only exposure and path-dependent two-thirds damage proxies."""
    required = {
        "id",
        "event_day",
        "daily_area_km2",
        "cumulative_area_km2",
    }
    if missing := required.difference(sequences.columns):
        raise ValueError(f"missing sequence columns: {sorted(missing)}")
    if missing := {"id", "snapshot_day"}.difference(features.columns):
        raise ValueError(f"missing feature columns: {sorted(missing)}")
    histories = {
        int(event_id): event.sort_values("event_day")
        for event_id, event in sequences.groupby("id", sort=False)
    }
    rows = []
    for row in features[["id", "snapshot_day"]].itertuples(index=False):
        history = histories[int(row.id)].iloc[: int(row.snapshot_day)]
        if len(history) != int(row.snapshot_day):
            raise ValueError("snapshot history is incomplete")
        area = history.cumulative_area_km2.to_numpy(dtype=float)
        daily = history.daily_area_km2.to_numpy(dtype=float)
        beta = daily / np.maximum(area ** (2.0 / 3.0), 1e-12)
        squared = beta**2
        decline = np.maximum(0.0, -np.diff(beta)).sum()
        volatility = np.abs(np.diff(beta)).sum()
        damage = {
            "id": int(row.id),
            "snapshot_day": int(row.snapshot_day),
            "log_cumulative_beta_exposure": float(np.log1p(beta.sum())),
            "log_cumulative_squared_beta_damage": float(np.log1p(squared.sum())),
            "log_beta_decline_damage": float(np.log1p(decline)),
            "log_beta_volatility_damage": float(np.log1p(volatility)),
        }
        for retention, label in ((0.80, "80"), (0.90, "90"), (0.97, "97")):
            retained = np.sum(
                squared[::-1] * retention ** np.arange(len(squared), dtype=float)
            )
            damage[f"log_squared_damage_rho_{label}"] = float(np.log1p(retained))
        damage["log_damage_to_cube_root_capacity"] = float(
            np.log1p(squared.sum() / max(area[-1] ** (1.0 / 3.0), 1e-12))
        )
        rows.append(damage)
    damage_frame = pd.DataFrame(rows)
    result = features.merge(
        damage_frame,
        on=["id", "snapshot_day"],
        how="left",
        validate="one_to_one",
    )
    if not np.isfinite(result.loc[:, DAMAGE_FEATURE_COLUMNS]).all().all():
        raise ValueError("damage features must be finite")
    return result


def add_horizon_features(frame: pd.DataFrame, horizons: Sequence[int]) -> pd.DataFrame:
    """Repeat landmark rows and add a flexible future-time hazard basis."""
    horizon = np.asarray(horizons, dtype=int)
    if len(frame) != horizon.size or np.any(horizon < 1):
        raise ValueError("one positive forecast horizon is required per row")
    result = frame.copy()
    log_horizon = np.log1p(horizon.astype(float))
    result["forecast_horizon"] = horizon
    result["log1p_forecast_horizon"] = log_horizon
    result["forecast_horizon_scaled"] = horizon / 30.0
    result["horizon_after_3"] = np.maximum(horizon - 3, 0) / 30.0
    result["horizon_after_7"] = np.maximum(horizon - 7, 0) / 30.0
    result["horizon_after_14"] = np.maximum(horizon - 14, 0) / 30.0
    result["accelerating_log_horizon"] = result.state_accelerating * log_horizon
    result["quiescent_log_horizon"] = result.state_quiescent * log_horizon
    result["reactivated_log_horizon"] = result.state_reactivated * log_horizon
    return result


def make_person_period_table(features: pd.DataFrame) -> pd.DataFrame:
    """Expand one snapshot per event into daily at-risk rows through death."""
    required = {"id", "snapshot_day", "death_day", "observed_state"}
    if missing := required.difference(features.columns):
        raise ValueError(f"missing survival columns: {sorted(missing)}")
    repeats = (
        features.death_day.to_numpy(dtype=int)
        - features.snapshot_day.to_numpy(dtype=int)
    )
    if np.any(repeats < 1):
        raise ValueError("all landmark events must survive beyond the snapshot")
    expanded = features.loc[features.index.repeat(repeats)].reset_index(drop=True)
    horizons = np.concatenate([np.arange(1, value + 1) for value in repeats])
    expanded = add_horizon_features(expanded, horizons)
    expanded["terminal_transition"] = (
        expanded.forecast_horizon.to_numpy() == np.repeat(repeats, repeats)
    ).astype(float)
    return expanded


@dataclass(frozen=True)
class StandardizedLogisticHazard:
    """Ridge-regularized daily terminal-transition hazard."""

    feature_columns: tuple[str, ...]
    mean: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray
    logit_shift: float = 0.0

    def predict_logit(self, frame: pd.DataFrame) -> np.ndarray:
        values = frame.loc[:, self.feature_columns].to_numpy(dtype=float)
        standardized = (values - self.mean) / self.scale
        design = np.column_stack([np.ones(len(frame)), standardized])
        return design @ self.coefficients + self.logit_shift

    def predict_hazard(self, frame: pd.DataFrame) -> np.ndarray:
        return expit(self.predict_logit(frame))

    def with_shift(self, value: float) -> "StandardizedLogisticHazard":
        return replace(self, logit_shift=float(value))


def fit_logistic_hazard(
    person_period: pd.DataFrame,
    *,
    feature_columns: Sequence[str],
    alpha: float = 1.0,
) -> StandardizedLogisticHazard:
    """Fit a standardized logistic hazard with an unpenalized intercept."""
    columns = tuple(feature_columns)
    if not columns or alpha < 0:
        raise ValueError("feature columns cannot be empty and alpha must be nonnegative")
    if missing := set(columns).difference(person_period.columns):
        raise ValueError(f"missing hazard features: {sorted(missing)}")
    values = person_period.loc[:, columns].to_numpy(dtype=float)
    target = person_period.terminal_transition.to_numpy(dtype=float)
    if not np.isfinite(values).all() or not set(np.unique(target)).issubset({0.0, 1.0}):
        raise ValueError("hazard inputs must be finite and targets binary")
    mean = values.mean(axis=0)
    scale = values.std(axis=0)
    scale[scale < 1e-12] = 1.0
    design = np.column_stack([np.ones(len(values)), (values - mean) / scale])

    initial = np.zeros(design.shape[1], dtype=float)
    event_rate = np.clip(target.mean(), 1e-6, 1 - 1e-6)
    initial[0] = np.log(event_rate / (1 - event_rate))

    def objective(coefficients: np.ndarray) -> tuple[float, np.ndarray]:
        logits = design @ coefficients
        penalty = 0.5 * alpha * np.dot(coefficients[1:], coefficients[1:])
        loss = float(np.sum(np.logaddexp(0.0, logits) - target * logits) + penalty)
        gradient = design.T @ (expit(logits) - target)
        gradient[1:] += alpha * coefficients[1:]
        return loss, gradient

    result = minimize(
        objective,
        initial,
        method="L-BFGS-B",
        jac=True,
        options={"maxiter": 2000, "ftol": 1e-8},
    )
    if not result.success:
        raise RuntimeError(f"hazard fit failed: {result.message}")
    return StandardizedLogisticHazard(
        feature_columns=columns,
        mean=mean,
        scale=scale,
        coefficients=np.asarray(result.x, dtype=float),
    )


def predict_death_distributions(
    model: StandardizedLogisticHazard,
    features: pd.DataFrame,
    *,
    maximum_day: int = 60,
) -> pd.DataFrame:
    """Integrate daily hazards into event-level death-time distributions."""
    rows = []
    for event in features.itertuples(index=False):
        snapshot = int(event.snapshot_day)
        maximum_horizon = maximum_day - snapshot
        if maximum_horizon < 1:
            continue
        base = pd.DataFrame([event._asdict()] * maximum_horizon)
        horizons = np.arange(1, maximum_horizon + 1)
        design = add_horizon_features(base, horizons)
        hazard = model.predict_hazard(design)
        survival_before = np.r_[1.0, np.cumprod(1.0 - hazard[:-1])]
        probability = survival_before * hazard
        probability[-1] += max(0.0, 1.0 - probability.sum())
        probability /= probability.sum()
        cdf = np.cumsum(probability)
        days = snapshot + horizons

        def quantile(probability_level: float) -> int:
            return int(days[min(np.searchsorted(cdf, probability_level), len(days) - 1)])

        observed_death = int(event.death_day)
        observed_index = min(max(observed_death - snapshot - 1, 0), len(days) - 1)
        rows.append(
            {
                "id": int(event.id),
                "ig_year": int(event.ig_year),
                "snapshot_day": snapshot,
                "observed_state": str(event.observed_state),
                "observed_death_day": observed_death,
                "predicted_death_day": quantile(0.5),
                "distribution_mean_death_day": float(np.sum(days * probability)),
                "model_interval_lower": quantile(0.05),
                "model_interval_upper": quantile(0.95),
                "observed_death_probability": float(probability[observed_index]),
                "death_log_score": float(-np.log(max(probability[observed_index], 1e-15))),
            }
        )
    result = pd.DataFrame(rows)
    result["error"] = result.predicted_death_day - result.observed_death_day
    return result


def calibrate_logit_shift(
    model: StandardizedLogisticHazard,
    calibration: pd.DataFrame,
    *,
    shifts: Sequence[float] = tuple(np.linspace(-2.0, 2.0, 41)),
) -> tuple[StandardizedLogisticHazard, pd.DataFrame]:
    """Select a global hazard shift using calibration-period death log score."""
    rows = []
    for shift in shifts:
        candidate = model.with_shift(float(shift))
        predictions = predict_death_distributions(candidate, calibration)
        rows.append(
            {
                "logit_shift": float(shift),
                "calibration_log_score": float(predictions.death_log_score.mean()),
                "calibration_mae": float(np.abs(predictions.error).mean()),
            }
        )
    curve = pd.DataFrame(rows)
    selected = curve.loc[curve.calibration_log_score.idxmin()]
    return model.with_shift(float(selected.logit_shift)), curve


def conformal_interval_radius(
    predictions: pd.DataFrame, *, coverage: float = 0.9
) -> float:
    """Return a finite-sample split-conformal absolute-error radius."""
    if not 0 < coverage < 1 or predictions.empty:
        raise ValueError("coverage must be in (0, 1) and predictions cannot be empty")
    scores = np.sort(np.abs(predictions.error.to_numpy(dtype=float)))
    rank = int(np.ceil((len(scores) + 1) * coverage)) - 1
    return float(scores[min(rank, len(scores) - 1)])


def add_conformal_intervals(
    predictions: pd.DataFrame,
    radius: float,
    *,
    maximum_day: int = 60,
) -> pd.DataFrame:
    """Attach calibrated symmetric intervals around median death forecasts."""
    result = predictions.copy()
    result["interval_lower"] = np.maximum(
        result.snapshot_day + 1, result.predicted_death_day - radius
    )
    result["interval_upper"] = np.minimum(
        maximum_day, result.predicted_death_day + radius
    )
    return result
