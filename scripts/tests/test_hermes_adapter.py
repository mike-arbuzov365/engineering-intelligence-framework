#!/usr/bin/env python3
"""Hermes adapter acceptance tests (Stage 4).

Hermes has no single fixed entrypoint filename - it picks ONE of several
candidates per its own first-match precedence (verified live against the
official docs and, for the discovery-scope split below, empirically
against the real installed Hermes CLI via `hermes prompt-size`, an
offline, no-API-call command - see adapters/hermes/README.md):

  .hermes.md / HERMES.md  -> walks from cwd up to the git root (ancestor
                             tier; closest match wins)
  AGENTS.md               -> checked at the instance root ONLY, no parent
                             walk (empirically confirmed: a real root
                             AGENTS.md reports 0 bytes of context when
                             queried from a subdirectory, while a real
                             root .hermes.md reports its full size from
                             that same subdirectory)
  CLAUDE.md               -> same cwd-only scope as AGENTS.md
  .cursorrules            -> last-priority fallback in the same chain
                             (not resolved/adopted by this adapter - see
                             "existing-Cursor-rules" below)

eif_adapters.resolve_dynamic_entrypoint() mirrors this exactly: it never
defaults to creating a NEW, higher-priority file (.hermes.md) when a
lower-priority one (AGENTS.md/CLAUDE.md) already exists at the instance
root - it adopts whichever file is already there. A parent-directory
ancestor-tier match (found above, not AT, the instance root) is reported
as a shadow signal - exactly like Codex's AGENTS.override.md - rather
than silently overridden by a new instance-root file.

 1. greenfield init (nothing exists anywhere) -> defaults to .hermes.md.
 2. existing .hermes.md at the instance root -> adopted.
 3. existing HERMES.md (uppercase variant) at the instance root -> adopted.
 4. existing AGENTS.md at the instance root -> adopted (cwd-only tier);
    shadow-prevention: no NEW .hermes.md is created alongside it.
 5. AGENTS.md cwd-only limitation: a real AGENTS.md in a PARENT directory
    (not the instance root) is NOT adopted - the instance still resolves
    to its own greenfield default, exactly mirroring the empirically-
    confirmed 0-byte result from the real Hermes CLI.
 6. existing CLAUDE.md at the instance root -> adopted.
 7. existing .cursor/rules/*.mdc (Cursor's modern rule format, which
    Hermes's own docs say it also reads) -> detected as existing OTHER
    governance (STOP without a decision, coexist preserves it untouched)
    - never adopted/merged into directly by this adapter.
 8. shadow-prevention across a directory boundary: a real .hermes.md in a
    PARENT directory (ancestor tier, ancestor walk finds it) -> WARN,
    independent of adoption mode, and the parent file itself is never
    touched.
 9. explicit coexist: existing real AGENTS.md content is preserved
    (appended after, not overwritten).
10. the git-root-stopping boundary: an ancestor-tier file placed ABOVE the
    git root is never found (the walk stops exactly at the git root, not
    beyond it), while the identical file placed AT the git root IS found.
11/12. init/upgrade/reconfigure: flagless upgrade preserves the resolved
    entrypoint; --force reconfigure.
13/14. adapter switching claude-code <-> hermes, both directions (with
    the marker-merge "strip not delete" nuance, same as Codex).
15. malformed markers on the OLD entrypoint during a switch -> STOP.
16. doctor: clean pass + reversed-marker catch, including a lock whose
    recorded entrypoint is validated against the candidate SET, not a
    single static value.
17. rollback: fault injection after the entrypoint stage commits.
18/19. EN/UK generation.
20. privacy scan against a Hermes instance.

Usage:
    python scripts/tests/test_hermes_adapter.py
"""
from __future__ import annotations

import os
import subprocess
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import tempfile
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = FRAMEWORK_ROOT / "scripts"


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
    git(["config", "user.name", "Hermes Adapter Test"], root)


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
        # 1. greenfield init - nothing exists, defaults to .hermes.md
        # -------------------------------------------------------------
        inst1 = tmp / "scenario-1-greenfield"
        init_git_repo(inst1)
        r1 = eif_init(inst1, "--project-name", "hermes-fixture", "--adapter", "hermes", "--migration-status", "greenfield")
        results.append(check("1. greenfield hermes init exits 0", r1.returncode == 0, r1.stdout + r1.stderr))
        results.append(check("1. defaults to .hermes.md when nothing exists", (inst1 / ".hermes.md").exists()))
        text1 = (inst1 / ".hermes.md").read_text(encoding="utf-8") if (inst1 / ".hermes.md").exists() else ""
        results.append(check("1. entrypoint contains the EIF-managed block", "<!-- EIF:BEGIN" in text1 and "<!-- EIF:END -->" in text1))
        lock1 = (inst1 / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8")
        results.append(check("1. lock records the resolved entrypoint .hermes.md", ".hermes.md" in lock1, lock1))

        # -------------------------------------------------------------
        # 2. existing .hermes.md at the instance root -> adopted
        # -------------------------------------------------------------
        inst2 = tmp / "scenario-2-existing-dothermes"
        init_git_repo(inst2)
        existing2 = "# Our own Hermes notes\nDo not deploy on Fridays.\n"
        (inst2 / ".hermes.md").write_text(existing2, encoding="utf-8")
        r2 = eif_init(inst2, "--project-name", "hermes-fixture", "--adapter", "hermes", "--adoption-mode", "coexist")
        results.append(check("2. init with existing .hermes.md exits 0", r2.returncode == 0, r2.stdout + r2.stderr))
        text2 = (inst2 / ".hermes.md").read_text(encoding="utf-8")
        results.append(check("2. original .hermes.md content preserved", "Do not deploy on Fridays." in text2))
        results.append(check("2. no HERMES.md/AGENTS.md/CLAUDE.md was also created", not any((inst2 / n).exists() for n in ("HERMES.md", "AGENTS.md", "CLAUDE.md"))))

        # -------------------------------------------------------------
        # 3. existing HERMES.md (uppercase variant) -> adopted
        # -------------------------------------------------------------
        inst3 = tmp / "scenario-3-existing-HERMES"
        init_git_repo(inst3)
        (inst3 / "HERMES.md").write_text("Uppercase variant notes.\n", encoding="utf-8")
        r3 = eif_init(inst3, "--project-name", "hermes-fixture", "--adapter", "hermes", "--adoption-mode", "coexist")
        results.append(check("3. init with existing HERMES.md exits 0", r3.returncode == 0, r3.stdout + r3.stderr))
        text3 = (inst3 / "HERMES.md").read_text(encoding="utf-8") if (inst3 / "HERMES.md").exists() else ""
        results.append(check("3. HERMES.md was adopted (has the EIF block, original content kept)", "<!-- EIF:BEGIN" in text3 and "Uppercase variant notes." in text3, text3))
        results.append(check("3. no separate .hermes.md was created", not (inst3 / ".hermes.md").exists()))

        # -------------------------------------------------------------
        # 4. existing AGENTS.md at the instance root -> adopted;
        #    shadow-prevention: no .hermes.md created alongside it.
        # -------------------------------------------------------------
        inst4 = tmp / "scenario-4-existing-agents-md"
        init_git_repo(inst4)
        (inst4 / "AGENTS.md").write_text("Project agent notes.\n", encoding="utf-8")
        r4 = eif_init(inst4, "--project-name", "hermes-fixture", "--adapter", "hermes", "--adoption-mode", "coexist")
        results.append(check("4. init with existing AGENTS.md exits 0", r4.returncode == 0, r4.stdout + r4.stderr))
        text4 = (inst4 / "AGENTS.md").read_text(encoding="utf-8")
        results.append(check("4. AGENTS.md was adopted (has the EIF block)", "<!-- EIF:BEGIN" in text4))
        results.append(check("4. shadow-prevention: no NEW .hermes.md was created (would have silently shadowed AGENTS.md)", not (inst4 / ".hermes.md").exists()))
        results.append(check("4. shadow-prevention: no NEW HERMES.md was created either", not (inst4 / "HERMES.md").exists()))

        # -------------------------------------------------------------
        # 5. AGENTS.md cwd-only limitation: a real AGENTS.md in a PARENT
        #    directory is never adopted for a nested instance - mirrors
        #    the empirically-confirmed 0-byte real Hermes CLI result.
        # -------------------------------------------------------------
        inst5_parent = tmp / "scenario-5-agents-cwd-only" / "sub"
        init_git_repo(inst5_parent.parent)
        (inst5_parent.parent / "AGENTS.md").write_text("Parent-level agent notes (should NOT be adopted here).\n", encoding="utf-8")
        r5 = eif_init(inst5_parent, "--project-name", "hermes-nested", "--adapter", "hermes", "--migration-status", "greenfield")
        results.append(check("5. init in a subdirectory with a parent AGENTS.md exits 0", r5.returncode == 0, r5.stdout + r5.stderr))
        results.append(check("5. AGENTS.md cwd-only limitation: the parent's AGENTS.md was NOT adopted (defaults to .hermes.md instead)", (inst5_parent / ".hermes.md").exists()))
        results.append(check("5. the parent AGENTS.md itself is untouched (no EIF block)", "<!-- EIF:BEGIN" not in (inst5_parent.parent / "AGENTS.md").read_text(encoding="utf-8")))

        # -------------------------------------------------------------
        # 6. existing CLAUDE.md at the instance root -> adopted
        # -------------------------------------------------------------
        inst6 = tmp / "scenario-6-existing-claude-md"
        init_git_repo(inst6)
        (inst6 / "CLAUDE.md").write_text("Existing Claude notes.\n", encoding="utf-8")
        r6 = eif_init(inst6, "--project-name", "hermes-fixture", "--adapter", "hermes", "--adoption-mode", "coexist")
        results.append(check("6. init with existing CLAUDE.md exits 0", r6.returncode == 0, r6.stdout + r6.stderr))
        text6 = (inst6 / "CLAUDE.md").read_text(encoding="utf-8")
        results.append(check("6. CLAUDE.md was adopted (has the EIF block, original content kept)", "<!-- EIF:BEGIN" in text6 and "Existing Claude notes." in text6))

        # -------------------------------------------------------------
        # 7. existing .cursor/rules/*.mdc -> detected as OTHER governance
        #    (STOP without a decision, coexist preserves it); never
        #    adopted/merged into directly.
        # -------------------------------------------------------------
        inst7 = tmp / "scenario-7-existing-cursor-rules"
        init_git_repo(inst7)
        (inst7 / ".cursor" / "rules").mkdir(parents=True)
        cursor_rule_content7 = "---\nalwaysApply: true\n---\nProject Cursor rule.\n"
        (inst7 / ".cursor" / "rules" / "project.mdc").write_text(cursor_rule_content7, encoding="utf-8")
        before7 = snapshot(inst7)
        r7 = eif_init(inst7, "--project-name", "hermes-fixture", "--adapter", "hermes")
        results.append(check("7. existing .cursor/rules/*.mdc, no adoption decision -> STOP", r7.returncode != 0, r7.stdout + r7.stderr))
        after7 = snapshot(inst7)
        results.append(check("7. tree unchanged after STOP", after7 == before7))
        r7b = eif_init(inst7, "--project-name", "hermes-fixture", "--adapter", "hermes", "--adoption-mode", "coexist")
        results.append(check("7b. coexist with existing Cursor rule exits 0", r7b.returncode == 0, r7b.stdout + r7b.stderr))
        results.append(check("7b. Cursor rule file preserved byte-for-byte", (inst7 / ".cursor" / "rules" / "project.mdc").read_text(encoding="utf-8") == cursor_rule_content7))
        results.append(check("7b. Hermes still got its own default .hermes.md entrypoint", (inst7 / ".hermes.md").exists()))

        # -------------------------------------------------------------
        # 8. shadow-prevention across a directory boundary: a real
        #    .hermes.md in a PARENT directory -> WARN, independent of
        #    adoption mode; the parent file itself is never touched.
        # -------------------------------------------------------------
        inst8_parent_dir = tmp / "scenario-8-parent-shadow"
        inst8 = inst8_parent_dir / "sub"
        init_git_repo(inst8_parent_dir)
        parent_hermes_content8 = "Parent monorepo Hermes context.\n"
        (inst8_parent_dir / ".hermes.md").write_text(parent_hermes_content8, encoding="utf-8")
        r8 = eif_init(inst8, "--project-name", "hermes-sub", "--adapter", "hermes", "--migration-status", "greenfield")
        results.append(check("8. init in a subdir with a parent .hermes.md still exits 0 (WARN, not STOP)", r8.returncode == 0, r8.stdout + r8.stderr))
        # Compare resolved paths, not raw strings: the test constructs this
        # path before resolution (may render an 8.3 short alias on this
        # machine), while eif_init's own resolver always reports the fully
        # resolved (long-form) path - the same file, different string forms.
        results.append(check("8. WARN names the parent .hermes.md path", str((inst8_parent_dir / ".hermes.md").resolve()) in (r8.stdout + r8.stderr), r8.stdout + r8.stderr))
        results.append(check("8. WARN explains it is independent of adoption mode", "independent of adoption mode" in (r8.stdout + r8.stderr)))
        results.append(check("8. the parent .hermes.md is untouched, byte-for-byte", (inst8_parent_dir / ".hermes.md").read_text(encoding="utf-8") == parent_hermes_content8))
        results.append(check("8. the subdirectory still got its own .hermes.md (write itself is safe)", (inst8 / ".hermes.md").exists()))

        # -------------------------------------------------------------
        # 9. explicit coexist: existing real AGENTS.md content preserved
        #    (appended after, not overwritten) - already exercised by
        #    scenario 4/4b above via --adoption-mode coexist; this adds
        #    the explicit STOP-then-coexist pairing test_cursor_adapter.py
        #    and test_codex_adapter.py both use for their own equivalents.
        # -------------------------------------------------------------
        inst9 = tmp / "scenario-9-explicit-coexist-stop-then-ok"
        init_git_repo(inst9)
        existing9 = "# Real project instructions\nNever skip the payment reconciliation step.\n"
        (inst9 / "AGENTS.md").write_text(existing9, encoding="utf-8")
        before9 = snapshot(inst9)
        r9 = eif_init(inst9, "--project-name", "hermes-fixture", "--adapter", "hermes")
        results.append(check("9. existing AGENTS.md content, no adoption decision -> STOP", r9.returncode != 0, r9.stdout + r9.stderr))
        after9 = snapshot(inst9)
        results.append(check("9. tree unchanged after STOP", after9 == before9))
        r9b = eif_init(inst9, "--project-name", "hermes-fixture", "--adapter", "hermes", "--adoption-mode", "coexist")
        results.append(check("9b. coexist exits 0", r9b.returncode == 0, r9b.stdout + r9b.stderr))
        text9b = (inst9 / "AGENTS.md").read_text(encoding="utf-8")
        results.append(check("9b. original content preserved", "Never skip the payment reconciliation step." in text9b))

        # -------------------------------------------------------------
        # 10. git-root-stopping boundary: an ancestor-tier file ABOVE the
        #     git root is never found; the identical file AT the git root
        #     IS found.
        # -------------------------------------------------------------
        outside_root10 = tmp / "scenario-10-git-root-boundary"
        repo10 = outside_root10 / "repo"
        deep10 = repo10 / "a" / "b"
        deep10.mkdir(parents=True)
        (outside_root10 / ".hermes.md").write_text("OUTSIDE the git repo - must never be found.\n", encoding="utf-8")
        init_git_repo(repo10)
        r10a = eif_init(deep10, "--project-name", "hermes-boundary", "--adapter", "hermes", "--migration-status", "greenfield")
        results.append(check("10a. init deep inside a repo with a .hermes.md OUTSIDE the repo exits 0", r10a.returncode == 0, r10a.stdout + r10a.stderr))
        results.append(check("10a. the outside-repo .hermes.md is never adopted (walk stops at git root)", (deep10 / ".hermes.md").exists() and "<!-- EIF:BEGIN" in (deep10 / ".hermes.md").read_text(encoding="utf-8")))
        results.append(check("10a. the outside-repo .hermes.md itself is untouched", "OUTSIDE the git repo" in (outside_root10 / ".hermes.md").read_text(encoding="utf-8") and "<!-- EIF:BEGIN" not in (outside_root10 / ".hermes.md").read_text(encoding="utf-8")))
        results.append(check("10a. no parent-shadow WARN fires (the outside file is genuinely out of the walk's reach)", "independent of adoption mode" not in (r10a.stdout + r10a.stderr), r10a.stdout + r10a.stderr))

        repo10b_root = tmp / "scenario-10b-git-root-itself"
        deep10b = repo10b_root / "a" / "b"
        deep10b.mkdir(parents=True)
        init_git_repo(repo10b_root)
        (repo10b_root / ".hermes.md").write_text("AT the git root - must be found from deep inside.\n", encoding="utf-8")
        r10b = eif_init(deep10b, "--project-name", "hermes-boundary-b", "--adapter", "hermes", "--migration-status", "greenfield")
        results.append(check("10b. init deep inside a repo with .hermes.md AT the git root exits 0", r10b.returncode == 0, r10b.stdout + r10b.stderr))
        # The git-root file is found by the ancestor walk (proving the walk
        # reaches exactly that far) but is NOT at the instance root itself -
        # this is the same parent-shadow case as scenario 8, just found at
        # the boundary rather than one level up, so it WARNs rather than
        # silently defaulting.
        results.append(check("10b. WARN fires for the git-root file (found by the walk, not silently ignored)", "independent of adoption mode" in (r10b.stdout + r10b.stderr), r10b.stdout + r10b.stderr))
        results.append(check("10b. the deep instance still gets its own .hermes.md (write itself is safe)", (deep10b / ".hermes.md").exists()))
        text10b = (repo10b_root / ".hermes.md").read_text(encoding="utf-8")
        results.append(check("10b. the git-root .hermes.md itself remains untouched by the deep instance's own init", "AT the git root" in text10b and "<!-- EIF:BEGIN" not in text10b, text10b))

        # -------------------------------------------------------------
        # 11/12. flagless upgrade preserves the resolved entrypoint;
        #        --force reconfigure.
        # -------------------------------------------------------------
        inst11 = tmp / "scenario-11-upgrade-preserves-entrypoint"
        init_git_repo(inst11)
        eif_init(inst11, "--project-name", "hermes-fixture", "--adapter", "hermes", "--migration-status", "greenfield")
        r11 = eif_init(inst11)  # flagless upgrade
        results.append(check("11. flagless upgrade exits 0", r11.returncode == 0, r11.stdout + r11.stderr))
        cfg11 = (inst11 / ".eif" / "config.yaml").read_text(encoding="utf-8")
        results.append(check("11. adapter is still hermes after a flagless upgrade", "hermes" in cfg11))
        results.append(check("11. .hermes.md still exists after upgrade", (inst11 / ".hermes.md").exists()))

        # -------------------------------------------------------------
        # 13/14. adapter switching claude-code <-> hermes, both directions.
        #
        # 13 is a real, previously-crashing edge case found while building
        # this adapter: CLAUDE.md is both claude-code's own fixed
        # entrypoint AND one of Hermes's own candidates, so switching
        # claude-code -> hermes lands BOTH the "old entrypoint" (claude-
        # code, being switched away from) and the "new entrypoint" (hermes,
        # dynamically resolved) on the IDENTICAL path. The transaction
        # originally double-staged the same <path>.next file for two
        # separate stages ("entrypoint" and "old-entrypoint"), and the
        # second stage to commit crashed with "staged artifact missing"
        # once the first had already consumed it. Fixed by recognizing the
        # same-path case in eif_init.py and skipping the redundant
        # "old-entrypoint" stage entirely - the "entrypoint" stage's own
        # marker-merge already replaces the old block with the new one on
        # that single file.
        # -------------------------------------------------------------
        inst13 = tmp / "scenario-13-switch-claude-to-hermes-same-path"
        init_git_repo(inst13)
        eif_init(inst13, "--project-name", "hermes-fixture", "--adapter", "claude-code", "--migration-status", "greenfield")
        claude_path13 = inst13 / "CLAUDE.md"
        with_project_content13 = claude_path13.read_text(encoding="utf-8").replace(
            "<Add this project instance's own rules here.>",
            "Never touch the payments module without owner sign-off.",
        )
        claude_path13.write_text(with_project_content13, encoding="utf-8")
        r13 = eif_init(inst13, "--force", "--adapter", "hermes")
        results.append(check("13. switch claude-code -> hermes exits 0 (same-path collision handled, not a crash)", r13.returncode == 0, r13.stdout + r13.stderr))
        results.append(check("13. hermes resolver adopted the EXISTING CLAUDE.md rather than defaulting to a new .hermes.md", "existing 'CLAUDE.md' found at the instance root" in r13.stdout, r13.stdout))
        results.append(check("13. no separate .hermes.md was also created", not (inst13 / ".hermes.md").exists()))
        claude_after13 = claude_path13.read_text(encoding="utf-8") if claude_path13.exists() else None
        results.append(check("13. project-owned content preserved byte-for-byte across the switch", claude_after13 is not None and "Never touch the payments module without owner sign-off." in claude_after13, claude_after13))
        results.append(check("13. CLAUDE.md still has an EIF-managed block (now Hermes's, refreshed in place - not stripped, since it's also the NEW entrypoint)", claude_after13 is not None and "<!-- EIF:BEGIN" in claude_after13))

        # -------------------------------------------------------------
        # 13b. the genuinely-separate-file case: switching FROM Cursor
        #      (whose full-regen entrypoint, .cursor/rules/eif/
        #      governance.mdc, never collides with any Hermes candidate)
        #      TO hermes with nothing else present - hermes correctly
        #      defaults to a NEW .hermes.md, and Cursor's own dedicated
        #      file is deleted outright (full-regen contract), no collision.
        # -------------------------------------------------------------
        inst13b = tmp / "scenario-13b-switch-cursor-to-hermes-distinct-paths"
        init_git_repo(inst13b)
        eif_init(inst13b, "--project-name", "hermes-fixture", "--adapter", "cursor", "--migration-status", "greenfield")
        cursor_entry13b = inst13b / ".cursor" / "rules" / "eif" / "governance.mdc"
        results.append(check("13b. precondition: cursor entrypoint exists before switch", cursor_entry13b.exists()))
        # Cursor's own (about-to-be-replaced) entrypoint still matches
        # Hermes's own governance_discovery glob (.cursor/rules/**/*.mdc -
        # Hermes's docs say it reads these too), so it is correctly detected
        # as existing "other governance" needing an explicit decision, same
        # as any other adapter-switch scenario - --adoption-mode greenfield
        # is the informed override (it will be deleted by the switch itself
        # a moment later regardless).
        r13b = eif_init(inst13b, "--force", "--adapter", "hermes", "--adoption-mode", "greenfield")
        results.append(check("13b. switch cursor -> hermes exits 0", r13b.returncode == 0, r13b.stdout + r13b.stderr))
        results.append(check("13b. hermes correctly defaults to a NEW .hermes.md (nothing else existed)", "no existing candidate found anywhere" in r13b.stdout, r13b.stdout))
        results.append(check("13b. .hermes.md now exists", (inst13b / ".hermes.md").exists()))
        results.append(check("13b. old cursor entrypoint is gone (full-regen: always deleted outright on switch-away)", not cursor_entry13b.exists()))

        inst14 = tmp / "scenario-14-switch-hermes-to-claude"
        init_git_repo(inst14)
        eif_init(inst14, "--project-name", "hermes-fixture", "--adapter", "hermes", "--migration-status", "greenfield")
        results.append(check("14. precondition: .hermes.md exists before switch", (inst14 / ".hermes.md").exists()))
        r14 = eif_init(inst14, "--force", "--adapter", "claude-code")
        results.append(check("14. switch hermes -> claude-code exits 0", r14.returncode == 0, r14.stdout + r14.stderr))
        results.append(check("14. new CLAUDE.md now exists", (inst14 / "CLAUDE.md").exists()))
        hermes_after14 = (inst14 / ".hermes.md").read_text(encoding="utf-8") if (inst14 / ".hermes.md").exists() else None
        results.append(check("14. old .hermes.md still exists (stripped, not deleted - marker-merge with only the unfilled placeholder remaining)", hermes_after14 is not None, hermes_after14))
        results.append(check("14. old .hermes.md no longer has the EIF-managed block", hermes_after14 is not None and "<!-- EIF:BEGIN" not in hermes_after14))

        # -------------------------------------------------------------
        # 15. malformed markers on the OLD entrypoint during a switch ->
        #     STOP before any writes at all.
        # -------------------------------------------------------------
        inst15 = tmp / "scenario-15-malformed-old-markers-stop"
        init_git_repo(inst15)
        eif_init(inst15, "--project-name", "hermes-fixture", "--adapter", "hermes", "--migration-status", "greenfield")
        entry15 = inst15 / ".hermes.md"
        malformed15 = entry15.read_text(encoding="utf-8").replace("<!-- EIF:BEGIN", "<!-- EIF:BEGIN\n<!-- EIF:BEGIN", 1)
        entry15.write_text(malformed15, encoding="utf-8")
        before15 = snapshot(inst15)
        r15 = eif_init(inst15, "--force", "--adapter", "claude-code")
        results.append(check("15. switch with malformed old markers exits non-zero (STOP)", r15.returncode != 0, r15.stdout + r15.stderr))
        results.append(check("15. STOP message mentions malformed markers", "malformed" in (r15.stdout + r15.stderr)))
        after15 = snapshot(inst15)
        results.append(check("15. STOP wrote absolutely nothing (full snapshot unchanged)", after15 == before15))
        results.append(check("15. no CLAUDE.md was created by the refused switch", not (inst15 / "CLAUDE.md").exists()))

        # -------------------------------------------------------------
        # 16. doctor: clean pass + reversed-marker catch; lock entrypoint
        #     validated against the candidate SET, not a single value.
        # -------------------------------------------------------------
        inst16 = tmp / "scenario-16-doctor-hermes"
        init_git_repo(inst16)
        eif_init(inst16, "--project-name", "hermes-fixture", "--adapter", "hermes", "--migration-status", "greenfield")
        r16ok = eif_verify(inst16)
        results.append(check("16. doctor passes on a clean hermes instance (default .hermes.md)", r16ok.returncode == 0, r16ok.stdout + r16ok.stderr))

        inst16b = tmp / "scenario-16b-doctor-hermes-agents-md"
        init_git_repo(inst16b)
        (inst16b / "AGENTS.md").write_text("Existing notes.\n", encoding="utf-8")
        eif_init(inst16b, "--project-name", "hermes-fixture", "--adapter", "hermes", "--adoption-mode", "coexist")
        r16bok = eif_verify(inst16b)
        results.append(check("16b. doctor passes when the lock's resolved entrypoint is AGENTS.md, not the default .hermes.md", r16bok.returncode == 0, r16bok.stdout + r16bok.stderr))

        entry16 = inst16 / ".hermes.md"
        text16 = entry16.read_text(encoding="utf-8")
        reversed16 = text16.replace("<!-- EIF:BEGIN", "@@TMP@@").replace("<!-- EIF:END -->", "<!-- EIF:BEGIN").replace("@@TMP@@", "<!-- EIF:END -->")
        entry16.write_text(reversed16, encoding="utf-8")
        r16bad = eif_verify(inst16)
        results.append(check("16. doctor catches reversed markers in .hermes.md", r16bad.returncode != 0, r16bad.stdout + r16bad.stderr))

        # -------------------------------------------------------------
        # 17. rollback: fault injected immediately after the entrypoint
        #     stage commits -> full rollback.
        # -------------------------------------------------------------
        inst17 = tmp / "scenario-17-entrypoint-fault-rollback"
        init_git_repo(inst17)
        env17 = {"PATH": os.environ.get("PATH", ""), "EIF_INIT_TEST_FAIL_AFTER": "entrypoint"}
        proc17 = subprocess.run(
            [sys.executable, str(SCRIPTS / "eif_init.py"), "--framework-root", str(FRAMEWORK_ROOT),
             "--instance-path", str(inst17), "--allow-dirty", "--project-name", "hermes-fixture", "--adapter", "hermes",
             "--migration-status", "greenfield"],
            capture_output=True, text=True, encoding="utf-8", env=env17,
        )
        results.append(check("17. fault-after-entrypoint run exits non-zero", proc17.returncode != 0, proc17.stdout + proc17.stderr))
        results.append(check("17. no .hermes.md left behind (this run created it)", not (inst17 / ".hermes.md").exists()))
        results.append(check("17. no .eif/ left behind either", not (inst17 / ".eif").exists()))

        # -------------------------------------------------------------
        # 18/19. EN and UK generation.
        # -------------------------------------------------------------
        inst18 = tmp / "scenario-18-en-generation"
        init_git_repo(inst18)
        r18 = eif_init(inst18, "--project-name", "hermes-fixture", "--adapter", "hermes", "--locale", "en", "--migration-status", "greenfield")
        results.append(check("18. EN hermes init exits 0", r18.returncode == 0, r18.stdout + r18.stderr))
        results.append(check("18. governance content present (EN)", "Knowledge Delta" in (inst18 / ".hermes.md").read_text(encoding="utf-8")))

        inst19 = tmp / "scenario-19-uk-generation"
        init_git_repo(inst19)
        r19 = eif_init(inst19, "--project-name", "hermes-fixture", "--adapter", "hermes", "--locale", "uk", "--migration-status", "greenfield")
        results.append(check("19. UK hermes init exits 0", r19.returncode == 0, r19.stdout + r19.stderr))
        results.append(check("19. UK init-complete message present ('ініціалізовано')", "ініціалізовано" in r19.stdout, r19.stdout))

        # -------------------------------------------------------------
        # 20. privacy scan runs cleanly against a hermes instance.
        # -------------------------------------------------------------
        inst20 = tmp / "scenario-20-privacy-scan"
        init_git_repo(inst20)
        eif_init(inst20, "--project-name", "hermes-fixture", "--adapter", "hermes", "--migration-status", "greenfield")
        r20 = run([str(SCRIPTS / "eif_privacy_scan.py"), "--repo", str(inst20)])
        results.append(check("20. privacy scan runs cleanly against a hermes instance", r20.returncode == 0, r20.stdout + r20.stderr))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_hermes_adapter: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
