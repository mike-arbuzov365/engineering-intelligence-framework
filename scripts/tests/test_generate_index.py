#!/usr/bin/env python3
"""Tests for eif_generate_index.py: index creation, and the three-way
honest classification (valid / schema-invalid / unparseable YAML).

Usage:
    python scripts/tests/test_generate_index.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eif_generate_index import build_index, render  # noqa: E402

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]

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

# Parses as YAML fine, but violates the schema: 'not_a_real_type' isn't in
# the type enum, and 'rejected' is only valid for type: hypothesis.
SCHEMA_INVALID_BAD_TYPE = """---
type: not_a_real_type
status: validated
scope: project
evidence: OBSERVED
source: code
created: 2026-07-15
---

# Schema-invalid: bad type enum
"""

SCHEMA_INVALID_REJECTED_NOT_HYPOTHESIS = """---
type: fact
status: rejected
scope: project
evidence: OBSERVED
source: code
created: 2026-07-15
---

# Schema-invalid: rejected on a non-hypothesis
"""


def check(name: str, condition: bool, detail: str = "") -> bool:
    condition = bool(condition)
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
        (root / "invalid").mkdir()
        (root / "invalid" / "BAD-TYPE.md").write_text(SCHEMA_INVALID_BAD_TYPE, encoding="utf-8")
        (root / "invalid" / "REJECTED-NOT-HYP.md").write_text(SCHEMA_INVALID_REJECTED_NOT_HYPOTHESIS, encoding="utf-8")

        # --- Without --framework-root: schema checking is off, schema-invalid
        # artifacts pass through as if valid (a real limitation, not hidden).
        rows_no_schema, malformed_no_schema, invalid_no_schema = build_index(root, framework_root=None)
        results.append(check(
            "without framework-root, schema-invalid artifacts are NOT flagged (documented limitation)",
            invalid_no_schema == [], str(invalid_no_schema),
        ))
        results.append(check(
            "without framework-root, unparseable YAML is still caught (that check doesn't need a schema)",
            len(malformed_no_schema) == 2, f"got {len(malformed_no_schema)}",
        ))
        results.append(check(
            "without framework-root, schema-invalid rows fall into the valid bucket (4 = 2 real + 2 undetected)",
            len(rows_no_schema) == 4, f"got {len(rows_no_schema)}",
        ))

        # --- With --framework-root: three-way honest classification. ---
        rows, malformed, schema_invalid = build_index(root, framework_root=FRAMEWORK_ROOT)
        results.append(check("index creation: 2 genuinely valid artifacts indexed", len(rows) == 2, f"got {len(rows)}"))
        results.append(check("unparseable-YAML detection: 2 files excluded, not crashed", len(malformed) == 2, f"got {len(malformed)}"))
        results.append(check("schema-invalid detection: 2 files caught (distinct from unparseable)", len(schema_invalid) == 2, f"got {len(schema_invalid)}"))

        schema_invalid_paths = {r["path"] for r in schema_invalid}
        results.append(check("schema-invalid set is exactly the bad-type and bad-rejected files, not the broken-YAML ones",
                             schema_invalid_paths == {"invalid/BAD-TYPE.md", "invalid/REJECTED-NOT-HYP.md"},
                             str(schema_invalid_paths)))
        results.append(check("schema-invalid rows carry real jsonschema error messages, not just a boolean",
                             all(r.get("schema_errors") for r in schema_invalid)))

        types_found = {r["type"] for r in rows}
        results.append(check("indexed rows carry correct frontmatter type", types_found == {"fact", "rule"}, str(types_found)))

        rendered = render(rows, malformed, schema_invalid, root)
        results.append(check("rendered index lists both valid artifacts", "facts/FACT-0001.md" in rendered and "rules/RULE-0001.md" in rendered))
        results.append(check("rendered index reports unparseable files under their own heading", "Excluded (unparseable YAML frontmatter)" in rendered and "NO-FRONTMATTER.md" in rendered))
        results.append(check("rendered index reports schema-invalid files under a DIFFERENT heading", "Excluded (schema-invalid frontmatter)" in rendered and "BAD-TYPE.md" in rendered))

    passed = sum(results)
    print(f"\ntest_generate_index: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
