#!/usr/bin/env python3
"""Re-audit every one-half result under explicit intercept treatments."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "half_power_reaudit"
TMP = ROOT / "tmp" / "half_power_reaudit"
TMP.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(TMP / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(TMP / "cache"))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm
from scipy.stats import spearmanr

from fire_metabolism.geometric_manifold import (
    bootstrap_scaling,
    prepare_geometry_panel,
    scaling_estimates,
)
from fire_metabolism.half_power_reaudit import (
    DEFAULT_SEED,
    add_history_intercepts,
    event_bootstrap_difference,
    fit_fixed_attractor_center,
    fit_fixed_intercept,
    make_geometry_transitions,
    predict_fixed_attractor,
    score_intercept_treatments,
    summarize_scores,
)


SEQUENCES = ROOT / "outputs" / "fired_prediction" / "fired_sequences.csv.gz"
GEOMETRY = ROOT / "outputs" / "fired_lifecycle_prediction" / "fired_geometry_sequences.csv.gz"
ATTRACTOR = ROOT / "outputs" / "geometric_attractor_validation" / "attractor_transition_data.csv.gz"
GROWTH_RESIDUALS = ROOT / "outputs" / "latent_constraint_validation" / "growth_residuals.parquet"
REPLICATES = 1000


def audit_inventory() -> pd.DataFrame:
    columns = [
        "analysis", "file", "function", "figure_table", "response_variable", "predictor",
        "exponent", "category", "intercept_treatment", "normalization_treatment",
        "fire_specific_information_used", "current_state_anchoring_used",
        "prospective_or_retrospective", "data_split", "original_conclusion",
        "requires_rerun", "reason",
    ]
    rows = [
        ["FIRED transformed-area forecasts", "src/fire_metabolism/fired_prediction.py", "transformed_trend_forecast", "outputs/fired_prediction/prediction_metrics.csv", "future cumulative area", "recent transformed-area trend", "0.5", "F", "origin anchored in transformed area", "history-specific trend", "observed area history", "yes", "prospective", "temporal held-out", "one-half temporal growth can forecast short horizons", "no", "Temporal area-growth test; not a perimeter-area law."],
        ["Prediction validation figure", "scripts/run_fired_prediction_tests.py", "make_figures", "prediction validation", "future cumulative area", "temporal trajectory", "0.5", "F", "origin anchored", "history-specific", "observed area history", "yes", "prospective", "temporal held-out", "one-half is a temporal benchmark", "no", "Retain as category F with explicit terminology."],
        ["Adversarial scaling detector", "src/fire_metabolism/adversarial_validation.py", "fit_loglog_scaling", "scaling detector", "log perimeter", "log area", "0.5", "C", "fitted per analysis window", "window-specific", "window geometry", "no", "retrospective", "locked temporal split", "two-thirds detector compared SSE with one-half", "yes", "A fitted intercept does not test a common normalization."],
        ["Adversarial future-area forecasts", "src/fire_metabolism/adversarial_validation.py", "transformed_forecasts", "forecast table", "future area", "temporal growth", "0.5", "F", "origin anchored", "history-specific", "observed history", "yes", "prospective", "held-out", "one-half was competitive for area forecasts", "no", "Category F only."],
        ["Lifecycle temporal forecasts", "scripts/run_fired_lifecycle_prediction.py", "prediction analyses", "prediction tables", "future area/death", "temporal trajectory", "0.5", "F", "origin/history conditioned", "history-specific", "observed history", "yes", "prospective", "held-out", "one-half area-growth benchmark", "no", "Not a geometric exponent test."],
        ["Geometric attractor forecast", "scripts/run_geometric_attractor_validation.py", "prediction_analysis", "attractor_prediction_metrics.csv", "future rolling slope", "current rolling slope", "0.5", "E", "not applicable", "fixed equilibrium center", "current local slope", "no", "prospective", "development/calibration/held-out", "one-half fixed center can beat two-thirds", "yes", "Must be relabeled local-slope shrinkage."],
        ["Half-vs-two-thirds constraint test", "scripts/run_half_vs_two_thirds_constraint_test.py", "load_losses", "relative_advantage_vs_residual.csv", "future rolling-slope loss difference", "realization residual q", "0.5", "E", "not applicable", "fixed equilibrium center", "current local slope", "no", "prospective association", "held-out", "deficits did not explain one-half competitiveness", "yes", "Preserve E result and add geometric intercept-stratified test."],
        ["Effective coupling temporal forecasts", "scripts/run_effective_coupling_validation.py", "forecast comparison", "forecast metrics", "future area/effective coupling", "temporal history", "0.5", "F", "origin/history conditioned", "history-specific", "observed history", "yes", "prospective", "held-out", "half-power is a temporal comparator", "no", "Not a perimeter-area law."],
        ["Geometric manifold population scaling", "scripts/run_geometric_manifold_validation.py", "population_and_decomposition", "population_scaling.csv", "log perimeter", "log area", "0.5", "B", "population fitted", "common within split", "none from test fires", "no", "prospective evaluation", "development/calibration/held-out", "population exponent is above one-half", "yes", "Primary constrained-law comparison requested."],
        ["Geometric manifold within scaling", "src/fire_metabolism/geometric_manifold.py", "scaling_estimates", "within_between_scaling.csv", "within-fire log perimeter", "within-fire log area", "0.5", "C", "fire intercept removed", "fire-conditioned", "whole-fire mean geometry", "no", "retrospective estimand", "split estimates", "within exponent is about 0.59", "yes", "Quantify one-half normalization drift."],
        ["Geometric manifold anchored adequacy", "scripts/run_geometric_manifold_validation.py", "powerlaw_adequacy", "powerlaw_adequacy.csv", "future log perimeter", "future log area", "0.5", "D", "prediction-origin anchored", "origin conditioned", "origin geometry", "yes", "prospective", "held-out", "fixed one-half has weak anchored adequacy", "yes", "Cross all intercept treatments on identical transitions."],
        ["Geometric-state normalization", "scripts/run_geometric_manifold_validation.py", "state_dynamics", "normalization_drift.csv", "normalized log geometry", "log area", "0.5", "C", "fire effects retained descriptively", "candidate normalization", "repeated fire states", "no", "retrospective", "all splits", "one-half normalization drifts upward", "yes", "Direct universal-law diagnostic."],
        ["Synthetic geometric manifold", "scripts/run_geometric_manifold_validation.py", "synthetic_validation", "synthetic_manifold_results.csv", "multiple geometric summaries", "synthetic area trajectories", "0.5", "C/D", "fire-specific and anchored", "simulation-specific", "simulated c_i", "sometimes", "validation", "development-calibrated", "no fixed manifold reproduced all summaries", "yes", "Cross generating law with intercept treatment."],
        ["Model-output hexbin", "scripts/make_model_hexbin_plot.py", "write_hexbin_plot", "model hexbin figure", "model perimeter", "model area", "0.5", "visual", "common fitted model-cloud intercept", "shared coefficient with cloud fit", "none", "no", "descriptive", "model simulations", "one-half line tracks model fit", "no", "Line uses fitted cloud intercept; visual, not independent validation."],
        ["Reference-line animation", "scripts/animate_reference_lines_only.py", "write_reference_animation", "reference_lines_red_blue_only.mp4", "schematic perimeter", "schematic area", "0.5", "visual", "shared user-set coefficient", "common coefficient", "none", "no", "schematic", "none", "illustrates divergence", "no", "Pure analytical schematic."],
        ["Raster overlay reference", "scripts/add_two_thirds_line_to_image.py", "overlay_line", "event_hexbin_with_blue_two_thirds.png", "pixel-mapped perimeter", "pixel-mapped area", "0.5/0.667", "visual", "manual coefficient", "unclear relative to original red line", "none", "no", "retrospective graphic", "none", "visual alignment", "yes", "Original line normalization cannot be recovered from raster alone."],
        ["Manuscript empirical examples", "src/fire_metabolism/empirical_manuscript_figures.py", "example trajectory panel", "empirical manuscript figure", "perimeter", "area", "0.5", "D", "anchored to fitted event point", "event conditioned", "event fit", "yes", "retrospective example", "held-out example", "reference slopes show local divergence", "no", "Caption must state event-point anchoring."],
        ["Analytical smooth-family figure", "src/fire_metabolism/figures.py", "generate_analytical_figures", "02_smooth_vs_two_thirds", "analytical perimeter", "analytical area", "0.5", "visual", "shared c=4", "common arbitrary coefficient", "none", "no", "analytical", "none", "contrasts reference exponents", "no", "Schematic, not empirical evidence."],
        ["Fire-model scaling plots", "src/fire_model_scaling/plotting.py", "plot_scaling", "model scaling plots", "simulated perimeter", "simulated area", "0.5", "visual", "anchored to pooled medians", "common chosen point", "model cloud", "yes", "descriptive", "simulations", "reference comparison", "yes", "Median anchoring conditions the display on model output."],
        ["Grass-fire animation diagnostic", "scripts/animate_grass_fire_two_thirds.py", "plot_scaling", "scaling plot", "rendered-grid perimeter", "rendered area", "0.5", "visual", "common selected anchor", "same anchor as two-thirds", "selected simulation", "yes", "descriptive", "simulation", "animation calibrated near two-thirds", "no", "Explicitly a calibrated simulation schematic."],
        ["Formal counterexamples", "FireProof", "multiple theorems", "Lean audit", "mathematical propositions", "assumptions", "0.5", "formal", "not applicable", "not empirical", "none", "no", "deductive", "none", "logical implications only", "no", "Out of scope and unchanged."],
    ]
    return pd.DataFrame(rows, columns=columns)


def semantic_audit() -> pd.DataFrame:
    rows = [
        ("One-half predicts future FIRED area competitively.", "docs/PREDICTION_VALIDATION.md", "Anchored transformed temporal trend", "history/origin conditioned", "F: temporal area-growth forecast", True, "The one-half temporal area-growth benchmark is competitive at some short horizons."),
        ("One-half is competitive with two-thirds for future local slopes.", "docs/GEOMETRIC_ATTRACTOR_VALIDATION.md", "Fixed equilibrium center in a restoring model", "not a perimeter intercept", "E: local-slope shrinkage", False, "A one-half center can be a useful shrinkage target for noisy future rolling slopes."),
        ("Negative realization deficits do not explain the one-half advantage.", "docs/HALF_VS_TWO_THIRDS_CONSTRAINT_TEST.md", "q versus fixed-center local-slope loss", "not applicable", "E plus latent-constraint association", True, "Realization deficit q does not explain the relative local-slope shrinkage performance."),
        ("One-half is the diffusion-like geometric law.", "docs/storyboard.md", "Conceptual reference line", "unspecified", "shorthand, not an empirical result", False, "Use 'smooth shape-preserving geometric reference' unless a diffusion mechanism is independently tested."),
        ("Wildfires do not follow diffusion.", "docs/storyboard.md", "Contrast of conceptual exponents", "unspecified", "mechanistic claim", False, "The perimeter-area results reject an exact common one-half normalization; they do not by themselves reject every diffusion mechanism."),
        ("One-half normalization drifts upward with size.", "docs/GEOMETRIC_MANIFOLD_VALIDATION.md", "Within-fire normalization drift", "fire intercept removed", "C: within-fire diagnostic", True, "Within fires, log(P/A^1/2) increases systematically with log area."),
        ("The empirical within-fire exponent lies between one-half and two-thirds.", "docs/GEOMETRIC_MANIFOLD_VALIDATION.md", "Within-fire centered regression", "fire-conditioned", "C: longitudinal estimand", True, "The held-out within-fire exponent lies between the two references and excludes both at high precision."),
        ("A one-half regime indicates suppression or fuel restriction.", "prediction reports", "Trajectory association", "varied", "unsupported causal attribution", False, "A lower local slope or realization deficit is constraint-like; FIRED does not identify suppression or fuel limitation."),
        ("The one-half model wins.", "multiple reports", "Mixed A-F tests", "mixed", "semantically ambiguous", False, "Name the exact hypothesis: population law, fire-conditioned scaling, origin-anchored extrapolation, local-slope shrinkage, or temporal area growth."),
    ]
    return pd.DataFrame(rows, columns=["original_statement", "source", "actual_statistical_test", "intercept_treatment", "correct_interpretation", "original_wording_safe", "recommended_replacement_wording"])


def figure_audit() -> pd.DataFrame:
    rows = [
        ("model heterogeneous hexbin", "scripts/make_model_hexbin_plot.py", "1/2", "common fitted intercept", "uses the model-cloud OLS intercept", "descriptive only"),
        ("model heterogeneous hexbin", "scripts/make_model_hexbin_plot.py", "2/3 and 3/4", "anchored to chosen low-area point", "low-area percentile anchor", "not directly comparable to fitted one-half normalization"),
        ("reference lines animation", "scripts/animate_reference_lines_only.py", "1/2 and 2/3", "common coefficient", "coefficient CLI/default", "analytical schematic"),
        ("event hexbin raster overlay", "scripts/add_two_thirds_line_to_image.py", "2/3", "manual coefficient", "pixel-calibrated coefficient", "normalization relative to source line unclear"),
        ("empirical trajectory examples", "src/fire_metabolism/empirical_manuscript_figures.py", "1/2 and 2/3", "anchored to fitted event point", "event-specific anchor", "local visual comparison"),
        ("analytical smooth comparison", "src/fire_metabolism/figures.py", "1/2 and 2/3", "common arbitrary coefficient", "c=4", "schematic"),
        ("fire-model scaling", "src/fire_model_scaling/plotting.py", "1/2, 2/3, 3/4", "anchored to pooled medians", "median model area/perimeter", "conditions on model cloud"),
        ("grass-fire animation scaling", "scripts/animate_grass_fire_two_thirds.py", "1/2 and 2/3", "common selected anchor", "animation anchor point", "calibrated simulation"),
        ("geometric manifold primary figure", "scripts/run_geometric_manifold_validation.py", "1/2 and 2/3", "common anchor for display", "development median anchor", "display only; numeric inference is separate"),
        ("FIRED CONUS scaling plot", "historical output image; source table absent", "1/2 and 2/3", "reported median-event anchor", "historical caption", "cannot fully reproduce normalization from current source tree"),
        ("real vs level-set model scaling", "historical output image; source table absent", "2/3", "separate layer fits/visual anchors", "historical image", "source data unavailable in locked audit"),
    ]
    return pd.DataFrame(rows, columns=["figure", "source", "reference_exponent", "intercept_class", "intercept_basis", "audit_conclusion"])


def diffusion_audit() -> pd.DataFrame:
    rows = [
        ("docs/storyboard.md", "Wildfires do not follow diffusion", "unsupported", "Perimeter-area exponent alone does not identify a diffusion process.", "Replace with an exact geometric statement."),
        ("docs/storyboard.md", "diffusion-like predictions", "shorthand only", "Acceptable only as a labeled reference analogy.", "Say smooth shape-preserving one-half reference."),
        ("docs/fired-prediction.md", "diffusion-like spread (sigma=1/2)", "shorthand only", "This is a temporal area-growth exponent, not a diffusion-process test.", "Say one-half temporal growth benchmark."),
        ("scripts/make_model_hexbin_plot.py", "diffusion-like spread", "geometrically suggestive only", "The plotted line has a fitted cloud intercept.", "Label one-half reference; explain normalization in caption."),
        ("scripts/animate_reference_lines_only.py", "diffusion-like spread", "shorthand only", "Pure schematic with an arbitrary shared coefficient.", "Label smooth one-half reference."),
        ("README.md", "self-similar/shape-preserving local front", "geometrically justified", "A compact smooth shape family gives exponent one-half.", "Retain with no mechanistic diffusion claim."),
        ("docs/GEOMETRIC_MANIFOLD_VALIDATION.md", "one-half reference", "geometrically justified", "Used as a numerical reference and explicitly separated from mechanism.", "Retain."),
        ("prediction reports", "one-half state/regime", "unsupported", "Rolling-slope proximity is not a process regime.", "Say local slope near one-half."),
    ]
    return pd.DataFrame(rows, columns=["source", "language", "classification", "why", "recommended_action"])


def direct_population_scores(panel: pd.DataFrame, exponents: dict[str, float], dev_alpha: dict[str, float], cal_alpha: dict[str, float]) -> pd.DataFrame:
    held = panel[panel.partition.eq("held_out")]
    rows = []
    for treatment, intercepts in (("population_locked", dev_alpha), ("calibration_locked", cal_alpha)):
        event_errors: dict[str, pd.Series] = {}
        for name, sigma in exponents.items():
            error = intercepts[name] + sigma * held.log_area - held.log_perimeter
            event_error = pd.DataFrame({"id": held.id, "absolute_error": np.abs(error)}).groupby("id").absolute_error.mean()
            event_errors[name] = event_error
            generator = np.random.default_rng(DEFAULT_SEED + len(treatment) + len(name))
            draws = generator.choice(event_error.to_numpy(float), size=(REPLICATES, len(event_error)), replace=True).mean(axis=1)
            rows.append({"intercept_treatment": treatment, "candidate": name, "exponent": sigma, "n": len(held), "n_fires": held.id.nunique(), "mae_log": np.abs(error).mean(), "mae_event_weighted": event_error.mean(), "mae_event_ci95_lower": np.quantile(draws, .025), "mae_event_ci95_upper": np.quantile(draws, .975), "rmse_log": np.sqrt(np.mean(error**2)), "intercept": intercepts[name]})
        reference = event_errors["two_thirds"]
        for row in rows[-len(exponents):]:
            common = pd.concat([event_errors[row["candidate"]], reference], axis=1, keys=["candidate", "reference"]).dropna()
            difference = common.candidate - common.reference
            generator = np.random.default_rng(DEFAULT_SEED + 100 + len(treatment) + len(row["candidate"]))
            draws = generator.choice(difference.to_numpy(float), size=(REPLICATES, len(difference)), replace=True).mean(axis=1)
            row["event_weighted_mae_difference_vs_two_thirds"] = difference.mean()
            row["difference_ci95_lower"] = np.quantile(draws, .025)
            row["difference_ci95_upper"] = np.quantile(draws, .975)
    return pd.DataFrame(rows)


def add_score_uncertainty(summary: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    """Attach event-bootstrap MAE and paired differences versus two-thirds."""
    rows = []
    for record in summary.to_dict(orient="records"):
        frame = scores[
            scores.intercept_treatment.eq(record["intercept_treatment"])
            & scores.candidate.eq(record["candidate"])
        ]
        reference = scores[
            scores.intercept_treatment.eq(record["intercept_treatment"])
            & scores.candidate.eq("two_thirds")
        ]
        if str(record["lead_days"]) != "all":
            lead = int(record["lead_days"])
            frame = frame[frame.lead_days.eq(lead)]
            reference = reference[reference.lead_days.eq(lead)]
        event = frame.groupby("id").absolute_error.mean()
        generator = np.random.default_rng(DEFAULT_SEED + 200 + len(record["candidate"]) + len(record["intercept_treatment"]) + (0 if str(record["lead_days"]) == "all" else int(record["lead_days"])))
        draws = generator.choice(event.to_numpy(float), size=(REPLICATES, len(event)), replace=True).mean(axis=1)
        record["mae_event_weighted"] = event.mean()
        record["mae_event_ci95_lower"] = np.quantile(draws, .025)
        record["mae_event_ci95_upper"] = np.quantile(draws, .975)
        candidate_event = frame.groupby(["id", "origin_day", "future_day"]).absolute_error.mean().groupby("id").mean()
        reference_event = reference.groupby(["id", "origin_day", "future_day"]).absolute_error.mean().groupby("id").mean()
        paired = pd.concat([candidate_event, reference_event], axis=1, keys=["candidate", "reference"]).dropna()
        difference = paired.candidate - paired.reference
        diff_draws = generator.choice(difference.to_numpy(float), size=(REPLICATES, len(difference)), replace=True).mean(axis=1)
        record["event_weighted_mae_difference_vs_two_thirds"] = difference.mean()
        record["difference_ci95_lower"] = np.quantile(diff_draws, .025)
        record["difference_ci95_upper"] = np.quantile(diff_draws, .975)
        rows.append(record)
    return pd.DataFrame(rows)


def fire_specific_scores(panel: pd.DataFrame, exponents: dict[str, float]) -> pd.DataFrame:
    held = panel[panel.partition.eq("held_out")]
    rows = []
    for name, sigma in exponents.items():
        residual = held.log_perimeter - sigma * held.log_area
        alpha = residual.groupby(held.id).transform("mean")
        error = alpha + sigma * held.log_area - held.log_perimeter
        rows.append({"intercept_treatment": "fire_specific_full_retrospective", "candidate": name, "exponent": sigma, "n": len(held), "n_fires": held.id.nunique(), "mae_log": np.abs(error).mean(), "rmse_log": np.sqrt(np.mean(error**2))})
    return pd.DataFrame(rows)


def normalization_tables(panel: pd.DataFrame, exponents: dict[str, float]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    zero_rows = []
    for partition in ("development", "calibration", "held_out"):
        frame = panel[panel.partition.eq(partition)]
        estimates = scaling_estimates(frame)
        intervals = bootstrap_scaling(frame, replicates=REPLICATES, seed=DEFAULT_SEED + len(partition)).set_index("estimand")
        for name, sigma in exponents.items():
            for estimand in ("population", "between", "within"):
                value = estimates[estimand] - sigma
                ci = intervals.loc[estimand]
                rows.append({"partition": partition, "candidate": name, "candidate_exponent": sigma, "component": estimand, "normalization_drift": value, "ci95_lower": ci.ci95_lower - sigma, "ci95_upper": ci.ci95_upper - sigma, "n": len(frame), "n_fires": frame.id.nunique()})
        zero_rows.extend([
            {"partition": partition, "method": "within_centered_regression", "zero_drift_exponent": estimates["within"], "ci95_lower": intervals.loc["within", "ci95_lower"], "ci95_upper": intervals.loc["within", "ci95_upper"], "n_fires": frame.id.nunique()},
            {"partition": partition, "method": "normalization_drift_root", "zero_drift_exponent": estimates["within"], "ci95_lower": intervals.loc["within", "ci95_lower"], "ci95_upper": intervals.loc["within", "ci95_upper"], "n_fires": frame.id.nunique()},
        ])
    return pd.DataFrame(rows), pd.DataFrame(zero_rows)


def local_slope_reaudit(dev_sigma: float) -> pd.DataFrame:
    transitions = pd.read_csv(ATTRACTOR)
    rows = []
    for lead, frame in transitions.groupby("lead_days"):
        dev = frame[frame.partition.eq("development")]
        cal = frame[frame.partition.eq("calibration")]
        held = frame[frame.partition.eq("held_out")]
        if min(dev.id.nunique(), cal.id.nunique(), held.id.nunique()) < 20:
            continue
        grid = np.linspace(0.3, 0.8, 101)
        calibration = []
        for center in grid:
            slope, _ = fit_fixed_attractor_center(dev, center)
            pred = predict_fixed_attractor(cal, center, slope)
            calibration.append(np.mean(np.abs(pred - cal.future_sigma)))
        selected_center = float(grid[int(np.argmin(calibration))])
        training = pd.concat([dev, cal], ignore_index=True)
        centers = {"one_half": 0.5, "two_thirds": 2 / 3, "development_within": dev_sigma, "selected_local_center": selected_center}
        for name, center in centers.items():
            slope, _ = fit_fixed_attractor_center(training, center)
            prediction = predict_fixed_attractor(held, center, slope)
            error = prediction - held.future_sigma.to_numpy(float)
            rows.append({"lead_days": int(lead), "model": name, "center": center, "restoring_slope": slope, "n": len(held), "n_fires": held.id.nunique(), "mae": np.mean(np.abs(error)), "rmse": np.sqrt(np.mean(error**2)), "interpretation": "category E local-slope shrinkage; not a perimeter-area law", "selection": "center selected on calibration after fitting dynamics on development" if name == "selected_local_center" else "center prespecified; dynamics fit on development+calibration"})
    return pd.DataFrame(rows)


def adaptation_gain(scores: pd.DataFrame) -> pd.DataFrame:
    held = scores[scores.partition.eq("held_out")]
    event = held.groupby(["id", "candidate", "intercept_treatment"], as_index=False).absolute_error.mean()
    wide = event.pivot(index=["id", "candidate"], columns="intercept_treatment", values="absolute_error").reset_index()
    rows = []
    for candidate, group in wide.groupby("candidate"):
        for treatment in ("fire_specific_full", "fire_specific_history", "origin_anchored"):
            work = group.dropna(subset=["population_locked", treatment]).copy()
            work["population"] = work.population_locked
            work["adapted"] = work[treatment]
            result = event_bootstrap_difference(work, "population", "adapted", replicates=REPLICATES, seed=DEFAULT_SEED + len(candidate) + len(treatment))
            rows.append({"candidate": candidate, "adaptation": treatment, "gain_population_minus_adapted": result["difference"], "ci95_lower": result["ci95_lower"], "ci95_upper": result["ci95_upper"], "n_fires": result["n_fires"]})
    result = pd.DataFrame(rows)
    event_wide = event.pivot(index="id", columns=["candidate", "intercept_treatment"], values="absolute_error")
    for treatment in ("fire_specific_full", "fire_specific_history", "origin_anchored"):
        needed = [("one_half", "population_locked"), ("one_half", treatment), ("two_thirds", "population_locked"), ("two_thirds", treatment)]
        common = event_wide[needed].dropna()
        gains = pd.DataFrame(index=common.index)
        gains["half_gain"] = common[("one_half", "population_locked")] - common[("one_half", treatment)]
        gains["two_thirds_gain"] = common[("two_thirds", "population_locked")] - common[("two_thirds", treatment)]
        boot = event_bootstrap_difference(gains.reset_index(), "half_gain", "two_thirds_gain", replicates=REPLICATES, seed=DEFAULT_SEED + 400 + len(treatment))
        result = pd.concat([result, pd.DataFrame([{"candidate": "delta_gain_one_half_minus_two_thirds", "adaptation": treatment, "gain_population_minus_adapted": boot["difference"], "ci95_lower": boot["ci95_lower"], "ci95_upper": boot["ci95_upper"], "n_fires": boot["n_fires"]}])], ignore_index=True)
    return result


def expansion_discrimination(scores: pd.DataFrame, development_transitions: pd.DataFrame) -> tuple[pd.DataFrame, list[float]]:
    positive = development_transitions.log_area_ratio[development_transitions.log_area_ratio >= 0]
    bounds = np.unique(np.quantile(positive, [0, 0.5, 0.8, 0.95, 1])).tolist()
    bounds[0] = min(bounds[0], -1e-12)
    bounds[-1] = max(bounds[-1], positive.max() + 1e-12)
    labels = ["low", "moderate", "high", "extreme"][: len(bounds) - 1]
    held = scores[scores.partition.eq("held_out")].copy()
    held["expansion_bin"] = pd.cut(held.log_area_ratio, bounds, labels=labels, include_lowest=True)
    pivot = held[held.candidate.isin(["one_half", "two_thirds"])].pivot_table(
        index=["id", "origin_day", "future_day", "lead_days", "intercept_treatment", "area_ratio", "log_area_ratio", "half_vs_two_thirds_ratio", "expansion_bin"],
        columns="candidate",
        values="absolute_error",
        aggfunc="first",
        observed=True,
    ).dropna().reset_index()
    pivot["loss_half_minus_two_thirds"] = pivot.one_half - pivot.two_thirds
    rows = []
    for keys, group in pivot.groupby(["intercept_treatment", "lead_days", "expansion_bin"], observed=True):
        treatment, lead, label = keys
        rho = spearmanr(group.log_area_ratio, group.loss_half_minus_two_thirds)
        rows.append({"intercept_treatment": treatment, "lead_days": int(lead), "expansion_bin": str(label), "development_log_ratio_lower": bounds[labels.index(str(label))], "development_log_ratio_upper": bounds[labels.index(str(label)) + 1], "n": len(group), "n_fires": group.id.nunique(), "median_area_ratio": group.area_ratio.median(), "median_theoretical_P_two_thirds_over_half": group.half_vs_two_thirds_ratio.median(), "half_mae": group.one_half.mean(), "two_thirds_mae": group.two_thirds.mean(), "loss_half_minus_two_thirds": group.loss_half_minus_two_thirds.mean(), "spearman_log_expansion_vs_loss_difference": rho.statistic})
    return pd.DataFrame(rows), bounds


def long_trajectory_scores(panel: pd.DataFrame, scores: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    metrics = panel.groupby(["id", "partition"]).agg(n_observations=("event_day", "size"), duration_days=("event_day", lambda x: int(x.max() - x.min() + 1)), log_area_span=("log_area", lambda x: float(x.max() - x.min()))).reset_index()
    dev = metrics[metrics.partition.eq("development")]
    thresholds = {"n_observations": float(dev.n_observations.quantile(0.75)), "duration_days": float(dev.duration_days.quantile(0.75)), "log_area_span": float(dev.log_area_span.quantile(0.75))}
    eligible = metrics[(metrics.partition.eq("held_out")) & (metrics.n_observations >= thresholds["n_observations"]) & (metrics.duration_days >= thresholds["duration_days"]) & (metrics.log_area_span >= thresholds["log_area_span"])].id
    subset = scores[scores.id.isin(eligible) & scores.partition.eq("held_out") & scores.candidate.isin(["one_half", "two_thirds"])]
    result = summarize_scores(subset)
    result["eligibility_rule"] = "all three metrics >= development 75th percentile"
    return result, thresholds


def constraint_interaction(scores: pd.DataFrame) -> pd.DataFrame:
    residuals = pd.read_parquet(GROWTH_RESIDUALS)[["id", "origin_day", "lead_days", "partition", "realization_residual_q"]]
    held = scores[scores.partition.eq("held_out") & scores.candidate.isin(["one_half", "two_thirds"])].copy()
    keys = ["id", "origin_day", "future_day", "lead_days", "intercept_treatment"]
    wide = held.pivot_table(index=keys, columns="candidate", values="absolute_error", aggfunc="first").dropna().reset_index()
    wide["D_half_minus_two_thirds"] = wide.one_half - wide.two_thirds
    joined = wide.merge(residuals, on=["id", "origin_day", "lead_days"], how="inner")
    train = residuals[residuals.partition.ne("held_out")]
    rows = []
    for (treatment, lead), group in joined.groupby(["intercept_treatment", "lead_days"]):
        cut = np.unique(train[train.lead_days.eq(lead)].realization_residual_q.quantile([0, .2, .4, .6, .8, 1]).to_numpy())
        if len(cut) < 3:
            continue
        rho = spearmanr(group.realization_residual_q, group.D_half_minus_two_thirds)
        rows.append({"intercept_treatment": treatment, "lead_days": int(lead), "residual_bin": "continuous", "n": len(group), "n_fires": group.id.nunique(), "median_q": group.realization_residual_q.median(), "mean_D": group.D_half_minus_two_thirds.mean(), "half_win_rate": (group.D_half_minus_two_thirds < 0).mean(), "spearman_q_D": rho.statistic, "spearman_p": rho.pvalue})
        labels = [f"q{i + 1}" for i in range(len(cut) - 1)]
        group = group.copy(); group["bin"] = pd.cut(group.realization_residual_q, cut, labels=labels, include_lowest=True)
        for label, part in group.groupby("bin", observed=True):
            rows.append({"intercept_treatment": treatment, "lead_days": int(lead), "residual_bin": str(label), "n": len(part), "n_fires": part.id.nunique(), "median_q": part.realization_residual_q.median(), "mean_D": part.D_half_minus_two_thirds.mean(), "half_win_rate": (part.D_half_minus_two_thirds < 0).mean(), "spearman_q_D": np.nan, "spearman_p": np.nan})
    return pd.DataFrame(rows)


def synthetic_experiment(panel: pd.DataFrame, transitions: pd.DataFrame, exponents: dict[str, float], replicates: int = 20) -> pd.DataFrame:
    dev = panel[panel.partition.eq("development")]
    empirical_sigma = exponents["development_estimated"]
    residual = dev.log_perimeter - empirical_sigma * dev.log_area
    event_alpha = residual.groupby(dev.id).mean()
    alpha_mean, alpha_sd = float(event_alpha.mean()), float(event_alpha.std())
    centered = residual - dev.id.map(event_alpha)
    noise_sd = float(centered.std())
    event_codes = panel.id.astype("category")
    generator = np.random.default_rng(DEFAULT_SEED + 900)
    rows = []
    generating = {"S1_true_one_half": .5, "S2_true_two_thirds": 2 / 3, "S3_true_three_quarters": .75, "S4_true_development_within": empirical_sigma}
    for scenario, true_sigma in generating.items():
        for replicate in range(replicates):
            simulated = panel.copy()
            random_alpha = dict(zip(event_codes.cat.categories, generator.normal(alpha_mean, alpha_sd, len(event_codes.cat.categories)), strict=True))
            eps = generator.normal(0, noise_sd, len(simulated))
            simulated["log_perimeter"] = simulated.id.map(random_alpha).to_numpy(float) + true_sigma * simulated.log_area + eps
            dev_sim = simulated[simulated.partition.eq("development")]
            held_sim = simulated[simulated.partition.eq("held_out")]
            common_alpha = {name: fit_fixed_intercept(dev_sim, sigma) for name, sigma in exponents.items()}
            full_alpha = {name: (simulated.log_perimeter - sigma * simulated.log_area).groupby(simulated.id).transform("mean") for name, sigma in exponents.items()}
            for name, sigma in exponents.items():
                err = common_alpha[name] + sigma * held_sim.log_area - held_sim.log_perimeter
                rows.append({"scenario": scenario, "generating_exponent": true_sigma, "replicate": replicate, "intercept_treatment": "population_locked", "candidate": name, "candidate_exponent": sigma, "mae_log": np.abs(err).mean(), "n": len(held_sim), "n_fires": held_sim.id.nunique()})
                err = full_alpha[name][held_sim.index] + sigma * held_sim.log_area - held_sim.log_perimeter
                rows.append({"scenario": scenario, "generating_exponent": true_sigma, "replicate": replicate, "intercept_treatment": "fire_specific_full_retrospective", "candidate": name, "candidate_exponent": sigma, "mae_log": np.abs(err).mean(), "n": len(held_sim), "n_fires": held_sim.id.nunique()})
            lookup = simulated.set_index(["id", "event_day"]).log_perimeter
            held_t = transitions[transitions.partition.eq("held_out")]
            oy = np.array([lookup.loc[(i, d)] for i, d in zip(held_t.id, held_t.origin_day, strict=True)])
            fy = np.array([lookup.loc[(i, d)] for i, d in zip(held_t.id, held_t.future_day, strict=True)])
            for name, sigma in exponents.items():
                pred = oy + sigma * held_t.log_area_ratio.to_numpy(float)
                rows.append({"scenario": scenario, "generating_exponent": true_sigma, "replicate": replicate, "intercept_treatment": "origin_anchored", "candidate": name, "candidate_exponent": sigma, "mae_log": np.mean(np.abs(pred - fy)), "n": len(held_t), "n_fires": held_t.id.nunique()})
    return pd.DataFrame(rows)


def decisive_figure(panel: pd.DataFrame, scores: pd.DataFrame, summary: pd.DataFrame, drift: pd.DataFrame, expansion: pd.DataFrame, synthetic: pd.DataFrame, exponents: dict[str, float], dev_alpha: dict[str, float]) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(16, 10), constrained_layout=True)
    held = panel[panel.partition.eq("held_out")]
    ax = axes[0, 0]
    hb = ax.hexbin(held.log_area, held.log_perimeter, gridsize=55, mincnt=1, cmap="magma_r", norm=LogNorm())
    x = np.linspace(held.log_area.quantile(.005), held.log_area.quantile(.995), 200)
    ax.plot(x, dev_alpha["one_half"] + .5*x, color="#B3261E", lw=2.8, label="1/2, dev locked")
    ax.plot(x, dev_alpha["two_thirds"] + (2/3)*x, color="#6495ED", lw=2.8, label="2/3, dev locked")
    ax.set(xlabel="log area", ylabel="log perimeter", title="A  Population geometry")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[0, 1]
    held_t = scores[(scores.partition.eq("held_out")) & (scores.intercept_treatment.eq("origin_anchored"))]
    candidates = held_t.groupby(["id", "origin_day"]).area_ratio.max().sort_values()
    event_id, origin_day = candidates.index[min(len(candidates)-1, int(.9*len(candidates)))]
    ex = held_t[(held_t.id.eq(event_id)) & (held_t.origin_day.eq(origin_day)) & held_t.candidate.isin(["one_half", "two_thirds"])].sort_values("future_log_area")
    ax.scatter(ex.origin_log_area.iloc[0], ex.origin_log_perimeter.iloc[0], color="black", s=45, zorder=4, label="origin")
    for name, color in (("one_half", "#B3261E"), ("two_thirds", "#6495ED")):
        part = ex[ex.candidate.eq(name)]
        ax.plot(pd.concat([pd.Series([part.origin_log_area.iloc[0]]), part.future_log_area]), pd.concat([pd.Series([part.origin_log_perimeter.iloc[0]]), part.predicted_log_perimeter]), color=color, lw=2.8, label=name.replace("_", " "))
    actual = panel[(panel.id.eq(event_id)) & (panel.event_day >= origin_day)]
    ax.scatter(actual.log_area, actual.log_perimeter, color="#333333", s=18, alpha=.65, label="observed")
    ax.set(xlabel="log area", ylabel="log perimeter", title=f"B  Same fire, anchored (ID {event_id})")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[0, 2]
    all_summary = summary[summary.lead_days.astype(str).eq("all")]
    pivot = all_summary[all_summary.candidate.isin(["one_half", "two_thirds"])].pivot(index="intercept_treatment", columns="candidate", values="mae_log")
    delta = (pivot.one_half - pivot.two_thirds).reindex(["population_locked", "calibration_locked", "fire_specific_full", "origin_anchored"])
    ax.bar(np.arange(len(delta)), delta, color=["#555555", "#777777", "#D28B26", "#6495ED"])
    ax.axhline(0, color="black", lw=1)
    ax.set_xticks(np.arange(len(delta)), ["population\nlocked", "calibration\nlocked", "fire-specific", "origin\nanchored"])
    ax.set(ylabel="MAE(1/2) - MAE(2/3)", title="C  Intercept treatment")

    ax = axes[1, 0]
    shown = expansion[(expansion.intercept_treatment.eq("origin_anchored"))].groupby("expansion_bin", observed=True).agg(ratio=("median_area_ratio", "median"), D=("loss_half_minus_two_thirds", "mean"))
    ax.plot(np.log(shown.ratio), shown.D, marker="o", color="#315A9A", lw=2.5)
    ax.axhline(0, color="black", lw=1)
    ax.set(xlabel="log area expansion", ylabel="MAE(1/2) - MAE(2/3)", title="D  Anchored discrimination")

    ax = axes[1, 1]
    d = drift[(drift.partition.eq("held_out")) & (drift.component.eq("within"))]
    ax.errorbar(np.arange(len(d)), d.normalization_drift, yerr=[d.normalization_drift-d.ci95_lower, d.ci95_upper-d.normalization_drift], fmt="o", color="#333333", ecolor="#6495ED", capsize=4)
    ax.axhline(0, color="black", lw=1)
    ax.set_xticks(np.arange(len(d)), d.candidate.str.replace("_", " "), rotation=20)
    ax.set(ylabel="within-fire drift", title="E  Normalization drift")

    ax = axes[1, 2]
    syn = synthetic[(synthetic.scenario.eq("S2_true_two_thirds")) & synthetic.candidate.isin(["one_half", "two_thirds"])].groupby(["replicate", "intercept_treatment", "candidate"]).mae_log.mean().unstack("candidate").reset_index()
    syn["D"] = syn.one_half - syn.two_thirds
    order = ["population_locked", "fire_specific_full_retrospective", "origin_anchored"]
    values = syn.groupby("intercept_treatment").D.mean().reindex(order)
    ax.bar(np.arange(len(values)), values, color=["#555555", "#D28B26", "#6495ED"])
    ax.axhline(0, color="black", lw=1)
    ax.set_xticks(np.arange(len(values)), ["population\nlocked", "fire-specific", "anchored"])
    ax.set(ylabel="MAE(1/2) - MAE(2/3)", title="F  Synthetic true 2/3")
    for axis in axes.ravel():
        axis.grid(alpha=.2)
    fig.suptitle("Why can one-half predict locally even if it is not the global scaling law?", fontsize=17)
    for extension in ("pdf", "svg", "png"):
        fig.savefig(OUT / f"figure1_why_one_half_can_predict_locally.{extension}", dpi=400 if extension == "png" else None)
    plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    inventory = audit_inventory(); inventory.to_csv(OUT / "half_power_inventory.csv", index=False)
    semantics = semantic_audit(); semantics.to_csv(OUT / "semantic_audit.csv", index=False)
    figures = figure_audit(); figures.to_csv(OUT / "figure_intercept_audit.csv", index=False)
    diffusion = diffusion_audit(); diffusion.to_csv(OUT / "diffusion_language_audit.csv", index=False)

    sequences = pd.read_csv(SEQUENCES)
    geometry = pd.read_csv(GEOMETRY)
    panel = prepare_geometry_panel(sequences, geometry)
    counts = panel.groupby("partition").agg(n_observations=("id", "size"), n_fires=("id", "nunique")).reset_index()
    dev = panel[panel.partition.eq("development")]
    development_sigma = float(scaling_estimates(dev)["within"])
    exponents = {"one_half": .5, "two_thirds": 2/3, "three_quarters": .75, "development_estimated": development_sigma}
    development_intercepts = {name: fit_fixed_intercept(dev, sigma) for name, sigma in exponents.items()}
    training = panel[panel.partition.isin(["development", "calibration"])]
    calibration_intercepts = {name: fit_fixed_intercept(training, sigma) for name, sigma in exponents.items()}

    transitions = make_geometry_transitions(panel)
    transitions = add_history_intercepts(transitions, panel, exponents)
    scores = score_intercept_treatments(transitions, exponents, development_intercepts, calibration_intercepts)
    held_scores = scores[scores.partition.eq("held_out")]
    comparison = add_score_uncertainty(summarize_scores(held_scores), held_scores); comparison.to_csv(OUT / "intercept_treatment_comparison.csv", index=False)
    population = direct_population_scores(panel, exponents, development_intercepts, calibration_intercepts); population.to_csv(OUT / "population_locked_comparison.csv", index=False)
    fire = fire_specific_scores(panel, exponents)
    transition_fire = comparison[comparison.intercept_treatment.isin(["fire_specific_full", "fire_specific_history"])].copy()
    transition_fire["intercept_treatment"] = transition_fire.intercept_treatment.replace({"fire_specific_full": "fire_specific_full_same_transitions", "fire_specific_history": "fire_specific_history_prospective"})
    pd.concat([fire, transition_fire], ignore_index=True, sort=False).to_csv(OUT / "fire_specific_comparison.csv", index=False)
    comparison[comparison.intercept_treatment.eq("origin_anchored")].to_csv(OUT / "origin_anchored_comparison.csv", index=False)
    gain = adaptation_gain(scores); gain.to_csv(OUT / "intercept_adaptation_gain.csv", index=False)

    drift, zero = normalization_tables(panel, exponents)
    drift.to_csv(OUT / "normalization_drift.csv", index=False)
    zero.to_csv(OUT / "zero_drift_exponent.csv", index=False)
    local = local_slope_reaudit(development_sigma); local.to_csv(OUT / "local_slope_shrinkage.csv", index=False)
    constraint = constraint_interaction(scores); constraint.to_csv(OUT / "constraint_intercept_interaction.csv", index=False)
    expansion, expansion_bounds = expansion_discrimination(scores, transitions[transitions.partition.eq("development")]); expansion.to_csv(OUT / "area_expansion_discrimination.csv", index=False)
    long_result, long_thresholds = long_trajectory_scores(panel, scores); long_result.to_csv(OUT / "long_trajectory_comparison.csv", index=False)
    synthetic = synthetic_experiment(panel, transitions, exponents); synthetic.to_csv(OUT / "synthetic_intercept_experiment.csv", index=False)

    decisive_figure(panel, scores, comparison, drift, expansion, synthetic, exponents, development_intercepts)

    all_scores = comparison[comparison.lead_days.astype(str).eq("all")].set_index(["intercept_treatment", "candidate"])
    within_held = drift[(drift.partition.eq("held_out")) & (drift.component.eq("within"))].set_index("candidate")
    local_all = local.groupby("model").mae.mean()
    synthetic_two_thirds = synthetic[synthetic.scenario.eq("S2_true_two_thirds")].groupby(["intercept_treatment", "candidate"]).mae_log.mean()
    design = {
        "seed": DEFAULT_SEED,
        "cohort_source": str(SEQUENCES.relative_to(ROOT)),
        "geometry_source": str(GEOMETRY.relative_to(ROOT)),
        "event_inclusion_changed": False,
        "perimeter_definition": "exterior perimeter on positive daily-increment observations",
        "temporal_split": {"development": "2001-2012", "calibration": "2013-2015", "held_out": "2016-2020"},
        "verified_counts": counts.to_dict(orient="records"),
        "candidate_exponents": exponents,
        "development_locked_intercepts": development_intercepts,
        "calibration_locked_intercepts": calibration_intercepts,
        "calibration_contribution": "only the fixed-exponent intercept is finalized on development+calibration; held-out outcomes are never fit",
        "primary_loss": "mean absolute error in log perimeter",
        "uncertainty": f"whole-fire bootstrap with {REPLICATES} replicates where intervals are reported",
        "transition_horizons_days": [1, 3, 5, 7, 14, 21, 28],
        "area_expansion_log_ratio_bounds_from_development": expansion_bounds,
        "long_trajectory_thresholds_from_development": long_thresholds,
        "universal_category_A_status": "No physical common coefficient independent of FIRED was prespecified; category B development-locked population normalization is the strongest out-of-sample empirical test.",
    }
    (OUT / "design_lock.json").write_text(json.dumps(design, indent=2) + "\n")
    report = {
        "status": "complete",
        "answer": "One-half appears most competitive in local-slope shrinkage and origin-conditioned tests, not as a development-locked population perimeter-area law.",
        "development_estimated_within_exponent": development_sigma,
        "held_out_within_zero_drift_exponent": float(zero[(zero.partition.eq("held_out")) & (zero.method.eq("within_centered_regression"))].zero_drift_exponent.iloc[0]),
        "population_locked_mae": {name: float(all_scores.loc[("population_locked", name), "mae_log"]) for name in exponents},
        "origin_anchored_mae": {name: float(all_scores.loc[("origin_anchored", name), "mae_log"]) for name in exponents},
        "held_out_within_normalization_drift": {name: float(within_held.loc[name, "normalization_drift"]) for name in exponents},
        "mean_local_slope_shrinkage_mae_across_horizons": {name: float(value) for name, value in local_all.items()},
        "synthetic_true_two_thirds_mean_mae": {f"{treatment}:{candidate}": float(value) for (treatment, candidate), value in synthetic_two_thirds.items()},
        "outputs": sorted(path.name for path in OUT.iterdir()),
    }
    (OUT / "run_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
