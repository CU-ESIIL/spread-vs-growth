"""Publication figures from the locked FIRED adversarial-validation outputs.

This module is intentionally a presentation layer. It reads the machine-readable
validation products, selects representative past-only trajectories, and plots
the reported summaries without refitting any detector, forecast, or transition
model.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from .fired_lifecycle import merge_geometry_sequences


HALF_POWER = 0.5
TWO_THIRDS = 2.0 / 3.0
SNAPSHOT_DAYS = (5, 7, 10, 14, 21)
FORECAST_HORIZONS = (1, 3, 5, 7)

COLORS = {
    "blue": "#5B8EE6",
    "cornflower": "#6495ED",
    "red": "#B52322",
    "green": "#2E8B57",
    "teal": "#176B62",
    "purple": "#7B4BA3",
    "gold": "#D6A52A",
    "ink": "#202124",
    "gray": "#6B6F73",
    "light_gray": "#ECEDEF",
}

MODEL_LABELS = {
    "recent_linear": "Recent growth",
    "half_power": r"$A^{1/2}$ extrapolation",
    "two_thirds": r"$A^{2/3}$ extrapolation",
    "dynamics_ridge": "Dynamics ridge",
    "geometry_proxy": "Geometry proxy",
    "acceleration_persistence": "Persistence",
    "area_ridge": "Area",
}

REQUIRED_VALIDATION_FILES = (
    "detection_windows.csv.gz",
    "detection_summary.csv",
    "detection_robustness.csv",
    "forecast_metrics.csv",
    "paired_model_comparisons.csv",
    "transition_metrics.csv",
    "paired_transition_comparisons.csv",
)


@dataclass(frozen=True)
class EmpiricalFigureInputs:
    """Paths used to rebuild the empirical manuscript figures."""

    validation_dir: Path
    sequences_path: Path
    geometry_path: Path

    def required_paths(self) -> tuple[Path, ...]:
        return tuple(self.validation_dir / name for name in REQUIRED_VALIDATION_FILES) + (
            self.sequences_path,
            self.geometry_path,
        )


def validate_figure_inputs(inputs: EmpiricalFigureInputs) -> None:
    """Require every locked table and past trajectory source used by the figures."""

    missing = [path for path in inputs.required_paths() if not path.is_file()]
    if missing:
        joined = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(f"missing empirical figure inputs:\n{joined}")


def _read_validation_tables(inputs: EmpiricalFigureInputs) -> dict[str, pd.DataFrame]:
    validate_figure_inputs(inputs)
    tables = {
        Path(name).stem.replace(".csv", ""): pd.read_csv(inputs.validation_dir / name)
        for name in REQUIRED_VALIDATION_FILES
    }
    return tables


def select_detection_examples(
    detection_windows: pd.DataFrame,
    *,
    snapshot_day: int = 10,
) -> pd.DataFrame:
    """Select one representative held-out trajectory in each evidence class.

    The classes follow the locked detector output. Within each class, the event
    nearest the median normalized confidence-interval margin around ``2/3`` is
    selected. This deterministic rule avoids choosing unusually clean examples.
    """

    held = detection_windows[
        detection_windows.partition.eq("held_out")
        & detection_windows.snapshot_day.eq(snapshot_day)
    ].copy()
    if held.empty:
        raise ValueError(f"no held-out detection windows at day {snapshot_day}")

    ci_width = held.exterior_ci_upper - held.exterior_ci_lower
    held["contains_two_thirds"] = (
        held.exterior_ci_lower.le(TWO_THIRDS)
        & held.exterior_ci_upper.ge(TWO_THIRDS)
    )
    held["evidence_margin"] = np.minimum(
        TWO_THIRDS - held.exterior_ci_lower,
        held.exterior_ci_upper - TWO_THIRDS,
    ) / ci_width.replace(0.0, np.nan)

    categories = (
        ("Compatible", held.exterior_detected),
        ("Ambiguous", ~held.exterior_detected & held.contains_two_thirds),
        ("Inconsistent", ~held.exterior_detected & ~held.contains_two_thirds),
    )
    selected: list[pd.Series] = []
    for label, mask in categories:
        candidates = held[mask & np.isfinite(held.evidence_margin)]
        if candidates.empty:
            raise ValueError(f"no {label.lower()} held-out examples available")
        target = float(candidates.evidence_margin.quantile(0.5))
        index = (candidates.evidence_margin - target).abs().idxmin()
        row = candidates.loc[index].copy()
        row["evidence_class"] = label
        row["selection_quantile"] = 0.5
        selected.append(row)
    return pd.DataFrame(selected).reset_index(drop=True)


def past_trajectory(
    merged_sequences: pd.DataFrame,
    *,
    event_id: int,
    snapshot_day: int,
) -> pd.DataFrame:
    """Return only positive-growth observations available by a snapshot."""

    columns = [
        "id",
        "event_day",
        "cumulative_area_km2",
        "exterior_perimeter_km",
    ]
    trajectory = merged_sequences[
        merged_sequences.id.eq(event_id)
        & merged_sequences.event_day.le(snapshot_day)
        & merged_sequences.daily_area_km2.gt(0)
    ][columns].copy()
    if trajectory.empty or trajectory.event_day.max() > snapshot_day:
        raise ValueError(f"no valid past-only trajectory for event {event_id}")
    return trajectory.sort_values("event_day").reset_index(drop=True)


def detection_panel_data(
    tables: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Extract the locked summaries used in Figure 1."""

    summary = tables["detection_summary"]
    held_summary = (
        summary[summary.partition.eq("held_out") & summary.snapshot_day.isin(SNAPSHOT_DAYS)]
        .sort_values("snapshot_day")
        .reset_index(drop=True)
    )
    robustness = tables["detection_robustness"]
    held_robustness = robustness[robustness.partition.eq("held_out")].copy()
    contrasts = held_robustness[
        (
            held_robustness.snapshot_day.eq(10)
            & held_robustness.variant.isin(("exterior", "thinned"))
        )
        | (
            held_robustness.snapshot_day.eq(7)
            & held_robustness.variant.isin(("exterior", "total"))
        )
    ].copy()
    examples = select_detection_examples(tables["detection_windows"])
    return {
        "summary": held_summary,
        "contrasts": contrasts,
        "examples": examples,
        "windows": tables["detection_windows"],
    }


def prediction_panel_data(
    tables: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Extract the locked held-out summaries used in Figure 2."""

    forecast_models = (
        "recent_linear",
        "half_power",
        "two_thirds",
        "dynamics_ridge",
        "geometry_proxy",
    )
    forecast = tables["forecast_metrics"]
    forecast = (
        forecast[
            forecast.snapshot_day.eq(7)
            & forecast.horizon_days.isin(FORECAST_HORIZONS)
            & forecast.model.isin(forecast_models)
        ]
        .copy()
        .sort_values(["model", "horizon_days"])
    )

    paired = tables["paired_model_comparisons"]
    geometry_increment = paired[
        paired.snapshot_day.eq(7)
        & paired.first_model.eq("geometry_proxy")
        & paired.second_model.eq("dynamics_ridge")
        & paired.horizon_days.isin(FORECAST_HORIZONS)
    ].copy()
    day7_gain = paired[
        paired.snapshot_day.eq(7)
        & paired.horizon_days.eq(7)
        & paired.second_model.eq("dynamics_ridge")
        & paired.first_model.isin(("geometry_proxy", "geometry_indicator"))
    ].copy()
    day7_gain["gain"] = -day7_gain.mean_difference
    day7_gain["gain_ci95_lower"] = -day7_gain.ci95_upper
    day7_gain["gain_ci95_upper"] = -day7_gain.ci95_lower

    transition = tables["transition_metrics"]
    transition = transition[
        transition.snapshot_day.eq(7)
        & transition.horizon_days.eq(3)
        & transition.target.eq("future_accelerating")
        & transition.model.isin(
            ("acceleration_persistence", "area_ridge", "dynamics_ridge", "geometry_proxy")
        )
    ].copy()
    transition_order = {
        model: index
        for index, model in enumerate(
            ("acceleration_persistence", "area_ridge", "dynamics_ridge", "geometry_proxy")
        )
    }
    transition["plot_order"] = transition.model.map(transition_order)
    transition = transition.sort_values("plot_order")

    paired_transition = tables["paired_transition_comparisons"]
    transition_increment = paired_transition[
        paired_transition.snapshot_day.eq(7)
        & paired_transition.horizon_days.eq(3)
        & paired_transition.target.eq("future_accelerating")
        & paired_transition.first_model.eq("geometry_proxy")
        & paired_transition.second_model.eq("dynamics_ridge")
    ].copy()
    return {
        "forecast": forecast,
        "geometry_increment": geometry_increment,
        "day7_gain": day7_gain,
        "transition": transition,
        "transition_increment": transition_increment,
    }


def _style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 11.5,
            "axes.labelsize": 10.5,
            "axes.linewidth": 0.9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#D9DADD",
            "grid.alpha": 0.58,
            "grid.linewidth": 0.65,
            "legend.frameon": False,
            "legend.fontsize": 8.5,
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "fire-critter-empirical-figures",
        }
    )


def _panel_label(ax: plt.Axes, label: str, x: float = -0.12, y: float = 1.05) -> None:
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        fontsize=13,
        fontweight="bold",
        va="bottom",
    )


def _save_figure(
    fig: plt.Figure,
    output_dir: Path,
    stem: str,
    *,
    dpi: int,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for suffix in ("pdf", "svg", "png"):
        path = output_dir / f"{stem}.{suffix}"
        metadata = {"Date": None} if suffix == "svg" else None
        fig.savefig(
            path,
            dpi=dpi if suffix == "png" else None,
            bbox_inches="tight",
            facecolor="white",
            metadata=metadata,
        )
        paths.append(path)
    plt.close(fig)
    return paths


def _plot_detection_trajectories(
    fig: plt.Figure,
    grid: mpl.gridspec.SubplotSpec,
    examples: pd.DataFrame,
    merged_sequences: pd.DataFrame,
) -> pd.DataFrame:
    nested = grid.subgridspec(1, 3, wspace=0.20)
    class_colors = {
        "Compatible": COLORS["green"],
        "Ambiguous": COLORS["gold"],
        "Inconsistent": COLORS["red"],
    }
    trajectory_rows: list[pd.DataFrame] = []
    axes: list[plt.Axes] = []
    for index, row in enumerate(examples.itertuples(index=False)):
        axis = fig.add_subplot(nested[0, index])
        axes.append(axis)
        event = past_trajectory(
            merged_sequences,
            event_id=int(row.id),
            snapshot_day=int(row.snapshot_day),
        )
        event["evidence_class"] = row.evidence_class
        trajectory_rows.append(event)
        x = event.cumulative_area_km2.to_numpy(dtype=float)
        x_line = np.geomspace(float(x.min()), float(x.max()), 160)
        anchor_x = float(np.exp(np.mean(np.log(x))))
        anchor_y = float(np.exp(row.exterior_intercept) * anchor_x ** row.exterior_slope)
        for exponent, color, linestyle in (
            (HALF_POWER, COLORS["red"], "--"),
            (TWO_THIRDS, COLORS["cornflower"], "-"),
        ):
            y_line = anchor_y * (x_line / anchor_x) ** exponent
            axis.plot(x_line, y_line, color=color, linestyle=linestyle, lw=1.6, alpha=0.82)
        axis.plot(
            event.cumulative_area_km2,
            event.exterior_perimeter_km,
            color=class_colors[row.evidence_class],
            marker="o",
            markersize=3.5,
            markeredgecolor="white",
            markeredgewidth=0.45,
            lw=1.8,
            zorder=3,
        )
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_title(
            f"{row.evidence_class}: held-out event {int(row.id)}\n"
            rf"$\hat{{\sigma}}={row.exterior_slope:.2f}$ "
            rf"[{row.exterior_ci_lower:.2f}, {row.exterior_ci_upper:.2f}]",
            color=class_colors[row.evidence_class],
            fontsize=9.5,
        )
        axis.set_xlabel(r"Cumulative mapped area (km$^2$)")
        if index == 0:
            axis.set_ylabel("Exterior mapped perimeter (km)")
            _panel_label(axis, "A", x=-0.18, y=1.09)
        axis.grid(True, which="major")
        axis.grid(False, which="minor")
    handles = [
        Line2D([0], [0], color=COLORS["red"], ls="--", lw=1.8, label=r"$1/2$ slope guide"),
        Line2D([0], [0], color=COLORS["cornflower"], lw=1.8, label=r"$2/3$ slope guide"),
    ]
    axes[-1].legend(handles=handles, loc="lower right")
    return pd.concat(trajectory_rows, ignore_index=True)


def make_detection_figure(
    tables: dict[str, pd.DataFrame],
    merged_sequences: pd.DataFrame,
    output_dir: Path,
    *,
    dpi: int = 600,
) -> tuple[list[Path], dict[str, pd.DataFrame]]:
    """Build Figure 1: detection of a geometric signature."""

    _style()
    data = detection_panel_data(tables)
    fig = plt.figure(figsize=(13.2, 8.4), constrained_layout=True)
    outer = fig.add_gridspec(2, 3, height_ratios=(1.12, 1.0), hspace=0.24, wspace=0.22)
    trajectories = _plot_detection_trajectories(
        fig, outer[0, :], data["examples"], merged_sequences
    )

    axis = fig.add_subplot(outer[1, 0])
    windows = data["windows"]
    violin_data = []
    for day in SNAPSHOT_DAYS:
        values = windows[
            windows.partition.eq("held_out") & windows.snapshot_day.eq(day)
        ].exterior_slope.dropna().to_numpy(dtype=float)
        lower, upper = np.quantile(values, (0.01, 0.99))
        violin_data.append(values[(values >= lower) & (values <= upper)])
    violins = axis.violinplot(
        violin_data,
        positions=np.arange(len(SNAPSHOT_DAYS)),
        widths=0.78,
        showmeans=False,
        showmedians=False,
        showextrema=False,
    )
    for body in violins["bodies"]:
        body.set_facecolor(COLORS["cornflower"])
        body.set_edgecolor(COLORS["blue"])
        body.set_alpha(0.34)
        body.set_linewidth(0.8)
    axis.scatter(
        np.arange(len(SNAPSHOT_DAYS)),
        data["summary"].median_exterior_slope,
        color=COLORS["ink"],
        marker="D",
        s=25,
        zorder=4,
        label="Median",
    )
    axis.axhline(HALF_POWER, color=COLORS["red"], ls="--", lw=1.7, label=r"$1/2$")
    axis.axhline(TWO_THIRDS, color=COLORS["cornflower"], lw=1.8, label=r"$2/3$")
    axis.set_xticks(np.arange(len(SNAPSHOT_DAYS)), [str(day) for day in SNAPSHOT_DAYS])
    axis.set_xlabel("Snapshot day")
    axis.set_ylabel(r"Fitted slope $\hat{\sigma}$")
    axis.set_ylim(-0.02, 1.06)
    axis.set_title("Slope distributions remain near two-thirds", loc="left")
    axis.legend(ncol=3, loc="lower center", fontsize=7.8)
    axis.text(
        0.02,
        0.98,
        "Violins: central 98%",
        transform=axis.transAxes,
        va="top",
        color=COLORS["gray"],
        fontsize=8,
    )
    _panel_label(axis, "B")

    axis = fig.add_subplot(outer[1, 1])
    summary = data["summary"]
    axis.plot(
        summary.snapshot_day,
        100 * summary.geometric_detection_fraction,
        color=COLORS["cornflower"],
        marker="o",
        lw=2.4,
        label="Geometric indicator",
    )
    axis.plot(
        summary.snapshot_day,
        100 * summary.persistent_detection_fraction,
        color=COLORS["ink"],
        marker="s",
        lw=2.1,
        label="Persistent indicator",
    )
    axis.set_xticks(SNAPSHOT_DAYS)
    axis.set_xlabel("Snapshot day")
    axis.set_ylabel("Held-out fires (%)")
    axis.set_ylim(0, 66)
    axis.set_title("Compatibility becomes common, not universal", loc="left")
    axis.legend(loc="lower right")
    for row in summary.itertuples(index=False):
        axis.text(
            row.snapshot_day,
            100 * row.geometric_detection_fraction + 2.2,
            f"{100 * row.geometric_detection_fraction:.0f}",
            ha="center",
            color=COLORS["cornflower"],
            fontsize=7.5,
        )
    _panel_label(axis, "C")

    axis = fig.add_subplot(outer[1, 2])
    contrasts = data["contrasts"]
    contrast_spec = (
        ("Temporal sampling\n(day 10)", 10, "exterior", "thinned", "Full", "Every other"),
        ("Boundary definition\n(day 7)", 7, "exterior", "total", "Exterior", "Total"),
    )
    y_positions = (1.0, 0.0)
    for y, (group_label, day, first, second, first_label, second_label) in zip(
        y_positions, contrast_spec, strict=True
    ):
        rows = contrasts[contrasts.snapshot_day.eq(day)].set_index("variant")
        x1 = 100 * float(rows.loc[first, "detection_rate"])
        x2 = 100 * float(rows.loc[second, "detection_rate"])
        axis.plot([x1, x2], [y, y], color=COLORS["light_gray"], lw=5, zorder=1)
        axis.scatter(x1, y, color=COLORS["ink"], s=52, zorder=3)
        axis.scatter(x2, y, color=COLORS["gold"], s=52, zorder=3)
        axis.text(x1, y + 0.16, f"{first_label} {x1:.1f}%", ha="center", fontsize=8)
        axis.text(x2, y - 0.20, f"{second_label} {x2:.1f}%", ha="center", fontsize=8)
        if day == 10:
            axis.text(
                (x1 + x2) / 2,
                y - 0.39,
                f"{x2 - x1:+.1f} percentage points",
                color=COLORS["red"],
                ha="center",
                fontsize=8,
            )
    axis.set_yticks(y_positions, [item[0] for item in contrast_spec])
    axis.set_xlabel("Geometric indicator (%)")
    axis.set_xlim(15, 55)
    axis.set_ylim(-0.55, 1.42)
    axis.set_title("The observation rule changes detection", loc="left")
    axis.grid(axis="y", visible=False)
    _panel_label(axis, "D")

    fig.suptitle(
        "A recurring geometric signature is not a state label",
        fontsize=15.5,
        fontweight="bold",
    )
    fig.text(
        0.5,
        -0.012,
        "2/3 is a recurring geometric signature, not a state label.",
        ha="center",
        color=COLORS["gray"],
        fontsize=10,
    )
    paths = _save_figure(fig, output_dir, "figure_detection", dpi=dpi)
    return paths, {**data, "trajectories": trajectories}


def make_prediction_figure(
    tables: dict[str, pd.DataFrame],
    output_dir: Path,
    *,
    dpi: int = 600,
) -> tuple[list[Path], dict[str, pd.DataFrame]]:
    """Build Figure 2: held-out prediction from origin-time geometry."""

    _style()
    data = prediction_panel_data(tables)
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.5), constrained_layout=True)

    axis = axes[0, 0]
    styles = {
        "recent_linear": (COLORS["gray"], "-", 1.8),
        "half_power": (COLORS["red"], "--", 1.8),
        "two_thirds": (COLORS["cornflower"], "--", 1.8),
        "dynamics_ridge": (COLORS["purple"], "-", 2.2),
        "geometry_proxy": (COLORS["teal"], "-", 3.0),
    }
    for model in styles:
        rows = data["forecast"][data["forecast"].model.eq(model)].sort_values("horizon_days")
        color, linestyle, linewidth = styles[model]
        axis.plot(
            rows.horizon_days,
            rows.mean_absolute_log_error,
            color=color,
            ls=linestyle,
            lw=linewidth,
            marker="o",
            markersize=4.5,
            label=MODEL_LABELS[model],
        )
        axis.fill_between(
            rows.horizon_days,
            rows.absolute_log_error_ci95_lower,
            rows.absolute_log_error_ci95_upper,
            color=color,
            alpha=0.10,
            linewidth=0,
        )
    axis.set_xticks(FORECAST_HORIZONS)
    axis.set_xlabel("Forecast horizon (days)")
    axis.set_ylabel("Mean absolute log error")
    axis.set_ylim(0, 1.08)
    axis.set_title("Geometry improves future-area prediction", loc="left")
    axis.text(0.02, 0.96, "Lower is better", transform=axis.transAxes, va="top", color=COLORS["gray"])
    axis.legend(ncol=2, loc="upper left", bbox_to_anchor=(0.0, 0.86))
    _panel_label(axis, "A")

    axis = axes[0, 1]
    increment = data["geometry_increment"].sort_values("horizon_days")
    values = increment.mean_difference.to_numpy(dtype=float)
    lower = values - increment.ci95_lower.to_numpy(dtype=float)
    upper = increment.ci95_upper.to_numpy(dtype=float) - values
    axis.axhline(0, color=COLORS["gray"], lw=1.2)
    axis.errorbar(
        increment.horizon_days,
        values,
        yerr=[lower, upper],
        color=COLORS["teal"],
        marker="o",
        markersize=7,
        capsize=4,
        lw=2.2,
    )
    axis.fill_between(
        [0.5, 7.5],
        [-0.12, -0.12],
        [0, 0],
        color=COLORS["teal"],
        alpha=0.055,
        zorder=0,
    )
    axis.set_xticks(FORECAST_HORIZONS)
    axis.set_xlim(0.5, 7.5)
    axis.set_ylim(-0.12, 0.025)
    axis.set_xlabel("Forecast horizon (days)")
    axis.set_ylabel("Geometry error - dynamics error")
    axis.set_title("Paired improvement is consistent", loc="left")
    axis.text(
        0.97,
        0.08,
        "Negative values favor geometry",
        transform=axis.transAxes,
        ha="right",
        color=COLORS["teal"],
        fontsize=8.5,
    )
    _panel_label(axis, "B")

    axis = axes[1, 0]
    gains = data["day7_gain"].set_index("first_model").reindex(
        ["geometry_proxy", "geometry_indicator"]
    )
    values = gains.gain.to_numpy(dtype=float)
    lower = values - gains.gain_ci95_lower.to_numpy(dtype=float)
    upper = gains.gain_ci95_upper.to_numpy(dtype=float) - values
    positions = np.arange(2)
    axis.bar(
        positions,
        values,
        color=(COLORS["teal"], COLORS["cornflower"]),
        width=0.62,
        alpha=0.90,
    )
    axis.errorbar(
        positions,
        values,
        yerr=[lower, upper],
        fmt="none",
        color=COLORS["ink"],
        capsize=4,
        lw=1.2,
    )
    axis.set_xticks(positions, ["Full geometry\nproxy", "Binary geometric\nindicator"])
    axis.set_ylabel("Reduction in mean absolute log error")
    axis.set_ylim(0, 0.112)
    axis.set_title("The signal is richer than a two-thirds flag", loc="left")
    for position, value in zip(positions, values, strict=True):
        axis.text(position, value + 0.007, f"{value:.3f}", ha="center", fontweight="bold")
    axis.text(
        0.98,
        0.96,
        "Full geometry includes perimeter magnitude,\n"
        "excess perimeter, topology, and boundary change.",
        transform=axis.transAxes,
        ha="right",
        va="top",
        fontsize=8.4,
        color=COLORS["gray"],
    )
    _panel_label(axis, "C")

    axis = axes[1, 1]
    transition = data["transition"]
    positions = np.arange(len(transition))
    values = transition.balanced_accuracy.to_numpy(dtype=float)
    lower = values - transition.balanced_accuracy_ci95_lower.to_numpy(dtype=float)
    upper = transition.balanced_accuracy_ci95_upper.to_numpy(dtype=float) - values
    colors = [COLORS["gray"], COLORS["cornflower"], COLORS["purple"], COLORS["teal"]]
    axis.bar(positions, values, color=colors, width=0.68, alpha=0.92)
    axis.errorbar(
        positions,
        values,
        yerr=[lower, upper],
        fmt="none",
        color=COLORS["ink"],
        capsize=3.5,
        lw=1.15,
    )
    axis.axhline(0.5, color=COLORS["red"], ls="--", lw=1.5, label="Chance")
    axis.set_xticks(
        positions,
        [MODEL_LABELS[model] for model in transition.model],
        rotation=18,
        ha="right",
    )
    axis.set_ylabel("Balanced accuracy")
    axis.set_ylim(0.48, 0.87)
    axis.set_title("Geometry predicts future acceleration", loc="left")
    paired = data["transition_increment"].iloc[0]
    x1, x2 = 2, 3
    y = 0.845
    axis.plot([x1, x1, x2, x2], [y - 0.008, y, y, y - 0.008], color=COLORS["ink"], lw=1)
    axis.text(
        (x1 + x2) / 2,
        y + 0.006,
        f"+{paired.balanced_accuracy_difference:.3f}\n"
        f"95% CI {paired.ci95_lower:.3f} to {paired.ci95_upper:.3f}",
        ha="center",
        va="bottom",
        fontsize=8,
    )
    axis.legend(loc="upper left")
    _panel_label(axis, "D")

    fig.suptitle(
        "Current fire geometry predicts future fire dynamics",
        fontsize=15.5,
        fontweight="bold",
    )
    fig.text(
        0.5,
        -0.012,
        "Held-out fires from 2016-2020; uncertainty intervals resample whole fires.",
        ha="center",
        color=COLORS["gray"],
        fontsize=9.5,
    )
    paths = _save_figure(fig, output_dir, "figure_prediction", dpi=dpi)
    return paths, data


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_captions(output_dir: Path) -> tuple[Path, Path]:
    detection_caption = output_dir / "figure_detection_caption.md"
    prediction_caption = output_dir / "figure_prediction_caption.md"
    detection_caption.write_text(
        """**Figure 1. A recurring perimeter-area signature is informative but is not a state label.** """
        """We asked whether held-out FIRED trajectories exhibit the predicted geometric scaling and whether an uncertainty-aware geometric indicator behaves like a stable fire-state measurement. """
        """(A) Representative held-out trajectories through day 10 were selected reproducibly as the event nearest the median detector-evidence margin within compatible, ambiguous, and inconsistent classes; lines show mapped exterior perimeter against cumulative mapped area, with one-half and two-thirds slope guides centered on each trajectory. """
        """(B) Exterior-perimeter slope distributions at days 5, 7, 10, 14, and 21 (violins show the central 98%; diamonds are full-sample medians) remain near two-thirds, with medians of 0.676, 0.650, 0.647, 0.631, and 0.622. """
        """(C) The prespecified geometric indicator rises from 26.6% at day 5 to 55.2% at day 21, whereas persistent detection rises from 0.0% to 40.7%; these are detection frequencies, not sensitivity or specificity for an unobserved latent state. """
        """(D) Detection depends on the observation operator: at day 10 it falls from 49.2% with all mapped observations to 23.8% with every-other observations, while at day 7 it changes from 42.2% using exterior perimeter to 44.2% using total perimeter. """
        """All summaries use the temporally held-out 2016-2020 cohort; intervals in panel A are ordinary 95% slope intervals from the locked detector output. The near-two-thirds relation is therefore a recurring mapped geometric signature, not a uniquely identified coherent state or measurement of active fireline.\n""",
        encoding="utf-8",
    )
    prediction_caption.write_text(
        """**Figure 2. Origin-time mapped geometry predicts subsequent fire growth and acceleration.** """
        """We asked whether geometry available at day 7 improves prospective prediction beyond current area and recent growth history in temporally held-out FIRED fires. """
        """(A) Mean absolute log error for future cumulative area at one-, three-, five-, and seven-day horizons. The geometry proxy has errors of 0.122, 0.217, 0.310, and 0.366, compared with 0.140, 0.281, 0.386, and 0.443 for the equally informed dynamics ridge; fixed temporal extrapolations under one-half and two-thirds growth laws perform worse. Shading is the 95% whole-fire bootstrap interval. """
        """(B) Paired geometry-proxy error minus dynamics-ridge error is negative at every horizon: -0.017, -0.064, -0.076, and -0.077, with all 95% whole-fire bootstrap intervals below zero. """
        """(C) At seven days ahead, full geometry reduces mean absolute log error by 0.077 (95% interval 0.052-0.101), whereas adding only the binary geometric indicator reduces it by 0.011 (0.003-0.019). The predictive signal therefore includes perimeter magnitude, excess perimeter, topology, and boundary change rather than a two-thirds flag alone. """
        """(D) For acceleration over the next three days, held-out balanced accuracy is 0.583 for persistence, 0.688 for area, 0.692 for dynamics, and 0.790 for the geometry proxy. The paired geometry improvement over dynamics is 0.098 balanced-accuracy units (95% interval 0.063-0.134). """
        """Models were developed on 2001-2012, tuned on 2013-2015, and evaluated on 2016-2020; every plotted predictor is available at the forecast origin, and uncertainty resamples whole fires. These results establish prospective predictive value for mapped geometry, not causal identification of coherence, fuel connectivity, energetic metabolism, or the canonical latent-state model.\n""",
        encoding="utf-8",
    )
    return detection_caption, prediction_caption


def _export_source_data(
    output_dir: Path,
    detection_data: dict[str, pd.DataFrame],
    prediction_data: dict[str, pd.DataFrame],
) -> list[Path]:
    paths: list[Path] = []
    exports = {
        "figure_detection_summary.csv": detection_data["summary"],
        "figure_detection_examples.csv": detection_data["examples"],
        "figure_detection_trajectories.csv": detection_data["trajectories"],
        "figure_detection_observation_contrasts.csv": detection_data["contrasts"],
        "figure_prediction_forecast_metrics.csv": prediction_data["forecast"],
        "figure_prediction_paired_errors.csv": prediction_data["geometry_increment"],
        "figure_prediction_geometry_signal.csv": prediction_data["day7_gain"],
        "figure_prediction_transition_metrics.csv": prediction_data["transition"],
        "figure_prediction_transition_increment.csv": prediction_data["transition_increment"],
    }
    for name, frame in exports.items():
        path = output_dir / name
        frame.to_csv(path, index=False)
        paths.append(path)
    return paths


def build_detection_prediction_figures(
    inputs: EmpiricalFigureInputs,
    output_dir: Path,
    *,
    dpi: int = 600,
) -> dict[str, object]:
    """Build both empirical figures, captions, source tables, and a manifest."""

    if dpi < 300:
        raise ValueError("publication raster output requires at least 300 dpi")
    tables = _read_validation_tables(inputs)
    sequences = pd.read_csv(inputs.sequences_path)
    geometry = pd.read_csv(inputs.geometry_path)
    merged = merge_geometry_sequences(sequences, geometry)
    output_dir.mkdir(parents=True, exist_ok=True)

    detection_paths, detection_data = make_detection_figure(
        tables, merged, output_dir, dpi=dpi
    )
    prediction_paths, prediction_data = make_prediction_figure(
        tables, output_dir, dpi=dpi
    )
    caption_paths = list(_write_captions(output_dir))
    source_paths = _export_source_data(output_dir, detection_data, prediction_data)

    manifest_path = output_dir / "figure_manifest.json"
    manifest = {
        "scope": "presentation-only rendering of locked adversarial-validation outputs",
        "dpi": dpi,
        "reference_exponents": {"one_half": HALF_POWER, "two_thirds": TWO_THIRDS},
        "example_selection": (
            "day-10 held-out event nearest the median normalized CI margin within "
            "compatible, ambiguous, and inconsistent detector classes"
        ),
        "future_derived_predictors_recomputed": False,
        "input_sha256": {
            str(path): _sha256(path) for path in inputs.required_paths()
        },
        "outputs": [
            str(path)
            for path in detection_paths + prediction_paths + caption_paths + source_paths
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest["manifest"] = str(manifest_path)
    return manifest
