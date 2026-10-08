#!/usr/bin/env python3
"""Test persistent-course area potential versus realized FIRED outcomes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu

from fire_metabolism.fired_outcomes import fit_standardized_ridge
from fire_metabolism.fired_realization import (
    assign_realization_group,
    summarize_realization_groups,
    terminal_growth_diagnostics,
)
from fire_metabolism.fired_survival import (
    MECHANISTIC_SURVIVAL_FEATURE_COLUMNS,
    STATE_FEATURE_COLUMNS,
    add_observed_states,
)


FEATURE_COLUMNS = MECHANISTIC_SURVIVAL_FEATURE_COLUMNS + STATE_FEATURE_COLUMNS
GROUP_LABELS = {
    "high_confidence_true_persistent": "True persistent, high confidence",
    "high_confidence_early_ending": "Predicted persistent, ended early",
    "other_true_persistent": "Other true persistent",
    "other_ordinary": "Other ordinary",
}
GROUP_COLORS = {
    "high_confidence_true_persistent": "#1B9E77",
    "high_confidence_early_ending": "#D55E00",
    "other_true_persistent": "#56B4E9",
    "other_ordinary": "#A7A9AC",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sequences",
        type=Path,
        default=Path("outputs/fired_prediction/fired_sequences.csv.gz"),
    )
    parser.add_argument(
        "--features",
        type=Path,
        default=Path("outputs/fired_lifecycle_prediction/snapshot_features.csv.gz"),
    )
    parser.add_argument(
        "--probabilities",
        type=Path,
        default=Path(
            "outputs/fired_persistence_damage/held_out_persistent_regime_probabilities.csv.gz"
        ),
    )
    parser.add_argument(
        "--candidates",
        type=Path,
        default=Path(
            "outputs/fired_persistence_damage/external_termination_like_candidates.csv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/fired_realization_gap"),
    )
    parser.add_argument("--snapshot-day", type=int, default=7)
    return parser.parse_args()


def tune_persistent_area_model(
    development: pd.DataFrame,
    calibration: pd.DataFrame,
) -> tuple[object, pd.DataFrame]:
    rows = []
    models = {}
    for alpha in (0.1, 1.0, 10.0, 100.0, 1000.0):
        model = fit_standardized_ridge(
            development,
            np.log(development.final_area_km2.to_numpy(dtype=float)),
            feature_columns=FEATURE_COLUMNS,
            alpha=alpha,
        )
        predicted = np.maximum(
            calibration.snapshot_area_km2.to_numpy(dtype=float),
            np.exp(model.predict(calibration)),
        )
        error = np.abs(
            np.log(predicted / calibration.final_area_km2.to_numpy(dtype=float))
        )
        rows.append(
            {
                "alpha": alpha,
                "calibration_mean_absolute_log_error": float(error.mean()),
                "calibration_typical_error_factor": float(np.exp(error.mean())),
            }
        )
        models[alpha] = model
    tuning = pd.DataFrame(rows)
    selected = float(
        tuning.loc[tuning.calibration_mean_absolute_log_error.idxmin(), "alpha"]
    )
    tuning["selected"] = tuning.alpha == selected
    return models[selected], tuning


def bootstrap_median_difference(
    first: np.ndarray,
    second: np.ndarray,
    *,
    seed: int = 20261005,
    replicates: int = 5000,
) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    differences = np.empty(replicates, dtype=float)
    for index in range(replicates):
        a = rng.choice(first, size=len(first), replace=True)
        b = rng.choice(second, size=len(second), replace=True)
        differences[index] = np.median(a) - np.median(b)
    return (
        float(np.median(first) - np.median(second)),
        float(np.quantile(differences, 0.025)),
        float(np.quantile(differences, 0.975)),
    )


def signature_sensitivity(frame: pd.DataFrame) -> pd.DataFrame:
    candidate = frame.realization_group == "high_confidence_early_ending"
    persistent = frame.realization_group == "high_confidence_true_persistent"
    rows = []
    for threshold in (0.15, 0.25, 0.35):
        candidate_abrupt = frame.loc[candidate, "terminal_growth_fraction_of_peak"] >= threshold
        persistent_abrupt = frame.loc[persistent, "terminal_growth_fraction_of_peak"] >= threshold
        odds_ratio, p_value = fisher_exact(
            [
                [int(candidate_abrupt.sum()), int((~candidate_abrupt).sum())],
                [int(persistent_abrupt.sum()), int((~persistent_abrupt).sum())],
            ]
        )
        rows.append(
            {
                "abrupt_threshold_fraction_of_peak": threshold,
                "candidate_abrupt_fraction": float(candidate_abrupt.mean()),
                "true_persistent_abrupt_fraction": float(persistent_abrupt.mean()),
                "fisher_odds_ratio": float(odds_ratio),
                "fisher_p_value": float(p_value),
            }
        )
    return pd.DataFrame(rows)


def plot_potential_realization(frame: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), constrained_layout=True)
    ax = axes[0]
    for group_name in (
        "other_ordinary",
        "other_true_persistent",
        "high_confidence_true_persistent",
        "high_confidence_early_ending",
    ):
        group = frame[frame.realization_group == group_name]
        ax.scatter(
            group.persistent_course_area_km2,
            group.final_area_km2,
            s=18 if "high_confidence" in group_name else 10,
            alpha=0.72 if "high_confidence" in group_name else 0.25,
            color=GROUP_COLORS[group_name],
            label=GROUP_LABELS[group_name],
        )
    lower = min(frame.persistent_course_area_km2.min(), frame.final_area_km2.min())
    upper = max(frame.persistent_course_area_km2.max(), frame.final_area_km2.max())
    ax.plot([lower, upper], [lower, upper], color="#202124", ls="--", lw=1.2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set(
        xlabel="Day-7 persistent-course area forecast (km2)",
        ylabel="Realized final area (km2)",
        title="Persistent-course potential versus realization",
    )
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, fontsize=7)

    ax = axes[1]
    order = [
        "high_confidence_true_persistent",
        "high_confidence_early_ending",
        "other_true_persistent",
        "other_ordinary",
    ]
    values = [
        frame.loc[frame.realization_group == name, "area_realization_fraction"]
        for name in order
    ]
    boxes = ax.boxplot(values, showfliers=False, patch_artist=True)
    for patch, name in zip(boxes["boxes"], order, strict=True):
        patch.set_facecolor(GROUP_COLORS[name])
        patch.set_alpha(0.75)
    ax.axhline(1.0, color="#202124", ls="--", lw=1.2)
    ax.set_yscale("log")
    ax.set_xticks(range(1, len(order) + 1))
    ax.set_xticklabels(["True\npersistent", "Ended\nearly", "Other\npersistent", "Other\nordinary"])
    ax.set(
        ylabel="Realized / persistent-course forecast",
        title="Fraction of the persistent course realized",
    )
    ax.grid(axis="y", alpha=0.2)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def plot_terminal_signatures(frame: pd.DataFrame, output: Path) -> None:
    selected = frame[
        frame.realization_group.isin(
            ["high_confidence_true_persistent", "high_confidence_early_ending"]
        )
    ].copy()
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)
    order = ["high_confidence_true_persistent", "high_confidence_early_ending"]
    axes[0].boxplot(
        [
            selected.loc[
                selected.realization_group == name,
                "terminal_growth_fraction_of_peak",
            ]
            for name in order
        ],
        showfliers=False,
        patch_artist=True,
        boxprops={"facecolor": "#D8E6F0"},
    )
    axes[0].axhline(0.10, color="#1B9E77", ls="--", lw=1.2, label="Gradual <= 0.10")
    axes[0].axhline(0.25, color="#D55E00", ls="--", lw=1.2, label="Abrupt >= 0.25")
    axes[0].set_xticks([1, 2])
    axes[0].set_xticklabels(["True persistent", "Predicted persistent,\nended early"])
    axes[0].set(
        ylabel="Final 3-day growth / peak smoothed growth",
        title="Growth remaining at mapped termination",
    )
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].grid(axis="y", alpha=0.2)

    categories = ["gradual_decline_like", "intermediate", "abrupt_truncation_like"]
    labels = ["Gradual", "Intermediate", "Abrupt"]
    x = np.arange(2)
    bottom = np.zeros(2)
    colors = ["#1B9E77", "#E6AB02", "#D55E00"]
    for category, label, color in zip(categories, labels, colors, strict=True):
        fractions = []
        for name in order:
            group = selected[selected.realization_group == name]
            fractions.append(float(np.mean(group.terminal_signature == category)))
        axes[1].bar(x, fractions, bottom=bottom, color=color, label=label)
        bottom += np.asarray(fractions)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(["True persistent", "Ended early"])
    axes[1].set_ylim(0, 1)
    axes[1].set(
        ylabel="Fraction of events",
        title="Retrospective terminal signatures",
    )
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].grid(axis="y", alpha=0.2)
    fig.savefig(output, dpi=240)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    sequences = pd.read_csv(args.sequences)
    features = add_observed_states(pd.read_csv(args.features), sequences)
    probabilities = pd.read_csv(args.probabilities)
    candidates = pd.read_csv(args.candidates)

    landmark = features[features.snapshot_day == args.snapshot_day].copy()
    development = landmark[landmark.ig_year <= 2012]
    calibration = landmark[landmark.ig_year.between(2013, 2015)]
    held_out = landmark[landmark.ig_year >= 2016].copy()
    persistent_day = float(development.death_day.quantile(0.90))
    development_persistent = development[development.death_day >= persistent_day]
    calibration_persistent = calibration[calibration.death_day >= persistent_day]
    model, tuning = tune_persistent_area_model(
        development_persistent,
        calibration_persistent,
    )
    held_out["persistent_course_area_km2"] = np.maximum(
        held_out.snapshot_area_km2.to_numpy(dtype=float),
        np.exp(model.predict(held_out)),
    )
    held_out["area_realization_fraction"] = (
        held_out.final_area_km2 / held_out.persistent_course_area_km2
    )

    probability = probabilities[
        (probabilities.snapshot_day == args.snapshot_day)
        & (probabilities.model == "geometry_state")
    ][
        [
            "id",
            "persistent_probability",
            "high_confidence_threshold",
            "high_confidence_persistent",
            "actual_persistent",
        ]
    ]
    held_out = held_out.merge(probability, on="id", validate="one_to_one")
    candidate_flags = candidates[["id", "strong_candidate"]].copy()
    held_out = held_out.merge(candidate_flags, on="id", how="left", validate="one_to_one")
    held_out["strong_candidate"] = held_out.strong_candidate.fillna(False).astype(bool)
    held_out["realization_group"] = assign_realization_group(held_out)
    terminal = terminal_growth_diagnostics(
        sequences[sequences.ig_year >= 2016],
        window_days=3,
        gradual_threshold=0.10,
        abrupt_threshold=0.25,
    )
    held_out = held_out.merge(terminal, on="id", validate="one_to_one")

    group_summary = summarize_realization_groups(held_out)
    sensitivity = signature_sensitivity(held_out)
    candidate = held_out[
        held_out.realization_group == "high_confidence_early_ending"
    ]
    true_persistent = held_out[
        held_out.realization_group == "high_confidence_true_persistent"
    ]
    difference, difference_low, difference_high = bootstrap_median_difference(
        candidate.area_realization_fraction.to_numpy(dtype=float),
        true_persistent.area_realization_fraction.to_numpy(dtype=float),
    )
    rank_test = mannwhitneyu(
        candidate.area_realization_fraction,
        true_persistent.area_realization_fraction,
        alternative="two-sided",
    )
    primary_signature = sensitivity[
        sensitivity.abrupt_threshold_fraction_of_peak == 0.25
    ].iloc[0]

    tuning.to_csv(output / "persistent_course_area_tuning.csv", index=False)
    held_out.to_csv(
        output / "held_out_realization_gap.csv.gz",
        index=False,
        compression="gzip",
    )
    group_summary.to_csv(output / "realization_group_summary.csv", index=False)
    sensitivity.to_csv(output / "terminal_signature_sensitivity.csv", index=False)
    plot_potential_realization(held_out, output / "potential_vs_realized_area.png")
    plot_terminal_signatures(held_out, output / "terminal_signatures.png")

    candidate_summary = group_summary.set_index("realization_group").loc[
        "high_confidence_early_ending"
    ]
    persistent_summary = group_summary.set_index("realization_group").loc[
        "high_confidence_true_persistent"
    ]
    report = {
        "design": {
            "snapshot_day": args.snapshot_day,
            "persistent_threshold_day": persistent_day,
            "persistent_course_area_definition": "final-area ridge trained only on development-period persistent fires and tuned only on calibration-period persistent fires",
            "realization_fraction_definition": "observed final area divided by persistent-course area forecast",
            "gradual_signature_definition": "mean growth during the final three mapped days at or below 10% of peak smoothed growth",
            "abrupt_signature_definition": "mean growth during the final three mapped days at or above 25% of peak smoothed growth",
        },
        "primary_results": {
            "early_ending_candidate_n": int(len(candidate)),
            "high_confidence_true_persistent_n": int(len(true_persistent)),
            "candidate_median_realization_fraction": float(
                candidate_summary.median_area_realization_fraction
            ),
            "true_persistent_median_realization_fraction": float(
                persistent_summary.median_area_realization_fraction
            ),
            "median_realization_difference_candidate_minus_persistent": difference,
            "median_realization_difference_ci95": [difference_low, difference_high],
            "mann_whitney_p_value": float(rank_test.pvalue),
            "candidate_gradual_fraction": float(
                candidate_summary.fraction_gradual_decline_like
            ),
            "candidate_abrupt_fraction": float(
                candidate_summary.fraction_abrupt_truncation_like
            ),
            "true_persistent_gradual_fraction": float(
                persistent_summary.fraction_gradual_decline_like
            ),
            "true_persistent_abrupt_fraction": float(
                persistent_summary.fraction_abrupt_truncation_like
            ),
            "abrupt_signature_odds_ratio": float(
                primary_signature.fisher_odds_ratio
            ),
            "abrupt_signature_fisher_p_value": float(
                primary_signature.fisher_p_value
            ),
        },
        "interpretation": [
            "The persistent-course forecast is an empirical upper-course proxy, not a physical maximum attainable area.",
            "The large realization gap supports a distinction between geometric growth potential and realized outcome.",
            "Gradual terminal decline is compatible with fuel exhaustion, barriers, weather deterioration, or suppression that acts progressively.",
            "Abrupt termination with substantial residual growth is compatible with hard barriers, abrupt weather change, suppression, observation truncation, or model error.",
            "FIRED alone cannot causally distinguish fuel restriction from suppression.",
        ],
    }
    (output / "run_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (output / "README.md").write_text(
        "# FIRED potential-to-realization outputs\n\n"
        "This retrospective diagnostic compares a day-7 persistent-course final-area "
        "forecast with realized final area and classifies terminal growth as gradual, "
        "intermediate, or abrupt. The forecast is not a physical maximum, and the "
        "terminal signatures do not identify suppression without external labels.\n",
        encoding="utf-8",
    )
    print(json.dumps(report["primary_results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
