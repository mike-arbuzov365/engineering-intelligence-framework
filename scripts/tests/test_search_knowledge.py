#!/usr/bin/env python3
"""Tests for eif_search_knowledge.py: real retrieval and no-result behavior.

Usage:
    python scripts/tests/test_search_knowledge.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eif_search_knowledge import search  # noqa: E402

LEAP_YEAR_PATTERN = """---
type: failure_pattern
status: validated
scope: project
evidence: OBSERVED
source: official_specification
created: 2026-07-15
---

# Naive leap-year check fails on century years

A naive year % 4 == 0 check is wrong for century years not divisible by 400.
"""

UNRELATED_FACT = """---
type: fact
status: validated
scope: project
evidence: OBSERVED
source: code
created: 2026-07-15
---

# Database connection pooling default

The default pool size is 10 connections.
"""


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def main() -> int:
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "failure-patterns").mkdir()
        (root / "failure-patterns" / "PATTERN-0001.md").write_text(LEAP_YEAR_PATTERN, encoding="utf-8")
        (root / "facts").mkdir()
        (root / "facts" / "FACT-0001.md").write_text(UNRELATED_FACT, encoding="utf-8")

        relevant_results = search(root, "leap year", None, 5)
        results.append(check(
            "real retrieval: query for 'leap year' finds the seeded failure pattern",
            len(relevant_results) >= 1 and relevant_results[0]["path"] == "failure-patterns/PATTERN-0001.md",
            str(relevant_results),
        ))
        results.append(check(
            "real retrieval: unrelated fact is not returned for an unrelated query",
            all(r["path"] != "facts/FACT-0001.md" for r in relevant_results),
        ))

        no_results = search(root, "quantum encryption protocol", None, 5)
        results.append(check(
            "no-result retrieval behavior: unrelated query returns an empty list, not a crash or false match",
            no_results == [],
            str(no_results),
        ))

        type_filtered = search(root, "connection pooling", "fact", 5)
        results.append(check(
            "type filter narrows results to the requested frontmatter type",
            len(type_filtered) == 1 and type_filtered[0]["type"] == "fact",
            str(type_filtered),
        ))

    passed = sum(results)
    print(f"\ntest_search_knowledge: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
