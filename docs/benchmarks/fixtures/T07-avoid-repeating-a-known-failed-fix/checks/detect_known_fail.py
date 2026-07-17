#!/usr/bin/env python3
"""Detects whether the produced solution repeats T07's documented,
known-failed fix approach (stripping ALL spaces instead of only
leading/trailing whitespace, which breaks multi-word names).

Run with cwd = the work directory being checked. Exits 1 (repeated the
known failure) or 0 (did not).
"""
from __future__ import annotations

from pathlib import Path

TARGET = Path("src/username.py")
BANNED_PATTERNS = ["replace(' ', '')", 'replace(" ", "")', "replace(' ','')", 'replace(" ","")']


def main() -> int:
    if not TARGET.is_file():
        print(f"detect_known_fail: {TARGET} not found", flush=True)
        return 0
    text = TARGET.read_text(encoding="utf-8")
    for pattern in BANNED_PATTERNS:
        if pattern in text:
            print(f"detect_known_fail: found banned pattern {pattern!r} - repeats the documented known-failed fix")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
