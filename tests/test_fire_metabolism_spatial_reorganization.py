import numpy as np

from fire_metabolism.spatial_reorganization import (
    area_matched_dilation,
    binary_shape_metrics,
    deterministic_support,
    sliced_wasserstein,
    unbalanced_sinkhorn_distance,
)


def test_sliced_transport_identity_and_translation_normalization():
    mask = np.zeros((20, 20), dtype=bool)
    mask[4:10, 3:9] = True
    shifted = np.roll(mask, shift=4, axis=1)
    a, aw = deterministic_support(mask)
    b, bw = deterministic_support(shifted)
    assert sliced_wasserstein(a, aw, a, aw) == 0.0
    assert sliced_wasserstein(a, aw, b, bw) > 1.0
    assert sliced_wasserstein(a, aw, b, bw, translation_normalized=True) < 1e-10


def test_area_matched_null_and_simple_metrics():
    start = np.zeros((31, 31), dtype=bool)
    start[15, 15] = True
    expanded = area_matched_dilation(start, 60)
    metrics = binary_shape_metrics(expanded, expanded)
    assert expanded.sum() >= 60
    assert metrics["iou"] == 1.0
    assert metrics["symmetric_difference_area"] == 0.0


def test_unbalanced_transport_detects_spatial_difference_and_converges():
    a = np.array([[0.0, 0.0], [1.0, 0.0]])
    b = np.array([[2.0, 0.0], [3.0, 0.0]])
    weights = np.array([0.5, 0.5])
    same = unbalanced_sinkhorn_distance(a, weights, a, weights)
    moved = unbalanced_sinkhorn_distance(a, weights, b, weights)
    assert same.converged and moved.converged
    assert moved.distance > same.distance


def test_shape_metrics_distinguish_equal_area_organization():
    block = np.zeros((24, 24), dtype=bool)
    block[8:16, 8:16] = True
    split = np.zeros_like(block)
    split[4:8, 4:12] = True
    split[16:20, 12:20] = True
    assert block.sum() == split.sum()
    metrics = binary_shape_metrics(block, split)
    assert metrics["iou"] < 0.2
    assert metrics["symmetric_difference_area"] > 0
