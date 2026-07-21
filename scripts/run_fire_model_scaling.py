"""Command-line wrapper for the Tier-1 fire-model scaling workflow."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fire_model_scaling.run_all import main


if __name__ == "__main__":
    raise SystemExit(main())
