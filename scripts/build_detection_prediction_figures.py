#!/usr/bin/env python3
"""Build the two empirical Fire Critter manuscript figures from locked outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fire_metabolism.empirical_manuscript_figures import (
    EmpiricalFigureInputs,
    build_detection_prediction_figures,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validation-dir",
        type=Path,
        default=Path("outputs/adversarial_validation"),
    )
    parser.add_argument(
        "--sequences",
        type=Path,
        default=Path("outputs/fired_prediction/fired_sequences.csv.gz"),
    )
    parser.add_argument(
        "--geometry",
        type=Path,
        default=Path("outputs/fired_lifecycle_prediction/fired_geometry_sequences.csv.gz"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output/manuscript"))
    parser.add_argument("--dpi", type=int, default=600)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_detection_prediction_figures(
        EmpiricalFigureInputs(
            validation_dir=args.validation_dir,
            sequences_path=args.sequences,
            geometry_path=args.geometry,
        ),
        args.output_dir,
        dpi=args.dpi,
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
