import numpy as np
import pandas as pd

from fire_metabolism.half_power_reaudit import (
    add_history_intercepts,
    fit_fixed_intercept,
    make_geometry_transitions,
    score_intercept_treatments,
)


def example_panel() -> pd.DataFrame:
    rows = []
    for event_id, intercept in ((1, 1.0), (2, 2.0)):
        for day, area in enumerate((1.0, 2.0, 4.0), start=1):
            rows.append(
                {
                    "id": event_id,
                    "ig_year": 2018,
                    "partition": "held_out",
                    "event_day": day,
                    "cumulative_area_km2": area,
                    "log_area": np.log(area),
                    "log_perimeter": intercept + 0.5 * np.log(area),
                }
            )
    return pd.DataFrame(rows)


def test_fixed_intercept_recovers_known_value():
    panel = example_panel()
    assert np.isclose(fit_fixed_intercept(panel[panel.id.eq(1)], 0.5), 1.0)


def test_origin_anchor_is_exact_for_generating_exponent():
    panel = example_panel()
    transitions = make_geometry_transitions(panel, leads=(1,))
    transitions = add_history_intercepts(transitions, panel, {"one_half": 0.5})
    scores = score_intercept_treatments(
        transitions,
        {"one_half": 0.5},
        {"one_half": 1.5},
        {"one_half": 1.5},
    )
    anchored = scores[scores.intercept_treatment.eq("origin_anchored")]
    assert np.allclose(anchored.error, 0.0)


def test_theoretical_anchored_divergence_is_area_ratio_to_one_sixth():
    panel = example_panel()
    transition = make_geometry_transitions(panel, leads=(2,)).iloc[0]
    assert np.isclose(transition.half_vs_two_thirds_ratio, transition.area_ratio ** (1 / 6))

