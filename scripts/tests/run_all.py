#!/usr/bin/env python3
"""Run every EIF test suite and report a compact pass/fail summary.

Each suite is an independent script that exits 0 on success and prints a
standardized, machine-readable result line as part of its output:

    EIF-RESULT: passed=<P> total=<T>

This runner subprocesses each suite, parses that line, and aggregates. The
suite/check totals are DERIVED from what the suites actually report - they are
not hand-summed anywhere. A suite that does not emit the line has an UNKNOWN
check total: it is surfaced as `unknown` (in both plain-text and --json
output) and is NEVER silently counted as zero.

Usage:
    python scripts/tests/run_all.py                     # plain-text summary
    python scripts/tests/run_all.py --json              # machine-readable inventory
    python scripts/tests/run_all.py --only test_paths.py,test_locale.py
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SUITES = [
    "test_paths.py",
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
    "test_merge_gate.py",
]

# One standardized line per suite. Anchored so a suite that changes its human
# summary text cannot be mis-parsed - a missing line becomes UNKNOWN, not 0.
RESULT_RE = re.compile(r"^EIF-RESULT:\s*passed=(\d+)\s+total=(\d+)\s*$", re.M)


def run_suite(suite: str) -> dict:
    start = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(TESTS_DIR / suite)],
        capture_output=True, text=True, encoding="utf-8",
    )
    duration = round(time.monotonic() - start, 3)
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    m = RESULT_RE.search(proc.stdout)
    passed, total = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    human = next((ln for ln in reversed(lines) if not ln.startswith("EIF-RESULT:")), "(no output)")
    return {
        "suite": suite,
        "exit_code": proc.returncode,
        "passed": passed,
        "total": total,
        "duration_s": duration,
        "summary": human,
        "stdout_tail": lines[-8:],
    }


def aggregate(results: list[dict]) -> dict:
    """Derive suite/check aggregates from per-suite results. Suites with an
    unknown (unparsed) total contribute to `unknown_suites` and flip
    `checks_total_status` to "unknown" - never a silent zero."""
    known = [r for r in results if r["total"] is not None]
    unknown = [r["suite"] for r in results if r["total"] is None]
    return {
        "suites_passed": sum(1 for r in results if r["exit_code"] == 0),
        "suites_total": len(results),
        "checks_passed": sum(r["passed"] for r in known),
        "checks_total": sum(r["total"] for r in known),
        "checks_total_status": "exact" if not unknown else "unknown",
        "unknown_suites": unknown,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="Emit a machine-readable JSON inventory instead of the plain-text summary")
    ap.add_argument("--only", default=None, help="Comma-separated subset of suite filenames to run (for testing the runner itself)")
    args = ap.parse_args()

    suites = SUITES
    if args.only:
        requested = [s.strip() for s in args.only.split(",") if s.strip()]
        unknown_names = [s for s in requested if s not in SUITES]
        if unknown_names:
            print(f"run_all: unknown suite(s) in --only: {', '.join(unknown_names)}", file=sys.stderr)
            return 2
        suites = requested

    results = [run_suite(s) for s in suites]
    agg = aggregate(results)

    if args.json:
        print(json.dumps({"suites": results, "aggregate": agg}, indent=2))
        return 0 if agg["suites_passed"] == agg["suites_total"] else 1

    for r in results:
        status = "ok  " if r["exit_code"] == 0 else "FAIL"
        cnt = f"{r['passed']}/{r['total']}" if r["total"] is not None else "?/? (no EIF-RESULT)"
        print(f"{status} {r['suite']:<28} {cnt:<16} {r['summary']}")
        if r["exit_code"] != 0:
            for ln in r["stdout_tail"]:
                if ln.startswith("FAIL"):
                    print(f"       {ln}")

    ck = f"{agg['checks_passed']}/{agg['checks_total']} checks"
    if agg["checks_total_status"] != "exact":
        ck += f" (+UNKNOWN suites, not counted: {', '.join(agg['unknown_suites'])})"
    print()
    if agg["suites_passed"] != agg["suites_total"]:
        failed = [r["suite"] for r in results if r["exit_code"] != 0]
        print(f"run_all: {agg['suites_passed']}/{agg['suites_total']} suites passed; {ck}; FAILED: {', '.join(failed)}")
        return 1
    print(f"run_all: all {agg['suites_total']} suites passed; {ck}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
