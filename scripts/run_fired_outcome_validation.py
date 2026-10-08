#!/usr/bin/env python3
"""Predict FIRED final outcomes from early growth and validate on later fires."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fire_metabolism.fired_outcomes import (
    EARLY_FEATURE_COLUMNS,
    describe_fire_outcomes,
    fit_standardized_ridge,
    make_early_features,
)


MODEL_LABELS = {
    "no_future_growth": "No future growth",
    "training_median": "Historical median",
    "early_trajectory": "Early trajectory",
}
MODEL_COLORS = {
    "no_future_growth": "#555555",
    "training_median": "#0072B2",
    "early_trajectory": "#D55E00",
}


def _predict_partition(
    frame: pd.DataFrame,
    *,
    snapshot_day: int,
    area_model,
    duration_model,
    median_area_multiplier: float,
    median_remaining_days: float,
) -> pd.DataFrame:
    common = frame[
        [
            "id",
            "ig_year",
            "lc_name",
            "snapshot_area_km2",
            "final_area_km2",
            "duration_days",
        ]
    ].copy()
    common["snapshot_day"] = snapshot_day
    rows = []

    baseline = common.copy()
    baseline["model"] = "no_future_growth"
    baseline["predicted_final_area_km2"] = baseline["snapshot_area_km2"]
    baseline["predicted_duration_days"] = float(snapshot_day + 1)
    rows.append(baseline)

    historical = common.copy()
    historical["model"] = "training_median"
    historical["predicted_final_area_km2"] = (
        historical["snapshot_area_km2"] * median_area_multiplier
    )
    historical["predicted_duration_days"] = snapshot_day + median_remaining_days
    rows.append(historical)

    trajectory = common.copy()
    trajectory["model"] = "early_trajectory"
    trajectory["predicted_final_area_km2"] = np.maximum(
        trajectory["snapshot_area_km2"].to_numpy(dtype=float),
        np.exp(area_model.predict(frame)),
    )
    trajectory["predicted_duration_days"] = np.clip(
        snapshot_day + np.expm1(duration_model.predict(frame)),
        snapshot_day + 1,
        60,
    )
    rows.append(trajectory)
    return pd.concat(rows, ignore_index=True)


def fit_snapshot_models(
    development: pd.DataFrame,
    calibration: pd.DataFrame,
    testing: pd.DataFrame,
    snapshot_day: int,
    *,
    alpha: float,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    dev = make_early_features(development, snapshot_day)
    cal = make_early_features(calibration, snapshot_day)
    test = make_early_features(testing, snapshot_day)
    area_model = fit_standardized_ridge(
        dev,
        np.log(dev["final_area_km2"].to_numpy(dtype=float)),
        feature_columns=EARLY_FEATURE_COLUMNS,
        alpha=alpha,
    )
    duration_model = fit_standardized_ridge(
        dev,
        np.log1p(dev["duration_days"].to_numpy(dtype=float) - snapshot_day),
        feature_columns=EARLY_FEATURE_COLUMNS,
        alpha=alpha,
    )
    median_area_multiplier = float(
        np.median(dev["final_area_km2"] / dev["snapshot_area_km2"])
    )
    median_remaining_days = float(np.median(dev["duration_days"] - snapshot_day))
    parameters = {
        "snapshot_day": snapshot_day,
        "ridge_alpha": alpha,
        "median_area_multiplier": median_area_multiplier,
        "median_remaining_days": median_remaining_days,
    }
    calibration_predictions = _predict_partition(
        cal,
        snapshot_day=snapshot_day,
        area_model=area_model,
        duration_model=duration_model,
        median_area_multiplier=median_area_multiplier,
        median_remaining_days=median_remaining_days,
    )
    test_predictions = _predict_partition(
        test,
        snapshot_day=snapshot_day,
        area_model=area_model,
        duration_model=duration_model,
        median_area_multiplier=median_area_multiplier,
        median_remaining_days=median_remaining_days,
    )
    return calibration_predictions, test_predictions, parameters


def calibrate_intervals(
    calibration: pd.DataFrame, *, nominal_coverage: float = 0.9
) -> pd.DataFrame:
    rows = []
    for (snapshot, model), group in calibration.groupby(["snapshot_day", "model"]):
        area_residual = np.abs(
            np.log(group["predicted_final_area_km2"] / group["final_area_km2"])
        )
        duration_residual = np.abs(
            group["predicted_duration_days"] - group["duration_days"]
        )
        rows.append(
            {
                "snapshot_day": int(snapshot),
                "model": model,
                "nominal_coverage": nominal_coverage,
                "n_calibration_events": int(group["id"].nunique()),
                "area_absolute_log_radius": float(
                    np.quantile(area_residual, nominal_coverage, method="higher")
                ),
                "duration_absolute_day_radius": float(
                    np.quantile(duration_residual, nominal_coverage, method="higher")
                ),
            }
        )
    return pd.DataFrame(rows)


def apply_intervals(predictions: pd.DataFrame, intervals: pd.DataFrame) -> pd.DataFrame:
    result = predictions.merge(
        intervals,
        on=["snapshot_day", "model"],
        how="left",
        validate="many_to_one",
    )
    radius = result["area_absolute_log_radius"].to_numpy(dtype=float)
    predicted_area = result["predicted_final_area_km2"].to_numpy(dtype=float)
    result["final_area_lower_km2"] = predicted_area * np.exp(-radius)
    result["final_area_upper_km2"] = predicted_area * np.exp(radius)
    duration_radius = result["duration_absolute_day_radius"].to_numpy(dtype=float)
    predicted_duration = result["predicted_duration_days"].to_numpy(dtype=float)
    result["duration_lower_days"] = np.maximum(
        result["snapshot_day"].to_numpy(dtype=float) + 1,
        predicted_duration - duration_radius,
    )
    result["duration_upper_days"] = np.minimum(60, predicted_duration + duration_radius)
    result["area_absolute_log_error"] = np.abs(
        np.log(result["predicted_final_area_km2"] / result["final_area_km2"])
    )
    result["area_log_error"] = np.log(
        result["predicted_final_area_km2"] / result["final_area_km2"]
    )
    result["area_smape"] = (
        2
        * np.abs(result["predicted_final_area_km2"] - result["final_area_km2"])
        / (result["predicted_final_area_km2"] + result["final_area_km2"])
    )
    result["duration_absolute_error_days"] = np.abs(
        result["predicted_duration_days"] - result["duration_days"]
    )
    result["duration_error_days"] = (
        result["predicted_duration_days"] - result["duration_days"]
    )
    result["area_interval_contains"] = (
        (result["final_area_km2"] >= result["final_area_lower_km2"])
        & (result["final_area_km2"] <= result["final_area_upper_km2"])
    )
    result["duration_interval_contains"] = (
        (result["duration_days"] >= result["duration_lower_days"])
        & (result["duration_days"] <= result["duration_upper_days"])
    )
    return result


def summarize_validation(
    predictions: pd.DataFrame, *, bootstrap_replicates: int, seed: int
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for (snapshot, model), group in predictions.groupby(["snapshot_day", "model"]):
        area_error = group["area_absolute_log_error"].to_numpy(dtype=float)
        duration_error = group["duration_absolute_error_days"].to_numpy(dtype=float)
        if bootstrap_replicates:
            indices = rng.integers(
                0, len(group), size=(bootstrap_replicates, len(group))
            )
            area_boot = area_error[indices].mean(axis=1)
            duration_boot = duration_error[indices].mean(axis=1)
            area_lower, area_upper = np.quantile(area_boot, [0.025, 0.975])
            duration_lower, duration_upper = np.quantile(duration_boot, [0.025, 0.975])
        else:
            area_lower = area_upper = duration_lower = duration_upper = np.nan
        observed_log_area = np.log(group["final_area_km2"].to_numpy(dtype=float))
        predicted_log_area = np.log(
            group["predicted_final_area_km2"].to_numpy(dtype=float)
        )
        area_denominator = np.sum((observed_log_area - observed_log_area.mean()) ** 2)
        duration_observed = group["duration_days"].to_numpy(dtype=float)
        duration_predicted = group["predicted_duration_days"].to_numpy(dtype=float)
        duration_denominator = np.sum((duration_observed - duration_observed.mean()) ** 2)
        rows.append(
            {
                "snapshot_day": int(snapshot),
                "model": model,
                "n_test_events": int(group["id"].nunique()),
                "mean_absolute_log_area_error": float(area_error.mean()),
                "area_error_ci95_lower": float(area_lower),
                "area_error_ci95_upper": float(area_upper),
                "typical_area_error_factor": float(np.exp(area_error.mean())),
                "mean_area_smape": float(group["area_smape"].mean()),
                "mean_area_log_bias": float(group["area_log_error"].mean()),
                "log_area_r2": float(
                    1 - np.sum((predicted_log_area - observed_log_area) ** 2) / area_denominator
                ),
                "area_interval_coverage": float(group["area_interval_contains"].mean()),
                "mean_absolute_duration_error_days": float(duration_error.mean()),
                "duration_error_ci95_lower": float(duration_lower),
                "duration_error_ci95_upper": float(duration_upper),
                "mean_duration_bias_days": float(group["duration_error_days"].mean()),
                "duration_r2": float(
                    1 - np.sum((duration_predicted - duration_observed) ** 2) / duration_denominator
                ),
                "duration_interval_coverage": float(
                    group["duration_interval_contains"].mean()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(["snapshot_day", "model"]).reset_index(drop=True)


def describe_groups(outcomes: pd.DataFrame) -> pd.DataFrame:
    groups = [("All held-out events", outcomes)]
    groups.extend((name, group) for name, group in outcomes.groupby("lc_name"))
    rows = []
    for name, group in groups:
        rows.append(
            {
                "group": name,
                "n_events": int(len(group)),
                "final_area_median_km2": float(group["final_area_km2"].median()),
                "final_area_q25_km2": float(group["final_area_km2"].quantile(0.25)),
                "final_area_q75_km2": float(group["final_area_km2"].quantile(0.75)),
                "duration_median_days": float(group["duration_days"].median()),
                "duration_q25_days": float(group["duration_days"].quantile(0.25)),
                "duration_q75_days": float(group["duration_days"].quantile(0.75)),
                "peak_growth_median_km2_per_day": float(
                    group["peak_daily_growth_km2"].median()
                ),
                "half_area_timing_median": float(group["half_area_timing"].median()),
                "ninety_area_timing_median": float(group["ninety_area_timing"].median()),
                "peak_growth_timing_median": float(group["peak_growth_timing"].median()),
                "growth_burstiness_median": float(group["growth_burstiness"].median()),
                "active_growth_fraction_median": float(
                    group["active_growth_fraction"].median()
                ),
                "area_fraction_day_3_median": float(
                    group["area_fraction_day_3"].median()
                ),
                "area_fraction_day_5_median": float(
                    group["area_fraction_day_5"].median()
                ),
                "area_fraction_day_7_median": float(
                    group["area_fraction_day_7"].median()
                ),
            }
        )
    return pd.DataFrame(rows)


def plot_performance(summary: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    for model in MODEL_LABELS:
        values = summary[summary["model"] == model].sort_values("snapshot_day")
        x = values["snapshot_day"].to_numpy()
        area = values["mean_absolute_log_area_error"].to_numpy()
        duration = values["mean_absolute_duration_error_days"].to_numpy()
        axes[0].errorbar(
            x,
            area,
            yerr=np.vstack(
                [
                    area - values["area_error_ci95_lower"].to_numpy(),
                    values["area_error_ci95_upper"].to_numpy() - area,
                ]
            ),
            color=MODEL_COLORS[model],
            label=MODEL_LABELS[model],
            marker="o",
            linewidth=2.2,
            capsize=3,
        )
        axes[1].errorbar(
            x,
            duration,
            yerr=np.vstack(
                [
                    duration - values["duration_error_ci95_lower"].to_numpy(),
                    values["duration_error_ci95_upper"].to_numpy() - duration,
                ]
            ),
            color=MODEL_COLORS[model],
            label=MODEL_LABELS[model],
            marker="o",
            linewidth=2.2,
            capsize=3,
        )
    axes[0].set_title("Final-area prediction")
    axes[0].set_ylabel("Mean absolute log error")
    axes[1].set_title("Duration prediction")
    axes[1].set_ylabel("Mean absolute error (days)")
    for axis in axes:
        axis.set_xlabel("Information available through event day")
        axis.set_xticks([3, 5, 7])
        axis.grid(True, alpha=0.25)
    axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("Prediction of grown-fire outcomes on held-out FIRED events, 2016-2020")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(output, dpi=220)
    plt.close(fig)


def plot_observed_predicted(predictions: pd.DataFrame, output: Path, snapshot_day: int = 5) -> None:
    values = predictions[predictions["snapshot_day"] == snapshot_day]
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 8.2))
    for column, model in enumerate(MODEL_LABELS):
        group = values[values["model"] == model]
        area_axis = axes[0, column]
        area_axis.hexbin(
            group["final_area_km2"],
            group["predicted_final_area_km2"],
            xscale="log",
            yscale="log",
            gridsize=34,
            bins="log",
            mincnt=1,
            cmap="magma_r",
        )
        area_bounds = [
            min(group["final_area_km2"].min(), group["predicted_final_area_km2"].min()),
            max(group["final_area_km2"].max(), group["predicted_final_area_km2"].max()),
        ]
        area_axis.plot(area_bounds, area_bounds, color="#444444", linestyle="--")
        area_axis.set_title(MODEL_LABELS[model])
        duration_axis = axes[1, column]
        duration_axis.hexbin(
            group["duration_days"],
            group["predicted_duration_days"],
            gridsize=30,
            bins="log",
            mincnt=1,
            cmap="magma_r",
        )
        duration_axis.plot(
            [snapshot_day, 60], [snapshot_day, 60], color="#444444", linestyle="--"
        )
        duration_axis.set_xlim(snapshot_day, 61)
        duration_axis.set_ylim(snapshot_day, 61)
        duration_axis.set_xlabel("Observed duration (days)")
        area_axis.grid(True, alpha=0.18)
        duration_axis.grid(True, alpha=0.18)
    axes[0, 0].set_ylabel("Predicted final area (km$^2$)")
    axes[1, 0].set_ylabel("Predicted duration (days)")
    for axis in axes[0, :]:
        axis.set_xlabel("Observed final area (km$^2$)")
    fig.suptitle(f"Grown-fire predictions made after event day {snapshot_day}")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output, dpi=220)
    plt.close(fig)


def plot_descriptors(outcomes: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.5))
    axes[0, 0].hexbin(
        outcomes["duration_days"],
        outcomes["final_area_km2"],
        yscale="log",
        gridsize=32,
        bins="log",
        mincnt=1,
        cmap="magma_r",
    )
    axes[0, 0].set(
        title="Final size and mapped duration",
        xlabel="Duration (days)",
        ylabel="Final area (km$^2$)",
    )
    bins = np.linspace(0, 1, 21)
    axes[0, 1].hist(
        outcomes["half_area_timing"], bins=bins, alpha=0.72, label="50% of final area"
    )
    axes[0, 1].hist(
        outcomes["ninety_area_timing"], bins=bins, alpha=0.65, label="90% of final area"
    )
    axes[0, 1].set(
        title="When mapped growth accumulates",
        xlabel="Fraction of event duration",
        ylabel="Events",
    )
    axes[0, 1].legend(frameon=False)
    axes[1, 0].hist(outcomes["peak_growth_timing"], bins=bins, color="#D55E00", alpha=0.8)
    axes[1, 0].set(
        title="Timing of peak daily growth",
        xlabel="Fraction of event duration",
        ylabel="Events",
    )
    axes[1, 1].hexbin(
        outcomes["final_area_km2"],
        outcomes["growth_burstiness"],
        xscale="log",
        gridsize=32,
        bins="log",
        mincnt=1,
        cmap="magma_r",
    )
    axes[1, 1].set(
        title="Peak-to-mean active growth",
        xlabel="Final area (km$^2$)",
        ylabel="Growth burstiness",
    )
    for axis in axes.flat:
        axis.grid(True, alpha=0.18)
    fig.suptitle("Descriptions of fully grown held-out FIRED events, 2016-2020")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output, dpi=220)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sequences",
        type=Path,
        default=Path("outputs/fired_prediction/fired_sequences.csv.gz"),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("outputs/fired_outcome_validation")
    )
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260927)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.sequences.exists():
        raise FileNotFoundError(
            f"{args.sequences} does not exist; run scripts/run_fired_prediction_tests.py first"
        )
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    sequences = pd.read_csv(args.sequences, parse_dates=["date"])
    development = sequences[sequences["ig_year"] <= 2012].copy()
    calibration = sequences[sequences["ig_year"].between(2013, 2015)].copy()
    testing = sequences[sequences["ig_year"] >= 2016].copy()

    calibration_parts = []
    test_parts = []
    parameters = []
    for snapshot_day in (3, 5, 7):
        cal, test, fitted = fit_snapshot_models(
            development,
            calibration,
            testing,
            snapshot_day,
            alpha=args.ridge_alpha,
        )
        calibration_parts.append(cal)
        test_parts.append(test)
        parameters.append(fitted)
    calibration_predictions = pd.concat(calibration_parts, ignore_index=True)
    test_predictions = pd.concat(test_parts, ignore_index=True)
    intervals = calibrate_intervals(calibration_predictions)
    test_predictions = apply_intervals(test_predictions, intervals)
    summary = summarize_validation(
        test_predictions,
        bootstrap_replicates=args.bootstrap_replicates,
        seed=args.seed,
    )

    outcomes = describe_fire_outcomes(sequences, snapshot_days=(3, 5, 7))
    held_out_outcomes = outcomes[outcomes["ig_year"] >= 2016].copy()
    descriptive_summary = describe_groups(held_out_outcomes)

    outcomes.to_csv(output / "grown_fire_event_statistics.csv.gz", index=False, compression="gzip")
    descriptive_summary.to_csv(output / "grown_fire_descriptive_summary.csv", index=False)
    test_predictions.to_csv(
        output / "held_out_outcome_predictions.csv.gz", index=False, compression="gzip"
    )
    summary.to_csv(output / "outcome_validation_summary.csv", index=False)
    intervals.to_csv(output / "calibrated_intervals.csv", index=False)
    plot_performance(summary, output / "outcome_prediction_performance.png")
    plot_observed_predicted(test_predictions, output / "observed_vs_predicted_day5.png")
    plot_descriptors(held_out_outcomes, output / "grown_fire_descriptive_statistics.png")

    day5 = summary[summary["snapshot_day"] == 5].set_index("model")
    report = {
        "design": {
            "development_years": [2001, 2012],
            "interval_calibration_years": [2013, 2015],
            "held_out_test_years": [2016, 2020],
            "snapshot_days": [3, 5, 7],
            "nominal_interval_coverage": 0.9,
            "ridge_alpha": args.ridge_alpha,
            "feature_columns": list(EARLY_FEATURE_COLUMNS),
            "target_area_transform": "log(final area)",
            "target_duration_transform": "log1p(remaining days)",
        },
        "counts": {
            "development_events": int(development["id"].nunique()),
            "calibration_events": int(calibration["id"].nunique()),
            "held_out_test_events": int(testing["id"].nunique()),
        },
        "day5_early_trajectory": {
            "mean_absolute_log_area_error": float(
                day5.loc["early_trajectory", "mean_absolute_log_area_error"]
            ),
            "typical_area_error_factor": float(
                day5.loc["early_trajectory", "typical_area_error_factor"]
            ),
            "log_area_r2": float(day5.loc["early_trajectory", "log_area_r2"]),
            "area_interval_coverage": float(
                day5.loc["early_trajectory", "area_interval_coverage"]
            ),
            "mean_absolute_duration_error_days": float(
                day5.loc["early_trajectory", "mean_absolute_duration_error_days"]
            ),
            "duration_r2": float(day5.loc["early_trajectory", "duration_r2"]),
            "duration_interval_coverage": float(
                day5.loc["early_trajectory", "duration_interval_coverage"]
            ),
        },
        "fitted_snapshot_parameters": parameters,
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "matplotlib": plt.matplotlib.__version__,
        },
        "limitations": [
            "This is retrospective prediction from MODIS-derived FIRED sequences, not an operational forecast.",
            "Event filters condition the analysis on fires lasting 8-60 days and reaching at least 10 square kilometers.",
            "Prediction intervals are calibrated on 2013-2015 events and evaluated once on 2016-2020 events.",
            "Missing FIRED observation dates are represented as zero detected growth.",
        ],
    }
    (output / "run_report.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "README.md").write_text(
        "# FIRED grown-fire outcome validation\n\n"
        "Predictions use only FIRED observations available through event day 3, 5, or 7. "
        "Models are developed on 2001-2012 events, 90% intervals are calibrated on "
        "2013-2015 events, and all reported validation scores use untouched 2016-2020 "
        "events. See `run_report.json` for the design and limitations.\n"
    )
    print(json.dumps(report["counts"], indent=2))
    print("\nHeld-out validation summary:")
    print(
        summary[
            [
                "snapshot_day",
                "model",
                "mean_absolute_log_area_error",
                "typical_area_error_factor",
                "mean_absolute_duration_error_days",
                "area_interval_coverage",
                "duration_interval_coverage",
            ]
        ].to_string(index=False)
    )
    print("\nHeld-out grown-fire summary:")
    print(descriptive_summary.head(1).to_string(index=False))


if __name__ == "__main__":
    main()
