#!/usr/bin/env python3
"""Positive/negative fixture tests for eif_validate_frontmatter.py.

Every fixture named `positive_*` must pass (exit 0); every fixture named
`negative_*` must fail (exit 1). This is what "confirm every relevant gate
fails on bad input" means made concrete and automated, not just asserted
in prose.

Usage:
    python scripts/tests/test_validate.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "eif_validate_frontmatter.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, encoding="utf-8",
    )


def main() -> int:
    failures = []

    # --- frontmatter fixtures: each file validated individually ---
    fm_dir = FIXTURES / "frontmatter"
    fm_files = sorted(fm_dir.glob("*.md"))
    if not fm_files:
        print("no frontmatter fixtures found", file=sys.stderr)
        return 1

    for f in fm_files:
        rel = f.relative_to(REPO_ROOT)
        proc = run(["--framework-root", str(REPO_ROOT), "--instance-root", str(REPO_ROOT), str(rel)])
        expect_pass = f.name.startswith("positive_")
        expect_fail = f.name.startswith("negative_")
        if not (expect_pass or expect_fail):
            failures.append(f"fixture {f.name} doesn't start with positive_/negative_ - can't tell what to expect")
            continue
        ok = (proc.returncode == 0) if expect_pass else (proc.returncode != 0)
        status = "PASS" if ok else "FAIL"
        print(f"{status} {f.name} (exit={proc.returncode}, expected {'0' if expect_pass else 'nonzero'})")
        if not ok:
            failures.append(f"{f.name}: expected {'success' if expect_pass else 'failure'}, got exit {proc.returncode}\n{proc.stdout}\n{proc.stderr}")

    # --- config fixtures ---
    cfg_dir = FIXTURES / "config"
    cfg_files = sorted(cfg_dir.glob("*.yaml"))
    for f in cfg_files:
        proc = run(["--framework-root", str(REPO_ROOT), "--config", str(f)])
        expect_pass = f.name.startswith("positive")
        expect_fail = f.name.startswith("negative")
        if not (expect_pass or expect_fail):
            failures.append(f"fixture {f.name} doesn't start with positive/negative - can't tell what to expect")
            continue
        ok = (proc.returncode == 0) if expect_pass else (proc.returncode != 0)
        status = "PASS" if ok else "FAIL"
        print(f"{status} {f.name} (exit={proc.returncode}, expected {'0' if expect_pass else 'nonzero'})")
        if not ok:
            failures.append(f"{f.name}: expected {'success' if expect_pass else 'failure'}, got exit {proc.returncode}\n{proc.stdout}\n{proc.stderr}")

    total = len(fm_files) + len(cfg_files)
    print(f"EIF-RESULT: passed={total - len(failures)} total={total}")
    print(f"\ntest_validate: {total - len(failures)}/{total} fixture(s) behaved as expected")
    if failures:
        print("\nFailures:")
        for f in failures:
            print(f"- {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
