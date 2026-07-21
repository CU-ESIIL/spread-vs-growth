"""Export dense model-run metrics as a handoff dataset for plotting agents."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fire_model_scaling.fit_scaling import ols_loglog


MODEL_LABELS = {
    "exact_ellipse": "Exact ellipse",
    "huygens_emulator": "Huygens emulator",
    "level_set_emulator": "Level-set emulator",
    "cellular_emulator": "Cellular emulator",
}

DATA_DICTIONARY = [
    ("row_id", "Unique row id assigned during export."),
    ("source_row", "One-based row number in the source dense metrics CSV."),
    ("plot_group", "level_set for level_set_emulator; other_models for all other model outputs."),
    ("model", "Model id used by the project workflow."),
    ("model_label", "Human-readable model label."),
    ("implementation_type", "Analytic, rasterized, or geometric-emulator implementation type."),
    ("scenario", "Scenario id from the dense run."),
    ("scenario_class", "isotropic, homogeneous_wind, heterogeneous, or other."),
    ("heterogeneity_strength", "Parsed heterogeneity strength; 0 for homogeneous wind/isotropic scenarios."),
    ("wind_factor", "Parsed anisotropy/wind factor when encoded in the scenario; blank otherwise."),
    ("direction_degrees", "Parsed wind direction in degrees when encoded in the scenario; blank otherwise."),
    ("replicate", "Replicate id from the model run."),
    ("initial_shape", "Ignition/initial shape id."),
    ("resolution_km", "Cell size or vector resolution in kilometers."),
    ("time", "Model output time/stage value."),
    ("area_km2", "Burned area in square kilometers."),
    ("exterior_perimeter_km", "Exterior perimeter in kilometers."),
    ("hole_perimeter_km", "Hole/interior perimeter in kilometers; currently zero in these outputs."),
    ("total_perimeter_km", "Total perimeter in kilometers."),
    ("component_count", "Number of burned components in the mask/vector measurement."),
    ("largest_component_fraction", "Fraction of burned area in the largest component."),
    ("domain_edge_contact", "True when the burned mask touched the simulation domain boundary."),
    ("valid_geometry", "True when area and perimeter are positive."),
    ("include_in_plot", "True when valid and not touching the domain edge."),
    ("perimeter_estimator", "Perimeter estimator used for the row."),
]


def str_to_bool(value: object) -> bool:
    return str(value).strip().lower() == "true"


def parse_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def parse_scenario(scenario: str) -> dict[str, object]:
    if scenario == "isotropic":
        return {
            "scenario_class": "isotropic",
            "heterogeneity_strength": 0.0,
            "wind_factor": "",
            "direction_degrees": "",
        }

    wind_match = re.match(r"wind_(?P<wind>[0-9p]+)_dir_(?P<direction>[0-9]+)$", scenario)
    if wind_match:
        return {
            "scenario_class": "homogeneous_wind",
            "heterogeneity_strength": 0.0,
            "wind_factor": float(wind_match.group("wind").replace("p", ".")),
            "direction_degrees": float(wind_match.group("direction")),
        }

    hetero_match = re.match(
        r"heterogeneous_(?P<hetero>[0-9p]+)_wind_(?P<wind>[0-9p]+)_repgroup_(?P<repgroup>[0-9]+)$",
        scenario,
    )
    if hetero_match:
        return {
            "scenario_class": "heterogeneous",
            "heterogeneity_strength": float(hetero_match.group("hetero").replace("p", ".")),
            "wind_factor": float(hetero_match.group("wind").replace("p", ".")),
            "direction_degrees": float(hetero_match.group("repgroup")) * 30.0,
        }

    return {
        "scenario_class": "other",
        "heterogeneity_strength": "",
        "wind_factor": "",
        "direction_degrees": "",
    }


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open() as file:
        return list(csv.DictReader(file))


def export_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    exported: list[dict[str, object]] = []
    for source_row, row in enumerate(rows, start=1):
        scenario_fields = parse_scenario(row["scenario"])
        model = row["model"]
        area = float(row["area"])
        exterior_perimeter = float(row["exterior_perimeter"])
        valid_geometry = str_to_bool(row["valid_geometry"])
        edge_contact = str_to_bool(row["domain_edge_contact"])
        include = valid_geometry and not edge_contact and area > 0.0 and exterior_perimeter > 0.0
        exported.append(
            {
                "row_id": f"model_run_{source_row:06d}",
                "source_row": source_row,
                "plot_group": "level_set" if model == "level_set_emulator" else "other_models",
                "model": model,
                "model_label": MODEL_LABELS.get(model, model),
                "implementation_type": row["implementation_type"],
                "scenario": row["scenario"],
                **scenario_fields,
                "replicate": row["replicate"],
                "initial_shape": row["initial_shape"],
                "resolution_km": row["resolution"],
                "time": row["time"],
                "area_km2": row["area"],
                "exterior_perimeter_km": row["exterior_perimeter"],
                "hole_perimeter_km": row["hole_perimeter"],
                "total_perimeter_km": row["total_perimeter"],
                "component_count": row["component_count"],
                "largest_component_fraction": row["largest_component_fraction"],
                "domain_edge_contact": row["domain_edge_contact"],
                "valid_geometry": row["valid_geometry"],
                "include_in_plot": str(include),
                "perimeter_estimator": row["perimeter_estimator"],
            }
        )
    return exported


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fieldnames = fieldnames or list(rows[0].keys())
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fit_summary(rows: list[dict[str, object]], label: str) -> dict[str, object]:
    valid = [
        row
        for row in rows
        if str_to_bool(row["include_in_plot"])
        and float(row["area_km2"]) > 0.0
        and float(row["exterior_perimeter_km"]) > 0.0
    ]
    result: dict[str, object] = {
        "summary_group": label,
        "n_all": len(rows),
        "n_valid_plot": len(valid),
        "sigma": "",
        "intercept": "",
        "sigma_se": "",
        "ci_low": "",
        "ci_high": "",
        "rmse": "",
    }
    if len(valid) >= 3:
        intercept, sigma, sigma_se, ci_low, ci_high, rmse = ols_loglog(
            [float(row["area_km2"]) for row in valid],
            [float(row["exterior_perimeter_km"]) for row in valid],
        )
        result.update(
            {
                "sigma": sigma,
                "intercept": intercept,
                "sigma_se": sigma_se,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "rmse": rmse,
            }
        )
    return result


def build_fit_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    fit_rows = [fit_summary(rows, "all_models")]
    for group in ["level_set", "other_models"]:
        fit_rows.append(fit_summary([row for row in rows if row["plot_group"] == group], group))
    for model in sorted({str(row["model"]) for row in rows}):
        fit_rows.append(fit_summary([row for row in rows if row["model"] == model], model))
    for group in ["level_set", "other_models"]:
        group_rows = [row for row in rows if row["plot_group"] == group]
        for heterogeneity in sorted(
            {
                float(row["heterogeneity_strength"])
                for row in group_rows
                if row["heterogeneity_strength"] != ""
            }
        ):
            subset = [
                row
                for row in group_rows
                if row["heterogeneity_strength"] != ""
                and float(row["heterogeneity_strength"]) == heterogeneity
            ]
            fit_rows.append(fit_summary(subset, f"{group}_heterogeneity_{heterogeneity:g}"))
    return fit_rows


def write_readme(path: Path, manifest: dict[str, object]) -> None:
    text = f"""# Model Hexbin Handoff Dataset

This directory contains the complete dense heterogeneous model-output dataset used for the split model hexbin figures.

## Files

- `model_runs_all.csv`: all model-output rows with added grouping and parsed scenario fields.
- `model_runs_level_set.csv`: level-set emulator rows only.
- `model_runs_other_models.csv`: exact ellipse, Huygens emulator, and cellular emulator rows.
- `model_fit_summary.csv`: log-log perimeter-area fits for all rows, split groups, each model, and heterogeneity levels.
- `data_dictionary.csv`: column descriptions.
- `manifest.json`: row counts, source file, and generation metadata.
- `model_hexbin_handoff_dataset.zip`: compressed copy of the CSV/JSON/README handoff files.

## Plotting Fields

Use `area_km2` for x, `exterior_perimeter_km` for y, and `include_in_plot == True` to match the figures generated in this repository.
Use `plot_group` to split `level_set` from `other_models`.

## Counts

- All rows: {manifest["row_count_all"]:,}
- Level-set rows: {manifest["row_count_level_set"]:,}
- Other-model rows: {manifest["row_count_other_models"]:,}
- Valid plotting rows: {manifest["row_count_valid_plot"]:,}

## Source

Source metrics: `{manifest["source_metrics"]}`
Generated: `{manifest["generated_at_utc"]}`
"""
    path.write_text(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "metrics" / "model_outputs_hexbin_more_heterogeneity_metrics.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "datasets" / "model_hexbin_handoff",
    )
    args = parser.parse_args()

    source = args.source.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = export_rows(read_rows(source))
    fieldnames = [name for name, _ in DATA_DICTIONARY]
    all_path = output_dir / "model_runs_all.csv"
    level_set_path = output_dir / "model_runs_level_set.csv"
    other_path = output_dir / "model_runs_other_models.csv"
    fits_path = output_dir / "model_fit_summary.csv"
    dictionary_path = output_dir / "data_dictionary.csv"
    manifest_path = output_dir / "manifest.json"
    readme_path = output_dir / "README.md"
    zip_path = output_dir / "model_hexbin_handoff_dataset.zip"

    level_set_rows = [row for row in rows if row["plot_group"] == "level_set"]
    other_rows = [row for row in rows if row["plot_group"] == "other_models"]
    fit_rows = build_fit_rows(rows)

    write_csv(all_path, rows, fieldnames)
    write_csv(level_set_path, level_set_rows, fieldnames)
    write_csv(other_path, other_rows, fieldnames)
    write_csv(fits_path, fit_rows)
    write_csv(
        dictionary_path,
        [{"column": column, "description": description} for column, description in DATA_DICTIONARY],
    )

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_metrics": str(source),
        "output_directory": str(output_dir),
        "row_count_all": len(rows),
        "row_count_level_set": len(level_set_rows),
        "row_count_other_models": len(other_rows),
        "row_count_valid_plot": sum(1 for row in rows if str_to_bool(row["include_in_plot"])),
        "files": {
            "all": all_path.name,
            "level_set": level_set_path.name,
            "other_models": other_path.name,
            "fit_summary": fits_path.name,
            "data_dictionary": dictionary_path.name,
            "readme": readme_path.name,
            "zip": zip_path.name,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    write_readme(readme_path, manifest)

    with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
        for path in [all_path, level_set_path, other_path, fits_path, dictionary_path, manifest_path, readme_path]:
            archive.write(path, arcname=path.name)

    print(f"Wrote handoff dataset to {output_dir}")
    print(f"Wrote zip archive to {zip_path}")
    print(f"Rows: all={len(rows):,}, level_set={len(level_set_rows):,}, other_models={len(other_rows):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
