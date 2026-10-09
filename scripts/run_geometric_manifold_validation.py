#!/usr/bin/env python3
"""Test whether two-thirds is a within-fire or between-fire scaling law."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / "tmp" / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_ROOT / "tmp" / "cache"))

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from fire_metabolism.geometric_attractor import estimate_local_slopes
from fire_metabolism.geometric_manifold import (
    DEFAULT_SEED,
    REFERENCES,
    anchored_prediction_error,
    bootstrap_scaling,
    candidate_normalization_slopes,
    fire_specific_slopes,
    fit_random_slope_meta,
    fit_ridge,
    measurement_error_slopes,
    original_scale_profile,
    polynomial_within_fit,
    predict_ridge,
    prepare_geometry_panel,
    scaling_estimates,
)


COLORS = {"half": "#B52A25", "two_thirds": "#6495ED", "three_quarters": "#2A8C5A", "ink": "#222222"}
MODEL_NAMES = {0.5: "one_half", 2 / 3: "two_thirds", 0.75: "three_quarters"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequences", type=Path, default=Path("outputs/fired_prediction/fired_sequences.csv.gz"))
    parser.add_argument("--geometry", type=Path, default=Path("outputs/fired_lifecycle_prediction/fired_geometry_sequences.csv.gz"))
    parser.add_argument("--local-slopes", type=Path, default=Path("outputs/geometric_attractor_validation/local_slope_estimates.csv.gz"))
    parser.add_argument("--growth-residuals", type=Path, default=Path("outputs/latent_constraint_validation/growth_residuals.parquet"))
    parser.add_argument("--transport", type=Path, default=Path("outputs/integrated_geometry_transport/transport_transition_metrics.parquet"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/geometric_manifold_validation"))
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_table(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def add_reference_columns(frame: pd.DataFrame, estimate_column: str = "estimate") -> pd.DataFrame:
    result = frame.copy()
    for sigma, name in MODEL_NAMES.items():
        result[f"distance_from_{name}"] = result[estimate_column] - sigma
        if {"ci95_lower", "ci95_upper"}.issubset(result.columns):
            result[f"ci_contains_{name}"] = (result.ci95_lower <= sigma) & (result.ci95_upper >= sigma)
    return result


def population_and_within_between(panel: pd.DataFrame, replicates: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    population, decomposition = [], []
    partitions = [("all", panel)] + list(panel.groupby("partition", sort=False))
    for index, (name, frame) in enumerate(partitions):
        boot = bootstrap_scaling(frame, replicates=replicates, seed=DEFAULT_SEED + index * 31)
        boot["partition"] = name
        boot["n_observations"] = len(frame)
        boot["n_fires"] = frame.id.nunique()
        boot["log_area_min"] = frame.log_area.min()
        boot["log_area_max"] = frame.log_area.max()
        boot["log_area_span"] = frame.log_area.max() - frame.log_area.min()
        population.append(boot[boot.estimand.eq("population")])
        decomposition.append(boot[boot.estimand.isin(["within", "between", "between_unweighted"])])
    return add_reference_columns(pd.concat(population, ignore_index=True)), add_reference_columns(pd.concat(decomposition, ignore_index=True))


def random_slope_analysis(fits: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, frame in [("all", fits), ("development", fits[fits.partition.eq("development")]), ("training", fits[fits.partition.isin(["development", "calibration"])]), ("held_out", fits[fits.partition.eq("held_out")])]:
        row = fit_random_slope_meta(frame)
        row["partition"] = name
        rows.append(row)
    return pd.DataFrame(rows)


def random_slope_prediction(panel: pd.DataFrame, model: pd.DataFrame, common_slope: float) -> pd.DataFrame:
    """Compare a common slope with an early-history empirical-Bayes slope."""
    training_model = model[model.partition.eq("training")].iloc[0]
    prior_mean = float(training_model.mean_slope)
    prior_variance = float(training_model.slope_variance)
    errors = {"common_within_slope": [], "random_slope_empirical_bayes": []}
    fires = 0
    for _, frame in panel[panel.partition.eq("held_out")].groupby("id", sort=False):
        frame = frame.sort_values("event_day")
        split = max(4, len(frame) // 2)
        if len(frame) - split < 2 or split < 3:
            continue
        x0 = frame.log_area.to_numpy(dtype=float)[:split]
        y0 = frame.log_perimeter.to_numpy(dtype=float)[:split]
        x1 = frame.log_area.to_numpy(dtype=float)[split:]
        y1 = frame.log_perimeter.to_numpy(dtype=float)[split:]
        early = np.polyfit(x0, y0, 1)
        residual = y0 - (early[1] + early[0] * x0)
        slope_variance = np.dot(residual, residual) / max(split - 2, 1) / np.dot(x0 - x0.mean(), x0 - x0.mean())
        weight = prior_variance / (prior_variance + max(slope_variance, 1e-10))
        eb_slope = weight * early[0] + (1 - weight) * prior_mean
        for name, slope in (("common_within_slope", common_slope), ("random_slope_empirical_bayes", eb_slope)):
            intercept = float(np.mean(y0 - slope * x0))
            errors[name].extend(y1 - (intercept + slope * x1))
        fires += 1
    rows = []
    for name, values in errors.items():
        values = np.asarray(values)
        rows.append({"method": name, "partition": "held_out_prediction", "n_fires": fires, "held_out_prediction_mae_log": np.mean(np.abs(values)), "held_out_prediction_rmse_log": np.sqrt(np.mean(values**2))})
    return pd.DataFrame(rows)


def candidate_tests(within_between: pd.DataFrame, equivalence_half_width: float) -> pd.DataFrame:
    rows = []
    for record in within_between.itertuples(index=False):
        if record.estimand not in {"within", "between"}:
            continue
        for sigma, label in MODEL_NAMES.items():
            distance = float(record.estimate - sigma)
            rows.append({
                "partition": record.partition, "estimand": record.estimand,
                "candidate": label, "candidate_exponent": sigma,
                "estimate": record.estimate, "ci95_lower": record.ci95_lower,
                "ci95_upper": record.ci95_upper, "distance": distance,
                "ci_contains_candidate": bool(record.ci95_lower <= sigma <= record.ci95_upper),
                "practically_equivalent": bool(abs(distance) <= equivalence_half_width),
                "equivalence_half_width": equivalence_half_width,
            })
    return pd.DataFrame(rows)


def heterogeneity_and_lifecycle(panel: pd.DataFrame, fits: pd.DataFrame) -> pd.DataFrame:
    eligible = fits[fits.eligible].copy()
    predictors = {
        "log_characteristic_area": np.log(eligible.mean_area_km2),
        "log_maximum_area_retrospective": np.log(eligible.maximum_observed_area_km2),
        "duration_days_retrospective": eligible.duration_days,
        "n_observations": eligible.n_observations,
        "log_initial_area": np.log(eligible.initial_area_km2),
        "mean_observation_spacing": eligible.duration_days / np.maximum(eligible.n_observations - 1, 1),
    }
    rows = []
    for partition in ("development", "calibration", "held_out"):
        mask = eligible.partition.eq(partition)
        y = eligible.loc[mask, "slope"].to_numpy(dtype=float)
        for name, values in predictors.items():
            x = np.asarray(values[mask], dtype=float)
            coefficient = np.polyfit(x, y, 1)[0]
            rho, pvalue = spearmanr(x, y)
            rows.append({"analysis": "slope_heterogeneity", "partition": partition, "predictor": name, "coefficient": coefficient, "spearman_rho": rho, "spearman_p": pvalue, "n_fires": len(y)})
    phase = panel.copy()
    phase["relative_age"] = phase.event_day / phase.groupby("id").event_day.transform("max")
    phase["lifecycle_phase"] = pd.cut(phase.relative_age, [0, 1/3, 2/3, 1.01], labels=["early", "middle", "late"], include_lowest=True)
    for (partition, lifecycle), frame in phase.groupby(["partition", "lifecycle_phase"], observed=True):
        if frame.id.nunique() < 20:
            continue
        estimate = scaling_estimates(frame)["within"]
        rows.append({"analysis": "phase_specific_within_slope", "partition": partition, "predictor": str(lifecycle), "coefficient": estimate, "spearman_rho": np.nan, "spearman_p": np.nan, "n_fires": frame.id.nunique()})
    return pd.DataFrame(rows)


def powerlaw_adequacy(panel: pd.DataFrame) -> pd.DataFrame:
    development = panel[panel.partition.eq("development")]
    held = panel[panel.partition.eq("held_out")]
    free = scaling_estimates(development)["within"]
    specs = [("fixed_one_half", np.array([0.5])), ("fixed_two_thirds", np.array([2/3])), ("fixed_three_quarters", np.array([0.75])), ("development_fixed", np.array([free]))]
    for degree in (2, 3):
        specs.append((f"within_polynomial_degree_{degree}", polynomial_within_fit(development, degree)))
    rows = []
    for name, coefficient in specs:
        score = anchored_prediction_error(held, coefficient)
        rows.append({"model": name, "degree": len(coefficient), "coefficients": json.dumps(coefficient.tolist()), "development_free_exponent": free, **score})
    # Local derivative summaries for the most flexible development fit.
    cubic = dict(specs)["within_polynomial_degree_3"]
    for quantile in (0.1, 0.25, 0.5, 0.75, 0.9):
        x = float(development.log_area.quantile(quantile))
        derivative = float(sum(power * cubic[power - 1] * x ** (power - 1) for power in range(1, 4)))
        rows.append({"model": "cubic_local_derivative", "degree": 3, "coefficients": json.dumps(cubic.tolist()), "development_free_exponent": free, "n_predictions": 0, "mae_log": np.nan, "rmse_log": np.nan, "area_quantile": quantile, "log_area": x, "implied_local_exponent": derivative})
    return pd.DataFrame(rows)


def sensitivity_tables(sequences: pd.DataFrame, geometry: pd.DataFrame, replicates: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    measurement_rows, thinning_rows, perimeter_rows, scale_rows = [], [], [], []
    for perimeter in ("exterior_perimeter_km", "total_perimeter_km"):
        for stride in (1, 2, 3):
            panel = prepare_geometry_panel(sequences, geometry, perimeter_column=perimeter, stride=stride)
            held = panel[panel.partition.eq("held_out")]
            boot = bootstrap_scaling(held, replicates=replicates, seed=DEFAULT_SEED + stride + len(perimeter))
            wb = boot[boot.estimand.isin(["within", "between"])].copy()
            wb["perimeter_definition"] = perimeter.replace("_perimeter_km", "")
            wb["observation_stride"] = stride
            thinning_rows.append(wb)
            if stride == 1:
                perimeter_rows.append(wb)
                methods = measurement_error_slopes(held)
                for method, estimate in methods.items():
                    measurement_rows.append({"partition": "held_out", "perimeter_definition": perimeter.replace("_perimeter_km", ""), "method": method, "estimate": estimate, "inferential_target": "conditional prediction" if method == "ols_conditional" else "symmetric association sensitivity"})
    scale_rows.append({"test": "multiple_spatial_resolutions", "status": "UNRESOLVED", "reason": "The locked FIRED geometry is available at one approximately 500 m source resolution; rerasterizing it would not create independent observation resolutions."})
    return pd.DataFrame(measurement_rows), pd.concat(thinning_rows, ignore_index=True), pd.concat(perimeter_rows, ignore_index=True), pd.DataFrame(scale_rows)


def log_original_sensitivity(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for partition in ("development", "calibration", "held_out"):
        frame = panel[panel.partition.eq(partition)]
        log_fit = scaling_estimates(frame)["within"]
        original = original_scale_profile(frame)
        residual = frame.log_perimeter - (frame.groupby("id").log_perimeter.transform("mean") + log_fit * (frame.log_area - frame.groupby("id").log_area.transform("mean")))
        rows.extend([
            {"partition": partition, "error_model": "multiplicative_lognormal", "exponent": log_fit, "objective": float(np.dot(residual, residual)), "residual_scale_correlation": spearmanr(np.abs(residual), frame.log_area).statistic},
            {"partition": partition, "error_model": "additive_original_scale_profiled_event_prefactor", "exponent": original["exponent"], "objective": original["sse"], "residual_scale_correlation": np.nan},
        ])
    return pd.DataFrame(rows)


def local_longitudinal(local_path: Path, panel: pd.DataFrame, fits: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    local = pd.read_csv(local_path)
    local = local[(local.estimator.eq("rolling_ols_7")) & (local.perimeter_definition.eq("exterior")) & (local.observation_stride.eq(1))].copy()
    local = local.merge(fits.loc[fits.eligible, ["id", "slope", "partition"]].rename(columns={"slope": "longitudinal_slope"}), on=["id", "partition"], how="inner")
    area = panel[["id", "event_day", "log_area", "log_perimeter"]].copy()
    area["window_log_area_span"] = area.groupby("id").log_area.transform(lambda values: values.rolling(7).max() - values.rolling(7).min())
    area["perimeter_log_change"] = area.groupby("id").log_perimeter.diff().abs()
    local = local.merge(area, on=["id", "event_day"], how="left", validate="many_to_one")
    local["local_error"] = local.sigma - local.longitudinal_slope
    local["absolute_local_error"] = local.local_error.abs()
    rows = []
    for partition, frame in local.groupby("partition"):
        event_stats = frame.groupby("id").agg(local_variance=("local_error", "var"), local_mean=("sigma", "mean"), longitudinal_slope=("longitudinal_slope", "first"), median_area_span=("window_log_area_span", "median"), mean_perimeter_change=("perimeter_log_change", "mean")).reset_index()
        autocorrelations = frame.sort_values(["id", "event_day"]).groupby("id").local_error.apply(
            lambda values: values.autocorr() if len(values) >= 2 and values.std() > 0 else np.nan
        ).dropna()
        rho_span = spearmanr(frame.absolute_local_error, frame.window_log_area_span, nan_policy="omit")
        rows.append({"partition": partition, "n_fires": frame.id.nunique(), "n_local_states": len(frame), "median_local_variance_around_longitudinal": event_stats.local_variance.median(), "median_local_lag1_autocorrelation": autocorrelations.median(), "local_mean_vs_longitudinal_rho": spearmanr(event_stats.local_mean, event_stats.longitudinal_slope).statistic, "absolute_error_vs_window_log_area_span_rho": rho_span.statistic, "absolute_error_vs_window_log_area_span_p": rho_span.pvalue, "median_window_log_area_span": frame.window_log_area_span.median()})
    return pd.DataFrame(rows), local


def synthetic_one(panel: pd.DataFrame, sigma: float, noise_sd: float, noise_rho: float, rng: np.random.Generator) -> dict[str, float]:
    frames = []
    intercepts = (panel.groupby("id").log_perimeter.mean() - sigma * panel.groupby("id").log_area.mean()).to_numpy()
    rng.shuffle(intercepts)
    for intercept, (_, fire) in zip(intercepts, panel.groupby("id", sort=False), strict=True):
        fire = fire.sort_values("event_day").copy()
        innovation_sd = noise_sd * np.sqrt(max(1 - noise_rho**2, 1e-6))
        noise = np.empty(len(fire)); noise[0] = rng.normal(0, noise_sd)
        for index in range(1, len(fire)):
            noise[index] = noise_rho * noise[index - 1] + rng.normal(0, innovation_sd)
        fire["log_perimeter"] = intercept + sigma * fire.log_area + noise
        fire["perimeter_km"] = np.exp(fire.log_perimeter)
        fire["exterior_perimeter_km"] = fire.perimeter_km
        frames.append(fire)
    synthetic = pd.concat(frames, ignore_index=True)
    estimates = scaling_estimates(synthetic)
    fits = fire_specific_slopes(synthetic)
    local = estimate_local_slopes(synthetic.rename(columns={"perimeter_km": "simulated_perimeter_km"}), perimeter_column="exterior_perimeter_km", estimator="rolling_ols_7")
    local = local.sort_values(["id", "event_day"])
    local["next_sigma"] = local.groupby("id").sigma.shift(-1)
    transitions = local.dropna(subset=["next_sigma"]).copy()
    x = transitions.sigma.to_numpy(); delta = transitions.next_sigma.to_numpy() - x
    restoring = np.polyfit(x, delta, 1)[0] if len(x) else np.nan
    autocorr = local.groupby("id").sigma.apply(
        lambda values: values.autocorr() if len(values) >= 2 and values.std() > 0 else np.nan
    ).median()
    return {
        "population_exponent": estimates["population"], "within_exponent": estimates["within"], "between_exponent": estimates["between"],
        "median_fire_specific_slope": fits.loc[fits.eligible, "slope"].median(), "sd_fire_specific_slope": fits.loc[fits.eligible, "slope"].std(),
        "local_slope_variance": local.groupby("id").sigma.var().median(), "local_slope_autocorrelation": autocorr,
        "apparent_restoring_coefficient": restoring,
        "one_half_forecast_mae": float(np.mean(np.abs(transitions.next_sigma - 0.5))),
        "two_thirds_forecast_mae": float(np.mean(np.abs(transitions.next_sigma - 2/3))),
        "fraction_local_closer_to_half": float((np.abs(local.sigma - 0.5) < np.abs(local.sigma - 2/3)).mean()),
        "thinning_sensitivity": scaling_estimates(synthetic[synthetic.groupby("id").cumcount().mod(2).eq(0)])["within"] - estimates["within"],
    }


def synthetic_reconciliation(panel: pd.DataFrame, observed_local: pd.DataFrame, replicates: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    development = panel[panel.partition.eq("development")].copy()
    dev_within = scaling_estimates(development)["within"]
    fitted = development.groupby("id").log_perimeter.transform("mean") + dev_within * (development.log_area - development.groupby("id").log_area.transform("mean"))
    residual = development.log_perimeter - fitted
    lag = pd.DataFrame({"r": residual, "lag": residual.groupby(development.id).shift()}).dropna()
    noise_rho = float(np.clip(lag.corr().iloc[0, 1], -0.9, 0.9))
    noise_sd = float(residual.std())
    rows = []
    candidates = [("S1_true_one_half", 0.5), ("S2_true_two_thirds", 2/3), ("S3_true_three_quarters", 0.75), ("S4_development_estimated", dev_within)]
    for model_index, (name, sigma) in enumerate(candidates):
        for replicate in range(replicates):
            metrics = synthetic_one(development, sigma, noise_sd, noise_rho, np.random.default_rng(DEFAULT_SEED + 1000 * model_index + replicate))
            rows.append({"model": name, "generating_exponent": sigma, "replicate": replicate, "noise_sd_log": noise_sd, "noise_lag1": noise_rho, **metrics})
    results = pd.DataFrame(rows)
    observed_panel = scaling_estimates(panel[panel.partition.eq("held_out")])
    held_local = observed_local[observed_local.partition.eq("held_out")].copy()
    held_local = held_local.sort_values(["id", "event_day"])
    held_local["next_sigma"] = held_local.groupby("id").sigma.shift(-1)
    transition = held_local.dropna(subset=["next_sigma"])
    observed = {
        "population_exponent": observed_panel["population"], "within_exponent": observed_panel["within"], "between_exponent": observed_panel["between"],
        "median_fire_specific_slope": held_local.longitudinal_slope.groupby(held_local.id).first().median(), "sd_fire_specific_slope": held_local.longitudinal_slope.groupby(held_local.id).first().std(),
        "local_slope_variance": held_local.groupby("id").sigma.var().median(), "local_slope_autocorrelation": held_local.groupby("id").sigma.apply(lambda values: values.autocorr()).median(),
        "apparent_restoring_coefficient": np.polyfit(transition.sigma, transition.next_sigma - transition.sigma, 1)[0],
        "one_half_forecast_mae": float(np.mean(np.abs(transition.next_sigma - 0.5))), "two_thirds_forecast_mae": float(np.mean(np.abs(transition.next_sigma - 2/3))),
        "fraction_local_closer_to_half": float((np.abs(held_local.sigma - 0.5) < np.abs(held_local.sigma - 2/3)).mean()),
    }
    discrepancy = []
    for model, frame in results.groupby("model"):
        distance = 0.0
        for metric, value in observed.items():
            center = frame[metric].mean(); scale = max(frame[metric].std(), 0.01)
            z = (value - center) / scale
            discrepancy.append({"model": model, "metric": metric, "observed": value, "synthetic_mean": center, "synthetic_sd": frame[metric].std(), "standardized_discrepancy": z, "absolute_standardized_discrepancy": abs(z)})
            distance += z * z
        discrepancy.append({"model": model, "metric": "joint_root_mean_square_standardized_discrepancy", "observed": np.nan, "synthetic_mean": np.nan, "synthetic_sd": np.nan, "standardized_discrepancy": np.sqrt(distance / len(observed)), "absolute_standardized_discrepancy": np.sqrt(distance / len(observed))})
    return results, pd.DataFrame(discrepancy)


def geometric_state_dynamics(panel: pd.DataFrame, free_sigma: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidates = [("one_half", 0.5), ("two_thirds", 2/3), ("three_quarters", 0.75), ("development_estimated", free_sigma)]
    states = panel[["id", "ig_year", "partition", "event_day", "log_area", "log_perimeter", "daily_area_km2", "cumulative_area_km2", "component_count", "hole_count"]].copy()
    rows = []
    for name, sigma in candidates:
        column = f"z_{name}"
        states[column] = states.log_perimeter - sigma * states.log_area
        states[f"delta_{column}"] = states.groupby("id")[column].diff()
        for partition, frame in states.groupby("partition"):
            event_means = frame.groupby("id")[column].mean()
            within_var = frame.groupby("id")[column].var().mean()
            lag = pd.DataFrame({"z": frame[column], "lag": frame.groupby("id")[column].shift()}).dropna()
            rows.append({"partition": partition, "normalization": name, "exponent": sigma, "between_fire_variance": event_means.var(), "mean_within_fire_variance": within_var, "within_fraction_total_variance": within_var / frame[column].var(), "lag1_correlation": lag.corr().iloc[0, 1], "drift_with_log_area": scaling_estimates(frame)["within"] - sigma, "drift_with_age": spearmanr(frame[column], frame.event_day).statistic})
    return pd.DataFrame(rows), states


def evaluate_models(train: pd.DataFrame, calibration: pd.DataFrame, held: pd.DataFrame, target: str, specs: dict[str, list[str]], kind: str, context: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for name, features in specs.items():
        best = None
        for alpha in (0.1, 1.0, 10.0, 100.0):
            model = fit_ridge(train, target, features, alpha)
            prediction = predict_ridge(model, calibration)
            score = float(np.mean((prediction - calibration[target]) ** 2))
            if best is None or score < best[0]:
                best = (score, alpha)
        combined = pd.concat([train, calibration], ignore_index=True)
        model = fit_ridge(combined, target, features, best[1])
        prediction = predict_ridge(model, held)
        error = prediction - held[target].to_numpy(dtype=float)
        row = {**context, "target": target, "target_kind": kind, "model": name, "features": ";".join(features), "selected_alpha": best[1], "n_held_out": len(held), "n_held_out_fires": held.id.nunique(), "mae": float(np.mean(np.abs(error))), "rmse_or_brier": float(np.sqrt(np.mean(error**2))) if kind == "continuous" else float(np.mean(error**2)), "r_squared": float(1 - np.dot(error, error) / np.dot(held[target] - held[target].mean(), held[target] - held[target].mean())) if kind == "continuous" else np.nan}
        rows.append(row)
    return rows


def state_prediction(growth_path: Path, transport_path: Path, states: pd.DataFrame, local_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    growth = pd.read_parquet(growth_path)
    growth = growth[growth.lead_days.isin([1, 3, 5, 7])].copy()
    local = pd.read_csv(local_path)
    local = local[(local.estimator.eq("rolling_ols_7")) & (local.perimeter_definition.eq("exterior")) & (local.observation_stride.eq(1))][["id", "event_day", "sigma"]].rename(columns={"event_day": "origin_day", "sigma": "local_sigma"})
    state = states[["id", "event_day", "z_two_thirds", "delta_z_two_thirds", "component_count", "hole_count"]].rename(columns={"event_day": "origin_day"})
    data = growth.merge(state, on=["id", "origin_day"], how="inner").merge(local, on=["id", "origin_day"], how="inner")
    data["log_future_area"] = np.log(data.observed_future_area_km2)
    data["acceleration_positive"] = (data.observed_mean_growth_km2_day > np.expm1(data.log_mean_daily_growth)).astype(float)
    base = ["log_origin_area", "origin_age_scaled", "log_recent_growth", "recent_area_fraction", "recent_growth_acceleration"]
    specs = {"A_area_recent_dynamics": base, "B_plus_local_sigma": base + ["local_sigma"], "C_plus_Z_two_thirds": base + ["z_two_thirds", "delta_z_two_thirds"], "D_sigma_and_Z": base + ["local_sigma", "z_two_thirds", "delta_z_two_thirds"], "E_full_geometry": base + ["local_sigma", "z_two_thirds", "delta_z_two_thirds", "log_exterior_perimeter", "exterior_perimeter_area_slope", "log_component_count", "log1p_hole_count"]}
    rows = []
    for lead, frame in data.groupby("lead_days"):
        dev, cal, held = frame[frame.partition.eq("development")], frame[frame.partition.eq("calibration")], frame[frame.partition.eq("held_out")]
        for target, kind in (("log_future_area", "continuous"), ("realized_coupling", "continuous"), ("acceleration_positive", "binary"), ("terminated_within_horizon", "binary")):
            valid = frame[np.isfinite(frame[target])]
            dev, cal, held = valid[valid.partition.eq("development")], valid[valid.partition.eq("calibration")], valid[valid.partition.eq("held_out")]
            if min(len(dev), len(cal), len(held)) < 50:
                continue
            rows.extend(evaluate_models(dev, cal, held, target, specs, kind, {"horizon_days": int(lead), "data_source": "growth_residuals"}))
    if transport_path.exists():
        transport = pd.read_parquet(transport_path)
        transport = transport[transport.primary_sample.astype(bool)].copy()
        transport = transport.merge(state, on=["id", "origin_day"], how="inner").merge(local, on=["id", "origin_day"], how="inner")
        # Base transport predictors are origin safe and measured before target geometry.
        transport["log_origin_area"] = np.log(transport.start_area_km2)
        transport["origin_age_scaled"] = transport.origin_day / 42.0
        transport["log_recent_growth"] = np.log1p(np.maximum(transport.delta_area_km2 / transport.actual_lead_days, 0))
        transport["recent_area_fraction"] = transport.delta_area_km2 / np.maximum(transport.target_area_km2, 1e-12)
        transport["recent_growth_acceleration"] = 0.0
        transport["log_exterior_perimeter"] = np.log(transport.actual_perimeter_km)
        transport["exterior_perimeter_area_slope"] = transport.local_sigma
        transport["log_component_count"] = np.log1p(transport.component_count if "component_count" in transport else 0)
        transport["log1p_hole_count"] = np.log1p(transport.hole_count if "hole_count" in transport else 0)
        for lead, frame in transport.groupby("actual_lead_days"):
            dev, cal, held = frame[frame.partition.eq("development")], frame[frame.partition.eq("calibration")], frame[frame.partition.eq("held_out")]
            if min(len(dev), len(cal), len(held)) >= 30:
                rows.extend(evaluate_models(dev, cal, held, "reorganization_primary", specs, "continuous", {"horizon_days": int(lead), "data_source": "transport"}))
    relationship = []
    for (partition, lead), frame in data.groupby(["partition", "lead_days"]):
        for predictor in ("z_two_thirds", "delta_z_two_thirds", "local_sigma"):
            rho, pvalue = spearmanr(frame[predictor], frame.realization_residual_q, nan_policy="omit")
            relationship.append({"partition": partition, "horizon_days": lead, "predictor": predictor, "outcome": "realization_residual_q", "spearman_rho": rho, "p_value": pvalue, "n": frame[[predictor, "realization_residual_q"]].dropna().shape[0]})
    return pd.DataFrame(rows), pd.DataFrame(relationship)


def select_examples(fits: pd.DataFrame, local: pd.DataFrame) -> pd.DataFrame:
    held = fits[fits.eligible & fits.partition.eq("held_out")].copy()
    variability = local[local.partition.eq("held_out")].groupby("id").sigma.std().rename("local_sigma_sd")
    held = held.join(variability, on="id").dropna(subset=["local_sigma_sd"])
    selections = []
    remaining = held.copy()
    rules = [
        ("consistent_two_thirds", (remaining.slope - 2/3).abs()),
        ("closer_one_half", (remaining.slope - 0.5).abs()),
        ("changing_geometry", -remaining.local_sigma_sd),
        ("counterexample_low_slope", remaining.slope),
    ]
    used = set()
    for label, score in rules:
        ordered = remaining.assign(_score=score).sort_values(["_score", "id"])
        row = ordered[~ordered.id.isin(used)].iloc[0]
        used.add(int(row.id))
        selections.append({"selection": label, "selection_rule": {"consistent_two_thirds": "minimum absolute longitudinal-slope distance from 2/3", "closer_one_half": "minimum absolute longitudinal-slope distance from 1/2 among unused fires", "changing_geometry": "maximum local-slope standard deviation among unused fires", "counterexample_low_slope": "minimum longitudinal slope among unused eligible held-out fires"}[label], **row.drop(labels=["_score"], errors="ignore").to_dict()})
    return pd.DataFrame(selections)


def save_figure(fig: plt.Figure, base: Path) -> None:
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=400, bbox_inches="tight")
    plt.close(fig)


def primary_figure(panel: pd.DataFrame, decomposition: pd.DataFrame, fits: pd.DataFrame, drift: pd.DataFrame, local: pd.DataFrame, discrepancy: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9.5), constrained_layout=True)
    ax = axes[0, 0]
    hb = ax.hexbin(panel.cumulative_area_km2, panel.perimeter_km, xscale="log", yscale="log", gridsize=55, mincnt=1, bins="log", cmap="magma_r", linewidths=0)
    x = np.geomspace(panel.cumulative_area_km2.min(), panel.cumulative_area_km2.max(), 200)
    anchor_x = float(panel.cumulative_area_km2.median()); anchor_y = float(panel.perimeter_km.median())
    for sigma, color, label in ((0.5, COLORS["half"], "1/2"), (2/3, COLORS["two_thirds"], "2/3"), (0.75, COLORS["three_quarters"], "3/4")):
        ax.plot(x, anchor_y * (x / anchor_x)**sigma, color=color, lw=2, label=label)
    ax.set(xlabel="Area (km$^2$)", ylabel="Exterior perimeter (km)", title="A  Locked population relationship")
    ax.legend(frameon=False, ncol=3, fontsize=8)
    fig.colorbar(hb, ax=ax, label="log count")

    ax = axes[0, 1]
    estimates = decomposition[(decomposition.partition.eq("all")) & decomposition.estimand.isin(["within", "between"])]
    for index, row in enumerate(estimates.itertuples()):
        ax.errorbar(row.estimate, index, xerr=[[row.estimate-row.ci95_lower], [row.ci95_upper-row.estimate]], fmt="o", color=COLORS["ink"], capsize=4)
    for sigma, color in ((0.5, COLORS["half"]), (2/3, COLORS["two_thirds"]), (0.75, COLORS["three_quarters"])):
        ax.axvline(sigma, color=color, lw=2, alpha=.75)
    ax.set(yticks=range(len(estimates)), yticklabels=["Within fires", "Between fires"], xlabel="Exponent", title="B  Within versus between")

    ax = axes[0, 2]
    eligible = fits[fits.eligible]
    ax.hist(eligible.slope, bins=np.linspace(0.15, 0.95, 48), color="#666666", alpha=.8)
    for sigma, color in ((0.5, COLORS["half"]), (2/3, COLORS["two_thirds"]), (0.75, COLORS["three_quarters"])):
        ax.axvline(sigma, color=color, lw=2)
    ax.set(xlabel="Fire-specific longitudinal slope", ylabel="Fires", title="C  Heterogeneous fire slopes")

    ax = axes[1, 0]
    labels = drift.normalization.tolist(); values = drift.within_normalization_drift.to_numpy()
    ax.bar(labels, values, color=[COLORS["half"], COLORS["two_thirds"], COLORS["three_quarters"], "#777777"])
    ax.axhline(0, color="black", lw=1)
    ax.set(ylabel="Within-fire drift in $Z_\\sigma$", title="D  Does normalization remove drift?")
    ax.tick_params(axis="x", rotation=25)

    ax = axes[1, 1]
    summary = local.groupby("id").agg(local_mean=("sigma", "mean"), longitudinal=("longitudinal_slope", "first"), local_sd=("sigma", "std")).dropna()
    hb2 = ax.hexbin(summary.longitudinal, summary.local_mean, gridsize=35, mincnt=1, bins="log", cmap="viridis")
    lim = [0.2, 0.9]; ax.plot(lim, lim, color="white", lw=4); ax.plot(lim, lim, color="black", lw=1.5)
    ax.set(xlim=lim, ylim=lim, xlabel="Longitudinal slope", ylabel="Mean rolling slope", title="E  Local estimates are noisy")
    fig.colorbar(hb2, ax=ax, label="log count")

    ax = axes[1, 2]
    joint = discrepancy[discrepancy.metric.eq("joint_root_mean_square_standardized_discrepancy")].sort_values("absolute_standardized_discrepancy")
    ax.barh(joint.model.str.replace("_", " "), joint.absolute_standardized_discrepancy, color="#6F4C9B")
    ax.set(xlabel="Joint standardized discrepancy (lower is better)", title="F  Synthetic reconciliation")
    fig.suptitle("Does two-thirds describe how individual fires grow?", fontsize=19)
    save_figure(fig, output)


def examples_figure(panel: pd.DataFrame, local: pd.DataFrame, examples: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(3, len(examples), figsize=(16, 9), constrained_layout=True)
    for column, row in enumerate(examples.itertuples()):
        fire = panel[panel.id.eq(row.id)].sort_values("event_day")
        rolling = local[local.id.eq(row.id)].sort_values("event_day")
        x, y = fire.log_area.to_numpy(), fire.log_perimeter.to_numpy()
        axes[0, column].plot(x, y, "o-", color="#333333", ms=3)
        xx = np.linspace(x.min(), x.max(), 100)
        intercept = np.mean(y - row.slope * x)
        axes[0, column].plot(xx, intercept + row.slope * xx, color="#222222", lw=2)
        reference = np.mean(y - (2/3)*x)
        axes[0, column].plot(xx, reference + (2/3)*xx, color=COLORS["two_thirds"], lw=2, ls="--")
        axes[0, column].set_title(f"{row.selection.replace('_', ' ')}\nFIRED {int(row.id)}; slope {row.slope:.2f}")
        axes[1, column].plot(fire.event_day, y - (2/3)*x, color="#6F4C9B", lw=2)
        axes[1, column].axhline(np.mean(y - (2/3)*x), color="#999999", lw=1)
        axes[2, column].plot(rolling.event_day, rolling.sigma, color="#333333", lw=1.5)
        axes[2, column].axhline(2/3, color=COLORS["two_thirds"], lw=2, ls="--")
        axes[2, column].set_xlabel("Event day")
    axes[0, 0].set_ylabel("log perimeter"); axes[1, 0].set_ylabel("$Z_{2/3}$"); axes[2, 0].set_ylabel("Rolling slope")
    save_figure(fig, output)


def main() -> None:
    args = parse_args()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    replicates = 100 if args.smoke else 1000
    synthetic_replicates = 2 if args.smoke else 20
    sequences = pd.read_csv(args.sequences)
    geometry = pd.read_csv(args.geometry)
    if args.smoke:
        ids = sequences.groupby("ig_year").id.unique().explode().groupby(level=0).head(30).astype(int).unique()
        sequences = sequences[sequences.id.isin(ids)]
        geometry = geometry[geometry.id.isin(ids)]
    panel = prepare_geometry_panel(sequences, geometry)

    design_lock = {
        "seed": DEFAULT_SEED,
        "development_years": [2001, 2012], "calibration_years": [2013, 2015], "held_out_years": [2016, 2020],
        "primary_perimeter": "exterior_perimeter_km", "area": "FIRED cumulative_area_km2 on positive mapped-increment days",
        "event_eligibility": {"minimum_observations": 7, "minimum_log_area_span": "log(2)", "minimum_duration_days": 7},
        "local_estimator": "rolling_ols_7 selected previously using development/calibration only",
        "bootstrap_unit": "whole fire", "bootstrap_replicates": replicates,
        "equivalence_rule": "max(0.03, development within-slope bootstrap 95% half-width)",
        "broad_237235_event_figure_status": "PNG and prior prompt history located; exact broad-event source table and plotting script were not found in repository. It is contextual only, not substituted for the locked cohort.",
        "input_sha256": {str(path): sha256(path) for path in (args.sequences, args.geometry, args.local_slopes, args.growth_residuals, args.transport) if path.exists()},
        "smoke": args.smoke,
    }
    (output / "design_lock.json").write_text(json.dumps(design_lock, indent=2) + "\n")

    population, decomposition = population_and_within_between(panel, replicates)
    write_table(population, output / "population_scaling.csv")
    write_table(decomposition, output / "within_between_scaling.csv")
    development_within = decomposition[(decomposition.partition.eq("development")) & (decomposition.estimand.eq("within"))].iloc[0]
    equivalence = max(0.03, (development_within.ci95_upper - development_within.ci95_lower) / 2)
    write_table(candidate_tests(decomposition, equivalence), output / "candidate_exponent_tests.csv")

    fits = fire_specific_slopes(panel)
    fits.to_parquet(output / "fire_specific_slopes.parquet", index=False)
    random_model = random_slope_analysis(fits)
    random_model = pd.concat([
        random_model,
        random_slope_prediction(panel, random_model, float(development_within.estimate)),
    ], ignore_index=True)
    write_table(random_model, output / "random_slope_model.csv")
    lifecycle = heterogeneity_and_lifecycle(panel, fits)
    write_table(lifecycle, output / "lifecycle_scaling.csv")

    free_sigma = float(development_within.estimate)
    drift_frames = []
    for partition in ("development", "calibration", "held_out"):
        part = candidate_normalization_slopes(panel[panel.partition.eq(partition)], [0.5, 2/3, 0.75, free_sigma])
        within_interval = decomposition[(decomposition.partition.eq(partition)) & (decomposition.estimand.eq("within"))].iloc[0]
        part["ci95_lower"] = within_interval.ci95_lower - part.candidate_exponent
        part["ci95_upper"] = within_interval.ci95_upper - part.candidate_exponent
        part["partition"] = partition
        part["normalization"] = ["one_half", "two_thirds", "three_quarters", "development_estimated"]
        drift_frames.append(part)
    drift = pd.concat(drift_frames, ignore_index=True)
    write_table(drift, output / "normalization_drift.csv")
    write_table(powerlaw_adequacy(panel), output / "powerlaw_adequacy.csv")

    measurement, thinning, perimeter, scale = sensitivity_tables(sequences, geometry, replicates)
    write_table(measurement, output / "measurement_error_sensitivity.csv")
    write_table(log_original_sensitivity(panel), output / "log_vs_original_scale.csv")
    write_table(thinning, output / "temporal_thinning_sensitivity.csv")
    write_table(perimeter, output / "perimeter_definition_sensitivity.csv")
    write_table(scale, output / "observation_scale_sensitivity.csv")

    local_summary, local = local_longitudinal(args.local_slopes, panel, fits)
    write_table(local_summary, output / "local_vs_longitudinal_slope.csv")
    synthetic, discrepancy = synthetic_reconciliation(panel, local, synthetic_replicates)
    write_table(synthetic, output / "synthetic_manifold_results.csv")
    write_table(discrepancy, output / "synthetic_joint_discrepancy.csv")

    state_summary, states = geometric_state_dynamics(panel, free_sigma)
    write_table(state_summary, output / "geometric_state_dynamics.csv")
    predictions, relationship = state_prediction(args.growth_residuals, args.transport, states, args.local_slopes)
    write_table(predictions, output / "geometric_state_prediction.csv")
    write_table(relationship, output / "constraint_manifold_relationship.csv")

    examples = select_examples(fits, local)
    write_table(examples, output / "event_examples.csv")
    primary_figure(panel, decomposition, fits, drift[drift.partition.eq("held_out")], local, discrepancy, output / "figure1_geometric_manifold_validation")
    examples_figure(panel, local, examples, output / "figure2_held_out_examples")

    all_est = decomposition[decomposition.partition.eq("all")].set_index("estimand")
    held_est = decomposition[decomposition.partition.eq("held_out")].set_index("estimand")
    best_synthetic = discrepancy[discrepancy.metric.eq("joint_root_mean_square_standardized_discrepancy")].sort_values("absolute_standardized_discrepancy").iloc[0]
    report = {
        "counts": {"events": int(panel.id.nunique()), "observations": int(len(panel)), "development_events": int(panel[panel.partition.eq("development")].id.nunique()), "calibration_events": int(panel[panel.partition.eq("calibration")].id.nunique()), "held_out_events": int(panel[panel.partition.eq("held_out")].id.nunique()), "eligible_fire_specific_slopes": int(fits.eligible.sum())},
        "primary_results": {"population_exponent": float(population[population.partition.eq("all")].estimate.iloc[0]), "within_exponent": float(all_est.loc["within", "estimate"]), "between_exponent": float(all_est.loc["between", "estimate"]), "held_out_within_exponent": float(held_est.loc["within", "estimate"]), "held_out_between_exponent": float(held_est.loc["between", "estimate"]), "development_locked_exponent": free_sigma, "random_slope_mean": float(random_model[random_model.partition.eq("all")].mean_slope.iloc[0]), "random_slope_sd": float(np.sqrt(random_model[random_model.partition.eq("all")].slope_variance.iloc[0])), "best_synthetic_model_by_relative_discrepancy": str(best_synthetic.model), "best_synthetic_joint_discrepancy": float(best_synthetic.absolute_standardized_discrepancy), "synthetic_model_adequate": bool(best_synthetic.absolute_standardized_discrepancy < 2.0)},
        "verdict": "The locked FIRED cohort separates a between-fire exponent near two-thirds from a substantially lower within-fire exponent. Two-thirds primarily describes how fires of different characteristic sizes compare, not the average trajectory followed by an individual fire. Fire-specific and observation-definition heterogeneity preclude a universal exponent claim.",
        "outcome_classification": ["Outcome D: heterogeneous exponents", "Outcome E: scale-dependent departures assessed", "Outcome F: observation-dependent scaling"],
        "limitations": ["FIRED geometry is retrospective and approximately 500 m.", "Exterior mapped perimeter is not independently measured active fireline.", "No genuine multi-resolution observation series was available.", "The two-stage random-slope model assumes Gaussian latent coefficients and treats per-fire OLS covariance as known.", "The broad 237,235-event figure could not be regenerated exactly because its source table/script is absent from the repository."],
    }
    (output / "run_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
