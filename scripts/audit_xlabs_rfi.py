#!/usr/bin/env python3
"""Audit proposal-facing wildfire metrics and prospective sample-size claims.

The audit reads locked repository outputs. When a draft RFI PDF is supplied,
it also extracts each response with ``pdftotext`` and counts portal characters.
Run with the environment that supplies pandas and a Parquet engine, for example:

    ../cubedynamics/.venv/bin/python scripts/audit_xlabs_rfi.py \
      --rfi-pdf /path/to/nsf_xlabs_rfi.pdf
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from pathlib import Path
from statistics import NormalDist

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "outputs" / "xlabs_rfi_audit"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rfi-pdf", type=Path, help="Draft RFI PDF to character-count")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def extract_responses(pdf_path: Path) -> pd.DataFrame:
    completed = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    text = completed.stdout.replace("\f", "\n")
    rows: list[dict[str, object]] = []
    for question in range(1, 29):
        next_question = question + 1
        if question < 28:
            terminator = rf"(?=\n\s*Q{next_question}\. |\n\s*4\.[0-9]\. |\Z)"
        else:
            terminator = r"(?=\Z)"
        pattern = rf"Q{question}\. .*?Response:\s*(.*?){terminator}"
        match = re.search(pattern, text, flags=re.DOTALL)
        if match is None:
            raise ValueError(f"Could not extract Q{question} response from {pdf_path}")
        response = re.sub(r"\s+", " ", match.group(1)).strip()
        rows.append(
            {
                "question": question,
                "characters_including_spaces": len(response),
                "portal_limit": 1300,
                "characters_remaining": 1300 - len(response),
                "within_limit": len(response) <= 1300,
            }
        )
    return pd.DataFrame(rows)


def proposal_metrics() -> pd.DataFrame:
    metrics = pd.read_csv(ROOT / "outputs/final_state_audit/target_horizon_metrics.csv")
    paired = pd.read_csv(ROOT / "outputs/final_state_audit/paired_model_comparisons.csv")
    models = ["M1_dynamics", "M2_raw_perimeter", "M4_full_geometry"]
    area = metrics[
        metrics["target"].eq("future_mapped_area") & metrics["model"].isin(models)
    ].copy()
    wide = area.pivot(index="horizon_days", columns="model", values="held_out_score")

    def paired_ci(horizon: int, comparator: str) -> tuple[float, float, float]:
        row = paired[
            paired["target"].eq("future_mapped_area")
            & paired["horizon_days"].eq(horizon)
            & paired["first_model"].eq("M4_full_geometry")
            & paired["second_model"].eq(comparator)
        ].iloc[0]
        return (
            float(row["loss_difference_first_minus_second"]),
            float(row["ci95_lower"]),
            float(row["ci95_upper"]),
        )

    rows: list[dict[str, object]] = []
    for horizon, values in wide.sort_index().iterrows():
        geometry = float(values["M4_full_geometry"])
        dynamics = float(values["M1_dynamics"])
        perimeter = float(values["M2_raw_perimeter"])
        vs_dynamics = paired_ci(int(horizon), "M1_dynamics")
        vs_perimeter = paired_ci(int(horizon), "M2_raw_perimeter")
        rows.append(
            {
                "horizon_days": int(horizon),
                "dynamics_mae_log_area": dynamics,
                "perimeter_mae_log_area": perimeter,
                "full_geometry_mae_log_area": geometry,
                "dynamics_typical_error_factor": math.exp(dynamics),
                "perimeter_typical_error_factor": math.exp(perimeter),
                "full_geometry_typical_error_factor": math.exp(geometry),
                "full_geometry_skill_vs_dynamics": 1.0 - geometry / dynamics,
                "geometry_minus_dynamics": vs_dynamics[0],
                "geometry_minus_dynamics_ci95_lower": vs_dynamics[1],
                "geometry_minus_dynamics_ci95_upper": vs_dynamics[2],
                "geometry_minus_perimeter": vs_perimeter[0],
                "geometry_minus_perimeter_ci95_lower": vs_perimeter[1],
                "geometry_minus_perimeter_ci95_upper": vs_perimeter[2],
            }
        )
    return pd.DataFrame(rows)


def prospective_sample_sizes() -> pd.DataFrame:
    predictions = pd.read_parquet(
        ROOT / "outputs/final_state_audit/held_out_predictions.parquet"
    )
    predictions = predictions[
        predictions["target_name"].eq("future_mapped_area")
        & predictions["model"].isin(
            ["M1_dynamics", "M2_raw_perimeter", "M4_full_geometry"]
        )
    ]
    z_alpha = NormalDist().inv_cdf(0.975)
    rows: list[dict[str, object]] = []
    for horizon in sorted(predictions["lead_days"].dropna().unique()):
        horizon_rows = predictions[predictions["lead_days"].eq(horizon)]
        paired = horizon_rows.pivot_table(
            index=["id", "origin_day"], columns="model", values="loss", aggfunc="first"
        ).dropna()
        event_loss = paired.groupby(level="id").mean()
        for comparator in ["M1_dynamics", "M2_raw_perimeter"]:
            differences = event_loss["M4_full_geometry"] - event_loss[comparator]
            mean_difference = float(differences.mean())
            sd_difference = float(differences.std(ddof=1))
            standardized_effect = abs(mean_difference) / sd_difference
            result: dict[str, object] = {
                "horizon_days": int(horizon),
                "comparison": f"M4_full_geometry minus {comparator}",
                "held_out_fires": int(differences.size),
                "mean_event_loss_difference": mean_difference,
                "event_difference_sd": sd_difference,
                "standardized_paired_effect": standardized_effect,
            }
            for power in [0.80, 0.90]:
                z_power = NormalDist().inv_cdf(power)
                result[f"approx_fires_for_{int(power * 100)}pct_power"] = math.ceil(
                    ((z_alpha + z_power) / standardized_effect) ** 2
                )
            result["approx_ci95_half_width_at_100_fires"] = (
                z_alpha * sd_difference / math.sqrt(100)
            )
            result["approx_ci95_half_width_at_300_fires"] = (
                z_alpha * sd_difference / math.sqrt(300)
            )
            rows.append(result)
    return pd.DataFrame(rows)


def transition_metrics() -> pd.DataFrame:
    metrics = pd.read_csv(
        ROOT / "outputs/adversarial_validation/transition_metrics.csv"
    )
    paired = pd.read_csv(
        ROOT / "outputs/adversarial_validation/paired_transition_comparisons.csv"
    )
    selected = metrics[
        metrics["snapshot_day"].eq(7)
        & metrics["target"].isin(["future_accelerating", "peak_in_window"])
        & metrics["model"].isin(["dynamics_ridge", "geometry_proxy"])
    ].copy()
    selected = selected[
        [
            "snapshot_day",
            "horizon_days",
            "target",
            "model",
            "n_events",
            "precision",
            "recall",
            "balanced_accuracy",
            "brier_score",
            "balanced_accuracy_ci95_lower",
            "balanced_accuracy_ci95_upper",
        ]
    ]
    comparisons = paired[
        paired["snapshot_day"].eq(7)
        & paired["target"].isin(["future_accelerating", "peak_in_window"])
        & paired["first_model"].eq("geometry_proxy")
        & paired["second_model"].eq("dynamics_ridge")
    ][
        [
            "target",
            "balanced_accuracy_difference",
            "ci95_lower",
            "ci95_upper",
            "probability_first_better",
        ]
    ]
    selected = selected.merge(comparisons, on="target", how="left")
    dynamics_brier = (
        selected[selected["model"].eq("dynamics_ridge")]
        .set_index("target")["brier_score"]
        .to_dict()
    )
    selected["relative_brier_reduction_vs_dynamics"] = selected.apply(
        lambda row: (
            1.0 - row["brier_score"] / dynamics_brier[row["target"]]
            if row["model"] == "geometry_proxy"
            else 0.0
        ),
        axis=1,
    )
    return selected.sort_values(["target", "model"])


def rare_event_design() -> pd.DataFrame:
    detection = pd.read_csv(ROOT / "outputs/final_state_audit/detection_metrics.csv")
    deficit_prevalence = float(
        detection.loc[detection["model"].eq("D0_prevalence"), "prevalence"].iloc[0]
    )

    transitions = pd.read_csv(ROOT / "outputs/adversarial_validation/transition_metrics.csv")
    peak = transitions[
        transitions["snapshot_day"].eq(7)
        & transitions["target"].eq("peak_in_window")
        & transitions["model"].eq("geometry_proxy")
    ].iloc[0]
    peak_prevalence = float((peak["tp"] + peak["fn"]) / peak["n_events"])

    survival_report = json.loads(
        (ROOT / "outputs/fired_state_survival/run_report.json").read_text()
    )
    long_prevalence = float(
        survival_report["duration_discrimination"][0]["prevalence"]
    )
    extreme_prevalence = float(
        survival_report["duration_discrimination"][1]["prevalence"]
    )

    targets = [
        ("major 3-day realization deficit", deficit_prevalence),
        ("peak transition in next 3 days", peak_prevalence),
        ("duration at least 22 days", long_prevalence),
        ("duration at least 29 days", extreme_prevalence),
    ]
    rows: list[dict[str, object]] = []
    for target, prevalence in targets:
        for incidents in [100, 300, 500]:
            rows.append(
                {
                    "target": target,
                    "observed_prevalence": prevalence,
                    "incidents": incidents,
                    "expected_positive_events": prevalence * incidents,
                    "expected_positive_events_per_regime_if_five_equal_regimes": (
                        prevalence * incidents / 5
                    ),
                }
            )
    return pd.DataFrame(rows)


def scaling_reconciliation() -> pd.DataFrame:
    population = pd.read_csv(
        ROOT / "outputs/geometric_manifold_validation/population_scaling.csv"
    )
    within_between = pd.read_csv(
        ROOT / "outputs/geometric_manifold_validation/within_between_scaling.csv"
    )
    selected = pd.concat(
        [
            population[population["partition"].isin(["all", "held_out"])],
            within_between[
                within_between["partition"].isin(["all", "held_out"])
                & within_between["estimand"].isin(["within", "between"])
            ],
        ],
        ignore_index=True,
    )
    return selected[
        [
            "partition",
            "estimand",
            "estimate",
            "ci95_lower",
            "ci95_upper",
            "n_observations",
            "n_fires",
            "distance_from_one_half",
            "distance_from_two_thirds",
        ]
    ].sort_values(["partition", "estimand"])


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics = proposal_metrics()
    sample_sizes = prospective_sample_sizes()
    transitions = transition_metrics()
    rare_events = rare_event_design()
    scaling = scaling_reconciliation()

    metrics.to_csv(output_dir / "proposal_metric_summary.csv", index=False)
    sample_sizes.to_csv(output_dir / "prospective_sample_size.csv", index=False)
    transitions.to_csv(output_dir / "transition_metric_summary.csv", index=False)
    rare_events.to_csv(output_dir / "rare_event_design.csv", index=False)
    scaling.to_csv(output_dir / "scaling_reconciliation.csv", index=False)

    character_summary: dict[str, object] | None = None
    if args.rfi_pdf:
        characters = extract_responses(args.rfi_pdf.resolve())
        characters.to_csv(output_dir / "rfi_character_counts.csv", index=False)
        character_summary = {
            "source": str(args.rfi_pdf.resolve()),
            "all_within_1300": bool(characters["within_limit"].all()),
            "maximum_characters": int(characters["characters_including_spaces"].max()),
            "median_characters": float(characters["characters_including_spaces"].median()),
            "total_unused_characters": int(characters["characters_remaining"].sum()),
        }

    seven_day = metrics[metrics["horizon_days"].eq(7)].iloc[0]
    seven_day_power = sample_sizes[sample_sizes["horizon_days"].eq(7)]
    acceleration = transitions[
        transitions["target"].eq("future_accelerating")
        & transitions["model"].eq("geometry_proxy")
    ].iloc[0]
    summary = {
        "inputs": {
            "final_state_audit": "outputs/final_state_audit",
            "geometric_manifold_validation": "outputs/geometric_manifold_validation",
            "adversarial_validation": "outputs/adversarial_validation",
            "state_survival": "outputs/fired_state_survival",
        },
        "rfi_character_summary": character_summary,
        "seven_day": {
            "dynamics_mae_log_area": float(seven_day["dynamics_mae_log_area"]),
            "perimeter_mae_log_area": float(seven_day["perimeter_mae_log_area"]),
            "full_geometry_mae_log_area": float(
                seven_day["full_geometry_mae_log_area"]
            ),
            "full_geometry_skill_vs_dynamics": float(
                seven_day["full_geometry_skill_vs_dynamics"]
            ),
            "full_geometry_typical_error_factor": float(
                seven_day["full_geometry_typical_error_factor"]
            ),
        },
        "seven_day_sample_size": seven_day_power.to_dict(orient="records"),
        "day_seven_acceleration_transition": {
            "n_events": int(acceleration["n_events"]),
            "balanced_accuracy": float(acceleration["balanced_accuracy"]),
            "balanced_accuracy_gain_vs_dynamics": float(
                acceleration["balanced_accuracy_difference"]
            ),
            "gain_ci95_lower": float(acceleration["ci95_lower"]),
            "gain_ci95_upper": float(acceleration["ci95_upper"]),
            "relative_brier_reduction_vs_dynamics": float(
                acceleration["relative_brier_reduction_vs_dynamics"]
            ),
        },
        "warnings": [
            "Power calculations assume the retrospective event-level paired effect and variance transfer prospectively.",
            "Daily FIRED area-loss effects do not justify a six-hour spatial Brier-score margin.",
            "Repeated forecast origins do not replace independent incident-level replication.",
            "Rare-event and regime-specific claims require separate sample-size targets.",
        ],
    }
    (output_dir / "audit_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
