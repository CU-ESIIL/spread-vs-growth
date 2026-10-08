#!/usr/bin/env python3
"""Rebuild the Fire Critter manuscript figures at publication resolution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fire_metabolism.manuscript_figures import generate_manuscript_figures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/manuscript_figures"))
    parser.add_argument("--dpi", type=int, default=400, help="Raster output resolution; vector PDFs/SVGs are also written.")
    parser.add_argument("--validation-runs", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20260927)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = generate_manuscript_figures(
        args.output_dir,
        dpi=args.dpi,
        validation_runs=args.validation_runs,
        seed=args.seed,
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

