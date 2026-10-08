import unittest

import numpy as np

from fire_metabolism.forecasting import (
    ForecastDesign,
    calibrate_beta_two_thirds,
    forecast_beta_sensitivity,
    forecast_two_thirds,
    monte_carlo_mean_area,
    transformed_moments_to_mean_area,
)


class ForecastingTests(unittest.TestCase):
    def test_calibration_reproduces_endpoint(self):
        beta = calibrate_beta_two_thirds(100, 2700, 0, 3)
        self.assertAlmostEqual(forecast_two_thirds(100, beta, 3), 2700)

    def test_design_prevents_future_data_leakage(self):
        with self.assertRaises(ValueError):
            ForecastDesign(0, 3, 2, 1)

    def test_back_transform_uncertainty_example(self):
        samples = np.array([2.0, 4.0])
        mean = samples.mean()
        variance = samples.var()
        third = np.mean((samples - mean) ** 3)
        self.assertAlmostEqual(transformed_moments_to_mean_area(mean, variance, third), 36)
        self.assertEqual(monte_carlo_mean_area(samples), 36)
        self.assertEqual(mean**3, 27)

    def test_beta_sensitivity(self):
        expected = 2 * (100 ** (1 / 3) + 4 * 2 / 3) ** 2
        self.assertAlmostEqual(forecast_beta_sensitivity(100, 4, 2), expected)


if __name__ == "__main__":
    unittest.main()
