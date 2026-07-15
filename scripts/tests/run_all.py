#!/usr/bin/env python3
"""Run every EIF test suite and report a compact pass/fail summary.

Convenience runner for local development and a single CI step. Each suite is
an independent script that exits 0 on success; this runner subprocesses them
and aggregates.

Usage:
    python scripts/tests/run_all.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SUITES = [
    "test_validate.py",
    "test_privacy_scan.py",
    "test_knowledge_delta.py",
    "test_generate_index.py",
    "test_search_knowledge.py",
    "test_locale.py",
    "test_render.py",
    "test_markers.py",
    "test_verify_runtime.py",
    "test_init.py",
    "test_journey.py",
    "test_adoption.py",
]


def main() -> int:
    failures = []
    for suite in SUITES:
        proc = subprocess.run(
            [sys.executable, str(TESTS_DIR / suite)],
            capture_output=True, text=True, encoding="utf-8",
        )
        last = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        summary = last[-1] if last else "(no output)"
        status = "ok  " if proc.returncode == 0 else "FAIL"
        print(f"{status} {suite:<28} {summary}")
        if proc.returncode != 0:
            failures.append(suite)
            # Show the failing detail so CI logs are actionable.
            for ln in last:
                if ln.startswith("FAIL"):
                    print(f"       {ln}")

    print()
    if failures:
        print(f"run_all: {len(SUITES) - len(failures)}/{len(SUITES)} suites passed; FAILED: {', '.join(failures)}")
        return 1
    print(f"run_all: all {len(SUITES)} suites passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
