"""Past-only active-front and weather features for FIRED predictions."""

from __future__ import annotations

import numpy as np
import pandas as pd


ACTIVE_FRONT_FEATURE_COLUMNS = (
    "log_recent_new_exterior_perimeter",
    "log_recent_new_boundary_efficiency",
    "recent_new_to_cumulative_perimeter",
    "log_recent_daily_component_count",
    "recent_new_perimeter_trend",
)

WEATHER_FEATURE_COLUMNS = (
    "recent_vpd_kpa",
    "recent_wind_speed_m_s",
    "recent_fuel_moisture_100hr_pct",
    "recent_energy_release_component",
    "log1p_recent_precipitation_mm",
    "vpd_change_from_prior",
    "wind_change_from_prior",
    "fuel_moisture_change_from_prior",
    "erc_change_from_prior",
    "precipitation_change_from_prior",
)

NEXT_DAY_WEATHER_FEATURE_COLUMNS = (
    "next_day_vpd_kpa",
    "next_day_wind_speed_m_s",
    "next_day_fuel_moisture_100hr_pct",
    "next_day_energy_release_component",
    "log1p_next_day_precipitation_mm",
)


def add_active_front_features(
    features: pd.DataFrame,
    sequences: pd.DataFrame,
    geometry: pd.DataFrame,
    *,
    recent_days: int = 3,
) -> pd.DataFrame:
    """Add past-only newly burned boundary proxies at each snapshot."""
    required_geometry = {
        "id",
        "event_day",
        "daily_exterior_perimeter_km",
        "daily_component_count",
        "exterior_perimeter_km",
    }
    if missing := required_geometry.difference(geometry.columns):
        raise ValueError(f"missing daily geometry columns: {sorted(missing)}")
    daily = sequences[["id", "event_day", "daily_area_km2"]].merge(
        geometry[list(required_geometry)],
        on=["id", "event_day"],
        how="left",
        validate="one_to_one",
    ).sort_values(["id", "event_day"])
    daily[["daily_exterior_perimeter_km", "daily_component_count"]] = daily[
        ["daily_exterior_perimeter_km", "daily_component_count"]
    ].fillna(0.0)
    daily["exterior_perimeter_km"] = daily.groupby("id", sort=False)[
        "exterior_perimeter_km"
    ].ffill()
    lookup = {int(event_id): event for event_id, event in daily.groupby("id")}
    rows = []
    for feature in features[["id", "snapshot_day"]].itertuples(index=False):
        event = lookup[int(feature.id)]
        history = event[event.event_day <= int(feature.snapshot_day)]
        if len(history) != int(feature.snapshot_day):
            raise ValueError("active-front history is incomplete")
        recent = history.tail(recent_days)
        new_perimeter = recent.daily_exterior_perimeter_km.to_numpy(dtype=float)
        recent_growth = recent.daily_area_km2.to_numpy(dtype=float)
        cumulative_perimeter = float(history.exterior_perimeter_km.iloc[-1])
        x = np.arange(len(new_perimeter), dtype=float)
        trend = (
            float(np.polyfit(x, new_perimeter, 1)[0])
            if len(new_perimeter) >= 2
            else 0.0
        )
        rows.append(
            {
                "id": int(feature.id),
                "snapshot_day": int(feature.snapshot_day),
                "log_recent_new_exterior_perimeter": float(
                    np.log1p(new_perimeter.mean())
                ),
                "log_recent_new_boundary_efficiency": float(
                    np.log1p(recent_growth.sum() / max(new_perimeter.sum(), 1e-12))
                ),
                "recent_new_to_cumulative_perimeter": float(
                    new_perimeter.mean() / max(cumulative_perimeter, 1e-12)
                ),
                "log_recent_daily_component_count": float(
                    np.log1p(recent.daily_component_count.mean())
                ),
                "recent_new_perimeter_trend": trend,
            }
        )
    result = features.merge(
        pd.DataFrame(rows),
        on=["id", "snapshot_day"],
        validate="one_to_one",
    )
    if not np.isfinite(result.loc[:, ACTIVE_FRONT_FEATURE_COLUMNS]).all().all():
        raise ValueError("active-front features must be finite")
    return result


def add_weather_features(
    features: pd.DataFrame,
    weather: pd.DataFrame,
    *,
    recent_days: int = 3,
) -> pd.DataFrame:
    """Add recent weather level and change features using only past days."""
    variables = {
        "vpd_kpa": "vpd",
        "wind_speed_m_s": "wind",
        "fuel_moisture_100hr_pct": "fuel_moisture",
        "energy_release_component": "erc",
        "precipitation_mm": "precipitation",
    }
    required = {"id", "event_day", *variables}
    if missing := required.difference(weather.columns):
        raise ValueError(f"missing weather columns: {sorted(missing)}")
    lookup = {
        int(event_id): event.sort_values("event_day")
        for event_id, event in weather.groupby("id")
    }
    rows = []
    for feature in features[["id", "snapshot_day"]].itertuples(index=False):
        event = lookup[int(feature.id)]
        history = event[event.event_day <= int(feature.snapshot_day)]
        if len(history) != int(feature.snapshot_day):
            raise ValueError("weather history is incomplete")
        recent = history.tail(recent_days)
        prior = history.iloc[-2 * recent_days : -recent_days]
        if prior.empty:
            prior = history.head(max(1, len(history) - recent_days))
        values: dict[str, float | int] = {
            "id": int(feature.id),
            "snapshot_day": int(feature.snapshot_day),
        }
        for column, stem in variables.items():
            recent_value = (
                float(recent[column].sum())
                if column == "precipitation_mm"
                else float(recent[column].mean())
            )
            prior_value = (
                float(prior[column].sum())
                if column == "precipitation_mm"
                else float(prior[column].mean())
            )
            if stem == "vpd":
                values["recent_vpd_kpa"] = recent_value
                values["vpd_change_from_prior"] = recent_value - prior_value
            elif stem == "wind":
                values["recent_wind_speed_m_s"] = recent_value
                values["wind_change_from_prior"] = recent_value - prior_value
            elif stem == "fuel_moisture":
                values["recent_fuel_moisture_100hr_pct"] = recent_value
                values["fuel_moisture_change_from_prior"] = recent_value - prior_value
            elif stem == "erc":
                values["recent_energy_release_component"] = recent_value
                values["erc_change_from_prior"] = recent_value - prior_value
            else:
                values["log1p_recent_precipitation_mm"] = float(
                    np.log1p(recent_value)
                )
                values["precipitation_change_from_prior"] = (
                    recent_value - prior_value
                )
        rows.append(values)
    result = features.merge(
        pd.DataFrame(rows),
        on=["id", "snapshot_day"],
        validate="one_to_one",
    )
    if not np.isfinite(result.loc[:, WEATHER_FEATURE_COLUMNS]).all().all():
        raise ValueError("weather features must be finite")
    return result


def add_next_day_weather_features(
    features: pd.DataFrame,
    weather: pd.DataFrame,
    *,
    lead_days: int = 1,
) -> pd.DataFrame:
    """Add observed future weather for an explicitly non-operational oracle test."""
    if lead_days < 1:
        raise ValueError("lead_days must be positive")
    variables = {
        "vpd_kpa": "next_day_vpd_kpa",
        "wind_speed_m_s": "next_day_wind_speed_m_s",
        "fuel_moisture_100hr_pct": "next_day_fuel_moisture_100hr_pct",
        "energy_release_component": "next_day_energy_release_component",
        "precipitation_mm": "log1p_next_day_precipitation_mm",
    }
    required = {"id", "event_day", *variables}
    if missing := required.difference(weather.columns):
        raise ValueError(f"missing weather columns: {sorted(missing)}")
    future = weather.loc[:, ["id", "event_day", *variables]].copy()
    future["snapshot_day"] = future["event_day"] - lead_days
    future = future.drop(columns="event_day").rename(columns=variables)
    future["log1p_next_day_precipitation_mm"] = np.log1p(
        future["log1p_next_day_precipitation_mm"]
    )
    result = features.merge(
        future,
        on=["id", "snapshot_day"],
        how="left",
        validate="one_to_one",
    )
    if result.loc[:, NEXT_DAY_WEATHER_FEATURE_COLUMNS].isna().any().any():
        raise ValueError("next-day weather is incomplete")
    if not np.isfinite(result.loc[:, NEXT_DAY_WEATHER_FEATURE_COLUMNS]).all().all():
        raise ValueError("next-day weather features must be finite")
    return result


def terminal_weather_changes(
    weather: pd.DataFrame,
    *,
    snapshot_day: int = 7,
    window_days: int = 3,
) -> pd.DataFrame:
    """Compare terminal weather with the recent snapshot weather."""
    columns = (
        "vpd_kpa",
        "wind_speed_m_s",
        "fuel_moisture_100hr_pct",
        "energy_release_component",
        "precipitation_mm",
    )
    rows = []
    for event_id, event in weather.groupby("id", sort=False):
        event = event.sort_values("event_day")
        baseline = event[event.event_day <= snapshot_day].tail(window_days)
        terminal = event.tail(window_days)
        if baseline.empty or terminal.empty:
            continue
        result: dict[str, float | int] = {"id": int(event_id)}
        for column in columns:
            if column == "precipitation_mm":
                result[f"terminal_{column}_change"] = float(
                    terminal[column].sum() - baseline[column].sum()
                )
            else:
                result[f"terminal_{column}_change"] = float(
                    terminal[column].mean() - baseline[column].mean()
                )
        rows.append(result)
    return pd.DataFrame(rows)


def active_day_terminal_fraction(
    sequences: pd.DataFrame,
    *,
    active_days: int = 3,
) -> pd.DataFrame:
    """Measure terminal growth using the last positive-detection days only."""
    rows = []
    for event_id, event in sequences.groupby("id", sort=False):
        growth = event.sort_values("event_day").daily_area_km2.to_numpy(dtype=float)
        active = growth[growth > 0]
        if active.size == 0:
            continue
        peak = max(float(pd.Series(growth).rolling(3, center=True, min_periods=1).mean().max()), 1e-12)
        rows.append(
            {
                "id": int(event_id),
                "active_day_terminal_growth_fraction": float(
                    active[-active_days:].mean() / peak
                ),
            }
        )
    return pd.DataFrame(rows)
