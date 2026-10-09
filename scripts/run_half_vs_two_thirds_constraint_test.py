#!/usr/bin/env python3
"""Test whether realization deficits explain one-half versus two-thirds performance."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from fire_metabolism.latent_constraints import event_bootstrap_mean_ci


SEED = 20261009
OUT = Path("outputs/half_vs_two_thirds_constraint_test")
LATENT = Path("outputs/latent_constraint_validation")
PREDICTIONS = Path("outputs/geometric_attractor_validation/held_out_attractor_predictions.csv.gz")
TRANSPORT = Path("outputs/integrated_geometry_transport/transport_transition_metrics.parquet")


def load_losses(residuals: pd.DataFrame) -> pd.DataFrame:
    predictions = pd.read_csv(PREDICTIONS)
    wide = predictions.pivot_table(
        index=["id", "ig_year", "origin_day", "lead_days", "sigma", "future_sigma"],
        columns="model", values=["predicted_future_sigma", "absolute_error"], aggfunc="first",
    )
    wide.columns = [f"{value}_{model}" for value, model in wide.columns]
    wide = wide.reset_index()
    data = wide.merge(
        residuals,
        on=["id", "ig_year", "origin_day", "lead_days"],
        how="inner",
        suffixes=("", "_growth"),
    )
    data["D_half_minus_two_thirds"] = data.absolute_error_half_attractor - data.absolute_error_two_thirds_attractor
    data["Z_origin_half_vs_two_thirds"] = np.abs(data.sigma - .5) - np.abs(data.sigma - 2 / 3)
    data["delta_toward_half"] = np.abs(data.future_sigma - 2 / 3) - np.abs(data.future_sigma - .5)
    data["mapped_boundary_productivity_exterior"] = data.observed_mean_growth_km2_day / np.maximum(np.exp(data.log_exterior_perimeter), 1e-12)
    data["mapped_boundary_productivity_total"] = data.observed_mean_growth_km2_day / np.maximum(np.exp(data.log_total_perimeter), 1e-12)
    data["perimeter_slope_discrepancy"] = data.total_perimeter_area_slope - data.exterior_perimeter_area_slope
    return data


def continuous_relationship(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for lead, group in data.groupby("lead_days"):
        x = group.realization_residual_q.to_numpy(float)
        y = group.D_half_minus_two_thirds.to_numpy(float)
        design = np.column_stack([np.ones(len(x)), x, x * x])
        beta, *_ = np.linalg.lstsq(design, y, rcond=None)
        rho, p = spearmanr(x, y)
        near = group[group.realization_residual_q >= group.realization_residual_q.quantile(.75)]
        rows.append(
            {
                "lead_days": int(lead), "n": len(group), "n_fires": group.id.nunique(),
                "quadratic_intercept": beta[0], "quadratic_q": beta[1], "quadratic_q2": beta[2],
                "spearman_rho": rho, "spearman_p": p,
                "mean_D": float(y.mean()),
                "near_potential_mean_D": float(near.D_half_minus_two_thirds.mean()),
                "near_potential_half_win_rate": float((near.D_half_minus_two_thirds < 0).mean()),
            }
        )
    return pd.DataFrame(rows)


def quantile_performance(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    result["residual_bin"] = pd.qcut(result.realization_residual_q, 5, labels=["strongest deficit", "q20-40", "q40-60", "q60-80", "closest to potential"], duplicates="drop")
    rows = []
    for (lead, label), group in result.groupby(["lead_days", "residual_bin"], observed=True):
        rows.append(
            {
                "lead_days": int(lead), "residual_bin": str(label), "n": len(group), "n_fires": group.id.nunique(),
                "median_q": float(group.realization_residual_q.median()),
                "half_mae": float(group.absolute_error_half_attractor.mean()),
                "two_thirds_mae": float(group.absolute_error_two_thirds_attractor.mean()),
                "flexible_mae": float(group.absolute_error_flexible_dynamics.mean()),
                "persistence_mae": float(group.absolute_error_persistence.mean()),
                "mean_D": float(group.D_half_minus_two_thirds.mean()),
                "half_win_rate": float((group.D_half_minus_two_thirds < 0).mean()),
            }
        )
    return pd.DataFrame(rows)


def filter_sensitivity(data: pd.DataFrame, residuals: pd.DataFrame) -> pd.DataFrame:
    train = residuals[residuals.partition.ne("held_out")]
    quantiles = [0, .05, .10, .20, .30, .50]
    rows = []
    for lead, group in data.groupby("lead_days"):
        source = train[train.lead_days.eq(lead)].realization_residual_q
        for quantile in quantiles:
            threshold = float(source.quantile(quantile))
            kept = group[group.realization_residual_q > threshold]
            for model in ("half_attractor", "two_thirds_attractor", "persistence", "flexible_dynamics"):
                rows.append(
                    {
                        "lead_days": int(lead), "excluded_training_quantile": quantile,
                        "threshold_q": threshold, "model": model, "n": len(kept), "n_fires": kept.id.nunique(),
                        "mae": float(kept[f"absolute_error_{model}"].mean()) if len(kept) else np.nan,
                    }
                )
    return pd.DataFrame(rows)


def slope_residual(data: pd.DataFrame) -> pd.DataFrame:
    binned = data.copy()
    binned["residual_bin"] = pd.qcut(binned.realization_residual_q, 5, labels=False, duplicates="drop")
    return (
        binned.groupby(["lead_days", "residual_bin"])
        .agg(n=("id", "size"), n_fires=("id", "nunique"), median_q=("realization_residual_q", "median"), median_origin_sigma=("sigma", "median"), median_future_sigma=("future_sigma", "median"), median_delta_sigma=("delta_toward_half", "median"))
        .reset_index()
    )


def age_area_hazard(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for target in ("realization_residual_q", "constraint_like"):
        x = np.column_stack([np.ones(len(data)), np.log(data.origin_area_km2), data.origin_day, data.lead_days])
        y = data[target].to_numpy(float)
        beta, *_ = np.linalg.lstsq(x, y, rcond=None)
        rows.append({"target": target, "n": len(data), "intercept": beta[0], "coefficient_log_area": beta[1], "coefficient_age_day": beta[2], "coefficient_lead_day": beta[3]})
    return pd.DataFrame(rows)


def boundary_and_perimeter(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    result = data.copy()
    result["residual_bin"] = pd.qcut(result.realization_residual_q, 5, labels=False, duplicates="drop")
    boundary = (
        result.groupby(["lead_days", "residual_bin"])
        .agg(n=("id", "size"), median_q=("realization_residual_q", "median"), exterior_productivity=("mapped_boundary_productivity_exterior", "median"), total_productivity=("mapped_boundary_productivity_total", "median"))
        .reset_index()
    )
    perimeter = (
        result.groupby(["lead_days", "residual_bin"])
        .agg(n=("id", "size"), median_q=("realization_residual_q", "median"), exterior_slope=("exterior_perimeter_area_slope", "median"), total_slope=("total_perimeter_area_slope", "median"), slope_discrepancy=("perimeter_slope_discrepancy", "median"))
        .reset_index()
    )
    return boundary, perimeter


def ot_test(data: pd.DataFrame) -> pd.DataFrame:
    if not TRANSPORT.exists():
        return pd.DataFrame()
    transport = pd.read_parquet(TRANSPORT)
    joined = transport.merge(
        data[["id", "origin_day", "lead_days", "realization_residual_q", "D_half_minus_two_thirds"]],
        left_on=["id", "origin_day", "actual_lead_days"], right_on=["id", "origin_day", "lead_days"], how="inner",
    )
    rows = []
    for target in ("realization_residual_q", "D_half_minus_two_thirds"):
        rho, p = spearmanr(joined.reorganization_primary, joined[target])
        rows.append({"target": target, "n": len(joined), "n_fires": joined.id.nunique(), "spearman_R": rho, "p_value": p, "timing": "contemporaneous; not prospective"})
    return pd.DataFrame(rows)


def prospective_mixture(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for lead, group in data.groupby("lead_days"):
        # Z is available at the origin; q is future. This is descriptive held-out prospective association.
        x = np.column_stack([np.ones(len(group)), group.Z_origin_half_vs_two_thirds, np.log(group.origin_area_km2), group.origin_day])
        y = group.realization_residual_q.to_numpy(float)
        beta, *_ = np.linalg.lstsq(x, y, rcond=None)
        predicted = x @ beta
        rows.append({"lead_days": int(lead), "n": len(group), "n_fires": group.id.nunique(), "coefficient_Z": beta[1], "coefficient_log_area": beta[2], "coefficient_age": beta[3], "q_mae_in_sample_heldout_descriptive": float(np.mean(np.abs(y - predicted))), "note": "association only; coefficients estimated on held-out for diagnosis, not an operational forecast"})
    return pd.DataFrame(rows)


def select_examples(data: pd.DataFrame) -> pd.DataFrame:
    near_cut = data.realization_residual_q.quantile(.75)
    deficit_cut = data.realization_residual_q.quantile(.10)
    categories = {
        "A_near_potential_two_thirds_better": data[(data.realization_residual_q >= near_cut) & (data.D_half_minus_two_thirds > 0)],
        "B_deficit_half_better": data[(data.realization_residual_q <= deficit_cut) & (data.D_half_minus_two_thirds < 0)],
        "C_deficit_two_thirds_better": data[(data.realization_residual_q <= deficit_cut) & (data.D_half_minus_two_thirds > 0)],
        "D_near_potential_half_better": data[(data.realization_residual_q >= near_cut) & (data.D_half_minus_two_thirds < 0)],
    }
    rows = []
    for label, subset in categories.items():
        if len(subset):
            row = subset.sort_values(["id", "origin_day", "lead_days"]).iloc[len(subset) // 2].to_dict()
            rows.append({"example": label, **{key: row[key] for key in ["id", "ig_year", "origin_day", "lead_days", "sigma", "future_sigma", "realization_residual_q", "D_half_minus_two_thirds"]}})
    return pd.DataFrame(rows)


def make_figure(data: pd.DataFrame, quantiles: pd.DataFrame, filtering: pd.DataFrame, boundary: pd.DataFrame, examples: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(16, 9), constrained_layout=True)
    ax = axes[0, 0]
    sample = data.sample(min(6000, len(data)), random_state=SEED)
    ax.scatter(sample.realization_residual_q, sample.D_half_minus_two_thirds, s=7, alpha=.12, color="#235789")
    bins = pd.qcut(data.realization_residual_q, 20, duplicates="drop")
    smooth = data.groupby(bins, observed=True).agg(q=("realization_residual_q", "mean"), D=("D_half_minus_two_thirds", "mean"))
    ax.plot(smooth.q, smooth.D, color="#B3261E", lw=3)
    ax.axhline(0, color="#333333", lw=1)
    ax.set(xlabel="Realization residual q", ylabel="D = loss(1/2) - loss(2/3)", title="A  Relative advantage versus deficit")

    ax = axes[0, 1]
    s = data.groupby(bins, observed=True).agg(q=("realization_residual_q", "mean"), future=("future_sigma", "median"))
    ax.plot(s.q, s.future, marker="o", color="#6495ED", lw=2)
    ax.axhline(.5, color="#B3261E", ls="--"); ax.axhline(2/3, color="#2A8C5A", ls="--")
    ax.set(xlabel="Realization residual q", ylabel="Median future mapped slope", title="B  Scaling state")

    ax = axes[0, 2]
    age = data.assign(age_bin=pd.qcut(data.origin_day, 8, duplicates="drop")).groupby("age_bin", observed=True).agg(age=("origin_day", "mean"), rate=("constraint_like", "mean"))
    ax.plot(age.age, age.rate, marker="o", color="#D28B26", lw=2)
    ax.set(xlabel="Fire age (days)", ylabel="Constraint-like fraction", title="C  Deficit frequency with age")

    ax = axes[1, 0]
    shown = filtering[filtering.lead_days.eq(14)]
    for model, group in shown.groupby("model"):
        ax.plot(group.excluded_training_quantile, group.mae, marker="o", label=model.replace("_", " "))
    ax.set(xlabel="Excluded lower-q training quantile", ylabel="Slope forecast MAE", title="D  Remove strongest deficits")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1, 1]
    b = boundary.groupby("residual_bin").agg(q=("median_q", "mean"), productivity=("exterior_productivity", "mean"))
    ax.plot(b.q, b.productivity, marker="o", color="#D28B26", lw=2)
    ax.set(xlabel="Median realization residual q", ylabel="Mapped boundary productivity", title="E  Boundary productivity")

    ax = axes[1, 2]
    for row in examples.itertuples(index=False):
        ax.scatter(row.realization_residual_q, row.D_half_minus_two_thirds, s=80, label=row.example.split("_", 1)[0])
        ax.annotate(row.example.split("_", 1)[0], (row.realization_residual_q, row.D_half_minus_two_thirds), xytext=(5, 5), textcoords="offset points")
    ax.axhline(0, color="#333333", lw=1)
    ax.set(xlabel="Realization residual q", ylabel="D", title="F  Reproducible examples")

    for ax in axes.ravel(): ax.grid(alpha=.2)
    for extension in ("pdf", "svg", "png"):
        fig.savefig(OUT / f"figure1_half_vs_two_thirds_constraint_test.{extension}", dpi=400 if extension == "png" else None)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    residuals = pd.read_parquet(LATENT / "growth_residuals.parquet")
    residuals.to_parquet(OUT / "realization_residuals.parquet", index=False)
    data = load_losses(residuals)
    data.to_parquet(OUT / "half_vs_two_thirds_transition_losses.parquet", index=False)
    relationship = continuous_relationship(data)
    relationship.to_csv(OUT / "relative_advantage_vs_residual.csv", index=False)
    quantiles = quantile_performance(data)
    quantiles.to_csv(OUT / "residual_quantile_performance.csv", index=False)
    filtering = filter_sensitivity(data, residuals)
    filtering.to_csv(OUT / "constraint_filter_sensitivity.csv", index=False)
    slope = slope_residual(data); slope.to_csv(OUT / "slope_vs_residual.csv", index=False)
    hazard = age_area_hazard(data); hazard.to_csv(OUT / "age_area_constraint_hazard.csv", index=False)
    boundary, perimeter = boundary_and_perimeter(data)
    boundary.to_csv(OUT / "boundary_productivity.csv", index=False)
    perimeter.to_csv(OUT / "perimeter_definition_sensitivity.csv", index=False)
    ot = ot_test(data); ot.to_csv(OUT / "ot_constraint_test.csv", index=False)
    quantiles.to_csv(OUT / "long_horizon_results.csv", index=False)
    prospective = prospective_mixture(data); prospective.to_csv(OUT / "prospective_mixture_results.csv", index=False)
    examples = select_examples(data); examples.to_csv(OUT / "event_examples.csv", index=False)
    make_figure(data, quantiles, filtering, boundary, examples)

    near = data[data.realization_residual_q >= data.realization_residual_q.quantile(.75)]
    strong = data[data.realization_residual_q <= data.realization_residual_q.quantile(.10)]
    rho, p = spearmanr(data.realization_residual_q, data.D_half_minus_two_thirds)
    verdict = "B_constraint_explains_part_not_all"
    if near.D_half_minus_two_thirds.mean() < 0:
        verdict = "C_half_remains_competitive_near_potential"
    elif rho > 0 and strong.D_half_minus_two_thirds.mean() < near.D_half_minus_two_thirds.mean():
        verdict = "A_half_advantage_concentrated_in_deficits"
    design = {
        "seed": SEED, "locked_cohort": 4032,
        "potential_growth_source": "origin-safe selected empirical model from latent-constraint validation",
        "primary_analysis": "continuous D versus q on held-out transitions",
        "D_definition": "absolute slope error one-half minus absolute slope error two-thirds",
        "near_potential_display_group": "held-out upper q quartile; interpretive only",
        "filter_thresholds": "development/calibration q quantiles",
        "causal_language": "constraint-like; FIRED does not attribute cause",
    }
    (OUT / "design_lock.json").write_text(json.dumps(design, indent=2) + "\n")
    report = {
        "status": "complete", "n": len(data), "n_fires": int(data.id.nunique()),
        "spearman_q_D": float(rho), "spearman_p": float(p),
        "near_potential_mean_D": float(near.D_half_minus_two_thirds.mean()),
        "near_potential_half_win_rate": float((near.D_half_minus_two_thirds < 0).mean()),
        "strong_deficit_mean_D": float(strong.D_half_minus_two_thirds.mean()),
        "strong_deficit_half_win_rate": float((strong.D_half_minus_two_thirds < 0).mean()),
        "verdict": verdict,
        "attribution": "not identifiable",
    }
    (OUT / "run_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
