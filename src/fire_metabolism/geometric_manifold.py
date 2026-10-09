"""Longitudinal perimeter-area scaling utilities.

The functions here distinguish pooled, between-fire, and within-fire
estimands. Uncertainty resamples whole fires, preserving the dependence among
repeated daily observations from the same FIRED event.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar


DEFAULT_SEED = 20261009
REFERENCES = (0.5, 2.0 / 3.0, 0.75)


def temporal_partition(year: pd.Series) -> pd.Series:
    """Apply the locked development/calibration/held-out split."""
    return pd.Series(
        np.select(
            [year <= 2012, year.between(2013, 2015), year.between(2016, 2020)],
            ["development", "calibration", "held_out"],
            default="excluded",
        ),
        index=year.index,
    )


def prepare_geometry_panel(
    sequences: pd.DataFrame,
    geometry: pd.DataFrame,
    *,
    perimeter_column: str = "exterior_perimeter_km",
    stride: int = 1,
) -> pd.DataFrame:
    """Join positive-increment geometry observations and add log coordinates."""
    columns = [
        "id", "event_day", "polygon_area_km2", "total_perimeter_km",
        "exterior_perimeter_km", "component_count", "hole_count",
    ]
    missing = set(columns).difference(geometry.columns)
    if missing:
        raise ValueError(f"missing geometry columns: {sorted(missing)}")
    panel = sequences.merge(
        geometry[columns], on=["id", "event_day"], how="inner", validate="one_to_one"
    )
    panel = panel[
        (panel.daily_area_km2 > 0)
        & (panel.cumulative_area_km2 > 0)
        & (panel[perimeter_column] > 0)
    ].copy()
    panel = panel.sort_values(["id", "event_day"])
    if stride > 1:
        panel = panel[panel.groupby("id", sort=False).cumcount().mod(stride).eq(0)]
    panel["perimeter_km"] = panel[perimeter_column]
    panel["perimeter_definition"] = perimeter_column.replace("_perimeter_km", "")
    panel["log_area"] = np.log(panel.cumulative_area_km2)
    panel["log_perimeter"] = np.log(panel.perimeter_km)
    panel["partition"] = temporal_partition(panel.ig_year)
    panel["event_mean_log_area"] = panel.groupby("id").log_area.transform("mean")
    panel["within_log_area"] = panel.log_area - panel.event_mean_log_area
    panel["event_mean_log_perimeter"] = panel.groupby("id").log_perimeter.transform("mean")
    return panel.reset_index(drop=True)


def _slope_from_sums(stats: np.ndarray) -> float:
    n, sx, sy, sxx, sxy = stats
    denominator = sxx - sx * sx / n
    return float((sxy - sx * sy / n) / denominator) if denominator > 0 else np.nan


def _event_sufficient_statistics(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for event_id, frame in panel.groupby("id", sort=False):
        x = frame.log_area.to_numpy(dtype=float)
        y = frame.log_perimeter.to_numpy(dtype=float)
        xc = x - x.mean()
        yc = y - y.mean()
        rows.append({
            "id": int(event_id),
            "n": len(frame),
            "sx": x.sum(), "sy": y.sum(),
            "sxx": np.dot(x, x), "sxy": np.dot(x, y),
            "within_sxx": np.dot(xc, xc),
            "within_sxy": np.dot(xc, yc),
            "mean_x": x.mean(), "mean_y": y.mean(),
        })
    return pd.DataFrame(rows)


def scaling_estimates(panel: pd.DataFrame) -> dict[str, float]:
    """Estimate pooled, within-fire, and weighted between-fire slopes."""
    stats = _event_sufficient_statistics(panel)
    pooled = _slope_from_sums(
        stats[["n", "sx", "sy", "sxx", "sxy"]].sum().to_numpy(dtype=float)
    )
    within = float(stats.within_sxy.sum() / stats.within_sxx.sum())
    between = _slope_from_sums(np.array([
        stats.n.sum(),
        np.dot(stats.n, stats.mean_x),
        np.dot(stats.n, stats.mean_y),
        np.dot(stats.n, stats.mean_x**2),
        np.dot(stats.n, stats.mean_x * stats.mean_y),
    ]))
    unweighted_between = float(np.polyfit(stats.mean_x, stats.mean_y, 1)[0])
    return {
        "population": pooled,
        "within": within,
        "between": between,
        "between_unweighted": unweighted_between,
    }


def bootstrap_scaling(
    panel: pd.DataFrame,
    *,
    replicates: int = 1000,
    seed: int = DEFAULT_SEED,
) -> pd.DataFrame:
    """Whole-fire bootstrap intervals for the three scaling estimands."""
    stats = _event_sufficient_statistics(panel)
    arrays = stats[
        ["n", "sx", "sy", "sxx", "sxy", "within_sxx", "within_sxy", "mean_x", "mean_y"]
    ].to_numpy(dtype=float)
    generator = np.random.default_rng(seed)
    draws = {"population": [], "within": [], "between": [], "between_unweighted": []}
    for _ in range(replicates):
        selected = arrays[generator.integers(0, len(arrays), len(arrays))]
        totals = selected[:, :5].sum(axis=0)
        draws["population"].append(_slope_from_sums(totals))
        draws["within"].append(selected[:, 6].sum() / selected[:, 5].sum())
        n = selected[:, 0]
        mx, my = selected[:, 7], selected[:, 8]
        draws["between"].append(_slope_from_sums(np.array([
            n.sum(), np.dot(n, mx), np.dot(n, my), np.dot(n, mx * mx), np.dot(n, mx * my)
        ])))
        draws["between_unweighted"].append(_slope_from_sums(np.array([
            len(mx), mx.sum(), my.sum(), np.dot(mx, mx), np.dot(mx, my)
        ])))
    point = scaling_estimates(panel)
    rows = []
    for estimand, values in draws.items():
        values = np.asarray(values, dtype=float)
        rows.append({
            "estimand": estimand,
            "estimate": point[estimand],
            "ci95_lower": float(np.nanquantile(values, 0.025)),
            "ci95_upper": float(np.nanquantile(values, 0.975)),
            "bootstrap_sd": float(np.nanstd(values, ddof=1)),
            "bootstrap_replicates": int(replicates),
        })
    return pd.DataFrame(rows)


def fire_specific_slopes(
    panel: pd.DataFrame,
    *,
    min_observations: int = 7,
    min_log_area_span: float = np.log(2.0),
    min_duration_days: int = 7,
) -> pd.DataFrame:
    """Estimate eligible event-specific longitudinal slopes and covariance."""
    rows = []
    global_center = float(panel.log_area.median())
    for event_id, frame in panel.groupby("id", sort=False):
        frame = frame.sort_values("event_day")
        x = frame.log_area.to_numpy(dtype=float)
        y = frame.log_perimeter.to_numpy(dtype=float)
        duration = int(frame.event_day.max() - frame.event_day.min() + 1)
        span = float(np.ptp(x))
        eligible = len(frame) >= min_observations and span >= min_log_area_span and duration >= min_duration_days
        if len(frame) < 3 or np.ptp(x) <= 1e-12:
            continue
        xc = x - global_center
        design = np.column_stack([np.ones(len(x)), xc])
        beta, *_ = np.linalg.lstsq(design, y, rcond=None)
        residual = y - design @ beta
        sse = float(np.dot(residual, residual))
        covariance = (sse / max(len(x) - 2, 1)) * np.linalg.inv(design.T @ design)
        slope_se = float(np.sqrt(max(covariance[1, 1], 0.0)))
        rows.append({
            "id": int(event_id), "ig_year": int(frame.ig_year.iloc[0]),
            "partition": str(frame.partition.iloc[0]), "eligible": bool(eligible),
            "perimeter_definition": str(frame.perimeter_definition.iloc[0]) if "perimeter_definition" in frame else "unspecified",
            "n_observations": int(len(frame)), "duration_days": duration,
            "log_area_span": span, "initial_area_km2": float(frame.cumulative_area_km2.iloc[0]),
            "maximum_observed_area_km2": float(frame.cumulative_area_km2.max()),
            "mean_area_km2": float(frame.cumulative_area_km2.mean()),
            "intercept_at_global_center": float(beta[0]), "slope": float(beta[1]),
            "slope_se": slope_se, "ci95_lower": float(beta[1] - 1.96 * slope_se),
            "ci95_upper": float(beta[1] + 1.96 * slope_se),
            "rmse_log": float(np.sqrt(sse / len(x))), "r_squared": float(1 - sse / np.dot(y-y.mean(), y-y.mean())) if np.ptp(y)>0 else np.nan,
            "cov_intercept": float(covariance[0, 0]), "cov_intercept_slope": float(covariance[0, 1]),
            "cov_slope": float(covariance[1, 1]), "global_log_area_center": global_center,
        })
    return pd.DataFrame(rows)


def fit_random_slope_meta(fits: pd.DataFrame) -> dict[str, float | str]:
    """Fit a two-stage Gaussian random-intercept/random-slope model by ML.

    Per-fire OLS coefficient covariance is retained as known sampling error.
    The latent coefficient vector follows a bivariate normal distribution.
    This is a hierarchical meta-analytic implementation, not a fixed-effect
    model with an absorbed between-fire predictor.
    """
    data = fits[fits.eligible].dropna(subset=["intercept_at_global_center", "slope"])
    estimates = data[["intercept_at_global_center", "slope"]].to_numpy(dtype=float)
    sampling = np.zeros((len(data), 2, 2), dtype=float)
    sampling[:, 0, 0] = data.cov_intercept
    sampling[:, 0, 1] = sampling[:, 1, 0] = data.cov_intercept_slope
    sampling[:, 1, 1] = data.cov_slope

    def unpack(theta: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        mean = theta[:2]
        lower = np.array([[np.exp(theta[2]), 0.0], [theta[3], np.exp(theta[4])]])
        return mean, lower @ lower.T

    def objective(theta: np.ndarray) -> float:
        mean, variance = unpack(theta)
        total = 0.0
        for estimate, sample_var in zip(estimates, sampling, strict=True):
            covariance = variance + sample_var + np.eye(2) * 1e-10
            sign, logdet = np.linalg.slogdet(covariance)
            if sign <= 0:
                return 1e30
            delta = estimate - mean
            total += 0.5 * (logdet + delta @ np.linalg.solve(covariance, delta))
        return total

    empirical = np.cov(estimates.T)
    start = np.array([
        estimates[:, 0].mean(), estimates[:, 1].mean(),
        np.log(max(np.sqrt(empirical[0, 0]), 1e-3)), 0.0,
        np.log(max(np.sqrt(empirical[1, 1]), 1e-3)),
    ])
    result = minimize(objective, start, method="L-BFGS-B")
    mean, variance = unpack(result.x)
    correlation = variance[0, 1] / np.sqrt(variance[0, 0] * variance[1, 1])
    mean_precision = np.zeros((2, 2), dtype=float)
    for sample_var in sampling:
        mean_precision += np.linalg.inv(variance + sample_var + np.eye(2) * 1e-10)
    mean_covariance = np.linalg.inv(mean_precision)
    mean_slope_se = float(np.sqrt(mean_covariance[1, 1]))
    return {
        "method": "two_stage_bivariate_gaussian_random_effects_ml",
        "converged": bool(result.success), "optimizer_message": str(result.message),
        "n_fires": int(len(data)), "mean_intercept": float(mean[0]),
        "mean_slope": float(mean[1]), "intercept_variance": float(variance[0, 0]),
        "mean_slope_se": mean_slope_se,
        "mean_slope_ci95_lower": float(mean[1] - 1.96 * mean_slope_se),
        "mean_slope_ci95_upper": float(mean[1] + 1.96 * mean_slope_se),
        "slope_variance": float(variance[1, 1]),
        "intercept_slope_covariance": float(variance[0, 1]),
        "intercept_slope_correlation": float(correlation),
        "negative_log_likelihood": float(result.fun),
    }


def candidate_normalization_slopes(panel: pd.DataFrame, candidates: Iterable[float]) -> pd.DataFrame:
    """Test within-fire drift in Z_sigma for candidate exponents."""
    within = scaling_estimates(panel)["within"]
    rows = []
    for sigma in candidates:
        observed = within - float(sigma)
        expected_if_two_thirds = (2.0 / 3.0) - float(sigma)
        rows.append({
            "candidate_exponent": float(sigma),
            "within_normalization_drift": observed,
            "expected_drift_if_true_two_thirds": expected_if_two_thirds,
            "difference_from_two_thirds_prediction": observed - expected_if_two_thirds,
        })
    return pd.DataFrame(rows)


def measurement_error_slopes(panel: pd.DataFrame) -> dict[str, float]:
    """Return conditional OLS, SMA, and unit-ratio Deming sensitivities."""
    x = panel.log_area - panel.groupby("id").log_area.transform("mean")
    y = panel.log_perimeter - panel.groupby("id").log_perimeter.transform("mean")
    x = x.to_numpy(dtype=float)
    y = y.to_numpy(dtype=float)
    sxx, syy, sxy = np.dot(x, x), np.dot(y, y), np.dot(x, y)
    ols = sxy / sxx
    sma = np.sign(sxy) * np.sqrt(syy / sxx)
    deming = (syy - sxx + np.sqrt((syy - sxx) ** 2 + 4 * sxy**2)) / (2 * sxy)
    return {"ols_conditional": float(ols), "sma_symmetric": float(sma), "deming_lambda_1": float(deming)}


def original_scale_profile(panel: pd.DataFrame, bounds: tuple[float, float] = (0.2, 1.1)) -> dict[str, float]:
    """Profile event prefactors for additive-error original-scale power law."""
    groups = [
        (frame.cumulative_area_km2.to_numpy(dtype=float), frame.perimeter_km.to_numpy(dtype=float))
        for _, frame in panel.groupby("id", sort=False)
    ]

    def sse(sigma: float) -> float:
        total = 0.0
        for area, perimeter in groups:
            basis = area**sigma
            coefficient = np.dot(perimeter, basis) / np.dot(basis, basis)
            residual = perimeter - coefficient * basis
            total += float(np.dot(residual, residual))
        return total

    result = minimize_scalar(sse, bounds=bounds, method="bounded")
    return {"exponent": float(result.x), "sse": float(result.fun), "converged": bool(result.success)}


def polynomial_within_fit(panel: pd.DataFrame, degree: int) -> np.ndarray:
    """Fit a within-fire polynomial after demeaning every basis column."""
    x = panel.log_area.to_numpy(dtype=float)
    y = panel.log_perimeter.to_numpy(dtype=float)
    event = panel.id.to_numpy()
    basis = np.column_stack([x**power for power in range(1, degree + 1)])
    centered = basis.copy()
    yc = y.copy()
    for event_id in np.unique(event):
        mask = event == event_id
        centered[mask] -= basis[mask].mean(axis=0)
        yc[mask] -= y[mask].mean()
    return np.linalg.lstsq(centered, yc, rcond=None)[0]


def anchored_prediction_error(panel: pd.DataFrame, coefficients: Sequence[float]) -> dict[str, float]:
    """Predict each held-out trajectory after anchoring only its first point."""
    coefficients = np.asarray(coefficients, dtype=float)
    errors = []
    for _, frame in panel.groupby("id", sort=False):
        frame = frame.sort_values("event_day")
        if len(frame) < 2:
            continue
        x = frame.log_area.to_numpy(dtype=float)
        y = frame.log_perimeter.to_numpy(dtype=float)
        basis = np.column_stack([x**power for power in range(1, len(coefficients) + 1)])
        shape = basis @ coefficients
        intercept = y[0] - shape[0]
        errors.extend(y[1:] - (intercept + shape[1:]))
    error = np.asarray(errors, dtype=float)
    return {
        "n_predictions": int(len(error)), "mae_log": float(np.mean(np.abs(error))),
        "rmse_log": float(np.sqrt(np.mean(error**2))),
    }


def fit_ridge(train: pd.DataFrame, target: str, features: Sequence[str], alpha: float = 1.0) -> dict[str, np.ndarray | tuple[str, ...]]:
    """Dependency-free standardized ridge model."""
    columns = tuple(features)
    x = train.loc[:, columns].to_numpy(dtype=float)
    y = train[target].to_numpy(dtype=float)
    mean = np.nanmean(x, axis=0)
    x = np.where(np.isfinite(x), x, mean)
    scale = np.nanstd(x, axis=0)
    scale[scale < 1e-12] = 1.0
    design = np.column_stack([np.ones(len(x)), (x - mean) / scale])
    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0.0
    coefficient = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return {"features": columns, "mean": mean, "scale": scale, "coefficient": coefficient}


def predict_ridge(model: dict[str, np.ndarray | tuple[str, ...]], frame: pd.DataFrame) -> np.ndarray:
    columns = model["features"]
    x = frame.loc[:, columns].to_numpy(dtype=float)
    x = np.where(np.isfinite(x), x, model["mean"])
    design = np.column_stack([np.ones(len(x)), (x - model["mean"]) / model["scale"]])
    return design @ model["coefficient"]
