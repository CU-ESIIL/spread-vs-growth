import unittest

import numpy as np

from fire_model_scaling.fit_scaling import ols_loglog
from fire_model_scaling.geometry import exact_ellipse_area, exact_ellipse_perimeter


class ScalingTests(unittest.TestCase):
    def test_regression_recovers_known_synthetic_exponent(self):
        area = np.geomspace(10.0, 100000.0, 30)
        perimeter = 3.0 * area**0.75
        _, sigma, _, ci_low, ci_high, _ = ols_loglog(area, perimeter)
        self.assertAlmostEqual(sigma, 0.75, places=6)
        self.assertLess(ci_low, 0.75)
        self.assertGreater(ci_high, 0.75)

    def test_exact_ellipse_benchmark_recovers_half(self):
        radii = np.geomspace(1.0, 100.0, 30)
        area = [exact_ellipse_area(2.0 * r, r) for r in radii]
        perimeter = [exact_ellipse_perimeter(2.0 * r, r) for r in radii]
        _, sigma, _, _, _, _ = ols_loglog(area, perimeter)
        self.assertAlmostEqual(sigma, 0.5, places=6)


if __name__ == "__main__":
    unittest.main()
