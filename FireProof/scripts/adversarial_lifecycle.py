#!/usr/bin/env python3
"""Deterministic stress test of the unchanged dimensionless life-cycle ODE.

This is a numerical search, not a proof.  It integrates

    x' = gamma * 4 C^2 F^2 / (C+F)^2 * x^(2/3)
    C' = C ((1-C)F - delta)
    F  = (1-x)/(1-x0)

where x=A/Amax and tau=alpha*t.  The closed forcing is algebraically equal to
``C*F*eta(C/F)`` for positive C and F and remains numerically stable near F=0.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp


@dataclass(frozen=True)
class RunSummary:
    run_id: int
    gamma: float
    delta: float
    x0: float
    c0: float
    initial_balance: float
    initial_acceleration: bool
    connectivity_initially_recruits: bool
    global_peak_tau: float
    global_peak_interior: bool
    local_peak_count: int
    monotone_decline: bool
    final_x: float
    final_c: float
    final_f: float
    final_rate_fraction: float
    connectivity_collapse_before_ten_percent_growth: bool
    fuel_depletion_while_well_matched: bool
    mismatch_loss_with_abundant_fuel: bool


def forcing(c: np.ndarray, f: np.ndarray) -> np.ndarray:
    denominator = c + f
    return np.divide(
        4.0 * c**2 * f**2,
        denominator**2,
        out=np.zeros_like(denominator),
        where=denominator > 0,
    )


def matching(c: np.ndarray, f: np.ndarray) -> np.ndarray:
    denominator = (c + f) ** 2
    return np.divide(
        4.0 * c * f,
        denominator,
        out=np.zeros_like(denominator),
        where=denominator > 0,
    )


def simulate(
    gamma: float,
    delta: float,
    x0: float,
    c0: float,
    tau: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    def rhs(_tau: float, state: np.ndarray) -> tuple[float, float]:
        x, c = state
        f = max(0.0, (1.0 - x) / (1.0 - x0))
        coupled = 0.0 if c + f <= 0 else 4.0 * c**2 * f**2 / (c + f) ** 2
        xdot = gamma * coupled * max(x, 0.0) ** (2.0 / 3.0)
        cdot = c * ((1.0 - c) * f - delta)
        return xdot, cdot

    solution = solve_ivp(
        rhs,
        (float(tau[0]), float(tau[-1])),
        (x0, c0),
        t_eval=tau,
        rtol=1e-9,
        atol=1e-12,
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    x = np.clip(solution.y[0], x0, 1.0)
    c = np.clip(solution.y[1], 0.0, 1.0)
    f = np.clip((1.0 - x) / (1.0 - x0), 0.0, 1.0)
    eta = matching(c, f)
    rate = gamma * forcing(c, f) * x ** (2.0 / 3.0)
    return x, c, f, eta, rate


def relative_rate_balance(
    gamma: float,
    delta: float,
    x0: float,
    x: np.ndarray,
    c: np.ndarray,
    f: np.ndarray,
    rate: np.ndarray,
) -> np.ndarray:
    c_log = (1.0 - c) * f - delta
    f_log = np.divide(
        -rate,
        (1.0 - x0) * f,
        out=np.full_like(rate, -np.inf),
        where=f > 0,
    )
    eta_log = np.divide(
        f - c,
        f + c,
        out=np.zeros_like(rate),
        where=f + c > 0,
    ) * (c_log - f_log)
    geometric = np.divide(
        (2.0 / 3.0) * rate,
        x,
        out=np.zeros_like(rate),
        where=x > 0,
    )
    return c_log + f_log + eta_log + geometric


def summarize_run(
    run_id: int,
    gamma: float,
    delta: float,
    x0: float,
    c0: float,
    tau: np.ndarray,
    x: np.ndarray,
    c: np.ndarray,
    f: np.ndarray,
    eta: np.ndarray,
    rate: np.ndarray,
) -> RunSummary:
    balance = relative_rate_balance(gamma, delta, x0, x, c, f, rate)
    peak_index = int(np.argmax(rate))
    slope_tolerance = max(float(np.max(rate)) * 1e-10, 1e-15)
    increments = np.diff(rate)
    peaks = np.flatnonzero(
        (increments[:-1] > slope_tolerance)
        & (increments[1:] <= slope_tolerance)
    ) + 1
    tolerance = max(float(np.max(rate)) * 2e-6, 1e-13)
    growth_fraction = (x - x0) / (1.0 - x0)
    collapse = np.flatnonzero(c <= 0.5 * c0)
    collapse_early = bool(
        collapse.size and growth_fraction[int(collapse[0])] < 0.10
    )
    return RunSummary(
        run_id=run_id,
        gamma=gamma,
        delta=delta,
        x0=x0,
        c0=c0,
        initial_balance=float(balance[0]),
        initial_acceleration=bool(balance[0] > 0),
        connectivity_initially_recruits=bool((1.0 - c0) > delta),
        global_peak_tau=float(tau[peak_index]),
        global_peak_interior=bool(0 < peak_index < len(tau) - 1),
        local_peak_count=int(len(peaks)),
        monotone_decline=bool(np.all(np.diff(rate) <= tolerance)),
        final_x=float(x[-1]),
        final_c=float(c[-1]),
        final_f=float(f[-1]),
        final_rate_fraction=float(rate[-1] / max(np.max(rate), 1e-300)),
        connectivity_collapse_before_ten_percent_growth=collapse_early,
        fuel_depletion_while_well_matched=bool(np.any((f < 0.1) & (eta > 0.8))),
        mismatch_loss_with_abundant_fuel=bool(np.any((f > 0.5) & (eta < 0.1))),
    )


def find_observational_twin(
    area_paths: np.ndarray,
    connectivity_paths: np.ndarray,
    summaries: list[RunSummary],
) -> dict[str, object]:
    squared_norms = np.sum(area_paths**2, axis=1)
    squared_distances = (
        squared_norms[:, None]
        + squared_norms[None, :]
        - 2.0 * area_paths @ area_paths.T
    )
    squared_distances = np.maximum(squared_distances, 0.0)
    np.fill_diagonal(squared_distances, np.inf)
    neighbors = np.argsort(squared_distances, axis=1)[:, :11]
    candidates: list[tuple[float, float, int, int]] = []
    for i in range(len(area_paths)):
        for j in neighbors[i]:
            c_rmse = float(np.sqrt(np.mean((connectivity_paths[i] - connectivity_paths[j]) ** 2)))
            area_rmse = float(
                np.sqrt(squared_distances[i, j] / area_paths.shape[1])
            )
            if c_rmse > 0.02:
                candidates.append((area_rmse, -c_rmse, i, int(j)))
    if not candidates:
        return {"found": False}
    area_rmse, neg_c_rmse, i, j = min(candidates)
    return {
        "found": True,
        "area_rmse": area_rmse,
        "connectivity_rmse": -neg_c_rmse,
        "run_a": asdict(summaries[i]),
        "run_b": asdict(summaries[j]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "results",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    tau = np.linspace(0.0, 200.0, 1601)
    parameter_grid = product(
        (0.01, 0.05, 0.2, 1.0, 5.0),
        (0.02, 0.1, 0.3, 0.7, 1.0, 1.5),
        (0.001, 0.05, 0.3, 0.7, 0.9),
        (0.005, 0.03, 0.15, 0.5, 0.9),
    )
    summaries: list[RunSummary] = []
    area_paths: list[np.ndarray] = []
    connectivity_paths: list[np.ndarray] = []
    sample_indices = np.linspace(0, len(tau) - 1, 101).astype(int)

    for run_id, (gamma, delta, x0, c0) in enumerate(parameter_grid):
        x, c, f, eta, rate = simulate(gamma, delta, x0, c0, tau)
        summaries.append(
            summarize_run(run_id, gamma, delta, x0, c0, tau, x, c, f, eta, rate)
        )
        area_paths.append(x[sample_indices])
        connectivity_paths.append(c[sample_indices])

    csv_path = args.output_dir / "lifecycle_parameter_sweep.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(summaries[0])))
        writer.writeheader()
        writer.writerows(asdict(summary) for summary in summaries)

    counts = {
        "runs": len(summaries),
        "initial_acceleration": sum(x.initial_acceleration for x in summaries),
        "monotone_decline": sum(x.monotone_decline for x in summaries),
        "interior_global_peak": sum(x.global_peak_interior for x in summaries),
        "multiple_local_peaks": sum(x.local_peak_count > 1 for x in summaries),
        "connectivity_collapse_before_ten_percent_growth": sum(
            x.connectivity_collapse_before_ten_percent_growth for x in summaries
        ),
        "fuel_depletion_while_well_matched": sum(
            x.fuel_depletion_while_well_matched for x in summaries
        ),
        "mismatch_loss_with_abundant_fuel": sum(
            x.mismatch_loss_with_abundant_fuel for x in summaries
        ),
        "rate_below_1e-4_of_peak_by_tau_200": sum(
            x.final_rate_fraction < 1e-4 for x in summaries
        ),
    }
    examples: dict[str, object] = {}
    predicates = {
        "monotone_decline": lambda x: x.monotone_decline,
        "interior_peak": lambda x: x.global_peak_interior,
        "connectivity_collapse": lambda x: x.connectivity_collapse_before_ten_percent_growth,
        "fuel_depletion_well_matched": lambda x: x.fuel_depletion_while_well_matched,
        "mismatch_abundant_fuel": lambda x: x.mismatch_loss_with_abundant_fuel,
    }
    for label, predicate in predicates.items():
        match = next((x for x in summaries if predicate(x)), None)
        examples[label] = asdict(match) if match else None

    report = {
        "classification": "NUMERICAL RESULT",
        "equations": {
            "x_rate": "gamma * 4*C^2*F^2/(C+F)^2 * x^(2/3)",
            "C_rate": "C*((1-C)*F-delta)",
            "F": "(1-x)/(1-x0)",
        },
        "grid": {
            "gamma": [0.01, 0.05, 0.2, 1.0, 5.0],
            "delta": [0.02, 0.1, 0.3, 0.7, 1.0, 1.5],
            "x0": [0.001, 0.05, 0.3, 0.7, 0.9],
            "C0": [0.005, 0.03, 0.15, 0.5, 0.9],
            "tau_horizon": 200.0,
        },
        "counts": counts,
        "examples": examples,
        "observational_twin": find_observational_twin(
            np.asarray(area_paths), np.asarray(connectivity_paths), summaries
        ),
        "caveat": "A finite grid and finite horizon cannot prove uniqueness or asymptotic extinction.",
    }
    json_path = args.output_dir / "lifecycle_adversarial_summary.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
