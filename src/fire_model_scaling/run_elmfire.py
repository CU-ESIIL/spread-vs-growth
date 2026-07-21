"""Record status for actual ELMFIRE runs.

This module reports only real ELMFIRE attempts and outputs. It intentionally
does not substitute emulator output for ELMFIRE.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _git_commit(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return ""


def attempt_elmfire(output_root: Path) -> dict[str, object]:
    log_path = output_root / "logs" / "elmfire_attempt.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    external_dir = PROJECT_ROOT / "external" / "elmfire"
    output_dir = output_root / "raw" / "elmfire_constant_wind"
    run_log = output_root / "logs" / "elmfire_constant_wind_real_run_patched.log"
    build_log = output_root / "logs" / "elmfire_native_build.log"
    toa_files = sorted(output_dir.glob("time_of_arrival_*.tif"))
    isochrone = output_dir / "hourly_isochrones.shp"
    commit = _git_commit(external_dir)

    if toa_files and isochrone.exists() and run_log.exists():
        status = "run_success"
        reason = (
            "official ELMFIRE tutorial 01 constant-wind case completed with "
            "elmfire_perf_2025.1002 after local macOS tutorial-path fixes"
        )
    elif build_log.exists():
        status = "build_attempted_no_successful_run"
        reason = "native build/run attempted; no copied ELMFIRE output artifacts detected"
    else:
        status = "not_run"
        reason = "no local ELMFIRE build or run artifacts detected"

    message = "\n".join(
        [
            "Actual ELMFIRE status",
            f"status: {status}",
            f"official repository: https://github.com/lautenberger/elmfire",
            f"documentation: https://elmfire.io/",
            f"external checkout: {external_dir}",
            f"external commit: {commit or 'unknown'}",
            f"native build log: {build_log}",
            f"real run log: {run_log}",
            f"copied output directory: {output_dir}",
            f"time-of-arrival outputs: {len(toa_files)}",
            f"hourly isochrones present: {isochrone.exists()}",
            f"reason: {reason}",
            "No emulator output has been labeled as ELMFIRE.",
            "",
        ]
    )
    log_path.write_text(message)
    return {
        "model": "ELMFIRE",
        "implementation_type": "actual_software",
        "status": status,
        "official_url": "https://github.com/lautenberger/elmfire",
        "documentation_url": "https://elmfire.io/",
        "external_commit": commit,
        "reason": reason,
        "log_path": str(log_path),
        "build_log_path": str(build_log),
        "run_log_path": str(run_log),
        "output_path": str(output_dir),
    }
