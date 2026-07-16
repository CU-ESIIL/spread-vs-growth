"""Shared filesystem paths for project scripts."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"
ANIMATIONS_DIR = OUTPUTS_DIR / "animations"
DOCS_ASSETS_DIR = PROJECT_ROOT / "docs" / "assets"
