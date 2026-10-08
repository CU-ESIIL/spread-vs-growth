"""Reproducible manuscript figures and synthetic fire life-cycle checks.

The routines in this module deliberately distinguish analytical schematics from
synthetic simulations.  None of the generated panels are presented as observed
fire data.  The life-cycle forecast check tests the internal consequences of the
specified model and is not a substitute for out-of-sample validation on fires.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from scipy import ndimage as ndi
from scipy.integrate import cumulative_trapezoid, solve_ivp
from skimage import measure, morphology


COLORS = {
    "blue": "#5B8EE6",
    "cornflower": "#6495ED",
    "red": "#B52322",
    "firebrick": "#A51F1F",
    "green": "#2E8B57",
    "lime": "#38B449",
    "purple": "#7B4BA3",
    "pink": "#F4A7A7",
    "yellow": "#F2D45C",
    "ink": "#202124",
    "gray": "#6B6F73",
    "light_gray": "#ECEDEF",
}


@dataclass(frozen=True)
class LifeCycleParameters:
    """Parameters for a resource-limited, two-thirds fire metabolism model."""

    duration_hours: float = 36.0
    time_step_hours: float = 0.1
    initial_area_ha: float = 70.0
    maximum_burnable_area_ha: float = 1800.0
    initial_connectivity: float = 0.02
    connectivity_recruitment_per_hour: float = 0.60
    fragmentation_loss_per_hour: float = 0.15
    beta_scale: float = 4.0
    perimeter_coefficient: float = 0.82
    energy_per_area_gj_per_ha: float = 180.0


@dataclass(frozen=True)
class LifeCycleTrajectory:
    time: np.ndarray
    area: np.ndarray
    active_perimeter: np.ndarray
    growth_rate: np.ndarray
    forcing: np.ndarray
    beta: np.ndarray
    fuel_fraction: np.ndarray
    effective_velocity: np.ndarray
    connectivity: np.ndarray
    matching_efficiency: np.ndarray
    coupling: np.ndarray
    sigma_edge: np.ndarray
    fragmentation: np.ndarray
    patch_dimension: np.ndarray
    frp: np.ndarray
    fre: np.ndarray
    stage_indices: dict[str, int]


def simulate_fire_life_cycle(params: LifeCycleParameters = LifeCycleParameters()) -> LifeCycleTrajectory:
    """Simulate a finite-fuel fire with a two-thirds metabolic closure.

    The state variables are cumulative burned area ``A`` and coherent fuel
    connectivity ``C``.  Every plotted line follows from

    ``P_a = k C A**(2/3)``
    ``v_eff = v0 F eta``
    ``dA/dt = v_eff P_a = beta0 C F eta A**(2/3)``

    where ``F`` is remaining connected fuel and ``eta`` is the impedance-
    matching efficiency.  Connectivity follows mass-action recruitment minus
    fragmentation loss.  No time-series shape is prescribed independently.
    """

    if params.duration_hours <= 0 or params.time_step_hours <= 0 or params.initial_area_ha <= 0:
        raise ValueError("duration, time step, and initial area must be positive")
    if params.maximum_burnable_area_ha <= params.initial_area_ha:
        raise ValueError("maximum burnable area must exceed initial area")
    if not 0 < params.initial_connectivity < 1:
        raise ValueError("initial connectivity must be in (0, 1)")
    if min(
        params.connectivity_recruitment_per_hour,
        params.fragmentation_loss_per_hour,
        params.beta_scale,
        params.perimeter_coefficient,
        params.energy_per_area_gj_per_ha,
    ) <= 0:
        raise ValueError("rate, geometry, and energy parameters must be positive")

    time = np.arange(0.0, params.duration_hours + params.time_step_hours / 2, params.time_step_hours)
    available_area = params.maximum_burnable_area_ha - params.initial_area_ha
    epsilon = 1e-8

    def state_terms(area_value: float, connectivity_value: float) -> tuple[float, float, float, float]:
        fuel = float(np.clip((params.maximum_burnable_area_ha - area_value) / available_area, 0.0, 1.0))
        connectivity_value = float(np.clip(connectivity_value, 0.0, 1.0))
        impedance_ratio = (connectivity_value + epsilon) / (fuel + epsilon)
        efficiency = 4.0 * impedance_ratio / (1.0 + impedance_ratio) ** 2
        beta_value = params.beta_scale * connectivity_value * fuel * efficiency
        return fuel, efficiency, beta_value, connectivity_value

    def rhs(_time: float, state: np.ndarray) -> tuple[float, float]:
        area_value, connectivity_value = state
        fuel, efficiency, beta_value, connectivity_value = state_terms(area_value, connectivity_value)
        metabolic_rate = beta_value * max(area_value, epsilon) ** (2.0 / 3.0)
        connectivity_rate = (
            params.connectivity_recruitment_per_hour * connectivity_value * (1.0 - connectivity_value) * fuel
            - params.fragmentation_loss_per_hour * connectivity_value
        )
        return metabolic_rate, connectivity_rate

    solution = solve_ivp(
        rhs,
        (float(time[0]), float(time[-1])),
        (params.initial_area_ha, params.initial_connectivity),
        t_eval=time,
        rtol=1e-10,
        atol=1e-12,
    )
    if not solution.success:
        raise RuntimeError(f"life-cycle integration failed: {solution.message}")
    area = solution.y[0]
    connectivity = np.clip(solution.y[1], 0.0, 1.0)
    fuel_fraction = np.clip((params.maximum_burnable_area_ha - area) / available_area, 0.0, 1.0)
    impedance_ratio = (connectivity + epsilon) / (fuel_fraction + epsilon)
    matching_efficiency = 4.0 * impedance_ratio / (1.0 + impedance_ratio) ** 2
    coupling = np.clip(2.0 * matching_efficiency * np.sqrt(connectivity * fuel_fraction), 0.0, 1.0)
    beta = params.beta_scale * connectivity * fuel_fraction * matching_efficiency
    forcing = beta / params.beta_scale
    growth_rate = beta * area ** (2.0 / 3.0)

    active_perimeter = params.perimeter_coefficient * connectivity * area ** (2.0 / 3.0)
    effective_velocity = (params.beta_scale / params.perimeter_coefficient) * fuel_fraction * matching_efficiency
    fragmentation = 1.0 - connectivity
    sigma_edge = 0.5 + coupling / 6.0
    patch_dimension = 1.0 + coupling / 3.0
    frp = params.energy_per_area_gj_per_ha * growth_rate / 3.6
    fre = cumulative_trapezoid(frp, time, initial=0.0)

    above = np.flatnonzero(connectivity >= 0.5)
    coupling_index = int(above[0]) if len(above) else 0
    peak_index = int(np.argmax(growth_rate))
    acceleration = np.gradient(growth_rate, time)
    acceleration_window = np.arange(coupling_index, max(coupling_index + 1, peak_index + 1))
    accelerating_index = int(acceleration_window[np.argmax(acceleration[acceleration_window])])
    if accelerating_index <= coupling_index:
        accelerating_index = coupling_index + max(1, (peak_index - coupling_index) // 2)
    after_peak = np.arange(peak_index + 1, len(time))
    collapsed = after_peak[
        (connectivity[after_peak] <= 0.22)
        | (growth_rate[after_peak] <= 0.08 * growth_rate[peak_index])
    ]
    fragment_index = int(collapsed[0]) if len(collapsed) else len(time) - 1
    stage_indices = {
        "Coupling": coupling_index,
        "Accelerating": min(accelerating_index, peak_index - 1),
        "Peak / endgame": peak_index,
        "Fragment / die": max(fragment_index, peak_index + 1),
    }

    return LifeCycleTrajectory(
        time=time,
        area=area,
        active_perimeter=active_perimeter,
        growth_rate=growth_rate,
        forcing=forcing,
        beta=beta,
        fuel_fraction=fuel_fraction,
        effective_velocity=effective_velocity,
        connectivity=connectivity,
        matching_efficiency=matching_efficiency,
        coupling=coupling,
        sigma_edge=sigma_edge,
        fragmentation=fragmentation,
        patch_dimension=patch_dimension,
        frp=frp,
        fre=fre,
        stage_indices=stage_indices,
    )


def transformed_area_forecast(
    history_time: np.ndarray,
    history_area: np.ndarray,
    target_time: float,
    sigma: float,
    window_hours: float = 6.0,
) -> float:
    """Forecast area by linearly extrapolating ``A**(1-sigma)``.

    Only arrays supplied as history are used, which makes future-leakage tests
    straightforward.  ``sigma=0`` is ordinary linear-area extrapolation.
    """

    history_time = np.asarray(history_time, dtype=float)
    history_area = np.asarray(history_area, dtype=float)
    if history_time.shape != history_area.shape or history_time.size < 3:
        raise ValueError("history arrays must match and contain at least three observations")
    if np.any(history_area <= 0) or not 0 <= sigma < 1:
        raise ValueError("area must be positive and sigma must be in [0, 1)")
    if target_time <= history_time[-1]:
        raise ValueError("target_time must be after the final history observation")

    keep = history_time >= history_time[-1] - window_hours
    t = history_time[keep] - history_time[keep][-1]
    power = 1.0 - sigma
    transformed = history_area[keep] ** power
    slope, intercept = np.polyfit(t, transformed, 1)
    future_transformed = max(intercept + slope * (target_time - history_time[-1]), np.finfo(float).eps)
    return float(future_transformed ** (1.0 / power))


def _jittered_parameters(rng: np.random.Generator) -> LifeCycleParameters:
    return LifeCycleParameters(
        initial_area_ha=float(rng.uniform(45.0, 110.0)),
        maximum_burnable_area_ha=float(rng.uniform(1450.0, 2300.0)),
        initial_connectivity=float(rng.uniform(0.012, 0.04)),
        connectivity_recruitment_per_hour=float(rng.uniform(0.48, 0.76)),
        fragmentation_loss_per_hour=float(rng.uniform(0.11, 0.20)),
        beta_scale=float(rng.uniform(3.2, 5.0)),
        perimeter_coefficient=float(rng.uniform(0.68, 0.98)),
        energy_per_area_gj_per_ha=float(rng.uniform(150.0, 220.0)),
    )


def run_life_cycle_validation(n_runs: int = 300, seed: int = 20260927) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Run synthetic robustness and past-only forecast checks."""

    if n_runs < 10:
        raise ValueError("n_runs must be at least 10")
    rng = np.random.default_rng(seed)
    records: list[dict[str, object]] = []
    stage_order_successes = 0
    monotonic_successes = 0

    for run in range(n_runs):
        params = _jittered_parameters(rng)
        trajectory = simulate_fire_life_cycle(params)
        stage_values = list(trajectory.stage_indices.values())
        stage_order_successes += int(stage_values == sorted(stage_values) and len(set(stage_values)) == 4)
        monotonic_successes += int(np.all(np.diff(trajectory.area) >= -1e-9))

        noisy_area = trajectory.area * np.exp(rng.normal(0.0, 0.012, len(trajectory.area)))
        noisy_area = np.maximum.accumulate(noisy_area)
        peak = trajectory.stage_indices["Peak / endgame"]
        fragment = trajectory.stage_indices["Fragment / die"]
        origins = {
            "accelerating": max(8, int(0.72 * peak)),
            "peak": peak,
            "declining": min(len(trajectory.time) - 42, peak + max(8, (fragment - peak) // 2)),
        }

        for phase, origin in origins.items():
            target = min(len(trajectory.time) - 1, origin + int(round(4.0 / params.time_step_hours)))
            history_time = trajectory.time[: origin + 1]
            history_area = noisy_area[: origin + 1]
            observed = float(trajectory.area[target])
            forecasts = {
                "no growth": float(history_area[-1]),
                "linear area": transformed_area_forecast(history_time, history_area, trajectory.time[target], 0.0),
                "square-root area": transformed_area_forecast(history_time, history_area, trajectory.time[target], 0.5),
                "cube-root area": transformed_area_forecast(history_time, history_area, trajectory.time[target], 2.0 / 3.0),
            }
            for model, prediction in forecasts.items():
                error = prediction - observed
                records.append(
                    {
                        "run": run,
                        "phase": phase,
                        "model": model,
                        "origin_hour": float(trajectory.time[origin]),
                        "target_hour": float(trajectory.time[target]),
                        "observed_area_ha": observed,
                        "predicted_area_ha": prediction,
                        "error_ha": error,
                        "absolute_percentage_error": abs(error) / observed * 100.0,
                    }
                )

    grouped: list[dict[str, object]] = []
    for phase in ("accelerating", "peak", "declining"):
        for model in ("no growth", "linear area", "square-root area", "cube-root area"):
            subset = [row for row in records if row["phase"] == phase and row["model"] == model]
            errors = np.array([float(row["error_ha"]) for row in subset])
            ape = np.array([float(row["absolute_percentage_error"]) for row in subset])
            grouped.append(
                {
                    "phase": phase,
                    "model": model,
                    "n": len(subset),
                    "median_absolute_percentage_error": float(np.median(ape)),
                    "mean_bias_ha": float(np.mean(errors)),
                    "rmse_ha": float(np.sqrt(np.mean(errors**2))),
                }
            )

    summary = {
        "scope": "synthetic internal validation; not empirical wildfire validation",
        "seed": seed,
        "n_runs": n_runs,
        "forecast_horizon_hours": 4.0,
        "monotonic_area_fraction": monotonic_successes / n_runs,
        "ordered_stage_fraction": stage_order_successes / n_runs,
        "metrics": grouped,
    }
    return records, summary


def _style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "axes.linewidth": 0.9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#D9DADD",
            "grid.alpha": 0.65,
            "grid.linewidth": 0.7,
            "legend.frameon": False,
            "savefig.facecolor": "white",
        }
    )


def _save_figure(fig: plt.Figure, output_dir: Path, stem: str, dpi: int) -> list[Path]:
    paths: list[Path] = []
    for extension in ("png", "pdf", "svg"):
        path = output_dir / f"{stem}.{extension}"
        kwargs = {"dpi": dpi} if extension == "png" else {}
        fig.savefig(path, bbox_inches="tight", facecolor="white", **kwargs)
        paths.append(path)
    plt.close(fig)
    return paths


def _panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(-0.08, 1.04, label, transform=ax.transAxes, fontsize=14, fontweight="bold", va="bottom")


def make_figure_1(output_dir: Path, dpi: int) -> list[Path]:
    """Analytical perimeter-area and coupling-efficiency schematic."""

    fig, axes = plt.subplots(1, 2, figsize=(16, 7.4), gridspec_kw={"width_ratios": [1.08, 1.0]}, constrained_layout=True)
    ax = axes[0]
    area = np.geomspace(10.0, 1e7, 320)
    log_area = np.log10(area)
    efficiencies = np.linspace(0.08, 1.0, 25)
    cmap = mpl.colormaps["viridis"]
    norm = Normalize(0.0, 1.0)
    for efficiency in efficiencies:
        spread = (1.0 - efficiency) * (0.18 + 0.065 * (log_area - 4.0) ** 2)
        for sign in (-1.0, 1.0):
            log_perimeter = -0.72 + (2.0 / 3.0) * log_area + sign * spread
            ax.plot(area, 10**log_perimeter, color=cmap(norm(efficiency)), lw=1.5, alpha=0.88)
    center = 10 ** (-0.72) * area ** (2.0 / 3.0)
    ax.plot(area, center, color=COLORS["yellow"], lw=4.0, label=r"matched ridge: $P\propto A^{2/3}$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"Fire area $A$ (arbitrary units)")
    ax.set_ylabel(r"Perimeter $P$ (arbitrary units)")
    ax.set_title("Perimeter-area scaling envelope")
    ax.legend(loc="lower right")
    _panel_label(ax, "a")

    ax = axes[1]
    delta = np.linspace(-0.34, 0.44, 500)
    sensitivity = 8.0
    ratio = np.exp(sensitivity * delta)
    efficiency = 4.0 * ratio / (1.0 + ratio) ** 2
    points = np.column_stack([delta, efficiency]).reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    collection = LineCollection(segments, cmap=cmap, norm=norm, linewidth=5.2)
    collection.set_array((efficiency[:-1] + efficiency[1:]) / 2.0)
    ax.add_collection(collection)
    left = delta <= 0
    right = delta >= 0
    ax.plot(delta[left], np.exp(sensitivity * delta[left]), ls="--", lw=2.3, color=COLORS["green"], label="under-folded limit")
    ax.plot(delta[right], np.exp(-sensitivity * delta[right]), ls="--", lw=2.3, color=COLORS["purple"], label="over-folded limit")
    ax.axvspan(-0.045, 0.045, color=COLORS["yellow"], alpha=0.19, lw=0)
    ax.axvline(0.0, color=COLORS["ink"], lw=1.2)
    ax.set_xlim(delta.min(), delta.max())
    ax.set_ylim(0.0, 1.08)
    ax.set_xlabel(r"Coupling divergence $\Delta=D_h-4/3$")
    ax.set_ylabel(r"Coupling efficiency $\eta$")
    ax.set_title("Coupling efficiency vs. interface geometry")
    ax.legend(loc="lower left")
    secondary = ax.secondary_xaxis("top", functions=(lambda value: value + 7.0 / 3.0, lambda value: value - 7.0 / 3.0))
    secondary.set_xlabel(r"Combustion-interface dimension $D=7/3+\Delta$")
    colorbar = fig.colorbar(collection, ax=ax, fraction=0.045, pad=0.03)
    colorbar.set_label(r"Efficiency $\eta$")
    _panel_label(ax, "b")

    fig.suptitle("Coupling efficiency links interface geometry to perimeter-area scaling", fontsize=17, y=1.035)
    fig.text(0.5, -0.02, "Analytical schematic: curves are model relationships, not observed fire records.", ha="center", color=COLORS["gray"], fontsize=9)
    return _save_figure(fig, output_dir, "figure1_coupling_efficiency", dpi)


def _rough_footprint(seed: int = 19, size: int = 260) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    axis = np.linspace(-1.25, 1.25, size)
    x, y = np.meshgrid(axis, axis)
    theta = np.arctan2(y, x)
    radius = np.sqrt((x / 1.08) ** 2 + (y / 0.93) ** 2)
    angular = 0.08 * np.sin(5 * theta + 0.4) + 0.055 * np.sin(11 * theta - 0.9) + 0.028 * np.sin(23 * theta + 1.4)
    noise = ndi.gaussian_filter(rng.normal(size=(size, size)), sigma=5.2)
    noise /= max(float(np.std(noise)), np.finfo(float).eps)
    mask = radius <= 0.95 + angular + 0.045 * noise
    distance = ndi.distance_transform_edt(mask)
    rough = ndi.gaussian_filter(rng.normal(size=(size, size)), sigma=2.0)
    rough += 0.55 * ndi.gaussian_filter(rng.normal(size=(size, size)), sigma=6.0)
    rough /= max(float(np.std(rough[mask])), np.finfo(float).eps)
    height = np.where(mask, 0.20 + 0.10 * np.sqrt(distance) + 0.13 * rough, np.nan)
    height = np.where(mask, np.clip(height, 0.03, None), np.nan)
    return x, y, height, mask


def _remove_small_components(mask: np.ndarray, minimum_size: int) -> np.ndarray:
    """Remove connected components without relying on version-specific APIs."""

    labels, count = ndi.label(mask)
    if count == 0:
        return mask.astype(bool)
    sizes = np.bincount(labels.ravel())
    keep = sizes >= minimum_size
    keep[0] = False
    return keep[labels]


def make_figure_2(output_dir: Path, dpi: int) -> list[Path]:
    """Conceptual 3-D combustion-interface to 2-D footprint projection."""

    x, y, height, mask = _rough_footprint()
    fig = plt.figure(figsize=(16, 8.4), constrained_layout=True)
    grid = fig.add_gridspec(1, 2, width_ratios=[1.35, 0.65])
    ax = fig.add_subplot(grid[0, 0], projection="3d")
    stride = 3
    face = mpl.colormaps["Reds"](Normalize(np.nanmin(height), np.nanmax(height))(np.nan_to_num(height, nan=np.nanmin(height))))
    face[..., -1] = np.where(mask, 0.92, 0.0)
    ax.plot_surface(
        x[::stride, ::stride],
        y[::stride, ::stride],
        height[::stride, ::stride],
        facecolors=face[::stride, ::stride],
        rstride=1,
        cstride=1,
        linewidth=0.0,
        antialiased=True,
        shade=True,
    )
    contours = measure.find_contours(mask.astype(float), 0.5)
    for contour in contours:
        row, col = contour[:, 0], contour[:, 1]
        xx = np.interp(col, np.arange(x.shape[1]), x[0])
        yy = np.interp(row, np.arange(y.shape[0]), y[:, 0])
        ztop = ndi.map_coordinates(np.nan_to_num(height, nan=0.0), [row, col], order=1)
        ax.plot(xx, yy, np.zeros_like(xx), color=COLORS["cornflower"], lw=3.2)
        ax.plot(xx, yy, ztop, color=COLORS["firebrick"], lw=1.1, alpha=0.8)
        for index in range(0, len(xx), max(1, len(xx) // 130)):
            ax.plot([xx[index], xx[index]], [yy[index], yy[index]], [0.0, ztop[index]], color=COLORS["cornflower"], lw=0.55, alpha=0.45)
    ax.contourf(x, y, mask.astype(float), zdir="z", offset=0.0, levels=[0.5, 1.5], colors=[COLORS["cornflower"]], alpha=0.13)
    ax.view_init(elev=27, azim=-58)
    ax.set_box_aspect((1.15, 1.0, 0.48))
    ax.set_axis_off()

    notes = fig.add_subplot(grid[0, 1])
    notes.axis("off")
    notes.text(0.04, 0.73, "Combustion manifold", color=COLORS["firebrick"], fontsize=23, fontweight="bold")
    notes.text(0.04, 0.66, r"rough surface, $D\approx7/3$", color=COLORS["firebrick"], fontsize=16)
    notes.annotate("", xy=(0.02, 0.62), xytext=(-0.44, 0.55), xycoords="axes fraction", arrowprops={"arrowstyle": "-", "lw": 4, "color": COLORS["firebrick"]})
    notes.text(0.04, 0.29, "Footprint perimeter", color=COLORS["cornflower"], fontsize=23, fontweight="bold")
    notes.text(0.04, 0.22, r"external hull, $D_h\approx4/3$", color=COLORS["cornflower"], fontsize=16)
    notes.annotate("", xy=(0.02, 0.34), xytext=(-0.43, 0.18), xycoords="axes fraction", arrowprops={"arrowstyle": "-", "lw": 4, "color": COLORS["cornflower"]})
    notes.text(0.04, 0.05, "Conceptual projection, not a dimension estimate", color=COLORS["gray"], fontsize=10)
    fig.suptitle("Emergence of footprint geometry from a wrinkled combustion interface", fontsize=18)
    return _save_figure(fig, output_dir, "figure2_interface_projection", dpi)


def _multiscale_masks(seed: int = 73, size: int = 156) -> tuple[np.ndarray, list[np.ndarray]]:
    rng = np.random.default_rng(seed)
    axis = np.linspace(-1.0, 1.0, size)
    x, y = np.meshgrid(axis, axis)
    radial = np.sqrt((x / 0.98) ** 2 + (y / 0.87) ** 2)
    noise = np.zeros((size, size), dtype=float)
    for sigma, weight in ((0.7, 0.35), (1.3, 0.35), (2.5, 0.50), (5.0, 0.65), (10.0, 0.80)):
        field = ndi.gaussian_filter(rng.normal(size=(size, size)), sigma=sigma)
        noise += weight * field / max(float(np.std(field)), np.finfo(float).eps)
    noise /= max(float(np.std(noise)), np.finfo(float).eps)
    arrival = radial + 0.18 * noise

    disconnected_field = ndi.gaussian_filter(np.random.default_rng(seed + 1).normal(size=(size, size)), sigma=1.2)
    disconnected = (disconnected_field > np.quantile(disconnected_field, 0.55)) & (radial < 0.70)
    masks = [disconnected]
    masks.extend(arrival <= threshold for threshold in (0.53, 0.70, 0.88, 1.05))
    return arrival, masks


def _boundary_dimension(mask: np.ndarray) -> float:
    boundary = np.logical_xor(mask, morphology.erosion(mask))
    sizes = np.array([2, 3, 4, 6, 8, 12, 16, 24], dtype=int)
    counts = []
    valid_sizes = []
    for box in sizes:
        rows = int(math.ceil(boundary.shape[0] / box))
        cols = int(math.ceil(boundary.shape[1] / box))
        padded = np.pad(boundary, ((0, rows * box - boundary.shape[0]), (0, cols * box - boundary.shape[1])))
        occupied = padded.reshape(rows, box, cols, box).any(axis=(1, 3))
        count = int(np.count_nonzero(occupied))
        if count > 1:
            counts.append(count)
            valid_sizes.append(box)
    return float(np.polyfit(np.log(1.0 / np.asarray(valid_sizes)), np.log(np.asarray(counts)), 1)[0])


def _network(seed: int, n_points: int = 230) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    points = rng.uniform(-1.0, 1.0, size=(n_points, 2))
    triangulation = mpl.tri.Triangulation(points[:, 0], points[:, 1])
    edges = set()
    for triangle in triangulation.triangles:
        for start, end in ((triangle[0], triangle[1]), (triangle[1], triangle[2]), (triangle[2], triangle[0])):
            edges.add(tuple(sorted((int(start), int(end)))))
    return points, np.asarray(sorted(edges), dtype=int)


def _mask_lookup(mask: np.ndarray, points: np.ndarray) -> np.ndarray:
    col = np.clip(((points[:, 0] + 1.0) * 0.5 * (mask.shape[1] - 1)).astype(int), 0, mask.shape[1] - 1)
    row = np.clip(((points[:, 1] + 1.0) * 0.5 * (mask.shape[0] - 1)).astype(int), 0, mask.shape[0] - 1)
    return mask[row, col]


def make_figure_3(output_dir: Path, dpi: int) -> list[Path]:
    """Synthetic multiscale coalescence and measured geometric summaries."""

    _, masks = _multiscale_masks()
    points, edges = _network(91)
    scale_labels = ["1 cm", "1 m", "10 m", "1 km", "10 km"]
    areas = np.array([np.count_nonzero(mask) for mask in masks], dtype=float)
    perimeters = np.array([measure.perimeter(mask, neighborhood=8) for mask in masks], dtype=float)
    dimensions = np.array([_boundary_dimension(mask) for mask in masks])
    scale_coordinate = np.arange(len(masks))

    fig = plt.figure(figsize=(18, 9.8), constrained_layout=True)
    grid = fig.add_gridspec(3, 6, width_ratios=[1, 1, 1, 1, 1, 1.08], wspace=0.04, hspace=0.08)
    row_labels = ["Spread network", "Measured boundary", "Burned area"]
    extent = (-1, 1, -1, 1)
    for column, (label, mask) in enumerate(zip(scale_labels, masks, strict=True)):
        inside = _mask_lookup(mask, points)
        for row in range(3):
            ax = fig.add_subplot(grid[row, column])
            ax.set_xlim(-1.02, 1.02)
            ax.set_ylim(-1.02, 1.02)
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            if row == 0:
                for start, end in edges:
                    color = COLORS["ink"] if inside[start] and inside[end] else COLORS["lime"]
                    alpha = 0.42 if color == COLORS["ink"] else 0.30
                    ax.plot(points[[start, end], 0], points[[start, end], 1], color=color, lw=0.42, alpha=alpha)
                ax.set_title(label, pad=5)
            elif row == 1:
                for start, end in edges[::2]:
                    ax.plot(points[[start, end], 0], points[[start, end], 1], color=COLORS["cornflower"], lw=0.38, alpha=0.42)
                ax.contour(mask.astype(float), levels=[0.5], extent=extent, colors=[COLORS["red"]], linewidths=1.7)
            else:
                ax.contourf(mask.astype(float), levels=[0.5, 1.5], extent=extent, colors=[COLORS["pink"]], alpha=0.64)
                ax.contour(mask.astype(float), levels=[0.5], extent=extent, colors=[COLORS["pink"]], linewidths=0.9)
            if column == 0:
                ax.text(-0.18, 0.5, row_labels[row], rotation=90, transform=ax.transAxes, va="center", ha="center", fontsize=12)

    ax_dimension = fig.add_subplot(grid[0, 5])
    ax_dimension.plot(scale_coordinate, dimensions, color=COLORS["ink"], marker="o", lw=2)
    ax_dimension.axhline(4.0 / 3.0, color=COLORS["green"], ls="--", lw=2, label="4/3 reference")
    ax_dimension.set_ylabel("Box-counted boundary dimension")
    ax_dimension.set_ylim(0.9, max(1.55, float(np.max(dimensions) + 0.12)))
    ax_dimension.legend(fontsize=8)

    ax_perimeter = fig.add_subplot(grid[1, 5], sharex=ax_dimension)
    ax_perimeter.plot(scale_coordinate, perimeters, color=COLORS["red"], marker="o", lw=2.2, label="measured")
    p_reference = perimeters[1] * (areas / areas[1]) ** (2.0 / 3.0)
    ax_perimeter.plot(scale_coordinate, p_reference, color=COLORS["red"], ls="--", lw=1.8, label=r"coalesced $A^{2/3}$ reference")
    ax_perimeter.set_ylabel("Perimeter (pixels)")
    ax_perimeter.legend(fontsize=8)

    ax_area = fig.add_subplot(grid[2, 5], sharex=ax_dimension)
    ax_area.plot(scale_coordinate, areas, color=COLORS["blue"], marker="o", lw=2.2, label="measured")
    ax_area.set_ylabel(r"Area (pixels$^2$)")
    ax_area.set_xticks(scale_coordinate, scale_labels, rotation=25)
    ax_area.set_xlabel("Nominal observation scale")
    ax_area.legend(fontsize=8)
    plt.setp(ax_dimension.get_xticklabels(), visible=False)
    plt.setp(ax_perimeter.get_xticklabels(), visible=False)
    fig.suptitle("Synthetic emergence of connected footprint geometry across scales", fontsize=18)
    fig.text(0.5, -0.015, "All rows derive from deterministic random fields; metrics are measured from the rendered masks.", ha="center", color=COLORS["gray"], fontsize=9)
    return _save_figure(fig, output_dir, "figure3_multiscale_emergence", dpi)


def _life_cycle_masks(seed: int = 117, size: int = 196) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    axis = np.linspace(-1.1, 1.1, size)
    x, y = np.meshgrid(axis, axis)
    radial = np.sqrt((x / 1.02) ** 2 + (y / 0.88) ** 2)
    noise = ndi.gaussian_filter(rng.normal(size=(size, size)), sigma=4.5)
    noise += 0.42 * ndi.gaussian_filter(rng.normal(size=(size, size)), sigma=10.0)
    noise /= max(float(np.std(noise)), np.finfo(float).eps)
    arrival = radial + 0.19 * noise
    masks = [arrival <= threshold for threshold in (0.34, 0.60, 0.90, 1.02)]
    masks[0] = _remove_small_components(masks[0], minimum_size=15)
    masks[1] = morphology.closing(masks[1], morphology.disk(2))
    masks[2] = morphology.closing(masks[2], morphology.disk(3))
    fragment_field = ndi.gaussian_filter(rng.normal(size=(size, size)), sigma=6.5)
    holes = fragment_field > np.quantile(fragment_field[masks[3]], 0.55)
    core = arrival <= 0.40
    masks[3] = _remove_small_components(masks[3] & (~holes | core), minimum_size=24)
    return masks


def _stage_spans(trajectory: LifeCycleTrajectory) -> list[tuple[float, float, str]]:
    indices = list(trajectory.stage_indices.values())
    boundaries = [0.0]
    for left, right in zip(indices[:-1], indices[1:], strict=True):
        boundaries.append(float((trajectory.time[left] + trajectory.time[right]) / 2.0))
    boundaries.append(float(trajectory.time[-1]))
    return [(boundaries[i], boundaries[i + 1], name) for i, name in enumerate(trajectory.stage_indices)]


def make_figure_4(output_dir: Path, dpi: int) -> tuple[list[Path], LifeCycleTrajectory]:
    """Fire life-cycle figure with spatial stages and measurable trajectories."""

    trajectory = simulate_fire_life_cycle()
    masks = _life_cycle_masks()
    fig = plt.figure(figsize=(16, 14.5), constrained_layout=True)
    grid = fig.add_gridspec(4, 4, height_ratios=[1.0, 1.18, 1.0, 1.0], hspace=0.17, wspace=0.11)
    stage_colors = ["#EEF2F7", "#FFF4D8", "#FCE5E4", "#EEE9F3"]
    for column, ((stage, index), mask, background) in enumerate(zip(trajectory.stage_indices.items(), masks, stage_colors, strict=True)):
        ax = fig.add_subplot(grid[0, column])
        ax.set_facecolor(background)
        ax.contourf(mask.astype(float), levels=[0.5, 1.5], colors=[COLORS["firebrick"]], alpha=0.28)
        ax.contour(mask.astype(float), levels=[0.5], colors=[COLORS["red"]], linewidths=2.4)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_title(f"{column + 1}. {stage}", fontweight="bold", pad=4)
        ax.text(0.5, -0.05, f"t = {trajectory.time[index]:.1f} h", transform=ax.transAxes, ha="center", color=COLORS["gray"], fontsize=9)

    time = trajectory.time
    spans = _stage_spans(trajectory)

    ax_area = fig.add_subplot(grid[1, :])
    for start, end, _ in spans:
        ax_area.axvspan(start, end, color=stage_colors[len(ax_area.patches) % len(stage_colors)], alpha=0.45, lw=0)
    area_line = ax_area.plot(time, trajectory.area, color=COLORS["blue"], lw=3.2, label=r"cumulative area $A(t)$")[0]
    ax_area.set_ylabel("Cumulative area (ha)")
    ax_area.set_xlim(time.min(), time.max())
    ax_perimeter = ax_area.twinx()
    perimeter_line = ax_perimeter.plot(time, trajectory.active_perimeter, color=COLORS["red"], lw=2.6, ls="--", label=r"active perimeter $P_a(t)$")[0]
    ax_perimeter.set_ylabel("Active perimeter (relative units)")
    ax_area.legend([area_line, perimeter_line], [area_line.get_label(), perimeter_line.get_label()], loc="upper left", ncol=2)
    ax_area.set_title(r"Derived geometry: $P_a=kCA^{2/3}$ and cumulative area cannot decrease", loc="left")

    ax_rate = fig.add_subplot(grid[2, :], sharex=ax_area)
    for start, end, _ in spans:
        ax_rate.axvspan(start, end, color=stage_colors[len(ax_rate.patches) % len(stage_colors)], alpha=0.45, lw=0)
    rate_line = ax_rate.plot(time, trajectory.growth_rate, color=COLORS["blue"], lw=3.0, label=r"metabolic rate $dA/dt$")[0]
    ax_rate.set_ylabel(r"Growth rate (ha h$^{-1}$)")
    forcing_axis = ax_rate.twinx()
    forcing_line = forcing_axis.plot(time, trajectory.forcing, color=COLORS["yellow"], lw=2.4, label=r"metabolic prefactor $\beta/\beta_0=CF\eta$")[0]
    forcing_axis.set_ylim(0, max(0.42, float(np.max(trajectory.forcing) * 1.12)))
    forcing_axis.set_ylabel(r"Normalized prefactor $\beta/\beta_0$")
    ax_rate.legend([rate_line, forcing_line], [rate_line.get_label(), forcing_line.get_label()], loc="upper left", ncol=2)
    peak_index = trajectory.stage_indices["Peak / endgame"]
    ax_rate.scatter([time[peak_index]], [trajectory.growth_rate[peak_index]], s=70, color=COLORS["red"], zorder=4)
    ax_rate.annotate("peak growth", (time[peak_index], trajectory.growth_rate[peak_index]), xytext=(15, 18), textcoords="offset points", arrowprops={"arrowstyle": "->", "color": COLORS["gray"]})

    ax_state = fig.add_subplot(grid[3, :], sharex=ax_area)
    for start, end, _ in spans:
        ax_state.axvspan(start, end, color=stage_colors[len(ax_state.patches) % len(stage_colors)], alpha=0.45, lw=0)
    connectivity_line = ax_state.plot(time, trajectory.connectivity, color=COLORS["green"], lw=2.8, label=r"connectivity $C$")[0]
    fuel_line = ax_state.plot(time, trajectory.fuel_fraction, color=COLORS["gray"], lw=2.2, ls="--", label=r"connected fuel $F$")[0]
    dimension_line = ax_state.plot(time, trajectory.patch_dimension - 1.0, color=COLORS["green"], lw=2.0, ls="-.", label=r"patch structure $D_{set}-1$")[0]
    ax_state.set_ylabel("Connectivity / structure")
    ax_state.set_ylim(0, 1.08)
    sigma_axis = ax_state.twinx()
    sigma_line = sigma_axis.plot(time, trajectory.sigma_edge, color=COLORS["purple"], lw=3.0, label=r"edge coupling $\sigma_{edge}$")[0]
    sigma_axis.axhline(0.5, color=COLORS["purple"], lw=1.6, ls="--", alpha=0.85)
    sigma_axis.set_ylim(0.44, 0.71)
    sigma_axis.set_ylabel(r"Edge coupling $\sigma_{edge}$")
    ax_state.set_xlabel("Time since ignition (h)")
    ax_state.legend(
        [connectivity_line, fuel_line, dimension_line, sigma_line],
        [connectivity_line.get_label(), fuel_line.get_label(), dimension_line.get_label(), sigma_line.get_label()],
        loc="upper right",
        ncol=4,
        fontsize=9,
    )
    for stage, index in trajectory.stage_indices.items():
        ax_state.axvline(time[index], color=COLORS["gray"], lw=0.8, alpha=0.55)

    fig.suptitle("The life and death of a fire from a two-thirds metabolic closure", fontsize=19)
    fig.text(
        0.5,
        -0.008,
        r"All lines derive from $A$ and $C$: $dA/dt=v_{eff}P_a=\beta_0CF\eta A^{2/3}$. Death denotes collapse of active throughput, not loss of cumulative burned area.",
        ha="center",
        color=COLORS["gray"],
        fontsize=9,
    )
    return _save_figure(fig, output_dir, "figure4_fire_life_cycle", dpi), trajectory


def make_validation_figure(output_dir: Path, dpi: int, records: list[dict[str, object]], summary: dict[str, object]) -> list[Path]:
    """Plot robustness and forecast errors for the synthetic ensemble."""

    models = ["no growth", "linear area", "square-root area", "cube-root area"]
    phases = ["accelerating", "peak", "declining"]
    model_colors = [COLORS["gray"], COLORS["red"], COLORS["green"], COLORS["blue"]]
    metrics = summary["metrics"]
    metric_lookup = {(row["phase"], row["model"]): row for row in metrics}

    fig, axes = plt.subplots(1, 2, figsize=(16, 6.8), constrained_layout=True)
    ax = axes[0]
    x = np.arange(len(phases), dtype=float)
    width = 0.19
    for index, (model, color) in enumerate(zip(models, model_colors, strict=True)):
        values = [float(metric_lookup[(phase, model)]["median_absolute_percentage_error"]) for phase in phases]
        ax.bar(x + (index - 1.5) * width, values, width=width, color=color, alpha=0.85, label=model)
    ax.set_xticks(x, [value.capitalize() for value in phases])
    ax.set_ylabel("Median absolute percentage error (%)")
    ax.set_xlabel("Forecast origin phase")
    ax.set_title("Four-hour area forecasts from past observations only")
    ax.legend(ncol=2, fontsize=9)
    _panel_label(ax, "a")

    ax = axes[1]
    rng = np.random.default_rng(41)
    for model, color in zip(models, model_colors, strict=True):
        subset = [row for row in records if row["model"] == model]
        selected = rng.choice(len(subset), size=min(130, len(subset)), replace=False)
        observed = np.array([float(subset[i]["observed_area_ha"]) for i in selected])
        predicted = np.array([float(subset[i]["predicted_area_ha"]) for i in selected])
        ax.scatter(observed, predicted, s=18, alpha=0.28, color=color, label=model, edgecolors="none")
    all_observed = np.array([float(row["observed_area_ha"]) for row in records])
    limits = [float(np.min(all_observed) * 0.88), float(np.max(all_observed) * 1.08)]
    ax.plot(limits, limits, color=COLORS["ink"], ls="--", lw=1.8, label="1:1")
    ax.set_xlim(limits)
    ax.set_ylim(limits)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Observed synthetic area (ha)")
    ax.set_ylabel("Predicted synthetic area (ha)")
    ax.set_title("Prediction agreement across parameter perturbations")
    ax.legend(fontsize=9)
    _panel_label(ax, "b")

    fig.suptitle("Robustness and internal prediction check for the fire life-cycle model", fontsize=18)
    fig.text(
        0.5,
        -0.02,
        f"Synthetic internal validation only: n={summary['n_runs']} trajectories; monotonic area={summary['monotonic_area_fraction']:.1%}; ordered stages={summary['ordered_stage_fraction']:.1%}. Not empirical wildfire validation.",
        ha="center",
        color=COLORS["gray"],
        fontsize=9,
    )
    return _save_figure(fig, output_dir, "figure5_life_cycle_validation", dpi)


def _write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    if not rows:
        raise ValueError("cannot write an empty CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def generate_manuscript_figures(
    output_dir: str | Path,
    *,
    dpi: int = 400,
    validation_runs: int = 300,
    seed: int = 20260927,
) -> dict[str, object]:
    """Generate all manuscript remakes, data tables, and a manifest."""

    if dpi < 150:
        raise ValueError("dpi must be at least 150")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _style()

    generated: list[Path] = []
    generated += make_figure_1(output_dir, dpi)
    generated += make_figure_2(output_dir, dpi)
    generated += make_figure_3(output_dir, dpi)
    figure4_paths, trajectory = make_figure_4(output_dir, dpi)
    generated += figure4_paths

    records, validation_summary = run_life_cycle_validation(n_runs=validation_runs, seed=seed)
    generated += make_validation_figure(output_dir, dpi, records, validation_summary)

    trajectory_rows = []
    reverse_stage = {index: stage for stage, index in trajectory.stage_indices.items()}
    for index in range(len(trajectory.time)):
        trajectory_rows.append(
            {
                "time_hours": float(trajectory.time[index]),
                "area_ha": float(trajectory.area[index]),
                "active_perimeter_relative": float(trajectory.active_perimeter[index]),
                "growth_rate_ha_per_hour": float(trajectory.growth_rate[index]),
                "normalized_metabolic_prefactor": float(trajectory.forcing[index]),
                "beta": float(trajectory.beta[index]),
                "connected_fuel_fraction": float(trajectory.fuel_fraction[index]),
                "effective_velocity": float(trajectory.effective_velocity[index]),
                "connectivity": float(trajectory.connectivity[index]),
                "matching_efficiency": float(trajectory.matching_efficiency[index]),
                "coupling": float(trajectory.coupling[index]),
                "sigma_edge": float(trajectory.sigma_edge[index]),
                "fragmentation": float(trajectory.fragmentation[index]),
                "patch_dimension": float(trajectory.patch_dimension[index]),
                "frp_relative": float(trajectory.frp[index]),
                "fre_relative": float(trajectory.fre[index]),
                "stage_marker": reverse_stage.get(index, ""),
            }
        )
    _write_csv(output_dir / "figure4_life_cycle_trajectory.csv", trajectory_rows)
    _write_csv(output_dir / "figure5_forecast_records.csv", records)
    _write_csv(output_dir / "figure5_forecast_summary.csv", validation_summary["metrics"])
    (output_dir / "figure5_validation_summary.json").write_text(json.dumps(validation_summary, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "title": "Fire Critter manuscript figure remakes",
        "source_reference": "Fire Critter for PNAS-8.pdf",
        "classification": {
            "figure1": "analytical schematic",
            "figure2": "conceptual synthetic geometry",
            "figure3": "synthetic measured masks",
            "figure4": "synthetic reduced life-cycle model",
            "figure5": "synthetic internal validation",
        },
        "empirical_claim": "None. Outputs are not validation on observed fires.",
        "dpi": dpi,
        "seed": seed,
        "validation_runs": validation_runs,
        "life_cycle_parameters": asdict(LifeCycleParameters()),
        "life_cycle_equations": {
            "fuel_fraction": "F = (A_max - A)/(A_max - A0)",
            "matching_efficiency": "eta = 4r/(1+r)^2, r=C/F",
            "active_perimeter": "P_a = k C A^(2/3)",
            "effective_velocity": "v_eff = v0 F eta",
            "metabolic_rate": "dA/dt = beta0 C F eta A^(2/3)",
            "connectivity": "dC/dt = alpha C (1-C) F - mu C",
            "coupling_capacity": "q = min(1, 2 eta sqrt(CF))",
        },
        "generated_files": [path.name for path in generated],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
