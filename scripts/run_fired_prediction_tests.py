#!/usr/bin/env python3
"""Run held-out cumulative-area forecasts on real FIRED daily sequences."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fire_metabolism.fired_prediction import (
    NATURAL_VEGETATION_CLASSES,
    load_fired_daily_attributes,
    reconstruct_daily_sequences,
    rolling_predictions,
    select_sigma_by_training_error,
    summarize_predictions,
)


MODEL_LABELS = {
    "no_growth": "No growth",
    "linear_area": "Linear area (sigma = 0)",
    "sqrt_area": "Diffusion-like (sigma = 1/2)",
    "cube_root_area": "Organized growth (sigma = 2/3)",
    "train_selected": "Train-selected sigma",
}
MODEL_COLORS = {
    "no_growth": "#4D4D4D",
    "linear_area": "#D95F02",
    "sqrt_area": "#6495ED",
    "cube_root_area": "#2E8B57",
    "train_selected": "#111111",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_train_selected_predictions(
    test_sequences: pd.DataFrame,
    selection_curve: pd.DataFrame,
    *,
    lookback_days: int,
) -> pd.DataFrame:
    selected = selection_curve[selection_curve["selected"]]
    frames = []
    for row in selected.itertuples(index=False):
        frame = rolling_predictions(
            test_sequences,
            {"train_selected": float(row.sigma)},
            lookback_days=lookback_days,
            horizons=(int(row.horizon_days),),
        )
        frames.append(frame[frame["model"] == "train_selected"])
    return pd.concat(frames, ignore_index=True)


def plot_performance(summary: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), sharey=True)
    for axis, subset, title in zip(
        axes,
        ("all", "growth_only"),
        ("All forecast targets", "Targets with observed growth"),
        strict=True,
    ):
        panel = summary[summary["subset"] == subset]
        for model in MODEL_LABELS:
            values = panel[panel["model"] == model].sort_values("horizon_days")
            if values.empty:
                continue
            x = values["horizon_days"].to_numpy()
            y = values["mean_event_absolute_log_ratio"].to_numpy()
            yerr = np.vstack(
                [y - values["ci95_lower"].to_numpy(), values["ci95_upper"].to_numpy() - y]
            )
            axis.errorbar(
                x,
                y,
                yerr=yerr,
                marker="o",
                markersize=5,
                linewidth=2.3,
                capsize=3,
                linestyle="--" if model == "train_selected" else "-",
                color=MODEL_COLORS[model],
                label=MODEL_LABELS[model],
            )
        axis.set_title(title)
        axis.set_xlabel("Forecast horizon (days)")
        axis.set_xticks([1, 2, 3])
        axis.grid(True, alpha=0.25)
    axes[0].set_ylabel("Event-balanced mean absolute log error")
    axes[1].legend(frameon=False, fontsize=9, loc="upper left")
    fig.suptitle("Held-out FIRED cumulative-area forecasts, 2016-2020", fontsize=15)
    fig.text(
        0.5,
        0.015,
        "Four prior calendar days used at each origin; lower error is better; bars are 95% event-bootstrap intervals.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.055, 1, 0.94))
    fig.savefig(output, dpi=220)
    plt.close(fig)


def plot_sigma_selection(curve: pd.DataFrame, output: Path) -> None:
    fig, axis = plt.subplots(figsize=(8.4, 5.2))
    colors = {1: "#0072B2", 2: "#D55E00", 3: "#009E73"}
    for horizon, group in curve.groupby("horizon_days"):
        group = group.sort_values("sigma")
        axis.plot(
            group["sigma"],
            group["mean_event_absolute_log_ratio"],
            marker="o",
            markersize=3.5,
            linewidth=2,
            color=colors[int(horizon)],
            label=f"{int(horizon)}-day horizon",
        )
        chosen = group[group["selected"]]
        axis.scatter(
            chosen["sigma"],
            chosen["mean_event_absolute_log_ratio"],
            s=80,
            facecolors="none",
            edgecolors=colors[int(horizon)],
            linewidths=2,
            zorder=4,
        )
    axis.axvline(0.5, color="#6495ED", linewidth=2, alpha=0.75, label="sigma = 1/2")
    axis.axvline(2 / 3, color="#2E8B57", linewidth=2, alpha=0.75, label="sigma = 2/3")
    axis.set(
        title="Exponent selection using FIRED training events, 2001-2015",
        xlabel="Candidate growth exponent, sigma",
        ylabel="Event-balanced mean absolute log error",
        xlim=(-0.02, 0.92),
    )
    axis.grid(True, alpha=0.25)
    axis.legend(frameon=False, ncol=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(output, dpi=220)
    plt.close(fig)


def plot_observed_predicted(predictions: pd.DataFrame, output: Path) -> None:
    models = ("no_growth", "linear_area", "sqrt_area", "cube_root_area")
    horizon = predictions[predictions["horizon_days"] == 2]
    lower = min(horizon["observed_area_km2"].min(), horizon["predicted_area_km2"].min())
    upper = max(horizon["observed_area_km2"].max(), horizon["predicted_area_km2"].max())
    fig, axes = plt.subplots(2, 2, figsize=(9.5, 8.5), sharex=True, sharey=True)
    for axis, model in zip(axes.flat, models, strict=True):
        values = horizon[horizon["model"] == model]
        axis.hexbin(
            values["observed_area_km2"],
            values["predicted_area_km2"],
            xscale="log",
            yscale="log",
            gridsize=44,
            mincnt=1,
            bins="log",
            cmap="magma_r",
        )
        axis.plot([lower, upper], [lower, upper], color="#444444", linewidth=1.4, linestyle="--")
        axis.set_title(MODEL_LABELS[model])
        axis.grid(True, alpha=0.18)
    for axis in axes[-1, :]:
        axis.set_xlabel("Observed cumulative area (km2)")
    for axis in axes[:, 0]:
        axis.set_ylabel("Predicted cumulative area (km2)")
    fig.suptitle("Two-day FIRED forecasts on held-out events, 2016-2020", fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output, dpi=220)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    default_source = os.environ.get(
        "FIRED_DAILY_GPKG",
        "data/raw/fired/fired_conus-ak_daily_nov2001-march2021.gpkg",
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fired-gpkg", type=Path, default=Path(default_source))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/fired_prediction"))
    parser.add_argument("--lookback-days", type=int, default=4)
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260927)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.fired_gpkg.expanduser().resolve()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)

    records = load_fired_daily_attributes(source)
    sequences = reconstruct_daily_sequences(records)
    training = sequences[sequences["ig_year"] <= 2015].copy()
    testing = sequences[sequences["ig_year"] >= 2016].copy()
    if training.empty or testing.empty:
        raise ValueError("the requested year split produced an empty partition")

    sigma_grid = np.unique(np.r_[np.arange(0, 0.901, 0.05), 0.5, 2 / 3])
    selection = select_sigma_by_training_error(
        training,
        sigma_grid,
        lookback_days=args.lookback_days,
        horizons=(1, 2, 3),
    )
    fixed = rolling_predictions(
        testing,
        {
            "linear_area": 0.0,
            "sqrt_area": 0.5,
            "cube_root_area": 2 / 3,
        },
        lookback_days=args.lookback_days,
        horizons=(1, 2, 3),
    )
    selected = add_train_selected_predictions(
        testing, selection, lookback_days=args.lookback_days
    )
    predictions = pd.concat([fixed, selected], ignore_index=True)

    summaries = []
    for index, subset in enumerate(("all", "growth_only", "active_origin")):
        summaries.append(
            summarize_predictions(
                predictions,
                subset=subset,
                bootstrap_replicates=args.bootstrap_replicates,
                seed=args.seed + index,
            )
        )
    summary = pd.concat(summaries, ignore_index=True)

    sequences.to_csv(output / "fired_sequences.csv.gz", index=False, compression="gzip")
    predictions.to_csv(output / "held_out_predictions.csv.gz", index=False, compression="gzip")
    selection.to_csv(output / "training_sigma_selection.csv", index=False)
    summary.to_csv(output / "forecast_summary.csv", index=False)
    plot_performance(summary, output / "forecast_performance.png")
    plot_sigma_selection(selection, output / "training_sigma_selection.png")
    plot_observed_predicted(predictions, output / "observed_vs_predicted_horizon2.png")

    chosen = selection[selection["selected"]][
        ["horizon_days", "sigma", "mean_event_absolute_log_ratio"]
    ].to_dict(orient="records")
    report = {
        "source": {
            "path": str(source),
            "sha256": sha256(source),
            "size_bytes": source.stat().st_size,
            "product": "FIRED CONUS+AK daily, November 2001-March 2021 archive naming",
            "dataset_page": "https://scholar.colorado.edu/concern/datasets/d504rm74m",
            "method_doi": "10.3390/rs12213498",
            "data_descriptor_doi": "10.1038/s41597-022-01572-3",
        },
        "design": {
            "train_years": [2001, 2015],
            "test_years": [2016, 2020],
            "lookback_days": args.lookback_days,
            "horizons_days": [1, 2, 3],
            "minimum_final_area_km2": 10.0,
            "duration_days": [8, 60],
            "minimum_detection_days": 4,
            "daily_to_reported_final_area_relative_tolerance": 0.01,
            "landcover_classes": list(NATURAL_VEGETATION_CLASSES),
            "selected_sigma_by_horizon": chosen,
            "primary_metric": "event-balanced mean absolute log(predicted/observed)",
        },
        "counts": {
            "events_total": int(sequences["id"].nunique()),
            "events_training": int(training["id"].nunique()),
            "events_testing": int(testing["id"].nunique()),
            "test_prediction_rows": int(len(predictions)),
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "matplotlib": plt.matplotlib.__version__,
        },
        "limitations": [
            "This is retrospective forecasting of satellite-derived cumulative burned area, not an operational fire forecast.",
            "FIRED sequences derive from MODIS MCD64A1 burn dates at approximately 500 m resolution.",
            "Natural-vegetation land-cover filtering does not prove that every event is an unplanned wildfire.",
            "Missing FIRED observation dates are treated as zero detected growth, so satellite timing affects short-horizon scores.",
            "Events whose daily increments do not reproduce reported final area within 1% are excluded as incomplete sequences.",
        ],
    }
    (output / "run_report.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "README.md").write_text(
        "# FIRED prediction outputs\n\n"
        "Real FIRED daily burned-area sequences were reconstructed from `dy_ar_km2`. "
        "Models use only the previous four calendar days at each forecast origin. "
        "The free exponent is selected on 2001-2015 events and all reported scores "
        "use held-out 2016-2020 events. See `run_report.json` for source identity, "
        "filters, counts, and limitations.\n"
    )
    print(json.dumps(report["counts"], indent=2))
    print("Selected sigma values:")
    print(pd.DataFrame(chosen).to_string(index=False))
    print("\nHeld-out all-target primary scores:")
    print(
        summary[summary["subset"] == "all"][
            ["horizon_days", "model", "mean_event_absolute_log_ratio", "ci95_lower", "ci95_upper"]
        ].sort_values(["horizon_days", "mean_event_absolute_log_ratio"]).to_string(index=False)
    )


if __name__ == "__main__":
    main()
