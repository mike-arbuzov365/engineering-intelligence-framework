#!/usr/bin/env python3
"""Anti-cheating mutation for T03: overwrites the work directory's
src/inventory.py with this fixture's known-buggy "refactor" (the
extracted helper silently drops the negative-quantity validation both
original functions had), regardless of how the agent structured its own
refactor - proving the test suite actually catches a refactor that
changes behavior, not just one that runs without crashing.

Usage:
    python apply_mutation.py <work_dir>
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: apply_mutation.py <work_dir>", file=sys.stderr)
        return 2
    work_dir = Path(sys.argv[1])
    target = work_dir / "src" / "inventory.py"
    if not target.parent.is_dir():
        print(f"apply_mutation: {target.parent} does not exist", file=sys.stderr)
        return 1
    shutil.copyfile(FIXTURE_DIR / "buggy_reference_inventory.py", target)
    print(f"apply_mutation: overwrote {target} with the known-buggy reference")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
