#!/usr/bin/env python3
"""Run the locked final FIRED geometric-state, detection, and prediction audit."""

from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fire_metabolism.final_state_audit import (
    DEFAULT_SEED,
    add_normalized_geometry,
    binary_performance,
    bootstrap_mean_ci,
    calibration_bins,
    curve_points,
    paired_bootstrap_ci,
)
from fire_metabolism.fired_outcomes import fit_standardized_ridge
from fire_metabolism.fired_survival import fit_logistic_hazard


OUT = Path("outputs/final_state_audit")
GROWTH = Path("outputs/latent_constraint_validation/growth_residuals.parquet")
TRANSPORT = Path("outputs/integrated_geometry_transport/transport_transition_metrics.parquet")
SCALE = Path("outputs/geometric_manifold_validation")
LEADS = (1, 3, 5, 7, 10, 14, 21, 28, 35, 42)
ALPHAS = (0.1, 1.0, 10.0, 100.0)
BOOTSTRAPS = 1000

COLORS = {
    "M1_dynamics": "#777777",
    "M2_raw_perimeter": "#B07A3F",
    "M3_development": "#6495ED",
    "M4_full_geometry": "#8B1E2D",
    "M5_prior_OT": "#2A8C5A",
}
LABELS = {
    "M0_area": "Area only",
    "M1_dynamics": "Area + dynamics",
    "M2_raw_perimeter": "+ raw perimeter",
    "M3_one_half": r"+ $Z_{1/2}$",
    "M3_two_thirds": r"+ $Z_{2/3}$",
    "M3_three_quarters": r"+ $Z_{3/4}$",
    "M3_development": r"+ $Z_{0.595}$",
    "M4_full_geometry": "+ full geometry",
    "M5_prior_OT": "+ prior reorganization",
}

M0 = ["log_origin_area"]
M1 = M0 + [
    "origin_age_scaled",
    "log_recent_growth",
    "recent_area_fraction",
    "recent_log_area_change",
    "recent_growth_acceleration",
]
FULL = [
    "log_exterior_perimeter",
    "log_exterior_excess_perimeter",
    "exterior_perimeter_area_slope",
    "log_component_count",
    "log1p_hole_count",
    "recent_log_exterior_perimeter_change",
    "recent_component_change",
    "recent_hole_change",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def model_specs(include_ot: bool = False) -> dict[str, list[str]]:
    specs = {
        "M0_area": M0,
        "M1_dynamics": M1,
        "M2_raw_perimeter": M1 + ["log_exterior_perimeter", "recent_log_exterior_perimeter_change"],
        "M3_one_half": M1 + ["z_one_half", "delta_z_one_half"],
        "M3_two_thirds": M1 + ["z_two_thirds", "delta_z_two_thirds"],
        "M3_three_quarters": M1 + ["z_three_quarters", "delta_z_three_quarters"],
        "M3_development": M1 + ["z_development", "delta_z_development"],
        "M4_full_geometry": M1 + FULL,
    }
    if include_ot:
        specs["M5_prior_OT"] = M1 + FULL + ["log1p_origin_R", "origin_one_minus_iou"]
    return specs


def tune_continuous(dev: pd.DataFrame, cal: pd.DataFrame, target: str, features: list[str]):
    rows = []
    for alpha in ALPHAS:
        model = fit_standardized_ridge(dev, dev[target], feature_columns=features, alpha=alpha)
        rows.append((float(np.mean(np.abs(model.predict(cal) - cal[target]))), alpha))
    return min(rows)[1], min(rows)[0]


def tune_binary(dev: pd.DataFrame, cal: pd.DataFrame, target: str, features: list[str]):
    rows = []
    for alpha in ALPHAS:
        train = dev.copy(); train["terminal_transition"] = train[target].astype(float)
        model = fit_logistic_hazard(train, feature_columns=features, alpha=alpha)
        probability = model.predict_hazard(cal)
        rows.append((float(np.mean((probability - cal[target]) ** 2)), alpha, model))
    _, alpha, model = min(rows, key=lambda item: item[0])
    probability = model.predict_hazard(cal)
    thresholds = np.linspace(0.05, 0.95, 37)
    threshold = max(thresholds, key=lambda value: binary_performance(cal[target], probability, value)["balanced_accuracy"])
    return alpha, float(threshold), min(rows)[0]


def evaluate_target(
    frame: pd.DataFrame,
    target: str,
    target_kind: str,
    target_label: str,
    horizon_column: str = "lead_days",
    include_ot: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_rows, prediction_rows, tuning_rows, bootstrap_rows = [], [], [], []
    specs = model_specs(include_ot=include_ot)
    horizons = sorted(set(frame[horizon_column].dropna().astype(int)).intersection(LEADS if horizon_column == "lead_days" else set(frame[horizon_column].astype(int))))
    for horizon in horizons:
        data = frame[frame[horizon_column].eq(horizon)].replace([np.inf, -np.inf], np.nan)
        for model_name, features in specs.items():
            valid = data.dropna(subset=[target, *features]).copy()
            dev = valid[valid.partition.eq("development")]
            cal = valid[valid.partition.eq("calibration")]
            held = valid[valid.partition.eq("held_out")]
            if min(len(dev), len(cal), len(held)) < 30 or held.id.nunique() < 20:
                continue
            if target_kind == "continuous":
                alpha, cal_loss = tune_continuous(dev, cal, target, features)
                train = pd.concat([dev, cal], ignore_index=True)
                fitted = fit_standardized_ridge(train, train[target], feature_columns=features, alpha=alpha)
                prediction = fitted.predict(held)
                loss = np.abs(prediction - held[target].to_numpy(dtype=float))
                score_name = "mae"
                threshold = np.nan
            else:
                alpha, threshold, cal_loss = tune_binary(dev, cal, target, features)
                train = pd.concat([dev, cal], ignore_index=True); train["terminal_transition"] = train[target].astype(float)
                fitted = fit_logistic_hazard(train, feature_columns=features, alpha=alpha)
                prediction = fitted.predict_hazard(held)
                loss = (prediction - held[target].to_numpy(dtype=float)) ** 2
                score_name = "brier"
            result = held[["id", "ig_year", "origin_day", horizon_column, target]].copy()
            result["target_name"] = target_label
            result["target_kind"] = target_kind
            result["model"] = model_name
            result["prediction"] = prediction
            result["loss"] = loss
            prediction_rows.append(result)
            lower, upper, draws = bootstrap_mean_ci(result, "loss", replicates=BOOTSTRAPS, seed=DEFAULT_SEED + horizon + len(metric_rows))
            row = {
                "target": target_label, "target_column": target, "target_kind": target_kind,
                "horizon_days": horizon, "model": model_name, "features": ";".join(features),
                "selected_alpha": alpha, "decision_threshold": threshold,
                "calibration_loss": cal_loss, "score_metric": score_name,
                "held_out_score": float(result.groupby("id").loss.mean().mean()), "ci95_lower": lower, "ci95_upper": upper,
                "n_prediction_origins": len(held), "n_fires": held.id.nunique(),
            }
            if target_kind == "binary":
                row.update(binary_performance(held[target], prediction, threshold))
            metric_rows.append(row)
            bootstrap_rows.extend({"target": target_label, "horizon_days": horizon, "model": model_name, "replicate": i, "mean_loss": value} for i, value in enumerate(draws))
            tuning_rows.append({"target": target_label, "horizon_days": horizon, "model": model_name, "selected_alpha": alpha, "decision_threshold": threshold, "calibration_loss": cal_loss})
    return pd.DataFrame(metric_rows), pd.concat(prediction_rows, ignore_index=True), pd.DataFrame(tuning_rows), pd.DataFrame(bootstrap_rows)


def add_pairwise(metrics: pd.DataFrame, predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, draws_out = [], []
    keys = ["id", "origin_day"]
    if "lead_days" in predictions.columns:
        keys.append("lead_days")
    for (target, horizon), group in predictions.groupby(["target_name", "lead_days"]):
        pivot = group.pivot_table(index=keys, columns="model", values="loss", aggfunc="first").reset_index()
        models = sorted(set(group.model))
        comparisons = [(model, "M1_dynamics") for model in models if model != "M1_dynamics"]
        normalized = [name for name in models if name.startswith("M3_")]
        comparisons += list(combinations(normalized, 2))
        comparisons += [("M4_full_geometry", name) for name in ("M2_raw_perimeter", "M3_development") if name in models]
        if "M5_prior_OT" in models:
            comparisons.append(("M5_prior_OT", "M4_full_geometry"))
        for first, second in comparisons:
            if first not in pivot or second not in pivot:
                continue
            valid = pivot.dropna(subset=[first, second])
            mean, lower, upper, draws = paired_bootstrap_ci(valid, first, second, replicates=BOOTSTRAPS, seed=DEFAULT_SEED + int(horizon) + len(rows))
            rows.append({"target": target, "horizon_days": int(horizon), "first_model": first, "second_model": second, "loss_difference_first_minus_second": mean, "ci95_lower": lower, "ci95_upper": upper, "n_fires": valid.id.nunique(), "n_prediction_origins": len(valid)})
            draws_out.extend({"target": target, "horizon_days": int(horizon), "first_model": first, "second_model": second, "replicate": i, "loss_difference": value} for i, value in enumerate(draws))
    return pd.DataFrame(rows), pd.DataFrame(draws_out)


def build_detection(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # A fixed three-day interval ending at day 10 matches the established trailing
    # dynamics window and makes all endpoint predictors contemporaneous.
    label = frame[(frame.origin_day.eq(7)) & (frame.lead_days.eq(3))][["id", "ig_year", "partition", "constraint_like", "realization_residual_q", "constraint_threshold_q"]].copy()
    endpoint = frame[frame.origin_day.eq(10)].drop_duplicates("id")
    detection = label.merge(endpoint.drop(columns=["ig_year", "partition"]), on="id", how="inner", suffixes=("_label", ""), validate="one_to_one")
    specs = {
        "D1_dynamics": M1,
        "D2_raw_perimeter": M1 + ["log_exterior_perimeter", "recent_log_exterior_perimeter_change"],
        "D3_development": M1 + ["z_development", "delta_z_development"],
        "D4_full_geometry": M1 + FULL,
    }
    rows, curves, calibration, predictions = [], [], [], []
    train_all = detection[detection.partition.ne("held_out")]
    held = detection[detection.partition.eq("held_out")]
    prevalence = float(train_all.constraint_like.mean())
    base_prob = np.full(len(held), prevalence)
    base_threshold = 0.5
    base = {"model": "D0_prevalence", "n": len(held), "n_fires": held.id.nunique(), **binary_performance(held.constraint_like, base_prob, base_threshold)}
    rows.append(base)
    predictions.append(pd.DataFrame({"id": held.id, "model": "D0_prevalence", "observed": held.constraint_like, "probability": base_prob}))
    for name, features in specs.items():
        dev = detection[detection.partition.eq("development")].dropna(subset=features)
        cal = detection[detection.partition.eq("calibration")].dropna(subset=features)
        test = held.dropna(subset=features)
        alpha, threshold, _ = tune_binary(dev, cal, "constraint_like", features)
        train = pd.concat([dev, cal], ignore_index=True); train["terminal_transition"] = train.constraint_like.astype(float)
        model = fit_logistic_hazard(train, feature_columns=features, alpha=alpha)
        probability = model.predict_hazard(test)
        performance = binary_performance(test.constraint_like, probability, threshold)
        rows.append({"model": name, "n": len(test), "n_fires": test.id.nunique(), "selected_alpha": alpha, **performance})
        curve = curve_points(test.constraint_like, probability); curve["model"] = name; curves.append(curve)
        bins = calibration_bins(test.constraint_like, probability); bins["model"] = name; calibration.append(bins)
        predictions.append(pd.DataFrame({"id": test.id, "model": name, "observed": test.constraint_like, "probability": probability}))
    # Same-interval OT is a separately labeled diagnostic on its smaller matched sample.
    if TRANSPORT.exists():
        transport = pd.read_parquet(TRANSPORT)
        same = transport[(transport.origin_day.eq(7)) & (transport.future_day.eq(10)) & transport.primary_sample.astype(bool)][["id", "reorganization_primary", "iou"]]
        matched = detection.merge(same, on="id", how="inner")
        matched["contemporaneous_R"] = np.log1p(matched.reorganization_primary.clip(lower=0))
        matched["contemporaneous_one_minus_iou"] = 1 - matched.iou
        features = M1 + FULL + ["contemporaneous_R", "contemporaneous_one_minus_iou"]
        dev, cal, test = (matched[matched.partition.eq(value)].dropna(subset=features) for value in ("development", "calibration", "held_out"))
        if min(len(dev), len(cal), len(test)) >= 20:
            alpha, threshold, _ = tune_binary(dev, cal, "constraint_like", features)
            train = pd.concat([dev, cal], ignore_index=True); train["terminal_transition"] = train.constraint_like.astype(float)
            model = fit_logistic_hazard(train, feature_columns=features, alpha=alpha)
            probability = model.predict_hazard(test)
            rows.append({"model": "D5_contemporaneous_OT", "n": len(test), "n_fires": test.id.nunique(), "selected_alpha": alpha, **binary_performance(test.constraint_like, probability, threshold)})
            predictions.append(pd.DataFrame({"id": test.id, "model": "D5_contemporaneous_OT", "observed": test.constraint_like, "probability": probability}))
    metrics = pd.DataFrame(rows)
    prediction_table = pd.concat(predictions, ignore_index=True)
    bootstrap_rows = []
    for model_name, group in prediction_table.groupby("model"):
        threshold = float(metrics.loc[metrics.model.eq(model_name), "decision_threshold"].iloc[0])
        generator = np.random.default_rng(DEFAULT_SEED + len(bootstrap_rows))
        values = group[["observed", "probability"]].to_numpy()
        for replicate in range(BOOTSTRAPS):
            sample = values[generator.integers(0, len(values), len(values))]
            result = binary_performance(sample[:, 0], sample[:, 1], threshold)
            bootstrap_rows.extend(
                {"model": model_name, "replicate": replicate, "metric": metric, "value": value}
                for metric, value in result.items()
                if metric in {"recall", "specificity", "precision", "balanced_accuracy", "f1", "roc_auc", "pr_auc", "brier"}
            )
    bootstrap = pd.DataFrame(bootstrap_rows)
    intervals = (
        bootstrap.groupby(["model", "metric"]).value.quantile([0.025, 0.975])
        .unstack().reset_index().rename(columns={0.025: "lower", 0.975: "upper"})
    )
    for row in intervals.itertuples(index=False):
        metrics.loc[metrics.model.eq(row.model), f"{row.metric}_ci95_lower"] = row.lower
        metrics.loc[metrics.model.eq(row.model), f"{row.metric}_ci95_upper"] = row.upper
    return metrics, pd.concat(curves, ignore_index=True), pd.concat(calibration, ignore_index=True), prediction_table, bootstrap


def scale_audit() -> pd.DataFrame:
    rows = []
    thinning = pd.read_csv(SCALE / "temporal_thinning_sensitivity.csv")
    for row in thinning[thinning.estimand.eq("within")].itertuples(index=False):
        rows.append({"scale_dimension": "temporal cadence", "variant": f"{row.perimeter_definition}, every {row.observation_stride} observation(s)", "estimate": row.estimate, "ci95_lower": row.ci95_lower, "ci95_upper": row.ci95_upper, "empirically_varied": "yes", "supports_scale_dependence": "yes"})
    lifecycle = pd.read_csv(SCALE / "lifecycle_scaling.csv")
    phase = lifecycle[lifecycle.analysis.astype(str).str.contains("phase", case=False, na=False)]
    for row in phase.itertuples(index=False):
        rows.append({"scale_dimension": "lifecycle position", "variant": f"{row.partition}: {getattr(row, 'phase', getattr(row, 'predictor', 'phase'))}", "estimate": getattr(row, "coefficient", np.nan), "ci95_lower": np.nan, "ci95_upper": np.nan, "empirically_varied": "yes", "supports_scale_dependence": "yes"})
    measurement = pd.read_csv(SCALE / "measurement_error_sensitivity.csv")
    for row in measurement.itertuples(index=False):
        rows.append({"scale_dimension": "estimator", "variant": f"{row.perimeter_definition}: {row.method}", "estimate": row.estimate, "ci95_lower": np.nan, "ci95_upper": np.nan, "empirically_varied": "yes", "supports_scale_dependence": "yes"})
    original = pd.read_csv(SCALE / "log_vs_original_scale.csv")
    for row in original[original.partition.eq("held_out")].itertuples(index=False):
        rows.append({"scale_dimension": "error scale", "variant": row.error_model, "estimate": row.exponent, "ci95_lower": np.nan, "ci95_upper": np.nan, "empirically_varied": "yes", "supports_scale_dependence": "yes"})
    cubic = pd.read_csv(SCALE / "powerlaw_adequacy.csv")
    for row in cubic[cubic.model.eq("cubic_local_derivative")].itertuples(index=False):
        rows.append({"scale_dimension": "area scale", "variant": f"development cubic derivative at area quantile {row.area_quantile:.2f}", "estimate": row.implied_local_exponent, "ci95_lower": np.nan, "ci95_upper": np.nan, "empirically_varied": "yes", "supports_scale_dependence": "yes"})
    rows.append({"scale_dimension": "independent spatial resolution", "variant": "no independent product located", "estimate": np.nan, "ci95_lower": np.nan, "ci95_upper": np.nan, "empirically_varied": "no", "supports_scale_dependence": "unresolved"})
    return pd.DataFrame(rows)


def make_figures(metrics: pd.DataFrame, pairwise: pd.DataFrame, detection: pd.DataFrame, curves: pd.DataFrame, calibration: pd.DataFrame, scale: pd.DataFrame, bootstraps: pd.DataFrame) -> list[dict[str, object]]:
    provenance = []
    plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 140})
    # Main: PR detection and future-area skill.
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), constrained_layout=True)
    ax = axes[0]
    detection_models = ["D1_dynamics", "D2_raw_perimeter", "D3_development", "D4_full_geometry"]
    det_colors = ["#777777", "#B07A3F", "#6495ED", "#8B1E2D"]
    det_labels = ["dynamics", "+ raw perimeter", r"+ $Z_{0.595}$", "+ full geometry"]
    for name, color, label in zip(detection_models, det_colors, det_labels, strict=True):
        group = curves[curves.model.eq(name)].sort_values("recall")
        auc = detection.loc[detection.model.eq(name), "pr_auc"].iloc[0]
        ax.plot(group.recall, group.precision, color=color, lw=2, label=f"{label} (AP={auc:.2f})")
        provenance.append({"figure": "figureX_detection_prediction", "panel": "A", "visual_element": name, "source_script": "scripts/run_final_state_audit.py", "source_file": "outputs/final_state_audit/detection_curve_points.csv", "cohort": "FIRED 2016-2020 held out", "target": "3-day major realized-growth deficit ending day 10", "model": name, "horizon_days": 3, "metric": "precision-recall curve and average precision", "uncertainty_method": "none on curve; tabulated whole-fire bootstrap"})
    prevalence = detection.loc[detection.model.eq("D0_prevalence"), "prevalence"].iloc[0]
    ax.axhline(prevalence, color="#BBBBBB", ls="--", lw=1)
    ax.set(xlabel="Recall", ylabel="Precision", title="Detecting current growth deficits", xlim=(0, 1), ylim=(0, 1))
    ax.legend(frameon=False, fontsize=7, loc="upper right")
    ax.text(-0.14, 1.04, "A", transform=ax.transAxes, fontsize=12, fontweight="bold")
    ax = axes[1]
    area = metrics[(metrics.target.eq("future_mapped_area")) & metrics.model.isin(["M1_dynamics", "M2_raw_perimeter", "M3_development", "M4_full_geometry"])]
    baseline = area[area.model.eq("M1_dynamics")].set_index("horizon_days").held_out_score
    for name in ["M2_raw_perimeter", "M3_development", "M4_full_geometry"]:
        group = area[area.model.eq(name)].sort_values("horizon_days")
        skill = 1 - group.held_out_score.to_numpy() / group.horizon_days.map(baseline).to_numpy()
        contrast = pairwise[(pairwise.target.eq("future_mapped_area")) & pairwise.first_model.eq(name) & pairwise.second_model.eq("M1_dynamics")].set_index("horizon_days")
        lower = -group.horizon_days.map(contrast.ci95_upper).to_numpy() / group.horizon_days.map(baseline).to_numpy()
        upper = -group.horizon_days.map(contrast.ci95_lower).to_numpy() / group.horizon_days.map(baseline).to_numpy()
        ax.plot(group.horizon_days, skill, marker="o", lw=2, color=COLORS[name], label=LABELS[name])
        ax.fill_between(group.horizon_days, lower, upper, color=COLORS[name], alpha=0.16, linewidth=0)
        provenance.append({"figure": "figureX_detection_prediction", "panel": "B", "visual_element": name, "source_script": "scripts/run_final_state_audit.py", "source_file": "outputs/final_state_audit/target_horizon_metrics.csv", "cohort": "FIRED 2016-2020 held out", "target": "future mapped area", "model": name, "horizon_days": "1,3,5,7,10,14,21,28,35,42", "metric": "1 - MAE(model)/MAE(M1)", "uncertainty_method": "95% whole-fire bootstrap bands"})
    ax.axhline(0, color="#777777", lw=1, ls="--")
    ax.set(xlabel="Prediction horizon (days)", ylabel="Skill relative to area + dynamics", title="Predicting future mapped area")
    ax.set_xscale("log"); ax.set_xticks([1, 3, 7, 14, 28, 42]); ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.legend(frameon=False, fontsize=7)
    ax.text(-0.14, 1.04, "B", transform=ax.transAxes, fontsize=12, fontweight="bold")
    for suffix in ("pdf", "svg", "png"):
        fig.savefig(OUT / f"figureX_detection_prediction.{suffix}", dpi=600 if suffix == "png" else None)
    plt.close(fig)

    # SI 1: normalization comparison across targets and horizons.
    norm = metrics[metrics.model.str.startswith("M3_")].copy()
    targets = list(norm.target.unique())
    fig, axes = plt.subplots(len(targets), 1, figsize=(7.2, max(3.0, 1.8 * len(targets))), constrained_layout=True, squeeze=False)
    for ax, target in zip(axes[:, 0], targets, strict=True):
        for name in ["M3_one_half", "M3_two_thirds", "M3_three_quarters", "M3_development"]:
            group = norm[(norm.target.eq(target)) & norm.model.eq(name)].sort_values("horizon_days")
            if len(group): ax.plot(group.horizon_days, group.held_out_score, marker="o", lw=1.4, label=LABELS[name])
        ax.set_title(target.replace("_", " ")); ax.set_ylabel("Held-out loss")
    axes[-1, 0].set_xlabel("Horizon (days)"); axes[0, 0].legend(ncol=4, frameon=False, fontsize=7)
    for suffix in ("pdf", "svg", "png"): fig.savefig(OUT / f"si1_normalization_comparison.{suffix}", dpi=500 if suffix == "png" else None)
    plt.close(fig)

    # SI 2: hierarchy.
    fig, ax = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    area = metrics[metrics.target.eq("future_mapped_area")]
    for name in ["M1_dynamics", "M2_raw_perimeter", "M3_development", "M4_full_geometry"]:
        group = area[area.model.eq(name)].sort_values("horizon_days")
        ax.plot(group.horizon_days, group.held_out_score, marker="o", lw=1.8, color=COLORS[name], label=LABELS[name])
    ax.set(xlabel="Horizon (days)", ylabel="Mean absolute log-area error", title="Raw perimeter, normalized geometry, and full state")
    ax.legend(frameon=False)
    for suffix in ("pdf", "svg", "png"): fig.savefig(OUT / f"si2_geometry_hierarchy.{suffix}", dpi=500 if suffix == "png" else None)
    plt.close(fig)

    # SI 3/4 curves and calibration.
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), constrained_layout=True)
    for name, color in zip(detection_models, det_colors, strict=True):
        group = curves[curves.model.eq(name)].sort_values("false_positive_rate")
        axes[0].plot(group.false_positive_rate, group.recall, color=color, label=name)
        group = curves[curves.model.eq(name)].sort_values("recall")
        axes[1].plot(group.recall, group.precision, color=color, label=name)
    axes[0].plot([0, 1], [0, 1], color="#BBBBBB", ls="--"); axes[0].set(xlabel="False-positive rate", ylabel="Recall", title="ROC")
    axes[1].axhline(prevalence, color="#BBBBBB", ls="--"); axes[1].set(xlabel="Recall", ylabel="Precision", title="Precision-recall")
    axes[1].legend(frameon=False, fontsize=6)
    for suffix in ("pdf", "svg", "png"): fig.savefig(OUT / f"si3_detection_curves.{suffix}", dpi=500 if suffix == "png" else None)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(4.2, 3.6), constrained_layout=True)
    for name, color in zip(detection_models, det_colors, strict=True):
        group = calibration[calibration.model.eq(name)]
        ax.plot(group.mean_probability, group.event_rate, marker="o", color=color, label=name)
    ax.plot([0, 1], [0, 1], color="#BBBBBB", ls="--"); ax.set(xlabel="Predicted probability", ylabel="Observed frequency", title="Detection calibration", xlim=(0, .7), ylim=(0, .7)); ax.legend(frameon=False, fontsize=6)
    for suffix in ("pdf", "svg", "png"): fig.savefig(OUT / f"si4_detection_calibration.{suffix}", dpi=500 if suffix == "png" else None)
    plt.close(fig)

    # SI 5 all targets, SI 6 scale, SI 7 sample sizes, SI 8 bootstrap distributions.
    fig, axes = plt.subplots(len(metrics.target.unique()), 1, figsize=(7.2, max(4, 1.9 * len(metrics.target.unique()))), constrained_layout=True, squeeze=False)
    for ax, target in zip(axes[:, 0], metrics.target.unique(), strict=True):
        for name in ["M1_dynamics", "M2_raw_perimeter", "M3_development", "M4_full_geometry", "M5_prior_OT"]:
            group = metrics[(metrics.target.eq(target)) & metrics.model.eq(name)].sort_values("horizon_days")
            if len(group): ax.plot(group.horizon_days, group.held_out_score, marker="o", lw=1.2, label=LABELS[name])
        ax.set_title(target.replace("_", " ")); ax.set_ylabel("Loss")
    axes[-1, 0].set_xlabel("Horizon (days)"); axes[0, 0].legend(ncol=3, frameon=False, fontsize=6)
    for suffix in ("pdf", "svg", "png"): fig.savefig(OUT / f"si5_all_targets_horizons.{suffix}", dpi=500 if suffix == "png" else None)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.2, 4.0), constrained_layout=True)
    plotted = scale.dropna(subset=["estimate"]).copy(); plotted["label"] = plotted.scale_dimension + ": " + plotted.variant
    ax.scatter(plotted.estimate, np.arange(len(plotted)), color="#394B59", s=22)
    ax.set_yticks(np.arange(len(plotted)), plotted.label, fontsize=6); ax.axvline(2/3, color="#6495ED", ls="--", lw=1); ax.set(xlabel="Estimated geometric exponent / derivative", title="Empirically available scale and estimator sensitivities")
    for suffix in ("pdf", "svg", "png"): fig.savefig(OUT / f"si6_scale_dependence.{suffix}", dpi=500 if suffix == "png" else None)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.2, 3.5), constrained_layout=True)
    samples = metrics[metrics.model.eq("M1_dynamics")]
    for target, group in samples.groupby("target"):
        ax.plot(group.horizon_days, group.n_fires, marker="o", label=target.replace("_", " "))
    ax.set(xlabel="Horizon (days)", ylabel="Held-out fires", title="Prediction sample size"); ax.legend(frameon=False, fontsize=6)
    for suffix in ("pdf", "svg", "png"): fig.savefig(OUT / f"si7_sample_sizes.{suffix}", dpi=500 if suffix == "png" else None)
    plt.close(fig)
    key = bootstraps[(bootstraps.target.eq("future_mapped_area")) & bootstraps.first_model.eq("M4_full_geometry") & bootstraps.second_model.isin(["M1_dynamics", "M2_raw_perimeter", "M3_development"]) & bootstraps.horizon_days.isin([3, 7, 14, 28])]
    fig, ax = plt.subplots(figsize=(7.2, 4.0), constrained_layout=True)
    labels, values = [], []
    for keys, group in key.groupby(["horizon_days", "second_model"]):
        labels.append(f"{keys[0]}d\nvs {LABELS[keys[1]].replace('+ ', '')}"); values.append(group.loss_difference.to_numpy())
    if values: ax.violinplot(values, showmeans=True, showextrema=False); ax.set_xticks(range(1, len(labels)+1), labels, fontsize=6)
    ax.axhline(0, color="#777777", ls="--"); ax.set(ylabel="Full geometry loss minus comparator", title="Whole-fire bootstrap contrasts")
    for suffix in ("pdf", "svg", "png"): fig.savefig(OUT / f"si8_bootstrap_distributions.{suffix}", dpi=500 if suffix == "png" else None)
    plt.close(fig)
    for target in targets:
        for name in ["M3_one_half", "M3_two_thirds", "M3_three_quarters", "M3_development"]:
            provenance.append({"figure": "si1_normalization_comparison", "panel": target, "visual_element": name, "source_script": "scripts/run_final_state_audit.py", "source_file": "outputs/final_state_audit/target_horizon_metrics.csv", "cohort": "FIRED 2016-2020 held out", "target": target, "model": name, "horizon_days": "available locked horizons", "metric": "held-out loss", "uncertainty_method": "95% whole-fire bootstrap in source table"})
    for name in ["M1_dynamics", "M2_raw_perimeter", "M3_development", "M4_full_geometry"]:
        provenance.append({"figure": "si2_geometry_hierarchy", "panel": "future mapped area", "visual_element": name, "source_script": "scripts/run_final_state_audit.py", "source_file": "outputs/final_state_audit/target_horizon_metrics.csv", "cohort": "FIRED 2016-2020 held out", "target": "future mapped area", "model": name, "horizon_days": "all", "metric": "mean absolute log-area error", "uncertainty_method": "95% whole-fire bootstrap in source table"})
    for name in detection_models:
        for figure, metric in (("si3_detection_curves", "ROC and precision-recall"), ("si4_detection_calibration", "probability calibration")):
            provenance.append({"figure": figure, "panel": "aggregate", "visual_element": name, "source_script": "scripts/run_final_state_audit.py", "source_file": "outputs/final_state_audit/detection_curve_points.csv" if figure.endswith("curves") else "outputs/final_state_audit/detection_calibration.csv", "cohort": "FIRED 2016-2020 held out", "target": "3-day major deficit ending day 10", "model": name, "horizon_days": 3, "metric": metric, "uncertainty_method": "whole-fire bootstrap metrics in detection_metrics.csv"})
    for (target, name), _ in metrics.groupby(["target", "model"]):
        provenance.append({"figure": "si5_all_targets_horizons", "panel": target, "visual_element": name, "source_script": "scripts/run_final_state_audit.py", "source_file": "outputs/final_state_audit/target_horizon_metrics.csv", "cohort": "FIRED 2016-2020 held out", "target": target, "model": name, "horizon_days": "available locked horizons", "metric": "held-out loss", "uncertainty_method": "95% whole-fire bootstrap"})
    for row in scale.itertuples(index=False):
        provenance.append({"figure": "si6_scale_dependence", "panel": row.scale_dimension, "visual_element": row.variant, "source_script": "scripts/run_final_state_audit.py", "source_file": "outputs/final_state_audit/scale_dependence_summary.csv", "cohort": "locked FIRED cohort; held out where specified", "target": "geometric scaling", "model": row.variant, "horizon_days": "not applicable", "metric": "exponent or local derivative", "uncertainty_method": "source-analysis whole-fire bootstrap where available"})
    for target in metrics.target.unique():
        provenance.append({"figure": "si7_sample_sizes", "panel": target, "visual_element": "M1 sample size", "source_script": "scripts/run_final_state_audit.py", "source_file": "outputs/final_state_audit/sample_sizes.csv", "cohort": "FIRED 2016-2020 held out", "target": target, "model": "M1_dynamics", "horizon_days": "available locked horizons", "metric": "number of fires", "uncertainty_method": "not applicable"})
    for keys, _ in key.groupby(["horizon_days", "second_model"]):
        provenance.append({"figure": "si8_bootstrap_distributions", "panel": f"{keys[0]} days", "visual_element": f"M4 minus {keys[1]}", "source_script": "scripts/run_final_state_audit.py", "source_file": "outputs/final_state_audit/paired_bootstrap_distributions.parquet", "cohort": "FIRED 2016-2020 held out", "target": "future mapped area", "model": f"M4_full_geometry vs {keys[1]}", "horizon_days": keys[0], "metric": "paired loss difference", "uncertainty_method": "1000 whole-fire bootstrap replicates"})
    return provenance


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    within = pd.read_csv(SCALE / "within_between_scaling.csv")
    development_exponent = float(within[(within.partition.eq("development")) & within.estimand.eq("within")].estimate.iloc[0])
    growth = add_normalized_geometry(pd.read_parquet(GROWTH), development_exponent)
    growth["future_log_area"] = np.log1p(growth.observed_future_area_km2)
    growth["future_log1p_coupling"] = np.log1p(growth.realized_coupling.clip(lower=0))
    growth["future_acceleration_positive"] = (growth.observed_mean_growth_km2_day > np.expm1(growth.log_mean_daily_growth)).astype(int)
    targets = [
        ("future_log_area", "continuous", "future_mapped_area"),
        ("future_log1p_coupling", "continuous", "future_realized_coupling"),
        ("future_acceleration_positive", "binary", "future_acceleration_sign"),
        ("constraint_like", "binary", "future_growth_deficit"),
        ("terminated_within_horizon", "binary", "future_termination"),
    ]
    metric_parts, prediction_parts, tuning_parts, bootstrap_parts = [], [], [], []
    for target, kind, label in targets:
        metrics, predictions, tuning, draws = evaluate_target(growth, target, kind, label, include_ot=False)
        metric_parts.append(metrics); prediction_parts.append(predictions); tuning_parts.append(tuning); bootstrap_parts.append(draws)
    # Prior OT comparison on its matched sample for the same five targets.
    matched = growth.dropna(subset=["log1p_origin_R", "origin_one_minus_iou"])
    for target, kind, label in targets:
        metrics, predictions, tuning, draws = evaluate_target(matched, target, kind, label + "_OT_matched", include_ot=True)
        metric_parts.append(metrics); prediction_parts.append(predictions); tuning_parts.append(tuning); bootstrap_parts.append(draws)
    # OT reorganization target on valid transitions with exact origin-state matches.
    if TRANSPORT.exists():
        transport = pd.read_parquet(TRANSPORT)
        state = growth.drop_duplicates(["id", "origin_day"]).drop(columns=["lead_days", "target_day"], errors="ignore")
        ot = transport[transport.primary_sample.astype(bool)].merge(state, on=["id", "origin_day", "ig_year", "partition"], how="inner", suffixes=("", "_state"))
        ot = ot.rename(columns={"actual_lead_days": "lead_days"})
        metrics, predictions, tuning, draws = evaluate_target(ot, "reorganization_primary", "continuous", "future_OT_reorganization", include_ot=True)
        metric_parts.append(metrics); prediction_parts.append(predictions); tuning_parts.append(tuning); bootstrap_parts.append(draws)
    metrics = pd.concat(metric_parts, ignore_index=True)
    predictions = pd.concat(prediction_parts, ignore_index=True)
    tuning = pd.concat(tuning_parts, ignore_index=True)
    model_bootstraps = pd.concat(bootstrap_parts, ignore_index=True)
    pairwise, pairwise_bootstraps = add_pairwise(metrics, predictions)
    metrics = metrics.merge(pairwise[pairwise.second_model.eq("M1_dynamics")][["target", "horizon_days", "first_model", "loss_difference_first_minus_second", "ci95_lower", "ci95_upper"]].rename(columns={"first_model": "model", "loss_difference_first_minus_second": "improvement_loss_difference_vs_M1", "ci95_lower": "improvement_ci95_lower", "ci95_upper": "improvement_ci95_upper"}), on=["target", "horizon_days", "model"], how="left")
    detection, curves, calibration, detection_predictions, detection_bootstraps = build_detection(growth)
    scale = scale_audit()
    metrics.to_csv(OUT / "target_horizon_metrics.csv", index=False)
    predictions.to_parquet(OUT / "held_out_predictions.parquet", index=False)
    tuning.to_csv(OUT / "model_tuning.csv", index=False)
    pairwise.to_csv(OUT / "paired_model_comparisons.csv", index=False)
    pairwise_bootstraps.to_parquet(OUT / "paired_bootstrap_distributions.parquet", index=False)
    model_bootstraps.to_parquet(OUT / "model_bootstrap_distributions.parquet", index=False)
    detection.to_csv(OUT / "detection_metrics.csv", index=False)
    curves.to_csv(OUT / "detection_curve_points.csv", index=False)
    calibration.to_csv(OUT / "detection_calibration.csv", index=False)
    detection_predictions.to_parquet(OUT / "detection_predictions.parquet", index=False)
    detection_bootstraps.to_parquet(OUT / "detection_bootstrap_distributions.parquet", index=False)
    scale.to_csv(OUT / "scale_dependence_summary.csv", index=False)
    metrics[["target", "horizon_days", "model", "n_fires", "n_prediction_origins"]].to_csv(OUT / "sample_sizes.csv", index=False)
    provenance = make_figures(metrics, pairwise, detection, curves, calibration, scale, pairwise_bootstraps)
    pd.DataFrame(provenance).to_csv(OUT / "figure_provenance.csv", index=False)
    design = {
        "cohort": "locked 4032-fire FIRED cohort",
        "partition": {"development": "2001-2012", "calibration": "2013-2015", "held_out": "2016-2020"},
        "candidate_exponents": {"one_half": 0.5, "two_thirds": 2/3, "three_quarters": 0.75, "development": development_exponent},
        "horizons_days": LEADS, "alphas": ALPHAS, "bootstrap_replicates": BOOTSTRAPS,
        "detection_target": "existing lead-specific lower-decile q indicator for the fixed 3-day interval from day 7 through day 10; endpoint day-10 predictors are contemporaneous",
        "prediction_targets": [label for _, _, label in targets] + ["future_OT_reorganization"],
        "input_sha256": {str(path): sha256(path) for path in (GROWTH, TRANSPORT) if path.exists()},
        "stopping_rule": "No exponent, threshold, lifecycle partition, deficit cutoff, or horizon searches after these prespecified tests.",
    }
    (OUT / "design_lock.json").write_text(json.dumps(design, indent=2) + "\n")
    report = {
        "development_exponent": development_exponent,
        "rows": len(growth), "fires": int(growth.id.nunique()),
        "held_out_rows": int(growth.partition.eq("held_out").sum()), "held_out_fires": int(growth[growth.partition.eq("held_out")].id.nunique()),
        "detection": detection.to_dict(orient="records"),
        "outputs": sorted(path.name for path in OUT.iterdir()),
    }
    (OUT / "run_report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
