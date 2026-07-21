"""Fit perimeter-area scaling exponents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class ScalingFit:
    model: str
    scenario: str
    initial_shape: str
    replicate: str
    n: int
    alpha: float
    sigma: float
    sigma_se: float
    ci_low: float
    ci_high: float
    rmse: float

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def ols_loglog(area: Iterable[float], perimeter: Iterable[float]) -> tuple[float, float, float, float, float]:
    area_arr = np.asarray(list(area), dtype=float)
    perim_arr = np.asarray(list(perimeter), dtype=float)
    keep = (area_arr > 0) & (perim_arr > 0)
    x = np.log10(area_arr[keep])
    y = np.log10(perim_arr[keep])
    if len(x) < 3:
        raise ValueError("Need at least three positive area/perimeter pairs")

    X = np.column_stack([np.ones_like(x), x])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    residuals = y - X @ beta
    dof = max(1, len(x) - 2)
    sigma2 = float(np.sum(residuals * residuals) / dof)
    cov = sigma2 * np.linalg.inv(X.T @ X)
    slope_se = float(np.sqrt(cov[1, 1]))
    rmse = float(np.sqrt(np.mean(residuals * residuals)))
    ci_low = float(beta[1] - 1.96 * slope_se)
    ci_high = float(beta[1] + 1.96 * slope_se)
    return float(beta[0]), float(beta[1]), slope_se, ci_low, ci_high, rmse


def fit_group(rows: list[dict[str, object]]) -> ScalingFit:
    alpha, sigma, se, ci_low, ci_high, rmse = ols_loglog(
        [float(row["area"]) for row in rows],
        [float(row["exterior_perimeter"]) for row in rows],
    )
    first = rows[0]
    replicate_values = sorted({str(row["replicate"]) for row in rows})
    return ScalingFit(
        model=str(first["model"]),
        scenario=str(first["scenario"]),
        initial_shape=str(first["initial_shape"]),
        replicate="+".join(replicate_values),
        n=len(rows),
        alpha=alpha,
        sigma=sigma,
        sigma_se=se,
        ci_low=ci_low,
        ci_high=ci_high,
        rmse=rmse,
    )


def exclude_transients(rows: list[dict[str, object]], early_fraction: float = 0.15) -> list[dict[str, object]]:
    valid = [
        row
        for row in rows
        if bool(row["valid_geometry"]) and not bool(row["domain_edge_contact"])
    ]
    if not valid:
        return []
    times = np.array([float(row["time"]) for row in valid])
    cutoff = float(times.min() + early_fraction * (times.max() - times.min()))
    return [row for row in valid if float(row["time"]) >= cutoff]


def fit_by_run(rows: list[dict[str, object]], early_fraction: float = 0.15) -> list[ScalingFit]:
    groups: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for row in rows:
        key = (row["model"], row["scenario"], row["initial_shape"], row["replicate"])
        groups.setdefault(key, []).append(row)

    fits: list[ScalingFit] = []
    for group_rows in groups.values():
        filtered = exclude_transients(group_rows, early_fraction)
        if len(filtered) >= 3:
            fits.append(fit_group(filtered))
    return fits


def fixed_exponent_scores(rows: list[dict[str, object]], exponents: tuple[float, ...] = (0.5, 2 / 3, 0.75)) -> list[dict[str, float]]:
    area = np.array([float(row["area"]) for row in rows if float(row["area"]) > 0])
    perimeter = np.array(
        [float(row["exterior_perimeter"]) for row in rows if float(row["exterior_perimeter"]) > 0]
    )
    n = min(len(area), len(perimeter))
    x = np.log10(area[:n])
    y = np.log10(perimeter[:n])
    scores = []
    for exponent in exponents:
        intercept = float(np.mean(y - exponent * x))
        residuals = y - (intercept + exponent * x)
        rss = float(np.sum(residuals * residuals))
        rmse = float(np.sqrt(np.mean(residuals * residuals)))
        aic = float(n * np.log(max(rss / n, 1e-12)) + 2 * 1)
        scores.append({"sigma": float(exponent), "intercept": intercept, "rmse": rmse, "aic": aic})
    min_aic = min(score["aic"] for score in scores)
    for score in scores:
        score["delta_aic"] = score["aic"] - min_aic
    return scores


def local_slopes(rows: list[dict[str, object]], window: int = 5) -> list[dict[str, float]]:
    ordered = sorted(rows, key=lambda row: float(row["area"]))
    result = []
    if len(ordered) < window:
        return result
    for start in range(0, len(ordered) - window + 1):
        subset = ordered[start : start + window]
        alpha, sigma, se, ci_low, ci_high, rmse = ols_loglog(
            [float(row["area"]) for row in subset],
            [float(row["exterior_perimeter"]) for row in subset],
        )
        result.append(
            {
                "log_area_mid": float(np.mean(np.log10([float(row["area"]) for row in subset]))),
                "sigma": sigma,
                "sigma_se": se,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "rmse": rmse,
            }
        )
    return result
