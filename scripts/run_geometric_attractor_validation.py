#!/usr/bin/env python3
"""Adversarially test whether mapped wildfire geometry restores toward 2/3."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from fire_metabolism.fired_lifecycle import merge_geometry_sequences
from fire_metabolism.fired_outcomes import fit_standardized_ridge
from fire_metabolism.geometric_attractor import (
    DEFAULT_SEED,
    TWO_THIRDS,
    LinearAttractor,
    estimate_local_slopes,
    event_bootstrap_attractor,
    fit_fixed_attractor,
    fit_free_attractor,
    half_life_days,
    make_transitions,
    predict_future_sigma,
    within_fire_restoration,
)


LEADS = (1, 3, 5, 7, 10, 14, 21, 28, 35, 42, 49)
CANDIDATES = (
    "adjacent",
    "rolling_ols_5",
    "rolling_ols_7",
    "rolling_theil_sen_5",
)
COLORS = {
    "persistence": "#777777",
    "population_mean": "#D28B26",
    "half_attractor": "#B52A25",
    "two_thirds_attractor": "#6495ED",
    "free_attractor": "#2A8C5A",
    "flexible_dynamics": "#6F4C9B",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sequences", type=Path,
        default=Path("outputs/fired_prediction/fired_sequences.csv.gz"),
    )
    parser.add_argument(
        "--geometry", type=Path,
        default=Path("outputs/fired_lifecycle_prediction/fired_geometry_sequences.csv.gz"),
    )
    parser.add_argument(
        "--coupling", type=Path,
        default=Path("outputs/effective_coupling_validation/coupling_observations.csv.gz"),
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("outputs/geometric_attractor_validation"),
    )
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def partition(year: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [year <= 2012, year.between(2013, 2015), year >= 2016],
            ["development", "calibration", "held_out"],
            default="excluded",
        ), index=year.index,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def deterministic_subset(frame: pd.DataFrame, n: int = 100) -> pd.DataFrame:
    event_year = frame.groupby("id", as_index=False).ig_year.first()
    event_year["partition"] = partition(event_year.ig_year)
    ids: list[int] = []
    for _, group in event_year.groupby("partition", sort=False):
        ids.extend(group.sort_values("id").id.head(n).tolist())
    return frame[frame.id.isin(ids)].copy()


def estimator_selection(merged: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    estimates, rows = [], []
    for estimator in CANDIDATES:
        local = estimate_local_slopes(merged, estimator=estimator)
        local["partition"] = partition(local.ig_year)
        estimates.append(local)
        transitions = make_transitions(local, leads=(1,))
        transitions["partition"] = partition(transitions.ig_year)
        development = transitions[transitions.partition.eq("development")]
        calibration = transitions[transitions.partition.eq("calibration")]
        model = fit_free_attractor(development)
        prediction = predict_future_sigma(model, calibration.sigma)
        rows.append({
            "estimator": estimator,
            "development_events": int(development.id.nunique()),
            "calibration_events": int(calibration.id.nunique()),
            "calibration_transitions": int(len(calibration)),
            "calibration_mae": float(np.mean(np.abs(prediction - calibration.future_sigma))),
            "calibration_rmse": float(np.sqrt(np.mean((prediction - calibration.future_sigma) ** 2))),
            "median_sigma_se": float(local.sigma_se.median()),
        })
    tuning = pd.DataFrame(rows)
    adequate = tuning[tuning.calibration_events >= (20 if len(merged.id.unique()) < 1000 else 100)]
    selected = str(adequate.loc[adequate.calibration_mae.idxmin(), "estimator"])
    tuning["selected"] = tuning.estimator.eq(selected)
    all_estimates = pd.concat(estimates, ignore_index=True)
    return all_estimates, tuning, selected


def fit_flexible(train: pd.DataFrame, calibration: pd.DataFrame, features: list[str]):
    alphas = (0.1, 1.0, 10.0, 100.0)
    rows = []
    for alpha in alphas:
        model = fit_standardized_ridge(
            train, train.future_sigma, feature_columns=features, alpha=alpha
        )
        pred = model.predict(calibration)
        rows.append((float(np.mean(np.abs(pred - calibration.future_sigma))), alpha))
    alpha = min(rows)[1]
    combined = pd.concat([train, calibration], ignore_index=True)
    model = fit_standardized_ridge(
        combined, combined.future_sigma, feature_columns=features, alpha=alpha
    )
    return model, alpha


def prediction_analysis(transitions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prediction_rows, metric_rows, equilibrium_rows = [], [], []
    for lead, frame in transitions.groupby("lead_days"):
        dev = frame[frame.partition.eq("development")].copy()
        cal = frame[frame.partition.eq("calibration")].copy()
        held = frame[frame.partition.eq("held_out")].copy()
        if min(dev.id.nunique(), cal.id.nunique(), held.id.nunique()) < 20:
            continue
        training = pd.concat([dev, cal], ignore_index=True)
        population_center = float(dev.sigma.median())
        models: dict[str, LinearAttractor] = {
            "population_mean": fit_fixed_attractor(training, population_center),
            "half_attractor": fit_fixed_attractor(training, 0.5),
            "two_thirds_attractor": fit_fixed_attractor(training, TWO_THIRDS),
            "free_attractor": fit_free_attractor(training),
        }
        features = ["sigma", "origin_day", "log_area", "log1p_growth", "log1p_coupling"]
        flexible, alpha = fit_flexible(dev, cal, features)
        predictions = {"persistence": held.sigma.to_numpy(dtype=float)}
        predictions.update({name: predict_future_sigma(model, held.sigma) for name, model in models.items()})
        predictions["flexible_dynamics"] = flexible.predict(held)
        for name, values in predictions.items():
            part = held[["id", "ig_year", "origin_day", "lead_days", "sigma", "future_sigma"]].copy()
            part["model"] = name
            part["predicted_future_sigma"] = values
            part["absolute_error"] = np.abs(values - part.future_sigma)
            part["squared_error"] = (values - part.future_sigma) ** 2
            prediction_rows.append(part)
            metric_rows.append({
                "lead_days": int(lead), "model": name,
                "n_events": int(part.id.nunique()), "n_transitions": int(len(part)),
                "mae": float(part.absolute_error.mean()),
                "rmse": float(np.sqrt(part.squared_error.mean())),
                "directional_accuracy": float(
                    (np.sign(values - held.sigma.to_numpy()) == np.sign(held.delta_sigma.to_numpy())).mean()
                ),
                "flexible_alpha": alpha if name == "flexible_dynamics" else np.nan,
            })
        for name, model in models.items():
            equilibrium_rows.append({
                "lead_days": int(lead), "model": name,
                "equilibrium": model.equilibrium,
                "restoring_strength": model.restoring_strength,
                "half_life_days": half_life_days(model.restoring_strength, float(lead)),
                "development_population_median": population_center,
            })
    predictions = pd.concat(prediction_rows, ignore_index=True)
    metrics = pd.DataFrame(metric_rows)
    generator = np.random.default_rng(DEFAULT_SEED + 700)
    comparison_rows = []
    for lead, frame in predictions.groupby("lead_days"):
        event_error = frame.groupby(["id", "model"], as_index=False).absolute_error.mean()
        pivot = event_error.pivot(index="id", columns="model", values="absolute_error")
        for model in pivot.columns:
            row = {"lead_days": int(lead), "model": model}
            for benchmark in ("persistence", "flexible_dynamics"):
                common = pivot[[model, benchmark]].dropna()
                difference = common[model].to_numpy() - common[benchmark].to_numpy()
                if len(difference):
                    samples = generator.choice(difference, size=(1000, len(difference)), replace=True).mean(axis=1)
                    row[f"mae_difference_vs_{benchmark}"] = float(difference.mean())
                    row[f"difference_vs_{benchmark}_ci95_lower"] = float(np.quantile(samples, 0.025))
                    row[f"difference_vs_{benchmark}_ci95_upper"] = float(np.quantile(samples, 0.975))
            comparison_rows.append(row)
    metrics = metrics.merge(pd.DataFrame(comparison_rows), on=["lead_days", "model"], how="left")
    return predictions, metrics, pd.DataFrame(equilibrium_rows)


def restoring_models(transitions: pd.DataFrame, replicates: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, equilibrium = [], []
    for lead, frame in transitions.groupby("lead_days"):
        for part in ("development", "calibration", "held_out"):
            sample = frame[frame.partition.eq(part)]
            if sample.id.nunique() < 20:
                continue
            result = event_bootstrap_attractor(
                sample, replicates=replicates, seed=DEFAULT_SEED + int(lead) * 10 + len(part)
            )
            rows.append({
                "lead_days": int(lead), "partition": part,
                "n_fires": int(sample.id.nunique()), "n_transitions": int(len(sample)),
                "directional_accuracy": float(sample.moved_toward_two_thirds.mean()),
                "effect_size_slope_sd": float(result["slope"] * sample.sigma.std()),
                **result,
            })
            equilibrium.append({
                "lead_days": int(lead), "partition": part,
                "equilibrium": result["equilibrium"],
                "ci95_lower": result["equilibrium_ci95_lower"],
                "ci95_upper": result["equilibrium_ci95_upper"],
                "compatible_two_thirds": bool(result["equilibrium_ci95_lower"] <= TWO_THIRDS <= result["equilibrium_ci95_upper"]),
                "compatible_one_half": bool(result["equilibrium_ci95_lower"] <= 0.5 <= result["equilibrium_ci95_upper"]),
            })
    return pd.DataFrame(rows), pd.DataFrame(equilibrium)


def null_models(frame: pd.DataFrame, replicates: int) -> pd.DataFrame:
    primary = frame[(frame.partition.eq("held_out")) & (frame.lead_days.eq(1))].copy()
    observed = fit_free_attractor(primary).slope
    generator = np.random.default_rng(DEFAULT_SEED + 900)
    groups = {event_id: group.sort_values("origin_day") for event_id, group in primary.groupby("id")}
    lagged = []
    all_changes = []
    for group in groups.values():
        change = group.delta_sigma.to_numpy(dtype=float)
        all_changes.extend(change)
        if len(change) > 1:
            lagged.extend(zip(change[:-1], change[1:]))
    all_changes = np.asarray(all_changes, dtype=float)
    random_walk_scale = float(np.std(all_changes))
    if lagged:
        lagged_array = np.asarray(lagged, dtype=float)
        random_walk_rho = float(np.corrcoef(lagged_array[:, 0], lagged_array[:, 1])[0, 1])
    else:
        random_walk_rho = 0.0
    random_walk_rho = float(np.clip(np.nan_to_num(random_walk_rho), -0.95, 0.95))
    innovation_scale = random_walk_scale * np.sqrt(1.0 - random_walk_rho**2)
    rows = []
    for null_name in ("measurement_error", "shuffled_time", "random_walk"):
        slopes = []
        for _ in range(replicates):
            n_total = sx = sy = sxx = sxy = 0.0
            for event_id, group in groups.items():
                n = len(group)
                if n < 2:
                    continue
                if null_name == "measurement_error":
                    center = float(group.sigma.mean())
                    scale = float(
                        np.nanmedian(
                            np.maximum(
                                group.sigma_se.fillna(group.sigma.std()).to_numpy(dtype=float),
                                0.03,
                            )
                        )
                    )
                    state = center + generator.normal(0, scale, n + 1)
                    current, future = state[:-1], state[1:]
                elif null_name == "shuffled_time":
                    state = generator.permutation(np.r_[group.sigma.to_numpy(), group.future_sigma.iloc[-1]])
                    current, future = state[:-1], state[1:]
                else:
                    increments = np.empty(n, dtype=float)
                    increments[0] = generator.choice(all_changes) - all_changes.mean()
                    for index in range(1, n):
                        increments[index] = (
                            random_walk_rho * increments[index - 1]
                            + generator.normal(0.0, innovation_scale)
                        )
                    current = np.empty(n)
                    current[0] = float(group.sigma.iloc[0])
                    if n > 1:
                        current[1:] = current[0] + np.cumsum(increments[:-1])
                    future = current + increments
                change = future - current
                n_total += len(current)
                sx += float(current.sum())
                sy += float(change.sum())
                sxx += float(np.dot(current, current))
                sxy += float(np.dot(current, change))
            denominator = sxx - sx * sx / n_total
            slopes.append((sxy - sx * sy / n_total) / denominator if denominator > 0 else np.nan)
        rows.append({
            "null_model": null_name, "observed_slope": observed,
            "null_median_slope": float(np.median(slopes)),
            "null_ci95_lower": float(np.quantile(slopes, 0.025)),
            "null_ci95_upper": float(np.quantile(slopes, 0.975)),
            "probability_null_as_or_more_negative": float(np.mean(np.asarray(slopes) <= observed)),
            "matched_increment_lag1_correlation": random_walk_rho if null_name == "random_walk" else np.nan,
            "matched_increment_sd": random_walk_scale if null_name == "random_walk" else np.nan,
            "replicates": replicates,
        })
    return pd.DataFrame(rows)


def within_fire_models(transitions: pd.DataFrame, replicates: int) -> pd.DataFrame:
    rows = []
    generator = np.random.default_rng(DEFAULT_SEED + 1200)
    for lead, frame in transitions[transitions.partition.eq("held_out")].groupby("lead_days"):
        model = within_fire_restoration(frame)
        ids = frame.id.unique()
        slopes = []
        statistics = []
        for _, group in frame.groupby("id", sort=False):
            x = group.sigma.to_numpy(dtype=float)
            x = x - x.mean()
            y = group.delta_sigma.to_numpy(dtype=float)
            statistics.append((np.dot(x, x), np.dot(x, y)))
        statistics = np.asarray(statistics, dtype=float)
        for _ in range(replicates):
            totals = statistics[generator.integers(0, len(ids), len(ids))].sum(axis=0)
            slopes.append(totals[1] / totals[0] if totals[0] > 0 else np.nan)
        rows.append({
            "lead_days": int(lead), "n_fires": int(len(ids)), "n_transitions": int(len(frame)),
            "within_fire_slope": model.slope,
            "restoring_strength": model.restoring_strength,
            "ci95_lower": float(np.nanquantile(slopes, 0.025)),
            "ci95_upper": float(np.nanquantile(slopes, 0.975)),
        })
    return pd.DataFrame(rows)


def return_time_results(local: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    threshold = 0.1
    rows, long_rows = [], []
    for event_id, event in local[local.partition.eq("held_out")].groupby("id"):
        event = event.sort_values("event_day").reset_index(drop=True)
        days = event.event_day.to_numpy(dtype=int)
        e = event.deviation_two_thirds.to_numpy(dtype=float)
        returns, overshoots = [], []
        for j in range(len(event) - 1):
            if abs(e[j]) < threshold:
                continue
            later = np.flatnonzero(np.abs(e[j + 1 :]) < threshold)
            if later.size:
                k = j + 1 + int(later[0])
                returns.append(days[k] - days[j])
                overshoots.append(bool(e[j] * e[k] < 0))
                rows.append({
                    "id": int(event_id), "origin_day": int(days[j]),
                    "initial_deviation": float(e[j]), "returned": True,
                    "return_time_days": int(days[k] - days[j]),
                    "overshoot": bool(e[j] * e[k] < 0),
                })
            else:
                rows.append({
                    "id": int(event_id), "origin_day": int(days[j]),
                    "initial_deviation": float(e[j]), "returned": False,
                    "return_time_days": np.nan, "overshoot": False,
                })
        if int(days[-1]) >= 40:
            long_rows.append({
                "id": int(event_id), "duration_days": int(days[-1]),
                "n_slope_states": int(len(event)),
                "crossings_two_thirds": int(np.sum(e[:-1] * e[1:] < 0)),
                "excursions_outside_0_1": int(np.sum(np.abs(e) >= threshold)),
                "return_fraction": float(np.mean([r["returned"] for r in rows if r["id"] == event_id])) if any(r["id"] == event_id for r in rows) else np.nan,
                "median_return_time_days": float(np.median(returns)) if returns else np.nan,
                "overshoot_fraction": float(np.mean(overshoots)) if overshoots else np.nan,
            })
    return pd.DataFrame(rows), pd.DataFrame(long_rows)


def observation_robustness(all_local: pd.DataFrame, merged: pd.DataFrame, selected: str, replicates: int) -> pd.DataFrame:
    variants = []
    for perimeter, stride, label in (
        ("exterior_perimeter_km", 1, "exterior_full"),
        ("total_perimeter_km", 1, "total_full"),
        ("exterior_perimeter_km", 2, "exterior_thinned"),
    ):
        if perimeter == "exterior_perimeter_km" and stride == 1:
            local = all_local[all_local.estimator.eq(selected)].copy()
        else:
            local = estimate_local_slopes(merged, perimeter_column=perimeter, estimator=selected, stride=stride)
        local["partition"] = partition(local.ig_year)
        trans = make_transitions(local, leads=(1,))
        held = trans[trans.ig_year >= 2016]
        if held.id.nunique() < 20:
            continue
        result = event_bootstrap_attractor(held, replicates=replicates, seed=DEFAULT_SEED + stride + len(label))
        variants.append({
            "variant": label, "n_fires": int(held.id.nunique()), "n_transitions": int(len(held)),
            "median_sigma": float(local[local.ig_year >= 2016].sigma.median()), **result,
        })
    return pd.DataFrame(variants)


def attach_origin_features(transitions: pd.DataFrame, local: pd.DataFrame, coupling: pd.DataFrame) -> pd.DataFrame:
    origin = local[["id", "event_day", "component_count", "hole_count", "perimeter_km"]].rename(columns={"event_day": "origin_day"})
    data = transitions.merge(origin, on=["id", "origin_day"], how="left", validate="many_to_one")
    k = coupling[["id", "event_day", "effective_coupling"]]
    data = data.merge(k.rename(columns={"event_day": "origin_day", "effective_coupling": "current_coupling"}), on=["id", "origin_day"], how="left")
    future = k.rename(columns={"event_day": "future_event_day", "effective_coupling": "future_coupling"})
    data = data.merge(future, on=["id", "future_event_day"], how="left")
    future_state = local[["id", "event_day", "area_km2", "daily_growth_km2"]].rename(
        columns={"event_day": "future_event_day", "area_km2": "future_area_km2", "daily_growth_km2": "future_growth_km2"}
    )
    data = data.merge(future_state, on=["id", "future_event_day"], how="left", validate="many_to_one")
    data["log_area"] = np.log(data.area_km2.clip(lower=1e-9))
    data["log1p_growth"] = np.log1p(data.daily_growth_km2.clip(lower=0))
    data["log1p_coupling"] = np.log1p(data.current_coupling.clip(lower=0))
    data["delta_coupling"] = data.future_coupling - data.current_coupling
    return data


def downstream_prediction_metrics(data: pd.DataFrame) -> pd.DataFrame:
    """Test whether forecast geometric state adds K, area, or acceleration skill."""
    rows = []
    base_features = ["sigma", "origin_day", "log_area", "log1p_growth", "log1p_coupling"]
    for lead, frame in data.groupby("lead_days"):
        dev = frame[frame.partition.eq("development")].dropna().copy()
        cal = frame[frame.partition.eq("calibration")].dropna().copy()
        held = frame[frame.partition.eq("held_out")].dropna().copy()
        if min(dev.id.nunique(), cal.id.nunique(), held.id.nunique()) < 20:
            continue
        development_attractor = fit_free_attractor(dev)
        final_attractor = fit_free_attractor(pd.concat([dev, cal], ignore_index=True))
        for subset in (dev, cal):
            subset["predicted_future_sigma"] = predict_future_sigma(development_attractor, subset.sigma)
        held["predicted_future_sigma"] = predict_future_sigma(final_attractor, held.sigma)
        targets = {
            "future_coupling": (np.log1p, "future_coupling", "mae"),
            "future_area": (np.log, "future_area_km2", "mae"),
            "future_acceleration": (None, "future_accelerating", "brier"),
        }
        for target_name, (transform, column, metric_name) in targets.items():
            if target_name == "future_acceleration":
                for subset in (dev, cal, held):
                    subset[column] = (subset.future_growth_km2 > subset.daily_growth_km2).astype(float)
            for model_name, features in (
                ("current_geometry", base_features),
                ("attractor_evolution", [*base_features, "predicted_future_sigma"]),
            ):
                if transform is None:
                    y_dev = dev[column].to_numpy(dtype=float)
                    y_cal = cal[column].to_numpy(dtype=float)
                    y_held = held[column].to_numpy(dtype=float)
                else:
                    y_dev = transform(dev[column].clip(lower=1e-12)).to_numpy(dtype=float)
                    y_cal = transform(cal[column].clip(lower=1e-12)).to_numpy(dtype=float)
                    y_held = transform(held[column].clip(lower=1e-12)).to_numpy(dtype=float)
                candidates = []
                for alpha in (0.1, 1.0, 10.0, 100.0):
                    model = fit_standardized_ridge(dev, y_dev, feature_columns=features, alpha=alpha)
                    prediction = model.predict(cal)
                    candidates.append((float(np.mean((prediction - y_cal) ** 2)), alpha))
                alpha = min(candidates)[1]
                train = pd.concat([dev, cal], ignore_index=True)
                train["predicted_future_sigma"] = predict_future_sigma(final_attractor, train.sigma)
                y_train = np.r_[y_dev, y_cal]
                model = fit_standardized_ridge(train, y_train, feature_columns=features, alpha=alpha)
                prediction = model.predict(held)
                if metric_name == "brier":
                    score = float(np.mean((np.clip(prediction, 0, 1) - y_held) ** 2))
                else:
                    score = float(np.mean(np.abs(prediction - y_held)))
                rows.append({
                    "lead_days": int(lead), "target": target_name, "model": model_name,
                    "n_events": int(held.id.nunique()), "n_transitions": int(len(held)),
                    "metric": metric_name, "score": score, "selected_alpha": alpha,
                })
    result = pd.DataFrame(rows)
    if not result.empty:
        baseline = result[result.model.eq("current_geometry")][["lead_days", "target", "score"]].rename(columns={"score": "baseline_score"})
        result = result.merge(baseline, on=["lead_days", "target"], how="left")
        result["score_difference_vs_current_geometry"] = result.score - result.baseline_score
    return result


def coupling_relationship(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    held = data[data.partition.eq("held_out")]
    for lead, frame in held.groupby("lead_days"):
        clean = frame.dropna(subset=["deviation_two_thirds", "current_coupling", "future_coupling"])
        if clean.id.nunique() < 20:
            continue
        for target in ("future_coupling", "delta_coupling"):
            rows.append({
                "lead_days": int(lead), "target": target,
                "n_fires": int(clean.id.nunique()), "n_transitions": int(len(clean)),
                "spearman_deviation": float(spearmanr(clean.deviation_two_thirds, clean[target]).statistic),
                "spearman_absolute_deviation": float(spearmanr(clean.deviation_two_thirds.abs(), clean[target]).statistic),
                "spearman_restoration": float(spearmanr(-np.sign(clean.deviation_two_thirds) * clean.delta_sigma, clean[target]).statistic),
            })
    return pd.DataFrame(rows)


def lifecycle_equilibria(transitions: pd.DataFrame) -> pd.DataFrame:
    data = transitions[transitions.partition.ne("held_out") & transitions.lead_days.eq(1)].copy()
    data["age_band"] = pd.cut(data.origin_day, [0, 7, 14, 28, np.inf], labels=["<=7", "8-14", "15-28", ">28"])
    data["area_band"] = pd.qcut(data.area_km2, 4, duplicates="drop")
    data["coupling_band"] = pd.qcut(data.current_coupling.rank(method="first"), 4, labels=False)
    rows = []
    for variable in ("age_band", "area_band", "coupling_band"):
        for level, group in data.groupby(variable, observed=True):
            if group.id.nunique() < 20:
                continue
            model = fit_free_attractor(group)
            rows.append({"moderator": variable, "level": str(level), "n_fires": int(group.id.nunique()), "equilibrium": model.equilibrium, "restoring_strength": model.restoring_strength})
    return pd.DataFrame(rows)


def make_figure(local: pd.DataFrame, transitions: pd.DataFrame, metrics: pd.DataFrame, long_metrics: pd.DataFrame, output: Path) -> None:
    held_local = local[local.partition.eq("held_out")]
    if not long_metrics.empty and "return_fraction" in long_metrics:
        candidates = long_metrics.dropna(subset=["return_fraction"]).sort_values(["return_fraction", "n_slope_states"])
        ids = list(candidates.head(2).id) + list(candidates.tail(2).id)
    else:
        counts = held_local.groupby("id").size().sort_values()
        ids = list(counts.tail(4).index)
    ids = list(dict.fromkeys(ids))
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 10.2), constrained_layout=True)
    ax = axes[0, 0]
    for event_id in ids:
        event = held_local[held_local.id.eq(event_id)].sort_values("event_day")
        ax.plot(event.event_day, event.sigma, marker="o", ms=3, lw=1.5, label=str(int(event_id)))
    ax.axhline(TWO_THIRDS, color="#6495ED", lw=3, alpha=0.8)
    ax.set(xlabel="Event day", ylabel=r"Local $\sigma(t)$", title="A  Held-out long-fire excursions")
    ax.legend(title="FIRED id", ncol=2, frameon=False, fontsize=8)

    ax = axes[0, 1]
    primary = transitions[(transitions.partition.eq("held_out")) & transitions.lead_days.eq(1)]
    aggregate = primary.groupby("id", as_index=False).agg(deviation=("deviation_two_thirds", "mean"), change=("delta_sigma", "mean"))
    ax.hexbin(aggregate.deviation, aggregate.change, gridsize=28, mincnt=1, cmap="magma_r", bins="log")
    model = fit_free_attractor(primary)
    x = np.linspace(np.quantile(aggregate.deviation, 0.01), np.quantile(aggregate.deviation, 0.99), 100)
    ax.plot(x, model.intercept + model.slope * (x + TWO_THIRDS), color="white", lw=5)
    ax.plot(x, model.intercept + model.slope * (x + TWO_THIRDS), color="#202020", lw=2.5)
    ax.axhline(0, color="#777777", lw=1)
    ax.axvline(0, color="#6495ED", lw=2, alpha=0.8)
    ax.set(xlabel=r"Current deviation $\sigma_t-2/3$", ylabel=r"Subsequent $\Delta\sigma$", title="B  Restoring-force test (fire means)")

    ax = axes[1, 0]
    day = metrics[metrics.lead_days.eq(1)].sort_values("mae")
    positions = np.arange(len(day))
    ax.barh(positions, day.mae, color=[COLORS[name] for name in day.model])
    ax.set_yticks(positions, [name.replace("_", " ") for name in day.model])
    ax.invert_yaxis()
    ax.set(xlabel="Held-out mean absolute slope error", title="C  Prospective model comparison")

    ax = axes[1, 1]
    primary = primary.copy()
    primary["magnitude_bin"] = pd.qcut(primary.deviation_two_thirds.abs(), 5, duplicates="drop")
    probability = primary.groupby("magnitude_bin", observed=True).agg(magnitude=("deviation_two_thirds", lambda x: float(np.mean(np.abs(x)))), probability=("moved_toward_two_thirds", "mean"), n=("id", "nunique")).reset_index()
    ax.plot(probability.magnitude, probability.probability, marker="o", color="#2A8C5A", lw=2.5)
    ax.axhline(0.5, color="#777777", ls="--")
    ax.set(xlabel=r"Initial $|\sigma_t-2/3|$", ylabel="Probability of moving closer", ylim=(0, 1), title="D  Directional return by excursion size")
    fig.suptitle("Is two-thirds a dynamical attractor of mapped wildfire geometry?", fontsize=17, fontweight="bold")
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(output / f"figure1_geometric_attractor_validation.{suffix}", dpi=400 if suffix == "png" else None)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    for path in (args.sequences, args.geometry, args.coupling):
        if not path.exists():
            raise FileNotFoundError(path)
    sequences = pd.read_csv(args.sequences, parse_dates=["date"])
    geometry = pd.read_csv(args.geometry)
    coupling = pd.read_csv(args.coupling)
    if args.smoke:
        sequences = deterministic_subset(sequences)
        ids = set(sequences.id.unique())
        geometry = geometry[geometry.id.isin(ids)]
        coupling = coupling[coupling.id.isin(ids)]
    merged = merge_geometry_sequences(sequences, geometry)
    replicates = 100 if args.smoke else 1000

    all_local, estimator_tuning, selected = estimator_selection(merged)
    primary = all_local[all_local.estimator.eq(selected)].copy()
    primary["partition"] = partition(primary.ig_year)
    transitions = make_transitions(primary, leads=LEADS)
    transitions["partition"] = partition(transitions.ig_year)
    transitions = attach_origin_features(transitions, primary, coupling)

    restoring, equilibria = restoring_models(transitions, replicates)
    predictions, prediction_metrics, model_equilibria = prediction_analysis(transitions)
    equilibria = pd.concat([equilibria, model_equilibria.assign(partition="locked_train")], ignore_index=True, sort=False)
    nulls = null_models(transitions, min(replicates, 500))
    within = within_fire_models(transitions, replicates)
    returns, long_metrics = return_time_results(primary)
    robustness = observation_robustness(all_local, merged, selected, replicates)
    coupling_results = coupling_relationship(transitions)
    downstream = downstream_prediction_metrics(transitions)
    lifecycle = lifecycle_equilibria(transitions)

    # Boundary change is associative and uses mapped cumulative-boundary proxies.
    boundary_rows = []
    lookup = primary[["id", "event_day", "perimeter_km", "component_count", "hole_count"]]
    future = lookup.rename(columns={"event_day": "future_event_day", "perimeter_km": "future_perimeter", "component_count": "future_components", "hole_count": "future_holes"})
    boundary = transitions.merge(future, on=["id", "future_event_day"], how="left")
    for lead, frame in boundary[boundary.partition.eq("held_out")].groupby("lead_days"):
        frame = frame.dropna(subset=["future_perimeter"])
        if frame.id.nunique() < 20:
            continue
        frame = frame.assign(
            perimeter_change=np.log(frame.future_perimeter / frame.perimeter_km),
            component_change=frame.future_components - frame.component_count,
            hole_change=frame.future_holes - frame.hole_count,
            restoration=-np.sign(frame.deviation_two_thirds) * frame.delta_sigma,
        )
        for target in ("perimeter_change", "component_change", "hole_change"):
            boundary_rows.append({
                "lead_days": int(lead), "target": target,
                "n_fires": int(frame.id.nunique()),
                "departure_correlation": float(spearmanr(frame.deviation_two_thirds.abs(), frame[target]).statistic),
                "restoration_correlation": float(spearmanr(frame.restoration, frame[target]).statistic),
            })
    boundary_results = pd.DataFrame(boundary_rows)

    all_local.to_csv(output / "local_slope_estimates.csv.gz", index=False)
    transitions.to_csv(output / "attractor_transition_data.csv.gz", index=False)
    restoring.to_csv(output / "restoring_force_models.csv", index=False)
    equilibria.to_csv(output / "equilibrium_estimates.csv", index=False)
    nulls.to_csv(output / "null_model_results.csv", index=False)
    within.to_csv(output / "within_fire_models.csv", index=False)
    returns.to_csv(output / "return_time_results.csv", index=False)
    robustness.to_csv(output / "observation_robustness.csv", index=False)
    prediction_metrics.to_csv(output / "attractor_prediction_metrics.csv", index=False)
    predictions.to_csv(output / "held_out_attractor_predictions.csv.gz", index=False)
    long_metrics.to_csv(output / "long_fire_attractor_metrics.csv", index=False)
    coupling_results.to_csv(output / "attractor_coupling_relationship.csv", index=False)
    downstream.to_csv(output / "attractor_downstream_prediction_metrics.csv", index=False)
    boundary_results.to_csv(output / "boundary_reorganization.csv", index=False)
    lifecycle.to_csv(output / "lifecycle_equilibria.csv", index=False)
    estimator_tuning.to_csv(output / "estimator_selection.csv", index=False)
    make_figure(primary, transitions, prediction_metrics, long_metrics, output)

    design = {
        "seed": DEFAULT_SEED,
        "partitions": {"development": [2001, 2012], "calibration": [2013, 2015], "held_out": [2016, 2020]},
        "candidate_estimators": list(CANDIDATES),
        "selected_estimator": selected,
        "selection_criterion": "minimum calibration one-step future-slope MAE with minimum event coverage",
        "primary_perimeter": "exterior_perimeter_km",
        "leads_days": list(LEADS),
        "bootstrap_unit": "whole fire",
        "nulls": ["measurement_error", "shuffled_time", "random_walk", "population_mean"],
        "spatial_resolution_tested": False,
        "input_sha256": {str(path): sha256(path) for path in (args.sequences, args.geometry, args.coupling)},
    }
    design_text = json.dumps(design, sort_keys=True)
    design["design_hash"] = hashlib.sha256(design_text.encode()).hexdigest()
    (output / "design_lock.json").write_text(json.dumps(design, indent=2) + "\n")

    held_one = restoring[(restoring.partition.eq("held_out")) & restoring.lead_days.eq(1)].iloc[0]
    day_one = prediction_metrics[prediction_metrics.lead_days.eq(1)].set_index("model")
    report = {
        "counts": {"events": int(sequences.id.nunique()), "local_states": int(len(primary)), "transitions": int(len(transitions)), "held_out_events": int(sequences[sequences.ig_year >= 2016].id.nunique())},
        "design_hash": design["design_hash"],
        "primary_results": {
            "selected_estimator": selected,
            "held_out_next_observation_slope": float(held_one.slope),
            "held_out_slope_ci95": [float(held_one.slope_ci95_lower), float(held_one.slope_ci95_upper)],
            "held_out_free_equilibrium": float(held_one.equilibrium),
            "held_out_equilibrium_ci95": [float(held_one.equilibrium_ci95_lower), float(held_one.equilibrium_ci95_upper)],
            "held_out_directional_accuracy": float(held_one.directional_accuracy),
            "two_thirds_mae": float(day_one.loc["two_thirds_attractor", "mae"]),
            "one_half_mae": float(day_one.loc["half_attractor", "mae"]),
            "population_mean_mae": float(day_one.loc["population_mean", "mae"]),
            "persistence_mae": float(day_one.loc["persistence", "mae"]),
            "flexible_mae": float(day_one.loc["flexible_dynamics", "mae"]),
        },
        "interpretation_boundary": "mapped FIRED cumulative geometry at available resolution; no literal optimization, active flame-front, causal reorganization, or energetic metabolism is identified",
    }
    (output / "run_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
