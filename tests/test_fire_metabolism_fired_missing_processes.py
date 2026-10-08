import numpy as np
import pandas as pd

from fire_metabolism.fired_missing_processes import (
    ACTIVE_FRONT_FEATURE_COLUMNS,
    NEXT_DAY_WEATHER_FEATURE_COLUMNS,
    WEATHER_FEATURE_COLUMNS,
    active_day_terminal_fraction,
    add_active_front_features,
    add_next_day_weather_features,
    add_weather_features,
    terminal_weather_changes,
)


def _sequences():
    return pd.DataFrame(
        [
            {"id": event_id, "event_day": day, "daily_area_km2": value}
            for event_id, values in {1: [1, 2, 3, 4], 2: [2, 0, 1, 1]}.items()
            for day, value in enumerate(values, 1)
        ]
    )


def test_active_front_features_are_past_only_and_finite():
    features = pd.DataFrame({"id": [1, 2], "snapshot_day": [3, 3]})
    geometry = _sequences()[["id", "event_day"]].copy()
    geometry["daily_exterior_perimeter_km"] = [1, 2, 3, 4, 2, 0, 1, 1]
    geometry["daily_component_count"] = 1
    geometry["exterior_perimeter_km"] = geometry.groupby("id")[
        "daily_exterior_perimeter_km"
    ].cumsum()
    result = add_active_front_features(features, _sequences(), geometry)
    assert np.isfinite(result.loc[:, ACTIVE_FRONT_FEATURE_COLUMNS]).all().all()
    assert result.loc[result.id == 1, "recent_new_to_cumulative_perimeter"].iloc[0] > 0


def test_weather_features_use_only_days_through_snapshot():
    features = pd.DataFrame({"id": [1], "snapshot_day": [3]})
    weather = pd.DataFrame(
        {
            "id": [1, 1, 1, 1],
            "event_day": [1, 2, 3, 4],
            "vpd_kpa": [1.0, 2.0, 3.0, 99.0],
            "wind_speed_m_s": [2.0, 2.0, 2.0, 99.0],
            "fuel_moisture_100hr_pct": [10.0, 9.0, 8.0, 99.0],
            "energy_release_component": [20.0, 21.0, 22.0, 99.0],
            "precipitation_mm": [0.0, 1.0, 0.0, 99.0],
        }
    )
    result = add_weather_features(features, weather)
    assert np.isfinite(result.loc[:, WEATHER_FEATURE_COLUMNS]).all().all()
    assert result.recent_vpd_kpa.iloc[0] == 2.0
    assert result.log1p_recent_precipitation_mm.iloc[0] == np.log1p(1.0)


def test_next_day_weather_features_are_explicitly_future_only():
    features = pd.DataFrame({"id": [1], "snapshot_day": [3]})
    weather = pd.DataFrame(
        {
            "id": [1, 1, 1, 1],
            "event_day": [1, 2, 3, 4],
            "vpd_kpa": [1.0, 2.0, 3.0, 4.0],
            "wind_speed_m_s": [2.0, 2.0, 2.0, 5.0],
            "fuel_moisture_100hr_pct": [10.0, 9.0, 8.0, 7.0],
            "energy_release_component": [20.0, 21.0, 22.0, 23.0],
            "precipitation_mm": [0.0, 1.0, 0.0, 2.0],
        }
    )
    result = add_next_day_weather_features(features, weather)
    assert np.isfinite(result.loc[:, NEXT_DAY_WEATHER_FEATURE_COLUMNS]).all().all()
    assert result.next_day_vpd_kpa.iloc[0] == 4.0
    assert result.log1p_next_day_precipitation_mm.iloc[0] == np.log1p(2.0)


def test_terminal_weather_changes_and_active_day_metric_are_defined():
    weather = _sequences().rename(columns={"daily_area_km2": "vpd_kpa"})
    weather["wind_speed_m_s"] = 2.0
    weather["fuel_moisture_100hr_pct"] = 10.0
    weather["energy_release_component"] = 20.0
    weather["precipitation_mm"] = 0.0
    changes = terminal_weather_changes(weather, snapshot_day=2, window_days=2)
    active = active_day_terminal_fraction(_sequences(), active_days=2)
    assert len(changes) == 2
    assert len(active) == 2
    assert np.isfinite(active.active_day_terminal_growth_fraction).all()
