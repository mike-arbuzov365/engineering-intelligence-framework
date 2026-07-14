#!/usr/bin/env python3
"""Tests for eif_generate_index.py: index creation and malformed-artifact
rejection.

Usage:
    python scripts/tests/test_generate_index.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eif_generate_index import build_index, render  # noqa: E402

VALID_FACT = """---
type: fact
status: validated
scope: project
evidence: OBSERVED
source: code
created: 2026-07-15
---

# A valid fact

Some body text that becomes the excerpt.
"""

VALID_RULE = """---
type: rule
status: draft
scope: project
created: 2026-07-15
---

# A valid rule

Rule body.
"""

MALFORMED_NO_FRONTMATTER = """# Not a knowledge artifact

Just prose, no --- frontmatter block at all.
"""

MALFORMED_BROKEN_YAML = """---
type: fact
status: [this is not
scope: project
---

# Broken YAML frontmatter
"""


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def main() -> int:
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "facts").mkdir()
        (root / "facts" / "FACT-0001.md").write_text(VALID_FACT, encoding="utf-8")
        (root / "rules").mkdir()
        (root / "rules" / "RULE-0001.md").write_text(VALID_RULE, encoding="utf-8")
        (root / "broken").mkdir()
        (root / "broken" / "NO-FRONTMATTER.md").write_text(MALFORMED_NO_FRONTMATTER, encoding="utf-8")
        (root / "broken" / "BROKEN-YAML.md").write_text(MALFORMED_BROKEN_YAML, encoding="utf-8")

        rows, malformed = build_index(root)

        results.append(check("index creation: 2 valid artifacts indexed", len(rows) == 2, f"got {len(rows)}"))
        results.append(check("malformed artifact rejection: 2 malformed files excluded, not crashed", len(malformed) == 2, f"got {len(malformed)}"))

        types_found = {r["type"] for r in rows}
        results.append(check("indexed rows carry correct frontmatter type", types_found == {"fact", "rule"}, str(types_found)))

        rendered = render(rows, malformed, root)
        results.append(check("rendered index lists both valid artifacts", "facts/FACT-0001.md" in rendered and "rules/RULE-0001.md" in rendered))
        results.append(check("rendered index reports excluded malformed files", "Excluded" in rendered and "NO-FRONTMATTER.md" in rendered))

    passed = sum(results)
    print(f"\ntest_generate_index: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
