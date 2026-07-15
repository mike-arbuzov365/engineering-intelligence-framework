#!/usr/bin/env python3
"""Existing-repository adoption tests (adoption-hardening round).

Builds a realistic, sanitized fixture that LOOKS like a real existing
repository being adopted - not a synthetic greenfield seed like
test_journey.py's: a large pre-existing CLAUDE.md with its own governance
section, an existing .gitignore, a nonstandard knowledge path
(docs/knowledge/, not the greenfield default), protected-looking ADR/
source files, a TypeScript OS-keychain interface that pattern-matches
eif_privacy_scan.py's password_assignment rule (a real false positive
found against wm-freelance-ops during the pilot round - see the private
planning packet), and a genuinely secret-shaped fixture value that must
NOT be suppressed by narrowly suppressing the keychain false positive.

No content here is from any private/production repository - names,
structure, and prose are original to this fixture.

Ten proof points, each its own numbered section below:
 1. dry-run writes zero files
 2. unspecified coexistence conflict stops before write
 3. configured coexistence generates correct (configured, not default) paths
 4. no duplicate/competing authority declaration
 5. everything outside markers stays byte-for-byte unchanged
 6. privacy baseline suppresses only the reviewed exact finding
 7. an unsuppressed real secret-shaped fixture still fails the scan
 8. link check runs successfully
 9. install and rollback restore the exact previous state
10. runtime verification passes after install and after reinstall (upgrade)

Usage:
    python scripts/tests/test_adoption.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = FRAMEWORK_ROOT / "scripts"

EXISTING_CLAUDE_MD = """# Agent instructions

This repository has its own operating rules. Read this file fully before
making changes - do not assume defaults from any framework or template.

## Tooling contract

Every shell command in this repository must go through the project's own
token-optimized wrapper. See TOOLING.md for the full command reference.
Do not call the underlying tools directly.

## Single-agent policy

All tasks in this repository are executed by one active agent at a time.
Do not spawn subagents or delegate repository work to child agents.

## Governance

Changes to authentication, credential storage, or payment code require
owner review before merge. This repository's own rules in this file take
precedence over any generic agent guidance from elsewhere.

## Style

Use ASCII punctuation only in prose and code comments - no smart quotes,
no em-dashes.
"""

EXISTING_GITIGNORE = """node_modules/
dist/
.env
*.log
"""

ADR_CONTENT = """# ADR-0001: Credential storage uses the OS keychain

## Status
Accepted

## Decision
Long-lived credentials are stored via the OS keychain, never in
plaintext config or environment files committed to the repository.
"""

KEYCHAIN_INTERFACE_TS = """export interface KeytarModule {
  getPassword(service: string, account: string): Promise<string | null>;
  setPassword(service: string, account: string, password: string): Promise<void>;
  deletePassword(service: string, account: string): Promise<boolean>;
}
"""

# Deliberately secret-SHAPED (matches SECRET_PATTERNS' api_key_assignment),
# not suppressed by any suppression this test configures - proof point 7
# needs a finding that survives a narrow, correctly-scoped suppression.
LEGACY_CONFIG_TS = """// Legacy config module - superseded by the OS-keychain store in
// src/auth/token-store.ts, kept only for a migration reference.
export const legacyApiKey = "sk-fixture1234567890abcdef";
"""

KNOWLEDGE_NOTE = """---
type: fact
status: validated
scope: project
evidence: OBSERVED
source: official_specification
created: 2026-07-15
review_after: 2027-07-15
---

# Existing project convention

Knowledge in this repository lives under docs/knowledge/, not a root
knowledge/ directory - a pre-existing convention this fixture represents.
"""

README_MD = """# Fixture project

See [ADR-0001](docs/adr/ADR-0001-credential-storage.md) for the
credential-storage decision and
[the existing knowledge note](docs/knowledge/existing-convention.md).
"""


def build_adoption_seed(root: Path) -> None:
    """Materialize the fixture tree at `root` (must already exist and be a
    git repo) - called fresh per scenario needing a pristine copy."""
    (root / "CLAUDE.md").write_text(EXISTING_CLAUDE_MD, encoding="utf-8")
    (root / ".gitignore").write_text(EXISTING_GITIGNORE, encoding="utf-8")
    (root / "README.md").write_text(README_MD, encoding="utf-8")
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "docs" / "adr" / "ADR-0001-credential-storage.md").write_text(ADR_CONTENT, encoding="utf-8")
    (root / "docs" / "knowledge").mkdir(parents=True)
    (root / "docs" / "knowledge" / "existing-convention.md").write_text(KNOWLEDGE_NOTE, encoding="utf-8")
    (root / "src" / "auth").mkdir(parents=True)
    (root / "src" / "auth" / "keytar.d.ts").write_text(KEYCHAIN_INTERFACE_TS, encoding="utf-8")
    (root / "src" / "config").mkdir(parents=True)
    (root / "src" / "config" / "legacy.ts").write_text(LEGACY_CONFIG_TS, encoding="utf-8")


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
    git(["config", "user.name", "Adoption Test"], root)


def commit_all(root: Path) -> None:
    git(["add", "-A"], root)
    git(["-c", "commit.gpgsign=false", "commit", "-q", "-m", "seed"], root)


def eif_init(inst: Path, *extra: str) -> subprocess.CompletedProcess:
    return run([str(SCRIPTS / "eif_init.py"), "--framework-root", str(FRAMEWORK_ROOT),
                "--instance-path", str(inst), "--allow-dirty", *extra])


def snapshot(root: Path) -> dict[str, bytes]:
    """Content of every tracked-or-not file under root except .git/, keyed
    by posix-relative path - used to prove byte-for-byte preservation and
    exact rollback, not just \"looks the same\"."""
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

        # A pristine, never-touched-by-eif_init copy of the fixture, kept
        # for the whole test run as the "original" comparison baseline.
        pristine = tmp / "pristine"
        init_git_repo(pristine)
        build_adoption_seed(pristine)
        commit_all(pristine)
        pristine_snapshot = snapshot(pristine)

        # ---------------------------------------------------------------
        # 1. dry-run writes zero files
        # ---------------------------------------------------------------
        inst1 = tmp / "scenario-1-dry-run"
        init_git_repo(inst1)
        build_adoption_seed(inst1)
        commit_all(inst1)
        before1 = snapshot(inst1)
        r1 = eif_init(inst1, "--project-name", "adoption-fixture", "--adoption-mode", "coexist", "--dry-run")
        results.append(check("1. dry-run against an adoption target exits 0", r1.returncode == 0, r1.stdout + r1.stderr))
        results.append(check("1. dry-run reports 'no files were written'", "no files were written" in r1.stdout, r1.stdout))
        after1 = snapshot(inst1)
        results.append(check("1. dry-run truly wrote zero files (snapshot identical)", after1 == before1))

        # ---------------------------------------------------------------
        # 2. unspecified coexistence conflict stops before write
        # ---------------------------------------------------------------
        inst2 = tmp / "scenario-2-unspecified-stop"
        init_git_repo(inst2)
        build_adoption_seed(inst2)
        commit_all(inst2)
        before2 = snapshot(inst2)
        r2 = eif_init(inst2, "--project-name", "adoption-fixture")  # no --adoption-mode
        results.append(check("2. init with existing governance and no --adoption-mode exits 1", r2.returncode == 1, r2.stdout + r2.stderr))
        results.append(check("2. preflight reports a STOP", "STOP" in r2.stdout, r2.stdout))
        after2 = snapshot(inst2)
        results.append(check("2. refused run wrote nothing at all", after2 == before2))
        results.append(check("2. no .eif/ directory was created by the refused run", not (inst2 / ".eif").exists()))

        # ---------------------------------------------------------------
        # 3. configured coexistence generates correct (configured) paths
        # ---------------------------------------------------------------
        inst3 = tmp / "scenario-3-configured-coexist"
        init_git_repo(inst3)
        build_adoption_seed(inst3)
        commit_all(inst3)
        r3 = eif_init(
            inst3, "--project-name", "adoption-fixture", "--adoption-mode", "coexist",
            "--knowledge-root", "docs/knowledge", "--knowledge-index-path", "docs/knowledge/index.md",
        )
        results.append(check("3. init with explicit --adoption-mode coexist succeeds", r3.returncode == 0, r3.stdout + r3.stderr))
        config_text = (inst3 / ".eif" / "config.yaml").read_text(encoding="utf-8")
        results.append(check("3. config records the configured knowledge root (not the greenfield default)", "docs/knowledge" in config_text and "root: knowledge\n" not in config_text))
        results.append(check("3. config records adoption.mode: coexist", "mode: coexist" in config_text))
        results.append(check("3. index generated at the CONFIGURED path", (inst3 / "docs" / "knowledge" / "index.md").exists()))
        results.append(check("3. no root knowledge/ directory silently created", not (inst3 / "knowledge").exists()))

        # ---------------------------------------------------------------
        # 4. no duplicate/competing authority declaration
        # ---------------------------------------------------------------
        claude_after3 = (inst3 / "CLAUDE.md").read_text(encoding="utf-8")
        claude_after3_flat = " ".join(claude_after3.split())  # whitespace-normalized, robust to line-wrapping
        results.append(check("4. generated block uses the coexistence authority section", "coexistence mode" in claude_after3))
        results.append(check("4. coexistence block does not claim sole/primary authority", "NOT this project's sole or primary authority" in claude_after3_flat))
        results.append(check("4. pre-existing '## Governance' section is still present, unaltered", "owner review before merge" in claude_after3))
        results.append(check("4. only ONE '## Execution authority' heading exists (no duplicate authority block)", claude_after3.count("Execution authority") == 1))

        # ---------------------------------------------------------------
        # 5. everything outside markers stays byte-for-byte unchanged
        # ---------------------------------------------------------------
        # render_merged_content's append-block path does existing_text.rstrip("\n")
        # + "\n\n" before the new block - it normalizes the exact trailing-
        # newline count AT the seam (so exactly one blank line separates old
        # content from the new block regardless of the original's own
        # trailing whitespace) without touching any real existing line. The
        # real guarantee (matching what the pilot verified via `git diff`
        # showing 0 deletions) is "every original line is preserved,
        # unmodified, in order" - not raw-string prefix equality including
        # that specific seam normalization.
        original_lines = EXISTING_CLAUDE_MD.splitlines()
        result_lines = claude_after3.splitlines()
        results.append(check(
            "5. every line of the original CLAUDE.md is preserved unmodified, in order",
            result_lines[:len(original_lines)] == original_lines,
        ))
        gi_after3 = (inst3 / ".gitignore").read_text(encoding="utf-8")
        results.append(check("5. .gitignore content above its managed block is byte-for-byte identical", gi_after3.startswith(EXISTING_GITIGNORE)))
        for rel in ("docs/adr/ADR-0001-credential-storage.md", "src/auth/keytar.d.ts", "src/config/legacy.ts", "README.md"):
            results.append(check(f"5. untouched file preserved exactly: {rel}", (inst3 / rel).read_bytes() == pristine_snapshot[rel]))

        # ---------------------------------------------------------------
        # 6 & 7. privacy baseline: narrow suppression, real secret still fails
        # ---------------------------------------------------------------
        (inst3 / ".eif" / "config.yaml").write_text(
            config_text.rstrip("\n") + "\n"
            "privacy:\n"
            "  suppressions:\n"
            "    - rule: \"secret_shaped:password_assignment\"\n"
            "      path: \"src/auth/keytar.d.ts\"\n"
            "      rationale: >-\n"
            "        TypeScript interface method signature for an OS-keychain\n"
            "        module - a type declaration, not an assigned secret value.\n"
            "      reviewed: \"2026-07-15\"\n",
            encoding="utf-8",
        )
        priv = run([str(SCRIPTS / "eif_privacy_scan.py"), "--repo", str(inst3), "--json"])
        import json as _json
        priv_result = _json.loads(priv.stdout)
        results.append(check("6. keytar.d.ts password-shaped finding is suppressed (not in active findings)",
                             "password_assignment" not in priv_result.get("secret_shaped", {})))
        results.append(check("6. suppressed finding is reported separately, not silently dropped",
                             "password_assignment" in priv_result.get("suppressed", {}).get("secret_shaped", {})))
        results.append(check("7. the unrelated real secret-shaped fixture (legacy.ts) still fails the scan",
                             "api_key_assignment" in priv_result.get("secret_shaped", {})))
        results.append(check("7. overall scan exit code is still 1 (one narrow suppression does not clear the run)",
                             priv.returncode == 1))

        # ---------------------------------------------------------------
        # 8. link check runs successfully
        # ---------------------------------------------------------------
        links = run([str(SCRIPTS / "eif_check_links.py"), "--repo", str(inst3)])
        results.append(check("8. link check runs and finds no broken relative links in the fixture", links.returncode == 0, links.stdout + links.stderr))

        # ---------------------------------------------------------------
        # 9. install and rollback restore the exact previous state
        # ---------------------------------------------------------------
        import shutil as _shutil
        _shutil.rmtree(inst3 / ".eif")
        git(["checkout", "--", "CLAUDE.md", ".gitignore"], inst3)
        # Real gap this test surfaced: the documented rollback (delete .eif/,
        # restore CLAUDE.md/.gitignore) does not by itself account for a
        # generated knowledge index file living OUTSIDE .eif/ - it must be
        # removed too, or rollback silently leaves a generated artifact
        # behind. Worth a docs/instance-contract.md correction (Stage 2F),
        # not just a test-side fix.
        (inst3 / "docs" / "knowledge" / "index.md").unlink(missing_ok=True)
        after_rollback = snapshot(inst3)
        # The suppression edit to config.yaml lived under .eif/, already
        # removed - compare directly against the pristine, never-installed
        # fixture snapshot for a true "back to before eif_init ever ran" proof.
        results.append(check("9. rollback restores every file to the pristine, pre-install snapshot exactly",
                             after_rollback == pristine_snapshot))

        # ---------------------------------------------------------------
        # 10. runtime verification passes after install and after reinstall
        # ---------------------------------------------------------------
        r3b = eif_init(inst3, "--project-name", "adoption-fixture", "--adoption-mode", "coexist",
                       "--knowledge-root", "docs/knowledge", "--knowledge-index-path", "docs/knowledge/index.md")
        results.append(check("10. reinstall after rollback succeeds", r3b.returncode == 0, r3b.stdout + r3b.stderr))
        verify1 = run([str(SCRIPTS / "eif_verify_runtime.py"), "--framework-root", str(inst3 / ".eif" / "runtime"), "--instance-path", str(inst3)])
        results.append(check("10. runtime verification passes after install", "all checks passed" in verify1.stdout, verify1.stdout))

        # Upgrade (routine re-run, no --force) - config-derived, should stay coexist/docs-knowledge.
        r3c = eif_init(inst3)
        results.append(check("10. routine upgrade after install succeeds", r3c.returncode == 0, r3c.stdout + r3c.stderr))
        verify2 = run([str(SCRIPTS / "eif_verify_runtime.py"), "--framework-root", str(inst3 / ".eif" / "runtime"), "--instance-path", str(inst3)])
        results.append(check("10. runtime verification passes after upgrade/reinstall", "all checks passed" in verify2.stdout, verify2.stdout))
        config_after_upgrade = (inst3 / ".eif" / "config.yaml").read_text(encoding="utf-8")
        results.append(check("10. adoption.mode survives a routine upgrade (still coexist, not reset)", "mode: coexist" in config_after_upgrade))

    passed = sum(results)
    print(f"\ntest_adoption: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
