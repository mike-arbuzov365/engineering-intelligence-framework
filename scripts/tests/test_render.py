#!/usr/bin/env python3
"""Tests for eif_render.py: the real, user-facing localized-render command.

Invokes the script as a subprocess (the way a project author actually uses
it), not just the underlying eif_locale functions.

Usage:
    python scripts/tests/test_render.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = FRAMEWORK_ROOT / "scripts" / "eif_render.py"


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--framework-root", str(FRAMEWORK_ROOT), *args],
        capture_output=True, text=True, encoding="utf-8",
    )


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def main() -> int:
    results = []

    uk_kd = run(["--locale", "uk", "knowledge-delta"])
    results.append(check("uk knowledge-delta renders Ukrainian headings", "Дельта знань" in uk_kd.stdout, uk_kd.stdout[:120]))

    uk_co = run(["--locale", "uk", "session-closeout"])
    results.append(check("uk session-closeout renders Ukrainian headings", "Сесію завершено" in uk_co.stdout, uk_co.stdout[:120]))

    # Unknown locale falls back to en, does not crash.
    xx = run(["--locale", "xx-nonexistent", "knowledge-delta"])
    results.append(check("unknown locale falls back to en template (exit 0)", xx.returncode == 0 and "Knowledge Delta" in xx.stdout))

    # Localized message with interpolation.
    m = run(["--locale", "uk", "message", "--key", "init_complete", "--set", "path=/tmp/x"])
    results.append(check("uk message interpolates and renders Cyrillic",
                         m.returncode == 0 and any("а" <= c <= "я" or c in "іїєґ" for c in m.stdout.lower()),
                         m.stdout + m.stderr))

    # English identifiers preserved: EIF stays English even in uk message.
    m_en_ident = run(["--locale", "uk", "message", "--key", "init_start", "--set", "path=/tmp/x"])
    results.append(check("technical identifier EIF stays English in uk output", "EIF" in m_en_ident.stdout))

    passed = sum(results)
    print(f"\ntest_render: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
