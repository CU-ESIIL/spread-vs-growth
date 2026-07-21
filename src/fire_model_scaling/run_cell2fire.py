"""Record status for actual Cell2Fire runs.

This module reports only real Cell2Fire attempts and outputs. It intentionally
does not substitute emulator output for Cell2Fire.
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


def attempt_cell2fire(output_root: Path) -> dict[str, object]:
    log_path = output_root / "logs" / "cell2fire_attempt.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    external_dir = PROJECT_ROOT / "external" / "Cell2Fire"
    executable = external_dir / "cell2fire" / "Cell2FireC" / "Cell2Fire"
    build_log = output_root / "logs" / "cell2fire_native_build.log"
    run_log = output_root / "logs" / "cell2fire_real_run.log"
    output_dir = output_root / "raw" / "cell2fire_sub40x40"
    commit = _git_commit(external_dir)

    build_text = build_log.read_text(errors="replace") if build_log.exists() else ""
    if executable.exists() and run_log.exists():
        status = "run_attempted"
        reason = "Cell2Fire executable and run log detected"
    elif "boost/algorithm/string.hpp" in build_text:
        status = "build_failed_missing_boost"
        reason = "native C++ build failed because Boost headers were not available"
    elif build_log.exists():
        status = "build_failed"
        reason = "native C++ build failed; inspect build log"
    else:
        status = "not_run"
        reason = "no local Cell2Fire build or run artifacts detected"

    message = "\n".join(
        [
            "Actual Cell2Fire status",
            f"status: {status}",
            f"official repository: https://github.com/cell2fire/Cell2Fire",
            f"documentation: https://cell2fire.readthedocs.io/",
            f"external checkout: {external_dir}",
            f"external commit: {commit or 'unknown'}",
            f"native build log: {build_log}",
            f"run log: {run_log}",
            f"output directory: {output_dir}",
            f"executable present: {executable.exists()}",
            f"reason: {reason}",
            "No emulator output has been labeled as Cell2Fire.",
            "",
        ]
    )
    log_path.write_text(message)
    return {
        "model": "Cell2Fire",
        "implementation_type": "actual_software",
        "status": status,
        "official_url": "https://github.com/cell2fire/Cell2Fire",
        "documentation_url": "https://cell2fire.readthedocs.io/",
        "external_commit": commit,
        "reason": reason,
        "log_path": str(log_path),
        "build_log_path": str(build_log),
        "run_log_path": str(run_log),
        "output_path": str(output_dir),
    }
