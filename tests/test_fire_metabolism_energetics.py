import unittest

import numpy as np

from fire_metabolism.energetics import (
    conditional_power_slope,
    effective_energy_per_area,
    growth_exponent_from_factors,
    power_components,
    turbulent_trace_dimension,
)


class EnergeticsTests(unittest.TestCase):
    def test_flux_weighted_energy_example_is_five(self):
        self.assertAlmostEqual(effective_energy_per_area([1, 3], [2, 6]), 5)

    def test_unweighted_average_would_be_wrong(self):
        weighted = effective_energy_per_area([1, 3], [2, 6])
        self.assertNotEqual(weighted, np.mean([2, 6]))

    def test_whole_fire_power_keeps_residual_separate(self):
        self.assertEqual(power_components(8, 3), 11)

    def test_variable_active_fraction_changes_growth_exponent(self):
        self.assertAlmostEqual(growth_exponent_from_factors(2 / 3, -1 / 6), 1 / 2)
        self.assertAlmostEqual(growth_exponent_from_factors(2 / 3, -2 / 3), 0)

    def test_variable_speed_changes_growth_exponent(self):
        self.assertAlmostEqual(growth_exponent_from_factors(2 / 3, speed_exponent=1 / 6), 5 / 6)

    def test_power_exponent_requires_stable_prefactor(self):
        self.assertAlmostEqual(conditional_power_slope(2 / 3, -1 / 6), 1 / 2)

    def test_surface_intersection_is_conditional_model(self):
        self.assertAlmostEqual(turbulent_trace_dimension(7 / 3), 4 / 3)


if __name__ == "__main__":
    unittest.main()
