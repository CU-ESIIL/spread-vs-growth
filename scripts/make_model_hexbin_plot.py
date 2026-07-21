"""Generate a dense, reference-style hexbin plot from model outputs."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

TMP_DIR = PROJECT_ROOT / "tmp"
(TMP_DIR / "matplotlib").mkdir(parents=True, exist_ok=True)
(TMP_DIR / "cache").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(TMP_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(TMP_DIR / "cache"))

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

from fire_model_scaling.fit_scaling import ols_loglog
from fire_model_scaling.run_benchmarks import run_exact_ellipse
from fire_model_scaling.run_cellular import run_cellular
from fire_model_scaling.run_huygens import run_huygens
from fire_model_scaling.run_level_set import run_level_set


def dense_config(output_steps: int, heterogeneity_levels: list[float]) -> dict[str, Any]:
    directions = [0.0, 30.0, 60.0, 90.0]
    wind_factors = [1.0, 1.35, 1.8]
    scenarios: list[dict[str, Any]] = []
    for wind_factor in wind_factors:
        for direction in directions:
            scenarios.append(
                {
                    "name": f"wind_{str(wind_factor).replace('.', 'p')}_dir_{int(direction)}",
                    "spread_rate": 1.0,
                    "wind_factor": wind_factor,
                    "direction_degrees": direction,
                    "heterogeneity": 0.0,
                }
            )
    for heterogeneity in heterogeneity_levels:
        for replicate_seed in range(4):
            for wind_factor in [1.0, 1.35]:
                scenarios.append(
                    {
                        "name": (
                            f"heterogeneous_{str(heterogeneity).replace('.', 'p')}"
                            f"_wind_{str(wind_factor).replace('.', 'p')}"
                            f"_repgroup_{replicate_seed}"
                        ),
                        "spread_rate": 1.0,
                        "wind_factor": wind_factor,
                        "direction_degrees": 30.0 * replicate_seed,
                        "heterogeneity": heterogeneity,
                        "replicates": 2,
                    }
                )

    return {
        "experiment": {
            "name": "model_hexbin_dense",
            "description": "Dense homogeneous and anisotropic model-output cloud for talk figures.",
            "random_seed": 42,
            "output_steps": output_steps,
            "exclude_early_fraction": 0.15,
            "max_domain_contact_fraction": 0.0,
        },
        "domain": {
            "width": 300,
            "height": 300,
            "cell_size": 0.1,
            "center": [150.0, 150.0],
        },
        "initial_shapes": ["compact", "irregular", "line"],
        "scenarios": scenarios,
        "models": {
            "exact_ellipse": {
                "enabled": True,
                "axis_ratio": 2.0,
                "max_radius": 130.0,
            },
            "huygens": {
                "enabled": True,
                "step_size": 2.4,
                "perimeter_samples": 96,
            },
            "level_set": {
                "enabled": True,
                "max_radius": 130.0,
            },
            "cellular": {
                "enabled": True,
                "connectivity": 8,
                "max_time": 130.0,
            },
        },
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, object]]:
    with path.open() as file:
        return list(csv.DictReader(file))


def is_true(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def valid_xy(rows: list[dict[str, object]]) -> tuple[np.ndarray, np.ndarray, list[dict[str, object]]]:
    valid_rows = [
        row
        for row in rows
        if is_true(row["valid_geometry"])
        and not is_true(row["domain_edge_contact"])
        and float(row["area"]) > 0
        and float(row["exterior_perimeter"]) > 0
    ]
    area = np.array([float(row["area"]) for row in valid_rows])
    perimeter = np.array([float(row["exterior_perimeter"]) for row in valid_rows])
    return area, perimeter, valid_rows


def add_reference_line(
    ax: plt.Axes,
    x: np.ndarray,
    *,
    x0: float,
    y0: float,
    exponent: float,
    color: str,
    linestyle: tuple[int, tuple[int, ...]] | str,
    label: str,
    linewidth: float = 2.3,
) -> None:
    ax.plot(
        x,
        y0 * (x / x0) ** exponent,
        color=color,
        linestyle=linestyle,
        linewidth=linewidth,
        label=label,
    )


def add_power_law_line(
    ax: plt.Axes,
    x: np.ndarray,
    *,
    coefficient: float,
    exponent: float,
    color: str,
    linestyle: tuple[int, tuple[int, ...]] | str,
    label: str,
    linewidth: float = 2.3,
) -> None:
    ax.plot(
        x,
        coefficient * x**exponent,
        color=color,
        linestyle=linestyle,
        linewidth=linewidth,
        label=label,
    )


def write_hexbin_plot(
    rows: list[dict[str, object]],
    output_base: Path,
    heterogeneity_levels: list[float],
    model_filter: list[str],
    show_high_reference_lines: bool,
) -> None:
    area, perimeter, valid_rows = valid_xy(rows)
    if len(area) < 10:
        raise ValueError("Not enough valid model outputs to plot.")

    fit_alpha, fit_sigma, _, _, _, _ = ols_loglog(area, perimeter)
    x_min = float(np.percentile(area, 0.5))
    x_max = float(np.percentile(area, 99.5))
    y_min = float(np.percentile(perimeter, 0.5))
    y_max = float(np.percentile(perimeter, 99.5))
    x = np.logspace(np.log10(x_min), np.log10(x_max), 200)
    anchor_x = float(np.percentile(area, 4.0))
    low_mask = area <= np.percentile(area, 8.0)
    anchor_y = float(np.median(perimeter[low_mask])) if np.any(low_mask) else float(np.percentile(perimeter, 4.0))

    fig, ax = plt.subplots(figsize=(16, 9), constrained_layout=True)
    hexbin = ax.hexbin(
        area,
        perimeter,
        xscale="log",
        yscale="log",
        gridsize=64,
        mincnt=1,
        linewidths=0.0,
        cmap="magma_r",
        norm=LogNorm(),
    )
    colorbar = fig.colorbar(hexbin, ax=ax, pad=0.012)
    colorbar.set_label("Model outputs per hexbin", fontsize=17)
    colorbar.ax.tick_params(labelsize=14)

    if show_high_reference_lines:
        add_reference_line(
            ax,
            x,
            x0=anchor_x,
            y0=anchor_y,
            exponent=0.75,
            color="#2e8b57",
            linestyle=(0, (8, 5)),
            label=r"$P \propto A^{3/4}$",
        )
        add_reference_line(
            ax,
            x,
            x0=anchor_x,
            y0=anchor_y,
            exponent=2 / 3,
            color="#5f87e9",
            linestyle="-",
            label=r"organized growth: $P \propto A^{2/3}$",
        )
    add_power_law_line(
        ax,
        x,
        coefficient=10.0**fit_alpha,
        exponent=0.5,
        color="#b22222",
        linestyle=(0, (8, 5)),
        label=r"diffusion-like spread: $P \propto A^{1/2}$",
    )
    add_power_law_line(
        ax,
        x,
        coefficient=10.0**fit_alpha,
        exponent=fit_sigma,
        color="#555555",
        linestyle=":",
        label=fr"model fit: slope {fit_sigma:.2f}",
        linewidth=1.8,
    )

    ax.set_xlim(x_min * 0.85, x_max * 1.15)
    ax.set_ylim(y_min * 0.85, y_max * 1.3)
    ax.set_xlabel(r"Model fire area (km$^2$, log scale)", fontsize=18)
    ax.set_ylabel("Model fire perimeter (km, log scale)", fontsize=18)
    ax.tick_params(axis="both", which="major", labelsize=16, length=7, width=1.0)
    ax.tick_params(axis="both", which="minor", length=3.5, width=0.8)
    ax.grid(True, which="major", color="#d9d9d9", linewidth=0.8, alpha=0.75)
    ax.grid(False, which="minor")
    ax.legend(frameon=False, fontsize=14, loc="lower right", handlelength=2.7)

    model_summary = ", ".join(model_filter) if model_filter else "all models"
    summary = (
        f"n={len(valid_rows):,}\n"
        f"model cloud fit: {fit_sigma:.2f}\n"
        f"{model_summary}\n"
        f"heterogeneity: "
        f"{', '.join(f'{level:g}' for level in heterogeneity_levels) if heterogeneity_levels else 'excluded'}"
    )
    ax.text(
        0.02,
        0.96,
        summary,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=12,
        color="#333333",
    )

    output_base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_base.with_suffix(".png"), dpi=200)
    fig.savefig(output_base.with_suffix(".pdf"))
    fig.savefig(output_base.with_suffix(".svg"))
    plt.close(fig)


def output_stem_for_metadata(output_name: str) -> str:
    if output_name == "model_outputs_hexbin":
        return "model_hexbin"
    return output_name


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-steps", type=int, default=56)
    parser.add_argument("--include-heterogeneous", action="store_true")
    parser.add_argument(
        "--heterogeneity-levels",
        nargs="*",
        type=float,
        default=None,
        help="Optional heterogeneity strengths to include, e.g. 0.25 0.5 0.75.",
    )
    parser.add_argument("--output-name", default="model_outputs_hexbin")
    parser.add_argument(
        "--models",
        nargs="*",
        default=[],
        help="Optional model ids to plot, for example level_set_emulator.",
    )
    parser.add_argument(
        "--input-metrics",
        type=Path,
        default=None,
        help="Optional existing metrics CSV to reuse while writing a new figure name.",
    )
    parser.add_argument("--reuse-metrics", action="store_true")
    parser.add_argument(
        "--hide-high-reference-lines",
        action="store_true",
        help="Hide the 2/3 and 3/4 reference lines while keeping 1/2 and fitted slope.",
    )
    args = parser.parse_args()

    if args.heterogeneity_levels is not None:
        heterogeneity_levels = args.heterogeneity_levels
    elif args.include_heterogeneous:
        heterogeneity_levels = [0.35]
    else:
        heterogeneity_levels = []

    config = dense_config(args.output_steps, heterogeneity_levels)
    output_root = PROJECT_ROOT / "outputs" / f"{args.output_name}_work"
    metadata_stem = output_stem_for_metadata(args.output_name)
    metrics_path = args.input_metrics or PROJECT_ROOT / "outputs" / "metrics" / f"{metadata_stem}_metrics.csv"
    if args.reuse_metrics and metrics_path.exists():
        rows = read_csv(metrics_path)
    else:
        rows: list[dict[str, object]] = []
        rows.extend(run_exact_ellipse(config, output_root))
        rows.extend(run_huygens(config, output_root))
        rows.extend(run_level_set(config, output_root))
        rows.extend(run_cellular(config, output_root))
        write_csv(metrics_path, rows)
    if args.models:
        rows = [row for row in rows if str(row["model"]) in set(args.models)]
    config_path = PROJECT_ROOT / "outputs" / "logs" / f"{metadata_stem}_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2))

    output_base = PROJECT_ROOT / "outputs" / "figures" / args.output_name
    write_hexbin_plot(
        rows,
        output_base,
        heterogeneity_levels,
        args.models,
        show_high_reference_lines=not args.hide_high_reference_lines,
    )
    print(f"Plotted {len(rows):,} dense model output records from {metrics_path}")
    print(f"Wrote model hexbin figure to {output_base.with_suffix('.png')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
