import unittest

import numpy as np
from scipy.integrate import solve_ivp

from fire_metabolism.growth import (
    analytic_area,
    apply_area_jumps,
    area_acceleration,
    beta_for_target,
    constant_beta_area,
    cube_root_rate,
    exponential_lifetime_exceedance,
    finite_speed_bound,
    finite_speed_crossing,
    late_stage_fraction,
    logarithmic_growth_rate,
    normalized_area,
    rate_change_ratio,
    two_thirds_accelerates,
)


class GrowthLawTests(unittest.TestCase):
    def test_constant_beta_two_thirds_solution(self):
        area = constant_beta_area(3, 100, 9.283177667225559, 2 / 3)
        self.assertAlmostEqual(area, 2700)

    def test_sigma_one_solution(self):
        self.assertAlmostEqual(float(constant_beta_area(2, 3, 0.5, 1)), 3 * np.e)

    def test_analytic_matches_numerical_multiple_exponents(self):
        for sigma in (0, 0.5, 2 / 3, 0.999, 1.0, 1.2):
            with self.subTest(sigma=sigma):
                area0, beta, horizon = 2.0, 0.15, 2.0
                solution = solve_ivp(lambda _t, y: beta * y**sigma, (0, horizon), [area0], rtol=1e-11, atol=1e-13)
                expected = float(constant_beta_area(horizon, area0, beta, sigma))
                self.assertAlmostEqual(solution.y[0, -1], expected, delta=1e-8)

    def test_invalid_superlinear_domain_is_explicit(self):
        with self.assertRaises(ValueError):
            analytic_area(10, 1, 2, 2)

    def test_normalized_growth_curves_share_initial_rate(self):
        step = 1e-6
        for sigma in (0, 0.5, 2 / 3, 1):
            derivative = (normalized_area(step, sigma) - normalized_area(0, sigma)) / step
            self.assertAlmostEqual(float(derivative), 1, places=5)

    def test_acceleration_identity_constant_beta(self):
        value = area_acceleration(27, 2, 0, 2 / 3)
        self.assertAlmostEqual(float(value), (2 / 3) * 4 * 3)

    def test_slowly_declining_beta_still_accelerates(self):
        self.assertTrue(two_thirds_accelerates(1000, 2, -0.1))

    def test_rapidly_declining_beta_decelerates(self):
        self.assertFalse(two_thirds_accelerates(1000, 2, -1))

    def test_log_growth_rate_identity(self):
        area, beta, sigma = 64, 2, 2 / 3
        area_dot = beta * area**sigma
        self.assertAlmostEqual(logarithmic_growth_rate(beta, 0.2, area, area_dot, sigma), 0.2 / beta + sigma * area_dot / area)

    def test_finite_speed_bound_eventually_conflicts_with_cubic_growth(self):
        crossing = finite_speed_crossing(1, 3, 1, 0.5, horizon=1e4)
        self.assertGreater(crossing, 0)
        after = crossing * 1.1
        self.assertGreater(constant_beta_area(after, 1, 3, 2 / 3), finite_speed_bound(after, 1, 0.5))

    def test_source_changes_cube_root_rate(self):
        self.assertNotAlmostEqual(cube_root_rate(100, 3, 10), 1)

    def test_discrete_jumps_are_separate(self):
        times = np.array([0, 1, 2, 3])
        result = apply_area_jumps(times, np.array([1, 2, 3, 4]), [2], [5])
        np.testing.assert_allclose(result, [1, 2, 8, 9])

    def test_late_stage_fraction(self):
        self.assertAlmostEqual(late_stage_fraction(3, 0.5), 7 / 8)
        self.assertAlmostEqual(late_stage_fraction(2, 0.5), 3 / 4)

    def test_exponential_termination_is_not_power_law(self):
        p1 = exponential_lifetime_exceedance(1, 1, 3, 1)
        p8 = exponential_lifetime_exceedance(8, 1, 3, 1)
        self.assertAlmostEqual(p8, p1**2)

    def test_rate_change_retains_finite_initial_area(self):
        self.assertNotAlmostEqual(rate_change_ratio(100, 9.283177667, 0.8, 5), 0.8**3)

    def test_target_below_start_is_invalid(self):
        with self.assertRaises(ValueError):
            beta_for_target(100, 50, 2)


if __name__ == "__main__":
    unittest.main()
