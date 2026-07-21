import unittest

import numpy as np

from fire_model_scaling.geometry import circle_polygon
from fire_model_scaling.metrics import measure_mask, rasterize_polygon


class MetricTests(unittest.TestCase):
    def test_raster_perimeter_bias_decreases_with_resolution(self):
        fine_polygon = circle_polygon((100.0, 100.0), 40.0, n=512)
        coarse_polygon = fine_polygon / 2.0
        fine = rasterize_polygon(fine_polygon, (220, 220))
        coarse = rasterize_polygon(coarse_polygon, (110, 110))
        fine_record = measure_mask(
            fine,
            model="test",
            implementation_type="test",
            scenario="test",
            replicate=0,
            initial_shape="compact",
            resolution=1.0,
            time=1.0,
        )
        coarse_record = measure_mask(
            coarse,
            model="test",
            implementation_type="test",
            scenario="test",
            replicate=0,
            initial_shape="compact",
            resolution=2.0,
            time=1.0,
        )
        true_perimeter = 2 * np.pi * 40.0
        fine_error = abs(fine_record.exterior_perimeter - true_perimeter)
        coarse_error = abs(coarse_record.exterior_perimeter - true_perimeter)
        self.assertLessEqual(fine_error, coarse_error * 1.2)

    def test_edge_touching_geometry_is_flagged(self):
        mask = np.zeros((20, 20), dtype=bool)
        mask[:5, :5] = True
        record = measure_mask(
            mask,
            model="test",
            implementation_type="test",
            scenario="test",
            replicate=0,
            initial_shape="compact",
            resolution=1.0,
            time=1.0,
        )
        self.assertTrue(record.domain_edge_contact)


if __name__ == "__main__":
    unittest.main()
