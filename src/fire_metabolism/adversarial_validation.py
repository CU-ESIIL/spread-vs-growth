"""Adversarial detection and prediction utilities for FIRED analyses.

The functions in this module deliberately separate geometric pattern
detection from dynamical prediction and mechanistic identification. They use
only origin-time information in fitted predictors and resample whole events
for uncertainty estimates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from .fired_outcomes import BASE_FEATURE_COLUMNS, fit_standardized_ridge
from .fired_prediction import transformed_trend_forecast
from .fired_survival import fit_logistic_hazard


DEFAULT_SEED = 20261008
TRAJECTORY_PREDICTORS = (
    "log_recent_beta_two_thirds",
    "log_recent_beta_one_half",
    "recent_beta_trend",
    "recent_growth_acceleration",
    "latest_growth_fraction_of_peak",
    "days_since_observed_peak",
    "days_since_last_detected_growth",
    "recent_active_fraction",
    "smoothed_growth_curvature",
    "recent_to_previous_growth_ratio",
)
GEOMETRY_PREDICTORS = (
    "log_total_perimeter",
    "log_exterior_perimeter",
    "log_total_excess_perimeter",
    "log_exterior_excess_perimeter",
    "total_perimeter_area_slope",
    "exterior_perimeter_area_slope",
    "log_recent_boundary_speed",
    "log_component_count",
    "log1p_hole_count",
    "recent_log_total_perimeter_change",
    "recent_log_exterior_perimeter_change",
    "recent_component_change",
    "recent_hole_change",
    "log_area_per_component",
)
AREA_PREDICTORS = tuple(BASE_FEATURE_COLUMNS)
DYNAMICS_PREDICTORS = AREA_PREDICTORS + TRAJECTORY_PREDICTORS
AREA_GEOMETRY_PREDICTORS = DYNAMICS_PREDICTORS + GEOMETRY_PREDICTORS
WEATHER_PREDICTORS = (
    "recent_vpd_kpa",
    "vpd_change_from_prior",
    "recent_wind_speed_m_s",
    "wind_change_from_prior",
    "recent_fuel_moisture_100hr_pct",
    "fuel_moisture_change_from_prior",
    "recent_energy_release_component",
    "erc_change_from_prior",
    "log1p_recent_precipitation_mm",
    "precipitation_change_from_prior",
)
ACTIVE_FRONT_PREDICTORS = (
    "log_recent_new_exterior_perimeter",
    "log_recent_new_boundary_efficiency",
    "recent_new_to_cumulative_perimeter",
    "log_recent_daily_component_count",
    "recent_new_perimeter_trend",
)


@dataclass(frozen=True)
class LogLogFit:
    """Ordinary least-squares fit for a log perimeter-area trajectory."""

    n: int
    intercept: float
    slope: float
    slope_se: float
    ci_lower: float
    ci_upper: float
    log_area_span: float
    rmse: float
    sse_half: float
    sse_two_thirds: float
    sse_free: float


def fit_loglog_scaling(area: Sequence[float], perimeter: Sequence[float]) -> LogLogFit:
    """Fit a free slope and score fixed one-half and two-thirds alternatives."""
    area_values = np.asarray(area, dtype=float)
    perimeter_values = np.asarray(perimeter, dtype=float)
    keep = (
        np.isfinite(area_values)
        & np.isfinite(perimeter_values)
        & (area_values > 0)
        & (perimeter_values > 0)
    )
    x = np.log(area_values[keep])
    y = np.log(perimeter_values[keep])
    if len(x) < 3 or np.ptp(x) < 1e-10:
        raise ValueError("at least three distinct positive observations are required")
    design = np.column_stack([np.ones(len(x)), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coefficients
    residual = y - fitted
    sse_free = float(np.dot(residual, residual))
    centered = x - x.mean()
    residual_variance = sse_free / max(len(x) - 2, 1)
    slope_se = float(np.sqrt(residual_variance / np.dot(centered, centered)))

    def fixed_sse(sigma: float) -> float:
        intercept = float(np.mean(y - sigma * x))
        error = y - (intercept + sigma * x)
        return float(np.dot(error, error))

    return LogLogFit(
        n=int(len(x)),
        intercept=float(coefficients[0]),
        slope=float(coefficients[1]),
        slope_se=slope_se,
        ci_lower=float(coefficients[1] - 1.96 * slope_se),
        ci_upper=float(coefficients[1] + 1.96 * slope_se),
        log_area_span=float(np.ptp(x)),
        rmse=float(np.sqrt(sse_free / len(x))),
        sse_half=fixed_sse(0.5),
        sse_two_thirds=fixed_sse(2.0 / 3.0),
        sse_free=sse_free,
    )


def _fit_detection_variant(
    history: pd.DataFrame,
    *,
    perimeter_column: str,
    stride: int,
) -> dict[str, float | int | bool]:
    sampled = history.iloc[::stride]
    if len(sampled) < 4:
        return {
            "n": int(len(sampled)),
            "slope": np.nan,
            "slope_se": np.nan,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "log_area_span": np.nan,
            "rmse": np.nan,
            "sse_half": np.nan,
            "sse_two_thirds": np.nan,
            "sse_free": np.nan,
            "detected": False,
        }
    try:
        fit = fit_loglog_scaling(
            sampled["cumulative_area_km2"], sampled[perimeter_column]
        )
    except ValueError:
        return {
            "n": int(len(sampled)),
            "slope": np.nan,
            "slope_se": np.nan,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "log_area_span": np.nan,
            "rmse": np.nan,
            "sse_half": np.nan,
            "sse_two_thirds": np.nan,
            "sse_free": np.nan,
            "detected": False,
        }
    detected = bool(
        fit.n >= 5
        and fit.log_area_span >= np.log(2.0)
        and fit.ci_lower <= 2.0 / 3.0 <= fit.ci_upper
        and fit.sse_two_thirds <= fit.sse_half
    )
    return {**fit.__dict__, "detected": detected}


def geometric_detection_table(
    sequences_with_geometry: pd.DataFrame,
    *,
    snapshot_days: Iterable[int] = (5, 7, 10, 14, 21),
) -> pd.DataFrame:
    """Create uncertainty-aware geometric indicators at fixed snapshots.

    Only positive mapped-increment days are used as distinct polygon
    observations. Primary detection uses exterior perimeter; total perimeter
    and every-other-observation fits are stability checks.
    """
    required = {
        "id",
        "ig_year",
        "event_day",
        "daily_area_km2",
        "cumulative_area_km2",
        "total_perimeter_km",
        "exterior_perimeter_km",
        "component_count",
        "hole_count",
    }
    if missing := required.difference(sequences_with_geometry.columns):
        raise ValueError(f"missing detection columns: {sorted(missing)}")
    snapshots = tuple(sorted({int(day) for day in snapshot_days}))
    rows: list[dict[str, object]] = []
    for event_id, event in sequences_with_geometry.groupby("id", sort=False):
        event = event.sort_values("event_day")
        observed = event[event.daily_area_km2 > 0]
        for snapshot in snapshots:
            history = observed[observed.event_day <= snapshot]
            if int(event.event_day.max()) <= snapshot or len(history) < 4:
                continue
            primary = _fit_detection_variant(
                history, perimeter_column="exterior_perimeter_km", stride=1
            )
            total = _fit_detection_variant(
                history, perimeter_column="total_perimeter_km", stride=1
            )
            thinned = _fit_detection_variant(
                history, perimeter_column="exterior_perimeter_km", stride=2
            )
            rows.append(
                {
                    "id": int(event_id),
                    "ig_year": int(event.ig_year.iloc[0]),
                    "snapshot_day": snapshot,
                    **{f"exterior_{key}": value for key, value in primary.items()},
                    **{f"total_{key}": value for key, value in total.items()},
                    **{f"thinned_{key}": value for key, value in thinned.items()},
                    "component_count": float(history.component_count.iloc[-1]),
                    "hole_count": float(history.hole_count.iloc[-1]),
                    "snapshot_area_km2": float(history.cumulative_area_km2.iloc[-1]),
                }
            )
    result = pd.DataFrame(rows).sort_values(["id", "snapshot_day"])
    if result.empty:
        raise ValueError("no geometric windows met the minimum observation count")
    previous = result.groupby("id", sort=False).exterior_detected.shift(1).fillna(False)
    result["persistent_detection"] = result.exterior_detected & previous
    available = result[["exterior_detected", "total_detected", "thinned_detected"]]
    result["variant_agreement"] = available.mean(axis=1)
    return result.reset_index(drop=True)


def attach_future_dynamics(
    features: pd.DataFrame,
    sequences: pd.DataFrame,
    *,
    horizon: int,
) -> pd.DataFrame:
    """Attach future growth and acceleration targets to snapshot features."""
    if horizon < 1:
        raise ValueError("horizon must be positive")
    lookup = {
        int(event_id): event.sort_values("event_day")
        for event_id, event in sequences.groupby("id", sort=False)
    }
    rows = []
    for row in features.itertuples(index=False):
        event = lookup.get(int(row.id))
        snapshot = int(row.snapshot_day)
        if event is None or int(event.event_day.max()) < snapshot + horizon:
            continue
        daily = event.daily_area_km2.to_numpy(dtype=float)
        cumulative = event.cumulative_area_km2.to_numpy(dtype=float)
        past = daily[max(0, snapshot - 3) : snapshot]
        future = daily[snapshot : snapshot + horizon]
        future_area = float(cumulative[snapshot + horizon - 1])
        origin_area = float(cumulative[snapshot - 1])
        rows.append(
            {
                "id": int(row.id),
                "snapshot_day": snapshot,
                "horizon_days": int(horizon),
                "origin_area_km2": origin_area,
                "future_area_km2": future_area,
                "future_increment_km2": future_area - origin_area,
                "past_mean_growth": float(np.mean(past)),
                "future_mean_growth": float(np.mean(future)),
                "future_accelerating": bool(np.mean(future) > np.mean(past)),
            }
        )
    targets = pd.DataFrame(rows)
    if targets.empty:
        raise ValueError("no snapshot rows have the requested future horizon")
    return features.merge(
        targets,
        on=["id", "snapshot_day"],
        how="inner",
        validate="one_to_one",
    )


def add_quadratic_features(
    frame: pd.DataFrame, columns: Sequence[str]
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    """Add a fixed nonlinear basis using no information beyond ``columns``."""
    result = frame.copy()
    expanded = list(columns)
    for column in columns:
        name = f"quad__{column}"
        result[name] = result[column].to_numpy(dtype=float) ** 2
        expanded.append(name)
    for first, second in zip(columns[:-1], columns[1:], strict=True):
        name = f"interaction__{first}__{second}"
        result[name] = (
            result[first].to_numpy(dtype=float)
            * result[second].to_numpy(dtype=float)
        )
        expanded.append(name)
    return result, tuple(expanded)


def tune_ridge_alpha(
    development: pd.DataFrame,
    calibration: pd.DataFrame,
    *,
    target_column: str,
    feature_columns: Sequence[str],
    alphas: Sequence[float] = (0.1, 1.0, 10.0, 100.0, 1000.0),
) -> tuple[object, pd.DataFrame]:
    """Select regularization on calibration absolute error and refit on development."""
    y_development = development[target_column].to_numpy(dtype=float)
    y_calibration = calibration[target_column].to_numpy(dtype=float)
    rows = []
    models = {}
    for alpha in alphas:
        model = fit_standardized_ridge(
            development,
            y_development,
            feature_columns=feature_columns,
            alpha=float(alpha),
        )
        error = np.abs(model.predict(calibration) - y_calibration)
        rows.append({"alpha": float(alpha), "calibration_mae": float(error.mean())})
        models[float(alpha)] = model
    curve = pd.DataFrame(rows)
    selected = float(curve.loc[curve.calibration_mae.idxmin(), "alpha"])
    curve["selected"] = curve.alpha == selected
    return models[selected], curve


def tune_binary_model(
    development: pd.DataFrame,
    calibration: pd.DataFrame,
    *,
    target_column: str,
    feature_columns: Sequence[str],
    alphas: Sequence[float] = (0.1, 1.0, 10.0, 100.0),
) -> tuple[object, float, pd.DataFrame]:
    """Tune a ridge-logistic model and decision threshold without held-out data."""
    train = development.copy()
    train["terminal_transition"] = train[target_column].astype(float)
    observed = calibration[target_column].to_numpy(dtype=bool)
    rows = []
    models = {}
    for alpha in alphas:
        model = fit_logistic_hazard(
            train, feature_columns=feature_columns, alpha=float(alpha)
        )
        probability = model.predict_hazard(calibration)
        brier = float(np.mean((probability - observed) ** 2))
        rows.append({"alpha": float(alpha), "calibration_brier": brier})
        models[float(alpha)] = model
    curve = pd.DataFrame(rows)
    selected = float(curve.loc[curve.calibration_brier.idxmin(), "alpha"])
    model = models[selected]
    probability = model.predict_hazard(calibration)
    threshold_rows = []
    for threshold in np.linspace(0.1, 0.9, 33):
        metrics = binary_metrics(observed, probability >= threshold)
        threshold_rows.append(
            {"threshold": float(threshold), "balanced_accuracy": metrics["balanced_accuracy"]}
        )
    thresholds = pd.DataFrame(threshold_rows)
    threshold = float(
        thresholds.loc[thresholds.balanced_accuracy.idxmax(), "threshold"]
    )
    curve["selected"] = curve.alpha == selected
    curve["decision_threshold"] = threshold
    return model, threshold, curve


def binary_metrics(observed: Sequence[bool], predicted: Sequence[bool]) -> dict[str, float]:
    """Return confusion-derived binary scores with explicit zero handling."""
    truth = np.asarray(observed, dtype=bool)
    estimate = np.asarray(predicted, dtype=bool)
    if truth.shape != estimate.shape or truth.ndim != 1:
        raise ValueError("binary inputs must be matching one-dimensional arrays")
    tp = int(np.sum(truth & estimate))
    tn = int(np.sum(~truth & ~estimate))
    fp = int(np.sum(~truth & estimate))
    fn = int(np.sum(truth & ~estimate))
    sensitivity = tp / (tp + fn) if tp + fn else np.nan
    specificity = tn / (tn + fp) if tn + fp else np.nan
    precision = tp / (tp + fp) if tp + fp else np.nan
    return {
        "tp": float(tp),
        "tn": float(tn),
        "fp": float(fp),
        "fn": float(fn),
        "sensitivity": float(sensitivity),
        "specificity": float(specificity),
        "false_positive_rate": float(1 - specificity),
        "false_negative_rate": float(1 - sensitivity),
        "precision": float(precision),
        "recall": float(sensitivity),
        "balanced_accuracy": float((sensitivity + specificity) / 2),
    }


def regression_metrics(observed: Sequence[float], predicted: Sequence[float]) -> dict[str, float]:
    """Return paired continuous forecast scores."""
    truth = np.asarray(observed, dtype=float)
    estimate = np.asarray(predicted, dtype=float)
    if truth.shape != estimate.shape or truth.ndim != 1:
        raise ValueError("regression inputs must be matching one-dimensional arrays")
    error = estimate - truth
    denominator = np.maximum(np.abs(truth) + np.abs(estimate), 1e-12)
    return {
        "n": float(len(truth)),
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "bias": float(np.mean(error)),
        "mean_absolute_log_error": float(
            np.mean(np.abs(np.log(np.maximum(estimate, 1e-12) / np.maximum(truth, 1e-12))))
        ),
        "smape": float(np.mean(2 * np.abs(error) / denominator)),
    }


def paired_event_bootstrap(
    frame: pd.DataFrame,
    *,
    first_error: str,
    second_error: str,
    replicates: int = 2000,
    seed: int = DEFAULT_SEED,
) -> dict[str, float]:
    """Bootstrap the paired mean error difference by whole event."""
    event = frame.groupby("id", as_index=False)[[first_error, second_error]].mean()
    difference = event[first_error].to_numpy() - event[second_error].to_numpy()
    generator = np.random.default_rng(seed)
    draws = generator.choice(difference, size=(replicates, len(difference)), replace=True)
    means = draws.mean(axis=1)
    return {
        "n_events": float(len(event)),
        "mean_difference": float(difference.mean()),
        "ci95_lower": float(np.quantile(means, 0.025)),
        "ci95_upper": float(np.quantile(means, 0.975)),
        "probability_first_better": float(np.mean(means < 0)),
    }


def transformed_forecasts(
    frame: pd.DataFrame,
    sequences: pd.DataFrame,
    *,
    sigma: float,
    lookback: int | None = None,
) -> np.ndarray:
    """Forecast each snapshot from its own pre-origin cumulative-area history."""
    lookup = {
        int(event_id): event.sort_values("event_day")
        for event_id, event in sequences.groupby("id", sort=False)
    }
    predictions = []
    for row in frame.itertuples(index=False):
        event = lookup[int(row.id)]
        snapshot = int(row.snapshot_day)
        history = event.cumulative_area_km2.to_numpy(dtype=float)[:snapshot]
        if lookback is not None:
            history = history[-lookback:]
        predictions.append(
            transformed_trend_forecast(history, int(row.horizon_days), sigma)
        )
    return np.asarray(predictions, dtype=float)


def synthetic_counterexamples(seed: int = DEFAULT_SEED) -> pd.DataFrame:
    """Generate negative controls for mechanism and forecast discrimination."""
    generator = np.random.default_rng(seed)
    rows = []
    time = np.arange(1, 25, dtype=float)

    # Exact 2/3 geometry with non-metabolic linear area and no lifecycle peak.
    area = 4.0 + 3.0 * time
    perimeter = 2.5 * area ** (2.0 / 3.0)
    fit = fit_loglog_scaling(area, perimeter)
    rows.append(
        {
            "counterexample": "non_metabolic_two_thirds",
            "slope": fit.slope,
            "detector_accepts_two_thirds": fit.ci_lower <= 2 / 3 <= fit.ci_upper,
            "has_interior_growth_peak": False,
            "mechanism_identified": False,
        }
    )

    # A proposed-style area path whose mapped perimeter is distorted by scale.
    area = (1.0 + 0.35 * time) ** 3
    true_perimeter = 3.0 * area ** (2.0 / 3.0)
    distorted = true_perimeter * area ** (-0.18) * np.exp(generator.normal(0, 0.03, len(area)))
    fit = fit_loglog_scaling(area, distorted)
    rows.append(
        {
            "counterexample": "true_growth_distorted_geometry",
            "slope": fit.slope,
            "detector_accepts_two_thirds": fit.ci_lower <= 2 / 3 <= fit.ci_upper,
            "has_interior_growth_peak": False,
            "mechanism_identified": False,
        }
    )

    # Linear-area process where a linear model should beat two-thirds extrapolation.
    area = 2.0 + 5.0 * time
    history = area[:7]
    observed = area[9]
    linear_prediction = transformed_trend_forecast(history, 3, 0.0)
    two_thirds_prediction = transformed_trend_forecast(history, 3, 2.0 / 3.0)
    rows.append(
        {
            "counterexample": "alternative_succeeds",
            "slope": np.nan,
            "detector_accepts_two_thirds": False,
            "has_interior_growth_peak": False,
            "mechanism_identified": False,
            "linear_absolute_error": abs(linear_prediction - observed),
            "two_thirds_absolute_error": abs(two_thirds_prediction - observed),
        }
    )

    # Same forcing can be generated by swapped coherence and fuel states.
    coherence, fuel = 0.25, 0.8
    forcing = (2 * coherence * fuel / (coherence + fuel)) ** 2
    swapped = (2 * fuel * coherence / (fuel + coherence)) ** 2
    rows.append(
        {
            "counterexample": "latent_state_swap",
            "slope": np.nan,
            "detector_accepts_two_thirds": False,
            "has_interior_growth_peak": False,
            "mechanism_identified": False,
            "forcing_difference": abs(forcing - swapped),
        }
    )
    return pd.DataFrame(rows)
