import unittest
from pathlib import Path

from fire_metabolism.diagnostics import assert_symbolic_checks, evidence_boundary_summary, load_claim_ledger
from fire_metabolism.units import AREA, LENGTH, TIME, beta_dimensions, perimeter_coefficient_dimensions


ROOT = Path(__file__).resolve().parents[1]


class DiagnosticTests(unittest.TestCase):
    def test_symbolic_residuals_reduce_to_zero(self):
        checks = assert_symbolic_checks()
        self.assertGreaterEqual(len(checks), 8)

    def test_claim_ledger_preserves_empirical_boundary(self):
        ledger = load_claim_ledger(ROOT / "claims" / "fire_metabolism_claims.json")
        summary = evidence_boundary_summary(ledger)
        self.assertGreater(summary["requires_empirical_data"], 0)
        self.assertEqual(summary["empirically_validated_here"], 0)

    def test_k_dimensions(self):
        self.assertAlmostEqual(perimeter_coefficient_dimensions(2 / 3).length, -1 / 3)

    def test_beta_dimensions(self):
        expected = AREA ** (1 / 3) / TIME
        actual = beta_dimensions(2 / 3)
        for observed, target in zip(actual.as_tuple(), expected.as_tuple(), strict=True):
            self.assertAlmostEqual(observed, target)
        self.assertNotEqual(LENGTH, AREA)


if __name__ == "__main__":
    unittest.main()
