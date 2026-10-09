#!/usr/bin/env python3
"""Validate unresolved realization deficits in the locked FIRED cohort."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from fire_metabolism.fired_outcomes import fit_standardized_ridge
from fire_metabolism.latent_constraints import (
    DEFAULT_LEADS,
    add_realization_residuals,
    attach_constraint_indicator,
    binary_scores,
    build_interval_table,
    development_thresholds,
    event_bootstrap_mean_ci,
    fit_constraint_hazards,
    predict_constraint_probability,
    robust_fixed_restoring,
    tune_ridge,
)


SEED = 20261009
OUT = Path("outputs/latent_constraint_validation")
SNAPSHOTS = Path("outputs/fired_lifecycle_prediction/snapshot_features.csv.gz")
SEQUENCES = Path("outputs/fired_prediction/fired_sequences.csv.gz")
TRANSITIONS = Path("outputs/geometric_attractor_validation/attractor_transition_data.csv.gz")
TRANSPORT = Path("outputs/integrated_geometry_transport/transport_transition_metrics.parquet")

BASE = ["log1p_lead", "log_origin_area", "origin_age_scaled"]
DYNAMICS = [
    "log_mean_daily_growth", "log_recent_growth", "growth_day_fraction",
    "recent_area_fraction", "recent_beta_trend", "recent_growth_acceleration",
    "latest_growth_fraction_of_peak", "days_since_observed_peak",
    "recent_active_fraction", "days_since_last_detected_growth",
]
GEOMETRY = [
    "log_exterior_perimeter", "log_exterior_excess_perimeter",
    "exterior_perimeter_area_slope", "log_component_count", "log1p_hole_count",
    "recent_log_exterior_perimeter_change",
]


def make_predictions(intervals: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object], pd.DataFrame]:
    feature_sets = {
        "age_area": BASE,
        "recent_dynamics": BASE + DYNAMICS,
        "geometry_dynamics": BASE + DYNAMICS + GEOMETRY,
    }
    model, selected, tuning = tune_ridge(
        intervals,
        target="log1p_observed_mean_growth",
        feature_sets=feature_sets,
    )
    residuals = add_realization_residuals(intervals, model.predict(intervals))
    thresholds = development_thresholds(residuals)
    residuals = attach_constraint_indicator(residuals, thresholds)
    return residuals, selected, tuning


def attach_origin_ot(residuals: pd.DataFrame) -> pd.DataFrame:
    """Attach transport accumulated through the forecast origin when available."""
    result = residuals.copy()
    result["log1p_origin_R"] = np.nan
    result["origin_one_minus_iou"] = np.nan
    if not TRANSPORT.exists():
        return result
    transport = pd.read_parquet(TRANSPORT)
    rows = []
    for record in transport.itertuples(index=False):
        for role in str(record.roles).split(";"):
            if role.startswith("prediction_origin_"):
                rows.append(
                    {
                        "id": int(record.id),
                        "origin_day": int(role.rsplit("_", 1)[1]),
                        "log1p_origin_R": float(np.log1p(max(record.reorganization_primary, 0))),
                        "origin_one_minus_iou": float(1 - record.iou),
                    }
                )
    origin = pd.DataFrame(rows).drop_duplicates(["id", "origin_day"])
    result = result.drop(columns=["log1p_origin_R", "origin_one_minus_iou"]).merge(
        origin, on=["id", "origin_day"], how="left", validate="many_to_one"
    )
    return result


def hazard_analysis(residuals: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    hazard_features = {
        "H0_constant": [],
        "H1_age_area": BASE,
        "H2_recent_dynamics": BASE + DYNAMICS,
        "H3_geometry": BASE + DYNAMICS + GEOMETRY,
    }
    models, definitions = fit_constraint_hazards(residuals, hazard_features)
    held = residuals[residuals.partition.eq("held_out")].copy()
    score_rows = []
    predictions = []
    for name, model in models.items():
        probability = predict_constraint_probability(model, held)
        score_rows.append({"model": name, "sample": "all_held_out", "n": len(held), **binary_scores(held.constraint_like, probability)})
        predictions.append(pd.DataFrame({"id": held.id, "origin_day": held.origin_day, "lead_days": held.lead_days, "model": name, "constraint_probability": probability}))
    matched = residuals.dropna(subset=["log1p_origin_R", "origin_one_minus_iou"]).copy()
    if len(matched):
        ot_features = BASE + DYNAMICS + GEOMETRY + ["log1p_origin_R", "origin_one_minus_iou"]
        ot_models, ot_definition = fit_constraint_hazards(matched, {"H4_geometry_OT": ot_features})
        held_ot = matched[matched.partition.eq("held_out")].copy()
        geometry_probability = predict_constraint_probability(models["H3_geometry"], held_ot)
        score_rows.append({"model": "H3_geometry_OT_matched", "sample": "OT_matched_held_out", "n": len(held_ot), **binary_scores(held_ot.constraint_like, geometry_probability)})
        definitions = pd.concat(
            [definitions, pd.DataFrame([{"model": "H3_geometry_OT_matched", "alpha": 1.0, "features": ";".join(BASE + DYNAMICS + GEOMETRY), "train_event_rate": float(matched[matched.partition.ne("held_out")].constraint_like.mean())}])],
            ignore_index=True,
        )
        probability = predict_constraint_probability(ot_models["H4_geometry_OT"], held_ot)
        score_rows.append({"model": "H4_geometry_OT", "sample": "OT_matched_held_out", "n": len(held_ot), **binary_scores(held_ot.constraint_like, probability)})
        predictions.append(pd.DataFrame({"id": held_ot.id, "origin_day": held_ot.origin_day, "lead_days": held_ot.lead_days, "model": "H4_geometry_OT", "constraint_probability": probability}))
        definitions = pd.concat([definitions, ot_definition], ignore_index=True)
    return definitions.merge(pd.DataFrame(score_rows), on="model", how="left"), pd.concat(predictions), models


def mixture_prediction_metrics(
    residuals: pd.DataFrame,
    probability_table: pd.DataFrame,
) -> pd.DataFrame:
    train = residuals[residuals.partition.ne("held_out")]
    held = residuals[residuals.partition.eq("held_out")].copy()
    conditional = (
        train.groupby(["lead_days", "constraint_like"]).realization_residual_q.mean().unstack(fill_value=0)
    )
    rows = []
    name_map = {
        "H0_constant": "P2_constant_hazard",
        "H1_age_area": "P3_age_area_hazard",
        "H2_recent_dynamics": "P3_state_hazard",
        "H3_geometry": "P4_geometry_hazard",
        "H4_geometry_OT": "P5_geometry_OT_hazard",
    }
    for model, probability in probability_table.groupby("model"):
        data = held.merge(probability, on=["id", "origin_day", "lead_days"], how="inner")
        near = data.lead_days.map(conditional.get(0, pd.Series(dtype=float))).fillna(0).to_numpy(float)
        deficit = data.lead_days.map(conditional.get(1, pd.Series(dtype=float))).fillna(0).to_numpy(float)
        p = data.constraint_probability.to_numpy(float)
        adjusted_log = data.predicted_log1p_mean_growth.to_numpy(float) + (1 - p) * near + p * deficit
        adjusted_growth = np.maximum(np.expm1(adjusted_log), 0)
        predicted_area = data.origin_area_km2.to_numpy(float) + adjusted_growth * data.lead_days.to_numpy(float)
        data["area_error"] = np.abs(np.log1p(predicted_area) - np.log1p(data.observed_future_area_km2))
        data["growth_error"] = np.abs(adjusted_log - data.log1p_observed_mean_growth)
        for lead, group in data.groupby("lead_days"):
            lo, hi = event_bootstrap_mean_ci(group, "area_error", seed=SEED + int(lead))
            rows.append(
                {
                    "prediction_model": name_map.get(model, model),
                    "lead_days": int(lead),
                    "n_rows": len(group),
                    "n_fires": group.id.nunique(),
                    "future_area_mae_log": float(group.area_error.mean()),
                    "future_area_mae_ci95_lower": lo,
                    "future_area_mae_ci95_upper": hi,
                    "future_growth_mae_log1p": float(group.growth_error.mean()),
                }
            )
    # The unadjusted expected-growth model is the interpretable point baseline.
    base = held.copy()
    base["area_error"] = base.future_area_log_error_potential
    for lead, group in base.groupby("lead_days"):
        lo, hi = event_bootstrap_mean_ci(group, "area_error", seed=SEED + 100 + int(lead))
        rows.append(
            {
                "prediction_model": "P1_model_implied_growth",
                "lead_days": int(lead),
                "n_rows": len(group), "n_fires": group.id.nunique(),
                "future_area_mae_log": float(group.area_error.mean()),
                "future_area_mae_ci95_lower": lo, "future_area_mae_ci95_upper": hi,
                "future_growth_mae_log1p": float(np.mean(np.abs(base.predicted_log1p_mean_growth - base.log1p_observed_mean_growth))),
            }
        )
    # P0 uses the most recent observed mean growth without a future residual correction.
    p0_growth = np.maximum(np.expm1(held.log_recent_growth.to_numpy(float)), 0)
    p0_area = held.origin_area_km2.to_numpy(float) + p0_growth * held.lead_days.to_numpy(float)
    p0 = held.copy()
    p0["area_error"] = np.abs(np.log1p(p0_area) - np.log1p(p0.observed_future_area_km2))
    for lead, group in p0.groupby("lead_days"):
        lo, hi = event_bootstrap_mean_ci(group, "area_error", seed=SEED + 200 + int(lead))
        rows.append({"prediction_model": "P0_recent_growth", "lead_days": int(lead), "n_rows": len(group), "n_fires": group.id.nunique(), "future_area_mae_log": float(group.area_error.mean()), "future_area_mae_ci95_lower": lo, "future_area_mae_ci95_upper": hi, "future_growth_mae_log1p": float(np.mean(np.abs(held.log_recent_growth - held.log1p_observed_mean_growth)))})
    return pd.DataFrame(rows)


def change_points(residuals: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    one = residuals[residuals.lead_days.eq(1)].sort_values(["id", "origin_day"]).copy()
    one["delta_q"] = one.groupby("id").realization_residual_q.diff()
    lock = one[one.partition.ne("held_out")].delta_q.quantile(0.10)
    one["abrupt_deficit"] = (one.constraint_like.eq(1) & one.delta_q.le(lock)).astype(int)
    candidates = one[one.constraint_like.eq(1)].copy()
    summary = (
        one.groupby("partition")
        .agg(n=("id", "size"), n_fires=("id", "nunique"), constraint_rate=("constraint_like", "mean"), abrupt_rate=("abrupt_deficit", "mean"), median_q=("realization_residual_q", "median"))
        .reset_index()
    )
    summary["development_delta_q_threshold"] = float(lock)
    return candidates, summary


def termination_analysis(residuals: pd.DataFrame) -> pd.DataFrame:
    held = residuals[residuals.partition.eq("held_out")].copy()
    rows = []
    for lead, group in held.groupby("lead_days"):
        for label, subset in group.groupby("constraint_like"):
            rows.append(
                {
                    "lead_days": int(lead), "constraint_like": int(label),
                    "n": len(subset), "n_fires": subset.id.nunique(),
                    "termination_rate": float(subset.terminated_within_horizon.mean()),
                    "median_remaining_area_km2": float(subset.remaining_area_km2.median()),
                    "median_q": float(subset.realization_residual_q.median()),
                }
            )
    return pd.DataFrame(rows)


def attractor_sensitivity(residuals: pd.DataFrame) -> pd.DataFrame:
    transitions = pd.read_csv(TRANSITIONS)
    q = residuals[["id", "origin_day", "lead_days", "realization_residual_q", "constraint_like"]]
    data = transitions.merge(q, on=["id", "origin_day", "lead_days"], how="inner")
    rows = []
    for partition, group in data.groupby("partition"):
        x = group.sigma.to_numpy(float) - 2 / 3
        y = group.delta_sigma.to_numpy(float)
        naive = float(np.dot(x, y) / max(np.dot(x, x), 1e-12))
        robust = robust_fixed_restoring(group)
        filtered = group[group.constraint_like.eq(0)]
        xf = filtered.sigma.to_numpy(float) - 2 / 3
        yf = filtered.delta_sigma.to_numpy(float)
        filtered_coefficient = float(np.dot(xf, yf) / max(np.dot(xf, xf), 1e-12))
        for method, coefficient, n in (
            ("all_naive", naive, len(group)),
            ("all_huber", robust, len(group)),
            ("exclude_development_defined_extremes", filtered_coefficient, len(filtered)),
        ):
            rows.append({"partition": partition, "method": method, "fixed_two_thirds_coefficient": coefficient, "restoring_strength": -coefficient, "n": n, "n_fires": group.id.nunique()})
    return pd.DataFrame(rows)


def ot_analysis(residuals: pd.DataFrame) -> pd.DataFrame:
    if not TRANSPORT.exists():
        return pd.DataFrame()
    transport = pd.read_parquet(TRANSPORT)
    q = residuals[["id", "origin_day", "lead_days", "partition", "realization_residual_q", "constraint_like"]]
    data = transport.merge(
        q,
        left_on=["id", "origin_day", "actual_lead_days"],
        right_on=["id", "origin_day", "lead_days"],
        how="inner",
        suffixes=("_transport", ""),
    )
    rows = []
    for partition, group in data.groupby("partition"):
        rho, pvalue = spearmanr(group.reorganization_primary, group.realization_residual_q)
        rows.append({"analysis": "contemporaneous_R_vs_q", "partition": partition, "n": len(group), "n_fires": group.id.nunique(), "spearman_rho": rho, "p_value": pvalue})
    # Prospective signal: use the most recent transport interval ending no later than origin.
    prior = transport[["id", "future_day", "reorganization_primary"]].sort_values(["future_day", "id"])
    targets = q.sort_values(["origin_day", "id"])
    joined = pd.merge_asof(targets, prior, left_on="origin_day", right_on="future_day", by="id", direction="backward", allow_exact_matches=False)
    joined = joined.dropna(subset=["reorganization_primary"])
    for partition, group in joined.groupby("partition"):
        rho, pvalue = spearmanr(group.reorganization_primary, group.realization_residual_q)
        rows.append({"analysis": "prior_R_vs_future_q", "partition": partition, "n": len(group), "n_fires": group.id.nunique(), "spearman_rho": rho, "p_value": pvalue})
    return pd.DataFrame(rows)


def make_figure(residuals: pd.DataFrame, metrics: pd.DataFrame, attractor: pd.DataFrame) -> None:
    held = residuals[residuals.partition.eq("held_out")]
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)
    ax = axes[0, 0]
    sample = held.sample(min(4000, len(held)), random_state=SEED)
    ax.scatter(sample.model_implied_mean_growth_km2_day, sample.observed_mean_growth_km2_day, s=7, alpha=.18, color="#235789")
    limit = np.quantile(np.r_[sample.model_implied_mean_growth_km2_day, sample.observed_mean_growth_km2_day], .98)
    ax.plot([0, limit], [0, limit], color="#333333", lw=1.5, ls="--")
    ax.set(xlim=(0, limit), ylim=(0, limit), xlabel="Model-implied mean growth (km²/day)", ylabel="Realized mean growth (km²/day)", title="A  Potential versus realized growth")

    ax = axes[0, 1]
    ax.hist(held.realization_residual_q.clip(-5, 3), bins=60, color="#6495ED", edgecolor="white")
    ax.axvline(held.constraint_threshold_q.median(), color="#B3261E", lw=2, ls="--")
    ax.set(xlabel="Realization residual q", ylabel="Intervals", title="B  Negative residual tail")

    ax = axes[0, 2]
    rate = held.groupby("lead_days").constraint_like.mean()
    ax.plot(rate.index, rate.values, marker="o", color="#B3261E", lw=2.2)
    ax.set(xlabel="Forecast horizon (days)", ylabel="Constraint-like fraction", title="C  Deficit risk accumulates")

    ax = axes[1, 0]
    chart = metrics.pivot(index="lead_days", columns="prediction_model", values="future_area_mae_log")
    for name, values in chart.items():
        if name in {"P0_recent_growth", "P1_model_implied_growth", "P2_constant_hazard", "P4_geometry_hazard"}:
            ax.plot(values.index, values, marker="o", lw=2, label=name.replace("_", " "))
    ax.set(xlabel="Forecast horizon (days)", ylabel="Mean absolute log-area error", title="D  Prediction impact")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1, 1]
    shown = attractor[attractor.partition.eq("held_out")]
    ax.barh(shown.method.str.replace("_", " "), shown.restoring_strength, color=["#777777", "#6495ED", "#2A8C5A"][:len(shown)])
    ax.axvline(0, color="#333333", lw=1)
    ax.set(xlabel="Restoring strength toward 2/3", title="E  Attractor shock sensitivity")

    ax = axes[1, 2]
    bins = pd.qcut(held.realization_residual_q, 5, duplicates="drop")
    productivity = held.observed_mean_growth_km2_day / np.exp(held.log_exterior_perimeter)
    summary = pd.DataFrame({"q": held.realization_residual_q, "bin": bins, "productivity": productivity}).groupby("bin", observed=True).mean()
    ax.plot(summary.q, summary.productivity, marker="o", color="#D28B26", lw=2)
    ax.set(xlabel="Mean realization residual q", ylabel="Mapped boundary productivity", title="F  Boundary productivity")

    for axis in axes.ravel():
        axis.grid(alpha=.2)
    for extension in ("pdf", "svg", "png"):
        fig.savefig(OUT / f"figure1_latent_constraint_validation.{extension}", dpi=400 if extension == "png" else None)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    snapshots = pd.read_csv(SNAPSHOTS)
    sequences = pd.read_csv(SEQUENCES)
    intervals = build_interval_table(snapshots, sequences, leads=DEFAULT_LEADS)
    residuals, selected, tuning = make_predictions(intervals)
    residuals = attach_origin_ot(residuals)
    residuals.to_parquet(OUT / "growth_residuals.parquet", index=False)
    residuals[["id", "ig_year", "origin_day", "lead_days", "partition", "observed_mean_growth_km2_day", "realized_coupling", "predicted_potential_coupling"]].to_parquet(OUT / "realized_coupling.parquet", index=False)
    residuals[["id", "ig_year", "origin_day", "lead_days", "partition", "model_implied_mean_growth_km2_day", "model_implied_total_growth_km2", "model_implied_future_area_km2", "observed_future_area_km2"]].to_parquet(OUT / "potential_growth_predictions.parquet", index=False)
    candidates, change_summary = change_points(residuals)
    candidates.to_parquet(OUT / "constraint_event_candidates.parquet", index=False)
    change_summary.to_csv(OUT / "change_point_results.csv", index=False)
    hazard_defs, hazard_predictions, _ = hazard_analysis(residuals)
    hazard_defs.to_csv(OUT / "constraint_hazard_models.csv", index=False)
    prediction_metrics = mixture_prediction_metrics(residuals, hazard_predictions)
    prediction_metrics.to_csv(OUT / "constraint_prediction_metrics.csv", index=False)
    prediction_metrics.to_csv(OUT / "long_horizon_constraint_metrics.csv", index=False)
    termination = termination_analysis(residuals)
    termination.to_csv(OUT / "termination_constraint_analysis.csv", index=False)
    attractor = attractor_sensitivity(residuals)
    attractor.to_csv(OUT / "attractor_shock_sensitivity.csv", index=False)
    ot = ot_analysis(residuals)
    ot.to_csv(OUT / "ot_constraint_relationship.csv", index=False)
    tuning.to_csv(OUT / "potential_model_tuning.csv", index=False)
    make_figure(residuals, prediction_metrics, attractor)

    held = residuals[residuals.partition.eq("held_out")]
    design = {
        "seed": SEED,
        "cohort_events": int(intervals.id.nunique()),
        "partitions": {"development": "2001-2012", "calibration": "2013-2015", "held_out": "2016-2020"},
        "origins": sorted(map(int, snapshots.snapshot_day.unique())),
        "horizons": list(DEFAULT_LEADS),
        "potential_model_selection": "minimum calibration MAE; refit on development+calibration",
        "selected_potential_model": selected,
        "constraint_like_definition": "lead-specific lower 10% realization residual threshold from development+calibration",
        "terminology": "constraint-like growth deficit; no causal attribution",
    }
    (OUT / "design_lock.json").write_text(json.dumps(design, indent=2) + "\n")
    report = {
        "status": "complete",
        "rows": len(residuals), "events": int(residuals.id.nunique()),
        "held_out_rows": len(held), "held_out_events": int(held.id.nunique()),
        "held_out_constraint_rate": float(held.constraint_like.mean()),
        "selected_potential_model": selected,
        "most_negative_tail_q01": float(held.realization_residual_q.quantile(.01)),
        "median_q": float(held.realization_residual_q.median()),
        "ot_available": bool(len(ot)),
        "causal_attribution": "not identifiable from FIRED alone",
    }
    (OUT / "run_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
