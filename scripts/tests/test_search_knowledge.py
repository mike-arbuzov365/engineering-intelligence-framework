#!/usr/bin/env python3
"""Tests for eif_search_knowledge.py: real retrieval, no-result behavior,
Unicode/Ukrainian queries, lifecycle-aware status filtering, and honest
malformed-artifact reporting.

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

UKRAINIAN_FACT = """---
type: fact
status: validated
scope: project
evidence: OBSERVED
source: official_specification
created: 2026-07-15
---

# Високосний рік

Рік високосний, якщо ділиться на 4, окрім столітніх років, крім кратних 400.
"""

REJECTED_UK_HYPOTHESIS = """---
type: hypothesis
status: rejected
scope: project
evidence: OBSERVED
source: test
created: 2026-07-15
---

# Високосний рік = рік ділиться на 4 (відхилено)

Гіпотеза відхилена - не враховує столітній виняток.
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

MALFORMED = """---
type: fact
status: [broken yaml
---

# Malformed
"""


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def main() -> int:
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "fp").mkdir()
        (root / "fp" / "PATTERN-0001.md").write_text(LEAP_YEAR_PATTERN, encoding="utf-8")
        (root / "facts").mkdir()
        (root / "facts" / "FACT-uk.md").write_text(UKRAINIAN_FACT, encoding="utf-8")
        (root / "facts" / "HYP-uk.md").write_text(REJECTED_UK_HYPOTHESIS, encoding="utf-8")
        (root / "facts" / "FACT-db.md").write_text(UNRELATED_FACT, encoding="utf-8")
        (root / "facts" / "BROKEN.md").write_text(MALFORMED, encoding="utf-8")

        # English retrieval, default eligible = validated only
        en = search(root, "leap year", None, 5, {"validated"})
        results.append(check(
            "English retrieval finds the validated failure pattern",
            any(r["path"] == "fp/PATTERN-0001.md" for r in en["results"]),
            str(en["results"]),
        ))
        results.append(check(
            "unrelated fact not returned for unrelated query",
            all(r["path"] != "facts/FACT-db.md" for r in en["results"]),
        ))

        # BLOCKER regression: Ukrainian (Cyrillic) query must match Ukrainian content
        uk = search(root, "високосний", None, 5, {"validated"})
        results.append(check(
            "Unicode/Ukrainian query matches Ukrainian artifact (was zero before the WORD_RE fix)",
            any(r["path"] == "facts/FACT-uk.md" for r in uk["results"]),
            str(uk["results"]),
        ))

        # Lifecycle: default excludes the rejected hypothesis, reports it as skipped
        results.append(check(
            "rejected hypothesis NOT in default results",
            all(r["path"] != "facts/HYP-uk.md" for r in uk["results"]),
        ))
        results.append(check(
            "rejected hypothesis reported as status-ineligible, not silently dropped",
            any(r["path"] == "facts/HYP-uk.md" for r in uk["skipped_by_status"]),
            str(uk["skipped_by_status"]),
        ))

        # Lifecycle: explicit include returns the rejected one too
        uk_all = search(root, "високосний", None, 5, None)
        results.append(check(
            "--all-statuses (eligible=None) includes the rejected hypothesis",
            any(r["path"] == "facts/HYP-uk.md" for r in uk_all["results"]),
        ))

        # Honest failure: malformed artifact reported, distinct from 'not found'
        results.append(check(
            "malformed artifact reported explicitly (not confused with no-result)",
            "facts/BROKEN.md" in uk["malformed"],
            str(uk["malformed"]),
        ))

        # No-result behavior
        none = search(root, "quantum encryption protocol", None, 5, {"validated"})
        results.append(check(
            "no-result query returns empty results list, not a crash",
            none["results"] == [],
            str(none["results"]),
        ))

    passed = sum(results)
    print(f"\ntest_search_knowledge: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
