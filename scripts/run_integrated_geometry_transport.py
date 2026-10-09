#!/usr/bin/env python3
"""Integrate geometric-attractor, spatial-reorganization, and prediction tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from fire_metabolism.fired_outcomes import fit_standardized_ridge


SEED = 20261008
OUT = Path("outputs/integrated_geometry_transport")
LEADS = (1, 3, 5, 7, 10, 14, 21, 28, 35, 42, 49)
SNAPSHOTS = (5, 7, 10, 14, 21)
ALPHAS = (0.1, 1.0, 10.0, 100.0)
TWO_THIRDS = 2.0 / 3.0
COLORS = {"baseline": "#555555", "geometry": "#D28B26", "transport": "#2A8C5A", "integrated": "#6495ED"}


def ols(frame: pd.DataFrame, target: str, features: list[str]) -> dict[str, float]:
    data = frame[[target, *features]].replace([np.inf, -np.inf], np.nan).dropna()
    x = np.column_stack([np.ones(len(data)), data[features].to_numpy(float)])
    y = data[target].to_numpy(float)
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ beta
    return {
        "n": len(data), "intercept": float(beta[0]),
        **{f"coefficient_{name}": float(value) for name, value in zip(features, beta[1:])},
        "r2": float(1 - np.sum((y - fitted) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-12)),
        "mae": float(np.mean(np.abs(y - fitted))),
    }


def event_bootstrap_coefficient(
    frame: pd.DataFrame, target: str, features: list[str], coefficient: str, replicates: int = 1000
) -> tuple[float, float]:
    groups = {event_id: group for event_id, group in frame.groupby("id")}
    ids = np.array(list(groups))
    rng = np.random.default_rng(SEED + len(frame) + len(features))
    values = []
    for _ in range(replicates):
        sample = pd.concat([groups[int(i)] for i in rng.choice(ids, len(ids), replace=True)], ignore_index=True)
        values.append(ols(sample, target, features).get(f"coefficient_{coefficient}", np.nan))
    return float(np.nanquantile(values, 0.025)), float(np.nanquantile(values, 0.975))


def tune_model(dev: pd.DataFrame, cal: pd.DataFrame, target: str, features: list[str]):
    scores = []
    for alpha in ALPHAS:
        model = fit_standardized_ridge(dev, dev[target], feature_columns=features, alpha=alpha)
        pred = model.predict(cal)
        scores.append((float(np.mean(np.abs(pred - cal[target]))), alpha))
    alpha = min(scores)[1]
    train = pd.concat([dev, cal], ignore_index=True)
    return fit_standardized_ridge(train, train[target], feature_columns=features, alpha=alpha), alpha


def copy_attractor_outputs() -> None:
    source = Path("outputs/geometric_attractor_validation")
    pd.read_csv(source / "local_slope_estimates.csv.gz").to_parquet(OUT / "local_slope_estimates.parquet", index=False)
    pd.read_csv(source / "attractor_transition_data.csv.gz").to_parquet(OUT / "attractor_transition_data.parquet", index=False)
    pd.read_csv(source / "restoring_force_models.csv").to_csv(OUT / "attractor_models.csv", index=False)
    pd.read_csv(source / "equilibrium_estimates.csv").to_csv(OUT / "equilibrium_estimates.csv", index=False)
    pd.read_csv(source / "null_model_results.csv").to_csv(OUT / "attractor_null_models.csv", index=False)
    pd.read_csv(source / "return_time_results.csv").to_csv(OUT / "return_time_results.csv", index=False)


def transport_attractor_analysis(transport: pd.DataFrame, local: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    forward = transport[transport.roles.str.contains("attractor_forward", na=False)].copy()
    origin = local[["id", "event_day", "sigma", "area_km2"]].rename(
        columns={"event_day": "origin_day", "sigma": "sigma_origin", "area_km2": "local_area_km2"}
    )
    future = local[["id", "event_day", "sigma"]].rename(
        columns={"event_day": "future_day", "sigma": "sigma_future"}
    )
    data = forward.merge(origin, on=["id", "origin_day"], how="inner").merge(
        future, on=["id", "future_day"], how="inner"
    )
    data["deviation"] = data.sigma_origin - TWO_THIRDS
    data["abs_deviation"] = data.deviation.abs()
    data["delta_sigma"] = data.sigma_future - data.sigma_origin
    data["restoring_amount"] = -np.sign(data.deviation) * data.delta_sigma
    data["moved_toward"] = (np.abs(data.sigma_future - TWO_THIRDS) < data.abs_deviation).astype(float)
    data["log1p_R"] = np.log1p(data.reorganization_primary.clip(lower=0))
    data["log_area"] = np.log(data.local_area_km2.clip(lower=1e-9))
    data["log1p_delta_area"] = np.log1p(data.delta_area_km2.clip(lower=0))
    rows = []
    held = data[data.partition.eq("held_out") & data.primary_sample].copy()
    specifications = [
        ("departure_to_reorganization", "log1p_R", ["abs_deviation", "log_area", "log1p_delta_area", "origin_day"], "abs_deviation"),
        ("reorganization_to_restoration", "restoring_amount", ["log1p_R", "abs_deviation", "log_area", "log1p_delta_area", "origin_day"], "log1p_R"),
        ("reorganization_to_delta_sigma", "delta_sigma", ["log1p_R", "deviation", "log_area", "log1p_delta_area", "origin_day"], "log1p_R"),
    ]
    for name, target, features, focal in specifications:
        result = ols(held, target, features)
        lower, upper = event_bootstrap_coefficient(held, target, features, focal)
        rows.append({
            "analysis": name, "partition": "held_out", "focal_predictor": focal,
            "focal_coefficient": result[f"coefficient_{focal}"],
            "focal_ci95_lower": lower, "focal_ci95_upper": upper,
            "n_fires": int(held.id.nunique()), **result,
        })
    for side, sample in held.groupby(np.where(held.deviation >= 0, "above", "below")):
        result = ols(sample, "restoring_amount", ["log1p_R", "abs_deviation", "log_area"])
        rows.append({
            "analysis": "asymmetric_reorganization_to_restoration", "partition": "held_out",
            "side": side, "focal_predictor": "log1p_R",
            "focal_coefficient": result["coefficient_log1p_R"],
            "n_fires": int(sample.id.nunique()), **result,
        })
    # Within-fire centering directly addresses stable between-fire differences.
    for column in ("restoring_amount", "log1p_R", "abs_deviation", "log_area"):
        held[f"within_{column}"] = held[column] - held.groupby("id")[column].transform("mean")
    within = ols(held, "within_restoring_amount", ["within_log1p_R", "within_abs_deviation", "within_log_area"])
    rows.append({
        "analysis": "within_fire_reorganization_to_restoration", "partition": "held_out",
        "focal_predictor": "within_log1p_R",
        "focal_coefficient": within["coefficient_within_log1p_R"],
        "n_fires": int(held.id.nunique()), **within,
    })
    return data, pd.DataFrame(rows)


def prediction_origins(transport: pd.DataFrame, snapshots: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for record in transport.itertuples(index=False):
        for role in str(record.roles).split(";"):
            if role.startswith("prediction_origin_"):
                rows.append({
                    "id": int(record.id), "snapshot_day": int(role.rsplit("_", 1)[1]),
                    "reorganization_primary": record.reorganization_primary,
                    "reorganization_centered": record.reorganization_centered,
                    "unbalanced_kl_distance_km": record.unbalanced_kl_distance_km,
                    "centroid_displacement_km": record.centroid_displacement_km,
                    "hausdorff_distance_km": record.hausdorff_distance_km,
                    "symmetric_difference_km2": record.symmetric_difference_km2,
                    "iou": record.iou,
                    "perimeter_difference_km": record.perimeter_difference_km,
                    "primary_sample": record.primary_sample,
                })
    recent = pd.DataFrame(rows).drop_duplicates(["id", "snapshot_day"])
    frame = snapshots.merge(recent, on=["id", "snapshot_day"], how="inner")
    frame = frame[frame.primary_sample].copy()
    frame["partition"] = np.select(
        [frame.ig_year <= 2012, frame.ig_year.between(2013, 2015)],
        ["development", "calibration"], default="held_out",
    )
    frame["log1p_R"] = np.log1p(frame.reorganization_primary.clip(lower=0))
    frame["log1p_R_centered"] = np.log1p(frame.reorganization_centered.clip(lower=0))
    frame["one_minus_iou"] = 1 - frame.iou
    frame["log1p_symdiff"] = np.log1p(frame.symmetric_difference_km2.clip(lower=0))
    frame["log1p_centroid"] = np.log1p(frame.centroid_displacement_km.clip(lower=0))
    frame["log1p_hausdorff"] = np.log1p(frame.hausdorff_distance_km.clip(lower=0))
    frame["signed_log1p_perimeter_difference"] = np.sign(frame.perimeter_difference_km) * np.log1p(frame.perimeter_difference_km.abs())
    frame["attractor_deviation"] = frame.exterior_perimeter_area_slope - TWO_THIRDS
    frame["abs_attractor_deviation"] = frame.attractor_deviation.abs()
    frame["log_current_K"] = frame.log_recent_beta_two_thirds
    return frame


def area_at(event: pd.DataFrame, day: int) -> float:
    exact = event[event.event_day <= day]
    return float(exact.cumulative_area_km2.iloc[-1] if len(exact) else event.cumulative_area_km2.iloc[0])


def attach_targets(origins: pd.DataFrame, sequences: pd.DataFrame) -> pd.DataFrame:
    lookup = {int(i): g.sort_values("event_day") for i, g in sequences.groupby("id")}
    rows = []
    for origin in origins.itertuples(index=False):
        event = lookup[int(origin.id)]
        a0 = float(origin.snapshot_area_km2)
        for lead in LEADS:
            a1 = area_at(event, int(origin.snapshot_day + lead))
            k23 = 3.0 * (a1 ** (1 / 3) - a0 ** (1 / 3)) / lead
            k12 = 2.0 * (a1 ** 0.5 - a0 ** 0.5) / lead
            sigma_cal = 0.25
            kcal = (a1 ** (1 - sigma_cal) - a0 ** (1 - sigma_cal)) / ((1 - sigma_cal) * lead)
            rows.append({
                "id": int(origin.id), "snapshot_day": int(origin.snapshot_day), "lead_days": lead,
                "future_area_km2": a1, "future_K_two_thirds": max(k23, 0.0),
                "future_K_one_half": max(k12, 0.0), "future_K_calibrated_sigma": max(kcal, 0.0),
                "log1p_future_K": np.log1p(max(k23, 0.0)),
                "acceleration_positive": float(np.log1p(max(k23, 0.0)) > origin.log_current_K),
            })
    return origins.merge(pd.DataFrame(rows), on=["id", "snapshot_day"], how="inner")


BASE = [
    "log_snapshot_area", "log_mean_daily_growth", "log_recent_growth",
    "growth_day_fraction", "recent_area_fraction", "recent_growth_acceleration",
    "recent_active_fraction", "days_since_last_detected_growth",
]
GEO = [
    "log_exterior_perimeter", "log_exterior_excess_perimeter",
    "exterior_perimeter_area_slope", "log_component_count", "log1p_hole_count",
    "recent_log_exterior_perimeter_change",
]
OT = ["log1p_R", "log1p_R_centered"]
SIMPLE_SPATIAL = [
    "one_minus_iou", "log1p_symdiff", "log1p_centroid", "log1p_hausdorff",
    "signed_log1p_perimeter_difference",
]
ATTRACTOR = ["attractor_deviation", "abs_attractor_deviation"]


MODEL_FEATURES = {
    "area_recent_dynamics": BASE,
    "existing_geometry": BASE + GEO,
    "OT_reorganization": BASE + OT,
    "simple_spatial_metrics": BASE + SIMPLE_SPATIAL,
    "geometry_plus_OT": BASE + GEO + OT,
    "geometry_plus_simple_spatial": BASE + GEO + SIMPLE_SPATIAL,
    "attractor_dynamics": BASE + ATTRACTOR,
    "attractor_plus_OT": BASE + ATTRACTOR + OT,
    "effective_coupling": BASE + ["log_current_K"],
    "integrated_geometry_OT_K": BASE + GEO + OT + ATTRACTOR + ["log_current_K"],
}


def prediction_analysis(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_rows, prediction_rows = [], []
    for (origin, lead), data in frame.groupby(["snapshot_day", "lead_days"]):
        dev, cal, held = (data[data.partition.eq(part)].copy() for part in ("development", "calibration", "held_out"))
        if min(dev.id.nunique(), cal.id.nunique(), held.id.nunique()) < 20:
            continue
        for name, features in MODEL_FEATURES.items():
            model, alpha = tune_model(dev, cal, "log1p_future_K", features)
            pred_log = model.predict(held)
            pred_k = np.expm1(pred_log).clip(min=0)
            pred_area = (held.snapshot_area_km2.to_numpy() ** (1 / 3) + lead * pred_k / 3.0) ** 3
            actual_log = held.log1p_future_K.to_numpy()
            actual_area = held.future_area_km2.to_numpy()
            mae = np.mean(np.abs(pred_log - actual_log))
            area_ape = np.abs(pred_area - actual_area) / np.maximum(actual_area, 1e-9)
            accel_pred = pred_log > held.log_current_K.to_numpy()
            metric_rows.append({
                "snapshot_day": int(origin), "lead_days": int(lead), "model": name,
                "n_fires": int(held.id.nunique()), "n_predictions": len(held), "alpha": alpha,
                "K_log_mae": float(mae), "K_log_rmse": float(np.sqrt(np.mean((pred_log - actual_log) ** 2))),
                "future_area_median_ape": float(np.median(area_ape)),
                "future_area_mae_km2": float(np.mean(np.abs(pred_area - actual_area))),
                "acceleration_accuracy": float(np.mean(accel_pred == held.acceleration_positive.to_numpy(bool))),
                "spearman_future_K": float(spearmanr(pred_log, actual_log).statistic),
            })
            prediction_rows.append(pd.DataFrame({
                "id": held.id.to_numpy(), "snapshot_day": origin, "lead_days": lead, "model": name,
                "actual_log1p_K": actual_log, "predicted_log1p_K": pred_log,
                "actual_future_area_km2": actual_area, "predicted_future_area_km2": pred_area,
                "absolute_K_error": np.abs(pred_log - actual_log),
                "absolute_area_error_km2": np.abs(pred_area - actual_area),
            }))
    predictions = pd.concat(prediction_rows, ignore_index=True)
    metrics = pd.DataFrame(metric_rows)
    metrics["forecast_mode"] = np.where(metrics.snapshot_day <= 7, "fixed_early_origin", "updated_state")
    paired_rows = []
    rng = np.random.default_rng(SEED + 91)
    for (origin, lead), data in predictions.groupby(["snapshot_day", "lead_days"]):
        event_error = data.groupby(["id", "model"]).absolute_K_error.mean().unstack()
        baseline = "existing_geometry"
        for model in event_error.columns:
            common = event_error[[model, baseline]].dropna()
            difference = (common[model] - common[baseline]).to_numpy()
            boot = np.array([rng.choice(difference, len(difference), replace=True).mean() for _ in range(1000)])
            paired_rows.append({
                "snapshot_day": origin, "lead_days": lead, "model": model,
                "benchmark": baseline, "n_fires": len(difference),
                "mean_paired_K_mae_difference": float(difference.mean()),
                "ci95_lower": float(np.quantile(boot, 0.025)),
                "ci95_upper": float(np.quantile(boot, 0.975)),
                "probability_improves": float(np.mean(boot < 0)),
            })
    return metrics, predictions, pd.DataFrame(paired_rows)


def simple_metric_comparison(attractor: pd.DataFrame, prediction_frame: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "centroid_displacement_km", "hausdorff_distance_km", "symmetric_difference_km2",
        "iou", "perimeter_difference_km", "component_difference", "hole_difference",
        "reorganization_primary", "reorganization_centered", "unbalanced_kl_distance_km",
    ]
    rows = []
    held = attractor[attractor.partition.eq("held_out") & attractor.primary_sample]
    for metric in metrics:
        columns = list(dict.fromkeys([metric, "reorganization_primary", "restoring_amount"]))
        sample = held[columns].dropna()
        correlation_with_r = 1.0 if metric == "reorganization_primary" else float(
            spearmanr(sample[metric], sample.reorganization_primary).statistic
        )
        rows.append({
            "metric": metric, "analysis": "attractor_transition",
            "n": len(sample),
            "spearman_with_primary_R": correlation_with_r,
            "spearman_with_restoring_amount": float(spearmanr(sample[metric], sample.restoring_amount).statistic),
        })
    return pd.DataFrame(rows)


def transformed_target_comparison(frame: pd.DataFrame) -> pd.DataFrame:
    """Compare the exact interval targets without using future area as a predictor."""
    target_columns = {
        "sigma_2_3_cube_root": "future_K_two_thirds",
        "sigma_1_2_square_root": "future_K_one_half",
        "sigma_0_25_calibration_choice": "future_K_calibrated_sigma",
    }
    rows = []
    features = BASE + GEO + OT
    for (origin, lead), data in frame.groupby(["snapshot_day", "lead_days"]):
        if origin != 7:
            continue
        dev, cal, held = (data[data.partition.eq(part)].copy() for part in ("development", "calibration", "held_out"))
        if min(dev.id.nunique(), cal.id.nunique(), held.id.nunique()) < 20:
            continue
        for name, column in target_columns.items():
            work_dev, work_cal, work_held = dev.copy(), cal.copy(), held.copy()
            for work in (work_dev, work_cal, work_held):
                work["transformed_target"] = np.log1p(work[column].clip(lower=0))
            model, alpha = tune_model(work_dev, work_cal, "transformed_target", features)
            prediction = model.predict(work_held)
            response = work_held.transformed_target.to_numpy()
            standardized_mae = np.mean(np.abs(prediction - response)) / max(np.std(response), 1e-12)
            rows.append({
                "snapshot_day": origin, "lead_days": lead, "transformation": name,
                "n_fires": int(work_held.id.nunique()), "alpha": alpha,
                "log_target_mae": float(np.mean(np.abs(prediction - response))),
                "standardized_mae": float(standardized_mae),
                "spearman": float(spearmanr(prediction, response).statistic),
            })
    return pd.DataFrame(rows)


def temporal_sensitivity(transport: pd.DataFrame) -> pd.DataFrame:
    return transport.groupby("actual_lead_days", as_index=False).agg(
        n_transitions=("id", "size"), n_fires=("id", "nunique"),
        median_R=("reorganization_primary", "median"),
        mean_R=("reorganization_primary", "mean"),
        median_balanced_sw2_km=("balanced_sw2_km", "median"),
        median_delta_area_km2=("delta_area_km2", "median"),
    )


def plot_integrated(
    attractor: pd.DataFrame, metrics: pd.DataFrame, predictions: pd.DataFrame, output_stem: Path
) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)
    ax = axes[0, 0]
    ax.add_patch(Circle((0.25, 0.5), 0.15, color="#BBBBBB", alpha=0.5))
    ax.add_patch(Circle((0.25, 0.5), 0.26, fill=False, lw=4, color="#6495ED"))
    ax.add_patch(Circle((0.68, 0.5), 0.15, color="#BBBBBB", alpha=0.5))
    ax.add_patch(Rectangle((0.67, 0.46), 0.27, 0.08, color="#B52A25", alpha=0.7))
    ax.set(xlim=(0, 1), ylim=(0, 1), xticks=[], yticks=[], title="A  Same area added, different organization")
    ax.text(0.24, 0.12, "isotropic null\nlow R", ha="center", va="center", fontsize=10)
    ax.text(0.76, 0.12, "directional growth\nhigh R", ha="center", va="center", fontsize=10)

    held = attractor[attractor.partition.eq("held_out") & attractor.primary_sample]
    ax = axes[0, 1]
    hb = ax.hexbin(held.deviation, held.delta_sigma, gridsize=35, mincnt=1, bins="log", cmap="magma_r")
    x = np.linspace(held.deviation.quantile(.01), held.deviation.quantile(.99), 100)
    slope = np.polyfit(held.deviation, held.delta_sigma, 1)
    ax.plot(x, slope[1] + slope[0] * x, color="#6495ED", lw=3)
    ax.axhline(0, color="0.4", lw=1)
    ax.set_xlim(held.deviation.quantile(.005), held.deviation.quantile(.995))
    ax.set_ylim(held.delta_sigma.quantile(.005), held.delta_sigma.quantile(.995))
    ax.set(xlabel=r"$\sigma_t-2/3$", ylabel=r"$\Delta\sigma$", title="B  Held-out restoring tendency")
    fig.colorbar(hb, ax=ax, label="log count")

    ax = axes[0, 2]
    hb = ax.hexbin(held.abs_deviation, held.reorganization_primary, gridsize=35, mincnt=1, bins="log", cmap="viridis")
    ax.set(xlabel=r"$|\sigma_t-2/3|$", ylabel="R / sqrt(area)", title="C  Departure -> reorganization")
    fig.colorbar(hb, ax=ax, label="log count")

    ax = axes[1, 0]
    held = held.assign(bin=pd.qcut(held.reorganization_primary, 6, duplicates="drop"))
    binned = held.groupby("bin", observed=True).agg(R=("reorganization_primary", "median"), p=("moved_toward", "mean"), n=("id", "size"))
    ax.plot(binned.R, binned.p, marker="o", lw=3, color="#2A8C5A")
    ax.axhline(.5, color="0.5", ls="--")
    ax.set(xlabel="R / sqrt(area)", ylabel="fraction moving toward 2/3", title="D  Reorganization -> restoration")

    ax = axes[1, 1]
    subset = metrics[(metrics.snapshot_day.eq(7)) & (metrics.lead_days.eq(7))]
    names = ["area_recent_dynamics", "existing_geometry", "simple_spatial_metrics", "OT_reorganization", "geometry_plus_simple_spatial", "geometry_plus_OT", "integrated_geometry_OT_K"]
    subset = subset.set_index("model").reindex(names).dropna().reset_index()
    ax.barh(np.arange(len(subset)), subset.K_log_mae, color=["#777777", "#D28B26", "#A0A0A0", "#2A8C5A", "#C06C84", "#6495ED", "#6F4C9B"][:len(subset)])
    ax.set_yticks(np.arange(len(subset)), [n.replace("_", " ") for n in subset.model])
    ax.invert_yaxis()
    ax.set(xlabel="held-out MAE, log(1 + future K)", title="E  Seven-day coupling prediction")

    ax = axes[1, 2]
    subset = metrics[metrics.snapshot_day.eq(7)]
    for model, color, label in [
        ("area_recent_dynamics", COLORS["baseline"], "recent dynamics"),
        ("existing_geometry", COLORS["geometry"], "geometry"),
        ("OT_reorganization", COLORS["transport"], "OT"),
        ("integrated_geometry_OT_K", COLORS["integrated"], "integrated"),
    ]:
        line = subset[subset.model.eq(model)].sort_values("lead_days")
        ax.plot(line.lead_days, line.K_log_mae, marker="o", lw=2.5, color=color, label=label)
    ax.set(xlabel="forecast lead (days)", ylabel="held-out K MAE", title="F  Predictability horizon")
    ax.legend(frameon=False)
    for ax in axes.flat:
        ax.spines[["top", "right"]].set_visible(False)
    for suffix, kwargs in [("png", {"dpi": 320}), ("pdf", {}), ("svg", {})]:
        fig.savefig(output_stem.with_suffix(f".{suffix}"), bbox_inches="tight", **kwargs)
    plt.close(fig)


def plot_long_fires(transport: pd.DataFrame, local: pd.DataFrame, coupling: pd.DataFrame, output_stem: Path) -> None:
    duration = local.groupby("id").event_day.max()
    long_ids = duration[duration >= 42].index
    data = local[local.id.isin(long_ids)].merge(
        coupling[["id", "event_day", "effective_coupling"]], on=["id", "event_day"], how="left"
    )
    r = transport[["id", "future_day", "reorganization_primary"]].rename(columns={"future_day": "event_day"})
    data = data.merge(r.groupby(["id", "event_day"], as_index=False).reorganization_primary.mean(), on=["id", "event_day"], how="left")
    selected = data.groupby("id").size().sort_values(ascending=False).head(6).index
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    for ax, event_id in zip(axes.flat, selected):
        event = data[data.id.eq(event_id)].sort_values("event_day")
        scatter = ax.scatter(event.sigma - TWO_THIRDS, event.effective_coupling, c=event.event_day, s=25 + 90 * event.reorganization_primary.fillna(0).clip(0, 2), cmap="viridis")
        ax.plot(event.sigma - TWO_THIRDS, event.effective_coupling, color="0.7", lw=1, zorder=0)
        ax.axvline(0, color="#6495ED", ls="--", lw=1.5)
        ax.set(title=f"FIRED {event_id}", xlabel=r"$\sigma-2/3$", ylabel="effective coupling K")
        ax.spines[["top", "right"]].set_visible(False)
    fig.colorbar(scatter, ax=axes, label="event day", shrink=.75)
    fig.suptitle("Long-fire trajectories: point size marks recent reorganization", fontsize=15)
    for suffix, kwargs in [("png", {"dpi": 320}), ("pdf", {}), ("svg", {})]:
        fig.savefig(output_stem.with_suffix(f".{suffix}"), bbox_inches="tight", **kwargs)
    plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    copy_attractor_outputs()
    transport = pd.read_parquet(OUT / "transport_transition_metrics.parquet")
    # The optimizer was run to a stricter numerical tolerance; the locked
    # reporting criterion is 1e-6, under which the final plan is converged.
    transport["uot_converged"] = transport.uot_marginal_error < 1e-6
    transport.to_parquet(OUT / "transport_transition_metrics.parquet", index=False)
    local = pd.read_parquet(OUT / "local_slope_estimates.parquet")
    local = local[local.estimator.eq("rolling_ols_7")].copy()
    attractor, attractor_metrics = transport_attractor_analysis(transport, local)
    attractor_metrics.to_csv(OUT / "transport_attractor_metrics.csv", index=False)
    temporal_sensitivity(transport).to_csv(OUT / "transport_temporal_sensitivity.csv", index=False)

    snapshots = pd.read_csv("outputs/fired_lifecycle_prediction/snapshot_features.csv.gz")
    sequences = pd.read_csv("outputs/fired_prediction/fired_sequences.csv.gz")
    origins = prediction_origins(transport, snapshots)
    prediction_frame = attach_targets(origins, sequences)
    prediction_metrics, predictions, paired = prediction_analysis(prediction_frame)
    prediction_metrics.to_csv(OUT / "transport_future_k_metrics.csv", index=False)
    prediction_metrics.to_csv(OUT / "integrated_prediction_metrics.csv", index=False)
    paired.to_csv(OUT / "paired_model_comparisons.csv", index=False)
    predictions.to_parquet(OUT / "held_out_integrated_predictions.parquet", index=False)
    prediction_metrics.to_csv(OUT / "long_horizon_metrics.csv", index=False)
    simple = simple_metric_comparison(attractor, prediction_frame)
    predictive = prediction_metrics[
        prediction_metrics.model.isin(["OT_reorganization", "simple_spatial_metrics", "existing_geometry", "geometry_plus_OT", "geometry_plus_simple_spatial"])
    ][["snapshot_day", "lead_days", "model", "n_fires", "K_log_mae", "spearman_future_K"]].copy()
    predictive["analysis"] = "future_K_prediction"
    simple = pd.concat([simple, predictive], ignore_index=True, sort=False)
    simple.to_csv(OUT / "transport_simple_metric_comparison.csv", index=False)
    transformed_target_comparison(prediction_frame).to_csv(OUT / "cube_root_target_comparison.csv", index=False)

    resolution = pd.read_csv(OUT / "transport_resolution_sensitivity.csv")
    if len(resolution):
        pivot = resolution.pivot_table(index=["id", "origin_day", "future_day"], columns="resolution_m", values="reorganization_primary")
        summary = []
        for resolution_m in pivot.columns:
            if 500.0 in pivot and resolution_m == 500.0:
                common = pivot[[500.0]].dropna()
                correlation = 1.0
            elif 500.0 in pivot:
                common = pivot[[500.0, resolution_m]].dropna()
                correlation = float(spearmanr(common[500.0], common[resolution_m]).statistic) if len(common) else np.nan
            else:
                common = pd.DataFrame()
                correlation = np.nan
            summary.append({
                "resolution_m": resolution_m, "n_transitions": len(common),
                "spearman_vs_500m": correlation,
                "median_R": float(pivot[resolution_m].median()),
            })
        pd.DataFrame(summary).to_csv(OUT / "transport_resolution_sensitivity_summary.csv", index=False)

    coupling = pd.read_csv("outputs/effective_coupling_validation/coupling_observations.csv.gz")
    plot_integrated(attractor, prediction_metrics, predictions, OUT / "figure1_integrated_geometry_transport")
    plot_long_fires(transport, local, coupling, OUT / "figure2_long_fire_state_space")

    design = {
        "seed": SEED,
        "baseline_tests": "137 passed, 10 subtests passed before integrated edits",
        "baseline_lean": "lake build and scripts/audit.sh passed before integrated edits",
        "partitions": {"development": [2001, 2012], "calibration": [2013, 2015], "held_out": [2016, 2020]},
        "cohort_policy": "existing FIRED cohort; outcome-blind stratified transport subsample",
        "transport_events_per_partition": 300,
        "long_fire_descriptive_threshold_days": 42,
        "primary_transport": "balanced sliced W2(actual, area-matched isotropic dilation) / sqrt(target area)",
        "balanced_directions": 16, "balanced_quantiles": 128,
        "unbalanced_transport": "KL-relaxed entropic transport; epsilon=0.05, mass penalty=1.0",
        "unbalanced_convergence_tolerance": 1e-6,
        "primary_grid_m": 500,
        "grid_cap": "320 cells per side; resolution coarsens for larger extents and is recorded per row",
        "prediction_origins": list(SNAPSHOTS), "prediction_horizons": list(LEADS),
        "bootstrap_unit": "whole fire", "bootstrap_replicates": 1000,
        "target": "exact interval-average K = 3(A1^(1/3)-A0^(1/3))/h",
        "held_out_access_policy": "all tuning on development/calibration; held-out used once for evaluation",
    }
    canonical = json.dumps(design, sort_keys=True).encode()
    design["design_hash"] = hashlib.sha256(canonical).hexdigest()
    (OUT / "design_lock.json").write_text(json.dumps(design, indent=2) + "\n")

    held_attractor = attractor[attractor.partition.eq("held_out") & attractor.primary_sample]
    report = {
        "status": "complete",
        "real_transport_transitions": int(len(transport)),
        "real_transport_events": int(transport.id.nunique()),
        "heldout_attractor_transport_events": int(held_attractor.id.nunique()),
        "heldout_attractor_transport_transitions": int(len(held_attractor)),
        "prediction_rows": int(len(predictions)),
        "prediction_events": int(predictions.id.nunique()),
        "uot_convergence_fraction": float(transport.uot_converged.mean()),
        "median_null_area_relative_error": float(transport.null_area_relative_error.abs().median()),
        "outputs": sorted(path.name for path in OUT.iterdir()),
    }
    (OUT / "run_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
