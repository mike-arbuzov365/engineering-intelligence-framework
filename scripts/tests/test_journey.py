#!/usr/bin/env python3
"""Full, isolated, subprocess-based journey test.

Runs the actual CLI scripts as subprocesses against a fresh seed project in
a temp directory - not just calling internal functions - so this proves the
lifecycle mechanics an instance owner would actually experience, not an
approximation of them.

Covers: real init CLI -> config/lock validation -> runtime materialization
-> adapter entrypoint generation -> knowledge index generation -> English +
Ukrainian retrieval -> task-scope creation -> failing behavioral test ->
deterministic solution application -> passing behavioral test -> config-
driven Ukrainian Knowledge Delta + closeout generation TO FILES -> artifact
validation -> privacy + link checks from the instance's own bundle ->
non-destructive re-init (upgrade) -> an injected upgrade failure (a
mandatory bundle source goes missing) proving the instance's existing,
working runtime survives untouched.

Deliberately does not need an agent to re-derive the fix - it proves the
framework lifecycle mechanics reproduce, using the same recorded solution as
examples/demo-workspace.

Usage:
    python scripts/tests/test_journey.py
"""
from __future__ import annotations

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


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True, text=True, encoding="utf-8",
    )


def check(name: str, condition: bool, detail: str = "") -> bool:
    condition = bool(condition)
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")


def main() -> int:
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "seed-project"
        inst.mkdir()

        # A real instance is a real git repo - eif_privacy_scan.py and
        # eif_check_links.py both fail closed against a non-git directory
        # (a deliberate design choice from an earlier round), so this is not
        # optional scaffolding, it's what makes step 14 below meaningful.
        git(["init", "-q"], inst)
        git(["config", "user.email", "test@example.invalid"], inst)
        git(["config", "user.name", "Journey Test"], inst)

        # --- 1. Real init CLI ---
        r = run([str(SCRIPTS / "eif_init.py"), "--framework-root", str(FRAMEWORK_ROOT),
                 "--instance-path", str(inst), "--project-name", "journey-seed",
                 "--locale", "uk", "--allow-dirty"])
        results.append(check("1. real eif_init.py subprocess succeeds", r.returncode == 0, r.stdout + r.stderr))

        # --- 2. Config/lock validation (already run inside eif_init, re-verify standalone) ---
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

        # --- 5. Knowledge index generation: seed real artifacts, regenerate ---
        knowledge = inst / "knowledge"
        (knowledge / "facts").mkdir(parents=True)
        (knowledge / "facts" / "FACT-0001.md").write_text(FACT_ARTIFACT, encoding="utf-8")
        (knowledge / "failure-patterns").mkdir()
        (knowledge / "failure-patterns" / "PATTERN-0001.md").write_text(PATTERN_ARTIFACT, encoding="utf-8")
        idx = run([str(bundle / "eif_generate_index.py"), "--knowledge-root", str(knowledge), "--framework-root", str(bundle)])
        results.append(check("5. knowledge index generated via the bundle", idx.returncode == 0 and (knowledge / "index.md").exists(), idx.stdout + idx.stderr))

        # --- 6. English and Ukrainian retrieval, from the bundle, from the instance ---
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
        co = run([str(bundle / "eif_render.py"), "--framework-root", str(bundle), "session-closeout"], cwd=inst)
        kd_file, co_file = inst / "knowledge-delta.md", inst / "session-closeout.md"
        results.append(check("11. config-driven render created knowledge-delta.md (locale from config, no --locale flag)",
                             kd.returncode == 0 and kd_file.exists() and "Дельта знань" in kd_file.read_text(encoding="utf-8"),
                             kd.stdout + kd.stderr))
        results.append(check("12. config-driven render created session-closeout.md",
                             co.returncode == 0 and co_file.exists() and "Сесію завершено" in co_file.read_text(encoding="utf-8"),
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

        # --- 15. Non-destructive re-init (the routine upgrade path) ---
        cfg_before = (inst / ".eif" / "config.yaml").read_text(encoding="utf-8")
        upgrade = run([str(SCRIPTS / "eif_init.py"), "--framework-root", str(FRAMEWORK_ROOT),
                       "--instance-path", str(inst), "--project-name", "journey-seed",
                       "--locale", "uk", "--allow-dirty"])
        results.append(check("15. re-init (upgrade) succeeds", upgrade.returncode == 0, upgrade.stdout + upgrade.stderr))
        results.append(check("15. upgrade leaves user config byte-for-byte unchanged",
                             (inst / ".eif" / "config.yaml").read_text(encoding="utf-8") == cfg_before))
        results.append(check("15. upgrade creates no config backup (only --force would)",
                             list((inst / ".eif").glob("config.yaml.bak-*")) == []))
        results.append(check("15. knowledge seeded before the upgrade survives it",
                             (inst / "knowledge" / "facts" / "FACT-0001.md").exists()))

        # --- 17. Fresh-directory materialization: same seed, independent instance ---
        inst2 = Path(tmp) / "seed-project-2"
        inst2.mkdir()
        r2 = run([str(SCRIPTS / "eif_init.py"), "--framework-root", str(FRAMEWORK_ROOT),
                  "--instance-path", str(inst2), "--project-name", "journey-seed-2",
                  "--locale", "en", "--allow-dirty"])
        results.append(check("17. a second, independent instance initializes cleanly from the same framework",
                             r2.returncode == 0 and (inst2 / ".eif" / "runtime").is_dir(), r2.stdout + r2.stderr))

    # --- 16. Injected upgrade failure + rollback, using a deliberately broken
    # framework copy so the real repo is never touched. ---
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
        results.append(check("16. first init against the (deliberately non-git) framework copy succeeds via --framework-ref", first.returncode == 0, first.stdout + first.stderr))

        original_lock = (inst3 / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8")

        # Break the framework copy: remove a mandatory bundle source.
        (fake_fw / "scripts" / "eif_render.py").unlink()

        second = run([str(fake_fw / "scripts" / "eif_init.py"), "--framework-root", str(fake_fw),
                      "--instance-path", str(inst3), "--project-name", "rollback-test",
                      "--locale", "en", "--framework-ref", fake_ref])
        results.append(check("16. upgrade against the broken framework copy fails, not silently degrades", second.returncode != 0, second.stdout + second.stderr))

        results.append(check("16. instance's runtime bundle still has the original files after the failed upgrade",
                             (inst3 / ".eif" / "runtime" / "eif_search_knowledge.py").exists()))
        results.append(check("16. instance's lock file is untouched by the failed upgrade (still records the original bundle)",
                             (inst3 / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8") == original_lock))

        still_works = run([str(inst3 / ".eif" / "runtime" / "eif_search_knowledge.py"), "--help"])
        results.append(check("16. the instance's bundle is still functional after the failed upgrade", still_works.returncode == 0, still_works.stdout + still_works.stderr))

    passed = sum(results)
    print(f"\ntest_journey: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
