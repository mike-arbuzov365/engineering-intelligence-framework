#!/usr/bin/env python3
"""Tests for eif_render.py: config-driven locale resolution, real
file-writing default (not stdout-only), overwrite protection, and English
fallback.

Invokes the script as a subprocess (the way a project author actually uses
it), not just the underlying eif_locale functions.

Usage:
    python scripts/tests/test_render.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = FRAMEWORK_ROOT / "scripts" / "eif_render.py"

UK_CONFIG = """\
schema_version: 1
project:
  name: test
adapter:
  name: claude-code
localization:
  documentation_locale: uk
"""


def run(instance_root: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--framework-root", str(FRAMEWORK_ROOT),
         "--instance-root", str(instance_root), *args],
        capture_output=True, text=True, encoding="utf-8",
    )


def check(name: str, condition: bool, detail: str = "") -> bool:
    condition = bool(condition)
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def main() -> int:
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        inst = Path(tmp) / "uk-instance"
        (inst / ".eif").mkdir(parents=True)
        (inst / ".eif" / "config.yaml").write_text(UK_CONFIG, encoding="utf-8")

        # Config-driven: no --locale flag, reads uk from .eif/config.yaml.
        r = run(inst, ["knowledge-delta"])
        results.append(check("no --locale flag: reads locale from .eif/config.yaml", r.returncode == 0, r.stdout + r.stderr))
        out_file = inst / "knowledge-delta.md"
        results.append(check("writes a real file by default (not stdout-only)", out_file.exists(), r.stdout + r.stderr))
        results.append(check("written file has Ukrainian headings", "Дельта знань" in out_file.read_text(encoding="utf-8") if out_file.exists() else False))

        # Overwrite protection.
        r2 = run(inst, ["knowledge-delta"])
        results.append(check("second run without --force refuses to overwrite", r2.returncode != 0, r2.stdout + r2.stderr))
        r3 = run(inst, ["knowledge-delta", "--force"])
        results.append(check("--force allows overwrite", r3.returncode == 0, r3.stdout + r3.stderr))

        # session-closeout too.
        r4 = run(inst, ["session-closeout"])
        co_file = inst / "session-closeout.md"
        results.append(check("session-closeout also writes a real file", co_file.exists()))
        results.append(check("session-closeout file has Ukrainian headings", "Сесію завершено" in co_file.read_text(encoding="utf-8") if co_file.exists() else False))

        # --stdout opts out of file-writing.
        r5 = run(inst, ["--stdout", "message", "--key", "init_complete", "--set", "path=/tmp/x"])
        results.append(check("--stdout prints instead of writing a file", "EIF" in r5.stdout, r5.stdout + r5.stderr))

        # --set on session-closeout: partial fill must not crash (real bug
        # found this round - str.format() requires every placeholder at
        # once, which is wrong for filling task_name now and
        # verification_result after the test runs).
        r6 = run(inst, ["--stdout", "session-closeout", "--set", "task_name=my task"])
        results.append(check("--set with only ONE of several placeholders does not crash",
                             r6.returncode == 0, r6.stdout + r6.stderr))
        results.append(check("--set fills the given placeholder", "my task" in r6.stdout, r6.stdout))
        results.append(check("--set leaves other placeholders as literal tokens for a later fill",
                             "{branch_or_pr}" in r6.stdout, r6.stdout))

        # All placeholders given at once: every token filled, none left over.
        r7 = run(inst, ["--stdout", "session-closeout",
                        "--set", "task_name=t", "--set", "branch_or_pr=b",
                        "--set", "verification_result=v", "--set", "artifacts=a",
                        "--set", "promoted=p", "--set", "not_done=n", "--set", "open_questions=o"])
        results.append(check("--set with all placeholders leaves no {token} unfilled",
                             "{" not in r7.stdout, r7.stdout))

    with tempfile.TemporaryDirectory() as tmp:
        inst_en = Path(tmp) / "no-config-instance"
        inst_en.mkdir()
        # No .eif/config.yaml at all -> falls back to en, does not crash.
        r = run(inst_en, ["--stdout", "knowledge-delta"])
        results.append(check("missing .eif/config.yaml falls back to en, not a crash", r.returncode == 0 and "Knowledge Delta" in r.stdout, r.stdout + r.stderr))

        # Explicit --locale overrides config (there is none here, but proves override wins).
        r2 = run(inst_en, ["--locale", "uk", "--stdout", "knowledge-delta"])
        results.append(check("explicit --locale overrides (no config present) config-derived default", "Дельта знань" in r2.stdout, r2.stdout))

        # Unknown locale falls back to en template, does not crash.
        r3 = run(inst_en, ["--locale", "xx-nonexistent", "--stdout", "knowledge-delta"])
        results.append(check("unknown locale falls back to en template (exit 0)", r3.returncode == 0 and "Knowledge Delta" in r3.stdout))

    passed = sum(results)
    print(f"\ntest_render: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
