#!/usr/bin/env python3
"""Anti-cheating mutation for T05: overwrites the work directory's
src/pagination.py with the fixture's known-buggy reference implementation,
regardless of how the agent structured its fix.

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
    target = work_dir / "src" / "pagination.py"
    if not target.parent.is_dir():
        print(f"apply_mutation: {target.parent} does not exist", file=sys.stderr)
        return 1
    shutil.copyfile(FIXTURE_DIR / "buggy_reference_pagination.py", target)
    print(f"apply_mutation: overwrote {target} with the known-buggy reference")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
