import numpy as np
import pandas as pd

from fire_metabolism.fired_survival import (
    DAMAGE_FEATURE_COLUMNS,
    STATE_SURVIVAL_FEATURE_COLUMNS,
    add_conformal_intervals,
    add_metabolic_damage_features,
    add_observed_states,
    conformal_interval_radius,
    fit_logistic_hazard,
    make_person_period_table,
    predict_death_distributions,
)


def _features() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "ig_year": [2001, 2002, 2003, 2004],
            "snapshot_day": [3, 3, 3, 3],
            "death_day": [5, 6, 7, 8],
            "recent_growth_acceleration": [1.0, -1.0, 0.0, 2.0],
        }
    )


def _sequences() -> pd.DataFrame:
    patterns = {
        1: [1.0, 2.0, 3.0],
        2: [2.0, 2.0, 1.0],
        3: [1.0, 1.0, 0.0],
        4: [1.0, 0.0, 2.0],
    }
    return pd.DataFrame(
        [
            {"id": event_id, "event_day": day, "daily_area_km2": value}
            for event_id, values in patterns.items()
            for day, value in enumerate(values, 1)
        ]
    )


def test_observed_states_use_only_snapshot_growth_history():
    states = add_observed_states(_features(), _sequences()).set_index("id")
    assert states.loc[1, "observed_state"] == "accelerating"
    assert states.loc[2, "observed_state"] == "declining"
    assert states.loc[3, "observed_state"] == "quiescent"
    assert states.loc[4, "observed_state"] == "reactivated"


def test_person_period_table_has_one_terminal_transition_per_event():
    states = add_observed_states(_features(), _sequences())
    table = make_person_period_table(states)
    assert table.groupby("id").terminal_transition.sum().eq(1).all()
    assert table.groupby("id").size().to_dict() == {1: 2, 2: 3, 3: 4, 4: 5}


def test_fitted_hazard_produces_valid_ordered_death_distributions():
    states = add_observed_states(_features(), _sequences())
    table = make_person_period_table(states)
    model = fit_logistic_hazard(
        table,
        feature_columns=STATE_SURVIVAL_FEATURE_COLUMNS,
        alpha=1.0,
    )
    predictions = predict_death_distributions(model, states, maximum_day=10)
    assert np.isfinite(predictions.death_log_score).all()
    assert (predictions.model_interval_lower <= predictions.predicted_death_day).all()
    assert (predictions.predicted_death_day <= predictions.model_interval_upper).all()


def test_conformal_intervals_cover_calibration_residual_radius():
    predictions = pd.DataFrame(
        {
            "snapshot_day": [3, 3, 3],
            "predicted_death_day": [5, 7, 9],
            "observed_death_day": [4, 9, 6],
            "error": [1, -2, 3],
        }
    )
    radius = conformal_interval_radius(predictions, coverage=0.8)
    result = add_conformal_intervals(predictions, radius, maximum_day=12)
    assert radius == 3
    assert (result.interval_lower <= result.predicted_death_day).all()
    assert (result.predicted_death_day <= result.interval_upper).all()


def test_metabolic_damage_features_are_past_only_and_finite():
    features = add_observed_states(_features(), _sequences())
    sequences = _sequences().copy()
    sequences["cumulative_area_km2"] = sequences.groupby("id").daily_area_km2.cumsum()
    damaged = add_metabolic_damage_features(features, sequences).set_index("id")
    assert np.isfinite(damaged.loc[:, DAMAGE_FEATURE_COLUMNS]).all().all()
    assert (
        damaged.loc[1, "log_cumulative_squared_beta_damage"]
        > damaged.loc[3, "log_cumulative_squared_beta_damage"]
    )
