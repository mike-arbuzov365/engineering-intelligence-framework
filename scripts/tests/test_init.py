#!/usr/bin/env python3
"""Unit-level tests for eif_init.py: provenance/dirty-check (Finding E),
bundle manifest hashing, the init/upgrade/reconfigure contract (Finding A),
safe YAML generation, adapter registry restriction, and the transactional
commit/rollback primitives (Finding B) including injected-failure orphan
cleanup.

Full real-CLI subprocess scenarios (real upgrade preserving locale/adapter/
migration_status, real reconfigure, real rollback via the FAULT_INJECT_ENV
hook, marker-safety refusal) live in scripts/tests/test_journey.py - this
file is the fast unit layer underneath them.

Usage:
    python scripts/tests/test_init.py
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eif_init  # noqa: E402
from eif_validate_frontmatter import validate_config_mode, validate_lock_mode  # noqa: E402

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def check(name: str, condition: bool, detail: str = "") -> bool:
    condition = bool(condition)
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def _args(**overrides):
    base = dict(project_name=None, locale=None, adapter=None, migration_status=None,
                framework_version=None, force=False, knowledge_root=None,
                knowledge_index_path=None, adoption_mode=None, manage_knowledge_index=None)
    base.update(overrides)
    return SimpleNamespace(**base)


def main() -> int:
    results = []

    # --- Provenance (Finding E) ---
    ref, _short, dirty = eif_init.resolve_framework_state(FRAMEWORK_ROOT)
    results.append(check("resolve_framework_state returns a real 40-hex SHA", bool(ref) and bool(SHA_RE.match(ref)), str(ref)))
    results.append(check("dirty flag is a real bool", isinstance(dirty, bool)))
    not_a_repo_ref, _, _ = eif_init.resolve_framework_state(Path(tempfile.gettempdir()) / "definitely-not-a-repo-xyz")
    results.append(check("non-git framework-root resolves to None", not_a_repo_ref is None, str(not_a_repo_ref)))

    # --- Bundle manifest ---
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
        results.append(check("manifest sorted by path", [m["path"] for m in manifest] == sorted(m["path"] for m in manifest)))
        digest = eif_init.combined_digest(manifest)
        results.append(check("combined digest deterministic", eif_init.combined_digest(manifest) == digest))

        (fake_fw / "scripts" / eif_init.BUNDLE_SCRIPTS[0]).unlink()
        try:
            eif_init.collect_bundle_sources(fake_fw)
            results.append(check("missing mandatory bundle source raises", False))
        except FileNotFoundError:
            results.append(check("missing mandatory bundle source raises", True))

    # --- Finding A: init / upgrade / reconfigure mode resolution ---
    # init: no existing config -> requires project_name, applies CLI defaults.
    try:
        eif_init._resolve_mode_and_values(_args(), None, None)
        results.append(check("init without --project-name raises", False))
    except ValueError:
        results.append(check("init without --project-name raises", True))

    r1 = eif_init._resolve_mode_and_values(
        _args(project_name="p", locale="uk", adapter="claude-code", migration_status="adopted"), None, None,
    )
    results.append(check("init: mode is 'init'", r1.mode == "init"))
    results.append(check("init: values come from CLI args", (r1.project_name, r1.locale, r1.adapter, r1.migration_status) == ("p", "uk", "claude-code", "adopted")))

    r2 = eif_init._resolve_mode_and_values(_args(project_name="p"), None, None)
    results.append(check("init: unset flags fall back to sane defaults", (r2.locale, r2.adapter, r2.migration_status) == ("en", eif_init.DEFAULT_ADAPTER, "greenfield")))
    results.append(check("init: knowledge root/index default", (r2.knowledge_root, r2.knowledge_index_path) == ("knowledge", "knowledge/index.md")))
    results.append(check("init: adoption mode defaults to greenfield", r2.adoption_mode == "greenfield"))

    r2b = eif_init._resolve_mode_and_values(_args(project_name="p", knowledge_root="docs/knowledge", adoption_mode="coexist"), None, None)
    results.append(check("init: explicit knowledge-root honored, index derived from it", r2b.knowledge_index_path == "docs/knowledge/index.md"))
    results.append(check("init: explicit adoption-mode honored", r2b.adoption_mode == "coexist"))

    # upgrade: existing config present, no --force -> config/lock are the
    # sole source of truth; any CLI values passed anyway are reported as ignored.
    existing_config = {"project": {"name": "existing-proj"}, "adapter": {"name": "claude-code"},
                       "localization": {"documentation_locale": "uk"}, "framework": {"version": "0.1.0-dev"},
                       "knowledge": {"root": "docs/knowledge", "index_path": "docs/knowledge/index.md"},
                       "adoption": {"mode": "coexist"}}
    existing_lock = {"instance": {"migration_status": "adopted"}}
    r3 = eif_init._resolve_mode_and_values(_args(), existing_config, existing_lock)
    results.append(check("upgrade: mode is 'upgrade'", r3.mode == "upgrade"))
    results.append(check("upgrade: values derived from existing config/lock, not CLI defaults",
                         (r3.project_name, r3.locale, r3.adapter, r3.migration_status) == ("existing-proj", "uk", "claude-code", "adopted")))
    results.append(check("upgrade: knowledge root/adoption mode derived from existing config",
                         (r3.knowledge_root, r3.knowledge_index_path, r3.adoption_mode) == ("docs/knowledge", "docs/knowledge/index.md", "coexist")))
    results.append(check("upgrade: ignored list is empty when no conflicting flags were passed", r3.ignored == []))

    r4 = eif_init._resolve_mode_and_values(
        _args(project_name="ignored-name", locale="en", knowledge_root="ignored-root", adoption_mode="greenfield"), existing_config, existing_lock,
    )
    results.append(check("upgrade: passing --project-name/--locale anyway does NOT change the derived values",
                         (r4.project_name, r4.locale) == ("existing-proj", "uk")))
    results.append(check("upgrade: passing --knowledge-root/--adoption-mode anyway does NOT change derived values",
                         (r4.knowledge_root, r4.adoption_mode) == ("docs/knowledge", "coexist")))
    results.append(check("upgrade: passed-but-ignored flags are reported for the caller to warn about",
                         set(r4.ignored) == {"--project-name", "--locale", "--knowledge-root", "--adoption-mode"}, str(r4.ignored)))

    # reconfigure: --force -> only explicitly-passed values change; everything else keeps its prior value.
    r5 = eif_init._resolve_mode_and_values(
        _args(force=True, locale="en"), existing_config, existing_lock,
    )
    results.append(check("reconfigure: mode is 'reconfigure'", r5.mode == "reconfigure"))
    results.append(check("reconfigure: explicitly-passed --locale changes", r5.locale == "en"))
    results.append(check("reconfigure: un-passed project_name/adapter/migration_status keep their prior values",
                         (r5.project_name, r5.adapter, r5.migration_status) == ("existing-proj", "claude-code", "adopted")))
    results.append(check("reconfigure: un-passed knowledge root/adoption mode keep their prior values",
                         (r5.knowledge_root, r5.adoption_mode) == ("docs/knowledge", "coexist")))

    # --- Migration provenance (independent-review): adoption.mode (current
    # coexistence behavior) reconciled against migration_status (historical
    # origin) via finalize_migration_status, driven by the REPOSITORY-ORIGIN
    # classification ("empty" | "pre_existing" | "unknown") - NOT the
    # entrypoint/governance preflight. (status, stop_reason) tuples. ---
    def fin(*, mode, resolved, explicit, adoption_mode, origin):
        return eif_init.finalize_migration_status(
            mode=mode, resolved_status=resolved, explicit_status=explicit,
            adoption_mode=adoption_mode, repository_origin=origin,
        )

    # init: genuinely empty greenfield repo stays greenfield
    results.append(check("provenance init: empty greenfield -> greenfield",
                         fin(mode="init", resolved="greenfield", explicit=None, adoption_mode="greenfield", origin="empty") == ("greenfield", None)))
    # init: coexist mode implies adopted history even on an empty-looking dir
    st, stop = fin(mode="init", resolved="greenfield", explicit=None, adoption_mode="coexist", origin="empty")
    results.append(check("provenance init: coexist -> adopted (no --migration-status needed)", (st, stop) == ("adopted", None)))
    # init: pre-existing repo (files outside .git/.eif) -> adopted, even in greenfield
    # AUTHORITY mode - the KEY fix: this used to depend on a CLAUDE.md existing.
    st, stop = fin(mode="init", resolved="greenfield", explicit=None, adoption_mode="greenfield", origin="pre_existing")
    results.append(check("provenance init: pre-existing repo (no CLAUDE.md needed) -> adopted history", (st, stop) == ("adopted", None)))
    # init: explicit coexist + greenfield is the hard contradiction -> STOP
    st, stop = fin(mode="init", resolved="greenfield", explicit="greenfield", adoption_mode="coexist", origin="empty")
    results.append(check("provenance init: coexist + explicit greenfield -> STOP", st is None and stop is not None and "contradiction" in stop))
    # init: explicit greenfield over a PRE-EXISTING repo -> STOP (false history)
    st, stop = fin(mode="init", resolved="greenfield", explicit="greenfield", adoption_mode="greenfield", origin="pre_existing")
    results.append(check("provenance init: explicit greenfield over pre-existing repo -> STOP", st is None and stop is not None))
    # init: explicit greenfield on a genuinely empty repo is fine
    results.append(check("provenance init: explicit greenfield on empty repo -> greenfield",
                         fin(mode="init", resolved="greenfield", explicit="greenfield", adoption_mode="greenfield", origin="empty") == ("greenfield", None)))
    # init: explicit adopted honored
    results.append(check("provenance init: explicit adopted honored",
                         fin(mode="init", resolved="greenfield", explicit="adopted", adoption_mode="coexist", origin="empty") == ("adopted", None)))
    # init: UNKNOWN origin (unreadable dir) never silently becomes greenfield -> STOP
    st, stop = fin(mode="init", resolved="greenfield", explicit=None, adoption_mode="greenfield", origin="unknown")
    results.append(check("provenance init: unknown origin, no --migration-status -> STOP (fail closed)", st is None and stop is not None))
    # init: UNKNOWN origin + an explicit historical decision is honored
    results.append(check("provenance init: unknown origin + explicit greenfield honored",
                         fin(mode="init", resolved="greenfield", explicit="greenfield", adoption_mode="greenfield", origin="unknown") == ("greenfield", None)))
    results.append(check("provenance init: unknown origin + explicit adopted honored",
                         fin(mode="init", resolved="greenfield", explicit="adopted", adoption_mode="greenfield", origin="unknown") == ("adopted", None)))
    # upgrade: persisted preserved verbatim, no contradiction logic, origin ignored
    results.append(check("provenance upgrade: persisted adopted preserved",
                         fin(mode="upgrade", resolved="adopted", explicit=None, adoption_mode="coexist", origin="pre_existing") == ("adopted", None)))
    # reconfigure: switching to coexist under recorded greenfield -> STOP (do not silently rewrite)
    st, stop = fin(mode="reconfigure", resolved="greenfield", explicit=None, adoption_mode="coexist", origin="pre_existing")
    results.append(check("provenance reconfigure: coexist over recorded greenfield, no flag -> STOP", st is None and stop is not None))
    # reconfigure: switching to coexist with explicit adopted is fine
    results.append(check("provenance reconfigure: coexist + explicit adopted -> adopted",
                         fin(mode="reconfigure", resolved="greenfield", explicit="adopted", adoption_mode="coexist", origin="pre_existing") == ("adopted", None)))
    # reconfigure: coexist + explicit greenfield still a contradiction
    st, stop = fin(mode="reconfigure", resolved="adopted", explicit="greenfield", adoption_mode="coexist", origin="pre_existing")
    results.append(check("provenance reconfigure: coexist + explicit greenfield -> STOP", st is None and stop is not None))
    # reconfigure: greenfield authority over recorded adopted history is allowed (preserve adopted)
    results.append(check("provenance reconfigure: greenfield mode keeps recorded adopted history",
                         fin(mode="reconfigure", resolved="adopted", explicit=None, adoption_mode="greenfield", origin="pre_existing") == ("adopted", None)))

    # --- Source-type consistency (adoption-hardening round): a routine
    # upgrade must never silently cross installed-package <-> git <->
    # source-bundle kinds; --force is the only way. ---
    pkg_lock = {"framework": {"source_type": "installed-package"}}
    git_lock_stub = {"framework": {"source_type": "git"}}
    no_source_type_lock = {"framework": {}}
    results.append(check(
        "source-type consistency: no existing lock -> no error (fresh init)",
        eif_init.check_source_type_consistency("git", None, force=False) is None,
    ))
    results.append(check(
        "source-type consistency: same kind on routine upgrade -> no error",
        eif_init.check_source_type_consistency("installed-package", pkg_lock, force=False) is None,
    ))
    results.append(check(
        "source-type consistency: installed-package -> git on routine upgrade -> STOP",
        eif_init.check_source_type_consistency("git", pkg_lock, force=False) is not None,
    ))
    results.append(check(
        "source-type consistency: git -> installed-package on routine upgrade -> STOP",
        eif_init.check_source_type_consistency("installed-package", git_lock_stub, force=False) is not None,
    ))
    results.append(check(
        "source-type consistency: --force explicitly permits the same kind change -> no error",
        eif_init.check_source_type_consistency("git", pkg_lock, force=True) is None,
    ))
    results.append(check(
        "source-type consistency: a lock predating this field (no recorded source_type) -> no error",
        eif_init.check_source_type_consistency("installed-package", no_source_type_lock, force=False) is None,
    ))
    results.append(check(
        "source-type consistency: STOP message names --force as the concrete repair",
        "--force" in (eif_init.check_source_type_consistency("git", pkg_lock, force=False) or ""),
    ))

    # --- detect_repository_origin: read-only origin classification, distinct
    # from governance detection (the entrypoint-only bug's real fix) ---
    with tempfile.TemporaryDirectory() as tmp:
        empty_dir = Path(tmp) / "empty"
        empty_dir.mkdir()
        results.append(check("origin: genuinely empty dir -> empty",
                             eif_init.detect_repository_origin(empty_dir)[0] == "empty"))
        git_only = Path(tmp) / "gitonly"
        (git_only / ".git").mkdir(parents=True)
        (git_only / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        results.append(check("origin: only .git/ present -> empty (VCS metadata is not project content)",
                             eif_init.detect_repository_origin(git_only)[0] == "empty"))
        stray_eif = Path(tmp) / "strayeif"
        (stray_eif / ".eif").mkdir(parents=True)
        (stray_eif / ".eif" / "junk.txt").write_text("x", encoding="utf-8")
        results.append(check("origin: only a stray .eif/ present -> empty (EIF namespace, documented policy)",
                             eif_init.detect_repository_origin(stray_eif)[0] == "empty"))
        readme_only = Path(tmp) / "readme"
        readme_only.mkdir()
        (readme_only / "README.md").write_text("# Project\n", encoding="utf-8")
        results.append(check("origin: README-only repo (no CLAUDE.md) -> pre_existing",
                             eif_init.detect_repository_origin(readme_only)[0] == "pre_existing"))
        src_tree = Path(tmp) / "srctree"
        (src_tree / "src").mkdir(parents=True)
        (src_tree / "src" / "main.py").write_text("print(1)\n", encoding="utf-8")
        (src_tree / ".git").mkdir()
        results.append(check("origin: source tree beside .git/ (no CLAUDE.md) -> pre_existing",
                             eif_init.detect_repository_origin(src_tree)[0] == "pre_existing"))
        missing = Path(tmp) / "does-not-exist"
        results.append(check("origin: non-existent dir -> empty (nothing there to adopt)",
                             eif_init.detect_repository_origin(missing)[0] == "empty"))

    # --- Config/lock rendering + schema validation, safe YAML for special characters ---
    tricky_name = "weird: name, with \"quotes\" and a # hash"
    data = eif_init.render_config_data(tricky_name, "claude-code", "uk", "0.1.0-dev", "knowledge", "knowledge/index.md", "greenfield", True)
    errors = eif_init.validate_in_memory(FRAMEWORK_ROOT, "eif-config.schema.json", data)
    results.append(check("config with YAML-special characters validates", errors == [], str(errors)))
    content = eif_init._dump_yaml(eif_init.CONFIG_HEADER, data)
    import yaml as _yaml
    round_tripped = _yaml.safe_load(content.split("\n\n", 1)[1] if "\n\n" in content else content)
    results.append(check("YAML-dumped config round-trips the tricky name exactly", round_tripped["project"]["name"] == tricky_name))

    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "config.yaml"
        cfg_path.write_text(content, encoding="utf-8")
        results.append(check("on-disk config validates via validate_config_mode", validate_config_mode(FRAMEWORK_ROOT, cfg_path) == 0))

    # --- Lock rendering, discriminated framework.source_type (adoption-hardening) ---
    common_lock_args = (
        "claude-code", "CLAUDE.md", ".eif/runtime",
        [{"path": "x.py", "sha256": "a" * 64}], "sha256:" + "b" * 64,
        "adopted", "0.1.0", "2026-07-15T00:00:00+00:00",
    )

    git_lock = eif_init.render_lock_data(
        "git", {"commit_sha": ref or "a" * 40, "dirty": True}, None, None, *common_lock_args,
    )
    git_errors = eif_init.validate_in_memory(FRAMEWORK_ROOT, "framework-lock.schema.json", git_lock)
    results.append(check("git-source lock validates", git_errors == [], str(git_errors)))
    results.append(check("dirty=True is NOT silently cleared for a git-source lock", git_lock["git"]["dirty"] is True))
    with tempfile.TemporaryDirectory() as tmp:
        lock_path = Path(tmp) / "framework.lock.yaml"
        lock_path.write_text(eif_init._dump_yaml(eif_init.LOCK_HEADER, git_lock), encoding="utf-8")
        results.append(check("on-disk git-source lock validates via validate_lock_mode", validate_lock_mode(FRAMEWORK_ROOT, lock_path) == 0))

    bundle_lock = eif_init.render_lock_data(
        "source-bundle", None, None, {"asserted_ref": "export-2026-07-15", "dirty": True}, *common_lock_args,
    )
    bundle_errors = eif_init.validate_in_memory(FRAMEWORK_ROOT, "framework-lock.schema.json", bundle_lock)
    results.append(check("source-bundle lock (asserted, not git-verified) validates", bundle_errors == [], str(bundle_errors)))
    results.append(check("dirty=True is NOT silently cleared for an asserted source-bundle lock", bundle_lock["source_bundle"]["dirty"] is True))

    package_lock = eif_init.render_lock_data(
        "installed-package", None,
        {"distribution": "engineering-intelligence-framework", "version": "0.1.0.dev0",
         "python_version": "3.12.0", "resource_manifest_digest": "sha256:" + "c" * 64},
        None, *common_lock_args,
    )
    package_errors = eif_init.validate_in_memory(FRAMEWORK_ROOT, "framework-lock.schema.json", package_lock)
    results.append(check("installed-package lock validates, no fabricated git commit_sha", package_errors == [], str(package_errors)))
    results.append(check("installed-package lock has no 'git' object at all", "git" not in package_lock))

    mismatched_lock = dict(git_lock)
    mismatched_lock["framework"] = dict(git_lock["framework"], source_type="installed-package")
    mismatch_errors = eif_init.validate_in_memory(FRAMEWORK_ROOT, "framework-lock.schema.json", mismatched_lock)
    results.append(check("source_type=installed-package with a 'git' object but no 'package' object is rejected", len(mismatch_errors) > 0))

    bad_source_type_lock = dict(git_lock)
    bad_source_type_lock["framework"] = dict(git_lock["framework"], source_type="not-a-real-value")
    bad_errors = eif_init.validate_in_memory(FRAMEWORK_ROOT, "framework-lock.schema.json", bad_source_type_lock)
    results.append(check("an invalid framework.source_type value is rejected by the schema", len(bad_errors) > 0))

    missing_instance_lock = {k: v for k, v in git_lock.items() if k != "instance"}
    missing_errors = eif_init.validate_in_memory(FRAMEWORK_ROOT, "framework-lock.schema.json", missing_instance_lock)
    results.append(check("a lock missing the 'instance' block is rejected (now required)", len(missing_errors) > 0))

    # --- Adapter registry restriction ---
    try:
        eif_init.entrypoint_for("cursor-does-not-exist")
        results.append(check("entrypoint_for rejects an unregistered adapter", False))
    except ValueError:
        results.append(check("entrypoint_for rejects an unregistered adapter", True))
    results.append(check("entrypoint_for('claude-code') returns CLAUDE.md", eif_init.entrypoint_for("claude-code") == "CLAUDE.md"))

    # --- Transactional _Stage / commit_transaction (Finding B) ---
    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "inst"
        inst.mkdir()
        live = inst / "artifact.txt"
        live.write_text("original", encoding="utf-8")

        next1 = inst / "artifact.txt.next"
        next1.write_text("updated", encoding="utf-8")
        stage1 = eif_init._Stage("a", next1, live, is_dir=False)
        stage1.commit()
        results.append(check("_Stage.commit swaps content into place", live.read_text(encoding="utf-8") == "updated"))
        results.append(check("_Stage.commit leaves a .previous during the run", stage1.previous_path.exists()))
        stage1.cleanup()
        results.append(check("_Stage.cleanup removes the .previous", not stage1.previous_path.exists()))

        # Full transaction: 3 stages, injected failure after the 2nd -> both
        # committed stages roll back, and the 3rd stage's never-committed
        # .next is cleaned up too (the orphan bug found via manual testing).
        import os
        a_live, b_live, c_live = inst / "a.txt", inst / "b.txt", inst / "c.txt"
        a_live.write_text("a-orig", encoding="utf-8")
        b_live.write_text("b-orig", encoding="utf-8")
        # c has no prior version - a brand-new artifact this "run" would create.
        a_next, b_next, c_next = inst / "a.txt.next", inst / "b.txt.next", inst / "c.txt.next"
        a_next.write_text("a-new", encoding="utf-8")
        b_next.write_text("b-new", encoding="utf-8")
        c_next.write_text("c-new", encoding="utf-8")
        stages = [
            eif_init._Stage("stage-a", a_next, a_live, is_dir=False),
            eif_init._Stage("stage-b", b_next, b_live, is_dir=False),
            eif_init._Stage("stage-c", c_next, c_live, is_dir=False),
        ]
        os.environ[eif_init.FAULT_INJECT_ENV] = "stage-b"
        try:
            eif_init.commit_transaction(stages)
            results.append(check("commit_transaction propagates the injected failure", False))
        except RuntimeError:
            results.append(check("commit_transaction propagates the injected failure", True))
        finally:
            del os.environ[eif_init.FAULT_INJECT_ENV]

        results.append(check("full rollback: stage-a restored to its original content", a_live.read_text(encoding="utf-8") == "a-orig"))
        results.append(check("full rollback: stage-b restored to its original content", b_live.read_text(encoding="utf-8") == "b-orig"))
        results.append(check("full rollback: stage-c (never committed) has no live artifact left behind", not c_live.exists()))
        results.append(check("full rollback: no orphaned .next files for any stage",
                             not a_next.exists() and not b_next.exists() and not c_next.exists()))
        results.append(check("full rollback: no leftover .previous files",
                             not stages[0].previous_path.exists() and not stages[1].previous_path.exists()))

    # --- Config backup: collision-safe destination + self-cleaning copy ---
    import os
    import datetime as _dt
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "config.yaml"
        src.write_text("original config\n", encoding="utf-8")
        d1 = eif_init._backup_dest(src)
        results.append(check("_backup_dest returns a non-existing path", not d1.exists()))
        d1.write_text("b1", encoding="utf-8")
        d2 = eif_init._backup_dest(src)
        results.append(check("_backup_dest: a second call avoids the existing backup", d2 != d1 and not d2.exists()))

        # Force a FIXED timestamp so the collision loop (not the microsecond
        # clock) is what guarantees distinctness - same-instant backups must
        # still never collide or overwrite an existing recovery backup.
        class _FixedDatetime:
            @staticmethod
            def now():
                return _dt.datetime(2026, 7, 16, 12, 0, 0, 123456)

        class _FixedModule:
            datetime = _FixedDatetime

        saved_dt = eif_init.datetime
        try:
            eif_init.datetime = _FixedModule
            e1 = eif_init._backup_dest(src); e1.write_text("x", encoding="utf-8")
            e2 = eif_init._backup_dest(src); e2.write_text("x", encoding="utf-8")
            e3 = eif_init._backup_dest(src)
            results.append(check("_backup_dest: same-instant calls never collide (collision loop)",
                                 len({e1, e2, e3}) == 3 and not e3.exists()))
        finally:
            eif_init.datetime = saved_dt

        # _backup_copy self-cleans a partial destination on the injected fault.
        dest = eif_init._backup_dest(src)
        os.environ[eif_init.FAULT_INJECT_PARTIAL_ENV] = "backup"
        try:
            eif_init._backup_copy(src, dest)
            results.append(check("_backup_copy propagates the partial-backup fault", False))
        except RuntimeError:
            results.append(check("_backup_copy propagates the partial-backup fault", True))
        finally:
            os.environ.pop(eif_init.FAULT_INJECT_PARTIAL_ENV, None)
        results.append(check("_backup_copy self-cleaned the partial backup (no orphan)", not dest.exists()))

        good = eif_init._backup_dest(src)
        eif_init._backup_copy(src, good)
        results.append(check("_backup_copy makes a byte-for-byte copy", good.read_bytes() == src.read_bytes()))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_init: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
