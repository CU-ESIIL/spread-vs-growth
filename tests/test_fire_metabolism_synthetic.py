import unittest

import numpy as np

from fire_metabolism.synthetic import EXPERIMENT_STAGES, SpatialRunMetadata, factorial_design, rough_surface_projection, summarize_spatial_run


class SyntheticExperimentTests(unittest.TestCase):
    def test_all_required_stages_are_present(self):
        self.assertEqual(len(EXPERIMENT_STAGES), 13)

    def test_factorial_design_supports_mechanism_removal(self):
        design = factorial_design(["wind", "terrain", "spotting"])
        self.assertEqual(len(design), 8)
        self.assertIn((), design)
        self.assertIn(("wind", "terrain", "spotting"), design)

    def test_run_summary_calculates_required_metrics(self):
        area = np.array([1, 4, 9, 16], dtype=float)
        perimeter = 4 * np.sqrt(area)
        summary = summarize_spatial_run(area, perimeter, np.arange(4))
        self.assertAlmostEqual(summary["perimeter_area_slope"], 0.5)
        self.assertEqual(summary["area_rate"].shape, area.shape)

    def test_metadata_requires_resolution(self):
        with self.assertRaises(ValueError):
            SpatialRunMetadata(EXPERIMENT_STAGES[0], 0, 0, 1, ())

    def test_rough_surface_can_have_smooth_projected_boundary(self):
        x, y, z, mask = rough_surface_projection()
        self.assertTrue(np.nanstd(z) > 0)
        radii = np.sqrt(x[mask] ** 2 + y[mask] ** 2)
        self.assertLessEqual(radii.max(), 1.0)


if __name__ == "__main__":
    unittest.main()
