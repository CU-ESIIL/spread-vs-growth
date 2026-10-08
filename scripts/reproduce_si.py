#!/usr/bin/env python3
"""Reproduce mathematical checks, SI examples, and analytical figures."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from fire_metabolism.diagnostics import assert_symbolic_checks, evidence_boundary_summary, load_claim_ledger
from fire_metabolism.figures import generate_all_figures
from fire_metabolism.worked_examples import reproduce_worked_examples


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Run checks without regenerating figures")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "si_reproduction")
    return parser.parse_args()


def run_tests() -> tuple[int, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SRC)
    environment.setdefault("MPLCONFIGDIR", "/tmp/spread-vs-growth-mpl")
    command = [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests")]
    completed = subprocess.run(command, cwd=ROOT, env=environment, text=True, capture_output=True, check=False)
    transcript = completed.stdout + completed.stderr
    return completed.returncode, transcript


def flatten(prefix: str, value, rows: list[dict[str, object]]):
    if isinstance(value, dict):
        for key, child in value.items():
            flatten(f"{prefix}.{key}" if prefix else key, child, rows)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            flatten(f"{prefix}[{index}]", child, rows)
    else:
        rows.append({"result": prefix, "value": value})


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    symbolic = assert_symbolic_checks()
    worked = reproduce_worked_examples()
    ledger = load_claim_ledger(ROOT / "claims" / "fire_metabolism_claims.json")
    test_code, test_transcript = run_tests()
    if test_code:
        print(test_transcript, file=sys.stderr)
        return test_code

    if args.check_only:
        figure_paths = sorted((output_dir / "figures").glob("*.png")) + sorted((output_dir / "figures").glob("*.pdf"))
        generated_figure_count = 0
    else:
        figure_paths = generate_all_figures(output_dir / "figures")
        generated_figure_count = len(figure_paths) // 2
    rows: list[dict[str, object]] = []
    flatten("", worked, rows)
    with (output_dir / "worked_examples.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["result", "value"])
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "status": "mathematical_checks_passed",
        "empirical_validation_performed": False,
        "symbolic_checks": symbolic,
        "claim_summary": evidence_boundary_summary(ledger),
        "worked_examples": worked,
        "figures": [str(path.relative_to(ROOT)) for path in figure_paths],
        "test_transcript": test_transcript.strip(),
        "important_boundary": "Passing checks verifies algebra, numerics, constructions, and conditional consequences; it does not validate the empirical wildfire hypotheses.",
    }
    with (output_dir / "validation_report.json").open("w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)

    print("Fire metabolism SI reproduction: PASS")
    print(f"Symbolic checks: {len(symbolic)}")
    print(f"Worked examples: {len([key for key in worked if key.startswith('example_')])}/7")
    print(f"Figures generated: {generated_figure_count}")
    if args.check_only:
        print(f"Existing figure sets recorded: {len(figure_paths) // 2}")
    print(f"Claims requiring empirical data: {report['claim_summary']['requires_empirical_data']}")
    print("Empirical validation performed: no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
