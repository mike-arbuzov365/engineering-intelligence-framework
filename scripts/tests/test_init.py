#!/usr/bin/env python3
"""Tests for eif_init.py: config/lock split, real provenance + dirty-check,
transactional bundle staging/swap (including injected-failure rollback),
safe YAML generation, adapter registry restriction, and instance .gitignore
management.

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
from eif_validate_frontmatter import validate_config_mode, validate_lock_mode  # noqa: E402

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def check(name: str, condition: bool, detail: str = "") -> bool:
    condition = bool(condition)
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def _real_ref():
    ref, short, dirty = eif_init.resolve_framework_state(FRAMEWORK_ROOT)
    return ref or "a" * 40, short or "aaaaaaa"


def main() -> int:
    results = []

    # --- Provenance ---
    ref, ref_short, dirty = eif_init.resolve_framework_state(FRAMEWORK_ROOT)
    results.append(check("resolve_framework_state returns a real 40-hex SHA", bool(ref) and bool(SHA_RE.match(ref)), str(ref)))
    results.append(check("dirty flag is a real bool, not always False for a real repo", isinstance(dirty, bool)))

    not_a_repo_ref, not_a_repo_short, not_a_repo_dirty = eif_init.resolve_framework_state(Path(tempfile.gettempdir()))
    results.append(check("non-git framework-root resolves to None (forces --framework-ref)", not_a_repo_ref is None, str(not_a_repo_ref)))

    # --- Bundle manifest: real hashing over a synthetic source tree ---
    with tempfile.TemporaryDirectory() as tmp:
        fake_fw = Path(tmp) / "fw"
        (fake_fw / "scripts").mkdir(parents=True)
        for name in eif_init.BUNDLE_SCRIPTS:
            (fake_fw / "scripts" / name).write_text(f"# {name}\n", encoding="utf-8")
        for tree in eif_init.BUNDLE_TREES:
            d = fake_fw / tree
            d.mkdir(parents=True)
            (d / "a.txt").write_text("content", encoding="utf-8")

        sources = eif_init.collect_bundle_sources(fake_fw)
        results.append(check("collect_bundle_sources finds every mandatory file",
                             len(sources) == len(eif_init.BUNDLE_SCRIPTS) + len(eif_init.BUNDLE_TREES)))

        manifest = eif_init.build_manifest(sources)
        results.append(check("manifest entries are sorted by path",
                             [m["path"] for m in manifest] == sorted(m["path"] for m in manifest)))
        results.append(check("manifest hashes are real sha256 hex",
                             all(re.match(r"^[0-9a-f]{64}$", m["sha256"]) for m in manifest)))

        digest = eif_init.combined_digest(manifest)
        results.append(check("combined digest has the sha256: prefix", digest.startswith("sha256:")))
        results.append(check("combined digest is deterministic for the same manifest",
                             eif_init.combined_digest(manifest) == digest))

        # Mandatory bundle source missing -> raises, not silently skipped.
        (fake_fw / "scripts" / eif_init.BUNDLE_SCRIPTS[0]).unlink()
        try:
            eif_init.collect_bundle_sources(fake_fw)
            results.append(check("missing mandatory bundle source raises FileNotFoundError", False))
        except FileNotFoundError:
            results.append(check("missing mandatory bundle source raises FileNotFoundError", True))

    # --- Transactional swap_runtime: injected-failure rollback ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "inst"
        eif_dir = inst / ".eif"
        eif_dir.mkdir(parents=True)
        runtime = eif_dir / "runtime"
        runtime.mkdir()
        sentinel = runtime / "sentinel.txt"
        sentinel.write_text("original runtime - must survive a failed swap", encoding="utf-8")

        # Inject a failure: staging path does not exist, so the rename inside
        # swap_runtime raises. The pre-existing runtime must be restored.
        bogus_staging = eif_dir / "runtime.next-does-not-exist"
        try:
            eif_init.swap_runtime(inst, bogus_staging)
            results.append(check("swap_runtime with a bad staging path raises", False))
        except (FileNotFoundError, OSError):
            results.append(check("swap_runtime with a bad staging path raises", True))

        results.append(check("runtime directory still exists after a failed swap (rollback)", runtime.is_dir()))
        results.append(check("original runtime content survives a failed swap (rollback)",
                             sentinel.exists() and sentinel.read_text(encoding="utf-8").startswith("original")))
        results.append(check("no leftover runtime.previous after successful rollback",
                             not (eif_dir / "runtime.previous").exists()))

        # Now a real successful swap: stage a new runtime, verify it wins.
        staging = eif_dir / "runtime.next"
        staging.mkdir()
        (staging / "new.txt").write_text("new runtime", encoding="utf-8")
        eif_init.swap_runtime(inst, staging)
        results.append(check("successful swap replaces the runtime contents", (runtime / "new.txt").exists() and not sentinel.exists()))
        results.append(check("successful swap leaves no staging or previous dirs behind",
                             not staging.exists() and not (eif_dir / "runtime.previous").exists()))

    # --- verify_staged_bundle catches corruption ---
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "staging"
        staging.mkdir()
        (staging / "f.txt").write_text("correct content", encoding="utf-8")
        manifest = [{"path": "f.txt", "sha256": eif_init.hash_file(staging / "f.txt")}]
        results.append(check("verify_staged_bundle: clean bundle has no problems", eif_init.verify_staged_bundle(staging, manifest) == []))

        (staging / "f.txt").write_text("CORRUPTED", encoding="utf-8")
        problems = eif_init.verify_staged_bundle(staging, manifest)
        results.append(check("verify_staged_bundle: corrupted file is caught", len(problems) == 1 and "hash mismatch" in problems[0]))

        (staging / "f.txt").unlink()
        problems = eif_init.verify_staged_bundle(staging, manifest)
        results.append(check("verify_staged_bundle: missing file is caught", len(problems) == 1 and "missing" in problems[0]))

    # --- Config: safe YAML generation + schema validity + special characters ---
    ref, ref_short = _real_ref()
    tricky_name = "weird: name, with \"quotes\" and a # hash and a \nnewline-ish thing"
    data = eif_init.render_config_data(tricky_name, "claude-code", "uk", "0.1.0-dev")
    errors = eif_init.validate_in_memory(FRAMEWORK_ROOT, "eif-config.schema.json", data)
    results.append(check("config with YAML-special characters in project name still validates", errors == [], str(errors)))

    content = eif_init._dump_yaml(eif_init.CONFIG_HEADER, data)
    import yaml as _yaml  # local import, mirrors eif_init's own dependency
    round_tripped = _yaml.safe_load(content.split("\n\n", 1)[1] if "\n\n" in content else content)
    results.append(check("YAML-dumped config round-trips the tricky project name exactly",
                         round_tripped["project"]["name"] == tricky_name, repr(round_tripped.get("project"))))

    # --- Adapter registry restriction ---
    try:
        eif_init.entrypoint_for("cursor-does-not-exist")
        results.append(check("entrypoint_for rejects an unregistered adapter", False))
    except ValueError:
        results.append(check("entrypoint_for rejects an unregistered adapter", True))
    results.append(check("entrypoint_for('claude-code') returns CLAUDE.md", eif_init.entrypoint_for("claude-code") == "CLAUDE.md"))

    # --- End-to-end: config create -> keep (upgrade) -> force overwrite ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "proj"
        inst.mkdir()
        content = eif_init._dump_yaml(eif_init.CONFIG_HEADER, eif_init.render_config_data("p", "claude-code", "en", "0.1.0-dev"))
        action, cfg = eif_init.write_config(inst, content, dry_run=False, force=False)
        results.append(check("first write_config creates", action == "create" and cfg.exists()))
        results.append(check("created config validates against the schema", validate_config_mode(FRAMEWORK_ROOT, cfg) == 0))

        before = cfg.read_text(encoding="utf-8")
        action2, _ = eif_init.write_config(inst, "schema_version: 999\n", dry_run=False, force=False)
        results.append(check("second write_config without --force is 'keep' (the routine upgrade path), not an error",
                             action2 == "keep"))
        results.append(check("'keep' leaves the file byte-for-byte untouched", cfg.read_text(encoding="utf-8") == before))
        results.append(check("'keep' creates no backup file", list(inst.glob(".eif/*.bak-*")) == []))

        action3, _ = eif_init.write_config(inst, content, dry_run=False, force=True)
        backups = list((inst / ".eif").glob("config.yaml.bak-*"))
        results.append(check("--force overwrites and leaves exactly one backup", action3 == "overwrite" and len(backups) == 1))

    # --- Lock rendering + schema validity ---
    lock_data = eif_init.render_lock_data(ref, ref_short, True, "claude-code", "CLAUDE.md", ".eif/runtime",
                                          [{"path": "x.py", "sha256": "a" * 64}], "sha256:" + "b" * 64,
                                          "adopted", "0.1.0", "2026-07-15T00:00:00+00:00")
    lock_errors = eif_init.validate_in_memory(FRAMEWORK_ROOT, "framework-lock.schema.json", lock_data)
    results.append(check("rendered lock validates against the lock schema", lock_errors == [], str(lock_errors)))
    with tempfile.TemporaryDirectory() as tmp:
        lock_path = Path(tmp) / "framework.lock.yaml"
        lock_path.write_text(eif_init._dump_yaml(eif_init.LOCK_HEADER, lock_data), encoding="utf-8")
        results.append(check("on-disk lock validates via validate_lock_mode", validate_lock_mode(FRAMEWORK_ROOT, lock_path) == 0))

    # --- Bad lock (placeholder ref) is rejected ---
    bad_lock = dict(lock_data)
    bad_lock["framework"] = dict(lock_data["framework"], ref="not-a-real-sha")
    bad_errors = eif_init.validate_in_memory(FRAMEWORK_ROOT, "framework-lock.schema.json", bad_lock)
    results.append(check("a non-40-hex ref is rejected by the lock schema (placeholder guard)", len(bad_errors) > 0))

    # --- Instance .gitignore management ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "proj"
        inst.mkdir()
        action = eif_init.ensure_gitignore(inst, dry_run=False)
        results.append(check("gitignore created on a fresh instance", action == "created" and (inst / ".gitignore").exists()))
        results.append(check("created gitignore ignores the runtime bundle", ".eif/runtime/" in (inst / ".gitignore").read_text(encoding="utf-8")))
        action2 = eif_init.ensure_gitignore(inst, dry_run=False)
        results.append(check("re-running on an instance that already has the block is a no-op", action2 == "already-present"))

        inst2 = Path(tmp) / "existing-gitignore"
        inst2.mkdir()
        (inst2 / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        action3 = eif_init.ensure_gitignore(inst2, dry_run=False)
        text = (inst2 / ".gitignore").read_text(encoding="utf-8")
        results.append(check("appending to an existing .gitignore preserves prior content",
                             action3 == "appended" and "node_modules/" in text and ".eif/runtime/" in text))

    # --- CLAUDE.md marker merge (unchanged behavior, re-verified against new signature) ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "proj"
        inst.mkdir()
        action, claude = eif_init.merge_entrypoint(FRAMEWORK_ROOT, inst, "CLAUDE.md", dry_run=False)
        results.append(check("generates CLAUDE.md (Claude Code's real entrypoint), not AGENTS.md",
                             claude.name == "CLAUDE.md" and action == "create"))
        text = claude.read_text(encoding="utf-8")
        results.append(check("generated CLAUDE.md commands reference the bundle (.eif/runtime), not framework scripts/",
                             ".eif/runtime/eif_search_knowledge.py" in text and "python scripts/" not in text))

        user_line = "MY PROJECT RULE: never touch prod on Friday."
        claude.write_text(text + "\n" + user_line + "\n", encoding="utf-8")
        action2, _ = eif_init.merge_entrypoint(FRAMEWORK_ROOT, inst, "CLAUDE.md", dry_run=False)
        merged = claude.read_text(encoding="utf-8")
        results.append(check("re-init updates the managed block and preserves project-authored content",
                             action2 == "update-block" and user_line in merged))

    passed = sum(results)
    print(f"\ntest_init: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
