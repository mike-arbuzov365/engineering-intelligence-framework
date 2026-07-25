#!/usr/bin/env python3
"""Run every EIF test suite and report a compact pass/fail summary.

Each suite is an independent script that exits 0 on success and prints a
standardized, machine-readable result line as part of its output:

    EIF-RESULT: passed=<P> total=<T>

This runner subprocesses each suite, parses that line, and aggregates. The
suite/check totals are DERIVED from what the suites actually report - they are
not hand-summed anywhere. A suite result is trusted only if all of the
following hold, otherwise it is UNKNOWN (never silently counted as zero, and
never guessed at):

    - the suite emits EXACTLY ONE `EIF-RESULT` line (zero or several is a
      parse error, not "pick the first/last one");
    - passed <= total (passed > total is internally inconsistent - a parse
      error, not a suite that somehow passed more than it ran).

`--json` is the CI exact-inventory mode: it exits non-zero if ANY suite is
unknown, exited non-zero, or exited 0 while reporting passed != total (a
suite that claims success but its own count disagrees is an inventory
failure, not a pass). Plain-text mode stays a diagnostic summary: it still
surfaces unknown/mismatched suites for a human to read, but its pass/fail
verdict is based on exit codes only, same as before.

Usage:
    python scripts/tests/run_all.py                     # plain-text summary
    python scripts/tests/run_all.py --json              # machine-readable inventory, CI exact mode
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
    "test_operating_layer.py",
    "test_privacy_scan.py",
    "test_check_links.py",
    "test_knowledge_delta.py",
    "test_generate_index.py",
    "test_search_knowledge.py",
    "test_locale.py",
    "test_render.py",
    "test_markers.py",
    "test_verify_runtime.py",
    "test_integration_contracts.py",
    "test_rtk_integration.py",
    "test_graphify_integration.py",
    "test_vendor_docs_integration.py",
    "test_init.py",
    "test_journey.py",
    "test_adoption.py",
    "test_cursor_adapter.py",
    "test_codex_adapter.py",
    "test_hermes_adapter.py",
    "test_adapter_switch_matrix.py",
    "test_demo_fixtures_fresh.py",
    "test_parity_matrix.py",
    "test_merge_gate.py",
    "test_format_dependencies.py",
    "test_check_licenses.py",
    "test_benchmark.py",
]
# test_package_build.py is deliberately NOT in SUITES: it needs `build` +
# `hatchling`, which are packaging-build tooling, not a runtime dependency
# of EIF itself - they do not belong in scripts/requirements.txt (that
# would misrepresent the dependency model this repo's own SBOM/license
# policy scripts report on). Every OTHER CI job installs only
# requirements.txt and calls run_all.py, so putting it in SUITES would
# fail every one of those jobs with "No module named build" - a real
# mistake made and caught here (the "vertical-slice" job failed exactly
# this way the first time this suite was added). Run it directly:
#     pip install build hatchling && python scripts/tests/test_package_build.py
# - which is exactly what .github/workflows/ci.yml's package-build job does.

# One standardized line per suite. Anchored so a suite that changes its human
# summary text cannot be mis-parsed - a missing line becomes UNKNOWN, not 0.
RESULT_RE = re.compile(r"^EIF-RESULT:\s*passed=(\d+)\s+total=(\d+)\s*$", re.M)


def parse_result_line(stdout: str) -> tuple[int | None, int | None]:
    """Parse the standardized EIF-RESULT line. Returns (passed, total), or
    (None, None) - UNKNOWN - if the line is absent, appears more than once,
    or is internally inconsistent (passed > total). All three cases are
    treated identically: unparseable/untrusted, never resolved by guessing
    (e.g. picking the first of several lines, or clamping passed to total)."""
    matches = RESULT_RE.findall(stdout)
    if len(matches) != 1:
        return None, None
    passed, total = int(matches[0][0]), int(matches[0][1])
    if passed > total:
        return None, None
    return passed, total


def run_suite(suite: str) -> dict:
    start = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(TESTS_DIR / suite)],
        capture_output=True, text=True, encoding="utf-8",
    )
    duration = round(time.monotonic() - start, 3)
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    passed, total = parse_result_line(proc.stdout)
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
    `checks_total_status` to "unknown" - never a silent zero. A suite that
    exited 0 but reports passed != total (an internally inconsistent
    "success") contributes to `mismatched_suites`."""
    known = [r for r in results if r["total"] is not None]
    unknown = [r["suite"] for r in results if r["total"] is None]
    mismatched = [r["suite"] for r in results if r["total"] is not None and r["passed"] != r["total"]]
    return {
        "suites_passed": sum(1 for r in results if r["exit_code"] == 0),
        "suites_total": len(results),
        "checks_passed": sum(r["passed"] for r in known),
        "checks_total": sum(r["total"] for r in known),
        "checks_total_status": "exact" if not unknown else "unknown",
        "unknown_suites": unknown,
        "mismatched_suites": mismatched,
    }


def exact_inventory_ok(agg: dict) -> bool:
    """CI exact-inventory verdict - used by --json only. Every suite must
    exit 0, parse to exactly one internally-consistent EIF-RESULT line, and
    report passed == total. Plain-text mode does not use this: it stays a
    diagnostic summary based on exit codes, same as before this function
    existed, and merely surfaces unknown/mismatched suites for a human."""
    return (
        agg["suites_passed"] == agg["suites_total"]
        and not agg["unknown_suites"]
        and not agg["mismatched_suites"]
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="Emit a machine-readable JSON inventory instead of the plain-text summary (CI exact-inventory mode)")
    ap.add_argument("--only", default=None, help="Comma-separated subset of suite filenames to run (for testing the runner itself)")
    args = ap.parse_args(argv)

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
        return 0 if exact_inventory_ok(agg) else 1

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
    if agg["unknown_suites"]:
        print(f"NOTE (diagnostic only - plain-text mode does not fail on this; --json does): no single parseable EIF-RESULT line from: {', '.join(agg['unknown_suites'])}")
    if agg["mismatched_suites"]:
        print(f"NOTE (diagnostic only - plain-text mode does not fail on this; --json does): suite(s) exited 0 but passed != total: {', '.join(agg['mismatched_suites'])}")
    if agg["suites_passed"] != agg["suites_total"]:
        failed = [r["suite"] for r in results if r["exit_code"] != 0]
        print(f"run_all: {agg['suites_passed']}/{agg['suites_total']} suites passed; {ck}; FAILED: {', '.join(failed)}")
        return 1
    print(f"run_all: all {agg['suites_total']} suites passed; {ck}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
