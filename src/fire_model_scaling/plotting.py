"""Publication and presentation figures for fire-model scaling outputs."""

from __future__ import annotations

import csv
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TMP_DIR = PROJECT_ROOT / "tmp"
(TMP_DIR / "matplotlib").mkdir(parents=True, exist_ok=True)
(TMP_DIR / "cache").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(TMP_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(TMP_DIR / "cache"))

import matplotlib.pyplot as plt
import numpy as np


MODEL_COLORS = {
    "exact_ellipse": "#222222",
    "huygens_emulator": "#1f77b4",
    "level_set_emulator": "#2ca02c",
    "cellular_emulator": "#d62728",
}


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open() as file:
        return list(csv.DictReader(file))


def write_scaling_figures(metrics_path: Path, fits_path: Path, output_dir: Path) -> None:
    rows = read_csv_dicts(metrics_path)
    fits = read_csv_dicts(fits_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_loglog_plot(rows, fits, output_dir / "figure2_loglog_perimeter_area")
    write_sigma_plot(fits, output_dir / "figure3_sigma_by_model")


def write_loglog_plot(rows: list[dict[str, str]], fits: list[dict[str, str]], output_base: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        if row["valid_geometry"] != "True" or row["domain_edge_contact"] == "True":
            continue
        key = (row["model"], row["scenario"], row["initial_shape"], row["replicate"])
        grouped.setdefault(key, []).append(row)

    all_area = []
    all_perim = []
    models_seen = set()
    for key, group in grouped.items():
        model = key[0]
        group = sorted(group, key=lambda row: float(row["time"]))
        area = np.array([float(row["area"]) for row in group])
        perim = np.array([float(row["exterior_perimeter"]) for row in group])
        all_area.extend(area.tolist())
        all_perim.extend(perim.tolist())
        label = model.replace("_emulator", "") if model not in models_seen else None
        ax.plot(
            area,
            perim,
            color=MODEL_COLORS.get(model, "#777777"),
            alpha=0.35,
            linewidth=1.1,
            label=label,
        )
        models_seen.add(model)

    if all_area and all_perim:
        anchor_area = float(np.median(all_area))
        anchor_perim = float(np.median(all_perim))
        x = np.logspace(np.log10(min(all_area)), np.log10(max(all_area)), 100)
        for sigma, style, label in [(0.5, "-", "1/2"), (2 / 3, "--", "2/3"), (0.75, ":", "3/4")]:
            y = anchor_perim * (x / anchor_area) ** sigma
            ax.plot(x, y, color="black", linestyle=style, linewidth=1.0, label=f"slope {label}")

    summary_lines = []
    for model in sorted({fit["model"] for fit in fits}):
        sigmas = np.array([float(fit["sigma"]) for fit in fits if fit["model"] == model])
        summary_lines.append(f"{model.replace('_emulator', '')}: median sigma={np.median(sigmas):.2f}")
    ax.text(
        0.99,
        0.02,
        "\n".join(summary_lines),
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
        bbox={"facecolor": "white", "edgecolor": "#cccccc", "alpha": 0.86},
    )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Burned area A")
    ax.set_ylabel("Exterior perimeter P")
    ax.set_title("Perimeter-area scaling from Tier-1 fire-model experiments")
    ax.grid(True, which="both", color="#dddddd", linewidth=0.6)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    _save_figure(fig, output_base)


def write_sigma_plot(fits: list[dict[str, str]], output_base: Path) -> None:
    if not fits:
        return
    labels = [f"{fit['model']}\n{fit['scenario']}\n{fit['initial_shape']}" for fit in fits]
    sigma = np.array([float(fit["sigma"]) for fit in fits])
    low = np.array([float(fit["ci_low"]) for fit in fits])
    high = np.array([float(fit["ci_high"]) for fit in fits])
    y = np.arange(len(fits))

    fig, ax = plt.subplots(figsize=(8, max(4, 0.35 * len(fits))), constrained_layout=True)
    ax.errorbar(sigma, y, xerr=[sigma - low, high - sigma], fmt="o", color="#333333")
    for reference, label in [(0.5, "0.50"), (2 / 3, "0.667"), (0.75, "0.75")]:
        ax.axvline(reference, color="#999999", linestyle="--", linewidth=1.0)
        ax.text(reference, len(fits) - 0.5, label, rotation=90, va="top", ha="right", fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("Estimated scaling exponent sigma")
    ax.set_title("Estimated exponent by model, scenario, and ignition")
    ax.grid(True, axis="x", color="#dddddd", linewidth=0.6)
    _save_figure(fig, output_base)


def write_presentation_figure(metrics_path: Path, fits_path: Path, output_base: Path) -> None:
    rows = read_csv_dicts(metrics_path)
    fits = read_csv_dicts(fits_path)
    fig, (main_ax, summary_ax) = plt.subplots(
        1,
        2,
        figsize=(13.333, 7.5),
        gridspec_kw={"width_ratios": [3.0, 1.15]},
        constrained_layout=True,
    )
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if row["scenario"] != "isotropic" or row["initial_shape"] != "compact":
            continue
        grouped.setdefault(row["model"], []).append(row)

    all_area = []
    all_perim = []
    for model, group in grouped.items():
        group = sorted(group, key=lambda row: float(row["time"]))
        area = np.array([float(row["area"]) for row in group])
        perim = np.array([float(row["exterior_perimeter"]) for row in group])
        all_area.extend(area.tolist())
        all_perim.extend(perim.tolist())
        main_ax.plot(area, perim, marker="o", color=MODEL_COLORS.get(model, "#777777"), label=model)
        if len(area):
            main_ax.text(area[-1], perim[-1], model.replace("_emulator", ""), fontsize=9)

    if all_area and all_perim:
        anchor_area = float(np.median(all_area))
        anchor_perim = float(np.median(all_perim))
        x = np.logspace(np.log10(min(all_area)), np.log10(max(all_area)), 100)
        for sigma, style, label in [(0.5, "-", "1/2"), (2 / 3, "--", "2/3")]:
            main_ax.plot(
                x,
                anchor_perim * (x / anchor_area) ** sigma,
                color="black",
                linestyle=style,
                linewidth=1.2,
                label=f"slope {label}",
            )

    main_ax.set_xscale("log")
    main_ax.set_yscale("log")
    main_ax.set_title("What geometry do classical fire models generate?", fontsize=18)
    main_ax.set_xlabel("Burned area A")
    main_ax.set_ylabel("Exterior perimeter P")
    main_ax.grid(True, which="both", color="#dddddd", linewidth=0.6)

    summary_ax.axis("off")
    lines = ["Model | mechanism | sigma", ""]
    for fit in fits:
        if fit["scenario"] == "isotropic" and fit["initial_shape"] == "compact":
            mechanism = {
                "exact_ellipse": "analytic benchmark",
                "huygens_emulator": "local wavelets",
                "level_set_emulator": "normal front",
                "cellular_emulator": "neighbor ignition",
            }.get(fit["model"], "model output")
            lines.append(
                f"{fit['model'].replace('_emulator', '')}\n{mechanism}\n"
                f"sigma={float(fit['sigma']):.2f} [{float(fit['ci_low']):.2f}, {float(fit['ci_high']):.2f}]"
            )
            lines.append("")
    summary_ax.text(0.0, 1.0, "\n".join(lines), va="top", fontsize=10)
    output_base.parent.mkdir(parents=True, exist_ok=True)
    _save_figure(fig, output_base)


def _save_figure(fig: plt.Figure, output_base: Path) -> None:
    fig.savefig(output_base.with_suffix(".png"), dpi=200)
    fig.savefig(output_base.with_suffix(".svg"))
    fig.savefig(output_base.with_suffix(".pdf"))
    plt.close(fig)
