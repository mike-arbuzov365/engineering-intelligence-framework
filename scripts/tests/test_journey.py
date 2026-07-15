#!/usr/bin/env python3
"""Deterministic end-to-end journey test.

The clean-clone reproduction claimed for the demo previously only re-ran the
*already-passing* committed state - it never actually reproduced
failing-before -> passing-after, because the fix was already in the committed
source. This test reproduces the full journey deterministically, in an
isolated temp copy, without disturbing the committed demo:

  1. Copy the demo's src/tests/knowledge into a temp workspace.
  2. Reset the implementation to an UNIMPLEMENTED stub.
  3. Run the behavioral test -> assert it FAILS (before).
  4. Apply the recorded solution (the committed implementation).
  5. Run the behavioral test -> assert it PASSES (after).
  6. Prove retrieval influences the task: a search over the seeded knowledge
     surfaces the failure-pattern lesson the solution is expected to follow.
  7. Validate the instance's knowledge frontmatter.

"Deterministic solution application" = the recorded, committed implementation
is applied verbatim; the test proves the journey mechanics reproduce, not
that an agent re-derived the fix.

Usage:
    python scripts/tests/test_journey.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
DEMO = FRAMEWORK_ROOT / "examples" / "demo-workspace"

sys.path.insert(0, str(FRAMEWORK_ROOT / "scripts"))
from eif_search_knowledge import search  # noqa: E402
from eif_validate_frontmatter import validate_frontmatter_mode  # noqa: E402

STUB = '''\
def is_leap_year(year: int) -> bool:
    raise NotImplementedError("is_leap_year is not implemented yet")
'''


def run_demo_test(workspace: Path) -> subprocess.CompletedProcess:
    test_file = workspace / "tests" / "test_calendar_utils.py"
    return subprocess.run(
        [sys.executable, str(test_file)],
        capture_output=True, text=True, encoding="utf-8",
    )


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def main() -> int:
    results = []
    committed_solution = (DEMO / "src" / "calendar_utils.py").read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "demo"
        shutil.copytree(DEMO / "src", ws / "src")
        shutil.copytree(DEMO / "tests", ws / "tests")
        shutil.copytree(DEMO / "knowledge", ws / "knowledge")
        target = ws / "src" / "calendar_utils.py"

        # 2-3. Reset to stub, assert failing-before.
        target.write_text(STUB, encoding="utf-8")
        before = run_demo_test(ws)
        results.append(check("failing-before: behavioral test fails on the unimplemented stub",
                             before.returncode != 0, f"rc={before.returncode}"))

        # 4-5. Apply recorded solution, assert passing-after.
        target.write_text(committed_solution, encoding="utf-8")
        after = run_demo_test(ws)
        results.append(check("passing-after: applying the committed solution makes the test pass",
                             after.returncode == 0, after.stdout + after.stderr))

        # 6. Retrieval influences the task.
        found = search(ws / "knowledge", "leap year", None, 5, {"validated"})
        results.append(check("retrieval surfaces the seeded failure-pattern lesson before implementation",
                             any("PATTERN-0001" in r["path"] for r in found["results"]),
                             str(found["results"])))

        # 7. Instance knowledge validates.
        rc = validate_frontmatter_mode(FRAMEWORK_ROOT, ws, ["knowledge/**/*.md"])
        results.append(check("instance knowledge frontmatter validates", rc == 0))

    passed = sum(results)
    print(f"\ntest_journey: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
