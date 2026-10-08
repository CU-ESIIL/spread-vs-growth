import numpy as np
import pandas as pd

from fire_metabolism.fired_lifecycle import (
    LIFECYCLE_FEATURE_COLUMNS,
    describe_lifecycle_outcomes,
    fit_neighbor_index,
    make_lifecycle_features,
    merge_geometry_sequences,
    neighbor_predict,
    smooth_daily_growth,
    tune_neighbor_count,
)


def _sequences() -> pd.DataFrame:
    rows = []
    growth_patterns = {
        1: [1, 2, 4, 3, 2, 1, 0, 0],
        2: [2, 1, 1, 2, 4, 3, 1, 0],
        3: [1, 1, 1, 1, 1, 1, 1, 1],
    }
    for event_id, daily in growth_patterns.items():
        cumulative = np.cumsum(daily)
        for day, (increment, area) in enumerate(zip(daily, cumulative), 1):
            rows.append(
                {
                    "id": event_id,
                    "ig_year": 2000 + event_id,
                    "lc_name": "Grasslands",
                    "event_day": day,
                    "date": pd.Timestamp(2000 + event_id, 1, day),
                    "daily_area_km2": float(increment),
                    "cumulative_area_km2": float(area),
                    "reported_final_area_km2": float(cumulative[-1]),
                    "reconstructed_final_area_km2": float(cumulative[-1]),
                }
            )
    return pd.DataFrame(rows)


def _geometry() -> pd.DataFrame:
    rows = []
    for event_id, event in _sequences().groupby("id"):
        for row in event.iloc[::2].itertuples(index=False):
            area = row.cumulative_area_km2
            rows.append(
                {
                    "id": event_id,
                    "event_day": row.event_day,
                    "polygon_area_km2": area,
                    "total_perimeter_km": 5 * area ** (2 / 3),
                    "exterior_perimeter_km": 4 * area ** (2 / 3),
                    "component_count": 1 + int(row.event_day > 4),
                    "hole_count": int(row.event_day > 5),
                }
            )
    return pd.DataFrame(rows)


def test_merge_geometry_carries_detection_geometry_through_calendar_gaps():
    merged = merge_geometry_sequences(_sequences(), _geometry())
    event = merged[merged.id == 1].sort_values("event_day")
    assert not event.total_perimeter_km.isna().any()
    assert event.loc[event.event_day == 2, "total_perimeter_km"].iloc[0] == event.loc[
        event.event_day == 1, "total_perimeter_km"
    ].iloc[0]


def test_lifecycle_outcomes_distinguish_growth_peak_and_last_growth_day():
    outcomes = describe_lifecycle_outcomes(_sequences(), smoothing_window=1).set_index("id")
    assert outcomes.loc[1, "growth_peak_day"] == 3
    assert outcomes.loc[1, "death_day"] == 6
    assert outcomes.loc[2, "growth_peak_day"] == 5
    assert outcomes.loc[2, "death_day"] == 7


def test_lifecycle_features_are_past_only_and_finite():
    merged = merge_geometry_sequences(_sequences(), _geometry())
    features = make_lifecycle_features(merged, snapshot_day=5, horizons=(1, 3))
    assert set(LIFECYCLE_FEATURE_COLUMNS).issubset(features.columns)
    assert np.isfinite(features.loc[:, LIFECYCLE_FEATURE_COLUMNS]).all().all()
    event = features.set_index("id").loc[1]
    assert event.snapshot_area_km2 == 12
    assert event.area_horizon_1_km2 == 13
    assert event.area_horizon_3_km2 == 13


def test_neighbor_predictions_and_calibration_are_deterministic():
    frame = pd.DataFrame({"x": [0.0, 1.0, 2.0, 3.0]})
    index = fit_neighbor_index(frame, ("x",))
    neighbors = index.neighbor_indices(pd.DataFrame({"x": [0.2, 2.8]}), 3)
    target = np.array([0.0, 10.0, 20.0, 30.0])
    np.testing.assert_allclose(neighbor_predict(target, neighbors, 1), [0.0, 30.0])
    selected, curve = tune_neighbor_count(
        target,
        np.array([0.0, 30.0]),
        neighbors,
        candidates=(1, 2, 3),
    )
    assert selected == 1
    assert curve.loc[curve.calibration_mae.idxmin(), "hyperparameter"] == 1


def test_growth_smoother_preserves_length_and_nonnegative_values():
    daily = np.array([0.0, 1.0, 4.0, 1.0, 0.0])
    smoothed = smooth_daily_growth(daily, window=3)
    assert len(smoothed) == len(daily)
    assert np.all(smoothed >= 0)
    assert int(np.argmax(smoothed)) == 2
