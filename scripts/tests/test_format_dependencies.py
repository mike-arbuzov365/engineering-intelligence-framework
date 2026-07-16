#!/usr/bin/env python3
"""Proves the pinned jsonschema format-validation extra actually covers
every JSON Schema `format` value EIF's own schemas declare - not by
trusting a comment, but by reading core/schemas/*.schema.json directly and
checking jsonschema.FormatChecker's live registration plus real positive/
negative validation for each format found.

Also proves requirements.txt pins the non-GPL extra (`format-nongpl`, not
`format`) - a static text check, independent of whatever happens to already
be installed in the current environment (a stale local dev environment
that previously installed the GPL `format` extra will still have `rfc3987`
sitting in site-packages even after this change, since pip does not
uninstall packages an updated extras spec no longer requires - that is an
environment-hygiene fact, not something this test can or should assert
against; a fresh CI runner or a clean venv is unaffected).

Usage:
    python scripts/tests/test_format_dependencies.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = FRAMEWORK_ROOT / "core" / "schemas"
REQUIREMENTS_TXT = FRAMEWORK_ROOT / "scripts" / "requirements.txt"


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def find_declared_formats(schemas_dir: Path) -> set[str]:
    """Every distinct "format": "..." value used anywhere in a canonical
    schema file, found by walking the parsed JSON structure (not a text
    regex) so a value that happens to be a property named "format" but
    isn't a JSON Schema format-assertion keyword can't produce a false
    positive - though for these three schemas the two coincide."""
    formats: set[str] = set()
    for schema_file in sorted(schemas_dir.glob("*.schema.json")):
        data = json.loads(schema_file.read_text(encoding="utf-8"))
        _walk(data, formats)
    return formats


def _walk(node: object, formats: set[str]) -> None:
    if isinstance(node, dict):
        fmt = node.get("format")
        if isinstance(fmt, str):
            formats.add(fmt)
        for value in node.values():
            _walk(value, formats)
    elif isinstance(node, list):
        for item in node:
            _walk(item, formats)


# One realistic valid + one realistic invalid instance per format this
# repo's schemas are known to use. Extending find_declared_formats() to
# report a format not listed here fails loudly (see main()), rather than
# silently skipping the functional check for it.
KNOWN_CASES: dict[str, tuple[str, str]] = {
    "date": ("2026-07-16", "not-a-date"),
    "date-time": ("2026-07-16T21:00:00Z", "not-a-datetime"),
    "uri": ("https://github.com/mike-arbuzov365/engineering-intelligence-framework", "not a valid uri with spaces"),
}


def main() -> int:
    results: list[bool] = []

    declared = find_declared_formats(SCHEMAS_DIR)
    results.append(check(
        "at least one schema declares a format (sanity check the walk itself works)",
        len(declared) > 0,
        f"found: {sorted(declared)}",
    ))

    unknown = declared - KNOWN_CASES.keys()
    results.append(check(
        f"every declared format has a known positive/negative test case ({sorted(declared)})",
        not unknown,
        f"no test case for: {sorted(unknown)} - add one to KNOWN_CASES before trusting coverage",
    ))

    req_text = REQUIREMENTS_TXT.read_text(encoding="utf-8")
    results.append(check(
        "requirements.txt pins jsonschema[format-nongpl] (not the GPL-pulling [format] extra)",
        bool(re.search(r"jsonschema\[format-nongpl\]==", req_text)),
        req_text,
    ))
    results.append(check(
        "requirements.txt does not also pin the plain jsonschema[format] extra",
        not re.search(r"jsonschema\[format\]==", req_text),
    ))

    from jsonschema import Draft202012Validator

    for fmt in sorted(declared & KNOWN_CASES.keys()):
        valid_instance, invalid_instance = KNOWN_CASES[fmt]
        schema = {"type": "string", "format": fmt}
        validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)

        valid_errors = list(validator.iter_errors(valid_instance))
        results.append(check(
            f"format={fmt}: a well-formed instance passes ({valid_instance!r})",
            len(valid_errors) == 0,
            f"unexpected errors: {valid_errors}",
        ))

        invalid_errors = list(validator.iter_errors(invalid_instance))
        results.append(check(
            f"format={fmt}: a malformed instance is rejected, not silently accepted ({invalid_instance!r})",
            len(invalid_errors) > 0,
            "format checker did not register / silently no-op'd - the extra may be missing its dependency",
        ))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_format_dependencies: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
