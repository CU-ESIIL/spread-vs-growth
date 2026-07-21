#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH="src:${PYTHONPATH:-}" python scripts/run_fire_model_scaling.py
