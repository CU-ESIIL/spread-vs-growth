#!/usr/bin/env python3
"""Run the adversarial FIRED detection and prediction validation pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fire_metabolism.adversarial_validation import (
    ACTIVE_FRONT_PREDICTORS,
    AREA_GEOMETRY_PREDICTORS,
    AREA_PREDICTORS,
    DEFAULT_SEED,
    DYNAMICS_PREDICTORS,
    WEATHER_PREDICTORS,
    add_quadratic_features,
    attach_future_dynamics,
    binary_metrics,
    geometric_detection_table,
    paired_event_bootstrap,
    regression_metrics,
    synthetic_counterexamples,
    transformed_forecasts,
    tune_binary_model,
    tune_ridge_alpha,
)
from fire_metabolism.fired_lifecycle import merge_geometry_sequences, smooth_daily_growth


COLORS = {
    "persistence": "#777777",
    "recent_linear": "#202020",
    "half_power": "#B52A25",
    "two_thirds": "#6495ED",
    "free_sigma": "#2A8C5A",
    "area_ridge": "#D28B26",
    "dynamics_ridge": "#C46A1A",
    "flexible_dynamics": "#8A5AA5",
    "geometry_proxy": "#0B6E75",
    "geometry_indicator": "#43A6AC",
    "geometry_weather": "#B45A78",
}
MODEL_LABELS = {
    "persistence": "No growth",
    "recent_linear": "Recent growth",
    "half_power": r"$A^{1/2}$",
    "two_thirds": r"$A^{2/3}$",
    "free_sigma": "Free exponent",
    "area_ridge": "Area history",
    "dynamics_ridge": "Area + recent dynamics",
    "flexible_dynamics": "Flexible dynamics",
    "geometry_proxy": "Geometry proxy",
    "geometry_indicator": "Detected geometry",
    "geometry_weather": "Geometry + past weather",
}
DETECTION_FEATURES = (
    "exterior_detected",
    "persistent_detection",
    "variant_agreement",
)


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
        "--weather-features",
        type=Path,
        default=Path(
            "outputs/fired_missing_processes/snapshot_features_with_front_weather.csv.gz"
        ),
    )
    parser.add_argument(
        "--survival-summary",
        type=Path,
        default=Path("outputs/fired_state_survival/state_survival_summary.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/adversarial_validation"),
    )
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def partition(year: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [year <= 2012, year.between(2013, 2015), year >= 2016],
            ["development", "calibration", "held_out"],
            default="excluded",
        ),
        index=year.index,
    )


def deterministic_subset(frame: pd.DataFrame, events_per_partition: int = 80) -> pd.DataFrame:
    event_year = frame.groupby("id", as_index=False).ig_year.first()
    event_year["partition"] = partition(event_year.ig_year)
    ids: list[int] = []
    for _, group in event_year.groupby("partition", sort=False):
        ids.extend(group.sort_values("id").id.head(events_per_partition).tolist())
    return frame[frame.id.isin(ids)].copy()


def bootstrap_mean_ci(
    values: np.ndarray, *, replicates: int, seed: int
) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    generator = np.random.default_rng(seed)
    samples = generator.choice(values, size=(replicates, len(values)), replace=True)
    means = samples.mean(axis=1)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def conformal_radius(log_residual: np.ndarray, coverage: float = 0.9) -> float:
    values = np.sort(np.abs(np.asarray(log_residual, dtype=float)))
    rank = min(len(values) - 1, int(np.ceil((len(values) + 1) * coverage)) - 1)
    return float(values[rank])


def fit_regression_models(
    frame: pd.DataFrame,
    sequences: pd.DataFrame,
    *,
    snapshot: int,
    horizon: int,
    bootstrap_replicates: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = frame[(frame.snapshot_day == snapshot)].copy()
    data = attach_future_dynamics(data, sequences, horizon=horizon)
    data["partition"] = partition(data.ig_year)
    data["log_future_area"] = np.log(data.future_area_km2)
    development = data[data.partition == "development"].copy()
    calibration = data[data.partition == "calibration"].copy()
    held_out = data[data.partition == "held_out"].copy()
    if min(len(development), len(calibration), len(held_out)) < 10:
        raise ValueError("a temporal partition is too small for model comparison")

    prediction_rows: list[pd.DataFrame] = []
    tuning_rows: list[pd.DataFrame] = []

    def append_prediction(
        model_name: str,
        test_prediction: np.ndarray,
        calibration_prediction: np.ndarray,
        *,
        sigma: float | None = None,
    ) -> None:
        radius = conformal_radius(
            np.log(np.maximum(calibration_prediction, 1e-12))
            - np.log(calibration.future_area_km2.to_numpy(dtype=float))
        )
        part = held_out[
            ["id", "ig_year", "snapshot_day", "horizon_days", "origin_area_km2", "future_area_km2"]
        ].copy()
        part["model"] = model_name
        part["sigma"] = sigma
        part["predicted_area_km2"] = np.maximum(test_prediction, held_out.origin_area_km2)
        part["interval_lower"] = np.maximum(
            held_out.origin_area_km2,
            part.predicted_area_km2 * np.exp(-radius),
        )
        part["interval_upper"] = part.predicted_area_km2 * np.exp(radius)
        prediction_rows.append(part)

    for subset, label in ((calibration, "calibration"), (held_out, "held_out")):
        subset["horizon_days"] = horizon
    append_prediction(
        "persistence",
        held_out.origin_area_km2.to_numpy(dtype=float),
        calibration.origin_area_km2.to_numpy(dtype=float),
    )
    append_prediction(
        "recent_linear",
        held_out.origin_area_km2.to_numpy(dtype=float)
        + horizon * held_out.past_mean_growth.to_numpy(dtype=float),
        calibration.origin_area_km2.to_numpy(dtype=float)
        + horizon * calibration.past_mean_growth.to_numpy(dtype=float),
    )
    for model_name, sigma in (("half_power", 0.5), ("two_thirds", 2.0 / 3.0)):
        append_prediction(
            model_name,
            transformed_forecasts(held_out, sequences, sigma=sigma),
            transformed_forecasts(calibration, sequences, sigma=sigma),
            sigma=sigma,
        )

    sigma_rows = []
    sigma_predictions: dict[float, tuple[np.ndarray, np.ndarray]] = {}
    for sigma in np.linspace(0.0, 0.9, 10):
        calibration_prediction = transformed_forecasts(calibration, sequences, sigma=float(sigma))
        score = np.mean(
            np.abs(
                np.log(
                    np.maximum(calibration_prediction, 1e-12)
                    / calibration.future_area_km2.to_numpy(dtype=float)
                )
            )
        )
        sigma_rows.append({"sigma": float(sigma), "calibration_absolute_log_error": score})
        sigma_predictions[float(sigma)] = (
            calibration_prediction,
            transformed_forecasts(held_out, sequences, sigma=float(sigma)),
        )
    sigma_curve = pd.DataFrame(sigma_rows)
    selected_sigma = float(
        sigma_curve.loc[sigma_curve.calibration_absolute_log_error.idxmin(), "sigma"]
    )
    sigma_curve["selected"] = sigma_curve.sigma == selected_sigma
    sigma_curve["snapshot_day"] = snapshot
    sigma_curve["horizon_days"] = horizon
    sigma_curve["model"] = "free_sigma"
    tuning_rows.append(sigma_curve)
    calibration_prediction, test_prediction = sigma_predictions[selected_sigma]
    append_prediction(
        "free_sigma",
        test_prediction,
        calibration_prediction,
        sigma=selected_sigma,
    )

    regression_specs: list[tuple[str, tuple[str, ...], pd.DataFrame]] = [
        ("area_ridge", AREA_PREDICTORS, data),
        ("dynamics_ridge", DYNAMICS_PREDICTORS, data),
        ("geometry_proxy", AREA_GEOMETRY_PREDICTORS, data),
        (
            "geometry_indicator",
            DYNAMICS_PREDICTORS + DETECTION_FEATURES,
            data,
        ),
    ]
    nonlinear_data, nonlinear_columns = add_quadratic_features(data, DYNAMICS_PREDICTORS)
    regression_specs.append(("flexible_dynamics", nonlinear_columns, nonlinear_data))
    weather_columns = AREA_GEOMETRY_PREDICTORS + ACTIVE_FRONT_PREDICTORS + WEATHER_PREDICTORS
    if snapshot == 7 and set(weather_columns).issubset(data.columns):
        regression_specs.append(("geometry_weather", weather_columns, data))

    for model_name, columns, source in regression_specs:
        source_development = source[source.partition == "development"]
        source_calibration = source[source.partition == "calibration"]
        source_test = source[source.partition == "held_out"]
        model, curve = tune_ridge_alpha(
            source_development,
            source_calibration,
            target_column="log_future_area",
            feature_columns=columns,
        )
        curve["snapshot_day"] = snapshot
        curve["horizon_days"] = horizon
        curve["model"] = model_name
        tuning_rows.append(curve)
        append_prediction(
            model_name,
            np.exp(model.predict(source_test)),
            np.exp(model.predict(source_calibration)),
        )

    predictions = pd.concat(prediction_rows, ignore_index=True)
    predictions["error"] = predictions.predicted_area_km2 - predictions.future_area_km2
    predictions["absolute_error"] = np.abs(predictions.error)
    predictions["absolute_log_error"] = np.abs(
        np.log(predictions.predicted_area_km2 / predictions.future_area_km2)
    )
    predictions["covered"] = (
        (predictions.future_area_km2 >= predictions.interval_lower)
        & (predictions.future_area_km2 <= predictions.interval_upper)
    )

    metric_rows = []
    for model_name, group in predictions.groupby("model", sort=False):
        metrics = regression_metrics(group.future_area_km2, group.predicted_area_km2)
        lower, upper = bootstrap_mean_ci(
            group.absolute_log_error.to_numpy(dtype=float),
            replicates=bootstrap_replicates,
            seed=DEFAULT_SEED + snapshot * 100 + horizon,
        )
        metric_rows.append(
            {
                "snapshot_day": snapshot,
                "horizon_days": horizon,
                "model": model_name,
                **metrics,
                "absolute_log_error_ci95_lower": lower,
                "absolute_log_error_ci95_upper": upper,
                "interval_coverage": float(group.covered.mean()),
                "median_interval_width_factor": float(
                    np.median(group.interval_upper / group.interval_lower)
                ),
            }
        )
    metrics = pd.DataFrame(metric_rows)

    pivot = predictions.pivot(
        index="id", columns="model", values="absolute_log_error"
    ).reset_index()
    comparisons = []
    for first, second in (
        ("geometry_proxy", "dynamics_ridge"),
        ("geometry_proxy", "flexible_dynamics"),
        ("geometry_indicator", "dynamics_ridge"),
        ("geometry_weather", "geometry_proxy"),
        ("two_thirds", "half_power"),
        ("two_thirds", "recent_linear"),
    ):
        if {first, second}.issubset(pivot.columns):
            comparison = paired_event_bootstrap(
                pivot,
                first_error=first,
                second_error=second,
                replicates=bootstrap_replicates,
                seed=DEFAULT_SEED + snapshot * 1000 + horizon,
            )
            comparisons.append(
                {
                    "snapshot_day": snapshot,
                    "horizon_days": horizon,
                    "first_model": first,
                    "second_model": second,
                    **comparison,
                }
            )
    return predictions, metrics, pd.DataFrame(comparisons), pd.concat(tuning_rows, ignore_index=True)


def acceleration_models(
    frame: pd.DataFrame,
    sequences: pd.DataFrame,
    *,
    snapshot: int,
    horizon: int,
    bootstrap_replicates: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = attach_future_dynamics(
        frame[frame.snapshot_day == snapshot].copy(), sequences, horizon=horizon
    )
    data["partition"] = partition(data.ig_year)
    development = data[data.partition == "development"].copy()
    calibration = data[data.partition == "calibration"].copy()
    held_out = data[data.partition == "held_out"].copy()
    predictions = []
    tuning = []

    persistence_probability = held_out.recent_growth_acceleration.to_numpy(dtype=float)
    persistence_probability = 1 / (1 + np.exp(-persistence_probability))
    predictions.append(
        pd.DataFrame(
            {
                "id": held_out.id,
                "snapshot_day": snapshot,
                "horizon_days": horizon,
                "target": "future_accelerating",
                "model": "acceleration_persistence",
                "observed": held_out.future_accelerating.astype(bool),
                "probability": persistence_probability,
                "predicted": persistence_probability >= 0.5,
            }
        )
    )
    for model_name, columns in (
        ("area_ridge", AREA_PREDICTORS),
        ("dynamics_ridge", DYNAMICS_PREDICTORS),
        ("geometry_proxy", AREA_GEOMETRY_PREDICTORS),
        ("geometry_indicator", DYNAMICS_PREDICTORS + DETECTION_FEATURES),
    ):
        model, threshold, curve = tune_binary_model(
            development,
            calibration,
            target_column="future_accelerating",
            feature_columns=columns,
        )
        probability = model.predict_hazard(held_out)
        predictions.append(
            pd.DataFrame(
                {
                    "id": held_out.id,
                    "snapshot_day": snapshot,
                    "horizon_days": horizon,
                    "target": "future_accelerating",
                    "model": model_name,
                    "observed": held_out.future_accelerating.astype(bool),
                    "probability": probability,
                    "predicted": probability >= threshold,
                }
            )
        )
        curve["snapshot_day"] = snapshot
        curve["horizon_days"] = horizon
        curve["target"] = "future_accelerating"
        curve["model"] = model_name
        tuning.append(curve)

    weather_columns = AREA_GEOMETRY_PREDICTORS + ACTIVE_FRONT_PREDICTORS + WEATHER_PREDICTORS
    if snapshot == 7 and set(weather_columns).issubset(data.columns):
        model, threshold, curve = tune_binary_model(
            development,
            calibration,
            target_column="future_accelerating",
            feature_columns=weather_columns,
        )
        probability = model.predict_hazard(held_out)
        predictions.append(
            pd.DataFrame(
                {
                    "id": held_out.id,
                    "snapshot_day": snapshot,
                    "horizon_days": horizon,
                    "target": "future_accelerating",
                    "model": "geometry_weather",
                    "observed": held_out.future_accelerating.astype(bool),
                    "probability": probability,
                    "predicted": probability >= threshold,
                }
            )
        )
        curve["snapshot_day"] = snapshot
        curve["horizon_days"] = horizon
        curve["target"] = "future_accelerating"
        curve["model"] = "geometry_weather"
        tuning.append(curve)

    prediction = pd.concat(predictions, ignore_index=True)
    metric_rows = []
    for model_name, group in prediction.groupby("model", sort=False):
        values = binary_metrics(group.observed, group.predicted)
        values["brier_score"] = float(
            np.mean((group.probability.to_numpy() - group.observed.to_numpy()) ** 2)
        )
        generator = np.random.default_rng(DEFAULT_SEED + snapshot + horizon)
        event_ids = group.id.to_numpy()
        draws = []
        for _ in range(bootstrap_replicates):
            indices = generator.integers(0, len(event_ids), len(event_ids))
            sampled = group.iloc[indices]
            draws.append(binary_metrics(sampled.observed, sampled.predicted)["balanced_accuracy"])
        metric_rows.append(
            {
                "snapshot_day": snapshot,
                "horizon_days": horizon,
                "target": "future_accelerating",
                "model": model_name,
                "n_events": int(len(group)),
                **values,
                "balanced_accuracy_ci95_lower": float(np.nanquantile(draws, 0.025)),
                "balanced_accuracy_ci95_upper": float(np.nanquantile(draws, 0.975)),
            }
        )
    return prediction, pd.DataFrame(metric_rows), pd.concat(tuning, ignore_index=True)


def sign_change_peak_days(sequences: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for event_id, event in sequences.groupby("id", sort=False):
        event = event.sort_values("event_day")
        daily = event.daily_area_km2.to_numpy(dtype=float)
        if len(daily) < 5:
            continue
        smooth = smooth_daily_growth(daily, window=3)
        change = np.diff(smooth)
        crossing = np.where((change[:-1] > 0) & (change[1:] <= 0))[0] + 1
        peak_day = int(event.event_day.iloc[crossing[0]]) if len(crossing) else np.nan
        rows.append(
            {
                "id": int(event_id),
                "sign_change_peak_day": peak_day,
                "has_sign_change_peak": bool(len(crossing)),
            }
        )
    return pd.DataFrame(rows)


def peak_transition_models(
    frame: pd.DataFrame,
    peak_days: pd.DataFrame,
    *,
    snapshot: int,
    lead_window: int,
    bootstrap_replicates: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = frame[frame.snapshot_day == snapshot].merge(
        peak_days, on="id", how="left", validate="one_to_one"
    )
    data["peak_in_window"] = (
        data.sign_change_peak_day.gt(snapshot)
        & data.sign_change_peak_day.le(snapshot + lead_window)
    )
    data["partition"] = partition(data.ig_year)
    development = data[data.partition == "development"]
    calibration = data[data.partition == "calibration"]
    held_out = data[data.partition == "held_out"]
    predictions = []
    tuning = []
    for model_name, columns in (
        ("area_ridge", AREA_PREDICTORS),
        ("dynamics_ridge", DYNAMICS_PREDICTORS),
        ("geometry_proxy", AREA_GEOMETRY_PREDICTORS),
        ("geometry_indicator", DYNAMICS_PREDICTORS + DETECTION_FEATURES),
    ):
        model, threshold, curve = tune_binary_model(
            development,
            calibration,
            target_column="peak_in_window",
            feature_columns=columns,
        )
        probability = model.predict_hazard(held_out)
        predictions.append(
            pd.DataFrame(
                {
                    "id": held_out.id,
                    "snapshot_day": snapshot,
                    "horizon_days": lead_window,
                    "target": "peak_in_window",
                    "model": model_name,
                    "observed": held_out.peak_in_window,
                    "probability": probability,
                    "predicted": probability >= threshold,
                }
            )
        )
        curve["snapshot_day"] = snapshot
        curve["horizon_days"] = lead_window
        curve["target"] = "peak_in_window"
        curve["model"] = model_name
        tuning.append(curve)
    prediction = pd.concat(predictions, ignore_index=True)
    metric_rows = []
    for model_name, group in prediction.groupby("model", sort=False):
        scores = binary_metrics(group.observed, group.predicted)
        scores["brier_score"] = float(
            np.mean((group.probability - group.observed.astype(float)) ** 2)
        )
        generator = np.random.default_rng(DEFAULT_SEED + snapshot + lead_window)
        draws = []
        for _ in range(bootstrap_replicates):
            indices = generator.integers(0, len(group), len(group))
            sampled = group.iloc[indices]
            draws.append(binary_metrics(sampled.observed, sampled.predicted)["balanced_accuracy"])
        metric_rows.append(
            {
                "snapshot_day": snapshot,
                "horizon_days": lead_window,
                "target": "peak_in_window",
                "model": model_name,
                "n_events": int(len(group)),
                **scores,
                "balanced_accuracy_ci95_lower": float(np.nanquantile(draws, 0.025)),
                "balanced_accuracy_ci95_upper": float(np.nanquantile(draws, 0.975)),
            }
        )
    return prediction, pd.DataFrame(metric_rows), pd.concat(tuning, ignore_index=True)


def save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(
            output_dir / f"{stem}.{suffix}",
            dpi=320 if suffix == "png" else None,
            bbox_inches="tight",
        )
    plt.close(fig)


def figure_detection(
    merged: pd.DataFrame, detection: pd.DataFrame, output_dir: Path
) -> None:
    held = detection[(detection.ig_year >= 2016) & (detection.snapshot_day == 10)]
    selected = pd.concat(
        [
            held[held.exterior_detected].sort_values("exterior_rmse").head(3),
            held[~held.exterior_detected].sort_values("exterior_rmse").head(3),
        ]
    )
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), sharex=True, sharey=True)
    for axis, row in zip(axes.flat, selected.itertuples(index=False), strict=False):
        event = merged[(merged.id == row.id) & (merged.event_day <= 10) & (merged.daily_area_km2 > 0)]
        axis.plot(
            event.cumulative_area_km2,
            event.exterior_perimeter_km,
            "o-",
            color="#173F5F" if row.exterior_detected else "#B94B45",
            linewidth=1.5,
            markersize=4,
        )
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_title(
            f"Event {row.id}: slope {row.exterior_slope:.2f}\n"
            + ("geometric indicator" if row.exterior_detected else "indicator absent"),
            fontsize=9,
        )
        axis.grid(alpha=0.2)
    fig.supxlabel("Cumulative mapped area (km$^2$)")
    fig.supylabel("Exterior mapped perimeter (km)")
    fig.suptitle("Held-out geometric trajectories: accepted and rejected examples")
    save_figure(fig, output_dir, "figure1_detection")


def figure_robustness(robustness: pd.DataFrame, output_dir: Path) -> None:
    held = robustness[robustness.partition == "held_out"]
    pivot = held.pivot(index="variant", columns="snapshot_day", values="detection_rate")
    fig, axis = plt.subplots(figsize=(8, 3.8))
    image = axis.imshow(pivot.to_numpy(), vmin=0, vmax=1, cmap="viridis", aspect="auto")
    axis.set_xticks(range(len(pivot.columns)), pivot.columns)
    axis.set_yticks(range(len(pivot.index)), [value.replace("_", " ") for value in pivot.index])
    axis.set_xlabel("Snapshot day")
    axis.set_title("Held-out detector sensitivity to observation rule")
    for row in range(len(pivot.index)):
        for column in range(len(pivot.columns)):
            value = pivot.iloc[row, column]
            axis.text(column, row, f"{value:.2f}", ha="center", va="center", color="white" if value < 0.55 else "black")
    fig.colorbar(image, ax=axis, label="Detection fraction")
    save_figure(fig, output_dir, "figure2_detection_robustness")


def figure_predictions(
    sequences: pd.DataFrame,
    predictions: pd.DataFrame,
    output_dir: Path,
) -> None:
    target = predictions[
        (predictions.snapshot_day == 7)
        & (predictions.horizon_days == 7)
        & predictions.model.isin(["dynamics_ridge", "geometry_proxy"])
    ]
    pivot = target.pivot(index="id", columns="model", values=["predicted_area_km2", "future_area_km2"])
    pivot["gain"] = (
        np.abs(np.log(pivot[("predicted_area_km2", "dynamics_ridge")] / pivot[("future_area_km2", "dynamics_ridge")]))
        - np.abs(np.log(pivot[("predicted_area_km2", "geometry_proxy")] / pivot[("future_area_km2", "geometry_proxy")]))
    )
    event_ids = [int(pivot.gain.idxmax()), int(pivot.gain.idxmin())]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for axis, event_id, title in zip(axes, event_ids, ("Geometry helps", "Geometry fails"), strict=True):
        event = sequences[sequences.id == event_id].sort_values("event_day")
        axis.plot(event.event_day, event.cumulative_area_km2, color="#202020", linewidth=2, label="Observed")
        event_predictions = target[target.id == event_id]
        for row in event_predictions.itertuples(index=False):
            axis.plot(
                [7, 14],
                [row.origin_area_km2, row.predicted_area_km2],
                marker="o",
                color=COLORS[row.model],
                linewidth=2,
                label=MODEL_LABELS[row.model],
            )
        axis.axvline(7, color="#999999", linestyle="--", linewidth=1)
        axis.set_yscale("log")
        axis.set_xlabel("Event day")
        axis.set_ylabel("Cumulative mapped area (km$^2$)")
        axis.set_title(f"{title}: held-out event {event_id}")
        axis.legend(frameon=False)
        axis.grid(alpha=0.2)
    fig.suptitle("Representative held-out forecasts include successes and failures")
    save_figure(fig, output_dir, "figure3_prediction")


def figure_lifecycle(
    transition_metrics: pd.DataFrame,
    survival_summary: pd.DataFrame,
    output_dir: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    held = transition_metrics[transition_metrics.snapshot_day == 7]
    shared_models = [
        "area_ridge",
        "dynamics_ridge",
        "geometry_proxy",
        "geometry_indicator",
    ]
    positions = np.arange(len(shared_models), dtype=float)
    width = 0.36
    for offset, target, label, color in (
        (-width / 2, "future_accelerating", "Acceleration sign", "#4C78A8"),
        (width / 2, "peak_in_window", "Peak in next 3 days", "#D17C2F"),
    ):
        rows = held[held.target == target].set_index("model").reindex(shared_models)
        values = rows.balanced_accuracy.to_numpy(dtype=float)
        lower = values - rows.balanced_accuracy_ci95_lower.to_numpy(dtype=float)
        upper = rows.balanced_accuracy_ci95_upper.to_numpy(dtype=float) - values
        axes[0].bar(positions + offset, values, width=width, color=color, label=label)
        axes[0].errorbar(
            positions + offset,
            values,
            yerr=[lower, upper],
            fmt="none",
            color="black",
            capsize=3,
            linewidth=1,
        )
    axes[0].axhline(0.5, color="#B52A25", linestyle="--")
    axes[0].set_xticks(
        positions,
        [MODEL_LABELS[model] for model in shared_models],
        rotation=20,
        ha="right",
        fontsize=8,
    )
    axes[0].set_ylim(0, 1)
    axes[0].set_ylabel("Balanced accuracy")
    axes[0].set_title("Prospective transition prediction")
    axes[0].legend(frameon=False, fontsize=8)

    death = survival_summary[
        (survival_summary.evaluation_group == "all_at_risk")
        & survival_summary.snapshot_day.isin([5, 7, 10, 14, 21])
        & survival_summary.model.isin(["historical_median", "geometry_metabolic_ridge", "geometry_state_hazard"])
    ]
    for model, group in death.groupby("model"):
        axes[1].plot(group.snapshot_day, group.mean_absolute_error, marker="o", label=model.replace("_", " "))
    axes[1].set_xlabel("Forecast snapshot day")
    axes[1].set_ylabel("Death-day MAE (days)")
    axes[1].set_title("Termination improves only with later updates")
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].grid(alpha=0.2)
    fig.suptitle("Held-out life-cycle and termination validation")
    save_figure(fig, output_dir, "figure4_lifecycle_transitions")


def figure_discrimination(metrics: pd.DataFrame, output_dir: Path) -> None:
    data = metrics[metrics.snapshot_day == 7].copy()
    models = [
        "persistence",
        "recent_linear",
        "half_power",
        "two_thirds",
        "free_sigma",
        "area_ridge",
        "dynamics_ridge",
        "flexible_dynamics",
        "geometry_proxy",
        "geometry_indicator",
    ]
    fig, axis = plt.subplots(figsize=(10, 5.5))
    offsets = np.linspace(-0.32, 0.32, len(models))
    horizons = sorted(data.horizon_days.unique())
    for offset, model in zip(offsets, models, strict=True):
        group = data[data.model == model].set_index("horizon_days").reindex(horizons)
        axis.errorbar(
            np.asarray(horizons) + offset,
            group.mean_absolute_log_error,
            yerr=[
                group.mean_absolute_log_error - group.absolute_log_error_ci95_lower,
                group.absolute_log_error_ci95_upper - group.mean_absolute_log_error,
            ],
            marker="o",
            linestyle="none",
            color=COLORS[model],
            label=MODEL_LABELS[model],
            capsize=2,
        )
    axis.set_xticks(horizons)
    axis.set_xlabel("Forecast horizon (days after day 7)")
    axis.set_ylabel("Mean absolute log area error")
    axis.set_title("Paired held-out model discrimination")
    axis.grid(alpha=0.2, axis="y")
    axis.legend(frameon=False, ncol=3, fontsize=8)
    save_figure(fig, output_dir, "figure5_model_discrimination")


def figure_failure_map(
    features: pd.DataFrame,
    predictions: pd.DataFrame,
    output_dir: Path,
) -> None:
    target = predictions[
        (predictions.snapshot_day == 7)
        & (predictions.horizon_days == 7)
        & predictions.model.isin(["dynamics_ridge", "geometry_proxy"])
    ]
    pivot = target.pivot(index="id", columns="model", values="absolute_log_error")
    pivot["geometry_gain"] = pivot.dynamics_ridge - pivot.geometry_proxy
    state = features[features.snapshot_day == 7].set_index("id").join(pivot[["geometry_gain"]], how="inner")
    fig, axis = plt.subplots(figsize=(8, 5.5))
    scatter = axis.scatter(
        state.snapshot_area_km2,
        np.exp(state.log_component_count),
        c=state.geometry_gain,
        s=18 + 55 * state.variant_agreement,
        cmap="RdBu",
        vmin=-np.nanquantile(np.abs(state.geometry_gain), 0.95),
        vmax=np.nanquantile(np.abs(state.geometry_gain), 0.95),
        alpha=0.7,
    )
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("Mapped area at day 7 (km$^2$)")
    axis.set_ylabel("Mapped component count")
    axis.set_title("Where geometry helps, fails, or is observation-sensitive")
    colorbar = fig.colorbar(scatter, ax=axis)
    colorbar.set_label("Area-model error minus geometry-model error")
    axis.text(
        0.02,
        0.02,
        "Point size: detector agreement across observation rules\nRed: geometry worse; blue: geometry better",
        transform=axis.transAxes,
        fontsize=8,
        va="bottom",
    )
    save_figure(fig, output_dir, "figure6_theory_failure_map")


def make_subgroup_robustness(
    features: pd.DataFrame,
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize detector stability and geometry gain across prespecified strata."""
    day7 = features[features.snapshot_day == 7].copy()
    development = day7[day7.ig_year <= 2012].copy()
    target = predictions[
        (predictions.snapshot_day == 7)
        & (predictions.horizon_days == 7)
        & predictions.model.isin(["dynamics_ridge", "geometry_proxy"])
    ]
    errors = target.pivot(index="id", columns="model", values="absolute_log_error")
    errors["geometry_gain"] = errors.dynamics_ridge - errors.geometry_proxy
    day7 = day7.merge(errors[["geometry_gain"]], on="id", how="inner", validate="one_to_one")

    def thirds(values: pd.Series) -> tuple[float, float]:
        return tuple(np.quantile(values, [1 / 3, 2 / 3]))

    size_low, size_high = thirds(development.final_area_km2)
    duration_low, duration_high = thirds(development.death_day)
    vpd_low, vpd_high = thirds(development.recent_vpd_kpa)
    day7["final_size_group"] = pd.cut(
        day7.final_area_km2,
        [-np.inf, size_low, size_high, np.inf],
        labels=["small", "medium", "large"],
    ).astype(str)
    day7["duration_group"] = pd.cut(
        day7.death_day,
        [-np.inf, duration_low, duration_high, np.inf],
        labels=["short", "medium", "long"],
    ).astype(str)
    day7["weather_group"] = pd.cut(
        day7.recent_vpd_kpa,
        [-np.inf, vpd_low, vpd_high, np.inf],
        labels=["low_vpd", "medium_vpd", "high_vpd"],
    ).astype(str)
    day7["fragmentation_group"] = np.where(
        np.exp(day7.log_component_count) > 1.5, "fragmented", "single_component"
    )
    day7["hole_group"] = np.where(day7.log1p_hole_count > 0, "holes", "no_holes")
    held = day7[day7.ig_year >= 2016]
    rows = []
    specifications = (
        ("final_size", "final_size_group", "retrospective outcome stratum"),
        ("duration", "duration_group", "retrospective outcome stratum"),
        (
            "weather",
            "weather_group",
            "past weather at future-footprint centroid; sensitivity only",
        ),
        ("fragmentation", "fragmentation_group", "origin available"),
        ("holes", "hole_group", "origin available"),
        ("ecosystem", "lc_name", "future-derived dominant class; retrospective only"),
    )
    for variable, column, status in specifications:
        for level, group in held.groupby(column, observed=True):
            if len(group) < 10:
                continue
            lower, upper = bootstrap_mean_ci(
                group.geometry_gain.to_numpy(dtype=float),
                replicates=2000,
                seed=DEFAULT_SEED + len(rows),
            )
            rows.append(
                {
                    "stratification": variable,
                    "level": str(level),
                    "conditioning_status": status,
                    "n_events": int(len(group)),
                    "geometric_detection_fraction": float(group.exterior_detected.mean()),
                    "persistent_detection_fraction": float(group.persistent_detection.mean()),
                    "mean_variant_agreement": float(group.variant_agreement.mean()),
                    "mean_geometry_error_reduction": float(group.geometry_gain.mean()),
                    "geometry_error_reduction_ci95_lower": lower,
                    "geometry_error_reduction_ci95_upper": upper,
                }
            )
    return pd.DataFrame(rows)


def probability_calibration_table(predictions: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fixed-width reliability bins for held-out event probabilities."""
    frame = predictions.copy()
    frame["probability_bin"] = pd.cut(
        frame.probability,
        np.linspace(0, 1, 6),
        include_lowest=True,
    ).astype(str)
    return (
        frame.groupby(
            ["snapshot_day", "horizon_days", "target", "model", "probability_bin"],
            observed=True,
            as_index=False,
        )
        .agg(
            n_events=("id", "nunique"),
            mean_predicted_probability=("probability", "mean"),
            observed_frequency=("observed", "mean"),
        )
    )


def paired_transition_comparisons(
    predictions: pd.DataFrame,
    *,
    replicates: int,
) -> pd.DataFrame:
    """Compare balanced accuracy on paired held-out events."""
    rows = []
    pairs = (
        ("geometry_proxy", "dynamics_ridge"),
        ("geometry_indicator", "dynamics_ridge"),
        ("geometry_weather", "geometry_proxy"),
    )
    grouping = ["snapshot_day", "horizon_days", "target"]
    for keys, group in predictions.groupby(grouping, sort=False):
        snapshot, horizon, target = keys
        for first, second in pairs:
            first_rows = group[group.model == first].set_index("id")
            second_rows = group[group.model == second].set_index("id")
            common = first_rows.index.intersection(second_rows.index)
            if len(common) < 10:
                continue
            truth = first_rows.loc[common, "observed"].to_numpy(dtype=bool)
            first_prediction = first_rows.loc[common, "predicted"].to_numpy(dtype=bool)
            second_prediction = second_rows.loc[common, "predicted"].to_numpy(dtype=bool)
            observed_difference = (
                binary_metrics(truth, first_prediction)["balanced_accuracy"]
                - binary_metrics(truth, second_prediction)["balanced_accuracy"]
            )
            generator = np.random.default_rng(
                DEFAULT_SEED + int(snapshot) * 100 + int(horizon) + len(rows)
            )
            differences = []
            for _ in range(replicates):
                index = generator.integers(0, len(common), len(common))
                differences.append(
                    binary_metrics(truth[index], first_prediction[index])[
                        "balanced_accuracy"
                    ]
                    - binary_metrics(truth[index], second_prediction[index])[
                        "balanced_accuracy"
                    ]
                )
            rows.append(
                {
                    "snapshot_day": int(snapshot),
                    "horizon_days": int(horizon),
                    "target": target,
                    "first_model": first,
                    "second_model": second,
                    "n_events": int(len(common)),
                    "balanced_accuracy_difference": float(observed_difference),
                    "ci95_lower": float(np.nanquantile(differences, 0.025)),
                    "ci95_upper": float(np.nanquantile(differences, 0.975)),
                    "probability_first_better": float(
                        np.nanmean(np.asarray(differences) > 0)
                    ),
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    input_paths = [args.sequences, args.geometry, args.features, args.weather_features, args.survival_summary]
    for path in input_paths:
        if not path.exists():
            raise FileNotFoundError(path)

    sequences = pd.read_csv(args.sequences, parse_dates=["date"])
    geometry = pd.read_csv(args.geometry)
    features = pd.read_csv(args.features)
    weather = pd.read_csv(args.weather_features)
    survival_summary = pd.read_csv(args.survival_summary)
    if args.smoke:
        sequences = deterministic_subset(sequences)
        ids = set(sequences.id.unique())
        geometry = geometry[geometry.id.isin(ids)]
        features = features[features.id.isin(ids)]
        weather = weather[weather.id.isin(ids)]

    merged = merge_geometry_sequences(sequences, geometry)
    detection = geometric_detection_table(merged)
    detection["partition"] = partition(detection.ig_year)
    detection.to_csv(output_dir / "detection_windows.csv.gz", index=False)

    robustness_rows = []
    for (part, snapshot), group in detection.groupby(["partition", "snapshot_day"]):
        for variant in ("exterior", "total", "thinned"):
            robustness_rows.append(
                {
                    "partition": part,
                    "snapshot_day": int(snapshot),
                    "variant": variant,
                    "n_events": int(len(group)),
                    "detection_rate": float(group[f"{variant}_detected"].mean()),
                    "median_slope": float(group[f"{variant}_slope"].median()),
                }
            )
    robustness = pd.DataFrame(robustness_rows)
    robustness.to_csv(output_dir / "detection_robustness.csv", index=False)

    detection_summary = (
        detection.groupby(["partition", "snapshot_day"], as_index=False)
        .agg(
            n_events=("id", "nunique"),
            median_exterior_slope=("exterior_slope", "median"),
            geometric_detection_fraction=("exterior_detected", "mean"),
            persistent_detection_fraction=("persistent_detection", "mean"),
            mean_variant_agreement=("variant_agreement", "mean"),
            median_components=("component_count", "median"),
            median_holes=("hole_count", "median"),
        )
    )
    detection_summary.to_csv(output_dir / "detection_summary.csv", index=False)

    detection_for_merge = detection[
        ["id", "snapshot_day", *DETECTION_FEATURES, "exterior_slope", "exterior_slope_se"]
    ]
    model_features = features.merge(
        detection_for_merge,
        on=["id", "snapshot_day"],
        how="inner",
        validate="one_to_one",
    )
    for column in DETECTION_FEATURES:
        model_features[column] = model_features[column].astype(float)
    weather_columns = ["id", "snapshot_day", *ACTIVE_FRONT_PREDICTORS, *WEATHER_PREDICTORS]
    model_features = model_features.merge(
        weather.loc[:, weather_columns],
        on=["id", "snapshot_day"],
        how="left",
        validate="one_to_one",
    )

    bootstrap_replicates = 150 if args.smoke else 2000
    forecast_parts = []
    forecast_metrics = []
    comparisons = []
    forecast_tuning = []
    for snapshot in (5, 7):
        for horizon in (1, 3, 5, 7):
            result = fit_regression_models(
                model_features,
                sequences,
                snapshot=snapshot,
                horizon=horizon,
                bootstrap_replicates=bootstrap_replicates,
            )
            prediction, metrics, comparison, tuning = result
            forecast_parts.append(prediction)
            forecast_metrics.append(metrics)
            comparisons.append(comparison)
            forecast_tuning.append(tuning)
    forecast_predictions = pd.concat(forecast_parts, ignore_index=True)
    forecast_metric_frame = pd.concat(forecast_metrics, ignore_index=True)
    comparison_frame = pd.concat(comparisons, ignore_index=True)
    forecast_tuning_frame = pd.concat(forecast_tuning, ignore_index=True)
    forecast_predictions.to_csv(output_dir / "held_out_forecast_predictions.csv.gz", index=False)
    forecast_metric_frame.to_csv(output_dir / "forecast_metrics.csv", index=False)
    comparison_frame.to_csv(output_dir / "paired_model_comparisons.csv", index=False)
    forecast_tuning_frame.to_csv(output_dir / "model_tuning.csv", index=False)

    transition_predictions = []
    transition_metrics = []
    transition_tuning = []
    for snapshot in (5, 7):
        prediction, metrics, tuning = acceleration_models(
            model_features,
            sequences,
            snapshot=snapshot,
            horizon=3,
            bootstrap_replicates=bootstrap_replicates,
        )
        transition_predictions.append(prediction)
        transition_metrics.append(metrics)
        transition_tuning.append(tuning)
    peak_days = sign_change_peak_days(sequences)
    for snapshot in (5, 7):
        prediction, metrics, tuning = peak_transition_models(
            model_features,
            peak_days,
            snapshot=snapshot,
            lead_window=3,
            bootstrap_replicates=bootstrap_replicates,
        )
        transition_predictions.append(prediction)
        transition_metrics.append(metrics)
        transition_tuning.append(tuning)
    transition_prediction_frame = pd.concat(transition_predictions, ignore_index=True)
    transition_metric_frame = pd.concat(transition_metrics, ignore_index=True)
    transition_tuning_frame = pd.concat(transition_tuning, ignore_index=True)
    transition_prediction_frame.to_csv(output_dir / "held_out_transition_predictions.csv.gz", index=False)
    transition_metric_frame.to_csv(output_dir / "transition_metrics.csv", index=False)
    transition_tuning_frame.to_csv(output_dir / "transition_tuning.csv", index=False)
    probability_calibration_table(transition_prediction_frame).to_csv(
        output_dir / "transition_calibration.csv", index=False
    )
    paired_transition_comparisons(
        transition_prediction_frame, replicates=bootstrap_replicates
    ).to_csv(output_dir / "paired_transition_comparisons.csv", index=False)

    subgroup_robustness = make_subgroup_robustness(
        model_features, forecast_predictions
    )
    subgroup_robustness.to_csv(output_dir / "subgroup_robustness.csv", index=False)

    counterexamples = synthetic_counterexamples()
    counterexamples.to_csv(output_dir / "synthetic_counterexamples.csv", index=False)

    evidence = pd.DataFrame(
        [
            {
                "prediction": "Geometric scaling near two-thirds",
                "classification": "PARTIALLY SUPPORTED",
                "evidence_type": "held-out geometric pattern",
                "independent_state_test": False,
            },
            {
                "prediction": "Geometry identifies coherent whole-fire state",
                "classification": "NOT IDENTIFIABLE",
                "evidence_type": "no independent state labels",
                "independent_state_test": False,
            },
            {
                "prediction": "Geometry adds future-growth information",
                "classification": "SUPPORTED",
                "evidence_type": "paired held-out prediction",
                "independent_state_test": False,
            },
            {
                "prediction": "Fixed two-thirds temporal growth improves forecasts",
                "classification": "NOT SUPPORTED",
                "evidence_type": "paired held-out prediction",
                "independent_state_test": False,
            },
            {
                "prediction": "Coupled coherence-fuel forcing closure",
                "classification": "NOT IDENTIFIABLE",
                "evidence_type": "C and prospective Amax unavailable",
                "independent_state_test": False,
            },
            {
                "prediction": "Prospective acceleration and peak transition",
                "classification": "PARTIALLY SUPPORTED",
                "evidence_type": "held-out transition prediction",
                "independent_state_test": False,
            },
            {
                "prediction": "Past coarse weather adds to geometry",
                "classification": "NOT SUPPORTED",
                "evidence_type": "paired held-out prediction",
                "independent_state_test": False,
            },
            {
                "prediction": "Precise early termination prediction",
                "classification": "NOT SUPPORTED",
                "evidence_type": "held-out endpoint and survival prediction",
                "independent_state_test": False,
            },
            {
                "prediction": "Abrupt physical fire termination",
                "classification": "NOT IDENTIFIABLE",
                "evidence_type": "FIRED endpoint is an observation-product endpoint",
                "independent_state_test": False,
            },
            {
                "prediction": "Energetic metabolism",
                "classification": "NOT YET TESTED",
                "evidence_type": "no fuel consumption or energy release observations",
                "independent_state_test": False,
            },
            {
                "prediction": "Operational spread-model superiority",
                "classification": "NOT YET TESTED",
                "evidence_type": "no event-matched operational model outputs",
                "independent_state_test": False,
            },
        ]
    )
    evidence.to_csv(output_dir / "evidence_classification.csv", index=False)

    figure_detection(merged, detection, output_dir)
    figure_robustness(robustness, output_dir)
    figure_predictions(sequences, forecast_predictions, output_dir)
    figure_lifecycle(transition_metric_frame, survival_summary, output_dir)
    figure_discrimination(forecast_metric_frame, output_dir)
    figure_failure_map(model_features, forecast_predictions, output_dir)

    design = {
        "mode": "smoke" if args.smoke else "full",
        "random_seed": DEFAULT_SEED,
        "development_years": [2001, 2012],
        "calibration_years": [2013, 2015],
        "held_out_years": [2016, 2020],
        "snapshot_days": [5, 7],
        "forecast_horizons_days": [1, 3, 5, 7],
        "geometric_detection_snapshots": [5, 7, 10, 14, 21],
        "bootstrap_replicates": bootstrap_replicates,
        "predictor_policy": "immutable origin-safe whitelists; future-derived land cover excluded",
        "input_checksums": {str(path): sha256(path) for path in input_paths},
    }
    design_json = json.dumps(design, indent=2, sort_keys=True)
    (output_dir / "design_lock.json").write_text(design_json + "\n", encoding="utf-8")
    design_hash = hashlib.sha256(design_json.encode("utf-8")).hexdigest()

    held_detection = detection_summary[detection_summary.partition == "held_out"]
    day7_metrics = forecast_metric_frame[
        (forecast_metric_frame.snapshot_day == 7)
        & (forecast_metric_frame.horizon_days == 7)
    ].set_index("model")
    transition_day7 = transition_metric_frame[transition_metric_frame.snapshot_day == 7]
    report = {
        "design_hash": design_hash,
        "counts": {
            "events": int(sequences.id.nunique()),
            "held_out_events": int(sequences.loc[sequences.ig_year >= 2016, "id"].nunique()),
            "detection_windows": int(len(detection)),
            "held_out_forecasts": int(len(forecast_predictions)),
        },
        "primary_results": {
            "held_out_day7_geometric_detection_fraction": float(
                held_detection.loc[
                    held_detection.snapshot_day == 7, "geometric_detection_fraction"
                ].iloc[0]
            ),
            "held_out_day7_persistent_detection_fraction": float(
                held_detection.loc[
                    held_detection.snapshot_day == 7, "persistent_detection_fraction"
                ].iloc[0]
            ),
            "day7_horizon7_area_ridge_absolute_log_error": float(
                day7_metrics.loc["area_ridge", "mean_absolute_log_error"]
            ),
            "day7_horizon7_dynamics_ridge_absolute_log_error": float(
                day7_metrics.loc["dynamics_ridge", "mean_absolute_log_error"]
            ),
            "day7_horizon7_geometry_proxy_absolute_log_error": float(
                day7_metrics.loc["geometry_proxy", "mean_absolute_log_error"]
            ),
            "day7_horizon7_two_thirds_absolute_log_error": float(
                day7_metrics.loc["two_thirds", "mean_absolute_log_error"]
            ),
            "day7_acceleration_geometry_balanced_accuracy": float(
                transition_day7[
                    (transition_day7.target == "future_accelerating")
                    & (transition_day7.model == "geometry_proxy")
                ].balanced_accuracy.iloc[0]
            ),
            "day7_peak_geometry_balanced_accuracy": float(
                transition_day7[
                    (transition_day7.target == "peak_in_window")
                    & (transition_day7.model == "geometry_proxy")
                ].balanced_accuracy.iloc[0]
            ),
        },
        "non_identifiable": [
            "independent coherent-state classification accuracy",
            "latent coherence C",
            "prospective reachable-fuel fraction F",
            "canonical coupled forcing closure",
            "suppression versus fuel-barrier attribution",
            "physical combustion termination",
        ],
        "not_tested": [
            "energetic throughput",
            "real spatial-resolution sensitivity",
            "event-matched operational spread models",
        ],
    }
    (output_dir / "run_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote adversarial validation outputs to {output_dir}")
    print(json.dumps(report["primary_results"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
