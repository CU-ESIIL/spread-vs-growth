#!/usr/bin/env python3
"""Test whether predictable effective coupling improves FIRED forecasts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from fire_metabolism.adversarial_validation import (
    AREA_GEOMETRY_PREDICTORS,
    DYNAMICS_PREDICTORS,
    DEFAULT_SEED,
    binary_metrics,
    paired_event_bootstrap,
    regression_metrics,
    transformed_forecasts,
    tune_binary_model,
    tune_ridge_alpha,
)
from fire_metabolism.effective_coupling import (
    COUPLING_DYNAMICS_PREDICTORS,
    COUPLING_GEOMETRY_PREDICTORS,
    COUPLING_HISTORY_PREDICTORS,
    COUPLING_PREDICTION_COLUMNS,
    DEFAULT_SIGMA,
    add_coupling_history_features,
    coupling_observations,
    coupling_series,
    exact_growth_change_decomposition,
    fit_lead_coupling_models,
    fixed_quadratic_coupling_frame,
    future_coupling_targets,
    partition_years,
    predict_coupling,
    recursive_area_forecasts,
)
from fire_metabolism.fired_lifecycle import merge_geometry_sequences
from fire_metabolism.fired_outcomes import fit_standardized_ridge
from fire_metabolism.fired_survival import fit_logistic_hazard


PRIMARY_ORIGINS = (5, 7)
UPDATING_ORIGINS = (5, 7, 10, 14, 21)
HORIZONS = (1, 3, 5, 7, 10, 14, 21, 28, 35, 42, 49)
TRANSITION_WINDOWS = (3, 7, 14)
SIGMA_CANDIDATES = (0.0, 0.25, 0.5, 2.0 / 3.0, 0.75, 0.9)
MIN_PRIMARY_HELDOUT = 100
MIN_PERSISTENT_HELDOUT = 40
MIN_PARTITION_AT_ORIGIN = 40
BOOTSTRAP_REPLICATES = 2000
AREA_BIN_EDGES = (0.25, 1.0, 4.0, 16.0, 64.0, 256.0, 1024.0, np.inf)

COLORS = {
    "gray": "#74777A",
    "red": "#B52322",
    "blue": "#6495ED",
    "purple": "#7B4BA3",
    "teal": "#176B62",
    "green": "#2E8B57",
    "gold": "#D6A52A",
    "ink": "#202124",
    "light": "#ECEDEF",
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
        "--output-dir",
        type=Path,
        default=Path("outputs/effective_coupling_validation"),
    )
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--reuse-primary",
        action="store_true",
        help="Reuse an existing coupling_predictions.csv.gz and resume downstream work.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def deterministic_subset(frame: pd.DataFrame, count: int = 120) -> pd.DataFrame:
    event_year = frame.groupby("id", as_index=False).ig_year.first()
    event_year["partition"] = partition_years(event_year.ig_year)
    ids: list[int] = []
    for _, group in event_year.groupby("partition", sort=False):
        ids.extend(group.sort_values("id").id.head(count).tolist())
    return frame[frame.id.isin(ids)].copy()


def bootstrap_mean_ci(values: np.ndarray, *, seed: int, replicates: int) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    generator = np.random.default_rng(seed)
    draws = generator.choice(values, size=(replicates, len(values)), replace=True).mean(axis=1)
    return float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def descriptive_tables(coupling: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labels = ("0.25-1", "1-4", "4-16", "16-64", "64-256", "256-1024", "1024+")
    frame = coupling.copy()
    frame["area_bin"] = pd.cut(
        frame.start_area_km2,
        bins=AREA_BIN_EDGES,
        labels=labels,
        right=False,
    )
    rows = []
    for area_bin, group in frame.dropna(subset=["area_bin"]).groupby("area_bin", observed=True):
        event_means = group.groupby("id").log1p_effective_coupling.mean()
        event_vars = group.groupby("id").log1p_effective_coupling.var().dropna()
        rows.append(
            {
                "area_bin_km2": str(area_bin),
                "n_events": int(group.id.nunique()),
                "n_event_days": int(len(group)),
                "median_effective_coupling": float(group.effective_coupling.median()),
                "q10_effective_coupling": float(group.effective_coupling.quantile(0.1)),
                "q25_effective_coupling": float(group.effective_coupling.quantile(0.25)),
                "q75_effective_coupling": float(group.effective_coupling.quantile(0.75)),
                "q90_effective_coupling": float(group.effective_coupling.quantile(0.9)),
                "between_fire_log1p_variance": float(event_means.var()),
                "mean_within_fire_log1p_variance": float(event_vars.mean()),
            }
        )
    summary = pd.DataFrame(rows)

    positive = frame[frame.effective_coupling > 0].copy()
    positive["coupling_bin"] = pd.qcut(
        positive.effective_coupling,
        q=5,
        duplicates="drop",
    ).astype(str)
    reciprocal = (
        positive.groupby("coupling_bin", observed=True, as_index=False)
        .agg(
            n_events=("id", "nunique"),
            n_event_days=("id", "size"),
            median_area_km2=("start_area_km2", "median"),
            median_growth_km2=("daily_growth_km2", "median"),
            q10_growth_km2=("daily_growth_km2", lambda value: value.quantile(0.1)),
            q90_growth_km2=("daily_growth_km2", lambda value: value.quantile(0.9)),
        )
    )
    reciprocal["interpretation"] = "descriptive identity; not independent exponent validation"

    same_area = frame[frame.area_bin.astype(str).eq("16-64") & frame.partition.eq("held_out")]
    selected = []
    for label, quantile in (("low coupling", 0.1), ("high coupling", 0.9)):
        target_k = same_area.effective_coupling.quantile(quantile)
        target_area = same_area.start_area_km2.median()
        scale = max(float(same_area.start_area_km2.std()), 1e-12)
        score = (
            np.abs(same_area.effective_coupling - target_k)
            / max(float(same_area.effective_coupling.std()), 1e-12)
            + 0.25 * np.abs(same_area.start_area_km2 - target_area) / scale
        )
        row = same_area.loc[score.idxmin()].copy()
        row["example_class"] = label
        selected.append(row)
    examples = pd.DataFrame(selected)
    return summary, reciprocal, examples


def merge_targets(features: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    return targets.merge(
        features,
        on=["id", "snapshot_day"],
        how="left",
        validate="many_to_one",
    )


def fire_size_transfer(frame: pd.DataFrame, replicates: int) -> pd.DataFrame:
    """Compare normalized-coupling and raw-growth transfer across origin sizes."""
    rows = []
    feature_columns = COUPLING_GEOMETRY_PREDICTORS
    for snapshot, source in frame[frame.lead_days.eq(1)].groupby("snapshot_day"):
        development = source[source.partition.eq("development")].copy()
        calibration = source[source.partition.eq("calibration")].copy()
        held_out = source[source.partition.eq("held_out")].copy()
        threshold = float(development.snapshot_area_km2.median())
        for train_label, test_label, train_mask, calibration_mask, test_mask in (
            ("small", "large", development.snapshot_area_km2 <= threshold, calibration.snapshot_area_km2 <= threshold, held_out.snapshot_area_km2 > threshold),
            ("large", "small", development.snapshot_area_km2 > threshold, calibration.snapshot_area_km2 > threshold, held_out.snapshot_area_km2 <= threshold),
        ):
            train = development[train_mask].copy()
            tune = calibration[calibration_mask].copy()
            test = held_out[test_mask].copy()
            if min(train.id.nunique(), tune.id.nunique(), test.id.nunique()) < 40:
                continue
            for formulation, target in (
                ("normalized_coupling", "log1p_future_effective_coupling"),
                ("raw_growth", "log1p_future_growth"),
            ):
                for subset in (train, tune, test):
                    subset["log1p_future_growth"] = np.log1p(subset.future_growth_km2)
                model, curve = tune_ridge_alpha(
                    train,
                    tune,
                    target_column=target,
                    feature_columns=feature_columns,
                )
                prediction = model.predict(test)
                if formulation == "normalized_coupling":
                    predicted_growth = np.maximum(np.expm1(prediction), 0.0) * test.snapshot_area_km2.to_numpy(dtype=float) ** DEFAULT_SIGMA
                else:
                    predicted_growth = np.maximum(np.expm1(prediction), 0.0)
                error = np.abs(np.log1p(predicted_growth) - np.log1p(test.future_growth_km2.to_numpy(dtype=float)))
                event_error = pd.DataFrame({"id": test.id.to_numpy(), "error": error}).groupby("id").error.mean().to_numpy()
                lower, upper = bootstrap_mean_ci(
                    event_error,
                    seed=DEFAULT_SEED + int(snapshot) * 100 + len(train_label) + len(formulation),
                    replicates=replicates,
                )
                rows.append({
                    "snapshot_day": int(snapshot),
                    "train_origin_size": train_label,
                    "test_origin_size": test_label,
                    "development_size_threshold_km2": threshold,
                    "formulation": formulation,
                    "n_development_events": int(train.id.nunique()),
                    "n_calibration_events": int(tune.id.nunique()),
                    "n_held_out_events": int(test.id.nunique()),
                    "selected_alpha": float(curve.loc[curve.selected, "alpha"].iloc[0]),
                    "mean_absolute_log1p_growth_error": float(error.mean()),
                    "event_weighted_error": float(event_error.mean()),
                    "event_weighted_ci95_lower": lower,
                    "event_weighted_ci95_upper": upper,
                })
    result = pd.DataFrame(rows)
    if not result.empty:
        raw = result[result.formulation.eq("raw_growth")][
            ["snapshot_day", "train_origin_size", "test_origin_size", "event_weighted_error"]
        ].rename(columns={"event_weighted_error": "raw_growth_event_weighted_error"})
        result = result.merge(raw, on=["snapshot_day", "train_origin_size", "test_origin_size"], how="left")
        result["error_difference_vs_raw_growth"] = result.event_weighted_error - result.raw_growth_event_weighted_error
    return result


def fit_coupling_hierarchy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    specifications = {
        "coupling_history": COUPLING_HISTORY_PREDICTORS,
        "coupling_area_dynamics": COUPLING_DYNAMICS_PREDICTORS,
        "coupling_geometry": COUPLING_GEOMETRY_PREDICTORS,
    }
    model_sets = {
        name: fit_lead_coupling_models(
            frame,
            model_name=name,
            feature_columns=columns,
            leads=frame.lead_days.unique(),
        )
        for name, columns in specifications.items()
    }
    predictions = predict_coupling(frame, model_sets)
    tuning = [model.tuning for model in model_sets.values()]

    expanded, columns = fixed_quadratic_coupling_frame(frame)
    flexible_set = fit_lead_coupling_models(
        expanded,
        model_name="coupling_geometry_flexible",
        feature_columns=columns,
        leads=expanded.lead_days.unique(),
    )
    flexible = predict_coupling(
        expanded,
        {"coupling_geometry_flexible": flexible_set},
    )
    flexible = flexible[flexible.model.eq("coupling_geometry_flexible")]
    predictions = pd.concat([predictions, flexible], ignore_index=True)
    tuning.append(flexible_set.tuning)
    return predictions, pd.concat(tuning, ignore_index=True)


def coupling_metrics(predictions: pd.DataFrame, replicates: int) -> pd.DataFrame:
    rows = []
    held = predictions[predictions.partition.eq("held_out")]
    for keys, group in held.groupby(["snapshot_day", "lead_days", "model"], sort=False):
        snapshot, lead, model = keys
        error = group.absolute_log1p_coupling_error.to_numpy(dtype=float)
        lower, upper = bootstrap_mean_ci(
            error,
            seed=DEFAULT_SEED + int(snapshot) * 100 + int(lead),
            replicates=replicates,
        )
        correlation = spearmanr(
            group.future_effective_coupling,
            group.predicted_effective_coupling,
        ).statistic
        rows.append(
            {
                "snapshot_day": int(snapshot),
                "lead_days": int(lead),
                "model": model,
                "n_events": int(group.id.nunique()),
                "n_event_days": int(len(group)),
                "mean_absolute_log1p_error": float(error.mean()),
                "mae_ci95_lower": lower,
                "mae_ci95_upper": upper,
                "mean_absolute_raw_error": float(group.absolute_coupling_error.mean()),
                "spearman_correlation": float(correlation),
                "target_active_fraction": float((group.future_effective_coupling > 0).mean()),
            }
        )
    return pd.DataFrame(rows)


def coupling_comparisons(predictions: pd.DataFrame, replicates: int) -> pd.DataFrame:
    rows = []
    held = predictions[predictions.partition.eq("held_out")]
    comparisons = (
        ("coupling_geometry", "coupling_persistence"),
        ("coupling_geometry", "coupling_history"),
        ("coupling_geometry", "coupling_area_dynamics"),
        ("coupling_geometry_flexible", "coupling_geometry"),
    )
    for (snapshot, lead), group in held.groupby(["snapshot_day", "lead_days"]):
        pivot = group.pivot(index="id", columns="model", values="absolute_log1p_coupling_error").reset_index()
        for first, second in comparisons:
            if {first, second}.issubset(pivot.columns):
                result = paired_event_bootstrap(
                    pivot,
                    first_error=first,
                    second_error=second,
                    replicates=replicates,
                    seed=DEFAULT_SEED + int(snapshot) * 1000 + int(lead),
                )
                rows.append(
                    {
                        "snapshot_day": int(snapshot),
                        "lead_days": int(lead),
                        "first_model": first,
                        "second_model": second,
                        **result,
                    }
                )
    return pd.DataFrame(rows)


def direct_area_predictions(
    features: pd.DataFrame,
    sequences: pd.DataFrame,
    targets: pd.DataFrame,
    horizons: tuple[int, ...],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    tuning_rows = []
    for snapshot in sorted(features.snapshot_day.unique()):
        origin = features[features.snapshot_day.eq(snapshot)].copy()
        for horizon in horizons:
            target = targets[targets.lead_days.eq(horizon)][
                ["id", "snapshot_day", "future_area_km2"]
            ]
            data = origin.merge(target, on=["id", "snapshot_day"], validate="one_to_one")
            data["log_future_area"] = np.log(data.future_area_km2)
            data["horizon_days"] = horizon
            development = data[data.partition.eq("development")]
            calibration = data[data.partition.eq("calibration")]
            held = data[data.partition.eq("held_out")]
            if len(held) < MIN_PRIMARY_HELDOUT:
                continue

            def append(model: str, prediction: np.ndarray) -> None:
                part = held[["id", "ig_year", "snapshot_day", "snapshot_area_km2", "future_area_km2"]].copy()
                part["horizon_days"] = horizon
                part["model"] = model
                part["predicted_area_km2"] = np.maximum(prediction, part.snapshot_area_km2)
                rows.append(part)

            append("no_growth", held.snapshot_area_km2.to_numpy(dtype=float))
            recent_daily = np.expm1(held.log_recent_growth.to_numpy(dtype=float)) / 3.0
            append("recent_linear", held.snapshot_area_km2.to_numpy(dtype=float) + horizon * recent_daily)
            for name, sigma in (("half_power", 0.5), ("two_thirds", DEFAULT_SIGMA)):
                append(name, transformed_forecasts(held, sequences, sigma=sigma))
            for name, columns in (
                ("dynamics_ridge", DYNAMICS_PREDICTORS),
                ("geometry_proxy", AREA_GEOMETRY_PREDICTORS),
            ):
                model, curve = tune_ridge_alpha(
                    development,
                    calibration,
                    target_column="log_future_area",
                    feature_columns=columns,
                )
                curve["snapshot_day"] = snapshot
                curve["horizon_days"] = horizon
                curve["model"] = name
                tuning_rows.append(curve)
                append(name, np.exp(model.predict(held)))
    result = pd.concat(rows, ignore_index=True)
    result["signed_log_error"] = np.log(result.predicted_area_km2 / result.future_area_km2)
    result["absolute_log_error"] = result.signed_log_error.abs()
    return result, pd.concat(tuning_rows, ignore_index=True)


def area_metrics(predictions: pd.DataFrame, replicates: int) -> pd.DataFrame:
    rows = []
    for keys, group in predictions.groupby(["snapshot_day", "horizon_days", "model"], sort=False):
        snapshot, horizon, model = keys
        metrics = regression_metrics(group.future_area_km2, group.predicted_area_km2)
        lower, upper = bootstrap_mean_ci(
            group.absolute_log_error.to_numpy(dtype=float),
            seed=DEFAULT_SEED + int(snapshot) * 100 + int(horizon),
            replicates=replicates,
        )
        rows.append(
            {
                "snapshot_day": int(snapshot),
                "horizon_days": int(horizon),
                "model": model,
                "n_events": int(group.id.nunique()),
                "n_event_days": int(len(group)),
                **metrics,
                "absolute_log_error_ci95_lower": lower,
                "absolute_log_error_ci95_upper": upper,
            }
        )
    return pd.DataFrame(rows)


def structured_area_outputs(
    coupling_predictions: pd.DataFrame,
    horizons: tuple[int, ...],
) -> pd.DataFrame:
    recursive = recursive_area_forecasts(coupling_predictions)
    model_map = {
        "coupling_persistence": "structured_k_persistence",
        "coupling_history": "structured_k_history",
        "coupling_area_dynamics": "structured_k_dynamics",
        "coupling_geometry": "structured_k_geometry",
        "coupling_geometry_flexible": "structured_k_flexible",
    }
    recursive["model"] = recursive.model.map(model_map)
    return recursive[
        recursive.partition.eq("held_out") & recursive.lead_days.isin(horizons)
    ].rename(columns={"lead_days": "horizon_days"})


def structured_direct_comparisons(
    combined: pd.DataFrame,
    replicates: int,
) -> pd.DataFrame:
    rows = []
    for (snapshot, horizon), group in combined.groupby(["snapshot_day", "horizon_days"]):
        pivot = group.pivot(index="id", columns="model", values="absolute_log_error").reset_index()
        for first in ("structured_k_geometry", "structured_k_flexible"):
            if {first, "geometry_proxy"}.issubset(pivot.columns):
                result = paired_event_bootstrap(
                    pivot,
                    first_error=first,
                    second_error="geometry_proxy",
                    replicates=replicates,
                    seed=DEFAULT_SEED + int(snapshot) * 1000 + int(horizon),
                )
                rows.append(
                    {
                        "snapshot_day": int(snapshot),
                        "horizon_days": int(horizon),
                        "first_model": first,
                        "second_model": "geometry_proxy",
                        **result,
                    }
                )
    return pd.DataFrame(rows)


def acceleration_targets(features: pd.DataFrame, sequences: pd.DataFrame, windows: tuple[int, ...]) -> pd.DataFrame:
    lookup = {int(i): g.sort_values("event_day") for i, g in sequences.groupby("id", sort=False)}
    rows = []
    for origin in features.itertuples(index=False):
        event = lookup[int(origin.id)]
        daily = event.daily_area_km2.to_numpy(dtype=float)
        snapshot = int(origin.snapshot_day)
        past = daily[max(0, snapshot - 3):snapshot]
        for window in windows:
            future = np.zeros(window, dtype=float)
            available = daily[snapshot:min(len(daily), snapshot + window)]
            future[: len(available)] = available
            rows.append(
                {
                    "id": int(origin.id),
                    "snapshot_day": snapshot,
                    "window_days": window,
                    "past_mean_growth": float(past.mean()),
                    "future_mean_growth": float(future.mean()),
                    "future_accelerating": bool(future.mean() > past.mean()),
                }
            )
    return pd.DataFrame(rows)


def _binary_metric_with_ci(group: pd.DataFrame, replicates: int, seed: int) -> dict[str, float]:
    scores = binary_metrics(group.future_accelerating, group.predicted)
    generator = np.random.default_rng(seed)
    draws = []
    for _ in range(replicates):
        sample = group.iloc[generator.integers(0, len(group), len(group))]
        draws.append(binary_metrics(sample.future_accelerating, sample.predicted)["balanced_accuracy"])
    scores["balanced_accuracy_ci95_lower"] = float(np.nanquantile(draws, 0.025))
    scores["balanced_accuracy_ci95_upper"] = float(np.nanquantile(draws, 0.975))
    if "probability" in group:
        scores["brier_score"] = float(np.mean((group.probability - group.future_accelerating.astype(float)) ** 2))
    else:
        scores["brier_score"] = np.nan
    return scores


def acceleration_analysis(
    features: pd.DataFrame,
    targets: pd.DataFrame,
    recursive_all: pd.DataFrame,
    replicates: int,
) -> pd.DataFrame:
    rows = []
    for (snapshot, window), target in targets.groupby(["snapshot_day", "window_days"]):
        data = features[features.snapshot_day.eq(snapshot)].merge(
            target,
            on=["id", "snapshot_day"],
            validate="one_to_one",
        )
        development = data[data.partition.eq("development")]
        calibration = data[data.partition.eq("calibration")]
        held = data[data.partition.eq("held_out")]
        if len(held) < MIN_PRIMARY_HELDOUT:
            continue
        for name, columns in (
            ("dynamics_ridge", DYNAMICS_PREDICTORS),
            ("geometry_proxy", AREA_GEOMETRY_PREDICTORS),
        ):
            model, threshold, _ = tune_binary_model(
                development,
                calibration,
                target_column="future_accelerating",
                feature_columns=columns,
            )
            probability = model.predict_hazard(held)
            result = held[["id", "future_accelerating"]].copy()
            result["probability"] = probability
            result["predicted"] = probability >= threshold
            scores = _binary_metric_with_ci(
                result,
                replicates,
                DEFAULT_SEED + int(snapshot) * 100 + int(window),
            )
            rows.append({"snapshot_day": snapshot, "window_days": window, "model": name, "n_events": len(result), **scores})

        trajectory = recursive_all[
            recursive_all.snapshot_day.eq(snapshot)
            & recursive_all.lead_days.eq(window)
            & recursive_all.model.eq("coupling_geometry")
        ][["id", "partition", "origin_area_km2", "predicted_area_km2"]]
        structured = data[["id", "partition", "future_accelerating", "past_mean_growth"]].merge(
            trajectory,
            on=["id", "partition"],
            validate="one_to_one",
        )
        structured["structured_score"] = (
            (structured.predicted_area_km2 - structured.origin_area_km2) / window
            - structured.past_mean_growth
        )
        dev = structured[structured.partition.eq("development")].copy()
        cal = structured[structured.partition.eq("calibration")].copy()
        test = structured[structured.partition.eq("held_out")].copy()
        train = dev.rename(columns={"future_accelerating": "terminal_transition"})
        calibrator = fit_logistic_hazard(train, feature_columns=("structured_score",), alpha=1.0)
        cal_probability = calibrator.predict_hazard(cal)
        threshold_scores = []
        for threshold in np.linspace(0.1, 0.9, 33):
            score = binary_metrics(cal.future_accelerating, cal_probability >= threshold)["balanced_accuracy"]
            threshold_scores.append((score, threshold))
        threshold = max(threshold_scores)[1]
        test["probability"] = calibrator.predict_hazard(test)
        test["predicted"] = test.probability >= threshold
        scores = _binary_metric_with_ci(
            test,
            replicates,
            DEFAULT_SEED + int(snapshot) * 1000 + int(window),
        )
        rows.append({"snapshot_day": snapshot, "window_days": window, "model": "structured_k_geometry", "n_events": len(test), **scores})
    return pd.DataFrame(rows)


def coupling_memory(coupling: pd.DataFrame, replicates: int, max_lag: int = 21) -> pd.DataFrame:
    event_rows = []
    for event_id, event in coupling.groupby("id"):
        values = event.sort_values("event_day").log1p_effective_coupling.to_numpy(dtype=float)
        for lag in range(1, max_lag + 1):
            if len(values) - lag < 5:
                continue
            left, right = values[:-lag], values[lag:]
            if np.std(left) < 1e-12 or np.std(right) < 1e-12:
                continue
            event_rows.append({"id": int(event_id), "lag_days": lag, "correlation": float(np.corrcoef(left, right)[0, 1]), "n_pairs": len(left)})
    events = pd.DataFrame(event_rows)
    rows = []
    for lag, group in events.groupby("lag_days"):
        lower, upper = bootstrap_mean_ci(
            group.correlation.to_numpy(dtype=float),
            seed=DEFAULT_SEED + int(lag),
            replicates=replicates,
        )
        rows.append({"lag_days": int(lag), "n_events": int(group.id.nunique()), "n_event_pairs": int(group.n_pairs.sum()), "mean_within_fire_correlation": float(group.correlation.mean()), "median_within_fire_correlation": float(group.correlation.median()), "ci95_lower": lower, "ci95_upper": upper})
    return pd.DataFrame(rows)


def variance_decomposition(coupling: pd.DataFrame) -> pd.DataFrame:
    active = coupling[coupling.effective_coupling > 0].copy()
    active["stage"] = pd.cut(active.life_fraction, [0, 0.25, 0.5, 0.75, 1.01], labels=("early", "middle", "late", "terminal"), include_lowest=True)
    active["log_growth"] = np.log(active.daily_growth_km2)
    active["log_scale"] = DEFAULT_SIGMA * np.log(active.start_area_km2)
    active["log_coupling"] = np.log(active.effective_coupling)
    rows = []
    for scope, groups in (
        ("across event-days", active.groupby("stage", observed=True)),
        ("within-fire mean", active.groupby(["id", "stage"], observed=True)),
    ):
        local = []
        for key, group in groups:
            if len(group) < 3:
                continue
            stage = key[1] if isinstance(key, tuple) else key
            local.append({"stage": str(stage), "growth_variance": float(group.log_growth.var()), "scale_variance": float(group.log_scale.var()), "coupling_variance": float(group.log_coupling.var()), "twice_covariance": float(2 * group[["log_scale", "log_coupling"]].cov().iloc[0, 1])})
        local_frame = pd.DataFrame(local)
        if scope == "within-fire mean":
            local_frame = local_frame.groupby("stage", as_index=False).mean(numeric_only=True)
        local_frame["scope"] = scope
        rows.append(local_frame)
    return pd.concat(rows, ignore_index=True)


def normalization_comparison(
    base_features: pd.DataFrame,
    sequences: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for sigma in SIGMA_CANDIDATES:
        observations = coupling_observations(sequences, sigma=sigma)
        features = add_coupling_history_features(base_features, observations)
        targets = future_coupling_targets(features, sequences, leads=range(1, 8), sigma=sigma)
        frame = merge_targets(features, targets)
        model_set = fit_lead_coupling_models(frame, model_name="coupling_geometry", feature_columns=COUPLING_GEOMETRY_PREDICTORS, leads=range(1, 8))
        predictions = predict_coupling(frame, {"coupling_geometry": model_set})
        recursive = recursive_area_forecasts(predictions, sigma=sigma)
        for part in ("calibration", "held_out"):
            group = recursive[
                recursive.partition.eq(part)
                & recursive.model.eq("coupling_geometry")
                & recursive.lead_days.eq(7)
            ]
            rows.append({"sigma": sigma, "partition": part, "n_events": int(group.id.nunique()), "mean_absolute_log_error": float(group.absolute_log_error.mean())})
    result = pd.DataFrame(rows)
    calibration = result[result.partition.eq("calibration")]
    selected = float(calibration.loc[calibration.mean_absolute_log_error.idxmin(), "sigma"])
    result["selected_on_calibration"] = result.sigma.eq(selected)
    return result


def residual_diagnostics(predictions: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    data = predictions.merge(
        features[["id", "snapshot_day", "log_snapshot_area", "log_exterior_perimeter", "log_exterior_excess_perimeter", "log_component_count", "log1p_hole_count", "log_recent_growth"]],
        on=["id", "snapshot_day"],
        how="left",
        validate="many_to_one",
    )
    variables = ("log_snapshot_area", "log_exterior_perimeter", "log_exterior_excess_perimeter", "log_component_count", "log1p_hole_count", "log_recent_growth", "snapshot_day", "horizon_days")
    rows = []
    for model in ("structured_k_geometry", "geometry_proxy"):
        group = data[data.model.eq(model)]
        for variable in variables:
            correlation = spearmanr(group[variable], group.signed_log_error)
            rows.append({"model": model, "variable": variable, "n": len(group), "spearman_correlation": float(correlation.statistic), "p_value_descriptive": float(correlation.pvalue)})
    return pd.DataFrame(rows)


def select_long_cases(sequences: pd.DataFrame, comparisons: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    event = sequences.groupby("id", as_index=False).agg(ig_year=("ig_year", "first"), duration_days=("event_day", "max"), final_area_km2=("cumulative_area_km2", "last"))
    held = event[event.ig_year.ge(2016) & event.duration_days.ge(30)].copy()
    if len(held) < 3:
        held = event[event.ig_year.ge(2016)].nlargest(min(10, int((event.ig_year.ge(2016)).sum())), "duration_days")
    trajectory_ids = []
    for quantile in (0.2, 0.5, 0.8):
        target = held.duration_days.quantile(quantile)
        candidates = held[~held.id.isin(trajectory_ids)]
        trajectory_ids.append(int(candidates.loc[(candidates.duration_days - target).abs().idxmin(), "id"]))
    trajectories = held[held.id.isin(trajectory_ids)].copy()

    long_comparison = comparisons[comparisons.id.isin(held.id)].copy()
    improvement = long_comparison.groupby("id", as_index=False).improvement.mean()
    cases = []
    for label, quantile in (("structured failure", 0.2), ("structured success", 0.8)):
        target = improvement.improvement.quantile(quantile)
        row = improvement.loc[(improvement.improvement - target).abs().idxmin()].copy()
        row["case_class"] = label
        cases.append(row)
    return trajectories, pd.DataFrame(cases)


def _style() -> None:
    mpl.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 11.5, "axes.labelsize": 10.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.48, "grid.color": "#D9DADD", "legend.frameon": False, "pdf.fonttype": 42, "svg.fonttype": "none", "svg.hashsalt": "effective-coupling-validation"})


def save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    for suffix in ("pdf", "svg", "png"):
        metadata = {"Date": None} if suffix == "svg" else None
        fig.savefig(output_dir / f"{stem}.{suffix}", dpi=500 if suffix == "png" else None, bbox_inches="tight", facecolor="white", metadata=metadata)
    plt.close(fig)


def make_main_figure(
    coupling: pd.DataFrame,
    descriptive: pd.DataFrame,
    metrics: pd.DataFrame,
    comparisons: pd.DataFrame,
    acceleration: pd.DataFrame,
    output_dir: Path,
) -> None:
    _style()
    fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.4), constrained_layout=True)
    axis = axes[0, 0]
    display = coupling[(coupling.start_area_km2 > 0) & (coupling.effective_coupling > 0)]
    axis.hexbin(display.start_area_km2, display.effective_coupling, xscale="log", yscale="log", gridsize=42, mincnt=1, cmap="magma_r", bins="log", alpha=0.8)
    centers = np.sqrt(np.asarray(AREA_BIN_EDGES[:-2]) * np.asarray(AREA_BIN_EDGES[1:-1]))
    finite = descriptive.iloc[:-1]
    axis.plot(centers, finite.median_effective_coupling, color=COLORS["teal"], marker="o", lw=2.4, label="Median")
    axis.fill_between(centers, finite.q10_effective_coupling, finite.q90_effective_coupling, color=COLORS["teal"], alpha=0.15, label="10th-90th percentile")
    axis.set_xlabel(r"Start-of-day mapped area (km$^2$)")
    axis.set_ylabel(r"Effective coupling $K_{obs}$")
    axis.set_title("A  Scale does not determine normalized growth", loc="left", fontweight="bold")
    axis.legend(loc="lower left")

    axis = axes[0, 1]
    day7 = metrics[metrics.snapshot_day.eq(7) & metrics.lead_days.isin((1, 3, 5, 7))]
    model_style = {"coupling_persistence": (COLORS["gray"], "Persistence"), "coupling_history": (COLORS["purple"], "K history"), "coupling_area_dynamics": (COLORS["blue"], "Area + K dynamics"), "coupling_geometry": (COLORS["teal"], "Geometry-informed K")}
    for model, (color, label) in model_style.items():
        group = day7[day7.model.eq(model)].sort_values("lead_days")
        axis.plot(group.lead_days, group.mean_absolute_log1p_error, marker="o", color=color, lw=2.2, label=label)
        axis.fill_between(group.lead_days, group.mae_ci95_lower, group.mae_ci95_upper, color=color, alpha=0.10)
    axis.set_xticks((1, 3, 5, 7))
    axis.set_xlabel("Lead time (days)")
    axis.set_ylabel("Future-K mean absolute log1p error")
    axis.set_title("B  Can geometry predict future coupling?", loc="left", fontweight="bold")
    axis.legend(fontsize=8)

    axis = axes[1, 0]
    paired = comparisons[comparisons.snapshot_day.eq(7) & comparisons.horizon_days.isin((1, 3, 5, 7)) & comparisons.first_model.eq("structured_k_geometry")]
    values = paired.mean_difference.to_numpy(dtype=float)
    lower = values - paired.ci95_lower.to_numpy(dtype=float)
    upper = paired.ci95_upper.to_numpy(dtype=float) - values
    axis.axhline(0, color=COLORS["gray"], lw=1.2)
    axis.errorbar(paired.horizon_days, values, yerr=[lower, upper], color=COLORS["teal"], marker="o", lw=2.2, capsize=4)
    axis.set_xticks((1, 3, 5, 7))
    axis.set_xlabel("Forecast horizon (days)")
    axis.set_ylabel("Structured error - direct geometry error")
    axis.set_title("C  Does the decomposition improve area forecasts?", loc="left", fontweight="bold")
    axis.text(0.98, 0.06, "Negative favors structured K", transform=axis.transAxes, ha="right", color=COLORS["teal"], fontsize=8.5)

    axis = axes[1, 1]
    acc = acceleration[acceleration.snapshot_day.eq(7) & acceleration.window_days.eq(3)].set_index("model").reindex(("dynamics_ridge", "geometry_proxy", "structured_k_geometry"))
    positions = np.arange(len(acc))
    values = acc.balanced_accuracy.to_numpy(dtype=float)
    lower = values - acc.balanced_accuracy_ci95_lower.to_numpy(dtype=float)
    upper = acc.balanced_accuracy_ci95_upper.to_numpy(dtype=float) - values
    axis.bar(positions, values, color=(COLORS["purple"], COLORS["blue"], COLORS["teal"]), width=0.68)
    axis.errorbar(positions, values, yerr=[lower, upper], fmt="none", color=COLORS["ink"], capsize=4)
    axis.axhline(0.5, color=COLORS["red"], ls="--", lw=1.4)
    axis.set_xticks(positions, ("Dynamics", "Direct geometry", "Structured K"), rotation=16, ha="right")
    axis.set_ylabel("Balanced accuracy")
    axis.set_ylim(0.48, max(0.86, float(np.nanmax(values + upper) + 0.03)))
    axis.set_title("D  Does predicted coupling anticipate acceleration?", loc="left", fontweight="bold")
    fig.suptitle("Predicting a time-varying effective coupling", fontsize=15.5, fontweight="bold")
    fig.text(0.5, -0.012, "K is a normalized mapped-growth coefficient, not an independently observed latent mechanism.", ha="center", color=COLORS["gray"], fontsize=9)
    save_figure(fig, output_dir, "figure1_effective_coupling_validation")


def make_long_figure(
    all_area_metrics: pd.DataFrame,
    coupling_metrics_frame: pd.DataFrame,
    coupling: pd.DataFrame,
    sequences: pd.DataFrame,
    recursive: pd.DataFrame,
    direct: pd.DataFrame,
    trajectories: pd.DataFrame,
    cases: pd.DataFrame,
    output_dir: Path,
) -> None:
    _style()
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.6), constrained_layout=True)
    axis = axes[0, 0]
    styles = {"recent_linear": (COLORS["gray"], "Recent growth"), "half_power": (COLORS["red"], r"$A^{1/2}$"), "two_thirds": (COLORS["blue"], r"fixed $A^{2/3}$"), "geometry_proxy": (COLORS["purple"], "Direct geometry"), "structured_k_geometry": (COLORS["teal"], "Structured K")}
    day7 = all_area_metrics[all_area_metrics.snapshot_day.eq(7)]
    for model, (color, label) in styles.items():
        group = day7[day7.model.eq(model)].sort_values("horizon_days")
        axis.plot(group.horizon_days, group.mean_absolute_log_error, marker="o", ms=3.5, color=color, lw=2.1, label=label)
    axis.set_xlabel("Lead time (days)")
    axis.set_ylabel("Mean absolute log area error")
    axis.set_title("A  Fixed-origin skill decay", loc="left", fontweight="bold")
    axis.legend(fontsize=7.8, ncol=2)

    axis = axes[0, 1]
    day7k = coupling_metrics_frame[coupling_metrics_frame.snapshot_day.eq(7)]
    for model, (color, label) in {"coupling_persistence": (COLORS["gray"], "Persistence"), "coupling_history": (COLORS["purple"], "K history"), "coupling_area_dynamics": (COLORS["blue"], "Dynamics"), "coupling_geometry": (COLORS["teal"], "Geometry")}.items():
        group = day7k[day7k.model.eq(model)].sort_values("lead_days")
        axis.plot(group.lead_days, group.mean_absolute_log1p_error, marker="o", ms=3.5, color=color, lw=2.1, label=label)
    axis.set_xlabel("Lead time (days)")
    axis.set_ylabel("Future-K mean absolute log1p error")
    axis.set_title("B  Effective-coupling predictability", loc="left", fontweight="bold")
    axis.legend(fontsize=8, ncol=2)

    axis = axes[1, 0]
    cmap = mpl.colormaps["viridis"]
    for row in trajectories.itertuples(index=False):
        event = coupling[coupling.id.eq(row.id) & coupling.effective_coupling.gt(0)].sort_values("event_day")
        axis.scatter(event.start_area_km2, event.effective_coupling, c=event.life_fraction, cmap=cmap, s=18, alpha=0.75)
        axis.plot(event.start_area_km2, event.effective_coupling, color=COLORS["gray"], alpha=0.35, lw=0.8, label=f"Event {int(row.id)}")
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel(r"Mapped area (km$^2$)")
    axis.set_ylabel(r"Effective coupling $K_{obs}$")
    axis.set_title("C  Persistent-fire trajectories in A-K space", loc="left", fontweight="bold")
    axis.legend(fontsize=7)
    norm = mpl.colors.Normalize(0, 1)
    colorbar = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axis, fraction=0.045, pad=0.02)
    colorbar.set_label("Observed life fraction")

    axis = axes[1, 1]
    for index, case in enumerate(cases.itertuples(index=False)):
        event = sequences[sequences.id.eq(case.id)].sort_values("event_day")
        origin_area = float(event.loc[event.event_day.eq(7), "cumulative_area_km2"].iloc[0])
        observed = event[event.event_day.ge(7) & event.event_day.le(56)]
        rec = recursive[recursive.id.eq(case.id) & recursive.snapshot_day.eq(7) & recursive.model.eq("coupling_geometry") & recursive.lead_days.le(49)]
        direct_event = direct[direct.id.eq(case.id) & direct.snapshot_day.eq(7) & direct.model.eq("geometry_proxy")]
        linestyle = "-" if index == 0 else "--"
        label = case.case_class
        axis.plot(observed.event_day, observed.cumulative_area_km2 / origin_area, color=COLORS["ink"], ls=linestyle, lw=2.0, label=f"Observed: {label}")
        axis.plot(7 + rec.lead_days, rec.predicted_area_km2 / origin_area, color=COLORS["teal"], ls=linestyle, lw=2.0, label=f"Structured K: {label}")
        axis.plot(7 + direct_event.horizon_days, direct_event.predicted_area_km2 / origin_area, color=COLORS["purple"], ls=linestyle, lw=1.6, marker="o", ms=3, label=f"Direct: {label}")
    axis.axvline(7, color=COLORS["gray"], ls=":")
    axis.set_yscale("log")
    axis.set_xlabel("Event day")
    axis.set_ylabel("Area / day-7 area")
    axis.set_title("D  Long-fire success and failure", loc="left", fontweight="bold")
    axis.legend(fontsize=6.7, ncol=2)
    fig.suptitle("How long does early fire geometry remain predictive?", fontsize=15.5, fontweight="bold")
    fig.text(0.5, -0.012, "Primary curves include post-terminal plateaus; persistent-fire panels are retrospective descriptions.", ha="center", color=COLORS["gray"], fontsize=9)
    save_figure(fig, output_dir, "figure2_long_horizon_coupling")


def main() -> int:
    args = parse_args()
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    for path in (args.sequences, args.geometry, args.features):
        if not path.is_file():
            raise FileNotFoundError(path)

    sequences = pd.read_csv(args.sequences, parse_dates=["date"])
    geometry = pd.read_csv(args.geometry)
    features = pd.read_csv(args.features)
    if args.smoke:
        sequences = deterministic_subset(sequences)
        ids = set(sequences.id)
        geometry = geometry[geometry.id.isin(ids)]
        features = features[features.id.isin(ids)]
    merged = merge_geometry_sequences(sequences, geometry)
    replicates = 100 if args.smoke else BOOTSTRAP_REPLICATES
    horizons = (1, 3, 7) if args.smoke else HORIZONS
    all_leads = tuple(range(1, max(horizons) + 1))

    design = {
        "mode": "smoke" if args.smoke else "full",
        "random_seed": DEFAULT_SEED,
        "sigma_primary": DEFAULT_SIGMA,
        "sigma_candidates": list(SIGMA_CANDIDATES),
        "development_years": [2001, 2012],
        "calibration_years": [2013, 2015],
        "held_out_years": [2016, 2020],
        "primary_origins": list(PRIMARY_ORIGINS),
        "updating_origins": list(UPDATING_ORIGINS),
        "forecast_horizons": list(horizons),
        "target_definition": "daily start-of-interval K; zero after mapped termination",
        "area_recursion": "predicted K and recursively predicted area only",
        "minimum_primary_heldout_events": MIN_PRIMARY_HELDOUT,
        "minimum_persistent_heldout_events": MIN_PERSISTENT_HELDOUT,
        "minimum_events_per_partition_at_origin": MIN_PARTITION_AT_ORIGIN,
        "geometry_predictability_horizon_rule": "largest consecutive calibration lead with >=2% MAE improvement over coupling persistence",
        "bootstrap_replicates": replicates,
        "predictor_policy": "locked origin-safe adversarial-validation whitelists",
        "input_checksums": {str(path): sha256(path) for path in (args.sequences, args.geometry, args.features)},
    }
    design_text = json.dumps(design, indent=2, sort_keys=True)
    (output / "design_lock.json").write_text(design_text + "\n", encoding="utf-8")
    design_hash = hashlib.sha256(design_text.encode()).hexdigest()

    coupling = coupling_observations(sequences)
    coupling.to_csv(output / "coupling_observations.csv.gz", index=False)
    descriptive, reciprocal, same_area_examples = descriptive_tables(coupling)
    descriptive.to_csv(output / "coupling_descriptive_summary.csv", index=False)
    reciprocal.to_csv(output / "coupling_reciprocal_summary.csv", index=False)
    same_area_examples.to_csv(output / "same_area_examples.csv", index=False)

    primary_features = features[features.snapshot_day.isin(PRIMARY_ORIGINS)].copy()
    primary_features = add_coupling_history_features(primary_features, coupling)
    targets = future_coupling_targets(primary_features, sequences, leads=all_leads)
    model_frame = merge_targets(primary_features, targets)
    transfer = fire_size_transfer(model_frame, replicates)
    transfer.to_csv(output / "fire_size_transfer.csv", index=False)

    prediction_path = output / "coupling_predictions.csv.gz"
    if args.reuse_primary and prediction_path.is_file():
        coupling_predictions = pd.read_csv(
            prediction_path,
            usecols=list(COUPLING_PREDICTION_COLUMNS),
        )
        coupling_predictions.to_csv(prediction_path, index=False)
    else:
        prediction_parts = []
        tuning_parts = []
        for snapshot in PRIMARY_ORIGINS:
            frame = model_frame[model_frame.snapshot_day.eq(snapshot)].copy()
            predictions, tuning = fit_coupling_hierarchy(frame)
            prediction_parts.append(predictions)
            tuning_parts.append(tuning.assign(snapshot_day=snapshot))
        coupling_predictions = pd.concat(prediction_parts, ignore_index=True)
        coupling_predictions.to_csv(prediction_path, index=False)
        pd.concat(tuning_parts, ignore_index=True).to_csv(output / "coupling_model_tuning.csv", index=False)
    coupling_metric_frame = coupling_metrics(coupling_predictions, replicates)
    coupling_metric_frame.to_csv(output / "coupling_forecast_metrics.csv", index=False)
    coupling_comparison_frame = coupling_comparisons(coupling_predictions, replicates)
    coupling_comparison_frame.to_csv(output / "coupling_paired_comparisons.csv", index=False)

    recursive_all = recursive_area_forecasts(coupling_predictions)
    structured = structured_area_outputs(coupling_predictions, horizons)
    direct, direct_tuning = direct_area_predictions(primary_features, sequences, targets, horizons)
    direct_tuning.to_csv(output / "direct_area_model_tuning.csv", index=False)
    combined_area = pd.concat([direct, structured], ignore_index=True)
    combined_area.to_csv(output / "held_out_area_predictions.csv.gz", index=False)
    area_metric_frame = area_metrics(combined_area, replicates)
    area_metric_frame.to_csv(output / "structured_area_forecast_metrics.csv", index=False)
    area_comparison_frame = structured_direct_comparisons(combined_area, replicates)
    area_comparison_frame.to_csv(output / "structured_vs_direct_comparisons.csv", index=False)

    acceleration_target_frame = acceleration_targets(primary_features, sequences, TRANSITION_WINDOWS if not args.smoke else (3,))
    acceleration = acceleration_analysis(primary_features, acceleration_target_frame, recursive_all, replicates)
    acceleration.to_csv(output / "coupling_acceleration_metrics.csv", index=False)

    normalization = normalization_comparison(features[features.snapshot_day.eq(7)].copy(), sequences)
    normalization.to_csv(output / "normalization_comparison.csv", index=False)
    selected_sigma = float(normalization.loc[normalization.selected_on_calibration, "sigma"].iloc[0])

    residuals = residual_diagnostics(combined_area, primary_features)
    residuals.to_csv(output / "residual_diagnostics.csv", index=False)
    memory = coupling_memory(coupling, replicates, max_lag=21)
    memory.to_csv(output / "coupling_memory.csv", index=False)
    variance = variance_decomposition(coupling)
    variance.to_csv(output / "coupling_variance_decomposition.csv", index=False)

    # Exact discrete acceleration decomposition is exported for auditability.
    decomposition_rows = []
    for event_id, event in coupling.groupby("id"):
        event = event.sort_values("event_day")
        if len(event) < 2:
            continue
        decomposition = exact_growth_change_decomposition(
            event.start_area_km2.to_numpy(dtype=float)[:-1],
            event.effective_coupling.to_numpy(dtype=float)[:-1],
            event.effective_coupling.to_numpy(dtype=float)[1:],
        )
        decomposition.insert(0, "id", int(event_id))
        decomposition.insert(1, "event_day", event.event_day.to_numpy(dtype=int)[1:])
        decomposition_rows.append(decomposition)
    pd.concat(decomposition_rows, ignore_index=True).to_csv(output / "acceleration_decomposition.csv.gz", index=False)

    # Persistent-fire conditional summaries retain only target-observable events.
    persistent = combined_area.merge(
        targets[["id", "snapshot_day", "lead_days", "observable_at_target"]],
        left_on=["id", "snapshot_day", "horizon_days"],
        right_on=["id", "snapshot_day", "lead_days"],
        how="left",
        validate="many_to_one",
    )
    persistent = persistent[persistent.observable_at_target]
    persistent_metrics = area_metrics(persistent, replicates)
    persistent_metrics = persistent_metrics[persistent_metrics.n_events.ge(MIN_PERSISTENT_HELDOUT)]
    persistent_metrics.to_csv(output / "persistent_fire_area_metrics.csv", index=False)

    # Calibration-locked geometry predictability horizon.
    calibration_metrics = []
    for (lead, model), group in coupling_predictions[coupling_predictions.partition.eq("calibration")].groupby(["lead_days", "model"]):
        calibration_metrics.append({"lead_days": lead, "model": model, "mae": float(group.absolute_log1p_coupling_error.mean())})
    calibration_metrics = pd.DataFrame(calibration_metrics)
    pivot = calibration_metrics.pivot(index="lead_days", columns="model", values="mae").sort_index()
    improvement = 1 - pivot.coupling_geometry / pivot.coupling_persistence
    eligible = []
    for lead in pivot.index:
        if improvement.loc[lead] >= 0.02 and (not eligible or lead == eligible[-1] + 1):
            eligible.append(int(lead))
        else:
            break
    predictability_horizon = max(eligible) if eligible else 0
    horizon_table = pd.DataFrame({"lead_days": pivot.index, "calibration_geometry_improvement_fraction": improvement.values, "within_locked_predictability_horizon": pivot.index <= predictability_horizon})
    horizon_table.to_csv(output / "coupling_predictability_horizon.csv", index=False)

    # Updating analysis: direct and structured geometry from later observed states.
    updating_parts = []
    if not args.smoke:
        for snapshot in UPDATING_ORIGINS:
            origin = features[features.snapshot_day.eq(snapshot)].copy()
            counts = origin.assign(partition=partition_years(origin.ig_year)).groupby("partition").id.nunique()
            if any(counts.get(part, 0) < MIN_PARTITION_AT_ORIGIN for part in ("development", "calibration", "held_out")):
                continue
            origin = add_coupling_history_features(origin, coupling)
            update_leads = range(1, 22)
            update_targets = future_coupling_targets(origin, sequences, leads=update_leads)
            update_frame = merge_targets(origin, update_targets)
            model_set = fit_lead_coupling_models(update_frame, model_name="coupling_geometry", feature_columns=COUPLING_GEOMETRY_PREDICTORS, leads=update_leads)
            update_prediction = predict_coupling(update_frame, {"coupling_geometry": model_set})
            update_recursive = structured_area_outputs(update_prediction, tuple(h for h in HORIZONS if h <= 21))
            update_direct, _ = direct_area_predictions(origin, sequences, update_targets, tuple(h for h in HORIZONS if h <= 21))
            update_combined = pd.concat([update_direct[update_direct.model.eq("geometry_proxy")], update_recursive[update_recursive.model.eq("structured_k_geometry")]], ignore_index=True)
            updating_parts.append(area_metrics(update_combined, replicates))
    updating_metrics = pd.concat(updating_parts, ignore_index=True) if updating_parts else pd.DataFrame()
    updating_metrics.to_csv(output / "updating_forecast_metrics.csv", index=False)

    # Reproducible long-fire examples.
    case_horizon = max(horizon for horizon in horizons if horizon <= 21)
    day7_compare = combined_area[combined_area.snapshot_day.eq(7) & combined_area.horizon_days.eq(case_horizon) & combined_area.model.isin(("geometry_proxy", "structured_k_geometry"))]
    case_pivot = day7_compare.pivot(index="id", columns="model", values="absolute_log_error").reset_index()
    case_pivot["improvement"] = case_pivot.geometry_proxy - case_pivot.structured_k_geometry
    trajectories, cases = select_long_cases(sequences, case_pivot)
    trajectories.to_csv(output / "persistent_trajectory_examples.csv", index=False)
    cases.to_csv(output / "long_fire_case_examples.csv", index=False)

    make_main_figure(coupling, descriptive, coupling_metric_frame, area_comparison_frame, acceleration, output)
    make_long_figure(area_metric_frame, coupling_metric_frame, coupling, sequences, recursive_all, direct, trajectories, cases, output)

    day7_h7 = area_comparison_frame[area_comparison_frame.snapshot_day.eq(7) & area_comparison_frame.horizon_days.eq(7) & area_comparison_frame.first_model.eq("structured_k_geometry")].iloc[0]
    long_rows = area_comparison_frame[area_comparison_frame.snapshot_day.eq(7) & area_comparison_frame.first_model.eq("structured_k_geometry")].sort_values("horizon_days")
    report = {
        "design_hash": design_hash,
        "counts": {"events": int(sequences.id.nunique()), "held_out_events": int(sequences.loc[sequences.ig_year.ge(2016), "id"].nunique()), "coupling_event_days": int(len(coupling)), "primary_predictions": int(len(combined_area))},
        "primary_results": {
            "selected_normalization_sigma": selected_sigma,
            "calibration_locked_geometry_K_predictability_horizon_days": predictability_horizon,
            "day7_horizon7_structured_minus_direct_error": float(day7_h7.mean_difference),
            "day7_horizon7_ci95": [float(day7_h7.ci95_lower), float(day7_h7.ci95_upper)],
            "day7_long_horizon_structured_minus_direct": {str(int(row.horizon_days)): float(row.mean_difference) for row in long_rows.itertuples(index=False)},
        },
        "interpretation_boundary": "K_obs is an observable normalized growth coefficient; C, F, beta0, active fireline, and energetic metabolism remain unidentified",
    }
    (output / "run_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
