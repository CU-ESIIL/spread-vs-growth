#!/usr/bin/env python3
"""Fit and evaluate state-conditioned FIRED death-survival models."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fire_metabolism.fired_survival import (
    GEOMETRY_STATE_SURVIVAL_FEATURE_COLUMNS,
    STATE_NAMES,
    STATE_SURVIVAL_FEATURE_COLUMNS,
    add_conformal_intervals,
    add_observed_states,
    calibrate_logit_shift,
    conformal_interval_radius,
    fit_logistic_hazard,
    make_person_period_table,
    predict_death_distributions,
)


MODEL_LABELS = {
    "historical_median": "Historical median endpoint",
    "geometry_metabolic_ridge": "Geometry endpoint ridge",
    "state_empirical_survival": "State empirical survival",
    "state_hazard": "State hazard",
    "geometry_state_hazard": "Geometry + state hazard",
}
MODEL_COLORS = {
    "historical_median": "#A6761D",
    "geometry_metabolic_ridge": "#1B9E77",
    "state_empirical_survival": "#6A3D9A",
    "state_hazard": "#4F79B7",
    "geometry_state_hazard": "#B52322",
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
        "--endpoint-predictions",
        type=Path,
        default=Path(
            "outputs/fired_lifecycle_prediction/held_out_lifecycle_predictions.csv.gz"
        ),
    )
    parser.add_argument(
        "--outcomes",
        type=Path,
        default=Path(
            "outputs/fired_lifecycle_prediction/event_lifecycle_outcomes.csv.gz"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/fired_state_survival"),
    )
    parser.add_argument("--coverage", type=float, default=0.9)
    return parser.parse_args()


def fit_tuned_hazard(
    development: pd.DataFrame,
    calibration: pd.DataFrame,
    *,
    model_name: str,
    feature_columns: tuple[str, ...],
    coverage: float,
) -> tuple[object, float, pd.DataFrame]:
    person_period = make_person_period_table(development)
    candidates = []
    fitted = {}
    for alpha in (0.1, 1.0, 10.0, 100.0):
        model = fit_logistic_hazard(
            person_period,
            feature_columns=feature_columns,
            alpha=alpha,
        )
        predictions = predict_death_distributions(model, calibration)
        candidates.append(
            {
                "model": model_name,
                "stage": "ridge_alpha",
                "alpha": alpha,
                "logit_shift": 0.0,
                "calibration_log_score": float(
                    predictions.death_log_score.mean()
                ),
                "calibration_mae": float(np.abs(predictions.error).mean()),
            }
        )
        fitted[alpha] = model
    tuning = pd.DataFrame(candidates)
    selected_alpha = float(
        tuning.loc[tuning.calibration_log_score.idxmin(), "alpha"]
    )
    shifted, shift_curve = calibrate_logit_shift(
        fitted[selected_alpha],
        calibration,
        shifts=np.linspace(-2.0, 2.0, 21),
    )
    shift_curve.insert(0, "model", model_name)
    shift_curve.insert(1, "stage", "logit_shift")
    shift_curve["alpha"] = selected_alpha
    calibration_prediction = predict_death_distributions(shifted, calibration)
    radius = conformal_interval_radius(
        calibration_prediction, coverage=coverage
    )
    tuning["selected"] = tuning.alpha == selected_alpha
    shift_curve["selected"] = (
        shift_curve.logit_shift == shifted.logit_shift
    )
    return shifted, radius, pd.concat([tuning, shift_curve], ignore_index=True)


def empirical_state_prediction(
    development: pd.DataFrame,
    target: pd.DataFrame,
    *,
    model_name: str = "state_empirical_survival",
) -> pd.DataFrame:
    remaining_all = development.death_day - development.snapshot_day
    rows = []
    for event in target.itertuples(index=False):
        state_values = development[
            development.observed_state == event.observed_state
        ]
        remaining = state_values.death_day - state_values.snapshot_day
        if len(remaining) < 20:
            remaining = remaining_all
        predicted = int(event.snapshot_day + np.median(remaining))
        rows.append(
            {
                "id": int(event.id),
                "ig_year": int(event.ig_year),
                "snapshot_day": int(event.snapshot_day),
                "observed_state": str(event.observed_state),
                "observed_death_day": int(event.death_day),
                "predicted_death_day": predicted,
                "distribution_mean_death_day": float(
                    event.snapshot_day + remaining.mean()
                ),
                "model_interval_lower": float(
                    event.snapshot_day + remaining.quantile(0.05)
                ),
                "model_interval_upper": float(
                    event.snapshot_day + remaining.quantile(0.95)
                ),
                "observed_death_probability": np.nan,
                "death_log_score": np.nan,
                "model": model_name,
                "error": predicted - int(event.death_day),
            }
        )
    return pd.DataFrame(rows)


def endpoint_prediction(
    endpoint: pd.DataFrame,
    state_features: pd.DataFrame,
) -> pd.DataFrame:
    selected = endpoint[
        (endpoint.target == "death_day")
        & endpoint.model.isin(["historical_median", "geometry_metabolic_ridge"])
    ].copy()
    selected = selected.merge(
        state_features[["id", "snapshot_day", "observed_state"]],
        on=["id", "snapshot_day"],
        how="left",
        validate="many_to_one",
    )
    selected = selected.rename(
        columns={"observed": "observed_death_day", "predicted": "predicted_death_day"}
    )
    selected["distribution_mean_death_day"] = selected.predicted_death_day
    selected["model_interval_lower"] = np.nan
    selected["model_interval_upper"] = np.nan
    selected["interval_lower"] = np.nan
    selected["interval_upper"] = np.nan
    selected["observed_death_probability"] = np.nan
    selected["death_log_score"] = np.nan
    return selected[
        [
            "id",
            "ig_year",
            "snapshot_day",
            "observed_state",
            "observed_death_day",
            "predicted_death_day",
            "distribution_mean_death_day",
            "model_interval_lower",
            "model_interval_upper",
            "interval_lower",
            "interval_upper",
            "observed_death_probability",
            "death_log_score",
            "model",
            "error",
        ]
    ]


def summarize_predictions(
    predictions: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    q90: float,
    q95: float,
) -> pd.DataFrame:
    death = outcomes.set_index("id").death_day
    predictions = predictions.copy()
    predictions["event_death_day"] = predictions.id.map(death)
    groups = {
        "all_at_risk": predictions,
        "long_q90_plus": predictions[predictions.event_death_day >= q90],
        "extreme_q95_plus": predictions[predictions.event_death_day >= q95],
    }
    rows = []
    for scope, selected in groups.items():
        for (snapshot, model), group in selected.groupby(
            ["snapshot_day", "model"], sort=True
        ):
            has_interval = group.interval_lower.notna()
            covered = (
                (group.observed_death_day >= group.interval_lower)
                & (group.observed_death_day <= group.interval_upper)
            )
            rows.append(
                {
                    "evaluation_group": scope,
                    "snapshot_day": int(snapshot),
                    "model": model,
                    "n_events": int(group.id.nunique()),
                    "mean_absolute_error": float(np.abs(group.error).mean()),
                    "median_absolute_error": float(np.abs(group.error).median()),
                    "mean_bias": float(group.error.mean()),
                    "distribution_mean_absolute_error": float(
                        np.abs(
                            group.distribution_mean_death_day
                            - group.observed_death_day
                        ).mean()
                    ),
                    "distribution_mean_bias": float(
                        (
                            group.distribution_mean_death_day
                            - group.observed_death_day
                        ).mean()
                    ),
                    "within_2_days_fraction": float((np.abs(group.error) <= 2).mean()),
                    "interval_coverage": (
                        float(covered[has_interval].mean())
                        if has_interval.any()
                        else np.nan
                    ),
                    "median_interval_width": (
                        float(
                            (group.interval_upper - group.interval_lower)[
                                has_interval
                            ].median()
                        )
                        if has_interval.any()
                        else np.nan
                    ),
                    "mean_death_log_score": float(group.death_log_score.mean()),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["evaluation_group", "snapshot_day", "mean_absolute_error"]
    )


def rank_auc(observed: np.ndarray, score: np.ndarray) -> float:
    """Return tie-aware ROC AUC from ranks without an extra dependency."""
    observed = np.asarray(observed, dtype=bool)
    score = np.asarray(score, dtype=float)
    positive = int(observed.sum())
    negative = int((~observed).sum())
    if positive == 0 or negative == 0:
        return np.nan
    ranks = pd.Series(score).rank(method="average").to_numpy(dtype=float)
    return float(
        (ranks[observed].sum() - positive * (positive + 1) / 2)
        / (positive * negative)
    )


def summarize_duration_discrimination(
    predictions: pd.DataFrame, *, q90: float, q95: float
) -> pd.DataFrame:
    rows = []
    survival = predictions[
        predictions.model.isin(["state_hazard", "geometry_state_hazard"])
    ]
    for (snapshot, model), group in survival.groupby(
        ["snapshot_day", "model"], sort=True
    ):
        for label, threshold in (("long_q90_plus", q90), ("extreme_q95_plus", q95)):
            observed = group.observed_death_day.to_numpy(dtype=float) >= threshold
            score = group.distribution_mean_death_day.to_numpy(dtype=float)
            rows.append(
                {
                    "snapshot_day": int(snapshot),
                    "model": model,
                    "duration_group": label,
                    "threshold_day": float(threshold),
                    "n_events": int(len(group)),
                    "prevalence": float(observed.mean()),
                    "rank_auc": rank_auc(observed, score),
                }
            )
    return pd.DataFrame(rows)


def summarize_states(
    features: pd.DataFrame, *, q90: float
) -> pd.DataFrame:
    held_out = features[features.ig_year >= 2016].copy()
    held_out["remaining_days"] = held_out.death_day - held_out.snapshot_day
    rows = []
    for (snapshot, state), group in held_out.groupby(
        ["snapshot_day", "observed_state"], sort=True
    ):
        rows.append(
            {
                "snapshot_day": int(snapshot),
                "observed_state": state,
                "n_events": int(len(group)),
                "median_remaining_days": float(group.remaining_days.median()),
                "remaining_days_q90": float(group.remaining_days.quantile(0.9)),
                "fraction_long_q90_plus": float((group.death_day >= q90).mean()),
            }
        )
    return pd.DataFrame(rows)


def plot_performance(summary: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.8), constrained_layout=True)
    for ax, scope, title in (
        (axes[0], "all_at_risk", "All fires still at risk"),
        (axes[1], "long_q90_plus", "Long fires (development Q90+)"),
    ):
        panel = summary[summary.evaluation_group == scope]
        for model in MODEL_LABELS:
            values = panel[panel.model == model].sort_values("snapshot_day")
            if values.empty:
                continue
            ax.plot(
                values.snapshot_day,
                values.mean_absolute_error,
                marker="o",
                lw=2.2,
                color=MODEL_COLORS[model],
                label=MODEL_LABELS[model],
            )
        ax.set(
            xlabel="Forecast snapshot day",
            ylabel="Death-day MAE (days)",
            title=title,
            xticks=sorted(panel.snapshot_day.unique()),
        )
        ax.grid(alpha=0.2)
    axes[0].legend(frameon=False, fontsize=8)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def plot_state_prognosis(states: pd.DataFrame, output: Path) -> None:
    selected = states[states.snapshot_day == 5].copy()
    selected["observed_state"] = pd.Categorical(
        selected.observed_state, categories=STATE_NAMES, ordered=True
    )
    selected = selected.sort_values("observed_state")
    positions = np.arange(len(selected))
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.5), constrained_layout=True)
    axes[0].bar(positions, selected.median_remaining_days, color="#4F79B7")
    axes[0].set(ylabel="Median remaining days", title="Day-5 state prognosis")
    axes[1].bar(
        positions, selected.fraction_long_q90_plus * 100, color="#B52322"
    )
    axes[1].set(ylabel="Long-fire fraction (%)", title="Long-fire enrichment")
    for ax in axes:
        ax.set_xticks(positions, selected.observed_state, rotation=20, ha="right")
        ax.grid(axis="y", alpha=0.2)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def plot_calibration(predictions: pd.DataFrame, output: Path) -> None:
    selected = predictions[
        (predictions.snapshot_day == 5)
        & (predictions.model == "geometry_state_hazard")
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.7), constrained_layout=True)
    axes[0].hexbin(
        selected.observed_death_day,
        selected.predicted_death_day,
        gridsize=35,
        mincnt=1,
        bins="log",
        cmap="magma_r",
    )
    limits = [
        min(selected.observed_death_day.min(), selected.predicted_death_day.min()),
        max(selected.observed_death_day.max(), selected.predicted_death_day.max()),
    ]
    axes[0].plot(limits, limits, color="#202124", ls="--", lw=1.3)
    axes[0].set(
        xlabel="Observed last-growth day",
        ylabel="Median predicted last-growth day",
        title="Day-5 state-survival prediction",
    )
    covered = (
        (selected.observed_death_day >= selected.interval_lower)
        & (selected.observed_death_day <= selected.interval_upper)
    )
    widths = selected.interval_upper - selected.interval_lower
    axes[1].hist(widths, bins=25, color="#2E745B", alpha=0.85)
    axes[1].axvline(
        widths.median(),
        color="#202124",
        lw=1.4,
        label=f"median width {widths.median():.0f} d",
    )
    axes[1].set(
        xlabel="Calibrated 90% interval width (days)",
        ylabel="Held-out fires",
        title=f"Coverage {covered.mean():.1%}",
    )
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.grid(alpha=0.18)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    if not 0 < args.coverage < 1:
        raise ValueError("coverage must be between zero and one")
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)

    sequences = pd.read_csv(args.sequences)
    features = pd.read_csv(args.features)
    outcomes = pd.read_csv(args.outcomes)
    endpoint = pd.read_csv(args.endpoint_predictions)
    features = add_observed_states(features, sequences)
    development_outcomes = outcomes[outcomes.ig_year <= 2012]
    q90 = float(development_outcomes.death_day.quantile(0.90))
    q95 = float(development_outcomes.death_day.quantile(0.95))

    prediction_frames = []
    tuning_frames = []
    for snapshot in sorted(features.snapshot_day.unique()):
        landmark = features[features.snapshot_day == snapshot].reset_index(drop=True)
        development = landmark[landmark.ig_year <= 2012].reset_index(drop=True)
        calibration = landmark[landmark.ig_year.between(2013, 2015)].reset_index(drop=True)
        test = landmark[landmark.ig_year >= 2016].reset_index(drop=True)

        empirical_calibration = empirical_state_prediction(development, calibration)
        empirical_radius = conformal_interval_radius(
            empirical_calibration, coverage=args.coverage
        )
        empirical_test = empirical_state_prediction(development, test)
        empirical_test = add_conformal_intervals(empirical_test, empirical_radius)
        prediction_frames.append(empirical_test)

        for model_name, columns in (
            ("state_hazard", STATE_SURVIVAL_FEATURE_COLUMNS),
            (
                "geometry_state_hazard",
                GEOMETRY_STATE_SURVIVAL_FEATURE_COLUMNS,
            ),
        ):
            model, radius, tuning = fit_tuned_hazard(
                development,
                calibration,
                model_name=model_name,
                feature_columns=columns,
                coverage=args.coverage,
            )
            tuning.insert(0, "snapshot_day", int(snapshot))
            tuning["conformal_radius_days"] = radius
            tuning_frames.append(tuning)
            predictions = predict_death_distributions(model, test)
            predictions = add_conformal_intervals(predictions, radius)
            predictions["model"] = model_name
            prediction_frames.append(predictions)

    predictions = pd.concat(prediction_frames, ignore_index=True, sort=False)
    endpoint_predictions = endpoint_prediction(endpoint, features)
    predictions = pd.concat(
        [predictions, endpoint_predictions], ignore_index=True, sort=False
    )
    tuning = pd.concat(tuning_frames, ignore_index=True, sort=False)
    summary = summarize_predictions(
        predictions, outcomes, q90=q90, q95=q95
    )
    discrimination = summarize_duration_discrimination(
        predictions, q90=q90, q95=q95
    )
    states = summarize_states(features, q90=q90)

    predictions.to_csv(
        output / "held_out_state_survival_predictions.csv.gz",
        index=False,
        compression="gzip",
    )
    tuning.to_csv(output / "state_survival_tuning.csv", index=False)
    summary.to_csv(output / "state_survival_summary.csv", index=False)
    discrimination.to_csv(
        output / "duration_discrimination_summary.csv", index=False
    )
    states.to_csv(output / "observed_state_prognosis.csv", index=False)
    plot_performance(summary, output / "state_survival_performance.png")
    plot_state_prognosis(states, output / "observed_state_prognosis.png")
    plot_calibration(predictions, output / "state_survival_calibration.png")

    day5 = summary[
        (summary.evaluation_group == "all_at_risk")
        & (summary.snapshot_day == 5)
    ]
    day5_long = summary[
        (summary.evaluation_group == "long_q90_plus")
        & (summary.snapshot_day == 5)
    ]
    report = {
        "design": {
            "development_years": [2001, 2012],
            "calibration_years": [2013, 2015],
            "held_out_test_years": [2016, 2020],
            "snapshot_days": sorted(int(value) for value in features.snapshot_day.unique()),
            "states": list(STATE_NAMES),
            "death_definition": "last day with a positive FIRED detected-area increment",
            "long_fire_threshold_day": q90,
            "extreme_duration_threshold_day": q95,
            "interval_coverage_target": args.coverage,
        },
        "counts": {
            "events": int(outcomes.id.nunique()),
            "held_out_events": int((outcomes.ig_year >= 2016).sum()),
            "prediction_rows": int(len(predictions)),
        },
        "day5_all_fire_results": day5.set_index("model")[
            [
                "n_events",
                "mean_absolute_error",
                "mean_bias",
                "distribution_mean_absolute_error",
                "distribution_mean_bias",
                "within_2_days_fraction",
                "interval_coverage",
                "median_interval_width",
            ]
        ].to_dict(orient="index"),
        "day5_long_fire_results": day5_long.set_index("model")[
            [
                "n_events",
                "mean_absolute_error",
                "mean_bias",
                "distribution_mean_absolute_error",
                "distribution_mean_bias",
                "within_2_days_fraction",
                "interval_coverage",
                "median_interval_width",
            ]
        ].to_dict(orient="index"),
        "duration_discrimination": discrimination[
            discrimination.snapshot_day.isin([5, 7, 21])
        ].to_dict(orient="records"),
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "limitations": [
            "Observed states are deterministic past-only proxies, not independently measured combustion states.",
            "The model uses cumulative mapped perimeter rather than active fireline length.",
            "No future weather, fuel moisture, suppression, or forward fuel connectivity is included.",
            "The FIRED last-growth day is an observation-product endpoint rather than physical extinction.",
            "Long-duration groups use observed outcomes only for retrospective evaluation.",
            "The source prediction cohort is restricted to FIRED events lasting 8-60 days with at least four detection days.",
        ],
    }
    (output / "run_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (output / "README.md").write_text(
        "# FIRED state-survival outputs\n\n"
        "This temporally held-out experiment compares endpoint death-day regression with "
        "state-conditioned discrete-time hazards. The survival models predict a complete "
        "death-time distribution and attach split-conformal 90% intervals calibrated only "
        "on 2013-2015 fires. See `run_report.json` for definitions and limitations.\n",
        encoding="utf-8",
    )
    print(json.dumps(report["day5_all_fire_results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
