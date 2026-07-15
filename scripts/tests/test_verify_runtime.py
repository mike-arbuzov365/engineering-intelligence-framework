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
    ref, ref_short, _ = eif_init.resolve_framework_state(FRAMEWORK_ROOT)
    sources = eif_init.collect_bundle_sources(FRAMEWORK_ROOT)
    manifest = eif_init.build_manifest(sources)
    digest = eif_init.combined_digest(manifest)

    config_data = eif_init.render_config_data("verify-test", "claude-code", "en", "0.1.0-dev", "knowledge", "knowledge/index.md", "greenfield", True)
    (inst / ".eif").mkdir(parents=True)
    (inst / ".eif" / "config.yaml").write_text(eif_init._dump_yaml(eif_init.CONFIG_HEADER, config_data), encoding="utf-8")

    lock_data = eif_init.render_lock_data(
        ref or "a" * 40, ref_short or "aaaaaaa", False, "git-verified", "claude-code", "CLAUDE.md",
        ".eif/runtime", manifest, digest, "greenfield", "0.1.0", "2026-07-15T00:00:00+00:00",
    )
    (inst / ".eif" / "framework.lock.yaml").write_text(eif_init._dump_yaml(eif_init.LOCK_HEADER, lock_data), encoding="utf-8")

    staging = eif_init.stage_bundle(inst, sources)
    runtime = inst / ".eif" / "runtime"
    staging.rename(runtime)

    block = eif_init._managed_block(FRAMEWORK_ROOT, "knowledge", "knowledge/index.md", "greenfield")
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
    ref, ref_short, _ = eif_init.resolve_framework_state(FRAMEWORK_ROOT)
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
        ref or "a" * 40, ref_short or "aaaaaaa", False, "git-verified", "claude-code", "CLAUDE.md",
        ".eif/runtime", manifest, digest, migration_status, "0.1.0", "2026-07-15T00:00:00+00:00",
        knowledge_index=knowledge_index_lock,
    )
    (inst / ".eif" / "framework.lock.yaml").write_text(eif_init._dump_yaml(eif_init.LOCK_HEADER, lock_data), encoding="utf-8")

    staging = eif_init.stage_bundle(inst, sources)
    runtime = inst / ".eif" / "runtime"
    staging.rename(runtime)

    block = eif_init._managed_block(FRAMEWORK_ROOT, knowledge_root, knowledge_index_path, adoption_mode)
    (inst / "CLAUDE.md").write_text(block + "\n", encoding="utf-8")
    (inst / ".gitignore").write_text(eif_init.GITIGNORE_BLOCK, encoding="utf-8")


def main() -> int:
    results = []

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
        results.append(check("clean instance: config/adapter/lock/entrypoint consistent", verify.check_consistency(config, lock) == []))
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
        problems = verify.check_consistency(config, lock)
        results.append(check("config/lock adapter name mismatch is caught", len(problems) > 0, str(problems)))

        lock2 = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        lock2["adapter"]["entrypoint"] = "WRONG.md"
        problems2 = verify.check_consistency(config, lock2)
        results.append(check("lock entrypoint not matching the registered entrypoint is caught", len(problems2) > 0, str(problems2)))

        lock3 = verify._load_yaml(inst / ".eif" / "framework.lock.yaml")
        lock3["instance"]["migration_status"] = "not-a-real-status"
        problems3 = verify.check_consistency(config, lock3)
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

    passed = sum(results)
    print(f"\ntest_verify_runtime: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
