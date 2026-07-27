"""
Generates validation_summary.json from an actual pytest run.

This is an explicit, manual step. The dashboard (app.py) never
invokes pytest itself — it only reads this file if present, and
shows "Validation summary unavailable" otherwise.

Usage:
    python generate_validation_summary.py
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone

OUTPUT_FILE = "validation_summary.json"

STATUS_TOKENS = ("PASSED", "FAILED", "ERROR", "SKIPPED")


def run_verbose_pytest():
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "-p",
            "no:cacheprovider",
            "--tb=no",
        ],
        capture_output=True,
        text=True,
    )


def parse_results(stdout):
    """
    Parses pytest -v output lines such as:
        tests/test_rules.py::test_algorithm_risk PASSED

    into overall and per-file pass/fail/error/skipped counts.
    """

    overall = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    category_counts = {}

    for line in stdout.splitlines():
        line = line.strip()

        if "::" not in line:
            continue

        parts = line.split()

        if not parts:
            continue

        node_id = parts[0]

        status = next(
            (token for token in parts[1:] if token in STATUS_TOKENS),
            None,
        )

        if status is None:
            continue

        status = status.lower()
        file_name = node_id.split("::")[0]

        category_counts.setdefault(
            file_name,
            {"passed": 0, "failed": 0, "error": 0, "skipped": 0},
        )

        category_counts[file_name][status] += 1
        overall[status] += 1

    return overall, category_counts


def main():
    start = time.time()
    result = run_verbose_pytest()
    duration_seconds = round(time.time() - start, 2)

    overall, category_counts = parse_results(result.stdout)

    total_tests = sum(overall.values())

    summary = {
        "generated_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds"),
        "total_tests": total_tests,
        "passed": overall["passed"],
        "failed": overall["failed"] + overall["error"],
        "skipped": overall["skipped"],
        "duration_seconds": duration_seconds,
        "category_counts": category_counts,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    print(f"Wrote {OUTPUT_FILE}")
    print(json.dumps(summary, indent=2))

    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
