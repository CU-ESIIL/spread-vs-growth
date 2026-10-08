import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from fire_metabolism.fired_prediction import (
    reconstruct_daily_sequences,
    rolling_predictions,
    summarize_predictions,
    transformed_trend_forecast,
)


def example_records():
    return pd.DataFrame(
        {
            "id": [7, 7, 7, 7],
            "ig_date": ["2020-01-01"] * 4,
            "event_day": [1, 2, 4, 6],
            "event_dur": [6] * 4,
            "dy_ar_km2": [1.0, 3.0, 5.0, 7.0],
            "tot_ar_km2": [16.0] * 4,
            "ig_year": [2020] * 4,
            "lc_name": ["Grasslands"] * 4,
            "dominant_lc_name": ["Grasslands"] * 4,
        }
    )


class FiredPredictionTests(unittest.TestCase):
    def test_reconstruction_inserts_zero_growth_days(self):
        sequence = reconstruct_daily_sequences(example_records())
        np.testing.assert_allclose(sequence["daily_area_km2"], [1, 3, 0, 5, 0, 7])
        np.testing.assert_allclose(sequence["cumulative_area_km2"], [1, 4, 4, 9, 9, 16])

    def test_transformed_forecast_recovers_square_law(self):
        history = np.array([1.0, 4.0, 9.0, 16.0])
        self.assertAlmostEqual(transformed_trend_forecast(history, 2, 0.5), 36.0)

    def test_rolling_forecast_uses_only_pre_origin_history(self):
        sequence = reconstruct_daily_sequences(example_records())
        baseline = rolling_predictions(sequence, {"linear_area": 0.0}, lookback_days=3, horizons=(1,))
        changed = sequence.copy()
        changed.loc[changed["event_day"] == 6, "cumulative_area_km2"] = 1600.0
        alternate = rolling_predictions(changed, {"linear_area": 0.0}, lookback_days=3, horizons=(1,))
        key = (baseline["origin_day"] == 4) & (baseline["model"] == "linear_area")
        alt_key = (alternate["origin_day"] == 4) & (alternate["model"] == "linear_area")
        self.assertAlmostEqual(
            float(baseline.loc[key, "predicted_area_km2"].iloc[0]),
            float(alternate.loc[alt_key, "predicted_area_km2"].iloc[0]),
        )

    def test_summary_is_event_balanced(self):
        sequence = reconstruct_daily_sequences(example_records())
        predictions = rolling_predictions(sequence, {"linear_area": 0.0}, lookback_days=3, horizons=(1,))
        summary = summarize_predictions(predictions, bootstrap_replicates=0)
        self.assertEqual(set(summary["model"]), {"no_growth", "linear_area"})
        self.assertTrue((summary["n_events"] == 1).all())


if __name__ == "__main__":
    unittest.main()
