#!/usr/bin/env python3
"""Committed example demo fixtures (examples/*/) stay byte-identical to what
the CURRENT shared template (templates/agent-instructions.md) actually
generates for that fixture's own recorded config - not a one-time snapshot
that can silently rot the next time the template changes.

Found and fixed while adding the Codex adapter (active-entrypoint
correctness round): templates/agent-instructions.md hardcoded a literal
"CLAUDE.md" reference until a fourth placeholder ({entrypoint_name}) was
added to fix it for non-Claude-Code adapters - examples/demo-cursor-
workspace's already-committed .mdc fixture still carried the stale text,
because nothing re-derived and compared it against the live template. This
suite closes that gap generically (every example fixture with a committed
.eif/config.yaml, not just the Cursor one) by regenerating each fixture's
managed block in memory from its own recorded config and diffing against
the committed file. Read-only - never writes anything itself; a failure
here means "run eif_init.py against this fixture (a routine upgrade, no
flags needed) and commit the result", not "this test writes the fix".

Usage:
    python scripts/tests/test_demo_fixtures_fresh.py
"""
from __future__ import annotations

import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = FRAMEWORK_ROOT / "examples"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eif_init  # noqa: E402
from eif_adapters import entrypoint_for  # noqa: E402

try:
    import yaml
except ImportError:
    print("test_demo_fixtures_fresh: PyYAML is required.", file=sys.stderr)
    raise SystemExit(1)


def check(name: str, cond: bool, detail: str = "") -> bool:
    status = "PASS" if cond else "FAIL"
    print(f"{status} {name}" + (f": {detail}" if detail and not cond else ""))
    return cond


def _default_index_path(knowledge_root: str) -> str:
    return f"{knowledge_root.rstrip('/')}/index.md"


def main() -> int:
    results: list[bool] = []

    fixture_dirs = sorted(
        d for d in EXAMPLES.iterdir()
        if d.is_dir() and (d / ".eif" / "config.yaml").is_file()
    )
    results.append(check(
        "found at least one committed example fixture with .eif/config.yaml",
        len(fixture_dirs) > 0, str(EXAMPLES),
    ))

    for fixture_dir in fixture_dirs:
        name = fixture_dir.relative_to(EXAMPLES).as_posix()
        config = yaml.safe_load((fixture_dir / ".eif" / "config.yaml").read_text(encoding="utf-8"))
        adapter = (config.get("adapter") or {}).get("name")
        adoption_mode = (config.get("adoption") or {}).get("mode", "greenfield")
        knowledge = config.get("knowledge") or {}
        knowledge_root = knowledge.get("root", "knowledge")
        knowledge_index_path = knowledge.get("index_path") or _default_index_path(knowledge_root)
        entrypoint = entrypoint_for(adapter)
        entry_path = fixture_dir / entrypoint

        if not check(f"{name}: recorded entrypoint {entrypoint} exists on disk", entry_path.is_file()):
            continue

        committed_text = entry_path.read_text(encoding="utf-8")
        has_block = eif_init.EIF_BEGIN in committed_text and eif_init.EIF_END in committed_text
        if not check(f"{name}: committed {entrypoint} has a well-formed EIF-managed block", has_block):
            continue
        committed_block = committed_text[
            committed_text.index(eif_init.EIF_BEGIN):
            committed_text.index(eif_init.EIF_END) + len(eif_init.EIF_END)
        ]

        fresh_block = eif_init._managed_block(
            FRAMEWORK_ROOT, knowledge_root, knowledge_index_path, adoption_mode, entrypoint,
        )

        results.append(check(
            f"{name}: committed {entrypoint}'s managed block matches templates/agent-instructions.md "
            f"as rendered right now for this fixture's own recorded config",
            committed_block == fresh_block,
            f"drifted - regenerate via: python scripts/eif_init.py --framework-root . "
            f"--instance-path examples/{name} (routine upgrade, no flags needed) and commit the result",
        ))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_demo_fixtures_fresh: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
