import unittest

import numpy as np

from fire_metabolism.residence import finite_recruitment_exponential_rate, total_consumed_mass


class ResidenceTests(unittest.TestCase):
    def test_exponential_closed_form_before_and_after_stop(self):
        values = finite_recruitment_exponential_rate(np.array([0, 2, 5]), 3, 4, 2, 1)
        self.assertAlmostEqual(values[0], 0)
        self.assertAlmostEqual(values[1], 12 * (1 - np.exp(-2)))
        self.assertAlmostEqual(values[2], 12 * (1 - np.exp(-2)) * np.exp(-3))

    def test_power_persists_after_area_recruitment_stops(self):
        value = finite_recruitment_exponential_rate(3, 3, 4, 2, 1)
        self.assertGreater(float(value), 0)

    def test_integrated_consumption_equals_recruited_mass(self):
        times = np.linspace(0, 40, 20001)
        rate = finite_recruitment_exponential_rate(times, 3, 4, 2, 1)
        self.assertAlmostEqual(total_consumed_mass(times, rate), 4 * 3 * 2, delta=2e-4)


if __name__ == "__main__":
    unittest.main()
