"""Run Tier-1 fire-model scaling experiments end to end."""

from __future__ import annotations

import csv
import json
import platform
import sys
from pathlib import Path

import numpy as np
import yaml

from .fit_scaling import fit_by_run, fixed_exponent_scores, local_slopes
from .plotting import write_presentation_figure, write_scaling_figures
from .run_benchmarks import run_exact_ellipse
from .run_cell2fire import attempt_cell2fire
from .run_cellular import run_cellular
from .run_elmfire import attempt_elmfire
from .run_huygens import run_huygens
from .run_level_set import run_level_set


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def package_versions() -> dict[str, str]:
    versions = {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
    }
    for name in ["scipy", "skimage", "matplotlib", "yaml"]:
        try:
            module = __import__(name)
            versions[name] = getattr(module, "__version__", "unknown")
        except Exception:
            versions[name] = "not_importable"
    return versions


def main() -> int:
    config_path = PROJECT_ROOT / "config" / "experiments.yml"
    output_root = PROJECT_ROOT / "outputs"
    with config_path.open() as file:
        config = yaml.safe_load(file)

    all_rows: list[dict[str, object]] = []
    all_rows.extend(run_exact_ellipse(config, output_root))
    all_rows.extend(run_huygens(config, output_root))
    all_rows.extend(run_level_set(config, output_root))
    all_rows.extend(run_cellular(config, output_root))

    metrics_path = output_root / "metrics" / "fire_model_scaling_metrics.csv"
    write_csv(metrics_path, all_rows)

    fits = fit_by_run(all_rows, early_fraction=float(config["experiment"]["exclude_early_fraction"]))
    fits_path = output_root / "tables" / "scaling_fits.csv"
    write_csv(fits_path, [fit.as_dict() for fit in fits])

    fixed_scores: list[dict[str, object]] = []
    local_rows: list[dict[str, object]] = []
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for row in all_rows:
        key = (row["model"], row["scenario"], row["initial_shape"], row["replicate"])
        grouped.setdefault(key, []).append(row)

    for key, rows in grouped.items():
        valid_rows = [
            row
            for row in rows
            if bool(row["valid_geometry"]) and not bool(row["domain_edge_contact"])
        ]
        if len(valid_rows) >= 3:
            for score in fixed_exponent_scores(valid_rows):
                fixed_scores.append(
                    {
                        "model": key[0],
                        "scenario": key[1],
                        "initial_shape": key[2],
                        "replicate": key[3],
                        **score,
                    }
                )
            for slope_row in local_slopes(valid_rows, window=min(5, len(valid_rows))):
                local_rows.append(
                    {
                        "model": key[0],
                        "scenario": key[1],
                        "initial_shape": key[2],
                        "replicate": key[3],
                        **slope_row,
                    }
                )

    write_csv(output_root / "tables" / "fixed_exponent_scores.csv", fixed_scores)
    write_csv(output_root / "tables" / "local_slopes.csv", local_rows)

    actual_status = [attempt_elmfire(output_root), attempt_cell2fire(output_root)]
    write_csv(output_root / "tables" / "actual_model_status.csv", actual_status)

    versions_path = output_root / "logs" / "package_versions.json"
    versions_path.parent.mkdir(parents=True, exist_ok=True)
    versions_path.write_text(json.dumps(package_versions(), indent=2))

    write_scaling_figures(metrics_path, fits_path, output_root / "figures")
    write_presentation_figure(
        metrics_path,
        fits_path,
        output_root / "figures" / "presentation_fire_model_geometry",
    )

    print(f"Wrote metrics to {metrics_path}")
    print(f"Wrote fits to {fits_path}")
    print(f"Wrote figures to {output_root / 'figures'}")
    print(f"Wrote actual-model status logs to {output_root / 'logs'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
