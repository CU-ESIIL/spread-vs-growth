import unittest

from fire_metabolism.worked_examples import reproduce_worked_examples


class WorkedExampleRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = reproduce_worked_examples()

    def test_example_1(self):
        self.assertAlmostEqual(self.results["example_1"]["sigma_hat"], 2 / 3)

    def test_example_2(self):
        result = self.results["example_2"]
        self.assertAlmostEqual(result["beta_hat_ha_one_third_day"], 9.28318, places=5)
        self.assertAlmostEqual(result["k_hat_km_ha_minus_two_thirds"], 0.185664, places=6)
        self.assertAlmostEqual(result["area_rate_day3_ha_day"], 1800)
        self.assertAlmostEqual(result["effective_speed_m_day"], 500)
        self.assertAlmostEqual(result["acceleration_day3_ha_day2"], 800)

    def test_example_3(self):
        result = self.results["example_3"]
        self.assertAlmostEqual(result["area_day4_ha"], 4929.63, places=2)
        self.assertAlmostEqual(result["area_day5_ha"], 8137.04, places=2)

    def test_example_4(self):
        expected = [(100, 4, 200, 0.04), (2700, 36, 1800, 0.01333), (4929.63, 53.78, 2688.89, 0.01091), (8137.04, 75.11, 3755.56, 0.00923)]
        for actual, target in zip(self.results["example_4"], expected, strict=True):
            self.assertAlmostEqual(actual["area_ha"], target[0], places=2)
            self.assertAlmostEqual(actual["perimeter_km"], target[1], places=2)
            self.assertAlmostEqual(actual["area_rate_ha_day"], target[2], places=2)
            self.assertAlmostEqual(actual["perimeter_area_km_ha"], target[3], places=5)

    def test_example_5(self):
        result = self.results["example_5"]
        self.assertAlmostEqual(result["power_over_temperature_w_k"], 1.63934e7, delta=50)
        self.assertAlmostEqual(result["power_over_perimeter_w_m"], 1.38889e5, delta=1)
        self.assertAlmostEqual(result["energy_per_area_day0_j_m2"] / 1e6, 216)
        self.assertAlmostEqual(result["energy_per_area_day3_j_m2"] / 1e6, 24)

    def test_example_6(self):
        result = self.results["example_6"]
        self.assertAlmostEqual(result["remaining_time_days"], 1.02605, places=5)
        self.assertAlmostEqual(result["frozen_rate_time_days"], 1.27778, places=5)

    def test_example_7(self):
        result = self.results["example_7"]
        self.assertAlmostEqual(result["reduced_area_day5_ha"], 4929.63, places=2)
        self.assertAlmostEqual(result["reduced_to_baseline_ratio"], 0.60583, places=5)
        self.assertAlmostEqual(result["beta_max_from_day0"], 7.47490, places=5)
        self.assertAlmostEqual(result["rho_max_from_day0"], 0.80521, places=5)
        self.assertAlmostEqual(result["beta_max_from_day3"], 4.76249, places=5)
        self.assertAlmostEqual(result["rho_max_from_day3"], 0.51302, places=5)


if __name__ == "__main__":
    unittest.main()
