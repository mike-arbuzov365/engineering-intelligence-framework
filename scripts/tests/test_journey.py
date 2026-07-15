#!/usr/bin/env python3
"""Full, isolated, subprocess-based journey test.

Runs the actual CLI scripts as subprocesses against fresh seed projects in
temp directories - not just calling internal functions - so this proves the
lifecycle mechanics an instance owner would actually experience.

Part 1 (steps 1-17): the original happy-path journey - real init CLI,
config/lock validation, runtime materialization, adapter entrypoint
generation, knowledge index generation, English + Ukrainian retrieval,
task-scope, failing-before/passing-after test, config-driven Ukrainian
Knowledge Delta + closeout to files, artifact validation, privacy/link
checks from the instance's own bundle, non-destructive re-init, a second
independent instance.

Part 2 (steps 18+, round-3 review): routine upgrade actually driven by the
existing config (not CLI defaults), explicit reconfiguration, adopted
migration_status surviving an upgrade, schema-aware retrieval via the
generated command, invalid-config render failure, strict-vs-draft closeout,
eif_verify_runtime.py integrity checks (clean, corrupt runtime, corrupt
lock), marker-conflict refusal, and injected failures at each managed-state
commit stage with full rollback proof - not merely a preflight failure.

Usage:
    python scripts/tests/test_journey.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = FRAMEWORK_ROOT / "scripts"

STUB_IMPL = '''\
def is_leap_year(year: int) -> bool:
    raise NotImplementedError("is_leap_year is not implemented yet")
'''

TEST_FILE = '''\
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from calendar_utils import is_leap_year  # noqa: E402


class TestIsLeapYear(unittest.TestCase):
    def test_ordinary_non_leap_year(self):
        self.assertFalse(is_leap_year(2023))

    def test_ordinary_leap_year(self):
        self.assertTrue(is_leap_year(2024))

    def test_century_year_not_divisible_by_400_is_not_leap(self):
        self.assertFalse(is_leap_year(1900))

    def test_century_year_divisible_by_400_is_leap(self):
        self.assertTrue(is_leap_year(2000))


if __name__ == "__main__":
    unittest.main()
'''

FACT_ARTIFACT = """---
type: fact
status: validated
scope: project
evidence: OBSERVED
source: official_specification
created: 2026-07-15
review_after: 2027-07-15
---

# Gregorian leap-year rule

Divisible by 4, except century years, unless also divisible by 400.
"""

PATTERN_ARTIFACT = """---
type: failure_pattern
status: validated
scope: project
evidence: OBSERVED
source: official_specification
created: 2026-07-15
review_after: 2027-07-15
---

# Naive leap-year check fails on century years

A naive `year % 4 == 0` check is wrong for century years not divisible by 400.
"""

ALL_CLOSEOUT_SET = [
    "--set", "task_name=t", "--set", "branch_or_pr=b",
    "--set", "verification_result=v", "--set", "artifacts=a",
    "--set", "promoted=p", "--set", "not_done=n", "--set", "open_questions=o",
]


def run(args: list[str], cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True, text=True, encoding="utf-8",
        env=full_env,
    )


def check(name: str, condition: bool, detail: str = "") -> bool:
    condition = bool(condition)
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")


def init(inst: Path, *extra: str) -> subprocess.CompletedProcess:
    return run([str(SCRIPTS / "eif_init.py"), "--framework-root", str(FRAMEWORK_ROOT),
                "--instance-path", str(inst), "--allow-dirty", *extra])


def main() -> int:
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "seed-project"
        inst.mkdir()
        git(["init", "-q"], inst)
        git(["config", "user.email", "test@example.invalid"], inst)
        git(["config", "user.name", "Journey Test"], inst)

        # --- 1. Real init CLI ---
        r = init(inst, "--project-name", "journey-seed", "--locale", "uk")
        results.append(check("1. real eif_init.py subprocess succeeds", r.returncode == 0, r.stdout + r.stderr))

        # --- 2. Config/lock validation ---
        cfg_check = run([str(SCRIPTS / "eif_validate_frontmatter.py"), "--framework-root", str(FRAMEWORK_ROOT),
                          "--config", str(inst / ".eif" / "config.yaml")])
        lock_check = run([str(SCRIPTS / "eif_validate_frontmatter.py"), "--framework-root", str(FRAMEWORK_ROOT),
                           "--lock", str(inst / ".eif" / "framework.lock.yaml")])
        results.append(check("2. config validates standalone", cfg_check.returncode == 0, cfg_check.stdout + cfg_check.stderr))
        results.append(check("2. lock validates standalone", lock_check.returncode == 0, lock_check.stdout + lock_check.stderr))

        # --- 3. Runtime materialization ---
        bundle = inst / ".eif" / "runtime"
        results.append(check("3. runtime bundle materialized", bundle.is_dir() and (bundle / "eif_search_knowledge.py").exists()))

        # --- 4. Adapter entrypoint generation ---
        claude_md = inst / "CLAUDE.md"
        results.append(check("4. CLAUDE.md generated (Claude Code's real entrypoint)", claude_md.exists() and "<!-- EIF:BEGIN" in claude_md.read_text(encoding="utf-8")))

        # --- 5. Knowledge index generation ---
        knowledge = inst / "knowledge"
        (knowledge / "facts").mkdir(parents=True)
        (knowledge / "facts" / "FACT-0001.md").write_text(FACT_ARTIFACT, encoding="utf-8")
        (knowledge / "failure-patterns").mkdir()
        (knowledge / "failure-patterns" / "PATTERN-0001.md").write_text(PATTERN_ARTIFACT, encoding="utf-8")
        idx = run([str(bundle / "eif_generate_index.py"), "--knowledge-root", str(knowledge), "--framework-root", str(bundle)])
        results.append(check("5. knowledge index generated via the bundle", idx.returncode == 0 and (knowledge / "index.md").exists(), idx.stdout + idx.stderr))

        # --- 6. English and Ukrainian retrieval ---
        en_search = run([str(bundle / "eif_search_knowledge.py"), "--knowledge-root", "knowledge",
                          "--framework-root", str(bundle), "leap year"], cwd=inst)
        results.append(check("6. English retrieval finds the seeded lesson", "PATTERN-0001" in en_search.stdout, en_search.stdout + en_search.stderr))

        (knowledge / "facts" / "FACT-uk.md").write_text(
            "---\ntype: fact\nstatus: validated\nscope: project\nevidence: OBSERVED\n"
            "source: official_specification\ncreated: 2026-07-15\n---\n\n"
            "# Високосний рік\n\nРік високосний, якщо ділиться на 4.\n",
            encoding="utf-8",
        )
        uk_search = run([str(bundle / "eif_search_knowledge.py"), "--knowledge-root", "knowledge",
                          "--framework-root", str(bundle), "високосний"], cwd=inst)
        results.append(check("6. Ukrainian (Cyrillic) retrieval works from the instance's own bundle", "FACT-uk" in uk_search.stdout, uk_search.stdout + uk_search.stderr))

        # --- 7. Task scope ---
        task_scope = inst / "task-scope.md"
        shutil.copyfile(bundle / "templates" / "task-scope.md", task_scope)
        results.append(check("7. task-scope.md created from the bundle template", task_scope.exists()))

        # --- 8-9-10. Failing test -> deterministic solution -> passing test ---
        src_dir, tests_dir = inst / "src", inst / "tests"
        src_dir.mkdir()
        tests_dir.mkdir()
        (src_dir / "calendar_utils.py").write_text(STUB_IMPL, encoding="utf-8")
        (tests_dir / "test_calendar_utils.py").write_text(TEST_FILE, encoding="utf-8")

        before = run([str(tests_dir / "test_calendar_utils.py")])
        results.append(check("8. failing-before: behavioral test fails on the stub", before.returncode != 0, before.stderr))

        (src_dir / "calendar_utils.py").write_text(
            "def is_leap_year(year: int) -> bool:\n"
            "    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)\n",
            encoding="utf-8",
        )
        after = run([str(tests_dir / "test_calendar_utils.py")])
        results.append(check("9-10. passing-after: deterministic solution makes the test pass", after.returncode == 0, after.stdout + after.stderr))

        # --- 11-12. Config-driven Ukrainian Knowledge Delta + closeout, TO FILES ---
        kd = run([str(bundle / "eif_render.py"), "--framework-root", str(bundle), "knowledge-delta"], cwd=inst)
        co = run([str(bundle / "eif_render.py"), "--framework-root", str(bundle), "session-closeout", *ALL_CLOSEOUT_SET], cwd=inst)
        kd_file, co_file = inst / "knowledge-delta.md", inst / "session-closeout.md"
        results.append(check("11. config-driven render created knowledge-delta.md (locale from config, no --locale flag)",
                             kd.returncode == 0 and kd_file.exists() and "Дельта знань" in kd_file.read_text(encoding="utf-8"),
                             kd.stdout + kd.stderr))
        results.append(check("12. config-driven render created a FULLY-FILLED session-closeout.md",
                             co.returncode == 0 and co_file.exists() and "Сесію завершено" in co_file.read_text(encoding="utf-8")
                             and "{" not in co_file.read_text(encoding="utf-8"),
                             co.stdout + co.stderr))

        # --- 13. Artifact validation ---
        art_check = run([str(bundle / "eif_validate_frontmatter.py"), "--framework-root", str(bundle),
                          "--instance-root", str(inst), "knowledge/**/*.md"])
        results.append(check("13. seeded knowledge artifacts validate via the bundle", art_check.returncode == 0, art_check.stdout + art_check.stderr))

        # --- 14. Privacy and link checks, available to the instance from its own bundle ---
        git(["add", "-A"], inst)
        priv = run([str(bundle / "eif_privacy_scan.py"), "--repo", ".", "--json"], cwd=inst)
        links = run([str(bundle / "eif_check_links.py"), "--repo", "."], cwd=inst)
        results.append(check("14. privacy scan runs from the instance's own bundle, 0 findings", priv.returncode == 0, priv.stdout + priv.stderr))
        results.append(check("14. link check runs from the instance's own bundle", links.returncode == 0, links.stdout + links.stderr))

        # --- 15. Non-destructive re-init (round-1 baseline: re-init succeeds and preserves user config content) ---
        cfg_before = (inst / ".eif" / "config.yaml").read_text(encoding="utf-8")
        upgrade = init(inst)
        results.append(check("15. re-init (upgrade) succeeds", upgrade.returncode == 0, upgrade.stdout + upgrade.stderr))
        results.append(check("15. upgrade leaves user config byte-for-byte unchanged",
                             (inst / ".eif" / "config.yaml").read_text(encoding="utf-8") == cfg_before))
        results.append(check("15. upgrade creates no config backup (only --force would)",
                             list((inst / ".eif").glob("config.yaml.bak-*")) == []))
        results.append(check("15. knowledge seeded before the upgrade survives it",
                             (inst / "knowledge" / "facts" / "FACT-0001.md").exists()))

        # --- 18. Round-3: routine upgrade is actually DRIVEN by the existing
        # config, not just "doesn't overwrite" - the locale used for the
        # run's own status messages must come from config.yaml (uk), not a
        # CLI default (en), even though --locale was not passed this time. ---
        results.append(check("18. upgrade with no --locale flag still prints the real Ukrainian init-start message (locale read from config, not CLI-defaulted to 'en')",
                             "Ініціалізація EIF project instance" in upgrade.stdout, upgrade.stdout))
        results.append(check("18. upgrade with no --locale flag still prints the real Ukrainian init-complete message",
                             "ініціалізовано" in upgrade.stdout.lower(), upgrade.stdout))

        # --- 19. Explicit reconfiguration: --force changes ONLY what's passed ---
        reconfig = init(inst, "--force", "--locale", "en")
        results.append(check("19. explicit reconfigure (--force --locale en) succeeds", reconfig.returncode == 0, reconfig.stdout + reconfig.stderr))
        new_cfg = (inst / ".eif" / "config.yaml").read_text(encoding="utf-8")
        results.append(check("19. reconfigure changed the locale", "documentation_locale: en" in new_cfg, new_cfg))
        results.append(check("19. reconfigure backed up the prior config", list((inst / ".eif").glob("config.yaml.bak-*")) != []))

        # --- 20. adopted migration_status must survive routine upgrades (the
        # exact bug independently reproduced during this review: a bare
        # re-run without --migration-status silently reset adopted -> greenfield) ---
        reconfig_adopt = init(inst, "--force", "--migration-status", "adopted")
        results.append(check("20. reconfigure sets migration_status: adopted", reconfig_adopt.returncode == 0))
        lock_text_1 = (inst / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8")
        results.append(check("20. lock shows migration_status: adopted right after setting it", "migration_status: adopted" in lock_text_1))

        routine_upgrade_after_adopt = init(inst)  # no flags at all
        results.append(check("20. a routine upgrade with NO flags at all succeeds", routine_upgrade_after_adopt.returncode == 0, routine_upgrade_after_adopt.stdout + routine_upgrade_after_adopt.stderr))
        lock_text_2 = (inst / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8")
        results.append(check("20. migration_status: adopted SURVIVES a routine upgrade with no flags (Finding A - was silently reset to greenfield before this fix)",
                             "migration_status: adopted" in lock_text_2, lock_text_2))

        # --- 21. Schema-aware retrieval via the ACTUAL generated command
        # (Finding C - the template used to omit --framework-root) ---
        claude_text = claude_md.read_text(encoding="utf-8")
        results.append(check("21. generated CLAUDE.md's search command includes --framework-root",
                             "eif_search_knowledge.py" in claude_text and "--framework-root" in claude_text.split("eif_search_knowledge.py")[1].split("\n")[0],
                             claude_text))

        # --- 22. Truthful rendering: invalid config fails, not silent English ---
        cfg_backup = (inst / ".eif" / "config.yaml").read_text(encoding="utf-8")
        (inst / ".eif" / "config.yaml").write_text("not: [valid yaml\n", encoding="utf-8")
        broken_render = run([str(bundle / "eif_render.py"), "--framework-root", str(bundle), "--stdout", "knowledge-delta"], cwd=inst)
        results.append(check("22. rendering with a broken .eif/config.yaml FAILS (not a silent English fallback)",
                             broken_render.returncode != 0, broken_render.stdout + broken_render.stderr))
        (inst / ".eif" / "config.yaml").write_text(cfg_backup, encoding="utf-8")

        # --- 23. Strict-vs-draft closeout (Finding H) ---
        strict_incomplete = run([str(bundle / "eif_render.py"), "--framework-root", str(bundle), "--stdout",
                                  "session-closeout", "--set", "task_name=only-this-one"], cwd=inst)
        results.append(check("23. a 'final' closeout render with unresolved placeholders FAILS by default",
                             strict_incomplete.returncode != 0, strict_incomplete.stdout + strict_incomplete.stderr))
        draft_incomplete = run([str(bundle / "eif_render.py"), "--framework-root", str(bundle), "--stdout", "--draft",
                                 "session-closeout", "--set", "task_name=only-this-one"], cwd=inst)
        results.append(check("23. --draft explicitly allows the same partial render to succeed",
                             draft_incomplete.returncode == 0 and "only-this-one" in draft_incomplete.stdout, draft_incomplete.stdout + draft_incomplete.stderr))

        # --- 24. Runtime integrity verification, clean state ---
        verify_clean = run([str(bundle / "eif_verify_runtime.py"), "--framework-root", str(bundle), "--instance-path", str(inst)])
        results.append(check("24. eif_verify_runtime.py passes on a clean, untouched instance", verify_clean.returncode == 0, verify_clean.stdout + verify_clean.stderr))

        # --- 25. Corrupt runtime detection ---
        target = bundle / "eif_locale.py"
        original_content = target.read_text(encoding="utf-8")
        target.write_text(original_content + "\n# corrupted for test\n", encoding="utf-8")
        verify_corrupt_runtime = run([str(bundle / "eif_verify_runtime.py"), "--framework-root", str(bundle), "--instance-path", str(inst)])
        results.append(check("25. eif_verify_runtime.py detects a hand-edited bundle file",
                             verify_corrupt_runtime.returncode != 0 and "eif_locale.py" in verify_corrupt_runtime.stdout, verify_corrupt_runtime.stdout))
        target.write_text(original_content, encoding="utf-8")  # restore

        # --- 26. Corrupt lock detection ---
        lock_path = inst / ".eif" / "framework.lock.yaml"
        lock_backup = lock_path.read_text(encoding="utf-8")
        lock_path.write_text(lock_backup.replace("lock_schema_version: 1", "lock_schema_version: \"not-an-integer\""), encoding="utf-8")
        verify_corrupt_lock = run([str(bundle / "eif_verify_runtime.py"), "--framework-root", str(bundle), "--instance-path", str(inst)])
        results.append(check("26. eif_verify_runtime.py detects a schema-invalid lock file", verify_corrupt_lock.returncode != 0, verify_corrupt_lock.stdout))
        lock_path.write_text(lock_backup, encoding="utf-8")  # restore

        # --- 27. Malformed managed markers refused, not silently corrupted ---
        claude_backup = claude_md.read_text(encoding="utf-8")
        claude_md.write_text("<!-- EIF:END -->\n\nstray content\n\n<!-- EIF:BEGIN duplicate -->\n", encoding="utf-8")
        malformed_marker_run = init(inst)
        results.append(check("27. init refuses to write when CLAUDE.md has malformed (reversed) markers",
                             malformed_marker_run.returncode != 0, malformed_marker_run.stdout + malformed_marker_run.stderr))
        results.append(check("27. the malformed file itself is left untouched (not partially merged/corrupted)",
                             claude_md.read_text(encoding="utf-8") == "<!-- EIF:END -->\n\nstray content\n\n<!-- EIF:BEGIN duplicate -->\n"))
        claude_md.write_text(claude_backup, encoding="utf-8")  # restore

        # --- 17. A second, independent instance in its own directory under the same framework ---
        inst2 = Path(tmp) / "seed-project-2"
        inst2.mkdir()
        r2 = init(inst2, "--project-name", "journey-seed-2", "--locale", "en")
        results.append(check("17. a second, independent instance initializes cleanly from the same framework",
                             r2.returncode == 0 and (inst2 / ".eif" / "runtime").is_dir(), r2.stdout + r2.stderr))

    # --- 16 / 28. Injected failures at EACH managed-state commit stage, with
    # full rollback proof - a deliberately broken, non-git framework COPY so
    # the real repo is never touched, and --framework-ref so init doesn't
    # need that copy to be a git checkout. ---
    for fail_stage in ["runtime", "lock", "entrypoint", "gitignore"]:
        with tempfile.TemporaryDirectory() as tmp2:
            fake_fw = Path(tmp2) / "framework-copy"
            fake_fw.mkdir()
            shutil.copytree(SCRIPTS, fake_fw / "scripts")
            shutil.copytree(FRAMEWORK_ROOT / "core", fake_fw / "core")
            shutil.copytree(FRAMEWORK_ROOT / "locales", fake_fw / "locales")
            shutil.copytree(FRAMEWORK_ROOT / "templates", fake_fw / "templates")

            inst3 = Path(tmp2) / "instance-3"
            inst3.mkdir()
            fake_ref = "a" * 40

            first = run([str(fake_fw / "scripts" / "eif_init.py"), "--framework-root", str(fake_fw),
                         "--instance-path", str(inst3), "--project-name", "rollback-test",
                         "--locale", "en", "--framework-ref", fake_ref])
            results.append(check(f"16/28. [{fail_stage}] baseline init against the framework copy succeeds",
                                 first.returncode == 0, first.stdout + first.stderr))

            original_lock = (inst3 / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8")
            original_claude = (inst3 / "CLAUDE.md").read_text(encoding="utf-8")
            original_gitignore = (inst3 / ".gitignore").read_text(encoding="utf-8")
            verify_before = run([str(inst3 / ".eif" / "runtime" / "eif_verify_runtime.py"),
                                  "--framework-root", str(inst3 / ".eif" / "runtime"), "--instance-path", str(inst3)])
            results.append(check(f"16/28. [{fail_stage}] baseline instance passes eif_verify_runtime before the injected failure",
                                 verify_before.returncode == 0, verify_before.stdout))

            # Not "call collect_bundle_sources and let it fail" (a preflight
            # failure) - actually commit up to and including `fail_stage`,
            # THEN fail. FAULT_INJECT_ENV fires *after* that stage commits.
            second = run(
                [str(fake_fw / "scripts" / "eif_init.py"), "--framework-root", str(fake_fw),
                 "--instance-path", str(inst3), "--allow-dirty", "--framework-ref", fake_ref],
                env={"EIF_INIT_TEST_FAIL_AFTER": fail_stage},
            )
            results.append(check(f"16/28. [{fail_stage}] injected failure after that stage commits makes the run fail",
                                 second.returncode != 0, second.stdout + second.stderr))

            # Full rollback: every managed artifact is back to its pre-upgrade
            # state, no orphaned .next/.previous files, and the instance is
            # still genuinely functional (not just "files present").
            no_orphans = not any(inst3.rglob("*.next")) and not any(inst3.rglob("*.previous"))
            results.append(check(f"16/28. [{fail_stage}] no orphaned .next/.previous files anywhere in the instance", no_orphans))
            results.append(check(f"16/28. [{fail_stage}] lock restored to its exact pre-failure content",
                                 (inst3 / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8") == original_lock))
            results.append(check(f"16/28. [{fail_stage}] CLAUDE.md restored to its exact pre-failure content",
                                 (inst3 / "CLAUDE.md").read_text(encoding="utf-8") == original_claude))
            results.append(check(f"16/28. [{fail_stage}] .gitignore restored to its exact pre-failure content",
                                 (inst3 / ".gitignore").read_text(encoding="utf-8") == original_gitignore))

            verify_after = run([str(inst3 / ".eif" / "runtime" / "eif_verify_runtime.py"),
                                 "--framework-root", str(inst3 / ".eif" / "runtime"), "--instance-path", str(inst3)])
            results.append(check(f"16/28. [{fail_stage}] instance passes full eif_verify_runtime AFTER the rollback (not just 'didn't crash')",
                                 verify_after.returncode == 0, verify_after.stdout))

            still_works = run([str(inst3 / ".eif" / "runtime" / "eif_search_knowledge.py"), "--help"])
            results.append(check(f"16/28. [{fail_stage}] the instance's bundle is still functional after the rollback",
                                 still_works.returncode == 0, still_works.stdout + still_works.stderr))

    # --- 29. Injected failure AFTER the knowledge_index stage - separate
    # from the loop above because the index stage only exists in the
    # transaction when there is something to index (independent-review
    # addition: the index used to be written outside the transaction
    # entirely, so this stage - and this test - did not exist before). ---
    with tempfile.TemporaryDirectory() as tmp3:
        fake_fw = Path(tmp3) / "framework-copy"
        fake_fw.mkdir()
        shutil.copytree(SCRIPTS, fake_fw / "scripts")
        shutil.copytree(FRAMEWORK_ROOT / "core", fake_fw / "core")
        shutil.copytree(FRAMEWORK_ROOT / "locales", fake_fw / "locales")
        shutil.copytree(FRAMEWORK_ROOT / "templates", fake_fw / "templates")

        inst4 = Path(tmp3) / "instance-4"
        inst4.mkdir()
        fake_ref = "b" * 40

        first = run([str(fake_fw / "scripts" / "eif_init.py"), "--framework-root", str(fake_fw),
                     "--instance-path", str(inst4), "--project-name", "rollback-index-test",
                     "--locale", "en", "--framework-ref", fake_ref])
        results.append(check("29. [knowledge_index] baseline init against the framework copy succeeds",
                             first.returncode == 0, first.stdout + first.stderr))

        # Seed real knowledge content AFTER the baseline init, so the
        # SECOND run (the one that gets the injected failure) has
        # something to index - action must be "create" for the stage to
        # exist in the transaction at all.
        (inst4 / "knowledge" / "facts").mkdir(parents=True)
        (inst4 / "knowledge" / "facts" / "FACT-0001.md").write_text(FACT_ARTIFACT, encoding="utf-8")

        verify_before = run([str(inst4 / ".eif" / "runtime" / "eif_verify_runtime.py"),
                              "--framework-root", str(inst4 / ".eif" / "runtime"), "--instance-path", str(inst4)])
        results.append(check("29. [knowledge_index] baseline instance passes eif_verify_runtime before the injected failure",
                             verify_before.returncode == 0, verify_before.stdout))
        results.append(check("29. [knowledge_index] no index file exists yet (seeded knowledge, but no run has indexed it)",
                             not (inst4 / "knowledge" / "index.md").exists()))

        original_lock = (inst4 / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8")
        original_claude = (inst4 / "CLAUDE.md").read_text(encoding="utf-8")
        original_gitignore = (inst4 / ".gitignore").read_text(encoding="utf-8")

        second = run(
            [str(fake_fw / "scripts" / "eif_init.py"), "--framework-root", str(fake_fw),
             "--instance-path", str(inst4), "--allow-dirty", "--framework-ref", fake_ref],
            env={"EIF_INIT_TEST_FAIL_AFTER": "knowledge_index"},
        )
        results.append(check("29. [knowledge_index] injected failure after that stage commits makes the run fail",
                             second.returncode != 0, second.stdout + second.stderr))

        no_orphans = not any(inst4.rglob("*.next")) and not any(inst4.rglob("*.previous"))
        results.append(check("29. [knowledge_index] no orphaned .next/.previous files anywhere in the instance", no_orphans))
        results.append(check("29. [knowledge_index] no NEW empty directories left behind (knowledge/ contains only the seeded fact)",
                             sorted(p.name for p in (inst4 / "knowledge").iterdir()) == ["facts"]))
        results.append(check("29. [knowledge_index] index.md itself does not exist after rollback (its own stage rolled back too)",
                             not (inst4 / "knowledge" / "index.md").exists()))
        results.append(check("29. [knowledge_index] lock restored to its exact pre-failure content",
                             (inst4 / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8") == original_lock))
        results.append(check("29. [knowledge_index] CLAUDE.md restored to its exact pre-failure content",
                             (inst4 / "CLAUDE.md").read_text(encoding="utf-8") == original_claude))
        results.append(check("29. [knowledge_index] .gitignore restored to its exact pre-failure content",
                             (inst4 / ".gitignore").read_text(encoding="utf-8") == original_gitignore))

        verify_after = run([str(inst4 / ".eif" / "runtime" / "eif_verify_runtime.py"),
                             "--framework-root", str(inst4 / ".eif" / "runtime"), "--instance-path", str(inst4)])
        results.append(check("29. [knowledge_index] instance passes full eif_verify_runtime AFTER the rollback",
                             verify_after.returncode == 0, verify_after.stdout))

        # Prove the stage really was reached and staged (not silently
        # skipped, which would make the "injected failure" assertion above
        # a false positive for the wrong reason) by re-running for real
        # (no fault injection) and confirming the index NOW appears.
        third = run([str(fake_fw / "scripts" / "eif_init.py"), "--framework-root", str(fake_fw),
                     "--instance-path", str(inst4), "--allow-dirty", "--framework-ref", fake_ref])
        results.append(check("29. [knowledge_index] a real re-run (no fault injection) succeeds", third.returncode == 0, third.stdout + third.stderr))
        results.append(check("29. [knowledge_index] and NOW the index exists with the seeded fact indexed",
                             (inst4 / "knowledge" / "index.md").exists() and "FACT-0001" in (inst4 / "knowledge" / "index.md").read_text(encoding="utf-8")))

    # --- 30. Injected failure on a genuinely FIRST-EVER init (no prior
    # successful run) - independent-review pilot finding against a real
    # adopted repository: eif_init.py's own `.eif` directory is mkdir'd
    # eagerly, outside every _Stage's rollback bookkeeping (each _Stage only
    # knows how to restore its own live_path, never the directory
    # containing it). Every OTHER fault-injection test above (16-28, 29)
    # injects its failure into a SECOND run against an instance a first,
    # successful run already initialized, so .eif/ always already existed
    # going in - none of them could have caught a rollback leaving a new,
    # empty .eif/ behind. This test's instance directory is never
    # initialized before the faulted call. ---
    with tempfile.TemporaryDirectory() as tmp4:
        fake_fw2 = Path(tmp4) / "framework-copy"
        fake_fw2.mkdir()
        shutil.copytree(SCRIPTS, fake_fw2 / "scripts")
        shutil.copytree(FRAMEWORK_ROOT / "core", fake_fw2 / "core")
        shutil.copytree(FRAMEWORK_ROOT / "locales", fake_fw2 / "locales")
        shutil.copytree(FRAMEWORK_ROOT / "templates", fake_fw2 / "templates")

        inst5 = Path(tmp4) / "instance-5"
        inst5.mkdir()
        fake_ref2 = "c" * 40
        results.append(check("30. [fresh-init] .eif does not exist before the first-ever run", not (inst5 / ".eif").exists()))

        first_ever = run(
            [str(fake_fw2 / "scripts" / "eif_init.py"), "--framework-root", str(fake_fw2),
             "--instance-path", str(inst5), "--project-name", "fresh-init-rollback-test",
             "--locale", "en", "--framework-ref", fake_ref2],
            env={"EIF_INIT_TEST_FAIL_AFTER": "runtime"},
        )
        results.append(check("30. [fresh-init] injected failure on the very first run makes it fail",
                             first_ever.returncode != 0, first_ever.stdout + first_ever.stderr))
        results.append(check("30. [fresh-init] .eif does not exist at all after rollback (not left behind empty)",
                             not (inst5 / ".eif").exists(), f"exists={( inst5 / '.eif').exists()}, contents={list((inst5 / '.eif').iterdir()) if (inst5 / '.eif').exists() else None}"))
        results.append(check("30. [fresh-init] CLAUDE.md was not created either (nothing partially written outside .eif)",
                             not (inst5 / "CLAUDE.md").exists()))
        results.append(check("30. [fresh-init] no orphaned .next/.previous files anywhere in the instance directory",
                             not any(inst5.rglob("*.next")) and not any(inst5.rglob("*.previous"))))

        # Prove the stage really was reached (not silently skipped, which
        # would make "injected failure" above a false positive for the
        # wrong reason) by re-running for real and confirming it succeeds
        # cleanly from this now-genuinely-empty starting point.
        real_run = run([str(fake_fw2 / "scripts" / "eif_init.py"), "--framework-root", str(fake_fw2),
                        "--instance-path", str(inst5), "--project-name", "fresh-init-rollback-test",
                        "--locale", "en", "--framework-ref", fake_ref2])
        results.append(check("30. [fresh-init] a real re-run (no fault injection) succeeds from the clean slate",
                             real_run.returncode == 0, real_run.stdout + real_run.stderr))
        results.append(check("30. [fresh-init] .eif now exists for real after the successful re-run",
                             (inst5 / ".eif" / "config.yaml").exists() and (inst5 / ".eif" / "runtime").is_dir()))

    passed = sum(results)
    print(f"\ntest_journey: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
