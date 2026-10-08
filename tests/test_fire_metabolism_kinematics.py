import unittest

import numpy as np

from fire_metabolism.kinematics import (
    aggregate_components,
    area_rate_residual,
    boundary_area_rate,
    swept_area_first_order,
)


class BoundaryKinematicsTests(unittest.TestCase):
    def test_uniform_normal_speed(self):
        result = boundary_area_rate([2, 2, 2, 2], [3, 3, 3, 3])
        self.assertAlmostEqual(result.total_rate, 24)
        self.assertAlmostEqual(result.mean_normal_speed, 3)

    def test_heterogeneous_normal_speed(self):
        result = boundary_area_rate([1, 2, 3], [1, 2, 4])
        self.assertAlmostEqual(result.tracked_rate, 17)

    def test_partially_active_boundary(self):
        result = boundary_area_rate([2, 2, 2, 2], [1, 1, 1, 1], [1, 0, 1, 0])
        self.assertAlmostEqual(result.active_fraction, 0.5)
        self.assertAlmostEqual(result.tracked_rate, 4)

    def test_hole_boundary_advancing_into_island_adds_area(self):
        # Hole-boundary speed is defined in the inward-to-hole growth direction.
        result = boundary_area_rate([10], [0.5])
        self.assertGreater(result.tracked_rate, 0)

    def test_multiple_components(self):
        components = [
            {"lengths": np.array([2, 2]), "speeds": np.array([1, 1])},
            {"lengths": np.array([3, 3]), "speeds": np.array([2, 2])},
        ]
        self.assertAlmostEqual(aggregate_components(components).tracked_rate, 16)

    def test_untracked_source_is_added_once(self):
        result = boundary_area_rate([4], [2], source_rate=5)
        self.assertEqual(result.tracked_rate, 8)
        self.assertEqual(result.total_rate, 13)

    def test_swept_area_matches_first_order_integral(self):
        self.assertAlmostEqual(swept_area_first_order([2, 3], [1, 4], 0.01), 0.14)

    def test_residual_detects_untracked_recruitment(self):
        self.assertAlmostEqual(area_rate_residual(13, 1, 2, 4), 5)

    def test_empty_active_set_has_no_mean_speed(self):
        result = boundary_area_rate([2, 2], [1, 1], [0, 0])
        self.assertIsNone(result.mean_normal_speed)
        self.assertEqual(result.tracked_rate, 0)


if __name__ == "__main__":
    unittest.main()
