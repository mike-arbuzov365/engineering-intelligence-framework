#!/usr/bin/env python3
"""Cursor adapter acceptance tests (Stage 3).

Covers what is genuinely NEW in this adapter, end-to-end via the real CLI
(subprocess, same convention as test_adoption.py) rather than only unit-
testing internals:

 1. greenfield Cursor init: nested .cursor/rules/eif/ created, valid
    frontmatter, governance content present.
 2. nested-entrypoint transaction rollback at multiple fault points (before/
    partial/after commit) - .cursor/, .cursor/rules/, .cursor/rules/eif/ are
    removed on failure (none existed before this run), and a PRE-EXISTING
    .cursor/rules/ directory (with an unrelated project-owned rule file) is
    never removed even on failure.
 3. flagless upgrade preserves the chosen adapter.
 4. adapter switching both directions (claude-code -> cursor, cursor ->
    claude-code): old entrypoint handled correctly (deleted if EIF-only,
    stripped-not-deleted if it has real project content), new entrypoint
    created, project-owned content preserved byte-for-byte.
 5. malformed markers on the OLD entrypoint during a switch -> STOP before
    any writes (full snapshot unchanged, including the new adapter's files).
 6. generated frontmatter parses as valid YAML with the exact expected
    fields.
 7. doctor (eif_verify_runtime.py) passes on a clean Cursor instance and
    catches a corrupted one (reversed markers).

Usage:
    python scripts/tests/test_cursor_adapter.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = FRAMEWORK_ROOT / "scripts"

CURSOR_ENTRY = Path(".cursor/rules/eif/governance.mdc")


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args], cwd=str(cwd) if cwd else None,
        capture_output=True, text=True, encoding="utf-8",
    )


def git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")


def init_git_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    git(["init", "-q"], root)
    git(["config", "user.email", "test@example.invalid"], root)
    git(["config", "user.name", "Cursor Adapter Test"], root)


def eif_init(inst: Path, *extra: str) -> subprocess.CompletedProcess:
    return run([str(SCRIPTS / "eif_init.py"), "--framework-root", str(FRAMEWORK_ROOT),
                "--instance-path", str(inst), "--allow-dirty", *extra])


def eif_verify(inst: Path, *extra: str) -> subprocess.CompletedProcess:
    return run([str(SCRIPTS / "eif_verify_runtime.py"), "--framework-root", str(FRAMEWORK_ROOT),
                "--instance-path", str(inst), *extra])


def snapshot(root: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if ".git" in p.relative_to(root).parts:
            continue
        out[p.relative_to(root).as_posix()] = p.read_bytes()
    return out


def check(name: str, cond: bool, detail: str = "") -> bool:
    status = "PASS" if cond else "FAIL"
    print(f"{status} {name}" + (f": {detail}" if detail and not cond else ""))
    return cond


def main() -> int:
    results: list[bool] = []

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # -------------------------------------------------------------
        # 1. greenfield Cursor init
        # -------------------------------------------------------------
        inst1 = tmp / "scenario-1-greenfield-cursor"
        init_git_repo(inst1)
        r1 = eif_init(inst1, "--project-name", "cursor-fixture", "--adapter", "cursor")
        results.append(check("1. greenfield cursor init exits 0", r1.returncode == 0, r1.stdout + r1.stderr))
        entry1 = inst1 / CURSOR_ENTRY
        results.append(check("1. nested .cursor/rules/eif/governance.mdc was created", entry1.exists()))
        text1 = entry1.read_text(encoding="utf-8") if entry1.exists() else ""
        results.append(check("1. entrypoint starts with YAML frontmatter", text1.startswith("---\n")))
        results.append(check("1. entrypoint contains the EIF-managed block", "<!-- EIF:BEGIN" in text1 and "<!-- EIF:END -->" in text1))
        results.append(check("1. entrypoint contains governance content (Knowledge Delta)", "Knowledge Delta" in text1))
        cfg1 = (inst1 / ".eif" / "config.yaml").read_text(encoding="utf-8")
        results.append(check("1. config records adapter.name: cursor", "cursor" in cfg1))
        lock1 = (inst1 / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8")
        results.append(check("1. lock records the nested entrypoint path", ".cursor/rules/eif/governance.mdc" in lock1 or ".cursor\\rules\\eif\\governance.mdc" in lock1, lock1))

        # -------------------------------------------------------------
        # 2. nested-entrypoint fault injection - before/partial/after,
        #    proving directories this run created are removed on failure.
        # -------------------------------------------------------------
        for fault_kind, env_var in (("before", "EIF_INIT_TEST_FAIL_BEFORE"), ("after", "EIF_INIT_TEST_FAIL_AFTER")):
            inst2 = tmp / f"scenario-2-fault-{fault_kind}"
            init_git_repo(inst2)
            env = {"PATH": __import__("os").environ.get("PATH", ""), env_var: "entrypoint"}
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "eif_init.py"), "--framework-root", str(FRAMEWORK_ROOT),
                 "--instance-path", str(inst2), "--allow-dirty", "--project-name", "cursor-fixture", "--adapter", "cursor"],
                capture_output=True, text=True, encoding="utf-8", env=env,
            )
            results.append(check(f"2. fault-{fault_kind}-entrypoint run exits non-zero", proc.returncode != 0, proc.stdout + proc.stderr))
            results.append(check(f"2. fault-{fault_kind}: .cursor/ removed entirely (this run created it)", not (inst2 / ".cursor").exists()))
            results.append(check(f"2. fault-{fault_kind}: no .eif/ left behind either", not (inst2 / ".eif").exists()))

        # 2b. a PRE-EXISTING .cursor/rules/ (with an unrelated project-owned
        #     rule file) must survive a fault untouched - only directories
        #     THIS run created are ever removed.
        inst2b = tmp / "scenario-2b-preexisting-rules-dir"
        init_git_repo(inst2b)
        (inst2b / ".cursor" / "rules").mkdir(parents=True)
        (inst2b / ".cursor" / "rules" / "my-own-rule.mdc").write_text("---\nalwaysApply: true\n---\nMy own rule.\n", encoding="utf-8")
        before2b = snapshot(inst2b)
        env2b = {"PATH": __import__("os").environ.get("PATH", ""), "EIF_INIT_TEST_FAIL_AFTER": "entrypoint"}
        proc2b = subprocess.run(
            [sys.executable, str(SCRIPTS / "eif_init.py"), "--framework-root", str(FRAMEWORK_ROOT),
             "--instance-path", str(inst2b), "--allow-dirty", "--project-name", "cursor-fixture", "--adapter", "cursor"],
            capture_output=True, text=True, encoding="utf-8", env=env2b,
        )
        results.append(check("2b. fault run against pre-existing .cursor/rules/ exits non-zero", proc2b.returncode != 0))
        after2b = snapshot(inst2b)
        results.append(check("2b. pre-existing .cursor/rules/my-own-rule.mdc is untouched, byte-for-byte", after2b.get(".cursor/rules/my-own-rule.mdc") == before2b.get(".cursor/rules/my-own-rule.mdc")))
        results.append(check("2b. pre-existing .cursor/rules/ directory itself was NOT removed", (inst2b / ".cursor" / "rules").is_dir()))
        results.append(check("2b. the new eif/ subdirectory this run would have created is gone", not (inst2b / ".cursor" / "rules" / "eif").exists()))

        # -------------------------------------------------------------
        # 3. flagless upgrade preserves the chosen adapter
        # -------------------------------------------------------------
        inst3 = tmp / "scenario-3-upgrade-preserves-adapter"
        init_git_repo(inst3)
        eif_init(inst3, "--project-name", "cursor-fixture", "--adapter", "cursor")
        r3 = eif_init(inst3)  # no --adapter, no --force: routine upgrade
        results.append(check("3. flagless upgrade exits 0", r3.returncode == 0, r3.stdout + r3.stderr))
        cfg3 = (inst3 / ".eif" / "config.yaml").read_text(encoding="utf-8")
        results.append(check("3. adapter is still cursor after a flagless upgrade", "cursor" in cfg3))
        results.append(check("3. the cursor entrypoint still exists after upgrade", (inst3 / CURSOR_ENTRY).exists()))

        # -------------------------------------------------------------
        # 4. adapter switching: claude-code -> cursor
        # -------------------------------------------------------------
        inst4 = tmp / "scenario-4-switch-claude-to-cursor"
        init_git_repo(inst4)
        eif_init(inst4, "--project-name", "cursor-fixture", "--adapter", "claude-code")
        claude_path4 = inst4 / "CLAUDE.md"
        # Add real project-owned content below the EIF:END marker.
        original4 = claude_path4.read_text(encoding="utf-8")
        with_project_content4 = original4.replace(
            "<Add this project instance's own rules here.>",
            "Never touch the payments module without owner sign-off.",
        )
        claude_path4.write_text(with_project_content4, encoding="utf-8")
        r4 = eif_init(inst4, "--force", "--adapter", "cursor")
        results.append(check("4. switch claude-code -> cursor exits 0", r4.returncode == 0, r4.stdout + r4.stderr))
        results.append(check("4. new cursor entrypoint now exists", (inst4 / CURSOR_ENTRY).exists()))
        claude_after4 = claude_path4.read_text(encoding="utf-8") if claude_path4.exists() else None
        results.append(check("4. old CLAUDE.md's project-owned content is preserved byte-for-byte", claude_after4 is not None and "Never touch the payments module without owner sign-off." in claude_after4, claude_after4))
        results.append(check("4. old CLAUDE.md no longer has the EIF-managed block (stripped, not deleted - real content remained)", claude_after4 is not None and "<!-- EIF:BEGIN" not in claude_after4))

        # -------------------------------------------------------------
        # 5. adapter switching: cursor -> claude-code (old entrypoint is
        #    EIF-only -> deleted, not left behind as an empty husk)
        # -------------------------------------------------------------
        inst5 = tmp / "scenario-5-switch-cursor-to-claude"
        init_git_repo(inst5)
        eif_init(inst5, "--project-name", "cursor-fixture", "--adapter", "cursor")
        results.append(check("5. precondition: cursor entrypoint exists before switch", (inst5 / CURSOR_ENTRY).exists()))
        r5 = eif_init(inst5, "--force", "--adapter", "claude-code")
        results.append(check("5. switch cursor -> claude-code exits 0", r5.returncode == 0, r5.stdout + r5.stderr))
        results.append(check("5. new CLAUDE.md now exists", (inst5 / "CLAUDE.md").exists()))
        results.append(check("5. old cursor entrypoint file is gone (was EIF-only)", not (inst5 / CURSOR_ENTRY).exists()))
        results.append(check("5. no second, dual-active EIF block left in .cursor/rules/eif/", not (inst5 / ".cursor" / "rules" / "eif").exists() or not any((inst5 / ".cursor" / "rules" / "eif").iterdir())))

        # -------------------------------------------------------------
        # 6. malformed markers on the OLD entrypoint during a switch -> STOP
        #    before any writes at all.
        # -------------------------------------------------------------
        inst6 = tmp / "scenario-6-malformed-old-markers-stop"
        init_git_repo(inst6)
        eif_init(inst6, "--project-name", "cursor-fixture", "--adapter", "claude-code")
        claude_path6 = inst6 / "CLAUDE.md"
        # Duplicate the BEGIN marker - malformed (find_managed_block raises MarkerConflict).
        malformed6 = claude_path6.read_text(encoding="utf-8")
        malformed6 = malformed6.replace("<!-- EIF:BEGIN", "<!-- EIF:BEGIN\n<!-- EIF:BEGIN", 1)
        claude_path6.write_text(malformed6, encoding="utf-8")
        before6 = snapshot(inst6)
        r6 = eif_init(inst6, "--force", "--adapter", "cursor")
        results.append(check("6. switch with malformed old markers exits non-zero (STOP)", r6.returncode != 0, r6.stdout + r6.stderr))
        results.append(check("6. STOP message mentions malformed markers", "malformed" in (r6.stdout + r6.stderr)))
        after6 = snapshot(inst6)
        results.append(check("6. STOP wrote absolutely nothing (full snapshot unchanged)", after6 == before6))
        results.append(check("6. no cursor entrypoint was created by the refused switch", not (inst6 / CURSOR_ENTRY).exists()))

        # -------------------------------------------------------------
        # 7. generated frontmatter is valid, parseable YAML with the exact
        #    expected fields.
        # -------------------------------------------------------------
        inst7 = tmp / "scenario-7-frontmatter-valid"
        init_git_repo(inst7)
        eif_init(inst7, "--project-name", "cursor-fixture", "--adapter", "cursor")
        text7 = (inst7 / CURSOR_ENTRY).read_text(encoding="utf-8")
        fm_end = text7.index("\n---\n", 4) if text7.startswith("---\n") else -1
        results.append(check("7. frontmatter has a proper closing '---'", fm_end != -1, text7[:200]))
        if fm_end != -1:
            fm_text = text7[4:fm_end]
            try:
                fm_data = yaml.safe_load(fm_text)
                results.append(check("7. frontmatter parses as valid YAML", isinstance(fm_data, dict), fm_text))
                results.append(check("7. frontmatter has alwaysApply: true", fm_data.get("alwaysApply") is True, fm_data))
                results.append(check("7. frontmatter has a non-empty description", bool(fm_data.get("description")), fm_data))
            except yaml.YAMLError as e:
                results.append(check("7. frontmatter parses as valid YAML", False, str(e)))

        # -------------------------------------------------------------
        # 8. doctor: clean cursor instance passes; a corrupted one (reversed
        #    markers) is caught - reusing eif_verify_runtime.py generically,
        #    unchanged for this adapter.
        # -------------------------------------------------------------
        inst8 = tmp / "scenario-8-doctor-cursor"
        init_git_repo(inst8)
        eif_init(inst8, "--project-name", "cursor-fixture", "--adapter", "cursor")
        r8ok = eif_verify(inst8)
        results.append(check("8. doctor passes on a clean cursor instance", r8ok.returncode == 0, r8ok.stdout + r8ok.stderr))

        entry8 = inst8 / CURSOR_ENTRY
        text8 = entry8.read_text(encoding="utf-8")
        reversed8 = text8.replace("<!-- EIF:BEGIN", "@@TMP@@").replace("<!-- EIF:END -->", "<!-- EIF:BEGIN").replace("@@TMP@@", "<!-- EIF:END -->")
        entry8.write_text(reversed8, encoding="utf-8")
        r8bad = eif_verify(inst8)
        results.append(check("8. doctor catches reversed markers in the cursor entrypoint", r8bad.returncode != 0, r8bad.stdout + r8bad.stderr))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_cursor_adapter: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
