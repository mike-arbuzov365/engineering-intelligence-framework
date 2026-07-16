#!/usr/bin/env python3
"""Existing-repository adoption tests (adoption-hardening round).

Builds a realistic, sanitized fixture that LOOKS like a real existing
repository being adopted - not a synthetic greenfield seed like
test_journey.py's: a large pre-existing CLAUDE.md with its own governance
section, an existing .gitignore, a nonstandard knowledge path
(docs/knowledge/, not the greenfield default), protected-looking ADR/
source files, a TypeScript OS-keychain interface that pattern-matches
eif_privacy_scan.py's password_assignment rule (a real false positive
found against a private pilot target during the pilot round - see the
private planning packet), and a genuinely secret-shaped fixture value that
must NOT be suppressed by narrowly suppressing the keychain false positive.

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

# Independent-review requirement: this fixture's secret-shaped content
# must not itself trip the framework's own self-scan of this file (fixed
# previously by adding this file to SELF_EXCLUDE_FILES - the actual fix is
# instead assembling the trigger text from split literals at RUNTIME, so
# the SOURCE file never contains the contiguous pattern the scanner looks
# for, while the in-memory value (written into the separate fixture file
# below) is byte-identical to the realistic case that motivated this
# fixture. "password" immediately followed by ": string" is what the
# password_assignment pattern matches - split across the `+` here so that
# exact contiguous text never appears in this .py file's own source.
_KEYCHAIN_PW_FIELD = "password" + ": string"
KEYCHAIN_INTERFACE_TS = (
    "export interface KeytarModule {\n"
    "  getPassword(service: string, account: string): Promise<string | null>;\n"
    "  setPassword(service: string, account: string, " + _KEYCHAIN_PW_FIELD + "): Promise<void>;\n"
    "  deletePassword(service: string, account: string): Promise<boolean>;\n"
    "}\n"
)

# Deliberately secret-SHAPED (matches SECRET_PATTERNS' api_key_assignment),
# not suppressed by any suppression this test configures - proof point 7
# needs a finding that survives a narrow, correctly-scoped suppression.
# Same split-literal technique as above - "Api" + "Key" never appear
# contiguous in this source file, only in the assembled runtime value.
_LEGACY_KEY_FIELD = "legacy" + "Api" + "Key"
_LEGACY_KEY_VALUE = "sk-" + "fixture1234567890abcdef"
LEGACY_CONFIG_TS = (
    "// Legacy config module - superseded by the OS-keychain store in\n"
    "// src/auth/token-store.ts, kept only for a migration reference.\n"
    "export const " + _LEGACY_KEY_FIELD + " = \"" + _LEGACY_KEY_VALUE + "\";\n"
)

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
        # 2b. coexist mode defaults knowledge-index management OFF -
        # independent-review requirement: no create/overwrite without
        # explicit opt-in, even for a brand-new index (nothing existed
        # before at all).
        # ---------------------------------------------------------------
        inst2b = tmp / "scenario-2b-coexist-no-index-optin"
        init_git_repo(inst2b)
        build_adoption_seed(inst2b)
        commit_all(inst2b)
        r2b = eif_init(inst2b, "--project-name", "adoption-fixture", "--adoption-mode", "coexist",
                       "--knowledge-root", "docs/knowledge", "--knowledge-index-path", "docs/knowledge/index.md")
        results.append(check("2b. coexist init without --manage-knowledge-index succeeds", r2b.returncode == 0, r2b.stdout + r2b.stderr))
        results.append(check("2b. no index file created (management not opted in)", not (inst2b / "docs" / "knowledge" / "index.md").exists()))
        results.append(check("2b. preflight/output names the skip reason", "coexist" in r2b.stdout and "manage-knowledge-index" in r2b.stdout, r2b.stdout))
        cfg2b = (inst2b / ".eif" / "config.yaml").read_text(encoding="utf-8")
        results.append(check("2b. config records knowledge.managed: false", "managed: false" in cfg2b, cfg2b))

        # ---------------------------------------------------------------
        # 3. configured coexistence generates correct (configured) paths -
        # WITH explicit --manage-knowledge-index opt-in (see 2b above for
        # the default-off case).
        # ---------------------------------------------------------------
        inst3 = tmp / "scenario-3-configured-coexist"
        init_git_repo(inst3)
        build_adoption_seed(inst3)
        commit_all(inst3)
        r3 = eif_init(
            inst3, "--project-name", "adoption-fixture", "--adoption-mode", "coexist",
            "--knowledge-root", "docs/knowledge", "--knowledge-index-path", "docs/knowledge/index.md",
            "--manage-knowledge-index",
        )
        results.append(check("3. init with explicit --adoption-mode coexist succeeds", r3.returncode == 0, r3.stdout + r3.stderr))
        config_text = (inst3 / ".eif" / "config.yaml").read_text(encoding="utf-8")
        results.append(check("3. config records the configured knowledge root (not the greenfield default)", "docs/knowledge" in config_text and "root: knowledge\n" not in config_text))
        results.append(check("3. config records adoption.mode: coexist", "mode: coexist" in config_text))
        results.append(check("3. config records knowledge.managed: true (explicit opt-in)", "managed: true" in config_text))
        results.append(check("3. index generated at the CONFIGURED path", (inst3 / "docs" / "knowledge" / "index.md").exists()))
        results.append(check("3. generated index carries the EIF ownership marker", (inst3 / "docs" / "knowledge" / "index.md").read_text(encoding="utf-8").startswith("<!-- Auto-generated by scripts/eif_generate_index.py")))
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
        # 6 & 7. privacy baseline: narrow, FINDING-specific suppression
        # (independent-review redesign - rule+path+fingerprint, not
        # rule+path/glob), real secret still fails.
        # ---------------------------------------------------------------
        import json as _json

        # Discover the real fingerprint the same way a human reviewer
        # would - run the scan first, unsuppressed, and read it off the
        # finding itself. Not hardcoded/recomputed independently, so this
        # test also proves the discovery workflow actually works.
        pre_priv = run([str(SCRIPTS / "eif_privacy_scan.py"), "--repo", str(inst3), "--json"])
        pre_result = _json.loads(pre_priv.stdout)
        keytar_hits = [h for h in pre_result.get("secret_shaped", {}).get("password_assignment", []) if h["file"].replace("\\", "/") == "src/auth/keytar.d.ts"]
        results.append(check("6. baseline (unsuppressed) scan finds the keytar.d.ts finding with a fingerprint", len(keytar_hits) == 1 and "fingerprint" in keytar_hits[0], pre_priv.stdout))
        keytar_fingerprint = keytar_hits[0]["fingerprint"] if keytar_hits else "0" * 16

        (inst3 / ".eif" / "config.yaml").write_text(
            config_text.rstrip("\n") + "\n"
            "privacy:\n"
            "  suppressions:\n"
            "    - rule: \"secret_shaped:password_assignment\"\n"
            "      path: \"src/auth/keytar.d.ts\"\n"
            f"      fingerprint: \"{keytar_fingerprint}\"\n"
            "      rationale: >-\n"
            "        TypeScript interface method signature for an OS-keychain\n"
            "        module - a type declaration, not an assigned secret value.\n"
            "      reviewed: \"2026-07-15\"\n"
            "      expires: \"2026-10-15\"\n",
            encoding="utf-8",
        )
        priv = run([str(SCRIPTS / "eif_privacy_scan.py"), "--repo", str(inst3), "--json"])
        priv_result = _json.loads(priv.stdout)
        results.append(check("6. keytar.d.ts password-shaped finding is suppressed (not in active findings)",
                             "password_assignment" not in priv_result.get("secret_shaped", {})))
        results.append(check("6. suppressed finding is reported separately, not silently dropped",
                             "password_assignment" in priv_result.get("suppressed", {}).get("secret_shaped", {})))
        results.append(check("7. the unrelated real secret-shaped fixture (legacy.ts) still fails the scan",
                             "api_key_assignment" in priv_result.get("secret_shaped", {})))
        results.append(check("7. overall scan exit code is still 1 (one narrow suppression does not clear the run)",
                             priv.returncode == 1))

        # --- Regression: a SECOND, different password_assignment finding in
        # the SAME file as the suppressed one must stay active - a
        # suppression identifies one finding, not a whole rule+file.
        # Done on a COPY of inst3 (not inst3 itself) so this mutation does
        # not interfere with scenario 9's byte-for-byte rollback proof
        # below, which needs inst3 to only ever contain eif_init's own
        # writes. ---
        import shutil as _shutil_regression
        inst3_regression_copy = tmp / "scenario-6-7-regression-copy"
        _shutil_regression.copytree(inst3, inst3_regression_copy)
        (inst3_regression_copy / "src" / "auth" / "keytar.d.ts").write_text(
            (inst3_regression_copy / "src" / "auth" / "keytar.d.ts").read_text(encoding="utf-8")
            + "\n// A second, unrelated, REAL secret-shaped line in the SAME file:\n"
            + "const debugPassword" + " = \"" + "not-a-real-secret-but-shaped-like-one\";\n",
            encoding="utf-8",
        )
        priv2 = run([str(SCRIPTS / "eif_privacy_scan.py"), "--repo", str(inst3_regression_copy), "--json"])
        priv2_result = _json.loads(priv2.stdout)
        same_file_active = [h for h in priv2_result.get("secret_shaped", {}).get("password_assignment", []) if h["file"].replace("\\", "/") == "src/auth/keytar.d.ts"]
        results.append(check("regression: a second real finding in the SAME suppressed file stays active", len(same_file_active) == 1, priv2.stdout))
        results.append(check("regression: overall exit code is still 1 (one suppressed finding does not hide a new one in the same file)", priv2.returncode == 1, priv2.stdout))

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

        # ---------------------------------------------------------------
        # 11. broken EXISTING user config must STOP, never be treated as
        # a fresh init (independent-review requirement) - three distinct
        # broken states, each its own byte-for-byte-unchanged proof.
        # ---------------------------------------------------------------
        for label, bad_content in (
            ("invalid_yaml", "knowledge:\n  root: [unclosed\n"),
            ("not_a_mapping", "- just\n- a\n- list\n"),
            ("schema_invalid", "schema_version: 1\nproject: {}\n"),  # missing required project.name etc.
        ):
            inst11 = tmp / f"scenario-11-broken-config-{label}"
            init_git_repo(inst11)
            build_adoption_seed(inst11)
            (inst11 / ".eif").mkdir()
            (inst11 / ".eif" / "config.yaml").write_text(bad_content, encoding="utf-8")
            commit_all(inst11)
            before11 = snapshot(inst11)
            r11 = eif_init(inst11, "--project-name", "should-not-matter", "--adoption-mode", "coexist")
            results.append(check(f"11. {label} existing config: init exits 1 (STOP, not silent re-init)", r11.returncode == 1, r11.stdout + r11.stderr))
            results.append(check(f"11. {label} existing config: refuses to treat it as a fresh init", "fresh init" in (r11.stdout + r11.stderr) or "refusing" in (r11.stdout + r11.stderr), r11.stdout + r11.stderr))
            after11 = snapshot(inst11)
            results.append(check(f"11. {label} existing config: tree byte-for-byte unchanged (nothing written)", after11 == before11))

        # ---------------------------------------------------------------
        # 12. existing non-EIF-owned knowledge index must STOP, never be
        # silently overwritten - even with explicit --manage-knowledge-index.
        # ---------------------------------------------------------------
        inst12 = tmp / "scenario-12-index-collision"
        init_git_repo(inst12)
        build_adoption_seed(inst12)
        (inst12 / "docs" / "knowledge" / "index.md").write_text(
            "# Our own hand-written knowledge index\n\nThis is NOT generated by EIF.\n", encoding="utf-8",
        )
        commit_all(inst12)
        before12 = snapshot(inst12)
        r12 = eif_init(inst12, "--project-name", "adoption-fixture", "--adoption-mode", "coexist",
                       "--knowledge-root", "docs/knowledge", "--knowledge-index-path", "docs/knowledge/index.md",
                       "--manage-knowledge-index")
        results.append(check("12. existing non-EIF index: init exits 1 (STOP)", r12.returncode == 1, r12.stdout + r12.stderr))
        results.append(check("12. existing non-EIF index: preflight names the collision", "ownership marker" in (r12.stdout + r12.stderr), r12.stdout + r12.stderr))
        after12 = snapshot(inst12)
        results.append(check("12. existing non-EIF index: tree byte-for-byte unchanged (nothing written, not even .eif/)", after12 == before12))

        # ---------------------------------------------------------------
        # 13. preflight uses PERSISTED adoption.mode, not just this run's
        # flag - independent-review fix for the hole where only mode==
        # "init" ever STOPped. Manually-created valid config (not eif_init-
        # generated) + existing CLAUDE.md content + no markers yet.
        # ---------------------------------------------------------------
        def make_manual_config(inst: Path, adoption_mode: str) -> None:
            (inst / ".eif").mkdir(exist_ok=True)
            (inst / ".eif" / "config.yaml").write_text(
                "schema_version: 1\n"
                "project:\n  name: manual-config-project\n"
                "adapter:\n  name: claude-code\n"
                "localization:\n  documentation_locale: en\n"
                "knowledge:\n  root: knowledge\n  index_path: knowledge/index.md\n  managed: true\n"
                f"adoption:\n  mode: {adoption_mode}\n",
                encoding="utf-8",
            )

        # 13a. persisted coexist -> OK, safe append (upgrade mode, no flag needed)
        inst13a = tmp / "scenario-13a-persisted-coexist"
        init_git_repo(inst13a)
        build_adoption_seed(inst13a)
        make_manual_config(inst13a, "coexist")
        commit_all(inst13a)
        r13a = eif_init(inst13a)  # routine upgrade, no --adoption-mode flag at all
        results.append(check("13a. persisted coexist (manual config, upgrade, no flag): succeeds", r13a.returncode == 0, r13a.stdout + r13a.stderr))
        results.append(check("13a. persisted coexist: CLAUDE.md got the coexist block appended", "coexistence mode" in (inst13a / "CLAUDE.md").read_text(encoding="utf-8")))

        # 13b. persisted greenfield (or absent) + no explicit flag on upgrade
        # -> STOP, not WARN (the exact hole this item closes: the OLD
        # preflight only ever checked mode == "init").
        inst13b = tmp / "scenario-13b-persisted-greenfield-upgrade-stop"
        init_git_repo(inst13b)
        build_adoption_seed(inst13b)
        make_manual_config(inst13b, "greenfield")
        commit_all(inst13b)
        before13b = snapshot(inst13b)
        r13b = eif_init(inst13b)  # routine upgrade, no flag - must NOT silently WARN-and-proceed
        results.append(check("13b. persisted greenfield + no markers, upgrade, no flag: exits 1 (STOP, not WARN)", r13b.returncode == 1, r13b.stdout + r13b.stderr))
        after13b = snapshot(inst13b)
        results.append(check("13b. persisted greenfield STOP: tree byte-for-byte unchanged", after13b == before13b))

        # 13c. same as 13b, but WITH an explicit informed override this run -
        # a bare --adoption-mode on a ROUTINE upgrade is ignored (same
        # contract as locale/adapter/etc.), so "explicit" here means
        # --force (reconfigure), matching how every other flag on this CLI
        # actually takes effect against an existing config: WARN, proceeds.
        r13c = eif_init(inst13b, "--force", "--adoption-mode", "greenfield")
        results.append(check("13c. same case + explicit --force --adoption-mode greenfield override: succeeds (WARN, not STOP)", r13c.returncode == 0, r13c.stdout + r13c.stderr))
        results.append(check("13c. explicit override: preflight output says WARN, not just OK", "WARN" in r13c.stdout, r13c.stdout))

        # ---------------------------------------------------------------
        # 14. markers deleted by hand after a prior real install - config
        # still says coexist, entrypoint has real content but no markers
        # anymore. Preflight must use the persisted mode here too.
        # ---------------------------------------------------------------
        inst14 = tmp / "scenario-14-deleted-markers"
        init_git_repo(inst14)
        build_adoption_seed(inst14)
        commit_all(inst14)
        r14_install = eif_init(inst14, "--project-name", "adoption-fixture", "--adoption-mode", "coexist")
        results.append(check("14. initial real install succeeds", r14_install.returncode == 0, r14_install.stdout + r14_install.stderr))
        # Hand-delete the managed block, leaving the rest of CLAUDE.md intact.
        claude_text = (inst14 / "CLAUDE.md").read_text(encoding="utf-8")
        begin_i = claude_text.index("<!-- EIF:BEGIN")
        end_i = claude_text.index("<!-- EIF:END -->") + len("<!-- EIF:END -->")
        (inst14 / "CLAUDE.md").write_text(claude_text[:begin_i].rstrip("\n") + "\n" + claude_text[end_i:].lstrip("\n"), encoding="utf-8")
        r14_upgrade = eif_init(inst14)  # routine upgrade, markers now gone, config still says coexist
        results.append(check("14. upgrade after hand-deleted markers (persisted coexist): succeeds, does not STOP", r14_upgrade.returncode == 0, r14_upgrade.stdout + r14_upgrade.stderr))
        results.append(check("14. markers restored via append (coexist framing, not a duplicate/competing block)",
                             (inst14 / "CLAUDE.md").read_text(encoding="utf-8").count("Execution authority") == 1))

        # ---------------------------------------------------------------
        # 15. reconfigure changes adoption mode explicitly in both
        # directions - explicit flag always wins over whatever was
        # persisted, in either direction.
        # ---------------------------------------------------------------
        inst15 = tmp / "scenario-15-reconfigure-both-ways"
        init_git_repo(inst15)
        build_adoption_seed(inst15)
        commit_all(inst15)
        eif_init(inst15, "--project-name", "adoption-fixture", "--adoption-mode", "greenfield")
        r15a = eif_init(inst15, "--force", "--adoption-mode", "coexist")
        results.append(check("15a. reconfigure greenfield -> coexist: succeeds", r15a.returncode == 0, r15a.stdout + r15a.stderr))
        results.append(check("15a. config now says coexist", "mode: coexist" in (inst15 / ".eif" / "config.yaml").read_text(encoding="utf-8")))
        r15b = eif_init(inst15, "--force", "--adoption-mode", "greenfield")
        results.append(check("15b. reconfigure coexist -> greenfield: succeeds (WARN, informed override)", r15b.returncode == 0, r15b.stdout + r15b.stderr))
        results.append(check("15b. config now says greenfield", "mode: greenfield" in (inst15 / ".eif" / "config.yaml").read_text(encoding="utf-8")))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_adoption: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
