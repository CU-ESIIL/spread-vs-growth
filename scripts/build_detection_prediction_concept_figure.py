#!/usr/bin/env python3
"""Build a publication-ready conceptual detection/prediction figure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle


BLUE = "#4C78A8"
BLUE_LIGHT = "#DCE6F1"
BLUE_MID = "#AFC3D8"
RED = "#C23B3B"
RED_DARK = "#8E2727"
ORANGE = "#F58518"
INK = "#202428"
GRAY = "#626A70"
LIGHT_GRAY = "#D9DEE2"


def radial_profile(seed: int, *, points: int = 320, roughness: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Return a deterministic, smooth irregular radial profile."""
    rng = np.random.default_rng(seed)
    theta = np.linspace(0, 2 * np.pi, points, endpoint=False)
    radius = np.ones_like(theta)
    for harmonic in range(2, 10):
        amplitude = roughness * rng.uniform(0.018, 0.065) / np.sqrt(harmonic)
        phase = rng.uniform(0, 2 * np.pi)
        radius += amplitude * np.cos(harmonic * theta + phase)
    return theta, np.clip(radius, 0.70, None)


def footprint(
    center: tuple[float, float],
    scale: float,
    seed: int,
    *,
    stretch: tuple[float, float] = (1.0, 1.0),
    drift: float = 0.0,
    roughness: float = 1.0,
) -> np.ndarray:
    """Construct a deterministic synthetic fire footprint in axes coordinates."""
    theta, radius = radial_profile(seed, roughness=roughness)
    directional = 1 + drift * np.cos(theta)
    x = center[0] + scale * stretch[0] * radius * directional * np.cos(theta)
    y = center[1] + scale * stretch[1] * radius * np.sin(theta)
    return np.column_stack([x, y])


def add_polygon(
    ax: plt.Axes,
    vertices: np.ndarray,
    *,
    facecolor: str,
    edgecolor: str,
    alpha: float = 1.0,
    linewidth: float = 1.2,
    linestyle: str = "-",
    zorder: float = 2,
) -> Polygon:
    patch = Polygon(
        vertices,
        closed=True,
        facecolor=facecolor,
        edgecolor=edgecolor,
        alpha=alpha,
        linewidth=linewidth,
        linestyle=linestyle,
        joinstyle="round",
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def panel_heading(ax: plt.Axes, letter: str, title: str, subtitle: str) -> None:
    ax.text(0.0, 1.01, letter, transform=ax.transAxes, fontsize=13, fontweight="bold", va="bottom")
    ax.text(0.065, 1.01, title, transform=ax.transAxes, fontsize=11.5, fontweight="bold", va="bottom")
    ax.text(0.065, 0.955, subtitle, transform=ax.transAxes, fontsize=7.8, color=GRAY, va="bottom")


def add_callout(ax: plt.Axes, headline: str, detail: str, color: str) -> None:
    ax.add_patch(Rectangle((0.02, 0.015), 0.96, 0.145, facecolor="#F7F8F9", edgecolor=LIGHT_GRAY, linewidth=0.8))
    ax.add_patch(Rectangle((0.02, 0.151), 0.96, 0.009, facecolor=color, edgecolor="none"))
    ax.text(0.05, 0.112, headline, fontsize=7.8, fontweight="bold", color=INK, va="center")
    ax.text(0.05, 0.058, detail, fontsize=6.5, color=GRAY, va="center")


def draw_detection(ax: plt.Axes) -> None:
    panel_heading(
        ax,
        "A",
        "Detect a change in growth",
        "Compare realized growth with prior-state potential.",
    )

    centers = [(0.10, 0.48), (0.23, 0.49), (0.37, 0.50), (0.51, 0.50)]
    scales = [0.047, 0.067, 0.086, 0.107]
    colors = ["#F4B3A9", "#EA9588", "#DE7567", "#D15849"]
    for index, (center, scale, color) in enumerate(zip(centers, scales, colors, strict=True)):
        vertices = footprint(center, scale, 31, stretch=(1.25, 0.82), drift=0.08)
        add_polygon(ax, vertices, facecolor=color, edgecolor=RED_DARK, alpha=0.93, linewidth=0.75, zorder=2 + index * 0.1)

    expected = footprint((0.76, 0.50), 0.165, 31, stretch=(1.12, 0.90), drift=0.12, roughness=0.9)
    realized = footprint((0.70, 0.50), 0.130, 31, stretch=(1.05, 0.91), drift=-0.02, roughness=1.05)
    add_polygon(ax, expected, facecolor=BLUE_LIGHT, edgecolor=BLUE, alpha=0.55, linewidth=1.35, linestyle=(0, (4, 3)), zorder=1)
    add_polygon(ax, realized, facecolor=RED, edgecolor=RED_DARK, alpha=0.98, linewidth=1.4, zorder=4)

    ax.text(0.70, 0.50, "mapped fire\nat time $t$", ha="center", va="center", fontsize=7.5, color="white", fontweight="bold", zorder=5)
    ax.annotate(
        "growth expected\nfrom the prior state",
        xy=(0.84, 0.62), xytext=(0.74, 0.755),
        fontsize=7.2, ha="center", color=INK,
        arrowprops={"arrowstyle": "->", "color": INK, "lw": 0.9},
    )
    ax.annotate(
        "realized growth",
        xy=(0.59, 0.43), xytext=(0.48, 0.365),
        fontsize=7.2, ha="center", color=INK,
        arrowprops={"arrowstyle": "->", "color": INK, "lw": 0.9},
    )
    ax.annotate(
        "departure from expectation",
        xy=(0.89, 0.47), xytext=(0.79, 0.345),
        fontsize=7.2, ha="center", color=BLUE,
        arrowprops={"arrowstyle": "-[,widthB=2.0,lengthB=0.45", "color": BLUE, "lw": 1.0},
    )

    ax.add_patch(FancyArrowPatch((0.07, 0.30), (0.54, 0.30), arrowstyle="-|>", mutation_scale=8, linewidth=0.9, color=INK))
    for x, label in zip([0.10, 0.23, 0.37, 0.51], ["$t-3$", "$t-2$", "$t-1$", "$t$"], strict=True):
        ax.text(x, 0.266, label, ha="center", fontsize=6.7, color=GRAY)
    ax.text(0.30, 0.222, "mapped history", ha="center", fontsize=6.7, color=GRAY)

    ax.text(0.04, 0.885, r"$q_t=\log(M_{\rm obs}+\epsilon)-\log(\widehat M_{\rm potential}+\epsilon)$", fontsize=8.0, color=INK)
    ax.text(0.04, 0.842, r"A large negative $q_t$ flags a growth deficit.", fontsize=7.1, color=GRAY)
    add_callout(
        ax,
        "A residual detects change, not cause.",
        "Fuel, weather, barriers, and suppression need independent data.",
        BLUE,
    )


def draw_prediction(ax: plt.Axes) -> None:
    panel_heading(
        ax,
        "B",
        "Constrain what happens next",
        "Propagate size, geometry, and recent dynamics.",
    )

    present = footprint((0.22, 0.50), 0.122, 71, stretch=(1.04, 0.90), roughness=1.05)
    add_polygon(ax, present, facecolor=RED, edgecolor=RED_DARK, linewidth=1.4, zorder=5)
    ax.text(0.22, 0.50, "present\nfire", ha="center", va="center", fontsize=7.6, color="white", fontweight="bold", zorder=6)

    ax.add_patch(FancyArrowPatch((0.35, 0.50), (0.45, 0.50), arrowstyle="-|>", mutation_scale=9, linewidth=1.0, color=GRAY, zorder=6))

    broad_specs = [
        ((0.67, 0.55), 0.205, 101, (1.20, 0.86), 0.18),
        ((0.69, 0.48), 0.225, 102, (1.10, 0.96), 0.12),
        ((0.66, 0.50), 0.245, 103, (1.13, 0.88), 0.21),
        ((0.70, 0.52), 0.185, 104, (1.27, 0.78), 0.24),
    ]
    for center, scale, seed, stretch, drift in broad_specs:
        vertices = footprint(center, scale, seed, stretch=stretch, drift=drift, roughness=0.8)
        add_polygon(ax, vertices, facecolor=BLUE_LIGHT, edgecolor=BLUE, alpha=0.22, linewidth=0.95, linestyle=(0, (3, 3)), zorder=1)

    narrow_specs = [
        ((0.66, 0.50), 0.175, 71, (1.24, 0.82), 0.21),
        ((0.67, 0.50), 0.192, 72, (1.22, 0.85), 0.22),
        ((0.68, 0.50), 0.207, 73, (1.20, 0.86), 0.23),
    ]
    for index, (center, scale, seed, stretch, drift) in enumerate(narrow_specs):
        vertices = footprint(center, scale, seed, stretch=stretch, drift=drift, roughness=0.75)
        add_polygon(
            ax,
            vertices,
            facecolor="#E5A6A0" if index == 1 else "none",
            edgecolor=RED_DARK,
            alpha=0.30 if index == 1 else 0.60,
            linewidth=1.05,
            zorder=3 + index * 0.1,
        )

    ax.annotate(
        "possible futures\nfrom size alone",
        xy=(0.87, 0.68), xytext=(0.86, 0.705),
        ha="center", fontsize=7.2, color=BLUE,
        arrowprops={"arrowstyle": "->", "color": BLUE, "lw": 0.9},
    )
    ax.annotate(
        "narrower futures from\nmapped geometry + dynamics",
        xy=(0.78, 0.43), xytext=(0.78, 0.285),
        ha="center", fontsize=7.2, color=RED_DARK,
        arrowprops={"arrowstyle": "->", "color": RED_DARK, "lw": 0.9},
    )

    ax.text(0.39, 0.855, r"conditional closure: $A'=\beta_0 G(C,F)A^{2/3}$", fontsize=7.6, color=INK)
    ax.text(0.39, 0.812, r"$C$ and reachable fuel $F$ need independent measurements.", fontsize=6.4, color=GRAY)

    add_callout(
        ax,
        "Same area, different futures.",
        "Geometry narrows outcomes; new forcing selects the realized path.",
        RED,
    )


def build_figure(output_dir: Path) -> list[Path]:
    """Render the conceptual figure in publication and presentation formats."""
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "mathtext.fontset": "dejavusans",
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "savefig.facecolor": "white",
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.25), gridspec_kw={"wspace": 0.10})
    for ax in axes:
        ax.set_xlim(0, 1.03)
        ax.set_ylim(0, 1)
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")
    draw_detection(axes[0])
    draw_prediction(axes[1])

    fig.suptitle("Fire geometry records change and constrains near-term prediction", x=0.055, y=0.975, ha="left", fontsize=11.4, fontweight="bold", color=INK)
    fig.add_artist(plt.Line2D([0.505, 0.505], [0.08, 0.875], transform=fig.transFigure, color=LIGHT_GRAY, linewidth=0.8))
    fig.subplots_adjust(left=0.05, right=0.985, top=0.86, bottom=0.04)

    stem = output_dir / "figure_detection_prediction_concept"
    paths = []
    for suffix in ("pdf", "svg", "png"):
        path = stem.with_suffix(f".{suffix}")
        fig.savefig(path, dpi=600 if suffix == "png" else None, bbox_inches="tight", pad_inches=0.04)
        paths.append(path)
    plt.close(fig)

    caption = (
        "**Conceptual framework for detection and prediction from a mapped fire state.** "
        "(A) Detection compares realized mapped growth with growth expected from the preceding "
        "state. A large negative realization residual identifies a changed trajectory but cannot "
        "attribute that change to fuel, weather, barriers, or suppression without independent "
        "observations. (B) Prediction propagates the present mapped state forward. Area alone admits "
        "a broad set of possible futures, whereas geometry and recent dynamics narrow near-term "
        "possibilities. The displayed two-thirds closure is conditional: latent coherence and "
        "reachable fuel require independent measurement, and future forcing determines the realized path. "
        "All footprints are deterministic synthetic schematics, not wildfire observations or fitted forecasts."
    )
    (output_dir / "figure_caption.md").write_text(caption + "\n")
    provenance = {
        "figure_type": "conceptual schematic",
        "source_script": "scripts/build_detection_prediction_concept_figure.py",
        "data": "none; deterministic synthetic polygons",
        "seed_families": [31, 71, 72, 73, 101, 102, 103, 104],
        "empirical_claim_boundary": "The figure depicts the theoretical logic, not measured detection or prediction performance.",
        "outputs": [path.name for path in paths],
    }
    (output_dir / "figure_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/conceptual_detection_prediction"))
    return parser.parse_args()


if __name__ == "__main__":
    build_figure(parse_args().output_dir)
