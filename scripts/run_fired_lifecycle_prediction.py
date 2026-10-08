#!/usr/bin/env python3
"""Test FIRED acceleration timing and geometry-informed life-cycle forecasts."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fire_metabolism.fired_lifecycle import (
    AREA_FEATURE_COLUMNS,
    LIFECYCLE_FEATURE_COLUMNS,
    describe_lifecycle_outcomes,
    fit_neighbor_index,
    make_lifecycle_features,
    merge_geometry_sequences,
    neighbor_predict,
    tune_neighbor_count,
    tune_ridge_alpha,
)
from fire_metabolism.fired_outcomes import fit_standardized_ridge
from fire_metabolism.fired_prediction import transformed_trend_forecast


MODEL_LABELS = {
    "no_growth": "No future growth",
    "historical_median": "Historical median",
    "cube_root_recent": "Recent cube-root trend",
    "area_ridge": "Area-only ridge",
    "geometry_metabolic_ridge": "Geometry + metabolic ridge",
    "geometry_metabolic_analog": "Geometry + metabolic analog",
    "day5_phase_ridge": "Day-5 phase-calibrated ridge",
}
MODEL_COLORS = {
    "no_growth": "#666666",
    "historical_median": "#A6761D",
    "cube_root_recent": "#6495ED",
    "area_ridge": "#D95F02",
    "geometry_metabolic_ridge": "#1B9E77",
    "geometry_metabolic_analog": "#6A3D9A",
    "day5_phase_ridge": "#B52322",
}
AREA_TARGETS = {"final_area", "area_horizon_1", "area_horizon_3", "area_horizon_5", "area_horizon_7"}
SNAPSHOT_DAYS = (3, 5, 7, 10, 14, 21)


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
        default=Path(
            "outputs/fired_lifecycle_prediction/fired_geometry_sequences.csv.gz"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/fired_lifecycle_prediction"),
    )
    parser.add_argument("--seed", type=int, default=20261005)
    parser.add_argument("--smoothing-window", type=int, default=3)
    return parser.parse_args()


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return np.nan, np.nan
    probability = successes / total
    denominator = 1 + z**2 / total
    center = (probability + z**2 / (2 * total)) / denominator
    half = z * np.sqrt(probability * (1 - probability) / total + z**2 / (4 * total**2)) / denominator
    return center - half, center + half


def acceleration_summary(outcomes: pd.DataFrame, development_thresholds: dict[str, float]) -> pd.DataFrame:
    partitions = {
        "development": outcomes[outcomes.ig_year <= 2012],
        "calibration": outcomes[outcomes.ig_year.between(2013, 2015)],
        "held_out_test": outcomes[outcomes.ig_year >= 2016],
    }
    rows = []
    for partition, frame in partitions.items():
        groups = {"all": frame}
        for label, threshold in development_thresholds.items():
            groups[label] = frame[frame.final_area_km2 >= threshold]
        for group_name, group in groups.items():
            successes = int(group.growth_peak_after_day5.sum())
            lower, upper = wilson_interval(successes, len(group))
            rows.append(
                {
                    "partition": partition,
                    "size_group": group_name,
                    "development_area_threshold_km2": (
                        np.nan if group_name == "all" else development_thresholds[group_name]
                    ),
                    "n_events": int(len(group)),
                    "median_growth_peak_day": float(group.growth_peak_day.median()),
                    "growth_peak_day_q25": float(group.growth_peak_day.quantile(0.25)),
                    "growth_peak_day_q75": float(group.growth_peak_day.quantile(0.75)),
                    "growth_peak_day_q90": float(group.growth_peak_day.quantile(0.90)),
                    "fraction_peak_after_day5": float(successes / len(group)),
                    "fraction_peak_after_day5_ci95_lower": float(lower),
                    "fraction_peak_after_day5_ci95_upper": float(upper),
                }
            )
    return pd.DataFrame(rows)


def transformed_targets(frame: pd.DataFrame, target: str) -> np.ndarray:
    if target == "final_area":
        return np.log(frame.final_area_km2.to_numpy(dtype=float))
    if target.startswith("area_horizon_"):
        horizon = int(target.rsplit("_", 1)[1])
        return np.log(frame[f"area_horizon_{horizon}_km2"].to_numpy(dtype=float))
    if target == "death_day":
        remaining = np.maximum(0.0, frame.death_day.to_numpy(dtype=float) - frame.snapshot_day.to_numpy(dtype=float))
        return np.log1p(remaining)
    if target == "growth_peak_day":
        return frame.growth_peak_day.to_numpy(dtype=float)
    raise ValueError(f"unknown target: {target}")


def inverse_target(values: np.ndarray, frame: pd.DataFrame, target: str) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if target in AREA_TARGETS:
        return np.maximum(frame.snapshot_area_km2.to_numpy(dtype=float), np.exp(values))
    if target == "death_day":
        return np.clip(frame.snapshot_day.to_numpy(dtype=float) + np.expm1(values), frame.snapshot_day, 60)
    if target == "growth_peak_day":
        return np.clip(values, 1, 60)
    raise ValueError(f"unknown target: {target}")


def observed_target(frame: pd.DataFrame, target: str) -> np.ndarray:
    if target == "final_area":
        return frame.final_area_km2.to_numpy(dtype=float)
    if target.startswith("area_horizon_"):
        horizon = int(target.rsplit("_", 1)[1])
        return frame[f"area_horizon_{horizon}_km2"].to_numpy(dtype=float)
    return frame[target].to_numpy(dtype=float)


def baseline_prediction(
    model: str,
    target: str,
    development: pd.DataFrame,
    test: pd.DataFrame,
    sequences: pd.DataFrame,
) -> np.ndarray:
    if target in AREA_TARGETS:
        if model == "no_growth":
            return test.snapshot_area_km2.to_numpy(dtype=float)
        if model == "historical_median":
            observed = observed_target(development, target)
            multiplier = np.median(observed / development.snapshot_area_km2)
            return test.snapshot_area_km2.to_numpy(dtype=float) * multiplier
        if model == "cube_root_recent" and target.startswith("area_horizon_"):
            horizon = int(target.rsplit("_", 1)[1])
            sequence_groups = {event_id: event.sort_values("event_day") for event_id, event in sequences.groupby("id")}
            predictions = []
            for row in test.itertuples(index=False):
                event = sequence_groups[row.id]
                history = event[event.event_day <= row.snapshot_day].cumulative_area_km2.to_numpy(dtype=float)
                history = history[-min(4, len(history)) :]
                predictions.append(transformed_trend_forecast(history, horizon, 2 / 3))
            return np.asarray(predictions)
    if model == "historical_median" and target == "death_day":
        remaining = development.death_day - development.snapshot_day
        return test.snapshot_day.to_numpy(dtype=float) + float(np.median(remaining))
    if model == "historical_median" and target == "growth_peak_day":
        return np.repeat(float(development.growth_peak_day.median()), len(test))
    raise ValueError(f"unsupported baseline {model} for {target}")


def evaluate_snapshot(
    features: pd.DataFrame,
    sequences: pd.DataFrame,
    snapshot_day: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    development = features[features.ig_year <= 2012].reset_index(drop=True)
    calibration = features[features.ig_year.between(2013, 2015)].reset_index(drop=True)
    test = features[features.ig_year >= 2016].reset_index(drop=True)
    if min(len(development), len(calibration), len(test)) == 0:
        raise ValueError("one temporal partition is empty")

    lifecycle_index = fit_neighbor_index(development, LIFECYCLE_FEATURE_COLUMNS)
    maximum_neighbors = 100
    calibration_neighbors = lifecycle_index.neighbor_indices(calibration, maximum_neighbors)
    test_neighbors = lifecycle_index.neighbor_indices(test, maximum_neighbors)
    phase_neighbors, phase_curve = tune_neighbor_count(
        development.growth_peak_day.to_numpy(dtype=float),
        calibration.growth_peak_day.to_numpy(dtype=float),
        calibration_neighbors,
    )
    calibration_phase_after_day5 = neighbor_predict(
        development.growth_peak_day.to_numpy(dtype=float),
        calibration_neighbors,
        phase_neighbors,
    ) > 5
    test_phase_after_day5 = neighbor_predict(
        development.growth_peak_day.to_numpy(dtype=float),
        test_neighbors,
        phase_neighbors,
    ) > 5

    predictions = []
    tuning = []
    targets = [
        "area_horizon_1",
        "area_horizon_3",
        "area_horizon_5",
        "area_horizon_7",
        "final_area",
        "death_day",
        "growth_peak_day",
    ]
    for target in targets:
        y_development = transformed_targets(development, target)
        y_calibration = transformed_targets(calibration, target)
        y_test = observed_target(test, target)

        baseline_models = ["historical_median"]
        if target in AREA_TARGETS:
            baseline_models.insert(0, "no_growth")
        if target.startswith("area_horizon_"):
            baseline_models.append("cube_root_recent")
        for model in baseline_models:
            predicted = baseline_prediction(model, target, development, test, sequences)
            for row, observation, prediction in zip(test.itertuples(index=False), y_test, predicted, strict=True):
                predictions.append(
                    {
                        "id": row.id,
                        "ig_year": row.ig_year,
                        "lc_name": row.lc_name,
                        "snapshot_day": snapshot_day,
                        "target": target,
                        "model": model,
                        "observed": float(observation),
                        "predicted": float(prediction),
                    }
                )

        for model, columns in (
            ("area_ridge", AREA_FEATURE_COLUMNS),
            ("geometry_metabolic_ridge", LIFECYCLE_FEATURE_COLUMNS),
        ):
            alpha, curve = tune_ridge_alpha(
                development,
                calibration,
                y_development,
                y_calibration,
                feature_columns=columns,
            )
            fitted = fit_standardized_ridge(
                development,
                y_development,
                feature_columns=columns,
                alpha=alpha,
            )
            predicted = inverse_target(fitted.predict(test), test, target)
            for curve_row in curve.itertuples(index=False):
                tuning.append(
                    {
                        "snapshot_day": snapshot_day,
                        "target": target,
                        "model": model,
                        "hyperparameter": curve_row.hyperparameter,
                        "calibration_mae": curve_row.calibration_mae,
                        "selected": bool(curve_row.hyperparameter == alpha),
                    }
                )
            for row, observation, prediction in zip(test.itertuples(index=False), y_test, predicted, strict=True):
                predictions.append(
                    {
                        "id": row.id,
                        "ig_year": row.ig_year,
                        "lc_name": row.lc_name,
                        "snapshot_day": snapshot_day,
                        "target": target,
                        "model": model,
                        "observed": float(observation),
                        "predicted": float(prediction),
                    }
                )

        if target != "growth_peak_day":
            phase_rows = []
            for alpha in (0.1, 1.0, 10.0, 100.0):
                calibration_prediction = np.empty(len(calibration), dtype=float)
                for phase_value in (False, True):
                    train_mask = development.growth_peak_after_day5.to_numpy(dtype=bool) == phase_value
                    model = fit_standardized_ridge(
                        development.loc[train_mask],
                        y_development[train_mask],
                        feature_columns=LIFECYCLE_FEATURE_COLUMNS,
                        alpha=alpha,
                    )
                    predict_mask = calibration_phase_after_day5 == phase_value
                    calibration_prediction[predict_mask] = model.predict(
                        calibration.loc[predict_mask]
                    )
                phase_rows.append(
                    {
                        "hyperparameter": alpha,
                        "calibration_mae": float(
                            np.mean(
                                np.abs(calibration_prediction - y_calibration)
                            )
                        ),
                    }
                )
            phase_curve = pd.DataFrame(phase_rows)
            phase_alpha = float(
                phase_curve.loc[
                    phase_curve.calibration_mae.idxmin(), "hyperparameter"
                ]
            )
            test_transformed = np.empty(len(test), dtype=float)
            for phase_value in (False, True):
                train_mask = development.growth_peak_after_day5.to_numpy(dtype=bool) == phase_value
                model = fit_standardized_ridge(
                    development.loc[train_mask],
                    y_development[train_mask],
                    feature_columns=LIFECYCLE_FEATURE_COLUMNS,
                    alpha=phase_alpha,
                )
                predict_mask = test_phase_after_day5 == phase_value
                test_transformed[predict_mask] = model.predict(test.loc[predict_mask])
            predicted = inverse_target(test_transformed, test, target)
            for curve_row in phase_curve.itertuples(index=False):
                tuning.append(
                    {
                        "snapshot_day": snapshot_day,
                        "target": target,
                        "model": "day5_phase_ridge",
                        "hyperparameter": curve_row.hyperparameter,
                        "calibration_mae": curve_row.calibration_mae,
                        "selected": bool(
                            curve_row.hyperparameter == phase_alpha
                        ),
                    }
                )
            for row, observation, prediction in zip(
                test.itertuples(index=False), y_test, predicted, strict=True
            ):
                predictions.append(
                    {
                        "id": row.id,
                        "ig_year": row.ig_year,
                        "lc_name": row.lc_name,
                        "snapshot_day": snapshot_day,
                        "target": target,
                        "model": "day5_phase_ridge",
                        "observed": float(observation),
                        "predicted": float(prediction),
                    }
                )

        neighbors, curve = tune_neighbor_count(
            y_development,
            y_calibration,
            calibration_neighbors,
        )
        predicted = inverse_target(
            neighbor_predict(y_development, test_neighbors, neighbors), test, target
        )
        for curve_row in curve.itertuples(index=False):
            tuning.append(
                {
                    "snapshot_day": snapshot_day,
                    "target": target,
                    "model": "geometry_metabolic_analog",
                    "hyperparameter": curve_row.hyperparameter,
                    "calibration_mae": curve_row.calibration_mae,
                    "selected": bool(curve_row.hyperparameter == neighbors),
                }
            )
        for row, observation, prediction in zip(test.itertuples(index=False), y_test, predicted, strict=True):
            predictions.append(
                {
                    "id": row.id,
                    "ig_year": row.ig_year,
                    "lc_name": row.lc_name,
                    "snapshot_day": snapshot_day,
                    "target": target,
                    "model": "geometry_metabolic_analog",
                    "observed": float(observation),
                    "predicted": float(prediction),
                }
            )
    prediction_frame = pd.DataFrame(predictions)
    prediction_frame["error"] = prediction_frame.predicted - prediction_frame.observed
    is_area = prediction_frame.target.isin(AREA_TARGETS)
    prediction_frame.loc[is_area, "absolute_log_error"] = np.abs(
        np.log(
            prediction_frame.loc[is_area, "predicted"]
            / prediction_frame.loc[is_area, "observed"]
        )
    )
    prediction_frame.loc[is_area, "smape"] = (
        2
        * np.abs(prediction_frame.loc[is_area, "error"])
        / (
            prediction_frame.loc[is_area, "predicted"]
            + prediction_frame.loc[is_area, "observed"]
        )
    )
    return prediction_frame, pd.DataFrame(tuning)


def summarize_predictions(
    predictions: pd.DataFrame, *, largest_fire_threshold_km2: float
) -> pd.DataFrame:
    rows = []
    evaluation_groups = {
        "all": predictions,
        "development_top_10_percent": predictions[
            predictions.event_final_area_km2 >= largest_fire_threshold_km2
        ],
    }
    for evaluation_group, selected in evaluation_groups.items():
        for (snapshot, target, model), group in selected.groupby(
            ["snapshot_day", "target", "model"], sort=False
        ):
            row = {
                "evaluation_group": evaluation_group,
                "snapshot_day": int(snapshot),
                "target": target,
                "model": model,
                "n_events": int(group.id.nunique()),
                "mean_bias": float(group.error.mean()),
                "mean_absolute_error": float(np.abs(group.error).mean()),
                "median_absolute_error": float(np.abs(group.error).median()),
            }
            if target in AREA_TARGETS:
                row.update(
                    {
                        "mean_absolute_log_error": float(group.absolute_log_error.mean()),
                        "typical_error_factor": float(np.exp(group.absolute_log_error.mean())),
                        "mean_smape": float(group.smape.mean()),
                        "within_20_percent_fraction": float(
                            (group.absolute_log_error <= np.log(1.2)).mean()
                        ),
                    }
                )
            else:
                row.update(
                    {
                        "within_1_day_fraction": float((np.abs(group.error) <= 1).mean()),
                        "within_2_days_fraction": float((np.abs(group.error) <= 2).mean()),
                    }
                )
            if target == "growth_peak_day":
                observed_after = group.observed > 5
                predicted_after = group.predicted > 5
                row["after_day5_accuracy"] = float((observed_after == predicted_after).mean())
                row["after_day5_sensitivity"] = float(
                    (predicted_after & observed_after).sum() / max(1, observed_after.sum())
                )
                row["after_day5_specificity"] = float(
                    ((~predicted_after) & (~observed_after)).sum()
                    / max(1, (~observed_after).sum())
                )
            rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["evaluation_group", "target", "snapshot_day", "model"]
    )


def summarize_by_duration(
    outcomes: pd.DataFrame,
    predictions: pd.DataFrame,
) -> tuple[dict[str, float], pd.DataFrame, pd.DataFrame]:
    """Stratify held-out forecasts by development-period fire duration."""
    development = outcomes[outcomes.ig_year <= 2012]
    quantiles = {
        "q75": float(development.death_day.quantile(0.75)),
        "q90": float(development.death_day.quantile(0.90)),
        "q95": float(development.death_day.quantile(0.95)),
    }
    q75, q90, q95 = (quantiles[key] for key in ("q75", "q90", "q95"))
    labels = [
        f"through day {q75:g}",
        f"days {q75 + 1:g}-{q90 - 1:g}",
        f"days {q90:g}-{q95 - 1:g}",
        f"day {q95:g} or later",
    ]

    def assign_duration(frame: pd.DataFrame) -> pd.DataFrame:
        result = frame.copy()
        result["duration_order"] = np.select(
            [
                result.death_day <= q75,
                result.death_day < q90,
                result.death_day < q95,
            ],
            [0, 1, 2],
            default=3,
        ).astype(int)
        result["duration_group"] = result.duration_order.map(dict(enumerate(labels)))
        return result

    outcome_rows = []
    partitions = {
        "development": outcomes[outcomes.ig_year <= 2012],
        "calibration": outcomes[outcomes.ig_year.between(2013, 2015)],
        "held_out_test": outcomes[outcomes.ig_year >= 2016],
    }
    for partition, frame in partitions.items():
        assigned = assign_duration(frame)
        for (order, group_name), group in assigned.groupby(
            ["duration_order", "duration_group"], sort=True
        ):
            outcome_rows.append(
                {
                    "partition": partition,
                    "duration_order": int(order),
                    "duration_group": group_name,
                    "n_events": int(len(group)),
                    "median_death_day": float(group.death_day.median()),
                    "median_growth_peak_day": float(group.growth_peak_day.median()),
                    "growth_peak_day_q90": float(group.growth_peak_day.quantile(0.90)),
                    "fraction_peak_after_day5": float(group.growth_peak_after_day5.mean()),
                    "median_final_area_km2": float(group.final_area_km2.median()),
                }
            )
    outcome_summary = pd.DataFrame(outcome_rows)

    held_out_duration = assign_duration(
        outcomes[outcomes.ig_year >= 2016][["id", "death_day"]]
    )[["id", "duration_order", "duration_group"]]
    joined = predictions.merge(held_out_duration, on="id", how="left", validate="many_to_one")
    prediction_rows = []
    selected = joined[
        joined.target.isin(
            ["area_horizon_7", "final_area", "growth_peak_day", "death_day"]
        )
    ]
    for (order, group_name, snapshot, target, model), group in selected.groupby(
        ["duration_order", "duration_group", "snapshot_day", "target", "model"],
        sort=True,
    ):
        row = {
            "duration_order": int(order),
            "duration_group": group_name,
            "snapshot_day": int(snapshot),
            "target": target,
            "model": model,
            "n_events": int(group.id.nunique()),
            "mean_bias": float(group.error.mean()),
            "mean_absolute_error": float(np.abs(group.error).mean()),
        }
        if target in AREA_TARGETS:
            row["typical_error_factor"] = float(
                np.exp(group.absolute_log_error.mean())
            )
        else:
            row["within_2_days_fraction"] = float(
                (np.abs(group.error) <= 2).mean()
            )
        prediction_rows.append(row)
    prediction_summary = pd.DataFrame(prediction_rows)
    return quantiles, outcome_summary, prediction_summary


def summarize_long_fire_rolling(
    outcomes: pd.DataFrame,
    predictions: pd.DataFrame,
    duration_thresholds: dict[str, float],
) -> pd.DataFrame:
    """Evaluate rolling held-out forecasts for development-defined long fires."""
    held_out = outcomes[outcomes.ig_year >= 2016]
    scopes = {
        "long_q90_plus": held_out[
            held_out.death_day >= duration_thresholds["q90"]
        ].id,
        "extreme_q95_plus": held_out[
            held_out.death_day >= duration_thresholds["q95"]
        ].id,
    }
    rows = []
    for scope, ids in scopes.items():
        selected = predictions[
            predictions.id.isin(ids)
            & predictions.target.isin(["area_horizon_7", "final_area", "death_day"])
        ]
        for (snapshot, target, model), group in selected.groupby(
            ["snapshot_day", "target", "model"], sort=True
        ):
            row = {
                "duration_scope": scope,
                "snapshot_day": int(snapshot),
                "target": target,
                "model": model,
                "n_events": int(group.id.nunique()),
                "mean_bias": float(group.error.mean()),
                "mean_absolute_error": float(np.abs(group.error).mean()),
            }
            if target in AREA_TARGETS:
                row["typical_error_factor"] = float(
                    np.exp(group.absolute_log_error.mean())
                )
            else:
                row["within_2_days_fraction"] = float(
                    (np.abs(group.error) <= 2).mean()
                )
            rows.append(row)
    return pd.DataFrame(rows)


def plot_acceleration(summary: pd.DataFrame, outcomes: pd.DataFrame, threshold: float, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    test_big = outcomes[(outcomes.ig_year >= 2016) & (outcomes.final_area_km2 >= threshold)]
    values = np.sort(test_big.growth_peak_day.to_numpy())
    axes[0].step(values, np.arange(1, len(values) + 1) / len(values), where="post", color="#B52322", lw=2.6)
    axes[0].axvline(5, color="#202124", ls="--", lw=1.5, label="day 5")
    axes[0].set(
        xlabel="Smoothed growth-peak day",
        ylabel="Cumulative fraction",
        title=f"Held-out top-decile fires (n={len(test_big)})",
    )
    axes[0].legend(frameon=False)
    selected = summary[summary.size_group == "top_10_percent"]
    positions = np.arange(len(selected))
    fraction = selected.fraction_peak_after_day5.to_numpy()
    lower = selected.fraction_peak_after_day5_ci95_lower.to_numpy()
    upper = selected.fraction_peak_after_day5_ci95_upper.to_numpy()
    axes[1].bar(positions, fraction, color=["#4F79B7", "#B7822A", "#2E745B"], alpha=0.85)
    axes[1].errorbar(positions, fraction, yerr=np.vstack([fraction - lower, upper - fraction]), fmt="none", color="#202124", capsize=4)
    axes[1].axhline(0.5, color="#202124", ls="--", lw=1)
    axes[1].set_xticks(positions, ["development", "calibration", "held-out test"], rotation=15)
    axes[1].set_ylim(0, 1)
    axes[1].set_ylabel("Fraction peaking after day 5")
    axes[1].set_title("The day-5 claim replicates, but is not universal")
    for ax in axes:
        ax.grid(alpha=0.2)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def plot_area_performance(summary: pd.DataFrame, output: Path) -> None:
    selected = summary[
        (summary.evaluation_group == "all")
        & (summary.snapshot_day == 5)
        & summary.target.str.startswith("area_horizon_")
    ]
    fig, ax = plt.subplots(figsize=(9.2, 5.3))
    for model in MODEL_LABELS:
        values = selected[selected.model == model].copy()
        if values.empty:
            continue
        values["horizon"] = values.target.str.rsplit("_", n=1).str[-1].astype(int)
        values = values.sort_values("horizon")
        ax.plot(
            values.horizon,
            values.mean_absolute_log_error,
            marker="o",
            lw=2.2,
            color=MODEL_COLORS[model],
            label=MODEL_LABELS[model],
        )
    ax.set(
        xlabel="Forecast horizon from day 5 (days)",
        ylabel="Mean absolute log area error",
        title="Held-out FIRED later-trajectory prediction",
        xticks=[1, 3, 5, 7],
    )
    ax.grid(alpha=0.23)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output, dpi=240)
    plt.close(fig)


def plot_death_prediction(predictions: pd.DataFrame, summary: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.0), constrained_layout=True)
    death_summary = summary[
        (summary.evaluation_group == "all") & (summary.target == "death_day")
    ]
    for model in (
        "historical_median",
        "area_ridge",
        "geometry_metabolic_ridge",
        "geometry_metabolic_analog",
        "day5_phase_ridge",
    ):
        values = death_summary[death_summary.model == model].sort_values("snapshot_day")
        axes[0].plot(values.snapshot_day, values.mean_absolute_error, marker="o", lw=2.2, color=MODEL_COLORS[model], label=MODEL_LABELS[model])
    axes[0].set(xlabel="Snapshot day", ylabel="Mean absolute death-day error", xticks=SNAPSHOT_DAYS, title="Death timing on held-out fires")
    axes[0].grid(alpha=0.23)
    axes[0].legend(frameon=False, fontsize=8)
    panel = predictions[(predictions.target == "death_day") & (predictions.snapshot_day == 5) & (predictions.model == "geometry_metabolic_ridge")]
    axes[1].hexbin(panel.observed, panel.predicted, gridsize=35, mincnt=1, bins="log", cmap="magma_r")
    limits = [min(panel.observed.min(), panel.predicted.min()), max(panel.observed.max(), panel.predicted.max())]
    axes[1].plot(limits, limits, color="#202124", ls="--", lw=1.3)
    axes[1].set(xlabel="Observed last-growth day", ylabel="Predicted last-growth day", title="Day-5 geometry + metabolic ridge")
    axes[1].grid(alpha=0.18)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def plot_geometry_qa(merged: pd.DataFrame, features: pd.DataFrame, output: Path) -> None:
    relative = np.abs(merged.polygon_area_km2 - merged.cumulative_area_km2) / merged.cumulative_area_km2
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)
    axes[0].hist(np.minimum(relative, 0.03) * 100, bins=45, color="#4F79B7", alpha=0.85)
    axes[0].axvline(relative.median() * 100, color="#202124", lw=1.4, label=f"median {relative.median()*100:.2f}%")
    axes[0].set(xlabel="Absolute polygon/attribute area difference (%)", ylabel="Daily records", title="Geometry-area reconciliation (tail clipped at 3%)")
    axes[0].legend(frameon=False)
    axes[1].hist(features.total_perimeter_area_slope, bins=50, range=(-0.5, 1.5), color="#2E745B", alpha=0.85)
    axes[1].axvline(0.5, color="#B52322", ls="--", lw=1.5, label="1/2")
    axes[1].axvline(2 / 3, color="#6495ED", ls="--", lw=1.5, label="2/3")
    axes[1].set(xlabel="Early observed log P / log A slope", ylabel="Events", title="Perimeter-area slopes through day 5")
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.grid(alpha=0.18)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def plot_duration_strata(
    outcomes: pd.DataFrame,
    prediction_summary: pd.DataFrame,
    output: Path,
) -> None:
    held_out = outcomes[outcomes.partition == "held_out_test"].sort_values(
        "duration_order"
    )
    labels = held_out.duration_group.tolist()
    positions = np.arange(len(labels))
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.9), constrained_layout=True)

    axes[0].bar(
        positions,
        held_out.fraction_peak_after_day5 * 100,
        color=["#7899C7", "#D6A84D", "#D36A4A", "#8F2D2D"],
        alpha=0.9,
    )
    for position, row in zip(positions, held_out.itertuples(index=False), strict=True):
        axes[0].text(
            position,
            row.fraction_peak_after_day5 * 100 + 2.5,
            f"peak day {row.median_growth_peak_day:g}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    axes[0].set(
        ylabel="Peak after day 5 (%)",
        title="Long fires are still accelerating",
        ylim=(0, 112),
    )

    for model in (
        "historical_median",
        "geometry_metabolic_ridge",
        "day5_phase_ridge",
    ):
        values = prediction_summary[
            (prediction_summary.snapshot_day == 5)
            & (prediction_summary.target == "death_day")
            & (prediction_summary.model == model)
        ].sort_values("duration_order")
        axes[1].plot(
            values.duration_order,
            values.mean_absolute_error,
            marker="o",
            lw=2.2,
            color=MODEL_COLORS[model],
            label=MODEL_LABELS[model],
        )
    axes[1].set(
        ylabel="Death-day MAE (days)",
        title="Day-5 death forecasts regress to ordinary fires",
    )
    axes[1].legend(frameon=False, fontsize=8)

    for target, label, color in (
        ("area_horizon_7", "Area seven days later", "#4F79B7"),
        ("final_area", "Final area", "#B52322"),
    ):
        values = prediction_summary[
            (prediction_summary.snapshot_day == 5)
            & (prediction_summary.target == target)
            & (prediction_summary.model == "geometry_metabolic_ridge")
        ].sort_values("duration_order")
        axes[2].plot(
            values.duration_order,
            values.typical_error_factor,
            marker="o",
            lw=2.2,
            color=color,
            label=label,
        )
    axes[2].axhline(1, color="#202124", ls="--", lw=1)
    axes[2].set(
        ylabel="Typical multiplicative error",
        title="Near-term area remains more predictable",
    )
    axes[2].legend(frameon=False, fontsize=8)

    for ax in axes:
        ax.set_xticks(positions, labels, rotation=20, ha="right")
        ax.grid(alpha=0.2)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def plot_long_fire_rolling(summary: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), constrained_layout=True)
    styles = {
        "long_q90_plus": ("Long fires (development Q90+)", "#2E745B"),
        "extreme_q95_plus": ("Extreme duration (development Q95+)", "#B52322"),
    }
    for scope, (label, color) in styles.items():
        death = summary[
            (summary.duration_scope == scope)
            & (summary.target == "death_day")
            & (summary.model == "geometry_metabolic_ridge")
        ].sort_values("snapshot_day")
        area = summary[
            (summary.duration_scope == scope)
            & (summary.target == "final_area")
            & (summary.model == "geometry_metabolic_ridge")
        ].sort_values("snapshot_day")
        axes[0].plot(
            death.snapshot_day,
            death.mean_absolute_error,
            marker="o",
            lw=2.4,
            color=color,
            label=label,
        )
        axes[1].plot(
            area.snapshot_day,
            area.typical_error_factor,
            marker="o",
            lw=2.4,
            color=color,
            label=label,
        )
    axes[0].set(
        xlabel="Forecast snapshot day",
        ylabel="Death-day MAE (days)",
        title="Rolling state updates improve death timing",
        xticks=SNAPSHOT_DAYS,
    )
    axes[1].axhline(1, color="#202124", ls="--", lw=1)
    axes[1].set(
        xlabel="Forecast snapshot day",
        ylabel="Final-area typical error factor",
        title="Final size becomes identifiable later",
        xticks=SNAPSHOT_DAYS,
    )
    for ax in axes:
        ax.grid(alpha=0.2)
        ax.legend(frameon=False, fontsize=8)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    sequences = pd.read_csv(args.sequences, parse_dates=["date"])
    geometry = pd.read_csv(args.geometry)
    merged = merge_geometry_sequences(sequences, geometry)
    outcomes = describe_lifecycle_outcomes(
        merged, smoothing_window=args.smoothing_window
    )
    development = outcomes[outcomes.ig_year <= 2012]
    thresholds = {
        "top_50_percent": float(development.final_area_km2.quantile(0.50)),
        "top_25_percent": float(development.final_area_km2.quantile(0.75)),
        "top_10_percent": float(development.final_area_km2.quantile(0.90)),
        "top_5_percent": float(development.final_area_km2.quantile(0.95)),
    }
    acceleration = acceleration_summary(outcomes, thresholds)

    all_features = []
    all_predictions = []
    all_tuning = []
    for snapshot in SNAPSHOT_DAYS:
        features = make_lifecycle_features(
            merged,
            snapshot,
            smoothing_window=args.smoothing_window,
        )
        predictions, tuning = evaluate_snapshot(features, merged, snapshot)
        all_features.append(features)
        all_predictions.append(predictions)
        all_tuning.append(tuning)
    features = pd.concat(all_features, ignore_index=True)
    predictions = pd.concat(all_predictions, ignore_index=True)
    tuning = pd.concat(all_tuning, ignore_index=True)
    final_area_by_id = outcomes.set_index("id")["final_area_km2"]
    predictions["event_final_area_km2"] = predictions.id.map(final_area_by_id)
    summary = summarize_predictions(
        predictions,
        largest_fire_threshold_km2=thresholds["top_10_percent"],
    )
    duration_thresholds, duration_outcomes, duration_predictions = summarize_by_duration(
        outcomes, predictions
    )
    long_fire_rolling = summarize_long_fire_rolling(
        outcomes, predictions, duration_thresholds
    )

    acceleration.to_csv(output / "acceleration_timing_summary.csv", index=False)
    outcomes.to_csv(output / "event_lifecycle_outcomes.csv.gz", index=False, compression="gzip")
    features.to_csv(output / "snapshot_features.csv.gz", index=False, compression="gzip")
    predictions.to_csv(output / "held_out_lifecycle_predictions.csv.gz", index=False, compression="gzip")
    summary.to_csv(output / "lifecycle_prediction_summary.csv", index=False)
    duration_outcomes.to_csv(output / "duration_stratified_outcomes.csv", index=False)
    duration_predictions.to_csv(
        output / "duration_stratified_prediction_summary.csv", index=False
    )
    long_fire_rolling.to_csv(
        output / "long_fire_rolling_prediction_summary.csv", index=False
    )
    tuning.to_csv(output / "calibration_tuning.csv", index=False)

    plot_acceleration(
        acceleration,
        outcomes,
        thresholds["top_10_percent"],
        output / "acceleration_cessation_day5.png",
    )
    plot_area_performance(summary, output / "later_area_prediction.png")
    plot_death_prediction(predictions, summary, output / "death_day_prediction.png")
    day5_features = features[features.snapshot_day == 5]
    plot_geometry_qa(merged, day5_features, output / "geometry_quality_assurance.png")
    plot_duration_strata(
        duration_outcomes,
        duration_predictions,
        output / "long_fire_failure_modes.png",
    )
    plot_long_fire_rolling(
        long_fire_rolling,
        output / "long_fire_rolling_updates.png",
    )

    test_top_decile = acceleration[
        (acceleration.partition == "held_out_test")
        & (acceleration.size_group == "top_10_percent")
    ].iloc[0]
    day5_death = summary[
        (summary.evaluation_group == "all")
        & (summary.snapshot_day == 5)
        & (summary.target == "death_day")
        & (summary.model == "geometry_metabolic_ridge")
    ].iloc[0]
    day5_final = summary[
        (summary.evaluation_group == "all")
        & (summary.snapshot_day == 5)
        & (summary.target == "final_area")
        & (summary.model == "geometry_metabolic_ridge")
    ].iloc[0]
    day5_big_death = summary[
        (summary.evaluation_group == "development_top_10_percent")
        & (summary.snapshot_day == 5)
        & (summary.target == "death_day")
        & (summary.model == "geometry_metabolic_ridge")
    ].iloc[0]
    day5_phase_final = summary[
        (summary.evaluation_group == "all")
        & (summary.snapshot_day == 5)
        & (summary.target == "final_area")
        & (summary.model == "day5_phase_ridge")
    ].iloc[0]
    day5_phase_death = summary[
        (summary.evaluation_group == "all")
        & (summary.snapshot_day == 5)
        & (summary.target == "death_day")
        & (summary.model == "day5_phase_ridge")
    ].iloc[0]
    day5_big_phase_final = summary[
        (summary.evaluation_group == "development_top_10_percent")
        & (summary.snapshot_day == 5)
        & (summary.target == "final_area")
        & (summary.model == "day5_phase_ridge")
    ].iloc[0]
    day5_big_phase_death = summary[
        (summary.evaluation_group == "development_top_10_percent")
        & (summary.snapshot_day == 5)
        & (summary.target == "death_day")
        & (summary.model == "day5_phase_ridge")
    ].iloc[0]
    held_out = outcomes[outcomes.ig_year >= 2016]
    long_ids = held_out[
        held_out.death_day >= duration_thresholds["q90"]
    ].id
    extreme_ids = held_out[
        held_out.death_day >= duration_thresholds["q95"]
    ].id
    long_geometry = predictions[
        (predictions.snapshot_day == 5)
        & (predictions.model == "geometry_metabolic_ridge")
        & predictions.id.isin(long_ids)
    ]
    long_death = long_geometry[long_geometry.target == "death_day"]
    long_final = long_geometry[long_geometry.target == "final_area"]
    long_horizon = long_geometry[long_geometry.target == "area_horizon_7"]
    held_out_long = held_out[held_out.id.isin(long_ids)]
    held_out_extreme = held_out[held_out.id.isin(extreme_ids)]
    day21_long = long_fire_rolling[
        (long_fire_rolling.duration_scope == "long_q90_plus")
        & (long_fire_rolling.snapshot_day == 21)
        & (long_fire_rolling.model == "geometry_metabolic_ridge")
    ]
    day21_long_death = day21_long[day21_long.target == "death_day"].iloc[0]
    day21_long_final = day21_long[day21_long.target == "final_area"].iloc[0]
    day21_extreme = long_fire_rolling[
        (long_fire_rolling.duration_scope == "extreme_q95_plus")
        & (long_fire_rolling.snapshot_day == 21)
        & (long_fire_rolling.model == "geometry_metabolic_ridge")
    ]
    day21_extreme_death = day21_extreme[day21_extreme.target == "death_day"].iloc[0]
    day21_extreme_final = day21_extreme[day21_extreme.target == "final_area"].iloc[0]
    report = {
        "design": {
            "development_years": [2001, 2012],
            "calibration_years": [2013, 2015],
            "held_out_test_years": [2016, 2020],
            "snapshot_days": list(SNAPSHOT_DAYS),
            "trajectory_horizons_days": [1, 3, 5, 7],
            "smoothing_window_days": args.smoothing_window,
            "largest_fire_definition": "top decile using development-year final area only",
            "development_top_decile_threshold_km2": thresholds["top_10_percent"],
            "long_fire_definition": "death day at or above the development-period 90th percentile",
            "development_duration_quantiles_days": duration_thresholds,
            "death_definition": "last day with positive FIRED detected area increment",
            "acceleration_cessation_proxy": "day of maximum centered smoothed daily area growth",
        },
        "counts": {
            "events": int(outcomes.id.nunique()),
            "development_events": int((outcomes.ig_year <= 2012).sum()),
            "calibration_events": int(outcomes.ig_year.between(2013, 2015).sum()),
            "held_out_test_events": int((outcomes.ig_year >= 2016).sum()),
            "geometry_detection_day_rows": int(len(geometry)),
            "prediction_rows": int(len(predictions)),
        },
        "primary_results": {
            "held_out_top_decile_n": int(test_top_decile.n_events),
            "held_out_top_decile_median_growth_peak_day": float(test_top_decile.median_growth_peak_day),
            "held_out_top_decile_fraction_peak_after_day5": float(test_top_decile.fraction_peak_after_day5),
            "held_out_top_decile_fraction_peak_after_day5_ci95": [
                float(test_top_decile.fraction_peak_after_day5_ci95_lower),
                float(test_top_decile.fraction_peak_after_day5_ci95_upper),
            ],
            "day5_geometry_metabolic_final_area_typical_error_factor": float(day5_final.typical_error_factor),
            "day5_geometry_metabolic_death_day_mae": float(day5_death.mean_absolute_error),
            "day5_geometry_metabolic_death_within_2_days": float(day5_death.within_2_days_fraction),
            "day5_top_decile_geometry_metabolic_death_day_mae": float(
                day5_big_death.mean_absolute_error
            ),
            "day5_phase_calibrated_final_area_typical_error_factor": float(
                day5_phase_final.typical_error_factor
            ),
            "day5_phase_calibrated_death_day_mae": float(
                day5_phase_death.mean_absolute_error
            ),
            "day5_top_decile_phase_calibrated_final_area_typical_error_factor": float(
                day5_big_phase_final.typical_error_factor
            ),
            "day5_top_decile_phase_calibrated_death_day_mae": float(
                day5_big_phase_death.mean_absolute_error
            ),
            "held_out_long_fire_n": int(len(held_out_long)),
            "held_out_long_fire_median_growth_peak_day": float(
                held_out_long.growth_peak_day.median()
            ),
            "held_out_long_fire_fraction_peak_after_day5": float(
                held_out_long.growth_peak_after_day5.mean()
            ),
            "held_out_extreme_duration_fire_n": int(len(held_out_extreme)),
            "held_out_extreme_duration_median_growth_peak_day": float(
                held_out_extreme.growth_peak_day.median()
            ),
            "day5_long_fire_geometry_death_day_mae": float(
                np.abs(long_death.error).mean()
            ),
            "day5_long_fire_geometry_death_day_bias": float(long_death.error.mean()),
            "day5_long_fire_geometry_final_area_typical_error_factor": float(
                np.exp(long_final.absolute_log_error.mean())
            ),
            "day5_long_fire_geometry_seven_day_area_typical_error_factor": float(
                np.exp(long_horizon.absolute_log_error.mean())
            ),
            "day21_long_fire_geometry_death_day_mae": float(
                day21_long_death.mean_absolute_error
            ),
            "day21_long_fire_geometry_final_area_typical_error_factor": float(
                day21_long_final.typical_error_factor
            ),
            "day21_extreme_duration_geometry_death_day_mae": float(
                day21_extreme_death.mean_absolute_error
            ),
            "day21_extreme_duration_geometry_final_area_typical_error_factor": float(
                day21_extreme_final.typical_error_factor
            ),
        },
        "geometry_qa": {
            "median_absolute_polygon_attribute_area_difference_fraction": float(
                np.median(
                    np.abs(merged.polygon_area_km2 - merged.cumulative_area_km2)
                    / merged.cumulative_area_km2
                )
            )
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "limitations": [
            "FIRED is a retrospective MODIS-derived product with daily timing and approximately 500 m geometry.",
            "The measured cumulative perimeter is not the independently observed active fireline length.",
            "Perimeter and component metrics depend on raster resolution and polygon conventions.",
            "The growth-peak day is a smoothed satellite-detection proxy for acceleration cessation.",
            "The last positive detected increment is a data-product death time, not an incident-control declaration.",
            "Weather, suppression, fuel moisture, and topography are not yet included.",
        ],
    }
    (output / "run_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "README.md").write_text(
        "# FIRED life-cycle prediction outputs\n\n"
        "The workflow tests the day-5 acceleration hypothesis, measures cumulative polygon geometry, "
        "and compares area-only forecasts with perimeter-area and two-thirds metabolic features. "
        "Duration-stratified tables and `long_fire_failure_modes.png` isolate the much longer fires. "
        "Development, calibration, and held-out test years remain temporally separated. "
        "See `run_report.json` for definitions, counts, primary results, and limitations.\n",
        encoding="utf-8",
    )
    print(json.dumps(report["primary_results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
