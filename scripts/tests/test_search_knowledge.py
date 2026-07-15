#!/usr/bin/env python3
"""Tests for eif_search_knowledge.py: real retrieval, no-result behavior,
Unicode/Ukrainian queries, lifecycle-aware status filtering, and the
three-way honest classification (malformed vs. schema-invalid vs. found).

Usage:
    python scripts/tests/test_search_knowledge.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eif_search_knowledge import search  # noqa: E402

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]

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

SCHEMA_INVALID_LEAP = """---
type: not_a_real_type
status: validated
scope: project
evidence: OBSERVED
source: code
created: 2026-07-15
---

# Leap year edge case, but schema-invalid

Mentions leap year but has a bad type enum.
"""


def check(name: str, condition: bool, detail: str = "") -> bool:
    condition = bool(condition)
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def main() -> int:
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "failure-patterns").mkdir()
        (root / "failure-patterns" / "PATTERN-0001.md").write_text(LEAP_YEAR_PATTERN, encoding="utf-8")
        (root / "facts").mkdir()
        (root / "facts" / "FACT-uk.md").write_text(UKRAINIAN_FACT, encoding="utf-8")
        (root / "facts" / "HYP-uk.md").write_text(REJECTED_UK_HYPOTHESIS, encoding="utf-8")
        (root / "facts" / "FACT-db.md").write_text(UNRELATED_FACT, encoding="utf-8")
        (root / "facts" / "BROKEN.md").write_text("---\ntype: fact\nstatus: [broken\n---\n", encoding="utf-8")
        (root / "facts" / "SCHEMA-INVALID-LEAP.md").write_text(SCHEMA_INVALID_LEAP, encoding="utf-8")

        # English retrieval, default eligible = validated only, schema-aware.
        en = search(root, "leap year", None, 5, {"validated"}, framework_root=FRAMEWORK_ROOT)
        results.append(check(
            "English retrieval finds the validated failure pattern",
            any(r["path"] == "failure-patterns/PATTERN-0001.md" for r in en["results"]),
            str(en["results"]),
        ))
        results.append(check(
            "unrelated fact not returned for unrelated query",
            all(r["path"] != "facts/FACT-db.md" for r in en["results"]),
        ))
        results.append(check(
            "a matching but schema-invalid artifact is NOT silently returned as a valid result",
            all(r["path"] != "facts/SCHEMA-INVALID-LEAP.md" for r in en["results"]),
        ))
        results.append(check(
            "schema-invalid artifact is reported distinctly, not conflated with malformed or no-result",
            any(e["path"] == "facts/SCHEMA-INVALID-LEAP.md" for e in en["schema_invalid"]),
            str(en["schema_invalid"]),
        ))
        results.append(check(
            "malformed (unparseable YAML) artifact reported in its own bucket, not mixed with schema_invalid",
            "facts/BROKEN.md" in en["malformed"] and all(e["path"] != "facts/BROKEN.md" for e in en["schema_invalid"]),
        ))

        # BLOCKER regression: Ukrainian (Cyrillic) query must match Ukrainian content
        uk = search(root, "високосний", None, 5, {"validated"}, framework_root=FRAMEWORK_ROOT)
        results.append(check(
            "Unicode/Ukrainian query matches Ukrainian artifact",
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
        uk_all = search(root, "високосний", None, 5, None, framework_root=FRAMEWORK_ROOT)
        results.append(check(
            "--all-statuses (eligible=None) includes the rejected hypothesis",
            any(r["path"] == "facts/HYP-uk.md" for r in uk_all["results"]),
        ))

        # Without framework_root: schema-invalid detection is off (documented limitation).
        en_no_schema = search(root, "leap year", None, 5, {"validated"}, framework_root=None)
        results.append(check(
            "without framework_root, schema-invalid detection is off (falls through as valid)",
            en_no_schema["schema_invalid"] == [],
        ))

        # No-result behavior
        none = search(root, "quantum encryption protocol", None, 5, {"validated"}, framework_root=FRAMEWORK_ROOT)
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
