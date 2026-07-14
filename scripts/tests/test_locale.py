#!/usr/bin/env python3
"""Tests for eif_locale.py's message/template lookup and fallback.

Usage:
    python scripts/tests/test_locale.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eif_locale import load_messages, msg, render_template  # noqa: E402

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def main() -> int:
    results = []

    en_messages = load_messages(FRAMEWORK_ROOT, "en")
    uk_messages = load_messages(FRAMEWORK_ROOT, "uk")

    results.append(check(
        "en and uk messages.yaml have the same key set",
        set(en_messages) == set(uk_messages),
        f"en-only={set(en_messages) - set(uk_messages)} uk-only={set(uk_messages) - set(en_messages)}",
    ))
    results.append(check("en/messages.yaml is non-empty", len(en_messages) > 0))

    uk_text = msg(FRAMEWORK_ROOT, "uk", "init_complete", path="/tmp/demo")
    results.append(check(
        "Ukrainian output: msg() renders Cyrillic content for a known key",
        any("а" <= c <= "я" or c in "іїєґ" for c in uk_text.lower()),
        uk_text,
    ))

    en_text = msg(FRAMEWORK_ROOT, "en", "init_complete", path="/tmp/demo")
    results.append(check(
        "English content does not contain Cyrillic",
        not any("а" <= c <= "я" or c in "іїєґ" for c in en_text.lower()),
        en_text,
    ))

    fallback_text = msg(FRAMEWORK_ROOT, "xx-nonexistent", "init_complete", path="/tmp/demo")
    results.append(check(
        "English fallback: unknown locale falls back to en, not a crash or [missing message]",
        fallback_text == en_text,
        fallback_text,
    ))

    uk_kd_text, uk_kd_locale = render_template(FRAMEWORK_ROOT, "uk", "knowledge-delta.md")
    results.append(check(
        "render_template locale selection: 'uk' resolves to the uk template, not silently falling back",
        uk_kd_locale == "uk" and "Дельта знань" in uk_kd_text,
    ))

    fallback_kd_text, fallback_kd_locale = render_template(FRAMEWORK_ROOT, "xx-nonexistent", "knowledge-delta.md")
    en_kd_text, _ = render_template(FRAMEWORK_ROOT, "en", "knowledge-delta.md")
    results.append(check(
        "render_template fallback: unknown locale directory falls back to en template",
        fallback_kd_locale == "en" and fallback_kd_text == en_kd_text,
    ))

    passed = sum(results)
    print(f"\ntest_locale: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
