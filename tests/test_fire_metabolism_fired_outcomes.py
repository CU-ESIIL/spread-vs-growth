import unittest

import numpy as np
import pandas as pd

from fire_metabolism.fired_outcomes import (
    BASE_FEATURE_COLUMNS,
    describe_fire_outcomes,
    fit_standardized_ridge,
    make_early_features,
)


def example_sequences():
    rows = []
    increments = {
        1: [1.0, 2.0, 0.0, 3.0, 4.0],
        2: [2.0, 1.0, 1.0, 2.0, 2.0],
    }
    for event_id, daily in increments.items():
        cumulative = np.cumsum(daily)
        for day, (growth, area) in enumerate(zip(daily, cumulative, strict=True), start=1):
            rows.append(
                {
                    "id": event_id,
                    "ig_year": 2010 + event_id,
                    "lc_name": "Grasslands",
                    "event_day": day,
                    "daily_area_km2": growth,
                    "cumulative_area_km2": area,
                }
            )
    return pd.DataFrame(rows)


class FiredOutcomeTests(unittest.TestCase):
    def test_grown_fire_descriptors(self):
        outcomes = describe_fire_outcomes(example_sequences(), snapshot_days=(3,))
        event = outcomes[outcomes["id"] == 1].iloc[0]
        self.assertEqual(event["final_area_km2"], 10.0)
        self.assertEqual(event["peak_growth_day"], 5)
        self.assertEqual(event["half_area_day"], 4)
        self.assertAlmostEqual(event["area_fraction_day_3"], 0.3)

    def test_early_predictors_do_not_use_later_growth(self):
        sequences = example_sequences()
        baseline = make_early_features(sequences, 3).set_index("id")
        changed = sequences.copy()
        mask = (changed["id"] == 1) & (changed["event_day"] > 3)
        changed.loc[mask, "daily_area_km2"] *= 20
        changed.loc[changed["id"] == 1, "cumulative_area_km2"] = np.cumsum(
            changed.loc[changed["id"] == 1, "daily_area_km2"]
        )
        alternate = make_early_features(changed, 3).set_index("id")
        np.testing.assert_allclose(
            baseline.loc[1, BASE_FEATURE_COLUMNS],
            alternate.loc[1, BASE_FEATURE_COLUMNS],
        )
        self.assertNotEqual(baseline.loc[1, "final_area_km2"], alternate.loc[1, "final_area_km2"])

    def test_standardized_ridge_recovers_linear_relation(self):
        frame = pd.DataFrame({"x": np.arange(1.0, 8.0), "z": np.arange(1.0, 8.0) ** 2})
        target = 2.0 + 3.0 * frame["x"] - 0.5 * frame["z"]
        model = fit_standardized_ridge(frame, target, feature_columns=("x", "z"), alpha=0)
        np.testing.assert_allclose(model.predict(frame), target, atol=1e-10)


if __name__ == "__main__":
    unittest.main()
