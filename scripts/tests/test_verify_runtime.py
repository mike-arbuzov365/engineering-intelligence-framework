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

    config_data = eif_init.render_config_data("verify-test", "claude-code", "en", "0.1.0-dev")
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

    block = eif_init._managed_block(FRAMEWORK_ROOT)
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

    passed = sum(results)
    print(f"\ntest_verify_runtime: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
