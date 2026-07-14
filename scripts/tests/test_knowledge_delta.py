#!/usr/bin/env python3
"""Tests for eif_check_knowledge_delta.py's three-way classification.

Usage:
    python scripts/tests/test_knowledge_delta.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eif_check_knowledge_delta import classify  # noqa: E402

TEMPLATE_SKELETON = """## Summary

Did a thing.

## Knowledge Delta

### Added

### Changed

### Not yet ratified

## Privacy statement

Ran the scanner.
"""

MEANINGFUL_BODY = """## Summary

Did a thing.

## Knowledge Delta

### Added
- New rule about X.

### Changed

### Not yet ratified

## Privacy statement

Ran the scanner.
"""

MECHANICAL_BODY = """## Summary

Fixed a typo.

<!-- no-knowledge-delta: mechanical task -->
"""

MECHANICAL_BODY_WITH_EMPTY_SECTION_TOO = """## Summary

Fixed a typo.

## Knowledge Delta

### Added

### Changed

<!-- no-knowledge-delta: mechanical task -->
"""

NO_SECTION_AT_ALL = """## Summary

Forgot the template entirely.
"""

MEANINGFUL_WITH_ONLY_A_COMMENT_LOOKING_LIKE_CONTENT = """## Knowledge Delta

<!-- reviewer: please check this carefully -->

## Privacy statement
"""


def main() -> int:
    cases = [
        ("untouched template skeleton", TEMPLATE_SKELETON, "empty"),
        ("meaningful content under Added", MEANINGFUL_BODY, "meaningful"),
        ("mechanical marker, no KD section", MECHANICAL_BODY, "mechanical"),
        ("mechanical marker wins even with empty KD section present", MECHANICAL_BODY_WITH_EMPTY_SECTION_TOO, "mechanical"),
        ("no Knowledge Delta heading at all", NO_SECTION_AT_ALL, "empty"),
        ("only an HTML comment under the heading is still empty", MEANINGFUL_WITH_ONLY_A_COMMENT_LOOKING_LIKE_CONTENT, "empty"),
    ]

    failures = []
    for name, body, expected in cases:
        actual = classify(body)
        ok = actual == expected
        print(f"{'PASS' if ok else 'FAIL'} {name}: expected={expected} actual={actual}")
        if not ok:
            failures.append(name)

    print(f"\ntest_knowledge_delta: {len(cases) - len(failures)}/{len(cases)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
