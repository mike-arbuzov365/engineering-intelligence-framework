#!/usr/bin/env python3
"""Tests for eif_render.py: config-driven locale resolution, real
file-writing default, overwrite protection, English fallback, and truthful
rendering (round-3 review, Finding H) - invalid config fails loudly rather
than silently degrading to English, and a "final" (non-draft) render with
unresolved placeholders fails rather than shipping an incomplete artifact.

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

ALL_CLOSEOUT_SET = [
    "--set", "task_name=t", "--set", "branch_or_pr=b",
    "--set", "verification_result=v", "--set", "artifacts=a",
    "--set", "promoted=p", "--set", "not_done=n", "--set", "open_questions=o",
]


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

        # --- Finding H: strict-by-default rendering ---
        r4 = run(inst, ["session-closeout"])
        results.append(check("FINAL closeout with NO --set fails by default (Finding H - not a silent partial artifact)",
                             r4.returncode != 0, r4.stdout + r4.stderr))
        results.append(check("closeout file NOT written when the strict render failed",
                             not (inst / "session-closeout.md").exists()))

        r4b = run(inst, ["session-closeout", "--draft"])
        results.append(check("--draft explicitly allows an incomplete closeout to be written",
                             r4b.returncode == 0, r4b.stdout + r4b.stderr))
        co_file = inst / "session-closeout.md"
        results.append(check("draft closeout file is written and has Ukrainian headings",
                             co_file.exists() and "Сесію завершено" in co_file.read_text(encoding="utf-8") if co_file.exists() else False))
        co_file.unlink(missing_ok=True)

        r4c = run(inst, ["session-closeout", *ALL_CLOSEOUT_SET])
        results.append(check("FINAL closeout with every placeholder set succeeds (no --draft needed)",
                             r4c.returncode == 0, r4c.stdout + r4c.stderr))
        results.append(check("fully-set closeout file has no leftover {token}",
                             co_file.exists() and "{" not in co_file.read_text(encoding="utf-8")))

        # --stdout opts out of file-writing.
        r5 = run(inst, ["--stdout", "message", "--key", "init_complete", "--set", "path=/tmp/x"])
        results.append(check("--stdout prints instead of writing a file", "EIF" in r5.stdout, r5.stdout + r5.stderr))

        # Partial --set without --draft still fails (strict is the default
        # regardless of --stdout vs file output).
        r6 = run(inst, ["--stdout", "session-closeout", "--set", "task_name=my task"])
        results.append(check("partial --set without --draft fails even in --stdout mode",
                             r6.returncode != 0, r6.stdout + r6.stderr))

        # Partial --set WITH --draft: fills what's given, leaves the rest literal.
        r6b = run(inst, ["--stdout", "session-closeout", "--draft", "--set", "task_name=my task"])
        results.append(check("--draft + partial --set does not crash",
                             r6b.returncode == 0, r6b.stdout + r6b.stderr))
        results.append(check("--draft + partial --set fills the given placeholder", "my task" in r6b.stdout, r6b.stdout))
        results.append(check("--draft + partial --set leaves other placeholders literal for a later fill",
                             "{branch_or_pr}" in r6b.stdout, r6b.stdout))

    # --- Finding H: invalid config fails loudly, not a silent English fallback ---
    with tempfile.TemporaryDirectory() as tmp:
        inst_broken = Path(tmp) / "broken-config-instance"
        (inst_broken / ".eif").mkdir(parents=True)
        (inst_broken / ".eif" / "config.yaml").write_text("schema_version: [this is not valid yaml\n", encoding="utf-8")
        r = run(inst_broken, ["--stdout", "knowledge-delta"])
        results.append(check("config.yaml exists but is invalid YAML -> render FAILS, not a silent English fallback",
                             r.returncode != 0, r.stdout + r.stderr))

        inst_incomplete = Path(tmp) / "incomplete-config-instance"
        (inst_incomplete / ".eif").mkdir(parents=True)
        (inst_incomplete / ".eif" / "config.yaml").write_text("schema_version: 1\nproject:\n  name: x\n", encoding="utf-8")
        r2 = run(inst_incomplete, ["--stdout", "knowledge-delta"])
        results.append(check("config.yaml exists but has no documentation_locale -> render FAILS",
                             r2.returncode != 0, r2.stdout + r2.stderr))

        # Explicit --locale bypasses config entirely, so it still works even
        # with a broken config on disk - the flag is an explicit override,
        # not a value that depends on the config being readable.
        r3 = run(inst_broken, ["--locale", "en", "--stdout", "knowledge-delta"])
        results.append(check("explicit --locale works even with a broken config.yaml present",
                             r3.returncode == 0, r3.stdout + r3.stderr))

    with tempfile.TemporaryDirectory() as tmp:
        inst_en = Path(tmp) / "no-config-instance"
        inst_en.mkdir()
        # No .eif/config.yaml at all -> falls back to en, does not crash.
        # (Genuinely different from "config exists but is broken" above.)
        r = run(inst_en, ["--stdout", "knowledge-delta"])
        results.append(check("missing .eif/config.yaml (not broken - absent) falls back to en, not a crash", r.returncode == 0 and "Knowledge Delta" in r.stdout, r.stdout + r.stderr))

        r2 = run(inst_en, ["--locale", "uk", "--stdout", "knowledge-delta"])
        results.append(check("explicit --locale overrides (no config present) config-derived default", "Дельта знань" in r2.stdout, r2.stdout))

        r3 = run(inst_en, ["--locale", "xx-nonexistent", "--stdout", "knowledge-delta"])
        results.append(check("unknown locale falls back to en template (exit 0)", r3.returncode == 0 and "Knowledge Delta" in r3.stdout))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_render: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
