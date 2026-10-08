"""Publication-quality analytical, synthetic, and hypothetical SI figures."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import cumulative_trapezoid, solve_ivp

from .geometry import polygon_area, polygon_perimeter, right_angle_polygon
from .growth import area_acceleration, constant_beta_area, finite_speed_bound, normalized_area
from .residence import finite_recruitment_exponential_rate
from .scaling import matching_efficiency, matching_ratio
from .synthetic import rough_surface_projection
from .worked_examples import reproduce_worked_examples


COLORS = {
    "blue": "#4C78A8",
    "orange": "#F58518",
    "green": "#2A9D6F",
    "red": "#C23B3B",
    "purple": "#8F63B8",
    "gray": "#62666A",
    "yellow": "#D6A51D",
}


def _style():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.18,
            "legend.frameon": False,
            "figure.dpi": 140,
            "savefig.dpi": 220,
        }
    )


def _finish(fig, output_dir: Path, name: str, category: str) -> list[Path]:
    category_label = category.upper()
    if len(category_label) > 16 and " " in category_label:
        first, rest = category_label.split(" ", 1)
        category_label = f"{first}\n{rest}"
    fig.text(0.015, 0.99, category_label, ha="left", va="top", fontsize=7, color=COLORS["gray"])
    paths = []
    for extension in ("png", "pdf"):
        path = output_dir / f"{name}.{extension}"
        fig.savefig(path, bbox_inches="tight")
        paths.append(path)
    plt.close(fig)
    return paths


def generate_all_figures(output_dir: str | Path) -> list[Path]:
    _style()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    fig, ax = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    labels = ["1D interval", "2D square/circle", "3D cube/sphere"]
    exponents = [0, 1 / 2, 2 / 3]
    bars = ax.bar(labels, exponents, color=[COLORS["gray"], COLORS["blue"], COLORS["orange"]], width=0.58)
    ax.bar_label(bars, labels=["0", "1/2", "2/3"], padding=4)
    ax.set_ylim(0, 0.78)
    ax.set_ylabel("Boundary-content exponent")
    ax.set_title("Dimensional ladder for geometrically similar objects")
    ax.text(0.02, 0.95, "The 3D 2/3 result does not derive\na planar wildfire law.", ha="left", va="top", color=COLORS["gray"], transform=ax.transAxes)
    generated += _finish(fig, output_dir, "01_dimensional_ladder", "analytical")

    area = np.geomspace(1, 1e6, 300)
    fig, ax = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    ax.loglog(area, 4 * area**0.5, lw=2.5, color=COLORS["red"], label=r"Smooth family: $P=4A^{1/2}$")
    ax.loglog(area, 4 * area ** (2 / 3), lw=2.5, color=COLORS["blue"], label=r"Conditional comparison: $P=4A^{2/3}$")
    ax.set(xlabel="Area (normalized)", ylabel="Perimeter (normalized)", title="Smooth similarity and a two-thirds comparison")
    ax.legend()
    generated += _finish(fig, output_dir, "02_smooth_vs_two_thirds", "analytical")

    fig, ax = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    ax.loglog(area, np.ones_like(area), color=COLORS["gray"], lw=2.5, label=r"Constant $R_P$: slope $1/2$")
    ax.loglog(area, area ** (1 / 6), color=COLORS["green"], lw=2.5, label=r"$R_P\propto A^{1/6}$: slope $2/3$")
    ax.scatter([64], [2], color=COLORS["orange"], zorder=3)
    ax.annotate("Area x64, excess perimeter x2", (64, 2), xytext=(130, 3.2), arrowprops={"arrowstyle": "->", "color": COLORS["gray"]})
    ax.set(xlabel="Area ratio $A/A_r$", ylabel="Excess perimeter ratio $R_P/R_{P,r}$", title="Excess perimeter diagnostic")
    ax.legend()
    generated += _finish(fig, output_dir, "03_excess_perimeter", "analytical")

    fig, axes = plt.subplots(2, 2, figsize=(8, 7), constrained_layout=True)
    for generation, ax in enumerate(axes.flat):
        item = right_angle_polygon(generation)
        vertices = item.vertices / item.side_length
        ax.fill(vertices[:, 0], vertices[:, 1], color=COLORS["blue"], alpha=0.22)
        ax.plot(*vertices.T, color=COLORS["blue"], lw=1.2)
        ax.set_aspect("equal")
        ax.set_title(f"j={generation}: A={item.expected_area:g}, P={item.expected_perimeter:g}, RP={item.excess_perimeter:g}")
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("Area-preserving right-angle polygon generations")
    generated += _finish(fig, output_dir, "04_right_angle_generations", "synthetic construction")

    fig, ax = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    times = np.linspace(0, 5, 200)
    for sigma, color in zip((0, 0.5, 2 / 3, 1.2), (COLORS["gray"], COLORS["red"], COLORS["blue"], COLORS["purple"]), strict=True):
        numerical = solve_ivp(lambda _t, y: 0.4 * y**sigma, (0, 5), [2], t_eval=times, rtol=1e-10, atol=1e-12)
        analytic = constant_beta_area(times, 2, 0.4, sigma)
        ax.plot(times, analytic, color=color, lw=2, label=fr"$\sigma={sigma:.3g}$ analytic")
        ax.scatter(times[::20], numerical.y[0, ::20], color=color, s=12, facecolors="none")
    ax.set(xlabel="Time", ylabel="Area", title="Analytic growth laws and numerical ODE checks")
    ax.legend(ncol=2, fontsize=8)
    generated += _finish(fig, output_dir, "05_analytic_numeric_growth", "analytical")

    fig, ax = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    theta = np.linspace(0, 4, 200)
    for sigma, color in zip((0, 0.5, 2 / 3, 1), (COLORS["gray"], COLORS["red"], COLORS["blue"], COLORS["orange"]), strict=True):
        ax.plot(theta, normalized_area(theta, sigma), lw=2.4, color=color, label=fr"$\sigma={sigma:.3g}$")
    ax.set(xlabel=r"Normalized time $\theta=G_0(t-t_0)/A_0$", ylabel=r"Normalized area $A/A_0$", title="Growth laws with a common initial area and growth rate")
    ax.legend()
    generated += _finish(fig, output_dir, "06_normalized_growth_laws", "analytical")

    results = reproduce_worked_examples()
    beta = results["example_2"]["beta_hat_ha_one_third_day"]
    worked_area = constant_beta_area(times, 100, beta, 2 / 3)
    fig, ax = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    ax.plot(times, worked_area ** (1 / 3), color=COLORS["blue"], lw=2.8)
    ax.scatter([0, 3], [100 ** (1 / 3), 2700 ** (1 / 3)], color=COLORS["orange"], zorder=3, label="Hypothetical inputs")
    ax.axvline(3, color=COLORS["gray"], ls="--", lw=1)
    ax.set(xlabel="Day", ylabel=r"Cube-root area (ha$^{1/3}$)", title="Two-thirds closure linearizes cube-root area")
    ax.legend()
    generated += _finish(fig, output_dir, "07_cube_root_linearization", "hypothetical")

    fig, axes = plt.subplots(1, 2, figsize=(9, 4.3), constrained_layout=True)
    t = np.linspace(0, 8, 300)
    beta_paths = {"constant": np.full_like(t, 1.5), "slow decline": 1.5 * np.exp(-0.04 * t), "rapid decline": 1.5 * np.exp(-0.5 * t)}
    for (label, beta_values), color in zip(beta_paths.items(), (COLORS["green"], COLORS["blue"], COLORS["red"]), strict=True):
        integrated = np.concatenate(([0], cumulative_trapezoid(beta_values, t)))
        area_path = (10 ** (1 / 3) + integrated / 3) ** 3
        beta_dot = np.gradient(beta_values, t)
        acceleration = area_acceleration(area_path, beta_values, beta_dot, 2 / 3)
        axes[0].plot(t, beta_values, color=color, lw=2.2, label=label)
        axes[1].plot(t, acceleration, color=color, lw=2.2, label=label)
    axes[0].set(xlabel="Time", ylabel=r"$\beta(t)$", title="Specified forcing")
    axes[1].axhline(0, color=COLORS["gray"], lw=1)
    axes[1].set(xlabel="Time", ylabel=r"$d^2A/dt^2$", title="Acceleration can change sign")
    axes[0].legend()
    fig.suptitle("A two-thirds geometry does not guarantee acceleration")
    generated += _finish(fig, output_dir, "08_constant_declining_beta", "synthetic")

    fig, ax = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    t = np.linspace(0, 30, 400)
    cubic = constant_beta_area(t, 1, 1, 2 / 3)
    bound = finite_speed_bound(t, 1, 0.2)
    ax.plot(t, cubic, color=COLORS["blue"], lw=2.5, label="Constant-positive-beta cubic")
    ax.plot(t, bound, color=COLORS["red"], lw=2.5, label="Finite local-speed bound")
    crossing_index = np.flatnonzero(cubic > bound)[0]
    ax.scatter(t[crossing_index], cubic[crossing_index], color=COLORS["orange"], zorder=3)
    ax.set(xlabel="Time", ylabel="Area", title="Cubic extrapolation eventually violates a fixed-speed bound")
    ax.legend()
    generated += _finish(fig, output_dir, "09_finite_speed_bound", "analytical")

    fig, ax = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    t = np.linspace(0, 10, 400)
    rate = finite_recruitment_exponential_rate(t, 2, 3, 4, 1.2)
    recruitment = np.where(t <= 4, 6.0, 0.0)
    ax.plot(t, recruitment, color=COLORS["blue"], lw=2.3, label="Mass recruitment rate")
    ax.plot(t, rate, color=COLORS["orange"], lw=2.3, label="Consumption rate")
    ax.axvline(4, color=COLORS["gray"], ls="--")
    ax.set(xlabel="Time", ylabel="Mass per time", title="Residence-time lag persists after area recruitment stops")
    ax.legend()
    generated += _finish(fig, output_dir, "10_residence_time_lag", "analytical")

    fig, ax = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    area = np.geomspace(1, 1e6, 300)
    cases = [(0, 0, "constant active fraction", COLORS["blue"]), (-1 / 6, 0, r"$f_a\propto A^{-1/6}$", COLORS["green"]), (-2 / 3, 0, r"$f_a\propto A^{-2/3}$", COLORS["red"]), (0, 1 / 6, r"$\bar v_n\propto A^{1/6}$", COLORS["purple"])]
    for fa_exp, speed_exp, label, color in cases:
        exponent = 2 / 3 + fa_exp + speed_exp
        ax.loglog(area, area**exponent, color=color, lw=2.3, label=f"{label}; growth exponent {exponent:.2f}")
    ax.set(xlabel="Area", ylabel="Area-growth rate", title="Geometry alone does not determine dynamics")
    ax.legend(fontsize=8)
    generated += _finish(fig, output_dir, "11_active_fraction_counterexamples", "analytical counterexamples")

    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), constrained_layout=True)
    r = np.geomspace(0.05, 20, 400)
    axes[0].semilogx(r, matching_efficiency(r), color=COLORS["blue"], lw=2.5)
    axes[0].axvline(1, color=COLORS["gray"], ls="--")
    axes[0].set(xlabel="Transport ratio r", ylabel=r"$\eta(r)$", title="Matching function peaks at r=1")
    dimensions = np.linspace(1, 2, 300)
    for dstar, color in ((4 / 3, COLORS["orange"]), (1.55, COLORS["green"]), (1.75, COLORS["purple"])):
        axes[1].plot(dimensions, matching_efficiency(matching_ratio(dimensions, dstar, 5)), color=color, lw=2.2, label=fr"Assumed $D_\star={dstar:.2f}$")
    axes[1].set(xlabel=r"Boundary dimension $D_h$", ylabel="Efficiency", title="The modeler places the preferred dimension")
    axes[1].legend(fontsize=8)
    fig.suptitle("Transport matching does not select a wildfire dimension")
    generated += _finish(fig, output_dir, "12_matching_counterexample", "analytical counterexample")

    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), constrained_layout=True)
    t = np.linspace(0, 5, 300)
    area = constant_beta_area(t, 100, beta, 2 / 3)
    k = results["example_2"]["k_hat_km_ha_minus_two_thirds"]
    axes[0].plot(t, area, color=COLORS["blue"], lw=2.5)
    axes[0].scatter([0, 3], [100, 2700], color=COLORS["orange"], label="Specified inputs")
    axes[0].axvline(3, color=COLORS["gray"], ls="--")
    axes[0].set(xlabel="Day", ylabel="Area (ha)", title="Conditional area trajectory")
    axes[1].plot(t, k * area ** (2 / 3), color=COLORS["green"], lw=2.5)
    axes[1].scatter([0, 3], [4, 36], color=COLORS["orange"])
    axes[1].axvline(3, color=COLORS["gray"], ls="--")
    axes[1].set(xlabel="Day", ylabel="Perimeter (km)", title="Conditional perimeter trajectory")
    axes[0].legend()
    fig.suptitle("Section S19 worked-example trajectory")
    generated += _finish(fig, output_dir, "13_worked_example_trajectory", "hypothetical")

    fig, ax = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    x_values = np.array([2, 4])
    area_values = x_values**3
    ax.scatter(x_values, area_values, s=80, color=[COLORS["blue"], COLORS["orange"]], label="Two equally likely outcomes")
    ax.scatter([3], [36], marker="D", s=70, color=COLORS["green"], label=r"$E[X^3]=36$")
    ax.scatter([3], [27], marker="x", s=90, color=COLORS["red"], label=r"$(E[X])^3=27$")
    ax.vlines(3, 27, 36, color=COLORS["gray"], ls="--")
    ax.set(xlabel=r"Future transformed area $X^*$", ylabel=r"Future area $A^*=(X^*)^3$", title="Forecasting uncertainty under a nonlinear back-transform")
    ax.legend()
    generated += _finish(fig, output_dir, "14_forecast_backtransform_uncertainty", "hypothetical")

    fig, axes = plt.subplots(1, 3, figsize=(10, 3.5), constrained_layout=True)
    x, y, z, mask = rough_surface_projection()
    axes[0].imshow(z, origin="lower", extent=(-1, 1, -1, 1), cmap="viridis")
    axes[0].set_title("Rough surface graph")
    axes[1].contour(x, y, z, levels=[0], colors=[COLORS["orange"]], linewidths=1)
    axes[1].set_title("Plane intersection trace")
    axes[2].imshow(mask, origin="lower", extent=(-1, 1, -1, 1), cmap="Greys")
    axes[2].set_title("Projected footprint boundary")
    for ax in axes:
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("Projection, intersection, and accumulated footprint are distinct objects")
    generated += _finish(fig, output_dir, "15_surface_intersection_projection", "synthetic schematic")

    return generated
