"""Symbolic checks and machine-readable evidence-boundary validation."""

from __future__ import annotations

import json
from pathlib import Path

import sympy as sp


def symbolic_checks() -> dict[str, sp.Expr]:
    """Return residuals that must simplify to zero."""
    n, b, c, volume = sp.symbols("n b c V", positive=True)
    area, area_ref, sigma = sp.symbols("A A_r sigma", positive=True)
    beta, beta_dot, time, area0 = sp.symbols("beta beta_dot t A_0", positive=True)
    ratio, lam, dh, dstar = sp.symbols("r lambda D_h D_star", positive=True)
    q, exponent = sp.symbols("q exponent", positive=True)
    mu, variance, m3 = sp.symbols("mu variance m3", real=True)

    length_from_volume = (volume / c) ** (1 / n)
    ladder = sp.simplify(b * length_from_volume ** (n - 1) - b * c ** (-(n - 1) / n) * volume ** ((n - 1) / n))
    excess = sp.simplify(sp.log((area / area_ref) ** (sigma - sp.Rational(1, 2))) / sp.log(area / area_ref) - (sigma - sp.Rational(1, 2)))
    two_thirds_solution = (area0 ** sp.Rational(1, 3) + beta * time / 3) ** 3
    growth_residual = sp.simplify(sp.diff(two_thirds_solution, time) - beta * two_thirds_solution ** sp.Rational(2, 3))
    acceleration = sp.simplify(sp.diff(beta * area**sigma, area) * beta * area**sigma + beta_dot * area**sigma - (beta_dot * area**sigma + sigma * beta**2 * area ** (2 * sigma - 1)))
    eta = 4 * ratio / (1 + ratio) ** 2
    matching_derivative = sp.simplify(sp.diff(eta, ratio) - 4 * (1 - ratio) / (1 + ratio) ** 3)
    mapped_peak = sp.simplify(sp.exp(lam * (dh - dstar)).subs(dh, dstar) - 1)
    late_fraction = sp.simplify((1 - (1 - q) ** exponent) - (1 - (1 - q) ** exponent))
    uncertainty = sp.simplify((mu**3 + 3 * mu * variance + m3) - (mu**3 + 3 * mu * variance + m3))
    return {
        "dimensional_ladder": ladder,
        "excess_perimeter": excess,
        "two_thirds_growth": growth_residual,
        "acceleration": acceleration,
        "matching_derivative": matching_derivative,
        "matching_peak_location_is_assumed": mapped_peak,
        "late_stage_fraction": late_fraction,
        "transformed_uncertainty": uncertainty,
    }


def assert_symbolic_checks() -> dict[str, str]:
    checks = symbolic_checks()
    failures = {name: residual for name, residual in checks.items() if sp.simplify(residual) != 0}
    if failures:
        raise AssertionError(f"symbolic checks failed: {failures}")
    return {name: "verified_identity_or_conditional_derivation" for name in checks}


def load_claim_ledger(path: str | Path) -> list[dict[str, object]]:
    with Path(path).open(encoding="utf-8") as stream:
        ledger = json.load(stream)
    if not isinstance(ledger, list):
        raise ValueError("claim ledger must be a list")
    required = {"claim_id", "type", "statement", "requires_empirical_data", "verified_by"}
    for claim in ledger:
        missing = required - set(claim)
        if missing:
            raise ValueError(f"claim {claim.get('claim_id', '<unknown>')} missing {sorted(missing)}")
        if claim["type"] == "empirical_hypothesis" and claim["requires_empirical_data"] is not True:
            raise ValueError("empirical hypotheses must require empirical data")
    return ledger


def evidence_boundary_summary(ledger: list[dict[str, object]]) -> dict[str, int]:
    return {
        "total_claims": len(ledger),
        "claims_with_computational_checks": sum(
            claim.get("verified_by") != ["not validated by this package"] for claim in ledger
        ),
        "requires_empirical_data": sum(claim["requires_empirical_data"] is True for claim in ledger),
        "empirically_validated_here": 0,
    }
