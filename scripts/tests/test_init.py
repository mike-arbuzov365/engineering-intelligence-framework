#!/usr/bin/env python3
"""Tests for eif_init.py: real framework provenance, self-contained runtime
bundle, correct adapter entrypoint, and non-destructive initialization
(conflict guard, --force backup, dry-run, CLAUDE.md marker merge).

Usage:
    python scripts/tests/test_init.py
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eif_init  # noqa: E402
from eif_validate_frontmatter import validate_config_mode  # noqa: E402

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def _render(ref="a" * 40, short="aaaaaaa", name="p", locale="en", adapter="claude-code",
            migration="greenfield", version="0.1.0-dev"):
    return eif_init.render_config(ref, short, name, locale, adapter, migration, version)


def main() -> int:
    results = []

    # 1. Real provenance: framework checkout resolves to a real 40-hex SHA.
    ref, short = eif_init.resolve_framework_ref(FRAMEWORK_ROOT)
    results.append(check("resolve_framework_ref returns a real 40-hex SHA (not a placeholder)",
                         bool(ref) and bool(SHA_RE.match(ref)), str(ref)))

    # 2. Rendered config carries the real ref and validates against the schema.
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "proj"
        inst.mkdir()
        content = _render(ref=ref or "a" * 40, short=short or "aaaaaaa", locale="uk")
        results.append(check("rendered config embeds the resolved ref", (ref or "") in content))
        results.append(check("rendered config's ref is not a placeholder token",
                             "<commit" not in content and ("0" * 40) not in content and "ref: main" not in content))
        action, cfg = eif_init.write_config(inst, content, dry_run=False, force=False)
        results.append(check("write_config creates config on a clean instance", action == "create" and cfg.exists()))
        results.append(check("generated config validates against the framework schema",
                             validate_config_mode(FRAMEWORK_ROOT, cfg) == 0))

        # 3. Non-destructive: second write without --force is a conflict, file untouched.
        cfg_before = cfg.read_text(encoding="utf-8")
        action2, _ = eif_init.write_config(inst, "schema_version: 999\n", dry_run=False, force=False)
        results.append(check("second write without --force reports conflict", action2 == "conflict"))
        results.append(check("conflicting write does not modify the existing config",
                             cfg.read_text(encoding="utf-8") == cfg_before))

        # 4. --force overwrites but backs up first.
        action3, _ = eif_init.write_config(inst, content, dry_run=False, force=True)
        backups = list((inst / ".eif").glob("config.yaml.bak-*"))
        results.append(check("--force overwrites and leaves a backup", action3 == "overwrite" and len(backups) == 1))

    # 5. dry-run writes nothing.
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "proj"
        inst.mkdir()
        action, cfg = eif_init.write_config(inst, _render(), dry_run=True, force=False)
        results.append(check("dry-run reports create but writes no file", action == "create" and not cfg.exists()))

    # 6. Runtime bundle: self-contained + generated CLAUDE.md points at it, not scripts/.
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "proj"
        inst.mkdir()
        runtime = eif_init.build_runtime_bundle(FRAMEWORK_ROOT, inst, dry_run=False)
        results.append(check("bundle contains the search script", (runtime / "eif_search_knowledge.py").exists()))
        results.append(check("bundle contains the config schema", (runtime / "core" / "schemas" / "eif-config.schema.json").exists()))
        results.append(check("bundle contains the uk locale", (runtime / "locales" / "uk" / "messages.yaml").exists()))
        results.append(check("bundle contains task-scope template", (runtime / "templates" / "task-scope.md").exists()))

        action, claude = eif_init.merge_entrypoint(FRAMEWORK_ROOT, inst, dry_run=False)
        claude_text = claude.read_text(encoding="utf-8")
        results.append(check("generates CLAUDE.md (the file Claude Code loads), not AGENTS.md",
                             claude.name == "CLAUDE.md" and action == "create"))
        results.append(check("generated CLAUDE.md commands reference the bundle (.eif/runtime), not framework scripts/",
                             ".eif/runtime/eif_search_knowledge.py" in claude_text and "python scripts/" not in claude_text))

        # 7. Marker merge is non-destructive to project-authored content.
        user_line = "MY PROJECT RULE: never touch prod on Friday."
        claude.write_text(claude_text + "\n" + user_line + "\n", encoding="utf-8")
        action2, _ = eif_init.merge_entrypoint(FRAMEWORK_ROOT, inst, dry_run=False)
        merged = claude.read_text(encoding="utf-8")
        results.append(check("re-init updates the managed block", action2 == "update-block"))
        results.append(check("re-init preserves project-authored content below the marker", user_line in merged))

        # 8. Adopting a pre-existing CLAUDE.md with no markers appends, never clobbers.
        inst2 = Path(tmp) / "existing"
        inst2.mkdir()
        (inst2 / "CLAUDE.md").write_text("# Existing project memory\n\nImportant existing rule.\n", encoding="utf-8")
        action3, claude2 = eif_init.merge_entrypoint(FRAMEWORK_ROOT, inst2, dry_run=False)
        text2 = claude2.read_text(encoding="utf-8")
        results.append(check("adopting an existing CLAUDE.md appends the block and keeps original content",
                             action3 == "append-block" and "Important existing rule." in text2 and eif_init.EIF_BEGIN in text2))

    passed = sum(results)
    print(f"\ntest_init: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
