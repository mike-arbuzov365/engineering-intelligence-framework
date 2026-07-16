#!/usr/bin/env python3
"""Verify run_all.py's machine-readable aggregation and its fail-closed
CI exact-inventory mode (--json).

- unit: `parse_result_line` treats a missing, duplicated, or internally
  inconsistent (passed > total) EIF-RESULT line identically - UNKNOWN, never
  guessed at. `aggregate()` derives suite/check totals from per-suite results
  and flags both unknown and mismatched (exit 0 but passed != total) suites.
  `exact_inventory_ok()` is the CI verdict function.
- integration: `run_all.py --json --only ...` emits an inventory whose
  aggregate equals the sum of the per-suite totals it reports (the total is
  derived by the runner, not hand-summed in PR prose anywhere), AND exits
  non-zero for a suite that is unknown or mismatched even though that suite's
  own exit code is 0. Plain-text mode is proven to stay diagnostic-only (it
  does not fail on the same unknown suite) - the two modes are deliberately
  different.

Standalone (deliberately NOT in run_all's SUITES list - it invokes run_all,
which would otherwise recurse). CI runs it as its own step.

Usage:
    python scripts/tests/test_run_all_json.py
"""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))
import run_all  # noqa: E402


def call_main_capture(argv: list[str]) -> tuple[int, str]:
    """Call run_all.main() in-process (not via subprocess) so a monkeypatch
    of run_all.SUITES in this process is actually seen by --only. Each
    fixture suite named in argv must exist as a real file on disk, since
    run_suite() still subprocesses it individually."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = run_all.main(argv)
    return code, buf.getvalue()


def write_fixture(name: str, content: str) -> Path:
    path = TESTS_DIR / name
    path.write_text(content, encoding="utf-8")
    return path


def with_fixture_suite(name: str, content: str, argv: list[str]) -> tuple[int, str]:
    """Write a throwaway suite script into TESTS_DIR, register it in
    run_all.SUITES for the duration of one call_main_capture(), then remove
    both the file and the registration - never leaves the fixture behind."""
    path = write_fixture(name, content)
    run_all.SUITES.append(name)
    try:
        return call_main_capture(argv)
    finally:
        run_all.SUITES.remove(name)
        path.unlink(missing_ok=True)


def main() -> int:
    results = []

    def check(name, cond, detail=""):
        ok = bool(cond)
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else ": " + str(detail)[:300]))
        results.append(ok)

    # --- unit: parse_result_line never guesses at an untrustworthy result ---
    check("unit: parse_result_line - normal single line",
          run_all.parse_result_line("noise\nEIF-RESULT: passed=5 total=5\nmore noise\n") == (5, 5))
    check("unit: parse_result_line - zero lines -> UNKNOWN, not (0,0)",
          run_all.parse_result_line("no result line here\n") == (None, None))
    check("unit: parse_result_line - two lines -> UNKNOWN, never silently picks the first",
          run_all.parse_result_line("EIF-RESULT: passed=1 total=1\nEIF-RESULT: passed=2 total=2\n") == (None, None))
    check("unit: parse_result_line - passed > total -> UNKNOWN, not clamped",
          run_all.parse_result_line("EIF-RESULT: passed=12 total=10\n") == (None, None))

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

    # --- unit: a suite that exits 0 but passed != total is a mismatch, not a pass ---
    synthetic_mismatch = [
        {"suite": "a", "exit_code": 0, "passed": 10, "total": 10},
        {"suite": "m", "exit_code": 0, "passed": 8, "total": 10},  # exits 0, but its own count disagrees
    ]
    agg_m = run_all.aggregate(synthetic_mismatch)
    check("unit: aggregate flags an exit-0 suite with passed != total as mismatched", agg_m["mismatched_suites"] == ["m"], agg_m)

    # --- unit: exact_inventory_ok is the single CI (--json) verdict function ---
    clean_agg = {"suites_passed": 3, "suites_total": 3, "unknown_suites": [], "mismatched_suites": []}
    check("unit: exact_inventory_ok - all clean -> True", run_all.exact_inventory_ok(clean_agg) is True)
    check("unit: exact_inventory_ok - an unknown suite -> False",
          run_all.exact_inventory_ok({**clean_agg, "unknown_suites": ["x"]}) is False)
    check("unit: exact_inventory_ok - a mismatched suite -> False",
          run_all.exact_inventory_ok({**clean_agg, "mismatched_suites": ["y"]}) is False)
    check("unit: exact_inventory_ok - a suite exited non-zero -> False",
          run_all.exact_inventory_ok({**clean_agg, "suites_passed": 2}) is False)

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
    check("integration: 2/2 suites, status exact, no unknowns/mismatches", a["suites_passed"] == 2 and a["suites_total"] == 2 and a["checks_total_status"] == "exact" and a["unknown_suites"] == [] and a["mismatched_suites"] == [], a)

    # --- integration: --json (CI exact mode) fails closed on unknown/mismatched suites ---
    code, out = with_fixture_suite(
        "_fixture_zero_result_lines.py", 'print("no result line here")\n',
        ["--json", "--only", "_fixture_zero_result_lines.py"],
    )
    check("integration: --json exits non-zero for a suite with zero EIF-RESULT lines (exits 0 otherwise)", code != 0, (code, out))

    code, out = with_fixture_suite(
        "_fixture_duplicate_result.py",
        'print("EIF-RESULT: passed=1 total=1")\nprint("EIF-RESULT: passed=2 total=2")\n',
        ["--json", "--only", "_fixture_duplicate_result.py"],
    )
    check("integration: --json exits non-zero for a suite with two EIF-RESULT lines (exits 0 otherwise)", code != 0, (code, out))

    code, out = with_fixture_suite(
        "_fixture_passed_gt_total.py", 'print("EIF-RESULT: passed=12 total=10")\n',
        ["--json", "--only", "_fixture_passed_gt_total.py"],
    )
    check("integration: --json exits non-zero for a suite reporting passed > total", code != 0, (code, out))

    code, out = with_fixture_suite(
        "_fixture_mismatch.py", 'print("EIF-RESULT: passed=8 total=10")\n',
        ["--json", "--only", "_fixture_mismatch.py"],
    )
    check("integration: --json exits non-zero for a suite that exits 0 but passed != total", code != 0, (code, out))

    code, out = with_fixture_suite(
        "_fixture_exit_nonzero.py", 'import sys\nprint("EIF-RESULT: passed=4 total=5")\nsys.exit(1)\n',
        ["--json", "--only", "_fixture_exit_nonzero.py"],
    )
    check("integration: --json exits non-zero for a suite that itself exits non-zero", code != 0, (code, out))

    # --- integration: plain-text mode is deliberately diagnostic-only ---
    code, out = with_fixture_suite(
        "_fixture_diagnostic_only.py", 'print("no result line here")\n',
        ["--only", "_fixture_diagnostic_only.py"],
    )
    check("integration: plain-text mode does NOT fail for an unknown suite that exits 0 (diagnostic NOTE instead)",
          code == 0 and "NOTE" in out, (code, out))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_run_all_json: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
