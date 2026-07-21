#!/usr/bin/env python3
"""Tests for eif_verify_runtime.py (round-3 review, Finding F/D): schema
checks, manifest digest self-consistency, bundle file hash verification,
missing/unexpected file detection, config/adapter/lock/entrypoint
consistency, and marker integrity - built against a REAL instance produced
by eif_init.py, then deliberately corrupted one way at a time.

Usage:
    python scripts/tests/test_verify_runtime.py
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import os
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eif_init  # noqa: E402
import eif_verify_runtime as verify  # noqa: E402

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]


def check(name: str, condition: bool, detail: str = "") -> bool:
    condition = bool(condition)
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def _init_real_instance(inst: Path) -> None:
    ref, _short, _dirty = eif_init.resolve_framework_state(FRAMEWORK_ROOT)
    sources = eif_init.collect_bundle_sources(FRAMEWORK_ROOT)
    manifest = eif_init.build_manifest(sources)
    digest = eif_init.combined_digest(manifest)

    config_data = eif_init.render_config_data("verify-test", "claude-code", "en", "0.1.0-dev", "knowledge", "knowledge/index.md", "greenfield", True)
    (inst / ".eif").mkdir(parents=True)
    (inst / ".eif" / "config.yaml").write_text(eif_init._dump_yaml(eif_init.CONFIG_HEADER, config_data), encoding="utf-8")

    lock_data = eif_init.render_lock_data(
        "git", {"commit_sha": ref or "a" * 40, "dirty": False}, None, None, "claude-code", "CLAUDE.md",
        ".eif/runtime", manifest, digest, "greenfield", "0.1.0", "2026-07-15T00:00:00+00:00",
    )
    (inst / ".eif" / "framework.lock.yaml").write_text(eif_init._dump_yaml(eif_init.LOCK_HEADER, lock_data), encoding="utf-8")

    staging = eif_init.stage_bundle(inst, sources)
    runtime = inst / ".eif" / "runtime"
    staging.rename(runtime)

    block = eif_init._managed_block(FRAMEWORK_ROOT, "knowledge", "knowledge/index.md", "greenfield", "CLAUDE.md", True)
    (inst / "CLAUDE.md").write_text(block + "\n", encoding="utf-8")
    (inst / ".gitignore").write_text(eif_init.GITIGNORE_BLOCK, encoding="utf-8")


def _init_real_instance_variant(
    inst: Path,
    *,
    adoption_mode: str = "greenfield",
    knowledge_root: str = "knowledge",
    knowledge_index_path: str = "knowledge/index.md",
    knowledge_index_lock: dict | None = None,
) -> None:
    """Like _init_real_instance, but parameterized for the independent-review
    drift-detection tests (Item 6): adoption mode, knowledge paths, and an
    optional lock.knowledge_index entry (present only when eif_init.py
    actually created/regenerated a managed index that run)."""
    ref, _short, _dirty = eif_init.resolve_framework_state(FRAMEWORK_ROOT)
    sources = eif_init.collect_bundle_sources(FRAMEWORK_ROOT)
    manifest = eif_init.build_manifest(sources)
    digest = eif_init.combined_digest(manifest)

    config_data = eif_init.render_config_data(
        "verify-test", "claude-code", "en", "0.1.0-dev",
        knowledge_root, knowledge_index_path, adoption_mode, True,
    )
    (inst / ".eif").mkdir(parents=True)
    (inst / ".eif" / "config.yaml").write_text(eif_init._dump_yaml(eif_init.CONFIG_HEADER, config_data), encoding="utf-8")

    migration_status = "adopted" if adoption_mode == "coexist" else "greenfield"
    lock_data = eif_init.render_lock_data(
        "git", {"commit_sha": ref or "a" * 40, "dirty": False}, None, None, "claude-code", "CLAUDE.md",
        ".eif/runtime", manifest, digest, migration_status, "0.1.0", "2026-07-15T00:00:00+00:00",
        knowledge_index=knowledge_index_lock,
    )
    (inst / ".eif" / "framework.lock.yaml").write_text(eif_init._dump_yaml(eif_init.LOCK_HEADER, lock_data), encoding="utf-8")

    staging = eif_init.stage_bundle(inst, sources)
    runtime = inst / ".eif" / "runtime"
    staging.rename(runtime)

    block = eif_init._managed_block(FRAMEWORK_ROOT, knowledge_root, knowledge_index_path, adoption_mode, "CLAUDE.md", True)
    (inst / "CLAUDE.md").write_text(block + "\n", encoding="utf-8")
    (inst / ".gitignore").write_text(eif_init.GITIGNORE_BLOCK, encoding="utf-8")


def main() -> int:
    results = []

    # --- check_provenance: discriminated framework.source_type (adoption-
    # hardening round) - each kind reports its own informational note,
    # never fabricates a note that implies a different kind. ---
    git_clean = verify.check_provenance({"framework": {"source_type": "git"}, "git": {"commit_sha": "a" * 40, "dirty": False}})
    results.append(check("provenance: clean git source has no notes", git_clean == []))
    git_dirty = verify.check_provenance({"framework": {"source_type": "git"}, "git": {"commit_sha": "a" * 40, "dirty": True}})
    results.append(check("provenance: dirty git source is noted", len(git_dirty) == 1 and "DIRTY" in git_dirty[0]))
    bundle_notes = verify.check_provenance({"framework": {"source_type": "source-bundle"}, "source_bundle": {"asserted_ref": "export-x", "dirty": False}})
    results.append(check("provenance: source-bundle is ALWAYS noted as asserted, even when not dirty", len(bundle_notes) == 1 and "ASSERTED" in bundle_notes[0]))
    bundle_dirty_notes = verify.check_provenance({"framework": {"source_type": "source-bundle"}, "source_bundle": {"asserted_ref": "export-x", "dirty": True}})
    results.append(check("provenance: dirty source-bundle gets both the asserted note and a dirty note", len(bundle_dirty_notes) == 2))
    pkg_notes = verify.check_provenance({"framework": {"source_type": "installed-package"}, "package": {"distribution": "engineering-intelligence-framework", "version": "0.1.0.dev0", "python_version": "3.12.0"}})
    results.append(check("provenance: installed-package source is noted by distribution/version, not a fake ref", len(pkg_notes) == 1 and "engineering-intelligence-framework" in pkg_notes[0] and "0.1.0.dev0" in pkg_notes[0]))

    # --- check_integrations: behavioral health and failure policy. Provider
    # canaries are covered by test_rtk_integration.py; this wrapper proves
    # doctor policy no longer equates PATH reachability with health. ---
    results.append(check(
        "integrations: disabled entry is never checked, even with a garbage provider",
        verify.check_integrations({"integrations": {"structural_graph": {"enabled": False, "provider": "not-a-real-thing"}}}) == [],
    ))
    results.append(check(
        "integrations: enabled RTK slot + wrong provider is misconfigured even under degrade",
        bool(verify.check_integrations({"integrations": {"shell_output_compression": {
            "enabled": True, "provider": "definitely-not-installed-xyz", "data_boundary": "local-only", "failure_policy": "degrade",
        }}})),
    ))
    results.append(check(
        "integrations: enabled + fail-closed + provider not on PATH -> reported",
        any("not-installed" in p or "no such executable" in p for p in verify.check_integrations({"integrations": {"shell_output_compression": {
            "enabled": True, "provider": "definitely-not-installed-xyz", "data_boundary": "local-only", "failure_policy": "fail-closed",
        }}})),
    ))
    mismatch = verify.check_integrations({"integrations": {"shell_output_compression": {
        "enabled": True, "provider": "rtk", "data_boundary": "external-api", "failure_policy": "degrade",
    }}})
    results.append(check(
        "integrations: RTK external-api boundary is misconfigured regardless of degrade policy",
        len(mismatch) == 1 and "misconfigured" in mismatch[0], mismatch,
    ))

    # --- Clean instance: everything passes ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "clean"
        _init_real_instance(inst)

        config = verify._load_yaml(inst / ".eif" / "config.yaml")
        lock = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")

        results.append(check("clean instance: config schema ok", verify.check_schema(FRAMEWORK_ROOT, inst / ".eif" / "config.yaml", "eif-config.schema.json", "config") == []))
        results.append(check("clean instance: lock schema ok", verify.check_schema(FRAMEWORK_ROOT, inst / ".eif" / "framework.lock.yaml", "framework-lock.schema.json", "lock") == []))
        results.append(check("clean instance: manifest digest self-consistent", verify.check_manifest_digest(lock) == []))
        hash_mismatches, missing, unexpected = verify.check_bundle_files(inst, lock)
        results.append(check("clean instance: no bundle file hash mismatches", hash_mismatches == []))
        results.append(check("clean instance: no missing managed files", missing == []))
        results.append(check("clean instance: no unexpected managed files (README.md/__pycache__ excluded correctly)", unexpected == []))
        results.append(check("clean instance: config/adapter/lock/entrypoint consistent", verify.check_consistency(config, lock, inst) == []))
        results.append(check("clean instance: marker integrity ok", verify.check_markers(inst, "CLAUDE.md") == []))

    # --- Corrupt runtime: a bundled file hand-edited after generation ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "corrupt-runtime"
        _init_real_instance(inst)
        lock = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        target = inst / ".eif" / "runtime" / "eif_locale.py"
        target.write_text(target.read_text(encoding="utf-8") + "\n# hand-edited after generation\n", encoding="utf-8")
        hash_mismatches, missing, unexpected = verify.check_bundle_files(inst, lock)
        results.append(check("corrupt runtime: hand-edited file caught as a hash mismatch",
                             "eif_locale.py" in hash_mismatches, str(hash_mismatches)))

    # --- Missing managed file ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "missing-file"
        _init_real_instance(inst)
        lock = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        (inst / ".eif" / "runtime" / "eif_locale.py").unlink()
        hash_mismatches, missing, unexpected = verify.check_bundle_files(inst, lock)
        results.append(check("missing managed file is caught", "eif_locale.py" in missing, str(missing)))

    # --- Unexpected file dropped into the bundle ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "unexpected-file"
        _init_real_instance(inst)
        lock = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        (inst / ".eif" / "runtime" / "not_supposed_to_be_here.py").write_text("# rogue file\n", encoding="utf-8")
        hash_mismatches, missing, unexpected = verify.check_bundle_files(inst, lock)
        results.append(check("unexpected file (not README.md/__pycache__) is flagged",
                             "not_supposed_to_be_here.py" in unexpected, str(unexpected)))
        (inst / ".eif" / "runtime" / "README.md").unlink()
        (inst / ".eif" / "runtime" / "README.md").write_text("# regenerated readme, still not in manifest\n", encoding="utf-8")
        _, _, unexpected2 = verify.check_bundle_files(inst, lock)
        results.append(check("README.md itself is NOT flagged as unexpected (known, by-design exclusion)",
                             "README.md" not in unexpected2))

    # --- Runtime schema-loading crash safety: a corrupt/partially-staged
    # bundle must fail this ONE check, not crash the whole doctor run before
    # later checks get a chance to report. Simulates self-audit mode
    # (--framework-root pointed at the instance's own bundled .eif/runtime,
    # not a framework checkout) since that's the bundled copy this fix
    # protects. ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "missing-schema"
        _init_real_instance(inst)
        bundled_root = inst / ".eif" / "runtime"
        schema_path = bundled_root / "core" / "schemas" / "eif-config.schema.json"
        schema_path.unlink()
        errors = verify.check_schema(bundled_root, inst / ".eif" / "config.yaml", "eif-config.schema.json", "config")
        results.append(check(
            "missing bundled schema is reported as this check's problem, not a crash",
            len(errors) == 1 and "missing" in errors[0], str(errors),
        ))

    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "corrupt-schema"
        _init_real_instance(inst)
        bundled_root = inst / ".eif" / "runtime"
        schema_path = bundled_root / "core" / "schemas" / "eif-config.schema.json"
        schema_path.write_text("{ not valid json", encoding="utf-8")
        errors = verify.check_schema(bundled_root, inst / ".eif" / "config.yaml", "eif-config.schema.json", "config")
        results.append(check(
            "corrupt (invalid JSON) bundled schema is reported as this check's problem, not a crash",
            len(errors) == 1 and "not valid JSON" in errors[0], str(errors),
        ))

    # --- Corrupted lock: manifest digest doesn't match its own manifest ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "corrupt-lock"
        _init_real_instance(inst)
        lock = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        lock["bundle"]["manifest"][0]["sha256"] = "f" * 64  # tamper with one entry
        results.append(check("tampered manifest entry breaks digest self-consistency",
                             verify.check_manifest_digest(lock) != []))

    # --- Consistency: adapter mismatch between config and lock ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "adapter-mismatch"
        _init_real_instance(inst)
        config = verify._load_yaml(inst / ".eif" / "config.yaml")
        lock = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        lock["adapter"]["name"] = "not-a-real-adapter"
        problems = verify.check_consistency(config, lock, inst)
        results.append(check("config/lock adapter name mismatch is caught", len(problems) > 0, str(problems)))

        lock2 = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        lock2["adapter"]["entrypoint"] = "WRONG.md"
        problems2 = verify.check_consistency(config, lock2, inst)
        results.append(check("lock entrypoint not matching the registered entrypoint is caught", len(problems2) > 0, str(problems2)))

        lock3 = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        lock3["instance"]["migration_status"] = "not-a-real-status"
        problems3 = verify.check_consistency(config, lock3, inst)
        results.append(check("invalid migration_status is caught", len(problems3) > 0, str(problems3)))

    # --- Marker integrity: corrupt CLAUDE.md with reversed markers ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "bad-markers"
        _init_real_instance(inst)
        (inst / "CLAUDE.md").write_text(
            eif_init.EIF_END + "\n\nstray\n\n" + eif_init.EIF_BEGIN + " x -->\n", encoding="utf-8",
        )
        problems = verify.check_markers(inst, "CLAUDE.md")
        results.append(check("reversed markers in CLAUDE.md are caught by verify_runtime", len(problems) > 0, str(problems)))

    # --- Independent-review Item 6: config/generated-block drift, clean cases ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "drift-clean-greenfield"
        _init_real_instance_variant(inst, adoption_mode="greenfield")
        config = verify._load_yaml(inst / ".eif" / "config.yaml")
        results.append(check("clean greenfield instance: no config/block drift",
                             verify.check_config_block_drift(config, inst, "CLAUDE.md") == []))

    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "drift-clean-coexist"
        _init_real_instance_variant(inst, adoption_mode="coexist")
        config = verify._load_yaml(inst / ".eif" / "config.yaml")
        results.append(check("clean coexist instance: no config/block drift",
                             verify.check_config_block_drift(config, inst, "CLAUDE.md") == []))

    # --- adoption.mode hand-edited in config.yaml without re-running eif_init.py ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "drift-mode-edited-to-coexist"
        _init_real_instance_variant(inst, adoption_mode="greenfield")  # CLAUDE.md generated as greenfield
        config = verify._load_yaml(inst / ".eif" / "config.yaml")
        config["adoption"]["mode"] = "coexist"  # simulated hand-edit, no regeneration
        problems = verify.check_config_block_drift(config, inst, "CLAUDE.md")
        results.append(check("hand-edited adoption.mode -> coexist without regeneration is caught",
                             len(problems) > 0 and "eif_init.py again" in problems[0], str(problems)))

    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "drift-mode-edited-to-greenfield"
        _init_real_instance_variant(inst, adoption_mode="coexist")  # CLAUDE.md generated as coexist
        config = verify._load_yaml(inst / ".eif" / "config.yaml")
        config["adoption"]["mode"] = "greenfield"  # simulated hand-edit, no regeneration
        problems = verify.check_config_block_drift(config, inst, "CLAUDE.md")
        results.append(check("hand-edited adoption.mode -> greenfield without regeneration is caught",
                             len(problems) > 0 and "eif_init.py again" in problems[0], str(problems)))

    # --- knowledge.root / knowledge.index_path hand-edited without regeneration ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "drift-knowledge-root-edited"
        _init_real_instance_variant(inst, knowledge_root="knowledge", knowledge_index_path="knowledge/index.md")
        config = verify._load_yaml(inst / ".eif" / "config.yaml")
        config["knowledge"]["root"] = "docs/knowledge"  # CLAUDE.md's search command still says --knowledge-root knowledge
        problems = verify.check_config_block_drift(config, inst, "CLAUDE.md")
        results.append(check("hand-edited knowledge.root without regeneration is caught", len(problems) > 0, str(problems)))

    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "drift-knowledge-index-path-edited"
        _init_real_instance_variant(inst, knowledge_root="knowledge", knowledge_index_path="knowledge/index.md")
        config = verify._load_yaml(inst / ".eif" / "config.yaml")
        config["knowledge"]["index_path"] = "knowledge/INDEX.md"  # CLAUDE.md's read instruction still says index.md
        problems = verify.check_config_block_drift(config, inst, "CLAUDE.md")
        results.append(check("hand-edited knowledge.index_path without regeneration is caught", len(problems) > 0, str(problems)))

    # --- Independent-review Item 6: knowledge index drift (ownership marker, hash) ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "index-drift-missing"
        content = verify.MANAGED_INDEX_MARKER + "\n\n# Knowledge Index\n\n(no entries)\n"
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        _init_real_instance_variant(inst, knowledge_index_lock={"path": "knowledge/index.md", "sha256": content_hash})
        lock = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        # deliberately never written to disk -> "missing"
        problems = verify.check_knowledge_index_drift(inst, lock)
        results.append(check("knowledge index drift: missing managed index file is caught", len(problems) > 0, str(problems)))

    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "index-drift-no-marker"
        content = verify.MANAGED_INDEX_MARKER + "\n\n# Knowledge Index\n\n(no entries)\n"
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        _init_real_instance_variant(inst, knowledge_index_lock={"path": "knowledge/index.md", "sha256": content_hash})
        lock = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        (inst / "knowledge").mkdir(parents=True, exist_ok=True)
        (inst / "knowledge" / "index.md").write_bytes(b"# Hand-edited index, ownership marker removed\n")
        problems = verify.check_knowledge_index_drift(inst, lock)
        results.append(check("knowledge index drift: stripped ownership marker is caught",
                             len(problems) > 0 and "ownership marker" in problems[0], str(problems)))

    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "index-drift-hash-mismatch"
        content = verify.MANAGED_INDEX_MARKER + "\n\n# Knowledge Index\n\n(no entries)\n"
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        _init_real_instance_variant(inst, knowledge_index_lock={"path": "knowledge/index.md", "sha256": content_hash})
        lock = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        (inst / "knowledge").mkdir(parents=True, exist_ok=True)
        mutated = verify.MANAGED_INDEX_MARKER + "\n\n# Knowledge Index (HAND EDITED)\n\n(no entries)\n"
        (inst / "knowledge" / "index.md").write_bytes(mutated.encode("utf-8"))
        problems = verify.check_knowledge_index_drift(inst, lock)
        results.append(check("knowledge index drift: hash mismatch after hand-edit is caught",
                             len(problems) > 0 and "hash" in problems[0], str(problems)))

    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "index-drift-clean"
        content = verify.MANAGED_INDEX_MARKER + "\n\n# Knowledge Index\n\n(no entries)\n"
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        _init_real_instance_variant(inst, knowledge_index_lock={"path": "knowledge/index.md", "sha256": content_hash})
        lock = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        (inst / "knowledge").mkdir(parents=True, exist_ok=True)
        (inst / "knowledge" / "index.md").write_bytes(content.encode("utf-8"))
        results.append(check("knowledge index drift: matching managed index has no drift",
                             verify.check_knowledge_index_drift(inst, lock) == []))

    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "index-drift-unmanaged"
        _init_real_instance_variant(inst, knowledge_index_lock=None)  # not EIF-managed this run
        lock = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        results.append(check("knowledge index drift: no lock entry means no check (not a false positive)",
                             verify.check_knowledge_index_drift(inst, lock) == []))

    # --- End-to-end: the actual doctor command (main()) on a hand-edited
    # config with no regeneration must FAIL with a specific fix instruction,
    # never silently report "all checks passed" (independent review's exact
    # wording of the Item 6 requirement). ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "e2e-hand-edited-config"
        _init_real_instance_variant(inst, adoption_mode="greenfield")
        cfg_path = inst / ".eif" / "config.yaml"
        config = verify._load_yaml(cfg_path)
        config["adoption"]["mode"] = "coexist"  # hand-edited value, CLAUDE.md never regenerated
        cfg_path.write_text(eif_init._dump_yaml(eif_init.CONFIG_HEADER, config), encoding="utf-8")

        buf = io.StringIO()
        old_argv = sys.argv
        sys.argv = ["eif_verify_runtime.py", "--framework-root", str(FRAMEWORK_ROOT), "--instance-path", str(inst)]
        try:
            with contextlib.redirect_stdout(buf):
                rc = verify.main()
        finally:
            sys.argv = old_argv
        output = buf.getvalue()
        results.append(check("doctor: hand-edited config without regeneration exits non-zero", rc == 1))
        results.append(check(
            "doctor: hand-edited config gives a specific fix instruction, not a silent pass",
            "run eif_init.py again" in output and "all checks passed" not in output,
            output[-800:],
        ))

    # --- Migration provenance consistency (independent-review): adoption.mode
    # (current coexistence behavior) vs migration_status (historical origin).
    # Pure-function truth table + one end-to-end. ---
    def cfg(mode):
        return {"adoption": {"mode": mode}}

    def lk(status):
        return {"instance": {"migration_status": status}}

    results.append(check("provenance doctor: coexist + greenfield -> FAIL",
                         verify.check_migration_provenance_consistency(cfg("coexist"), lk("greenfield")) != []))
    results.append(check("provenance doctor: coexist + adopted -> OK",
                         verify.check_migration_provenance_consistency(cfg("coexist"), lk("adopted")) == []))
    results.append(check("provenance doctor: greenfield + adopted -> OK (override history permissible)",
                         verify.check_migration_provenance_consistency(cfg("greenfield"), lk("adopted")) == []))
    results.append(check("provenance doctor: greenfield + greenfield -> OK",
                         verify.check_migration_provenance_consistency(cfg("greenfield"), lk("greenfield")) == []))
    results.append(check("provenance doctor: FAIL message names the concrete repair",
                         "--migration-status adopted" in verify.check_migration_provenance_consistency(cfg("coexist"), lk("greenfield"))[0]))

    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "e2e-migration-contradiction"
        _init_real_instance_variant(inst, adoption_mode="coexist")  # coexist + adopted, clean
        lock_path = inst / ".eif" / "framework.lock.yaml"
        lock = verify._load_yaml(lock_path)
        lock["instance"]["migration_status"] = "greenfield"  # corrupt to contradict the coexist config
        lock_path.write_text(eif_init._dump_yaml(eif_init.LOCK_HEADER, lock), encoding="utf-8")
        buf = io.StringIO()
        old_argv = sys.argv
        sys.argv = ["eif_verify_runtime.py", "--framework-root", str(FRAMEWORK_ROOT), "--instance-path", str(inst)]
        try:
            with contextlib.redirect_stdout(buf):
                rc = verify.main()
        finally:
            sys.argv = old_argv
        output = buf.getvalue()
        results.append(check("doctor e2e: coexist config + greenfield lock exits non-zero", rc == 1))
        results.append(check("doctor e2e: names the migration provenance contradiction",
                             "migration provenance" in output and "contradict" in output, output[-800:]))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_verify_runtime: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
