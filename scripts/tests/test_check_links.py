#!/usr/bin/env python3
"""Regression tests for Unicode diagnostics and deleted tracked Markdown."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
CHECKER = FRAMEWORK_ROOT / "scripts" / "eif_check_links.py"


def check(name: str, condition: bool, detail: str = "") -> tuple[bool, str]:
    line = f"{'PASS' if condition else 'FAIL'} {name}"
    if detail and not condition:
        line += f": {detail}"
    print(line)
    return condition, line


def run_checker(repo: Path, *, legacy_stdout: bool = False) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if legacy_stdout:
        env["PYTHONIOENCODING"] = "cp1252"
    return subprocess.run(
        [sys.executable, str(CHECKER), "--repo", str(repo)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def main() -> int:
    results: list[tuple[bool, str]] = []
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
        guide = repo / "guide.md"
        guide.write_text("[missing](відсутній.md)\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "guide.md"], check=True)

        broken = run_checker(repo, legacy_stdout=True)
        results.append(check(
            "Unicode broken-link diagnostic exits 1 without an encoding crash",
            broken.returncode == 1 and "UnicodeEncodeError" not in broken.stderr,
            broken.stdout + broken.stderr,
        ))
        results.append(check(
            "Unicode diagnostic still reports the broken-link result",
            "1 broken link(s)" in broken.stdout,
            broken.stdout + broken.stderr,
        ))

        guide.unlink()
        missing_tracked = run_checker(repo)
        results.append(check(
            "an intentionally deleted tracked Markdown file is skipped, not crashed",
            missing_tracked.returncode == 0 and "Traceback" not in missing_tracked.stderr,
            missing_tracked.stdout + missing_tracked.stderr,
        ))

    passed = sum(1 for ok, _ in results if ok)
    total = len(results)
    print(f"EIF-RESULT: passed={passed} total={total}")
    print(f"test_check_links: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
