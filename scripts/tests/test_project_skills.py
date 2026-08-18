#!/usr/bin/env python3
"""Project-owned skill discovery and validation.

`eifctl skills check` used to scan only the framework's own `skills/` and
`professional-profiles/*/skills/`. A project instance keeping its own
canonical skills had no way to run the contract checker against them, so
admission gate 6 in docs/reference/external-skill-admission.md ("passes
local eifctl skills check") was unreachable for exactly the artifacts most
likely to come from outside.

These checks cover the discovery rules and the two shape allowances a
self-contained project skill needs.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from engineering_intelligence_framework.commands import skills  # noqa: E402

PASSED = 0
TOTAL = 0


def check(label: str, condition: bool) -> None:
    global PASSED, TOTAL
    TOTAL += 1
    if condition:
        PASSED += 1
        print(f"PASS {label}")
    else:
        print(f"FAIL {label}")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


MINIMAL_CONTRACT = """schema_version: 1
skill:
  name: {name}
  profile: {profile}
  canonical_workflow: {canonical}
triggers:
  positive:
  - id: yes-case
    prompt: Do the thing this skill is for.
  negative:
  - id: no-case
    prompt: Do something this skill must refuse.
references:
  required:
  - {canonical}
evidence:
  required:
  - grounded evidence sentence
commands:
  required: []
stop_conditions:
  required:
  - stop before an owner decision
forbidden_behavior:
  required:
  - never invent a measurement
assertions:
  manifest_contains:
  - self-contained project skill
  canonical_contains:
  - self-contained project skill
  manifest_not_contains:
  - TODO
supporting_files:
  scripts: []
  references: []
provenance:
  origin: repository
  source_revision: repository
  license: repository
  external_import: false
  surfaces_reviewed:
    scripts: true
    references: true
    secrets: true
    network: true
    install: true
    permissions: true
evaluation:
  deterministic: required
  behavioral: required_for_material_semantic_change
"""

SELF_CANONICAL_MANIFEST = """---
name: {name}
description: A self-contained project skill that is its own canonical workflow.
---

# {name}

This skill carries its own workflow rather than pointing at a playbook.
It states a grounded evidence sentence so the contract's evidence token
has something to match against in the manifest body itself.

It must stop before an owner decision.
It must never invent a measurement it did not take.
"""

GENERATED_LOADER = """---
name: {name}
description: Generated loader, not a canonical skill.
---

<!-- eif:generated-skill-loader -->

Read the pinned source instead.
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        project = Path(raw) / "project"

        # A self-contained skill under docs/skills.
        name = "audit-something"
        write(
            project / "docs" / "skills" / name / "SKILL.md",
            SELF_CANONICAL_MANIFEST.format(name=name),
        )
        write(
            project / "docs" / "skills" / name / "tests" / "contract.yaml",
            MINIMAL_CONTRACT.format(
                name=name,
                profile="product-code",
                canonical=f"docs/skills/{name}/SKILL.md",
            ),
        )

        # A generated loader mirror that must never be validated as a skill.
        write(
            project / ".claude" / "skills" / name / "SKILL.md",
            GENERATED_LOADER.format(name=name),
        )
        # A loader sitting in a real skills root must also be skipped.
        write(
            project / "skills" / "mirrored-loader" / "SKILL.md",
            GENERATED_LOADER.format(name="mirrored-loader"),
        )

        records = skills.discover_project_skill_records(project)
        found = sorted(record.name for record in records)
        check("discovers a canonical project skill under docs/skills", found == [name])
        check("skips generated loader directories", "mirrored-loader" not in found)
        check(
            "does not reach agent discovery directories such as .claude/skills",
            len(records) == 1,
        )
        check(
            "takes the profile the contract declares, not a hardcoded label",
            records and records[0].profile == "product-code",
        )

        _, errors = skills.check_project(project)
        joined = " | ".join(errors)
        check(
            "a self-canonical skill is not reported as duplicating itself",
            "duplicates canonical workflow prose" not in joined,
        )
        check(
            "a self-canonical skill need not list itself as a required reference",
            "canonical workflow must be a required reference" not in joined,
        )
        check(
            "a self-canonical skill need not name its own filename in its body",
            "does not point to canonical workflow" not in joined,
        )
        check("the valid fixture produces no errors at all", errors == [])

        # A project with no skills of its own is normal, not a failure.
        empty = Path(raw) / "empty"
        empty.mkdir()
        empty_records, empty_errors = skills.check_project(empty)
        check("a project with no skills reports no records", empty_records == [])
        check("a project with no skills reports no errors", empty_errors == [])

        # A skill missing its contract is still reported.
        missing = Path(raw) / "missing"
        write(
            missing / "skills" / "no-contract" / "SKILL.md",
            SELF_CANONICAL_MANIFEST.format(name="no-contract"),
        )
        _, missing_errors = skills.check_project(missing)
        check(
            "a project skill without a contract fixture fails",
            any("missing local contract fixture" in error for error in missing_errors),
        )

    print(f"EIF-RESULT: passed={PASSED} total={TOTAL}")
    print(f"\ntest_project_skills: {PASSED}/{TOTAL} passed")
    return 0 if PASSED == TOTAL else 1


if __name__ == "__main__":
    raise SystemExit(main())
