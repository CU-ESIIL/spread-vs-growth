import numpy as np
import pandas as pd

from fire_metabolism.effective_coupling import (
    coupling_series,
    exact_growth_change_decomposition,
    recursive_area_forecasts,
)


def test_coupling_uses_start_of_day_area_and_excludes_day_one():
    event = pd.DataFrame({
        "event_day": [1, 2, 3],
        "daily_area_km2": [4.0, 5.0, 7.0],
        "cumulative_area_km2": [4.0, 9.0, 16.0],
    })
    result = coupling_series(event, sigma=0.5)
    assert result.event_day.tolist() == [2, 3]
    assert np.allclose(result.start_area_km2, [4.0, 9.0])
    assert np.allclose(result.effective_coupling, [2.5, 7.0 / 3.0])


def test_growth_change_decomposition_is_exact():
    result = exact_growth_change_decomposition(
        [4.0, 9.0], [1.0, 0.5], [0.8, 0.7], sigma=0.5
    )
    assert np.allclose(result.identity_residual, 0.0, atol=1e-12)


def test_recursive_area_forecast_uses_predicted_area_only():
    frame = pd.DataFrame({
        "id": [1, 1], "ig_year": [2018, 2018],
        "partition": ["held_out", "held_out"],
        "snapshot_day": [5, 5], "lead_days": [1, 2],
        "model": ["test", "test"], "snapshot_area_km2": [4.0, 4.0],
        "future_area_km2": [100.0, 200.0],
        "predicted_effective_coupling": [1.0, 1.0],
        "observable_at_target": [True, True],
    })
    result = recursive_area_forecasts(frame, sigma=0.5)
    assert np.isclose(result.predicted_area_km2.iloc[0], 6.0)
    assert np.isclose(result.predicted_area_km2.iloc[1], 6.0 + np.sqrt(6.0))
