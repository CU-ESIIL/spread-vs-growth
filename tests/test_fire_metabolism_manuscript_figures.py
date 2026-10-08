import numpy as np

from fire_metabolism.manuscript_figures import (
    LifeCycleParameters,
    run_life_cycle_validation,
    simulate_fire_life_cycle,
    transformed_area_forecast,
)


def test_life_cycle_area_is_cumulative_and_stages_are_ordered():
    trajectory = simulate_fire_life_cycle()
    assert np.all(np.diff(trajectory.area) >= 0)
    assert np.all(trajectory.growth_rate >= -1e-7)
    stage_indices = list(trajectory.stage_indices.values())
    assert stage_indices == sorted(stage_indices)
    assert len(set(stage_indices)) == 4
    peak = trajectory.stage_indices["Peak / endgame"]
    assert peak == int(np.argmax(trajectory.growth_rate))
    assert trajectory.growth_rate[-1] < 0.1 * trajectory.growth_rate[peak]


def test_life_cycle_is_deterministic():
    first = simulate_fire_life_cycle(LifeCycleParameters(beta_scale=2.0))
    second = simulate_fire_life_cycle(LifeCycleParameters(beta_scale=2.0))
    np.testing.assert_allclose(first.area, second.area)
    np.testing.assert_allclose(first.sigma_edge, second.sigma_edge)


def test_life_cycle_lines_follow_two_thirds_and_kinematic_closures():
    parameters = LifeCycleParameters()
    trajectory = simulate_fire_life_cycle(parameters)
    np.testing.assert_allclose(
        trajectory.growth_rate,
        trajectory.beta * trajectory.area ** (2 / 3),
        rtol=1e-12,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        trajectory.growth_rate,
        trajectory.effective_velocity * trajectory.active_perimeter,
        rtol=1e-12,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        trajectory.active_perimeter,
        parameters.perimeter_coefficient * trajectory.connectivity * trajectory.area ** (2 / 3),
        rtol=1e-12,
        atol=1e-12,
    )
    expected_coupling = np.clip(
        2.0 * trajectory.matching_efficiency * np.sqrt(trajectory.connectivity * trajectory.fuel_fraction),
        0.0,
        1.0,
    )
    np.testing.assert_allclose(trajectory.coupling, expected_coupling)
    np.testing.assert_allclose(trajectory.sigma_edge, 0.5 + trajectory.coupling / 6.0)


def test_forecast_uses_supplied_history_only():
    trajectory = simulate_fire_life_cycle()
    origin = 130
    target_time = trajectory.time[origin] + 4.0
    baseline = transformed_area_forecast(trajectory.time[: origin + 1], trajectory.area[: origin + 1], target_time, 2 / 3)
    mutated_future = trajectory.area.copy()
    mutated_future[origin + 1 :] *= 1000
    repeated = transformed_area_forecast(trajectory.time[: origin + 1], mutated_future[: origin + 1], target_time, 2 / 3)
    assert baseline == repeated


def test_synthetic_validation_reports_robustness_and_all_models():
    records, summary = run_life_cycle_validation(n_runs=12, seed=4)
    assert summary["scope"].startswith("synthetic")
    assert summary["monotonic_area_fraction"] == 1.0
    assert summary["ordered_stage_fraction"] == 1.0
    assert len(records) == 12 * 3 * 4
    assert {row["model"] for row in records} == {
        "no growth",
        "linear area",
        "square-root area",
        "cube-root area",
    }
