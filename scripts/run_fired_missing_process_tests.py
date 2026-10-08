#!/usr/bin/env python3
"""Test weather, active-front, and observation-process additions to FIRED models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu

from fire_metabolism.fired_missing_processes import (
    ACTIVE_FRONT_FEATURE_COLUMNS,
    NEXT_DAY_WEATHER_FEATURE_COLUMNS,
    WEATHER_FEATURE_COLUMNS,
    active_day_terminal_fraction,
    add_active_front_features,
    add_next_day_weather_features,
    add_weather_features,
    terminal_weather_changes,
)
from fire_metabolism.fired_outcomes import fit_standardized_ridge
from fire_metabolism.fired_realization import terminal_growth_diagnostics
from fire_metabolism.fired_survival import (
    MECHANISTIC_SURVIVAL_FEATURE_COLUMNS,
    STATE_FEATURE_COLUMNS,
    add_observed_states,
    fit_logistic_hazard,
)


BASE_COLUMNS = MECHANISTIC_SURVIVAL_FEATURE_COLUMNS + STATE_FEATURE_COLUMNS
MODEL_COLUMNS = {
    "geometry_state": BASE_COLUMNS,
    "geometry_state_active_front": BASE_COLUMNS + ACTIVE_FRONT_FEATURE_COLUMNS,
    "geometry_state_weather": BASE_COLUMNS + WEATHER_FEATURE_COLUMNS,
    "geometry_state_active_weather": BASE_COLUMNS
    + ACTIVE_FRONT_FEATURE_COLUMNS
    + WEATHER_FEATURE_COLUMNS,
    "geometry_state_active_weather_next_day": BASE_COLUMNS
    + ACTIVE_FRONT_FEATURE_COLUMNS
    + WEATHER_FEATURE_COLUMNS
    + NEXT_DAY_WEATHER_FEATURE_COLUMNS,
}
MODEL_LABELS = {
    "geometry_state": "Geometry + state",
    "geometry_state_active_front": "+ active-front proxy",
    "geometry_state_weather": "+ past weather",
    "geometry_state_active_weather": "+ active front + weather",
    "geometry_state_active_weather_next_day": "+ observed next-day weather",
}
MODEL_COLORS = {
    "geometry_state": "#4F79B7",
    "geometry_state_active_front": "#8C6BB1",
    "geometry_state_weather": "#D58A2A",
    "geometry_state_active_weather": "#1B9E77",
    "geometry_state_active_weather_next_day": "#C44E52",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sequences",
        type=Path,
        default=Path("outputs/fired_prediction/fired_sequences.csv.gz"),
    )
    parser.add_argument(
        "--geometry",
        type=Path,
        default=Path("outputs/fired_lifecycle_prediction/fired_geometry_sequences.csv.gz"),
    )
    parser.add_argument(
        "--features",
        type=Path,
        default=Path("outputs/fired_lifecycle_prediction/snapshot_features.csv.gz"),
    )
    parser.add_argument(
        "--weather",
        type=Path,
        default=Path("outputs/fired_missing_processes/gridmet_event_daily.csv.gz"),
    )
    parser.add_argument(
        "--realization",
        type=Path,
        default=Path("outputs/fired_realization_gap/held_out_realization_gap.csv.gz"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/fired_missing_processes"),
    )
    parser.add_argument("--snapshot-day", type=int, default=7)
    return parser.parse_args()


def rank_auc(observed: np.ndarray, score: np.ndarray) -> float:
    observed = np.asarray(observed, dtype=bool)
    positive = int(observed.sum())
    negative = int((~observed).sum())
    if positive == 0 or negative == 0:
        return np.nan
    ranks = pd.Series(score).rank(method="average").to_numpy(dtype=float)
    return float(
        (ranks[observed].sum() - positive * (positive + 1) / 2)
        / (positive * negative)
    )


def log_loss(observed: np.ndarray, probability: np.ndarray) -> float:
    observed = np.asarray(observed, dtype=float)
    probability = np.clip(np.asarray(probability, dtype=float), 1e-12, 1 - 1e-12)
    return float(
        -np.mean(observed * np.log(probability) + (1 - observed) * np.log(1 - probability))
    )


def tune_classifier(
    development: pd.DataFrame,
    calibration: pd.DataFrame,
    columns: tuple[str, ...],
    persistent_day: float,
) -> tuple[object, float, pd.DataFrame]:
    training = development.copy()
    training["terminal_transition"] = (
        training.death_day >= persistent_day
    ).astype(float)
    observed = (calibration.death_day >= persistent_day).to_numpy(dtype=float)
    rows = []
    models = {}
    for alpha in (0.1, 1.0, 10.0, 100.0, 1000.0):
        model = fit_logistic_hazard(training, feature_columns=columns, alpha=alpha)
        probability = model.predict_hazard(calibration)
        rows.append(
            {
                "alpha": alpha,
                "calibration_log_loss": log_loss(observed, probability),
                "calibration_auc": rank_auc(observed, probability),
            }
        )
        models[alpha] = model
    tuning = pd.DataFrame(rows)
    selected = float(tuning.loc[tuning.calibration_log_loss.idxmin(), "alpha"])
    threshold = float(np.quantile(models[selected].predict_hazard(calibration), 0.90))
    tuning["selected"] = tuning.alpha == selected
    tuning["high_confidence_threshold"] = threshold
    return models[selected], threshold, tuning


def tune_ridge(
    development: pd.DataFrame,
    calibration: pd.DataFrame,
    columns: tuple[str, ...],
    target: str,
    snapshot_day: int,
) -> tuple[object, pd.DataFrame]:
    if target == "final_area":
        development_target = np.log(development.final_area_km2.to_numpy(dtype=float))
    else:
        development_target = np.log1p(
            development.death_day.to_numpy(dtype=float) - snapshot_day
        )
    rows = []
    models = {}
    for alpha in (0.1, 1.0, 10.0, 100.0, 1000.0):
        model = fit_standardized_ridge(
            development,
            development_target,
            feature_columns=columns,
            alpha=alpha,
        )
        if target == "final_area":
            predicted = np.maximum(
                calibration.snapshot_area_km2.to_numpy(dtype=float),
                np.exp(model.predict(calibration)),
            )
            score = float(
                np.abs(
                    np.log(predicted / calibration.final_area_km2.to_numpy(dtype=float))
                ).mean()
            )
        else:
            predicted = snapshot_day + np.expm1(model.predict(calibration))
            score = float(np.abs(predicted - calibration.death_day).mean())
        rows.append({"alpha": alpha, "calibration_error": score})
        models[alpha] = model
    tuning = pd.DataFrame(rows)
    selected = float(tuning.loc[tuning.calibration_error.idxmin(), "alpha"])
    tuning["selected"] = tuning.alpha == selected
    return models[selected], tuning


def evaluate_models(
    features: pd.DataFrame,
    *,
    snapshot_day: int,
    persistent_day: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    development = features[features.ig_year <= 2012]
    calibration = features[features.ig_year.between(2013, 2015)]
    held_out = features[features.ig_year >= 2016]
    rows = []
    tuning_rows = []
    observed_persistent = (held_out.death_day >= persistent_day).to_numpy(dtype=bool)
    for model_name, columns in MODEL_COLUMNS.items():
        classifier, threshold, tuning = tune_classifier(
            development, calibration, columns, persistent_day
        )
        tuning.insert(0, "target", "persistent_regime")
        tuning.insert(1, "model", model_name)
        tuning_rows.append(tuning)
        probability = classifier.predict_hazard(held_out)
        selected = probability >= threshold
        rows.append(
            {
                "target": "persistent_regime",
                "model": model_name,
                "n_events": int(len(held_out)),
                "rank_auc": rank_auc(observed_persistent, probability),
                "brier_score": float(np.mean((probability - observed_persistent) ** 2)),
                "high_confidence_ppv": float(observed_persistent[selected].mean()),
                "high_confidence_sensitivity": float(
                    (selected & observed_persistent).sum() / observed_persistent.sum()
                ),
            }
        )
        for target in ("final_area", "death_day"):
            ridge, tuning = tune_ridge(
                development, calibration, columns, target, snapshot_day
            )
            tuning.insert(0, "target", target)
            tuning.insert(1, "model", model_name)
            tuning_rows.append(tuning)
            if target == "final_area":
                predicted = np.maximum(
                    held_out.snapshot_area_km2.to_numpy(dtype=float),
                    np.exp(ridge.predict(held_out)),
                )
                error = np.abs(
                    np.log(predicted / held_out.final_area_km2.to_numpy(dtype=float))
                )
                rows.append(
                    {
                        "target": target,
                        "model": model_name,
                        "n_events": int(len(held_out)),
                        "mean_absolute_log_error": float(error.mean()),
                        "typical_error_factor": float(np.exp(error.mean())),
                    }
                )
            else:
                predicted = snapshot_day + np.expm1(ridge.predict(held_out))
                error = predicted - held_out.death_day.to_numpy(dtype=float)
                for group_name, mask in (
                    ("all", np.ones(len(held_out), dtype=bool)),
                    ("persistent", observed_persistent),
                ):
                    rows.append(
                        {
                            "target": f"death_day_{group_name}",
                            "model": model_name,
                            "n_events": int(mask.sum()),
                            "mean_absolute_error": float(np.abs(error[mask]).mean()),
                            "mean_bias": float(error[mask].mean()),
                        }
                    )
    return pd.DataFrame(rows), pd.concat(tuning_rows, ignore_index=True)


def weather_diagnostics(
    realization: pd.DataFrame,
    changes: pd.DataFrame,
) -> pd.DataFrame:
    frame = realization.merge(changes, on="id", validate="one_to_one")
    variables = [column for column in changes if column != "id"]
    comparisons = {
        "early_ending_vs_true_persistent": (
            frame.realization_group == "high_confidence_early_ending",
            frame.realization_group == "high_confidence_true_persistent",
        ),
        "gradual_vs_abrupt_early_ending": (
            (frame.realization_group == "high_confidence_early_ending")
            & (frame.terminal_signature == "gradual_decline_like"),
            (frame.realization_group == "high_confidence_early_ending")
            & (frame.terminal_signature == "abrupt_truncation_like"),
        ),
    }
    rows = []
    for comparison, (first_mask, second_mask) in comparisons.items():
        for variable in variables:
            first = frame.loc[first_mask, variable].to_numpy(dtype=float)
            second = frame.loc[second_mask, variable].to_numpy(dtype=float)
            test = mannwhitneyu(first, second, alternative="two-sided")
            pooled_scale = float(np.std(np.r_[first, second], ddof=1))
            rows.append(
                {
                    "comparison": comparison,
                    "variable": variable,
                    "first_n": int(len(first)),
                    "second_n": int(len(second)),
                    "first_median": float(np.median(first)),
                    "second_median": float(np.median(second)),
                    "median_difference": float(np.median(first) - np.median(second)),
                    "standardized_median_difference": float(
                        (np.median(first) - np.median(second))
                        / max(pooled_scale, 1e-12)
                    ),
                    "mann_whitney_p_value": float(test.pvalue),
                }
            )
    result = pd.DataFrame(rows)
    result["holm_adjusted_p_value"] = np.nan
    for _, indices in result.groupby("comparison").groups.items():
        ordered = result.loc[indices].sort_values("mann_whitney_p_value")
        adjusted = []
        running = 0.0
        total = len(ordered)
        for rank, value in enumerate(ordered.mann_whitney_p_value, 1):
            running = max(running, (total - rank + 1) * float(value))
            adjusted.append(min(1.0, running))
        result.loc[ordered.index, "holm_adjusted_p_value"] = adjusted
    return result


def observation_robustness(
    sequences: pd.DataFrame,
    realization: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for window in (2, 3, 5):
        diagnostics = terminal_growth_diagnostics(
            sequences,
            window_days=window,
            gradual_threshold=0.10,
            abrupt_threshold=0.25,
        )
        frame = realization[["id", "realization_group"]].merge(
            diagnostics[["id", "terminal_growth_fraction_of_peak"]],
            on="id",
            validate="one_to_one",
        )
        rows.append(_abrupt_comparison(frame, f"calendar_last_{window}_days"))
    active = active_day_terminal_fraction(sequences, active_days=3).rename(
        columns={
            "active_day_terminal_growth_fraction": "terminal_growth_fraction_of_peak"
        }
    )
    frame = realization[["id", "realization_group"]].merge(
        active, on="id", validate="one_to_one"
    )
    rows.append(_abrupt_comparison(frame, "last_3_positive_detection_days"))
    return pd.DataFrame(rows)


def _abrupt_comparison(frame: pd.DataFrame, definition: str) -> dict[str, float | str]:
    candidate = frame.realization_group == "high_confidence_early_ending"
    persistent = frame.realization_group == "high_confidence_true_persistent"
    first = frame.loc[candidate, "terminal_growth_fraction_of_peak"] >= 0.25
    second = frame.loc[persistent, "terminal_growth_fraction_of_peak"] >= 0.25
    odds, p_value = fisher_exact(
        [
            [int(first.sum()), int((~first).sum())],
            [int(second.sum()), int((~second).sum())],
        ]
    )
    return {
        "definition": definition,
        "candidate_abrupt_fraction": float(first.mean()),
        "true_persistent_abrupt_fraction": float(second.mean()),
        "fisher_odds_ratio": float(odds),
        "fisher_p_value": float(p_value),
    }


def plot_model_comparison(summary: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.3), constrained_layout=True)
    targets = [
        ("persistent_regime", "rank_auc", "Persistent-regime AUC", False),
        ("final_area", "typical_error_factor", "Final-area error factor", True),
        ("death_day_persistent", "mean_absolute_error", "Persistent death MAE (days)", True),
    ]
    order = list(MODEL_COLUMNS)
    x = np.arange(len(order))
    for ax, (target, metric, title, lower_better) in zip(axes, targets, strict=True):
        selected = summary[summary.target == target].set_index("model")
        values = [selected.loc[name, metric] for name in order]
        ax.bar(x, values, color=[MODEL_COLORS[name] for name in order])
        ax.set_xticks(x)
        ax.set_xticklabels(
            ["Base", "+Front", "+Weather", "+Both", "+Next day"],
            rotation=24,
        )
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.2)
        if target == "persistent_regime":
            ax.set_ylim(0.65, max(values) + 0.03)
        for index, value in enumerate(values):
            ax.text(index, value, f"{value:.3f}" if value < 2 else f"{value:.2f}", ha="center", va="bottom", fontsize=8)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def plot_weather_diagnostics(summary: pd.DataFrame, output: Path) -> None:
    variables = [
        "terminal_vpd_kpa_change",
        "terminal_wind_speed_m_s_change",
        "terminal_fuel_moisture_100hr_pct_change",
        "terminal_energy_release_component_change",
        "terminal_precipitation_mm_change",
    ]
    labels = ["VPD", "Wind", "100-h fuel moisture", "ERC", "Precipitation"]
    comparison = summary[
        summary.comparison == "gradual_vs_abrupt_early_ending"
    ].set_index("variable")
    differences = [
        comparison.loc[name, "standardized_median_difference"]
        for name in variables
    ]
    significant = [
        comparison.loc[name, "holm_adjusted_p_value"] < 0.05
        for name in variables
    ]
    fig, ax = plt.subplots(figsize=(8.2, 4.5), constrained_layout=True)
    colors = ["#D55E00" if value else "#A7A9AC" for value in significant]
    ax.barh(labels, differences, color=colors)
    ax.axvline(0, color="#202124", lw=1)
    ax.set(
        xlabel="Standardized median difference, gradual minus abrupt",
        title="Terminal weather change within early-ending candidates",
    )
    ax.grid(axis="x", alpha=0.2)
    for index, (value, raw, p_value) in enumerate(
        zip(
            differences,
            [comparison.loc[name, "median_difference"] for name in variables],
            [comparison.loc[name, "holm_adjusted_p_value"] for name in variables],
            strict=True,
        )
    ):
        ax.text(value, index, f" raw {raw:.2f}; adjusted p={p_value:.3f}", va="center", ha="left" if value >= 0 else "right", fontsize=8)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def plot_observation_robustness(summary: pd.DataFrame, output: Path) -> None:
    x = np.arange(len(summary))
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), constrained_layout=True)
    axes[0].plot(x, summary.candidate_abrupt_fraction, marker="o", label="Ended early")
    axes[0].plot(x, summary.true_persistent_abrupt_fraction, marker="o", label="True persistent")
    axes[0].set_ylim(0, 1)
    axes[0].set_ylabel("Abrupt-signature fraction")
    axes[0].legend(frameon=False)
    axes[1].bar(x, summary.fisher_odds_ratio, color="#4F79B7")
    axes[1].axhline(1, color="#202124", ls="--")
    axes[1].set_ylabel("Fisher odds ratio")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(["2 calendar", "3 calendar", "5 calendar", "3 active"], rotation=20)
        ax.grid(axis="y", alpha=0.2)
    axes[0].set_title("Abrupt-ending enrichment")
    axes[1].set_title("Sensitivity to observation window")
    fig.savefig(output, dpi=240)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    sequences = pd.read_csv(args.sequences)
    geometry = pd.read_csv(args.geometry)
    weather = pd.read_csv(args.weather)
    realization = pd.read_csv(args.realization)
    features = pd.read_csv(args.features)
    features = features[features.snapshot_day == args.snapshot_day].copy()
    features = add_observed_states(features, sequences)
    features = add_active_front_features(features, sequences, geometry)
    features = add_weather_features(features, weather)
    features = add_next_day_weather_features(features, weather)
    persistent_day = float(
        features.loc[features.ig_year <= 2012, "death_day"].quantile(0.90)
    )

    model_summary, tuning = evaluate_models(
        features,
        snapshot_day=args.snapshot_day,
        persistent_day=persistent_day,
    )
    changes = terminal_weather_changes(weather, snapshot_day=args.snapshot_day)
    weather_summary = weather_diagnostics(realization, changes)
    held_out_sequences = sequences[sequences.ig_year >= 2016]
    observation_summary = observation_robustness(held_out_sequences, realization)

    features.to_csv(
        output / "snapshot_features_with_front_weather.csv.gz",
        index=False,
        compression="gzip",
    )
    model_summary.to_csv(output / "missing_process_model_summary.csv", index=False)
    tuning.to_csv(output / "missing_process_model_tuning.csv", index=False)
    weather_summary.to_csv(output / "terminal_weather_diagnostics.csv", index=False)
    observation_summary.to_csv(
        output / "observation_process_robustness.csv", index=False
    )
    plot_model_comparison(model_summary, output / "missing_process_model_comparison.png")
    plot_weather_diagnostics(weather_summary, output / "terminal_weather_diagnostics.png")
    plot_observation_robustness(
        observation_summary, output / "observation_process_robustness.png"
    )

    indexed = model_summary.set_index(["target", "model"])
    weather_rows = weather_summary[
        weather_summary.comparison == "gradual_vs_abrupt_early_ending"
    ].set_index("variable")
    report = {
        "design": {
            "snapshot_day": args.snapshot_day,
            "persistent_threshold_day": persistent_day,
            "development_years": [2001, 2012],
            "calibration_years": [2013, 2015],
            "held_out_years": [2016, 2020],
            "weather_source": "gridMET daily nearest cell at FIRED final-footprint centroid",
            "weather_variables": [
                "vapor pressure deficit",
                "10 m wind speed",
                "100-hour fuel moisture",
                "energy release component",
                "precipitation",
            ],
            "active_front_proxy": "exterior perimeter of newly detected daily burned polygons relative to cumulative exterior perimeter",
        },
        "primary_results": {
            "base_persistent_auc": float(indexed.loc[("persistent_regime", "geometry_state"), "rank_auc"]),
            "active_weather_persistent_auc": float(indexed.loc[("persistent_regime", "geometry_state_active_weather"), "rank_auc"]),
            "next_day_weather_persistent_auc": float(indexed.loc[("persistent_regime", "geometry_state_active_weather_next_day"), "rank_auc"]),
            "base_final_area_factor": float(indexed.loc[("final_area", "geometry_state"), "typical_error_factor"]),
            "active_weather_final_area_factor": float(indexed.loc[("final_area", "geometry_state_active_weather"), "typical_error_factor"]),
            "next_day_weather_final_area_factor": float(indexed.loc[("final_area", "geometry_state_active_weather_next_day"), "typical_error_factor"]),
            "base_persistent_death_mae": float(indexed.loc[("death_day_persistent", "geometry_state"), "mean_absolute_error"]),
            "active_weather_persistent_death_mae": float(indexed.loc[("death_day_persistent", "geometry_state_active_weather"), "mean_absolute_error"]),
            "next_day_weather_persistent_death_mae": float(indexed.loc[("death_day_persistent", "geometry_state_active_weather_next_day"), "mean_absolute_error"]),
            "observation_robustness_min_abrupt_odds_ratio": float(observation_summary.fisher_odds_ratio.min()),
            "observation_robustness_max_abrupt_odds_ratio": float(observation_summary.fisher_odds_ratio.max()),
            "gradual_vs_abrupt_weather_holm_p_values": {
                variable: float(weather_rows.loc[variable, "holm_adjusted_p_value"])
                for variable in weather_rows.index
            },
        },
        "interpretation_limits": [
            "Past gridMET weather tests predictive value but cannot represent future weather after the snapshot.",
            "Observed next-day weather is an optimistic oracle diagnostic, not an operational forecast input.",
            "Terminal weather changes are retrospective mechanism diagnostics and cannot be used as day-7 predictors.",
            "Newly burned polygon perimeter is a satellite-detection proxy, not observed active flaming fireline.",
            "Centroid gridMET does not resolve within-fire weather gradients, terrain-channelled winds, or gusts.",
            "Fuel continuity and suppression exposure remain unobserved, so causal attribution remains unresolved.",
        ],
    }
    (output / "run_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (output / "README.md").write_text(
        "# FIRED missing-process tests\n\n"
        "This analysis adds past-only gridMET weather and a newly burned boundary "
        "proxy to held-out FIRED models, then evaluates terminal weather and observation "
        "window sensitivity as retrospective mechanism diagnostics. Fuel connectivity "
        "and suppression remain unobserved.\n",
        encoding="utf-8",
    )
    print(json.dumps(report["primary_results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
