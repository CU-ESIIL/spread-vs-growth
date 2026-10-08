import numpy as np
import pandas as pd

from fire_metabolism.fired_realization import (
    assign_realization_group,
    summarize_realization_groups,
    terminal_growth_diagnostics,
)


def test_terminal_growth_diagnostics_separate_gradual_and_abrupt_endings():
    sequences = pd.DataFrame(
        [
            {"id": event_id, "event_day": day, "daily_area_km2": value}
            for event_id, values in {
                1: [8.0, 7.0, 6.0, 1.0, 0.2, 0.1],
                2: [1.0, 2.0, 4.0, 6.0, 8.0, 7.0],
            }.items()
            for day, value in enumerate(values, 1)
        ]
    )
    result = terminal_growth_diagnostics(sequences).set_index("id")
    assert result.loc[1, "terminal_signature"] == "gradual_decline_like"
    assert result.loc[2, "terminal_signature"] == "abrupt_truncation_like"
    assert np.isfinite(result.terminal_growth_fraction_of_peak).all()


def test_realization_groups_are_explicitly_outcome_aware():
    frame = pd.DataFrame(
        {
            "high_confidence_persistent": [True, True, False, False],
            "actual_persistent": [True, False, True, False],
        }
    )
    assert assign_realization_group(frame).tolist() == [
        "high_confidence_true_persistent",
        "high_confidence_early_ending",
        "other_true_persistent",
        "other_ordinary",
    ]


def test_realization_summary_reports_area_and_signature_fractions():
    frame = pd.DataFrame(
        {
            "realization_group": ["candidate", "candidate", "persistent"],
            "area_realization_fraction": [0.25, 0.75, 1.0],
            "terminal_signature": [
                "gradual_decline_like",
                "abrupt_truncation_like",
                "gradual_decline_like",
            ],
        }
    )
    result = summarize_realization_groups(frame).set_index("realization_group")
    assert result.loc["candidate", "median_area_realization_fraction"] == 0.5
    assert result.loc["candidate", "fraction_gradual_decline_like"] == 0.5
    assert result.loc["candidate", "fraction_abrupt_truncation_like"] == 0.5
