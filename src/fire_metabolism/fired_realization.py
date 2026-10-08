"""Diagnostics for persistent-course potential and realized fire termination."""

from __future__ import annotations

import numpy as np
import pandas as pd


def terminal_growth_diagnostics(
    sequences: pd.DataFrame,
    *,
    window_days: int = 3,
    gradual_threshold: float = 0.10,
    abrupt_threshold: float = 0.25,
) -> pd.DataFrame:
    """Measure how much growth remains immediately before mapped termination."""
    required = {"id", "event_day", "daily_area_km2"}
    if missing := required.difference(sequences.columns):
        raise ValueError(f"missing sequence columns: {sorted(missing)}")
    if window_days < 1:
        raise ValueError("window_days must be positive")
    if not 0 <= gradual_threshold < abrupt_threshold:
        raise ValueError("thresholds must satisfy 0 <= gradual < abrupt")

    rows = []
    for event_id, event in sequences.groupby("id", sort=False):
        event = event.sort_values("event_day")
        growth = event.daily_area_km2.to_numpy(dtype=float)
        if growth.size == 0 or np.any(growth < 0) or not np.isfinite(growth).all():
            raise ValueError("daily growth must be finite and nonnegative")
        rolling = (
            pd.Series(growth)
            .rolling(window_days, center=True, min_periods=1)
            .mean()
            .to_numpy(dtype=float)
        )
        peak_smoothed = max(float(rolling.max()), np.finfo(float).eps)
        terminal_mean = float(growth[-window_days:].mean())
        terminal_fraction = terminal_mean / peak_smoothed
        prior = growth[-2 * window_days : -window_days]
        prior_mean = float(prior.mean()) if prior.size else np.nan
        terminal_to_prior = (
            terminal_mean / prior_mean if np.isfinite(prior_mean) and prior_mean > 0 else np.nan
        )
        if terminal_fraction <= gradual_threshold:
            signature = "gradual_decline_like"
        elif terminal_fraction >= abrupt_threshold:
            signature = "abrupt_truncation_like"
        else:
            signature = "intermediate"
        rows.append(
            {
                "id": int(event_id),
                "death_day": int(event.event_day.max()),
                "peak_smoothed_growth_km2_per_day": peak_smoothed,
                "terminal_mean_growth_km2_per_day": terminal_mean,
                "terminal_growth_fraction_of_peak": terminal_fraction,
                "terminal_to_prior_growth_ratio": terminal_to_prior,
                "terminal_signature": signature,
            }
        )
    result = pd.DataFrame(rows)
    numeric = result.select_dtypes(include=[np.number]).drop(columns="id")
    if not np.isfinite(numeric.drop(columns="terminal_to_prior_growth_ratio")).all().all():
        raise ValueError("terminal diagnostics must be finite")
    return result


def assign_realization_group(frame: pd.DataFrame) -> pd.Series:
    """Assign outcome-aware groups used only for retrospective diagnostics."""
    required = {"high_confidence_persistent", "actual_persistent"}
    if missing := required.difference(frame.columns):
        raise ValueError(f"missing grouping columns: {sorted(missing)}")
    high = frame.high_confidence_persistent.astype(bool)
    actual = frame.actual_persistent.astype(bool)
    return pd.Series(
        np.select(
            [high & actual, high & ~actual, actual],
            [
                "high_confidence_true_persistent",
                "high_confidence_early_ending",
                "other_true_persistent",
            ],
            default="other_ordinary",
        ),
        index=frame.index,
        name="realization_group",
    )


def summarize_realization_groups(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize persistent-course area realization and terminal signatures."""
    required = {
        "realization_group",
        "area_realization_fraction",
        "terminal_signature",
    }
    if missing := required.difference(frame.columns):
        raise ValueError(f"missing realization columns: {sorted(missing)}")
    rows = []
    for group_name, group in frame.groupby("realization_group", sort=False):
        area = group.area_realization_fraction.to_numpy(dtype=float)
        rows.append(
            {
                "realization_group": group_name,
                "n_events": int(len(group)),
                "median_area_realization_fraction": float(np.median(area)),
                "area_realization_q25": float(np.quantile(area, 0.25)),
                "area_realization_q75": float(np.quantile(area, 0.75)),
                "fraction_realizing_less_than_half": float(np.mean(area < 0.5)),
                "fraction_gradual_decline_like": float(
                    np.mean(group.terminal_signature == "gradual_decline_like")
                ),
                "fraction_abrupt_truncation_like": float(
                    np.mean(group.terminal_signature == "abrupt_truncation_like")
                ),
            }
        )
    return pd.DataFrame(rows)
