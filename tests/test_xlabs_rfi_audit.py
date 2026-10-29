import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_xlabs_rfi.py"
SPEC = importlib.util.spec_from_file_location("audit_xlabs_rfi", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


def test_seven_day_proposal_metrics_match_locked_audit():
    row = audit.proposal_metrics().query("horizon_days == 7").iloc[0]
    assert row.full_geometry_mae_log_area == pytest.approx(0.4549361249679335)
    assert row.full_geometry_skill_vs_dynamics == pytest.approx(0.1333952776238041)
    assert row.geometry_minus_perimeter == pytest.approx(-0.0487014724292969)


def test_scaling_reconciliation_keeps_estimands_separate():
    scaling = audit.scaling_reconciliation()
    held_out = scaling[scaling.partition.eq("held_out")].set_index("estimand")
    assert held_out.loc["population", "estimate"] == pytest.approx(0.613287)
    assert held_out.loc["within", "estimate"] == pytest.approx(0.595040)
    assert held_out.loc["between", "estimate"] == pytest.approx(0.642610)


def test_transition_summary_preserves_predictive_gain_and_limit():
    transitions = audit.transition_metrics()
    acceleration = transitions[
        transitions.target.eq("future_accelerating")
        & transitions.model.eq("geometry_proxy")
    ].iloc[0]
    peak = transitions[
        transitions.target.eq("peak_in_window")
        & transitions.model.eq("geometry_proxy")
    ].iloc[0]
    assert acceleration.balanced_accuracy_difference == pytest.approx(
        0.098230, abs=1e-6
    )
    assert acceleration.relative_brier_reduction_vs_dynamics == pytest.approx(
        0.243159, rel=1e-4
    )
    assert peak.precision == pytest.approx(0.223684)
