#!/usr/bin/env python3
"""Validate EIF artifacts against their JSON Schemas.

Two modes:

  Knowledge frontmatter (default): validates the YAML frontmatter of
  Markdown knowledge artifacts against
  core/schemas/knowledge-frontmatter.schema.json.

  --config PATH: validates a single YAML file (typically .eif/config.yaml
  or .eif/config.yaml.example) against core/schemas/eif-config.schema.json.

Requires PyYAML and jsonschema[format] - see requirements.txt and
scripts/README.md#dependency-update-ownership for the pinned versions and
install command.

Framework root vs. instance root: schemas always come from
--framework-root (where core/schemas/ lives - this framework's own
checkout). The files being validated come from --instance-root, which can
be a *different* directory - a project instance does not need to vendor or
copy the framework source to be validated against it. Both default to the
current working directory for the common case of validating this
repository against itself.

Usage:
    python scripts/eif_validate_frontmatter.py [--framework-root PATH] [--instance-root PATH] [PATTERN ...]
    python scripts/eif_validate_frontmatter.py --framework-root PATH --config /path/to/.eif/config.yaml

Default PATTERN (frontmatter mode) is every core/ontology/*.md and
core/policies/*.md file under --instance-root.
Exit code 1 if any file fails validation, or if PyYAML/jsonschema are not
installed, or if the schema itself fails check_schema().
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "eif-validate: PyYAML is required. Install with: "
        "pip install -r scripts/requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(1)

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import SchemaError
except ImportError:
    print(
        "eif-validate: jsonschema is required. Install with: "
        "pip install -r scripts/requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(1)

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def load_schema(path: Path) -> dict:
    schema = json.loads(path.read_text(encoding="utf-8"))
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as e:
        print(f"eif-validate: schema itself is invalid: {path}\n  {e}", file=sys.stderr)
        raise SystemExit(1)
    return schema


def _normalize_yaml_scalars(value):
    """PyYAML auto-types unquoted YYYY-MM-DD scalars as datetime.date (and
    YYYY-MM-DD HH:MM:SS as datetime.datetime) per the YAML 1.1 spec - JSON
    Schema has no date type, only string+format:date, so normalize both to
    ISO-format strings before validation. This keeps frontmatter authoring
    ergonomic (no need to quote every date) while still getting real
    format:date validation on the resulting string.
    """
    if isinstance(value, dict):
        return {k: _normalize_yaml_scalars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_yaml_scalars(v) for v in value]
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    return value


def extract_frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    return _normalize_yaml_scalars(yaml.safe_load(m.group(1)) or {})


def validate_one(instance: dict, schema: dict, label: str) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    return [f"{'.'.join(str(p) for p in e.path) or '(root)'}: {e.message}" for e in errors]


def validate_frontmatter_mode(framework_root: Path, instance_root: Path, patterns: list[str]) -> int:
    schema_path = framework_root / "core" / "schemas" / "knowledge-frontmatter.schema.json"
    schema = load_schema(schema_path)

    patterns = patterns or ["core/ontology/*.md", "core/policies/*.md"]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(sorted(Path(p) for p in glob.glob(str(instance_root / pattern))))

    if not files:
        print("eif-validate: no files matched", file=sys.stderr)
        return 1

    total_errors = 0
    for f in files:
        rel = f.relative_to(instance_root) if f.is_relative_to(instance_root) else f
        fm = extract_frontmatter(f)
        if fm is None:
            print(f"FAIL {rel}: no frontmatter block found")
            total_errors += 1
            continue
        errors = validate_one(fm, schema, str(rel))
        if errors:
            total_errors += len(errors)
            print(f"FAIL {rel}:")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"ok   {rel}")

    print(f"eif-validate: {len(files)} file(s), {total_errors} error(s)")
    return 1 if total_errors else 0


def validate_config_mode(framework_root: Path, config_path: Path) -> int:
    schema_path = framework_root / "core" / "schemas" / "eif-config.schema.json"
    schema = load_schema(schema_path)

    if not config_path.exists():
        print(f"eif-validate: config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        instance = _normalize_yaml_scalars(yaml.safe_load(config_path.read_text(encoding="utf-8")) or {})
    except yaml.YAMLError as e:
        print(f"FAIL {config_path}: invalid YAML: {e}")
        return 1

    errors = validate_one(instance, schema, str(config_path))
    if errors:
        print(f"FAIL {config_path}:")
        for e in errors:
            print(f"  - {e}")
        print(f"eif-validate: 1 file, {len(errors)} error(s)")
        return 1

    print(f"ok   {config_path}")
    print("eif-validate: 1 file, 0 error(s)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--framework-root", default=".", help="Where core/schemas/ lives (this framework's checkout). Default: current directory.")
    ap.add_argument("--instance-root", default=None, help="Where the artifacts being validated live. Default: same as --framework-root.")
    ap.add_argument("--config", default=None, help="Validate this single YAML file against the .eif/config.yaml schema instead of frontmatter mode.")
    ap.add_argument("patterns", nargs="*", help="Glob pattern(s) relative to --instance-root (frontmatter mode only)")
    args = ap.parse_args()

    framework_root = Path(args.framework_root).resolve()
    instance_root = Path(args.instance_root).resolve() if args.instance_root else framework_root

    if args.config:
        return validate_config_mode(framework_root, Path(args.config).resolve())
    return validate_frontmatter_mode(framework_root, instance_root, args.patterns)


if __name__ == "__main__":
    raise SystemExit(main())
