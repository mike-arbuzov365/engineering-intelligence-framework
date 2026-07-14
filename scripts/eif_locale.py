#!/usr/bin/env python3
"""Locale-aware message and template rendering for EIF project instances.

Not a general i18n framework - a small, explicit lookup layer. Canonical
methodology text (this framework's own docs) is never localized; only
generated, project-facing output is (status messages, Knowledge Delta and
closeout headings). See docs/architecture/HOW-EIF-WORKS.md#language-configuration.

Fallback rule: if a locale directory, its messages.yaml, a specific message
key, or a specific template is missing, fall back to the `en` locale rather
than failing. `en` itself must always be complete - see
scripts/tests/test_locale.py for the parity check that enforces this.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "eif-locale: PyYAML is required. Install with: "
        "pip install -r scripts/requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(1)

DEFAULT_LOCALE = "en"


def _locales_dir(framework_root: Path) -> Path:
    return framework_root / "locales"


def load_messages(framework_root: Path, locale: str) -> dict:
    locales_dir = _locales_dir(framework_root)
    path = locales_dir / locale / "messages.yaml"
    if not path.exists():
        path = locales_dir / DEFAULT_LOCALE / "messages.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def msg(framework_root: Path, loc: str, key: str, **kwargs) -> str:
    """Render message `key` in locale `loc`, falling back to `en`.

    Parameter is named `loc`, not `locale`, so callers can pass
    `locale=...` as a **kwargs value to interpolate into a message (e.g.
    "Created config (locale: {locale})") without a name collision.
    """
    messages = load_messages(framework_root, loc)
    template = messages.get(key)
    if template is None:
        fallback = load_messages(framework_root, DEFAULT_LOCALE)
        template = fallback.get(key, f"[missing message: {key}]")
    return template.format(**kwargs)


def render_template(framework_root: Path, locale: str, template_name: str, **kwargs) -> str:
    locales_dir = _locales_dir(framework_root)
    path = locales_dir / locale / "templates" / template_name
    used_locale = locale
    if not path.exists():
        path = locales_dir / DEFAULT_LOCALE / "templates" / template_name
        used_locale = DEFAULT_LOCALE
    if not path.exists():
        raise FileNotFoundError(
            f"eif-locale: template not found in locale '{locale}' or fallback "
            f"'{DEFAULT_LOCALE}': {template_name}"
        )
    text = path.read_text(encoding="utf-8")
    if kwargs:
        text = text.format(**kwargs)
    return text, used_locale
