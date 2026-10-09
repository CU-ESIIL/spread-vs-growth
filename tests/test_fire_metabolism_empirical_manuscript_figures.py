from pathlib import Path

import numpy as np
import pandas as pd

from fire_metabolism.empirical_manuscript_figures import (
    HALF_POWER,
    TWO_THIRDS,
    EmpiricalFigureInputs,
    build_detection_prediction_figures,
    detection_panel_data,
    past_trajectory,
    prediction_panel_data,
    select_detection_examples,
    validate_figure_inputs,
)


VALIDATION_DIR = Path("outputs/adversarial_validation")
INPUTS = EmpiricalFigureInputs(
    validation_dir=VALIDATION_DIR,
    sequences_path=Path("outputs/fired_prediction/fired_sequences.csv.gz"),
    geometry_path=Path(
        "outputs/fired_lifecycle_prediction/fired_geometry_sequences.csv.gz"
    ),
)


def _tables() -> dict[str, pd.DataFrame]:
    return {
        "detection_windows": pd.read_csv(VALIDATION_DIR / "detection_windows.csv.gz"),
        "detection_summary": pd.read_csv(VALIDATION_DIR / "detection_summary.csv"),
        "detection_robustness": pd.read_csv(
            VALIDATION_DIR / "detection_robustness.csv"
        ),
        "forecast_metrics": pd.read_csv(VALIDATION_DIR / "forecast_metrics.csv"),
        "paired_model_comparisons": pd.read_csv(
            VALIDATION_DIR / "paired_model_comparisons.csv"
        ),
        "transition_metrics": pd.read_csv(
            VALIDATION_DIR / "transition_metrics.csv"
        ),
        "paired_transition_comparisons": pd.read_csv(
            VALIDATION_DIR / "paired_transition_comparisons.csv"
        ),
    }


def test_locked_figure_inputs_exist_and_reference_values_are_exact():
    validate_figure_inputs(INPUTS)
    assert HALF_POWER == 0.5
    assert TWO_THIRDS == 2.0 / 3.0


def test_plotted_detection_summaries_match_locked_outputs():
    data = detection_panel_data(_tables())
    np.testing.assert_allclose(
        data["summary"].median_exterior_slope,
        [0.675713, 0.650036, 0.646507, 0.631073, 0.622455],
        atol=1e-6,
    )
    np.testing.assert_allclose(
        data["summary"].geometric_detection_fraction,
        [0.266414, 0.421550, 0.492105, 0.547126, 0.551724],
        atol=1e-6,
    )
    examples = select_detection_examples(_tables()["detection_windows"])
    assert examples.evidence_class.tolist() == [
        "Compatible",
        "Ambiguous",
        "Inconsistent",
    ]
    assert examples.id.astype(int).tolist() == [368519, 386652, 352569]


def test_plotted_prediction_summaries_match_locked_outputs():
    data = prediction_panel_data(_tables())
    geometry = data["forecast"][data["forecast"].model.eq("geometry_proxy")]
    np.testing.assert_allclose(
        geometry.mean_absolute_log_error,
        [0.122051, 0.217113, 0.310152, 0.366128],
        atol=1e-6,
    )
    paired = data["geometry_increment"].sort_values("horizon_days")
    np.testing.assert_allclose(
        paired.mean_difference,
        [-0.017452, -0.064135, -0.075710, -0.076669],
        atol=1e-6,
    )
    transition = data["transition"]
    np.testing.assert_allclose(
        transition.balanced_accuracy,
        [0.582686, 0.687626, 0.691625, 0.789856],
        atol=1e-6,
    )


def test_past_trajectory_excludes_future_rows_and_columns():
    frame = pd.DataFrame(
        {
            "id": [1, 1, 1, 1],
            "event_day": [1, 2, 3, 4],
            "daily_area_km2": [1.0, 1.0, 1.0, 1.0],
            "cumulative_area_km2": [1.0, 2.0, 3.0, 999.0],
            "exterior_perimeter_km": [2.0, 3.0, 4.0, 999.0],
            "reported_final_area_km2": [999.0] * 4,
        }
    )
    result = past_trajectory(frame, event_id=1, snapshot_day=3)
    assert result.event_day.max() == 3
    assert "reported_final_area_km2" not in result.columns
    assert result.cumulative_area_km2.max() == 3.0


def test_figure_generation_is_deterministic(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    manifest_one = build_detection_prediction_figures(INPUTS, first, dpi=300)
    manifest_two = build_detection_prediction_figures(INPUTS, second, dpi=300)
    for name in ("figure_detection.svg", "figure_prediction.svg"):
        first_text = (first / name).read_text(encoding="utf-8")
        second_text = (second / name).read_text(encoding="utf-8")
        assert first_text == second_text
    assert manifest_one["reference_exponents"] == manifest_two["reference_exponents"]
    assert not manifest_one["future_derived_predictors_recomputed"]
