import numpy as np
import pandas as pd

from fire_metabolism.final_state_audit import (
    add_normalized_geometry,
    average_precision,
    binary_performance,
    rank_auc,
)


def test_normalizations_are_origin_safe_algebraic_reparameterizations():
    frame = pd.DataFrame({
        "log_exterior_perimeter": np.log([4.0, 8.0]),
        "log_origin_area": np.log([2.0, 4.0]),
        "recent_log_exterior_perimeter_change": [0.2, 0.3],
        "recent_area_fraction": [0.25, 0.5],
    })
    result = add_normalized_geometry(frame, 0.595)
    assert np.allclose(result.z_one_half, frame.log_exterior_perimeter - 0.5 * frame.log_origin_area)
    assert np.isfinite(result.filter(like="delta_z_").to_numpy()).all()


def test_binary_metrics_are_exact_for_perfect_ranking():
    observed = [0, 0, 1, 1]
    probability = [0.1, 0.2, 0.8, 0.9]
    assert rank_auc(observed, probability) == 1.0
    assert average_precision(observed, probability) == 1.0
    metrics = binary_performance(observed, probability, 0.5)
    assert metrics["balanced_accuracy"] == 1.0
    assert metrics["f1"] == 1.0
