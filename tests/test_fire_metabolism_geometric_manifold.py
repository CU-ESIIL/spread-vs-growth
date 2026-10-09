import numpy as np
import pandas as pd

from fire_metabolism.geometric_manifold import (
    candidate_normalization_slopes,
    fire_specific_slopes,
    measurement_error_slopes,
    scaling_estimates,
    temporal_partition,
)


def synthetic_panel(within=0.6, between=0.72):
    rows = []
    for event_id, mean_x in enumerate(np.linspace(0.0, 4.0, 30), start=1):
        for event_day, offset in enumerate(np.linspace(-1.0, 1.0, 9), start=1):
            x = mean_x + offset
            mean_y = 1.0 + between * mean_x
            rows.append({
                "id": event_id,
                "ig_year": 2010 + event_id % 10,
                "event_day": event_day,
                "log_area": x,
                "log_perimeter": mean_y + within * offset,
                "cumulative_area_km2": np.exp(x),
                "perimeter_km": np.exp(mean_y + within * offset),
                "partition": "development",
            })
    return pd.DataFrame(rows)


def test_within_between_decomposition_recovers_distinct_exponents():
    estimates = scaling_estimates(synthetic_panel())
    assert np.isclose(estimates["within"], 0.6)
    assert np.isclose(estimates["between"], 0.72)
    assert estimates["within"] != estimates["between"]


def test_normalization_drift_is_exact_slope_difference():
    result = candidate_normalization_slopes(synthetic_panel(), [0.5, 2 / 3])
    assert np.isclose(result.iloc[0].within_normalization_drift, 0.1)
    assert np.isclose(result.iloc[1].within_normalization_drift, 0.6 - 2 / 3)


def test_fire_specific_eligibility_is_prospective_and_recovers_slope():
    result = fire_specific_slopes(synthetic_panel(), min_log_area_span=np.log(2))
    assert result.eligible.all()
    assert np.allclose(result.slope, 0.6)


def test_measurement_error_sensitivities_are_finite():
    result = measurement_error_slopes(synthetic_panel())
    assert np.isclose(result["ols_conditional"], 0.6)
    assert all(np.isfinite(value) for value in result.values())


def test_locked_temporal_partition():
    result = temporal_partition(pd.Series([2001, 2012, 2013, 2015, 2016, 2020, 2021]))
    assert result.tolist() == [
        "development", "development", "calibration", "calibration",
        "held_out", "held_out", "excluded",
    ]
