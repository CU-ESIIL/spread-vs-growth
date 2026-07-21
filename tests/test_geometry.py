import math
import unittest

import numpy as np

from fire_model_scaling.geometry import (
    circle_polygon,
    exact_ellipse_area,
    exact_ellipse_perimeter,
    polygon_area,
    polygon_perimeter,
    scaled_polygon,
)


class GeometryTests(unittest.TestCase):
    def test_circle_area_perimeter_are_accurate(self):
        radius = 10.0
        polygon = circle_polygon((0.0, 0.0), radius, n=2048)
        self.assertAlmostEqual(polygon_area(polygon), math.pi * radius * radius, delta=0.1)
        self.assertAlmostEqual(polygon_perimeter(polygon), 2 * math.pi * radius, delta=0.01)

    def test_exact_ellipse_area_perimeter_are_positive(self):
        area = exact_ellipse_area(12.0, 4.0)
        perimeter = exact_ellipse_perimeter(12.0, 4.0)
        self.assertAlmostEqual(area, math.pi * 12.0 * 4.0)
        self.assertGreater(perimeter, 0.0)

    def test_uniform_scaling_area_perimeter_relationship(self):
        polygon = np.array([[0.0, 0.0], [3.0, 0.0], [2.0, 2.0], [0.0, 1.0]])
        base_area = polygon_area(polygon)
        base_perimeter = polygon_perimeter(polygon)
        scaled = scaled_polygon(polygon, 5.0)
        self.assertAlmostEqual(polygon_area(scaled), base_area * 25.0)
        self.assertAlmostEqual(polygon_perimeter(scaled), base_perimeter * 5.0)


if __name__ == "__main__":
    unittest.main()
