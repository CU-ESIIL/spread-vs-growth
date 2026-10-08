#!/usr/bin/env python3
"""Test persistent-regime detection, metabolic damage, and early termination."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fire_metabolism.fired_outcomes import fit_standardized_ridge
from fire_metabolism.fired_survival import (
    DAMAGE_FEATURE_COLUMNS,
    MECHANISTIC_SURVIVAL_FEATURE_COLUMNS,
    STATE_FEATURE_COLUMNS,
    add_metabolic_damage_features,
    add_observed_states,
    fit_logistic_hazard,
)


BASE_COLUMNS = MECHANISTIC_SURVIVAL_FEATURE_COLUMNS + STATE_FEATURE_COLUMNS
DAMAGE_COLUMNS = BASE_COLUMNS + DAMAGE_FEATURE_COLUMNS
MODEL_LABELS = {
    "pooled_endpoint": "Pooled geometry endpoint",
    "oracle_persistent_ridge": "Persistent-only geometry",
    "oracle_persistent_damage_ridge": "Persistent-only + damage",
    "operational_probability_blend": "Probability-weighted regime blend",
    "operational_damage_blend": "Probability-weighted + damage",
}
MODEL_COLORS = {
    "pooled_endpoint": "#1B9E77",
    "oracle_persistent_ridge": "#B52322",
    "oracle_persistent_damage_ridge": "#6A3D9A",
    "operational_probability_blend": "#4F79B7",
    "operational_damage_blend": "#D58A2A",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sequences",
        type=Path,
        default=Path("outputs/fired_prediction/fired_sequences.csv.gz"),
    )
    parser.add_argument(
        "--features",
        type=Path,
        default=Path("outputs/fired_lifecycle_prediction/snapshot_features.csv.gz"),
    )
    parser.add_argument(
        "--outcomes",
        type=Path,
        default=Path(
            "outputs/fired_lifecycle_prediction/event_lifecycle_outcomes.csv.gz"
        ),
    )
    parser.add_argument(
        "--endpoint-predictions",
        type=Path,
        default=Path(
            "outputs/fired_lifecycle_prediction/held_out_lifecycle_predictions.csv.gz"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/fired_persistence_damage"),
    )
    return parser.parse_args()


def binary_log_loss(observed: np.ndarray, probability: np.ndarray) -> float:
    probability = np.clip(np.asarray(probability, dtype=float), 1e-12, 1 - 1e-12)
    observed = np.asarray(observed, dtype=float)
    return float(
        -np.mean(observed * np.log(probability) + (1 - observed) * np.log(1 - probability))
    )


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


def fit_persistence_classifier(
    development: pd.DataFrame,
    calibration: pd.DataFrame,
    *,
    feature_columns: tuple[str, ...],
    threshold_day: float,
) -> tuple[object, float, pd.DataFrame]:
    training = development.copy()
    validation = calibration.copy()
    training["terminal_transition"] = (
        training.death_day >= threshold_day
    ).astype(float)
    validation_target = (
        validation.death_day >= threshold_day
    ).to_numpy(dtype=float)
    rows = []
    models = {}
    for alpha in (0.1, 1.0, 10.0, 100.0, 1000.0):
        model = fit_logistic_hazard(
            training,
            feature_columns=feature_columns,
            alpha=alpha,
        )
        probability = model.predict_hazard(validation)
        rows.append(
            {
                "alpha": alpha,
                "calibration_log_loss": binary_log_loss(
                    validation_target, probability
                ),
                "calibration_auc": rank_auc(validation_target, probability),
            }
        )
        models[alpha] = model
    tuning = pd.DataFrame(rows)
    selected_alpha = float(
        tuning.loc[tuning.calibration_log_loss.idxmin(), "alpha"]
    )
    model = models[selected_alpha]
    calibration_probability = model.predict_hazard(validation)
    high_confidence_threshold = float(np.quantile(calibration_probability, 0.90))
    tuning["selected"] = tuning.alpha == selected_alpha
    tuning["high_confidence_threshold"] = high_confidence_threshold
    return model, high_confidence_threshold, tuning


def classifier_metrics(
    observed: np.ndarray,
    probability: np.ndarray,
    high_confidence_threshold: float,
) -> dict[str, float]:
    observed = np.asarray(observed, dtype=bool)
    selected = probability >= high_confidence_threshold
    return {
        "n_events": int(len(observed)),
        "prevalence": float(observed.mean()),
        "rank_auc": rank_auc(observed, probability),
        "brier_score": float(np.mean((probability - observed) ** 2)),
        "high_confidence_threshold": high_confidence_threshold,
        "high_confidence_n": int(selected.sum()),
        "high_confidence_ppv": float(observed[selected].mean())
        if selected.any()
        else np.nan,
        "high_confidence_sensitivity": float((selected & observed).sum() / observed.sum()),
        "high_confidence_specificity": float(
            ((~selected) & (~observed)).sum() / (~observed).sum()
        ),
    }


def tune_remaining_life_ridge(
    development: pd.DataFrame,
    calibration: pd.DataFrame,
    *,
    feature_columns: tuple[str, ...],
) -> tuple[object, pd.DataFrame]:
    target = np.log1p(
        development.death_day.to_numpy(dtype=float)
        - development.snapshot_day.to_numpy(dtype=float)
    )
    rows = []
    models = {}
    for alpha in (0.1, 1.0, 10.0, 100.0, 1000.0):
        model = fit_standardized_ridge(
            development,
            target,
            feature_columns=feature_columns,
            alpha=alpha,
        )
        predicted = calibration.snapshot_day.to_numpy(dtype=float) + np.expm1(
            model.predict(calibration)
        )
        rows.append(
            {
                "alpha": alpha,
                "calibration_mae": float(
                    np.abs(predicted - calibration.death_day).mean()
                ),
            }
        )
        models[alpha] = model
    tuning = pd.DataFrame(rows)
    selected_alpha = float(tuning.loc[tuning.calibration_mae.idxmin(), "alpha"])
    tuning["selected"] = tuning.alpha == selected_alpha
    return models[selected_alpha], tuning


def ridge_death_prediction(model: object, frame: pd.DataFrame) -> np.ndarray:
    return frame.snapshot_day.to_numpy(dtype=float) + np.expm1(model.predict(frame))


def summarize_death_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = {
        "all_at_risk": predictions,
        "true_persistent": predictions[predictions.actual_persistent],
    }
    for group_name, selected in groups.items():
        for (snapshot, model), group in selected.groupby(
            ["snapshot_day", "model"], sort=True
        ):
            if model.startswith("oracle_") and group_name == "all_at_risk":
                continue
            error = group.predicted_death_day - group.observed_death_day
            rows.append(
                {
                    "evaluation_group": group_name,
                    "snapshot_day": int(snapshot),
                    "model": model,
                    "n_events": int(group.id.nunique()),
                    "mean_absolute_error": float(np.abs(error).mean()),
                    "mean_bias": float(error.mean()),
                    "within_2_days_fraction": float((np.abs(error) <= 2).mean()),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["evaluation_group", "snapshot_day", "mean_absolute_error"]
    )


def persistent_entry_summary(probabilities: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    geometry = probabilities[probabilities.model == "geometry_state"].copy()
    rows = []
    for event_id, event in geometry.groupby("id", sort=False):
        event = event.sort_values("snapshot_day")
        entered = event[event.high_confidence_persistent]
        rows.append(
            {
                "id": int(event_id),
                "actual_persistent": bool(event.actual_persistent.iloc[0]),
                "first_high_confidence_entry_day": (
                    float(entered.snapshot_day.iloc[0]) if not entered.empty else np.nan
                ),
                "maximum_persistent_probability": float(
                    event.persistent_probability.max()
                ),
            }
        )
    entries = pd.DataFrame(rows)
    summary_rows = []
    for actual, group in entries.groupby("actual_persistent"):
        detected = group.first_high_confidence_entry_day.notna()
        summary_rows.append(
            {
                "actual_persistent": bool(actual),
                "n_events": int(len(group)),
                "fraction_ever_high_confidence": float(detected.mean()),
                "median_entry_day_when_detected": float(
                    group.loc[detected, "first_high_confidence_entry_day"].median()
                ),
                "median_maximum_probability": float(
                    group.maximum_persistent_probability.median()
                ),
            }
        )
    return entries, pd.DataFrame(summary_rows)


def plot_persistence_detection(metrics: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.5), constrained_layout=True)
    for model, color, label in (
        ("geometry_state", "#1B9E77", "Geometry + state"),
        ("geometry_state_damage", "#6A3D9A", "Geometry + state + damage"),
    ):
        values = metrics[metrics.model == model].sort_values("snapshot_day")
        axes[0].plot(
            values.snapshot_day,
            values.rank_auc,
            marker="o",
            lw=2.3,
            color=color,
            label=label,
        )
    geometry = metrics[metrics.model == "geometry_state"].sort_values("snapshot_day")
    axes[1].plot(
        geometry.snapshot_day,
        geometry.high_confidence_ppv,
        marker="o",
        lw=2.3,
        color="#B52322",
        label="Precision",
    )
    axes[1].plot(
        geometry.snapshot_day,
        geometry.high_confidence_sensitivity,
        marker="o",
        lw=2.3,
        color="#4F79B7",
        label="Sensitivity",
    )
    axes[0].set(
        xlabel="Snapshot day",
        ylabel="Held-out ROC AUC",
        title="Persistent-regime discrimination",
        ylim=(0.5, 1.0),
    )
    axes[1].set(
        xlabel="Snapshot day",
        ylabel="Fraction",
        title="Calibration-defined top-risk group",
        ylim=(0, 1),
    )
    for ax in axes:
        ax.grid(alpha=0.2)
        ax.legend(frameon=False)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def plot_persistent_death(summary: pd.DataFrame, output: Path) -> None:
    selected = summary[summary.evaluation_group == "true_persistent"]
    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    for model in MODEL_LABELS:
        values = selected[selected.model == model].sort_values("snapshot_day")
        if values.empty:
            continue
        ax.plot(
            values.snapshot_day,
            values.mean_absolute_error,
            marker="o",
            lw=2.3,
            color=MODEL_COLORS[model],
            label=MODEL_LABELS[model],
        )
    ax.set(
        xlabel="Snapshot day",
        ylabel="Death-day MAE (days)",
        title="Death timing within the persistent regime",
        xticks=sorted(selected.snapshot_day.unique()),
    )
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output, dpi=240)
    plt.close(fig)


def plot_external_termination(candidates: pd.DataFrame, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    for state, group in candidates.groupby("observed_state"):
        ax.scatter(
            group.persistent_probability,
            group.persistent_course_shortfall_days,
            s=35,
            alpha=0.72,
            label=state,
        )
    ax.axhline(10, color="#202124", ls="--", lw=1.2)
    ax.set(
        xlabel="Day-7 predicted persistent-regime probability",
        ylabel="Persistent-course predicted minus observed death (days)",
        title="External-termination-like candidates, not suppression labels",
    )
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(output, dpi=240)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    sequences = pd.read_csv(args.sequences)
    features = pd.read_csv(args.features)
    outcomes = pd.read_csv(args.outcomes)
    endpoint = pd.read_csv(args.endpoint_predictions)
    features = add_observed_states(features, sequences)
    features = add_metabolic_damage_features(features, sequences)
    development_outcomes = outcomes[outcomes.ig_year <= 2012]
    persistent_day = float(development_outcomes.death_day.quantile(0.90))

    probability_rows = []
    classifier_rows = []
    classifier_tuning = []
    coefficient_rows = []
    classifier_models: dict[tuple[int, str], object] = {}
    classifier_thresholds: dict[tuple[int, str], float] = {}
    for snapshot in sorted(features.snapshot_day.unique()):
        if snapshot >= persistent_day:
            continue
        landmark = features[features.snapshot_day == snapshot].reset_index(drop=True)
        development = landmark[landmark.ig_year <= 2012].reset_index(drop=True)
        calibration = landmark[landmark.ig_year.between(2013, 2015)].reset_index(drop=True)
        test = landmark[landmark.ig_year >= 2016].reset_index(drop=True)
        if any(
            frame.assign(target=frame.death_day >= persistent_day).target.nunique() < 2
            for frame in (development, calibration, test)
        ):
            continue
        for model_name, columns in (
            ("geometry_state", BASE_COLUMNS),
            ("geometry_state_damage", DAMAGE_COLUMNS),
        ):
            model, threshold, tuning = fit_persistence_classifier(
                development,
                calibration,
                feature_columns=columns,
                threshold_day=persistent_day,
            )
            classifier_models[(int(snapshot), model_name)] = model
            classifier_thresholds[(int(snapshot), model_name)] = threshold
            tuning.insert(0, "snapshot_day", int(snapshot))
            tuning.insert(1, "model", model_name)
            classifier_tuning.append(tuning)
            probability = model.predict_hazard(test)
            observed = test.death_day.to_numpy(dtype=float) >= persistent_day
            metrics = classifier_metrics(observed, probability, threshold)
            metrics.update({"snapshot_day": int(snapshot), "model": model_name})
            classifier_rows.append(metrics)
            for row, value, actual in zip(
                test.itertuples(index=False), probability, observed, strict=True
            ):
                probability_rows.append(
                    {
                        "id": int(row.id),
                        "ig_year": int(row.ig_year),
                        "snapshot_day": int(snapshot),
                        "observed_state": row.observed_state,
                        "model": model_name,
                        "persistent_probability": float(value),
                        "high_confidence_threshold": threshold,
                        "high_confidence_persistent": bool(value >= threshold),
                        "actual_persistent": bool(actual),
                        "observed_death_day": int(row.death_day),
                    }
                )
            for column, coefficient in zip(
                model.feature_columns, model.coefficients[1:], strict=True
            ):
                coefficient_rows.append(
                    {
                        "snapshot_day": int(snapshot),
                        "model": model_name,
                        "feature": column,
                        "standardized_log_odds_coefficient": float(coefficient),
                    }
                )

    probabilities = pd.DataFrame(probability_rows)
    classifier_summary = pd.DataFrame(classifier_rows)
    classifier_tuning_frame = pd.concat(classifier_tuning, ignore_index=True)
    coefficients = pd.DataFrame(coefficient_rows)
    entries, entry_summary = persistent_entry_summary(probabilities)

    endpoint_death = endpoint[
        (endpoint.target == "death_day")
        & (endpoint.model == "geometry_metabolic_ridge")
    ].copy()
    death_rows = []
    death_tuning = []
    for snapshot in sorted(features.snapshot_day.unique()):
        landmark = features[features.snapshot_day == snapshot].reset_index(drop=True)
        development = landmark[landmark.ig_year <= 2012].reset_index(drop=True)
        calibration = landmark[landmark.ig_year.between(2013, 2015)].reset_index(drop=True)
        test = landmark[landmark.ig_year >= 2016].reset_index(drop=True)
        dev_persistent = development[development.death_day >= persistent_day]
        cal_persistent = calibration[calibration.death_day >= persistent_day]
        test_actual = test.death_day.to_numpy(dtype=float) >= persistent_day

        persistent_predictions = {}
        for model_name, columns in (
            ("oracle_persistent_ridge", BASE_COLUMNS),
            ("oracle_persistent_damage_ridge", DAMAGE_COLUMNS),
        ):
            model, tuning = tune_remaining_life_ridge(
                dev_persistent,
                cal_persistent,
                feature_columns=columns,
            )
            tuning.insert(0, "snapshot_day", int(snapshot))
            tuning.insert(1, "model", model_name)
            death_tuning.append(tuning)
            persistent_predictions[model_name] = ridge_death_prediction(model, test)

        pooled = endpoint_death[endpoint_death.snapshot_day == snapshot].set_index("id")
        pooled_prediction = pooled.loc[test.id, "predicted"].to_numpy(dtype=float)
        predictions_by_model = {
            "pooled_endpoint": pooled_prediction,
            **persistent_predictions,
        }
        if (int(snapshot), "geometry_state") in classifier_models:
            base_probability = classifier_models[
                (int(snapshot), "geometry_state")
            ].predict_hazard(test)
            damage_probability = classifier_models[
                (int(snapshot), "geometry_state_damage")
            ].predict_hazard(test)
            predictions_by_model["operational_probability_blend"] = (
                pooled_prediction
                + base_probability
                * (
                    persistent_predictions["oracle_persistent_ridge"]
                    - pooled_prediction
                )
            )
            predictions_by_model["operational_damage_blend"] = (
                pooled_prediction
                + damage_probability
                * (
                    persistent_predictions["oracle_persistent_damage_ridge"]
                    - pooled_prediction
                )
            )
        for model_name, predicted in predictions_by_model.items():
            for row, prediction, actual_persistent in zip(
                test.itertuples(index=False), predicted, test_actual, strict=True
            ):
                death_rows.append(
                    {
                        "id": int(row.id),
                        "ig_year": int(row.ig_year),
                        "snapshot_day": int(snapshot),
                        "observed_state": row.observed_state,
                        "model": model_name,
                        "observed_death_day": int(row.death_day),
                        "predicted_death_day": float(prediction),
                        "actual_persistent": bool(actual_persistent),
                    }
                )

    death_predictions = pd.DataFrame(death_rows)
    death_summary = summarize_death_predictions(death_predictions)
    death_tuning_frame = pd.concat(death_tuning, ignore_index=True)

    day7_probability = probabilities[
        (probabilities.snapshot_day == 7)
        & (probabilities.model == "geometry_state")
        & probabilities.high_confidence_persistent
        & (~probabilities.actual_persistent)
    ].copy()
    day7_course = death_predictions[
        (death_predictions.snapshot_day == 7)
        & (death_predictions.model == "oracle_persistent_ridge")
    ][["id", "predicted_death_day"]].rename(
        columns={"predicted_death_day": "persistent_course_predicted_death_day"}
    )
    external_candidates = day7_probability.merge(
        day7_course, on="id", how="left", validate="one_to_one"
    )
    external_candidates["persistent_course_shortfall_days"] = (
        external_candidates.persistent_course_predicted_death_day
        - external_candidates.observed_death_day
    )
    external_candidates["external_termination_like_score"] = (
        external_candidates.persistent_probability
        * np.maximum(0.0, external_candidates.persistent_course_shortfall_days)
    )
    external_candidates["strong_candidate"] = (
        external_candidates.persistent_course_shortfall_days >= 10
    )
    external_candidates = external_candidates.sort_values(
        "external_termination_like_score", ascending=False
    )

    probabilities.to_csv(
        output / "held_out_persistent_regime_probabilities.csv.gz",
        index=False,
        compression="gzip",
    )
    classifier_summary.to_csv(
        output / "persistent_regime_classifier_summary.csv", index=False
    )
    classifier_tuning_frame.to_csv(
        output / "persistent_regime_classifier_tuning.csv", index=False
    )
    coefficients.to_csv(
        output / "persistent_regime_coefficients.csv", index=False
    )
    entries.to_csv(output / "persistent_regime_entry_by_event.csv", index=False)
    entry_summary.to_csv(output / "persistent_regime_entry_summary.csv", index=False)
    death_predictions.to_csv(
        output / "held_out_persistent_death_predictions.csv.gz",
        index=False,
        compression="gzip",
    )
    death_summary.to_csv(
        output / "persistent_death_prediction_summary.csv", index=False
    )
    death_tuning_frame.to_csv(
        output / "persistent_death_tuning.csv", index=False
    )
    external_candidates.to_csv(
        output / "external_termination_like_candidates.csv", index=False
    )
    plot_persistence_detection(
        classifier_summary, output / "persistent_regime_detection.png"
    )
    plot_persistent_death(
        death_summary, output / "persistent_regime_death_prediction.png"
    )
    plot_external_termination(
        external_candidates, output / "external_termination_like_candidates.png"
    )

    day5_classifier = classifier_summary[
        (classifier_summary.snapshot_day == 5)
        & (classifier_summary.model == "geometry_state")
    ].iloc[0]
    day7_classifier = classifier_summary[
        (classifier_summary.snapshot_day == 7)
        & (classifier_summary.model == "geometry_state")
    ].iloc[0]
    day5_death = death_summary[
        (death_summary.evaluation_group == "true_persistent")
        & (death_summary.snapshot_day == 5)
    ].set_index("model")
    report = {
        "design": {
            "persistent_regime_definition": "death day at or above the development-period 90th percentile",
            "persistent_threshold_day": persistent_day,
            "high_confidence_definition": "persistent probability at or above the calibration-period 90th percentile",
            "damage_definition": "past-only linear and squared two-thirds beta exposure with decline, volatility, and exponential retention",
            "external_termination_definition": "high predicted persistence followed by an observed death at least ten days earlier than the persistent-course model",
        },
        "primary_results": {
            "day5_persistent_auc": float(day5_classifier.rank_auc),
            "day5_high_confidence_ppv": float(day5_classifier.high_confidence_ppv),
            "day5_high_confidence_sensitivity": float(
                day5_classifier.high_confidence_sensitivity
            ),
            "day7_persistent_auc": float(day7_classifier.rank_auc),
            "day7_high_confidence_ppv": float(day7_classifier.high_confidence_ppv),
            "day5_pooled_persistent_death_mae": float(
                day5_death.loc["pooled_endpoint", "mean_absolute_error"]
            ),
            "day5_oracle_persistent_death_mae": float(
                day5_death.loc["oracle_persistent_ridge", "mean_absolute_error"]
            ),
            "day5_oracle_persistent_damage_death_mae": float(
                day5_death.loc[
                    "oracle_persistent_damage_ridge", "mean_absolute_error"
                ]
            ),
            "day7_external_termination_like_events": int(len(external_candidates)),
            "day7_strong_external_termination_like_candidates": int(
                external_candidates.strong_candidate.sum()
            ),
        },
        "interpretation_limits": [
            "Oracle persistent-only performance uses observed duration to define the evaluation regime and is not operational.",
            "Damage terms computed only from area growth are largely transformed versions of the existing trajectory.",
            "External-termination-like candidates are not suppression labels and may reflect weather, fuel barriers, topography, observation error, or model misspecification.",
            "The source cohort includes only FIRED events lasting 8-60 days with at least four detection days.",
        ],
    }
    (output / "run_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (output / "README.md").write_text(
        "# FIRED persistence and damage outputs\n\n"
        "This experiment tests past-only persistent-regime classification, oracle and "
        "operational regime-specific death prediction, metabolic-damage features, and "
        "noncausal external-termination-like candidates. See `run_report.json` and the "
        "project documentation for interpretation limits.\n",
        encoding="utf-8",
    )
    print(json.dumps(report["primary_results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
