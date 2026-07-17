#!/usr/bin/env python3
"""Codex adapter acceptance tests (Stage 3).

Covers what is genuinely NEW in this adapter, end-to-end via the real CLI
(subprocess, same convention as test_cursor_adapter.py) rather than only
unit-testing internals. Codex's entrypoint (AGENTS.md) is entry_strategy=
"marker-merge" like CLAUDE.md (a flat file at the instance root, not a
nested dedicated file like Cursor's .mdc) - so most scenarios mirror
CLAUDE.md's own contract. What's genuinely unique to Codex, verified
against the live official contract (developers.openai.com/codex/guides/
agents-md, and empirically via `codex debug prompt-input` against a
disposable probe project - see adapters/codex/README.md), is:

 - AGENTS.override.md in the SAME directory as AGENTS.md makes Codex never
   read AGENTS.md's content at all (confirmed empirically, not assumed) -
   scenarios 9/10 below.
 - Nested AGENTS.md/AGENTS.override.md files in subdirectories are part of
   Codex's own instruction chain (unlike Cursor's AGENTS.md, which is a
   wholly separate mechanism) - scenarios 11/12.

 1. greenfield codex init.
 2. flagless upgrade preserves the chosen adapter.
 3. adapter switching claude-code -> codex: old CLAUDE.md project content
    preserved byte-for-byte, EIF block stripped not deleted.
 4. adapter switching codex -> claude-code: old AGENTS.md deleted (was
    EIF-only).
 5. malformed markers on the OLD entrypoint during a switch -> STOP before
    any writes.
 6. malformed EIF target on a plain upgrade (not switching) -> STOP.
 7. doctor passes on a clean codex instance; catches reversed markers.
 8. existing real AGENTS.md content, no adoption decision -> STOP; coexist
    preserves it (appended after, not overwritten).
 9. AGENTS.override.md next to AGENTS.md -> WARN (not STOP - the write
    itself is still safe), independent of adoption mode; AGENTS.override.md
    itself is never touched.
10. the WARN does not also appear as a duplicate generic "other governance"
    entry (would be misleading: choosing an adoption mode does not resolve
    a shadow signal the way it resolves everything else that block covers).
11. nested-subdirectory AGENTS.md, no adoption decision -> STOP; coexist
    preserves it untouched (a genuinely different, non-shadowing case from
    9/10 - reported via the generic governance-surfaces channel).
12. a nested-subdirectory AGENTS.override.md is discovered the same way as
    11 (also a nested file, not a same-dir shadow of OUR entrypoint).
13/14. EN/UK generation.
15. generated search command is extracted and actually executed against a
    seeded fixture.
16. privacy scan against a codex instance.
17. rollback: fault injection immediately after the entrypoint stage
    commits -> full rollback (flat marker-merge file, no directories to
    create/remove the way Cursor's nested .mdc needed).
18. exactly one active EIF block after a successful switch, both
    directions.

Usage:
    python scripts/tests/test_codex_adapter.py
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import tempfile
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = FRAMEWORK_ROOT / "scripts"

CODEX_ENTRY = Path("AGENTS.md")


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
    git(["config", "user.name", "Codex Adapter Test"], root)


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
        # 1. greenfield codex init
        # -------------------------------------------------------------
        inst1 = tmp / "scenario-1-greenfield-codex"
        init_git_repo(inst1)
        r1 = eif_init(inst1, "--project-name", "codex-fixture", "--adapter", "codex")
        results.append(check("1. greenfield codex init exits 0", r1.returncode == 0, r1.stdout + r1.stderr))
        entry1 = inst1 / CODEX_ENTRY
        results.append(check("1. AGENTS.md was created", entry1.exists()))
        text1 = entry1.read_text(encoding="utf-8") if entry1.exists() else ""
        results.append(check("1. entrypoint contains the EIF-managed block", "<!-- EIF:BEGIN" in text1 and "<!-- EIF:END -->" in text1))
        results.append(check("1. entrypoint contains governance content (Knowledge Delta)", "Knowledge Delta" in text1))
        results.append(check("1. entrypoint correctly names itself (not a stale 'CLAUDE.md' reference)", "AGENTS.md/.gitignore marker integrity" in text1, text1))
        cfg1 = (inst1 / ".eif" / "config.yaml").read_text(encoding="utf-8")
        results.append(check("1. config records adapter.name: codex", "codex" in cfg1))
        lock1 = (inst1 / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8")
        results.append(check("1. lock records the entrypoint path AGENTS.md", "AGENTS.md" in lock1, lock1))

        # -------------------------------------------------------------
        # 2. flagless upgrade preserves the chosen adapter
        # -------------------------------------------------------------
        inst2 = tmp / "scenario-2-upgrade-preserves-adapter"
        init_git_repo(inst2)
        eif_init(inst2, "--project-name", "codex-fixture", "--adapter", "codex")
        r2 = eif_init(inst2)  # no --adapter, no --force: routine upgrade
        results.append(check("2. flagless upgrade exits 0", r2.returncode == 0, r2.stdout + r2.stderr))
        cfg2 = (inst2 / ".eif" / "config.yaml").read_text(encoding="utf-8")
        results.append(check("2. adapter is still codex after a flagless upgrade", "codex" in cfg2))
        results.append(check("2. AGENTS.md still exists after upgrade", (inst2 / CODEX_ENTRY).exists()))

        # -------------------------------------------------------------
        # 3. adapter switching: claude-code -> codex
        # -------------------------------------------------------------
        inst3 = tmp / "scenario-3-switch-claude-to-codex"
        init_git_repo(inst3)
        eif_init(inst3, "--project-name", "codex-fixture", "--adapter", "claude-code")
        claude_path3 = inst3 / "CLAUDE.md"
        original3 = claude_path3.read_text(encoding="utf-8")
        with_project_content3 = original3.replace(
            "<Add this project instance's own rules here.>",
            "Never touch the payments module without owner sign-off.",
        )
        claude_path3.write_text(with_project_content3, encoding="utf-8")
        r3 = eif_init(inst3, "--force", "--adapter", "codex")
        results.append(check("3. switch claude-code -> codex exits 0", r3.returncode == 0, r3.stdout + r3.stderr))
        results.append(check("3. new AGENTS.md now exists", (inst3 / CODEX_ENTRY).exists()))
        claude_after3 = claude_path3.read_text(encoding="utf-8") if claude_path3.exists() else None
        results.append(check("3. old CLAUDE.md's project-owned content is preserved byte-for-byte", claude_after3 is not None and "Never touch the payments module without owner sign-off." in claude_after3, claude_after3))
        results.append(check("3. old CLAUDE.md no longer has the EIF-managed block (stripped, not deleted)", claude_after3 is not None and "<!-- EIF:BEGIN" not in claude_after3))

        # -------------------------------------------------------------
        # 4. adapter switching: codex -> claude-code. Both are marker-merge
        #    adapters, so the old entrypoint is STRIPPED (EIF block removed)
        #    but not deleted - eif_init.py only deletes an old marker-merge
        #    entrypoint if nothing but whitespace remains once the block is
        #    gone, and the "Project-specific rules" placeholder footer is
        #    always non-empty. Contrast with Cursor's dedicated full-regen
        #    file, which IS always deleted outright (it never has real
        #    content outside the block by contract).
        # -------------------------------------------------------------
        inst4 = tmp / "scenario-4-switch-codex-to-claude"
        init_git_repo(inst4)
        eif_init(inst4, "--project-name", "codex-fixture", "--adapter", "codex")
        results.append(check("4. precondition: AGENTS.md exists before switch", (inst4 / CODEX_ENTRY).exists()))
        r4 = eif_init(inst4, "--force", "--adapter", "claude-code")
        results.append(check("4. switch codex -> claude-code exits 0", r4.returncode == 0, r4.stdout + r4.stderr))
        results.append(check("4. new CLAUDE.md now exists", (inst4 / "CLAUDE.md").exists()))
        agents_after4 = (inst4 / CODEX_ENTRY).read_text(encoding="utf-8") if (inst4 / CODEX_ENTRY).exists() else None
        results.append(check("4. old AGENTS.md still exists (stripped, not deleted - marker-merge with only the unfilled placeholder remaining)", agents_after4 is not None, agents_after4))
        results.append(check("4. old AGENTS.md no longer has the EIF-managed block", agents_after4 is not None and "<!-- EIF:BEGIN" not in agents_after4))

        # -------------------------------------------------------------
        # 5. malformed markers on the OLD entrypoint during a switch -> STOP
        # -------------------------------------------------------------
        inst5 = tmp / "scenario-5-malformed-old-markers-stop"
        init_git_repo(inst5)
        eif_init(inst5, "--project-name", "codex-fixture", "--adapter", "claude-code")
        claude_path5 = inst5 / "CLAUDE.md"
        malformed5 = claude_path5.read_text(encoding="utf-8").replace("<!-- EIF:BEGIN", "<!-- EIF:BEGIN\n<!-- EIF:BEGIN", 1)
        claude_path5.write_text(malformed5, encoding="utf-8")
        before5 = snapshot(inst5)
        r5 = eif_init(inst5, "--force", "--adapter", "codex")
        results.append(check("5. switch with malformed old markers exits non-zero (STOP)", r5.returncode != 0, r5.stdout + r5.stderr))
        results.append(check("5. STOP message mentions malformed markers", "malformed" in (r5.stdout + r5.stderr)))
        after5 = snapshot(inst5)
        results.append(check("5. STOP wrote absolutely nothing (full snapshot unchanged)", after5 == before5))
        results.append(check("5. no AGENTS.md was created by the refused switch", not (inst5 / CODEX_ENTRY).exists()))

        # -------------------------------------------------------------
        # 6. malformed EIF target on a plain upgrade (not switching) -> STOP
        # -------------------------------------------------------------
        inst6 = tmp / "scenario-6-malformed-target-stop"
        init_git_repo(inst6)
        eif_init(inst6, "--project-name", "codex-fixture", "--adapter", "codex")
        entry6 = inst6 / CODEX_ENTRY
        malformed6 = entry6.read_text(encoding="utf-8").replace("<!-- EIF:BEGIN", "<!-- EIF:BEGIN\n<!-- EIF:BEGIN", 1)
        entry6.write_text(malformed6, encoding="utf-8")
        r6 = eif_init(inst6)  # flagless upgrade, same adapter
        results.append(check("6. malformed EIF target on a plain upgrade -> STOP", r6.returncode != 0, r6.stdout + r6.stderr))
        results.append(check("6. STOP message mentions malformed markers", "malformed" in (r6.stdout + r6.stderr), r6.stdout + r6.stderr))

        # -------------------------------------------------------------
        # 7. doctor: clean codex instance passes; reversed markers caught.
        # -------------------------------------------------------------
        inst7 = tmp / "scenario-7-doctor-codex"
        init_git_repo(inst7)
        eif_init(inst7, "--project-name", "codex-fixture", "--adapter", "codex")
        r7ok = eif_verify(inst7)
        results.append(check("7. doctor passes on a clean codex instance", r7ok.returncode == 0, r7ok.stdout + r7ok.stderr))

        entry7 = inst7 / CODEX_ENTRY
        text7 = entry7.read_text(encoding="utf-8")
        reversed7 = text7.replace("<!-- EIF:BEGIN", "@@TMP@@").replace("<!-- EIF:END -->", "<!-- EIF:BEGIN").replace("@@TMP@@", "<!-- EIF:END -->")
        entry7.write_text(reversed7, encoding="utf-8")
        r7bad = eif_verify(inst7)
        results.append(check("7. doctor catches reversed markers in AGENTS.md", r7bad.returncode != 0, r7bad.stdout + r7bad.stderr))

        # -------------------------------------------------------------
        # 8. existing real AGENTS.md content, no adoption decision -> STOP;
        #    coexist preserves it (appended after, not overwritten).
        # -------------------------------------------------------------
        inst8 = tmp / "scenario-8-existing-content-stop-then-coexist"
        init_git_repo(inst8)
        existing_content8 = "# Our own agent notes\n\nDo not run destructive migrations without review.\n"
        (inst8 / CODEX_ENTRY).write_text(existing_content8, encoding="utf-8")
        before8 = snapshot(inst8)
        r8 = eif_init(inst8, "--project-name", "codex-fixture", "--adapter", "codex")
        results.append(check("8. existing AGENTS.md content, no adoption decision -> STOP", r8.returncode != 0, r8.stdout + r8.stderr))
        after8 = snapshot(inst8)
        results.append(check("8. tree unchanged after STOP", after8 == before8))
        r8b = eif_init(inst8, "--project-name", "codex-fixture", "--adapter", "codex", "--adoption-mode", "coexist")
        results.append(check("8b. coexist with existing AGENTS.md content exits 0", r8b.returncode == 0, r8b.stdout + r8b.stderr))
        text8b = (inst8 / CODEX_ENTRY).read_text(encoding="utf-8")
        results.append(check("8b. original content is preserved", "Do not run destructive migrations without review." in text8b))
        results.append(check("8b. EIF-managed block was appended", "<!-- EIF:BEGIN" in text8b and "<!-- EIF:END -->" in text8b))

        # -------------------------------------------------------------
        # 9. AGENTS.override.md next to AGENTS.md -> WARN (never STOP - the
        #    write itself is safe), independent of adoption mode.
        # -------------------------------------------------------------
        inst9 = tmp / "scenario-9-override-shadow-warn"
        init_git_repo(inst9)
        override_content9 = "Project override content.\n"
        (inst9 / "AGENTS.override.md").write_text(override_content9, encoding="utf-8")
        r9 = eif_init(inst9, "--project-name", "codex-fixture", "--adapter", "codex")
        results.append(check("9. init with a same-dir AGENTS.override.md still exits 0 (WARN, not STOP)", r9.returncode == 0, r9.stdout + r9.stderr))
        results.append(check("9. WARN names AGENTS.override.md", "AGENTS.override.md" in (r9.stdout + r9.stderr), r9.stdout + r9.stderr))
        results.append(check("9. WARN explains it is independent of adoption mode", "independent of adoption mode" in (r9.stdout + r9.stderr), r9.stdout + r9.stderr))
        results.append(check("9. AGENTS.md was still created despite the shadow", (inst9 / CODEX_ENTRY).exists()))
        results.append(check("9. AGENTS.override.md itself is untouched, byte-for-byte", (inst9 / "AGENTS.override.md").read_text(encoding="utf-8") == override_content9))

        # -------------------------------------------------------------
        # 10. the shadow WARN is not ALSO reported as a duplicate generic
        #     "other governance surface" STOP/OK entry for the same file.
        # -------------------------------------------------------------
        results.append(check(
            "10. no duplicate 'existing governance surface(s) detected' line mentions AGENTS.override.md",
            "existing governance surface(s) detected" not in (r9.stdout + r9.stderr)
            or "AGENTS.override.md" not in (r9.stdout + r9.stderr).split("existing governance surface(s) detected", 1)[-1].split("\n", 1)[0],
            r9.stdout + r9.stderr,
        ))

        # -------------------------------------------------------------
        # 11. nested-subdirectory AGENTS.md, no adoption decision -> STOP;
        #     coexist preserves it untouched (distinct from 9/10: a genuinely
        #     different, non-shadowing file).
        # -------------------------------------------------------------
        inst11 = tmp / "scenario-11-nested-agents-md"
        init_git_repo(inst11)
        (inst11 / "packages" / "sub").mkdir(parents=True)
        nested_content11 = "Sub-package instructions.\n"
        (inst11 / "packages" / "sub" / "AGENTS.md").write_text(nested_content11, encoding="utf-8")
        before11 = snapshot(inst11)
        r11 = eif_init(inst11, "--project-name", "codex-fixture", "--adapter", "codex")
        results.append(check("11. nested AGENTS.md, no adoption decision -> STOP", r11.returncode != 0, r11.stdout + r11.stderr))
        results.append(check("11. STOP output names the nested path", "packages/sub/AGENTS.md" in (r11.stdout + r11.stderr) or "packages\\sub\\AGENTS.md" in (r11.stdout + r11.stderr), r11.stdout + r11.stderr))
        after11 = snapshot(inst11)
        results.append(check("11. tree unchanged after STOP", after11 == before11))
        r11b = eif_init(inst11, "--project-name", "codex-fixture", "--adapter", "codex", "--adoption-mode", "coexist")
        results.append(check("11b. coexist with nested AGENTS.md exits 0", r11b.returncode == 0, r11b.stdout + r11b.stderr))
        results.append(check("11b. nested AGENTS.md preserved byte-for-byte", (inst11 / "packages" / "sub" / "AGENTS.md").read_text(encoding="utf-8") == nested_content11))
        results.append(check("11b. root AGENTS.md was still created", (inst11 / CODEX_ENTRY).exists()))

        # -------------------------------------------------------------
        # 12. a nested-subdirectory AGENTS.override.md is discovered the
        #     same way as 11 (a nested file, not a same-dir shadow).
        # -------------------------------------------------------------
        inst12 = tmp / "scenario-12-nested-agents-override"
        init_git_repo(inst12)
        (inst12 / "packages" / "sub").mkdir(parents=True)
        (inst12 / "packages" / "sub" / "AGENTS.override.md").write_text("Sub-package override.\n", encoding="utf-8")
        r12 = eif_init(inst12, "--project-name", "codex-fixture", "--adapter", "codex")
        results.append(check("12. nested AGENTS.override.md, no adoption decision -> STOP", r12.returncode != 0, r12.stdout + r12.stderr))
        results.append(check("12. STOP is the generic governance-surface one, not the shadow WARN (nested file never shadows the root entrypoint)", "existing governance surface(s) detected" in (r12.stdout + r12.stderr), r12.stdout + r12.stderr))

        # -------------------------------------------------------------
        # 13/14. EN and UK generation.
        # -------------------------------------------------------------
        inst13 = tmp / "scenario-13-en-generation"
        init_git_repo(inst13)
        r13 = eif_init(inst13, "--project-name", "codex-fixture", "--adapter", "codex", "--locale", "en")
        results.append(check("13. EN codex init exits 0", r13.returncode == 0, r13.stdout + r13.stderr))
        results.append(check("13. governance content present (EN)", "Knowledge Delta" in (inst13 / CODEX_ENTRY).read_text(encoding="utf-8")))

        inst14 = tmp / "scenario-14-uk-generation"
        init_git_repo(inst14)
        r14 = eif_init(inst14, "--project-name", "codex-fixture", "--adapter", "codex", "--locale", "uk")
        results.append(check("14. UK codex init exits 0", r14.returncode == 0, r14.stdout + r14.stderr))
        results.append(check("14. UK init-complete message present ('ініціалізовано')", "ініціалізовано" in r14.stdout, r14.stdout))

        # -------------------------------------------------------------
        # 15. generated search command actually executes on a codex fixture.
        # -------------------------------------------------------------
        inst15 = tmp / "scenario-15-search-command-runs"
        init_git_repo(inst15)
        eif_init(inst15, "--project-name", "codex-fixture", "--adapter", "codex")
        (inst15 / "knowledge").mkdir(parents=True, exist_ok=True)
        (inst15 / "knowledge" / "fact-1.md").write_text(
            "---\ntype: fact\nstatus: validated\nscope: local\ncreated: 2026-07-17\n---\n\n"
            "Codex search command works.\n",
            encoding="utf-8",
        )
        text15 = (inst15 / CODEX_ENTRY).read_text(encoding="utf-8")
        m15 = re.search(r"`(python \.eif/runtime/eif_search_knowledge\.py[^`]*)`", text15)
        results.append(check("15. generated governance content includes the exact search command", m15 is not None, text15))
        if m15:
            cmd15 = m15.group(1).replace('"<your task in a few words>"', '"search command works"')
            args15 = shlex.split(cmd15)
            args15[0] = sys.executable
            proc15 = subprocess.run(args15, cwd=str(inst15), capture_output=True, text=True, encoding="utf-8")
            results.append(check("15. generated search command actually executes (exit 0) on the codex fixture", proc15.returncode == 0, proc15.stdout + proc15.stderr))
            results.append(check("15. search command finds the seeded fact", "fact-1" in proc15.stdout, proc15.stdout))

        # -------------------------------------------------------------
        # 16. privacy scan runs cleanly against a codex instance.
        # -------------------------------------------------------------
        inst16 = tmp / "scenario-16-privacy-scan"
        init_git_repo(inst16)
        eif_init(inst16, "--project-name", "codex-fixture", "--adapter", "codex")
        r16 = run([str(SCRIPTS / "eif_privacy_scan.py"), "--repo", str(inst16)])
        results.append(check("16. privacy scan runs cleanly against a codex instance", r16.returncode == 0, r16.stdout + r16.stderr))

        # -------------------------------------------------------------
        # 17. rollback: fault injected immediately after the entrypoint
        #     stage commits -> full rollback (flat marker-merge file).
        # -------------------------------------------------------------
        inst17 = tmp / "scenario-17-entrypoint-fault-rollback"
        init_git_repo(inst17)
        env17 = {"PATH": os.environ.get("PATH", ""), "EIF_INIT_TEST_FAIL_AFTER": "entrypoint"}
        proc17 = subprocess.run(
            [sys.executable, str(SCRIPTS / "eif_init.py"), "--framework-root", str(FRAMEWORK_ROOT),
             "--instance-path", str(inst17), "--allow-dirty", "--project-name", "codex-fixture", "--adapter", "codex"],
            capture_output=True, text=True, encoding="utf-8", env=env17,
        )
        results.append(check("17. fault-after-entrypoint run exits non-zero", proc17.returncode != 0, proc17.stdout + proc17.stderr))
        results.append(check("17. no AGENTS.md left behind (this run created it)", not (inst17 / CODEX_ENTRY).exists()))
        results.append(check("17. no .eif/ left behind either", not (inst17 / ".eif").exists()))

        # -------------------------------------------------------------
        # 18. exactly one active EIF block after a successful switch, both
        #     directions.
        # -------------------------------------------------------------
        inst18a = tmp / "scenario-18a-claude-to-codex-single-active"
        init_git_repo(inst18a)
        eif_init(inst18a, "--project-name", "codex-fixture", "--adapter", "claude-code")
        eif_init(inst18a, "--force", "--adapter", "codex")
        claude_after18a = (inst18a / "CLAUDE.md").read_text(encoding="utf-8") if (inst18a / "CLAUDE.md").exists() else ""
        active_blocks_18a = sum([
            1 if "<!-- EIF:BEGIN" in claude_after18a else 0,
            1 if "<!-- EIF:BEGIN" in (inst18a / CODEX_ENTRY).read_text(encoding="utf-8") else 0,
        ])
        results.append(check("18a. exactly one active EIF block after claude->codex switch", active_blocks_18a == 1, active_blocks_18a))

        inst18b = tmp / "scenario-18b-codex-to-claude-single-active"
        init_git_repo(inst18b)
        eif_init(inst18b, "--project-name", "codex-fixture", "--adapter", "codex")
        eif_init(inst18b, "--force", "--adapter", "claude-code")
        codex_has_block_18b = (inst18b / CODEX_ENTRY).exists() and "<!-- EIF:BEGIN" in (inst18b / CODEX_ENTRY).read_text(encoding="utf-8")
        active_blocks_18b = (1 if codex_has_block_18b else 0) + (1 if "<!-- EIF:BEGIN" in (inst18b / "CLAUDE.md").read_text(encoding="utf-8") else 0)
        results.append(check("18b. exactly one active EIF block after codex->claude switch", active_blocks_18b == 1, active_blocks_18b))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_codex_adapter: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
