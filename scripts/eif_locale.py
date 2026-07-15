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

import re
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

PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")


class UnresolvedPlaceholderError(Exception):
    """A 'final' (non-draft) render still has {placeholder} tokens after
    substitution - round-3 review, Finding H: a final Knowledge Delta or
    closeout with silently-unfilled tokens is a truthfulness bug, not a
    convenience. Pass every value, or render with draft=True to explicitly
    accept a partial fill."""


class _KeepMissing(dict):
    """dict that leaves an unrecognized {key} token as literal text instead of
    raising KeyError - str.format() requires every placeholder in a template
    to be supplied at once, which is wrong for a partial-fill workflow (e.g.
    filling task_name now, verification_result after the test runs). Known
    keys still get replaced; everything else stays as `{key}` for the next
    fill or for manual completion."""

    def __missing__(self, key):
        return "{" + key + "}"


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


def render_template(framework_root: Path, locale: str, template_name: str,
                    draft: bool = False, **kwargs) -> tuple[str, str]:
    """Returns (rendered_text, locale_actually_used).

    Substitution is always partial-fill (a caller filling task_name before
    a test has run, and verification_result after, is a normal workflow,
    not an error mid-way through). What differs is what happens with
    whatever's LEFT unresolved once kwargs are applied:

    - draft=False (default): any remaining {placeholder} raises
      UnresolvedPlaceholderError - a "final" render with a silently-unfilled
      token is a truthfulness bug (round-3 review, Finding H).
    - draft=True: remaining placeholders are left as literal text, same as
      before - an explicit, deliberate partial render.
    """
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
        text = text.format_map(_KeepMissing(kwargs))
    if not draft:
        unresolved = sorted(set(PLACEHOLDER_RE.findall(text)))
        if unresolved:
            raise UnresolvedPlaceholderError(
                f"{template_name}: unresolved placeholder(s) after substitution: "
                f"{', '.join(unresolved)} - pass --set for each, or --draft to "
                f"explicitly accept a partial render"
            )
    return text, used_locale
