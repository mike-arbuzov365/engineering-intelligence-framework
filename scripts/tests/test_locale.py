#!/usr/bin/env python3
"""Tests for eif_locale.py's message/template lookup and fallback.

Usage:
    python scripts/tests/test_locale.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

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
        uk_kd_locale == "uk" and uk_kd_text.startswith("## Knowledge Delta"),
    ))

    fallback_kd_text, fallback_kd_locale = render_template(FRAMEWORK_ROOT, "xx-nonexistent", "knowledge-delta.md")
    en_kd_text, _ = render_template(FRAMEWORK_ROOT, "en", "knowledge-delta.md")
    results.append(check(
        "render_template fallback: unknown locale directory falls back to en template",
        fallback_kd_locale == "en" and fallback_kd_text == en_kd_text,
    ))

    en_terms = yaml.safe_load(
        (FRAMEWORK_ROOT / "locales" / "en" / "terminology.yaml").read_text(encoding="utf-8")
    )
    uk_terms = yaml.safe_load(
        (FRAMEWORK_ROOT / "locales" / "uk" / "terminology.yaml").read_text(encoding="utf-8")
    )
    results.append(check(
        "terminology packs use the same canonical term keys",
        set(en_terms["terms"]) == set(uk_terms["terms"]),
    ))
    required_agentic_terms = {
        "large_language_model",
        "ai_agent",
        "agentic_software_development",
        "agent_harness",
        "context_engineering",
        "context_window",
        "session_context",
        "compaction",
        "agent_memory",
        "retrieval",
        "model_context_protocol",
        "agents_md",
        "agent_skill",
        "agent_skills_specification",
        "specification_driven_development",
        "evaluation",
        "checkpoint",
        "project_knowledge",
    }
    results.append(check(
        "terminology packs cover the agentic-development publication contract",
        required_agentic_terms <= set(en_terms["terms"]),
        f"missing={required_agentic_terms - set(en_terms['terms'])}",
    ))
    allowed_term_classes = {
        "standards-aligned",
        "open-specification",
        "industry-established",
        "emerging-industry",
        "eif-defined",
    }
    results.append(check(
        "terminology packs use the same approved class for every concept",
        all(
            en_terms["terms"][key].get("class") == uk_terms["terms"][key].get("class")
            and en_terms["terms"][key].get("class") in allowed_term_classes
            for key in en_terms["terms"]
        ),
    ))
    results.append(check(
        "named EIF artifacts stay canonical in Ukrainian",
        uk_terms["terms"]["knowledge_delta"]["preferred"] == "Knowledge Delta"
        and uk_terms["terms"]["execution_packet"]["preferred"] == "execution packet",
    ))
    results.append(check(
        "Ukrainian agentic terms keep the agent, model, and harness distinct",
        uk_terms["terms"]["large_language_model"]["preferred"] == "велика мовна модель (LLM)"
        and uk_terms["terms"]["ai_agent"]["preferred"] == "агент ШІ"
        and uk_terms["terms"]["agent_harness"]["preferred"] == "агентний харнес",
    ))

    uk_pack_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((FRAMEWORK_ROOT / "locales" / "uk").rglob("*"))
        if path.is_file() and path.name != "terminology.yaml"
    )
    results.append(check(
        "Ukrainian locale pack avoids deprecated calques and em dashes",
        "Дельта знань" not in uk_pack_text
        and "Промоут" not in uk_pack_text
        and "—" not in uk_pack_text,
    ))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_locale: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
