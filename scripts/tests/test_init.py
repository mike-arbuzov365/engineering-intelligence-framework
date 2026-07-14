#!/usr/bin/env python3
"""Tests for eif_init.py: config creation+validation, framework-root vs.
instance-root separation, and reproduction from a clean temporary
directory outside the framework checkout entirely.

Usage:
    python scripts/tests/test_init.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eif_init import write_config, generate_instructions, generate_index  # noqa: E402
from eif_validate_frontmatter import validate_config_mode  # noqa: E402

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def main() -> int:
    results = []

    # tempfile.gettempdir() is intentionally outside FRAMEWORK_ROOT - this
    # is the "clean checkout, instance not vendored into the framework"
    # scenario the framework-root/instance-root split exists for.
    with tempfile.TemporaryDirectory() as tmp:
        instance_path = Path(tmp) / "some-other-project"
        instance_path.mkdir()

        results.append(check(
            "instance-root is genuinely outside framework-root",
            not str(instance_path).startswith(str(FRAMEWORK_ROOT)),
            f"{instance_path} vs {FRAMEWORK_ROOT}",
        ))

        config_path = write_config(instance_path, "some-other-project", "uk", "0.1.0-dev")
        results.append(check("config creation: .eif/config.yaml written", config_path.exists()))

        rc = validate_config_mode(FRAMEWORK_ROOT, config_path)
        results.append(check(
            "config validation: generated config validates against the framework's schema "
            "without vendoring the framework into the instance",
            rc == 0,
        ))

        instructions_path = generate_instructions(FRAMEWORK_ROOT, instance_path)
        results.append(check(
            "agent instructions generated into the instance, sourced from the framework",
            instructions_path.exists() and instructions_path.read_text(encoding="utf-8") ==
            (FRAMEWORK_ROOT / "templates" / "agent-instructions.md").read_text(encoding="utf-8"),
        ))

        knowledge_root = instance_path / "knowledge"
        knowledge_root.mkdir()
        (knowledge_root / "FACT-0001.md").write_text(
            "---\ntype: fact\nstatus: validated\nscope: project\nevidence: OBSERVED\n"
            "source: code\ncreated: 2026-07-15\n---\n\n# A fact\n\nBody.\n",
            encoding="utf-8",
        )
        index_path, count = generate_index(instance_path)
        results.append(check("knowledge index creation via eif_init", index_path.exists() and count == 1, f"count={count}"))

    # Broken config: schema_version missing -> must fail validation, not
    # silently pass.
    with tempfile.TemporaryDirectory() as tmp2:
        bad_config = Path(tmp2) / "bad-config.yaml"
        bad_config.write_text("framework:\n  version: 0.1.0-dev\n", encoding="utf-8")
        rc = validate_config_mode(FRAMEWORK_ROOT, bad_config)
        results.append(check("malformed config is rejected, not silently accepted", rc != 0))

    passed = sum(results)
    print(f"\ntest_init: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
