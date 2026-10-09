import numpy as np
import pandas as pd

from fire_metabolism.geometric_attractor import (
    TWO_THIRDS,
    estimate_local_slopes,
    fit_fixed_attractor,
    fit_free_attractor,
    half_life_days,
    make_transitions,
    predict_future_sigma,
)


def synthetic_sequences(sigma: float = TWO_THIRDS) -> pd.DataFrame:
    area = np.geomspace(1.0, 32.0, 8)
    return pd.DataFrame({
        "id": 1,
        "ig_year": 2010,
        "event_day": np.arange(1, 9),
        "daily_area_km2": np.r_[area[0], np.diff(area)],
        "cumulative_area_km2": area,
        "exterior_perimeter_km": 3.0 * area**sigma,
        "total_perimeter_km": 3.2 * area**sigma,
        "component_count": 1,
        "hole_count": 0,
    })


def test_local_rolling_slope_recovers_power_law_without_future_rows():
    slopes = estimate_local_slopes(synthetic_sequences(), estimator="rolling_ols_5")
    assert np.allclose(slopes.sigma, TWO_THIRDS)
    assert slopes.event_day.min() == 5
    assert slopes.event_day.max() == 8


def test_transition_pairs_respect_requested_future_lead():
    slopes = estimate_local_slopes(synthetic_sequences(), estimator="rolling_ols_5")
    transitions = make_transitions(slopes, leads=(1, 3))
    assert (transitions.actual_lead_days >= transitions.lead_days).all()
    assert (transitions.actual_lead_days <= transitions.lead_days + 2).all()


def test_free_and_fixed_attractor_recover_known_dynamics():
    sigma = np.linspace(0.3, 1.0, 30)
    center = 0.62
    delta = -0.25 * (sigma - center)
    frame = pd.DataFrame({"sigma": sigma, "delta_sigma": delta})
    free = fit_free_attractor(frame)
    fixed = fit_fixed_attractor(frame, center)
    assert np.isclose(free.equilibrium, center)
    assert np.isclose(free.restoring_strength, 0.25)
    assert np.allclose(predict_future_sigma(fixed, sigma), sigma + delta)


def test_discrete_half_life():
    assert np.isclose(half_life_days(0.5, 1), 1.0)
    assert np.isnan(half_life_days(1.2, 1))
