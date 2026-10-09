"""Shared calculations for the final FIRED state, scale, and prediction audit."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


DEFAULT_SEED = 20261009
CANDIDATE_EXPONENTS = {
    "one_half": 0.5,
    "two_thirds": 2.0 / 3.0,
    "three_quarters": 0.75,
}


def add_normalized_geometry(
    frame: pd.DataFrame, development_exponent: float
) -> pd.DataFrame:
    """Add fixed geometric levels and origin-safe recent changes."""
    result = frame.copy()
    fraction = np.clip(result.recent_area_fraction.to_numpy(dtype=float), 0.0, 1.0 - 1e-9)
    result["recent_log_area_change"] = -np.log1p(-fraction)
    exponents = {**CANDIDATE_EXPONENTS, "development": float(development_exponent)}
    for name, exponent in exponents.items():
        result[f"z_{name}"] = (
            result.log_exterior_perimeter.to_numpy(dtype=float)
            - exponent * result.log_origin_area.to_numpy(dtype=float)
        )
        result[f"delta_z_{name}"] = (
            result.recent_log_exterior_perimeter_change.to_numpy(dtype=float)
            - exponent * result.recent_log_area_change.to_numpy(dtype=float)
        )
    return result


def rank_auc(observed: Sequence[int], probability: Sequence[float]) -> float:
    """Return ROC AUC using average ranks, including tied predictions."""
    y = np.asarray(observed, dtype=int)
    p = np.asarray(probability, dtype=float)
    positive = y == 1
    n_pos = int(positive.sum())
    n_neg = int((~positive).sum())
    if not n_pos or not n_neg:
        return float("nan")
    ranks = pd.Series(p).rank(method="average").to_numpy(dtype=float)
    return float((ranks[positive].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def average_precision(observed: Sequence[int], probability: Sequence[float]) -> float:
    """Return non-interpolated area under the precision-recall curve."""
    y = np.asarray(observed, dtype=int)
    p = np.asarray(probability, dtype=float)
    positives = int(y.sum())
    if positives == 0:
        return float("nan")
    previous_recall = 0.0
    area = 0.0
    for threshold in np.unique(p)[::-1]:
        selected = p >= threshold
        true_positive = int(np.sum(selected & (y == 1)))
        recall = true_positive / positives
        precision = true_positive / max(int(selected.sum()), 1)
        area += (recall - previous_recall) * precision
        previous_recall = recall
    return float(area)


def binary_performance(
    observed: Sequence[int], probability: Sequence[float], threshold: float
) -> dict[str, float]:
    """Return discrimination, classification, and proper-score metrics."""
    y = np.asarray(observed, dtype=int)
    p = np.clip(np.asarray(probability, dtype=float), 1e-9, 1 - 1e-9)
    prediction = p >= float(threshold)
    positive = y == 1
    tp = int(np.sum(prediction & positive))
    tn = int(np.sum(~prediction & ~positive))
    fp = int(np.sum(prediction & ~positive))
    fn = int(np.sum(~prediction & positive))
    recall = tp / (tp + fn) if tp + fn else np.nan
    specificity = tn / (tn + fp) if tn + fp else np.nan
    precision = tp / (tp + fp) if tp + fp else np.nan
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else np.nan
    logits = np.log(p / (1 - p))
    design = np.column_stack([np.ones(len(y)), logits])
    calibration, *_ = np.linalg.lstsq(design, y.astype(float), rcond=None)
    return {
        "prevalence": float(y.mean()),
        "recall": float(recall),
        "specificity": float(specificity),
        "precision": float(precision),
        "balanced_accuracy": float((recall + specificity) / 2),
        "f1": float(f1),
        "roc_auc": rank_auc(y, p),
        "pr_auc": average_precision(y, p),
        "brier": float(np.mean((p - y) ** 2)),
        "log_score": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
        "calibration_intercept_linear": float(calibration[0]),
        "calibration_slope_linear": float(calibration[1]),
        "decision_threshold": float(threshold),
    }


def curve_points(observed: Sequence[int], probability: Sequence[float]) -> pd.DataFrame:
    """Build compact held-out ROC and precision-recall coordinates."""
    y = np.asarray(observed, dtype=int)
    p = np.asarray(probability, dtype=float)
    thresholds = np.unique(np.quantile(p, np.linspace(0, 1, 201)))
    rows = []
    for threshold in thresholds[::-1]:
        prediction = p >= threshold
        tp = np.sum(prediction & (y == 1))
        fp = np.sum(prediction & (y == 0))
        fn = np.sum(~prediction & (y == 1))
        tn = np.sum(~prediction & (y == 0))
        rows.append(
            {
                "threshold": float(threshold),
                "recall": float(tp / max(tp + fn, 1)),
                "false_positive_rate": float(fp / max(fp + tn, 1)),
                "precision": float(tp / max(tp + fp, 1)),
            }
        )
    return pd.DataFrame(rows)


def calibration_bins(
    observed: Sequence[int], probability: Sequence[float], bins: int = 10
) -> pd.DataFrame:
    """Return equal-frequency calibration bins."""
    data = pd.DataFrame({"observed": observed, "probability": probability})
    data["bin"] = pd.qcut(data.probability, q=min(bins, len(data)), duplicates="drop")
    return (
        data.groupby("bin", observed=False)
        .agg(n=("observed", "size"), mean_probability=("probability", "mean"), event_rate=("observed", "mean"))
        .reset_index(drop=True)
    )


def bootstrap_mean_ci(
    frame: pd.DataFrame,
    value: str,
    *,
    replicates: int = 1000,
    seed: int = DEFAULT_SEED,
) -> tuple[float, float, np.ndarray]:
    """Bootstrap a row metric after first averaging within whole fires."""
    event = frame.groupby("id", sort=False)[value].mean().to_numpy(dtype=float)
    generator = np.random.default_rng(seed)
    draws = generator.choice(event, size=(replicates, len(event)), replace=True).mean(axis=1)
    lower, upper = np.quantile(draws, [0.025, 0.975])
    return float(lower), float(upper), draws


def paired_bootstrap_ci(
    frame: pd.DataFrame,
    first: str,
    second: str,
    *,
    replicates: int = 1000,
    seed: int = DEFAULT_SEED,
) -> tuple[float, float, float, np.ndarray]:
    """Bootstrap a paired first-minus-second loss contrast by fire."""
    event = frame.groupby("id", sort=False)[[first, second]].mean()
    difference = (event[first] - event[second]).to_numpy(dtype=float)
    generator = np.random.default_rng(seed)
    draws = generator.choice(difference, size=(replicates, len(difference)), replace=True).mean(axis=1)
    lower, upper = np.quantile(draws, [0.025, 0.975])
    return float(difference.mean()), float(lower), float(upper), draws
