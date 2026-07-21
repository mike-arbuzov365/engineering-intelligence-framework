#!/usr/bin/env python3
"""Schema-first tests for optional integration provider and health contracts."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = FRAMEWORK_ROOT / "core" / "schemas"
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "integrations"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validates(schema_name: str, fixture_name: str) -> bool:
    schema = load_json(SCHEMA_ROOT / schema_name)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return not list(validator.iter_errors(load_json(FIXTURE_ROOT / fixture_name)))


def check(name: str, condition: bool) -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}")
    return condition


def main() -> int:
    results = [
        check(
            "provider manifest accepts a strict versioned behavioral contract",
            validates("integration-provider-manifest.schema.json", "provider-manifest.valid.json"),
        ),
        check(
            "provider manifest rejects unversioned and empty capability declarations",
            not validates("integration-provider-manifest.schema.json", "provider-manifest.invalid.json"),
        ),
        check(
            "health result accepts the disabled core-only state",
            validates("integration-health-result.schema.json", "health-disabled.valid.json"),
        ),
        check(
            "health result accepts compatible version plus passing required canary",
            validates("integration-health-result.schema.json", "health-healthy.valid.json"),
        ),
        check(
            "health result rejects healthy when version and required canary fail",
            not validates("integration-health-result.schema.json", "health-invalid-healthy.json"),
        ),
    ]
    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_integration_contracts: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
