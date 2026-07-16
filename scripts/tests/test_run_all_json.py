#!/usr/bin/env python3
"""Verify run_all.py's machine-readable aggregation.

- unit: aggregate() derives suite/check totals from per-suite results and
  reports UNKNOWN (never a silent 0) for a suite with no parsed total;
- integration: `run_all.py --json --only ...` emits an inventory whose
  aggregate equals the sum of the per-suite totals it reports - the total is
  derived by the runner, not hand-summed in PR prose anywhere.

Standalone (deliberately NOT in run_all's SUITES list - it invokes run_all,
which would otherwise recurse). CI runs it as its own step.

Usage:
    python scripts/tests/test_run_all_json.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))
import run_all  # noqa: E402


def main() -> int:
    results = []

    def check(name, cond, detail=""):
        ok = bool(cond)
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else ": " + str(detail)[:300]))
        results.append(ok)

    # --- unit: an unknown total is surfaced, never silently counted as 0 ---
    synthetic = [
        {"suite": "a", "exit_code": 0, "passed": 10, "total": 10},
        {"suite": "b", "exit_code": 0, "passed": 5, "total": 5},
        {"suite": "c", "exit_code": 0, "passed": None, "total": None},  # emitted no EIF-RESULT line
    ]
    agg = run_all.aggregate(synthetic)
    check("unit: known checks summed (15); the unknown suite is not counted", agg["checks_passed"] == 15 and agg["checks_total"] == 15, agg)
    check("unit: unknown suite surfaced with status 'unknown' (not a silent 0)", agg["checks_total_status"] == "unknown" and agg["unknown_suites"] == ["c"], agg)
    check("unit: all-known -> status 'exact'", run_all.aggregate(synthetic[:2])["checks_total_status"] == "exact")

    # --- integration: aggregate == sum of the per-suite totals it reports ---
    proc = subprocess.run(
        [sys.executable, str(TESTS_DIR / "run_all.py"), "--json", "--only", "test_paths.py,test_locale.py"],
        capture_output=True, text=True, encoding="utf-8",
    )
    check("integration: run_all --json --only exits 0", proc.returncode == 0, proc.stderr)
    inv = json.loads(proc.stdout)
    per_suite_total = sum(s["total"] for s in inv["suites"])
    per_suite_passed = sum(s["passed"] for s in inv["suites"])
    a = inv["aggregate"]
    check("integration: aggregate.checks_total == sum(per-suite totals) - derived, not hardcoded", a["checks_total"] == per_suite_total, (a["checks_total"], per_suite_total))
    check("integration: aggregate.checks_passed == sum(per-suite passed)", a["checks_passed"] == per_suite_passed)
    check("integration: 2/2 suites, status exact, no unknowns", a["suites_passed"] == 2 and a["suites_total"] == 2 and a["checks_total_status"] == "exact" and a["unknown_suites"] == [], a)

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_run_all_json: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
