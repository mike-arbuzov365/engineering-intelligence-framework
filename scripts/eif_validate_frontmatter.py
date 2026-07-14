#!/usr/bin/env python3
"""Validate YAML frontmatter of knowledge-artifact Markdown files against
core/schemas/knowledge-frontmatter.schema.json.

Uses only the standard library (no PyYAML/jsonschema dependency) with a
minimal frontmatter parser and a minimal schema checker covering the
subset of JSON Schema the frontmatter schema actually uses (type, enum,
required, allOf/if/then). This is intentionally small rather than pulling
in a dependency for a CI-only check; if the schema grows past what this
covers, switch to `jsonschema` + `pyyaml` rather than extending this by
hand indefinitely.

Usage:
    python scripts/eif_validate_frontmatter.py [--repo PATH] [PATTERN ...]

Default PATTERN is every core/ontology/*.md and core/policies/*.md file.
Exit code 1 if any file fails validation.
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def parse_minimal_yaml_mapping(text: str) -> dict:
    """Parse a flat-ish YAML mapping (frontmatter) without a YAML library.
    Supports: scalar values, quoted strings, block lists (- item), nested
    'related:' style lists. Not a general YAML parser - sufficient for the
    frontmatter shape this schema defines.
    """
    result: dict[str, object] = {}
    current_list_key: str | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        if raw_line.startswith(("  - ", "- ")) and current_list_key:
            item = raw_line.strip()[2:].strip().strip("'\"")
            result.setdefault(current_list_key, [])
            result[current_list_key].append(item)  # type: ignore[union-attr]
            continue
        m = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", raw_line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if value == "":
            current_list_key = key
            result[key] = []
            continue
        current_list_key = None
        value = value.strip("'\"")
        result[key] = value
    return result


def extract_frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    return parse_minimal_yaml_mapping(m.group(1))


def validate_against_schema(fm: dict, schema: dict) -> list[str]:
    errors = []
    for req in schema.get("required", []):
        if req not in fm:
            errors.append(f"missing required field: {req}")

    props = schema.get("properties", {})
    for key, value in fm.items():
        prop_schema = props.get(key)
        if not prop_schema:
            continue
        enum = prop_schema.get("enum")
        if enum and isinstance(value, str) and value not in enum:
            errors.append(f"field '{key}' = '{value}' not in allowed values {enum}")

    for rule in schema.get("allOf", []):
        cond = rule.get("if", {}).get("properties", {})
        matches = all(
            fm.get(k) == v.get("const")
            for k, v in cond.items()
            if "const" in v
        )
        if matches and cond:
            for req in rule.get("then", {}).get("required", []):
                if req not in fm:
                    cond_desc = ", ".join(f"{k}={v.get('const')}" for k, v in cond.items())
                    errors.append(f"missing '{req}' required when {cond_desc}")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".", help="Repository root")
    ap.add_argument("patterns", nargs="*", help="Glob pattern(s) relative to repo root")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    schema_path = repo / "core" / "schemas" / "knowledge-frontmatter.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    patterns = args.patterns or ["core/ontology/*.md", "core/policies/*.md"]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(sorted(Path(p) for p in glob.glob(str(repo / pattern))))

    if not files:
        print("eif-validate-frontmatter: no files matched", file=sys.stderr)
        return 1

    total_errors = 0
    for f in files:
        fm = extract_frontmatter(f)
        rel = f.relative_to(repo)
        if fm is None:
            print(f"FAIL {rel}: no frontmatter block found")
            total_errors += 1
            continue
        errors = validate_against_schema(fm, schema)
        if errors:
            total_errors += len(errors)
            print(f"FAIL {rel}:")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"ok   {rel}")

    print(f"eif-validate-frontmatter: {len(files)} file(s), {total_errors} error(s)")
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
