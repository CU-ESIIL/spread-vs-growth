import unittest

import numpy as np

from fire_metabolism.scaling import (
    apparent_two_thirds_from_changing_intercept,
    between_size_experiment,
    boundary_bridge,
    compare_perimeter_hypotheses,
    compare_scaling_models,
    dimensional_k_length_power,
    excess_ratio_change,
    fit_between_events,
    fit_within_event,
    local_slope_decomposition,
    loglog_slope,
    matching_efficiency,
    matching_ratio,
    rolling_scaling_slopes,
    series_flux,
    trajectory_experiment,
)


class ScalingTests(unittest.TestCase):
    def test_boundary_bridge_is_conditional_ratio(self):
        self.assertAlmostEqual(boundary_bridge(2, 4 / 3), 2 / 3)

    def test_two_thirds_requires_compact_area_for_four_thirds_boundary(self):
        self.assertNotAlmostEqual(boundary_bridge(1.8, 4 / 3), 2 / 3)

    def test_excess_perimeter_exponent_given_two_thirds_closure(self):
        self.assertAlmostEqual(excess_ratio_change(64, 2 / 3), 2)

    def test_constant_excess_perimeter_gives_half_slope(self):
        self.assertAlmostEqual(excess_ratio_change(64, 0.5), 1)

    def test_dimensional_k_at_two_thirds(self):
        self.assertAlmostEqual(dimensional_k_length_power(2 / 3), -1 / 3)

    def test_k_is_dimensionless_only_at_half(self):
        self.assertEqual(dimensional_k_length_power(0.5), 0)

    def test_local_slope_decomposition(self):
        self.assertAlmostEqual(local_slope_decomposition(0.5, 1 / 6, np.log(10), 0), 2 / 3)

    def test_changing_intercept_can_fake_two_thirds(self):
        area = np.geomspace(1, 1e6, 100)
        perimeter = apparent_two_thirds_from_changing_intercept(area)
        self.assertAlmostEqual(loglog_slope(area, perimeter), 2 / 3, places=12)

    def test_scaling_experiments_have_distinct_metadata(self):
        area = np.array([1, 4, 16], dtype=float)
        perimeter = 4 * np.sqrt(area)
        between = between_size_experiment(area, perimeter, resolution=10)
        through_time = trajectory_experiment(np.array([0, 1, 2]), area, perimeter)
        self.assertNotEqual(between.experiment, through_time.experiment)

    def test_percolation_comparison_requires_convention(self):
        with self.assertRaises(ValueError):
            compare_perimeter_hypotheses(4 / 3, "")
        result = compare_perimeter_hypotheses(4 / 3, "accessible exterior at 30 m")
        self.assertAlmostEqual(result["accessible_external_perimeter"], 0)

    def test_matching_curve_maximum_at_one(self):
        values = matching_efficiency(np.array([0.5, 1.0, 2.0]))
        self.assertEqual(np.argmax(values), 1)

    def test_matching_preferred_dimension_is_inserted(self):
        self.assertAlmostEqual(matching_ratio(1.7, 1.7), 1)
        self.assertAlmostEqual(matching_ratio(4 / 3, 4 / 3), 1)

    def test_equal_series_resistances_not_unique_flux_maximum(self):
        equal = series_flux(1, 2, 2)
        lower_one = series_flux(1, 1, 2)
        self.assertGreater(lower_one, equal)

    def test_within_event_api_refuses_pooling(self):
        records = [
            {"event_id": "a", "area": 1, "perimeter": 4, "perimeter_convention": "outer"},
            {"event_id": "b", "area": 4, "perimeter": 8, "perimeter_convention": "outer"},
        ]
        with self.assertRaises(ValueError):
            fit_within_event(records)

    def test_between_event_api_requires_one_final_record(self):
        records = [
            {"event_id": "a", "area": 1, "perimeter": 4},
            {"event_id": "a", "area": 4, "perimeter": 8},
        ]
        with self.assertRaises(ValueError):
            fit_between_events(records)

    def test_scaling_model_comparison_includes_fixed_and_free_exponents(self):
        area = np.geomspace(1, 1e4, 30)
        perimeter = 3 * area**0.5
        models = compare_scaling_models(area, perimeter)
        self.assertEqual({model["model"] for model in models}, {"sigma_free", "sigma_one_half", "sigma_two_thirds"})
        best = min(models, key=lambda model: model["aic"])
        self.assertIn(best["model"], {"sigma_free", "sigma_one_half"})

    def test_changing_exponent_is_estimated_in_explicit_windows(self):
        area = np.geomspace(1, 1e6, 60)
        perimeter = np.where(area < 1e3, area**0.5, area ** (2 / 3) / 1e0)
        slopes = rolling_scaling_slopes(area, perimeter, window=15)
        self.assertGreater(slopes[-1], slopes[0])


if __name__ == "__main__":
    unittest.main()
