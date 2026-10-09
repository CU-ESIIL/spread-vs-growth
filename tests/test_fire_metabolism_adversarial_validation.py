import numpy as np
import pandas as pd

from fire_metabolism.adversarial_validation import (
    attach_future_dynamics,
    binary_metrics,
    fit_loglog_scaling,
    geometric_detection_table,
    synthetic_counterexamples,
)


def test_loglog_fit_recovers_exact_two_thirds_and_prefers_it_to_half():
    area = np.geomspace(1.0, 128.0, 12)
    perimeter = 4.2 * area ** (2.0 / 3.0)
    fit = fit_loglog_scaling(area, perimeter)
    assert np.isclose(fit.slope, 2.0 / 3.0)
    assert fit.ci_lower <= 2.0 / 3.0 <= fit.ci_upper
    assert fit.sse_two_thirds < fit.sse_half


def _merged_sequences() -> pd.DataFrame:
    rows = []
    for event_id, year in ((1, 2010), (2, 2017)):
        for day in range(1, 13):
            area = float(day**2)
            rows.append(
                {
                    "id": event_id,
                    "ig_year": year,
                    "event_day": day,
                    "daily_area_km2": area - float((day - 1) ** 2),
                    "cumulative_area_km2": area,
                    "total_perimeter_km": 5.0 * area ** (2.0 / 3.0),
                    "exterior_perimeter_km": 4.0 * area ** (2.0 / 3.0),
                    "component_count": 1,
                    "hole_count": 0,
                }
            )
    return pd.DataFrame(rows)


def test_geometric_detector_requires_persistence_across_snapshots():
    detection = geometric_detection_table(
        _merged_sequences(), snapshot_days=(5, 7, 10)
    )
    assert detection.exterior_detected.all()
    first = detection.groupby("id", sort=False).head(1)
    later = detection.drop(first.index)
    assert not first.persistent_detection.any()
    assert later.persistent_detection.all()


def test_future_targets_use_only_rows_after_snapshot_for_outcome():
    sequences = _merged_sequences()
    features = pd.DataFrame(
        {
            "id": [1, 2],
            "snapshot_day": [5, 5],
            "ig_year": [2010, 2017],
            "recent_growth_acceleration": [1.0, -1.0],
        }
    )
    result = attach_future_dynamics(features, sequences, horizon=3)
    assert np.allclose(result.origin_area_km2, 25.0)
    assert np.allclose(result.future_area_km2, 64.0)
    assert result.future_accelerating.all()


def test_binary_metrics_report_balanced_accuracy_and_error_rates():
    result = binary_metrics(
        [True, True, False, False], [True, False, True, False]
    )
    assert result["balanced_accuracy"] == 0.5
    assert result["false_positive_rate"] == 0.5
    assert result["false_negative_rate"] == 0.5


def test_synthetic_controls_do_not_equate_two_thirds_with_mechanism():
    controls = synthetic_counterexamples().set_index("counterexample")
    geometric = controls.loc["non_metabolic_two_thirds"]
    assert bool(geometric.detector_accepts_two_thirds)
    assert not bool(geometric.mechanism_identified)
    alternative = controls.loc["alternative_succeeds"]
    assert alternative.linear_absolute_error < alternative.two_thirds_absolute_error
    assert controls.loc["latent_state_swap", "forcing_difference"] == 0.0
