from pathlib import Path

import numpy as np

from scripts.build_detection_prediction_concept_figure import build_figure, footprint, radial_profile


def test_radial_profile_and_footprint_are_finite_and_deterministic():
    theta, radius = radial_profile(12)
    assert len(theta) == len(radius) == 320
    assert np.all(radius > 0)
    first = footprint((0.5, 0.5), 0.2, 12)
    second = footprint((0.5, 0.5), 0.2, 12)
    assert np.allclose(first, second)
    assert np.isfinite(first).all()


def test_concept_figure_exports_all_formats(tmp_path: Path):
    paths = build_figure(tmp_path)
    assert {path.suffix for path in paths} == {".pdf", ".svg", ".png"}
    assert all(path.stat().st_size > 1_000 for path in paths)
    assert (tmp_path / "figure_caption.md").exists()
    assert (tmp_path / "figure_provenance.json").exists()
