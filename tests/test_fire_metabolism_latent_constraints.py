import numpy as np
import pandas as pd

from fire_metabolism.latent_constraints import (
    add_realization_residuals,
    assign_partition,
    attach_constraint_indicator,
    binary_scores,
    development_thresholds,
    fixed_center_prediction,
)


def test_locked_partitions_are_calendar_based():
    years = pd.Series([2001, 2012, 2013, 2015, 2016, 2020])
    assert assign_partition(years).tolist() == [
        "development", "development", "calibration", "calibration", "held_out", "held_out"
    ]


def test_realization_residual_is_negative_below_model_implied_growth():
    frame = pd.DataFrame(
        {
            "observed_mean_growth_km2_day": [1.0, 4.0],
            "origin_area_km2": [8.0, 8.0],
            "lead_days": [3, 3],
            "observed_future_area_km2": [11.0, 20.0],
        }
    )
    result = add_realization_residuals(frame, np.log1p([2.0, 2.0]))
    assert result.realization_residual_q.iloc[0] < 0
    assert result.realization_residual_q.iloc[1] > 0
    assert np.allclose(result.model_implied_future_area_km2, 14.0)


def test_constraint_thresholds_do_not_use_held_out_rows():
    frame = pd.DataFrame(
        {
            "lead_days": [1, 1, 1, 1],
            "partition": ["development", "calibration", "held_out", "held_out"],
            "realization_residual_q": [-2.0, 0.0, -100.0, 100.0],
        }
    )
    threshold = development_thresholds(frame, quantile=0.5)
    assert threshold.constraint_threshold_q.iloc[0] == -1.0
    classified = attach_constraint_indicator(frame, threshold)
    assert classified.constraint_like.tolist() == [1, 0, 1, 0]


def test_binary_scores_are_proper_and_finite():
    score = binary_scores([0, 1, 1, 0], [.1, .8, .7, .2])
    assert 0 <= score["brier"] <= 1
    assert np.isfinite(score["log_score"])


def test_fixed_center_prediction_uses_training_only_coefficient():
    train = pd.DataFrame({"sigma": [.4, .8], "delta_sigma": [.1, -.1]})
    evaluation = pd.DataFrame({"sigma": [.5, 2 / 3]})
    predicted = fixed_center_prediction(train, evaluation, 2 / 3)
    assert predicted.shape == (2,)
    assert predicted[1] == 2 / 3
