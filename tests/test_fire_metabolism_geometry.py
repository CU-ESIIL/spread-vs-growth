import math
import unittest

import numpy as np

from fire_metabolism.geometry import (
    connectivity,
    dimensional_ladder,
    ellipse_family,
    polygon_area,
    polygon_perimeter,
    right_angle_polygon,
    sample_polygon_boundary,
    similarity_boundary,
)
from fire_metabolism.scaling import box_count_resolution_experiment, loglog_slope


class DimensionalLadderTests(unittest.TestCase):
    def test_square_identity(self):
        self.assertAlmostEqual(similarity_boundary(25, 2, 1, 4), 20)

    def test_circle_identity(self):
        area = math.pi * 9
        self.assertAlmostEqual(similarity_boundary(area, 2, math.pi, 2 * math.pi), 6 * math.pi)

    def test_cube_identity(self):
        self.assertAlmostEqual(similarity_boundary(125, 3, 1, 6), 150)

    def test_sphere_identity(self):
        volume = (4 / 3) * math.pi * 8
        expected = (36 * math.pi) ** (1 / 3) * volume ** (2 / 3)
        self.assertAlmostEqual(similarity_boundary(volume, 3, 4 * math.pi / 3, 4 * math.pi), expected)

    def test_interval_boundary_count_is_constant(self):
        self.assertEqual(dimensional_ladder(1)["interval"][1], dimensional_ladder(10)["interval"][1])


class EllipseFamilyTests(unittest.TestCase):
    def test_fixed_aspect_ratio_ellipse_slope_is_half(self):
        area, perimeter, _ = ellipse_family(np.geomspace(1, 100, 40), aspect_ratio=3)
        self.assertAlmostEqual(loglog_slope(area, perimeter), 0.5, places=10)

    def test_varying_aspect_ratio_changes_apparent_slope(self):
        area, perimeter, _ = ellipse_family(np.geomspace(1, 100, 40), aspect_ratio=1, aspect_power=0.8)
        self.assertGreater(loglog_slope(area, perimeter), 0.5)


class RightAngleConstructionTests(unittest.TestCase):
    def test_right_angle_family_exact_coordinates(self):
        expected = {0: (1, 4, 1), 1: (64, 64, 2), 2: (4096, 1024, 4), 3: (262144, 16384, 8)}
        for generation, (area, perimeter, excess) in expected.items():
            with self.subTest(generation=generation):
                polygon = right_angle_polygon(generation)
                self.assertAlmostEqual(polygon_area(polygon.vertices), area)
                self.assertAlmostEqual(polygon_perimeter(polygon.vertices), perimeter)
                self.assertAlmostEqual(polygon.excess_perimeter, excess)

    def test_right_angle_family_has_between_size_slope_two_thirds(self):
        polygons = [right_angle_polygon(j) for j in range(4)]
        areas = np.array([polygon_area(item.vertices) for item in polygons])
        perimeters = np.array([polygon_perimeter(item.vertices) for item in polygons])
        self.assertAlmostEqual(loglog_slope(areas, perimeters), 2 / 3, places=12)

    def test_each_polygon_is_finite_rectilinear_boundary(self):
        polygon = right_angle_polygon(2)
        differences = np.diff(np.vstack((polygon.vertices, polygon.vertices[0])), axis=0)
        self.assertTrue(np.all((differences[:, 0] == 0) | (differences[:, 1] == 0)))

    def test_box_counting_metadata_keeps_resolution_experiment_separate(self):
        polygon = right_angle_polygon(1)
        samples = sample_polygon_boundary(polygon.vertices, 0.02)
        result = box_count_resolution_experiment(samples, np.array([2.0, 1.0, 0.5, 0.25]))
        self.assertEqual(result.experiment, "fixed_object_vary_resolution")
        self.assertIn("n_points", result.metadata)


class ConnectivityTests(unittest.TestCase):
    def test_connectivity_two_thirds_is_unrelated_statistic(self):
        self.assertAlmostEqual(connectivity(np.array([3, 6])), 2 / 3)


if __name__ == "__main__":
    unittest.main()
