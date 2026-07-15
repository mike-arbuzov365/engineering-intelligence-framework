#!/usr/bin/env python3
"""Render a localized, project-facing EIF artifact (Knowledge Delta, session
closeout, or a status message) - config-driven, truthful, and writes a real
file by default.

Truthful rendering (round-3 review, Finding H):
  - If .eif/config.yaml EXISTS but is invalid (bad YAML, or missing
    localization.documentation_locale), rendering FAILS - it does not
    silently fall back to English and pretend nothing was wrong. A missing
    config file is fine (falls back to English); a broken one is not the
    same thing.
  - A "final" render (the default) with unresolved {placeholder} tokens
    FAILS - pass --set for every token, or pass --draft to explicitly
    accept a partial render.
  - Output writes are atomic (write to a temp file in the same directory,
    then rename into place) - an interrupted write never leaves a
    half-written artifact where a complete one used to be.

This is the real, user-facing rendering path the locale layer needs: run
from an instance root with no flags beyond --framework-root, it reads the
locale from .eif/config.yaml and writes knowledge-delta.md / session-closeout.md
into the instance - it does not just print a template to stdout and leave the
caller to redirect it.

Framework identifiers, schema field names, commands and code stay English;
only the generated prose/headings are localized, per
docs/architecture/HOW-EIF-WORKS.md#language-configuration.

Usage:
    python scripts/eif_render.py --framework-root PATH knowledge-delta
    python scripts/eif_render.py --framework-root PATH session-closeout --set task_name=... [...]
    python scripts/eif_render.py --framework-root PATH session-closeout --draft   # partial fill OK
    python scripts/eif_render.py --framework-root PATH --locale uk --stdout knowledge-delta
    python scripts/eif_render.py --framework-root PATH message --key init_complete --set path=/some/dir
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eif_locale import msg, render_template, UnresolvedPlaceholderError  # noqa: E402

try:
    import yaml
except ImportError:
    print(
        "eif-render: PyYAML is required. Install with: "
        "pip install -r scripts/requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(1)

TEMPLATE_FILES = {
    "knowledge-delta": "knowledge-delta.md",
    "session-closeout": "session-closeout.md",
}


class ConfigError(Exception):
    """.eif/config.yaml exists but is invalid - must fail, not silently fall
    back to English as if the file were simply absent."""


def locale_from_config(instance_root: Path) -> str | None:
    """Return the configured locale, or None if there is genuinely no
    config file (a legitimate case that falls back to English). Raises
    ConfigError if a config file EXISTS but is broken - that is not the
    same situation and must not be silently treated the same way."""
    config_path = instance_root / ".eif" / "config.yaml"
    if not config_path.exists():
        return None
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"{config_path} exists but is not valid YAML: {e}")
    if not isinstance(data, dict):
        raise ConfigError(f"{config_path} exists but does not contain a YAML mapping")
    locale = (data.get("localization") or {}).get("documentation_locale")
    if not locale:
        raise ConfigError(f"{config_path} exists but has no localization.documentation_locale")
    return locale


def resolve_locale(args_locale: str | None, instance_root: Path) -> tuple[str, str]:
    """Return (locale, source_description). Raises ConfigError (propagated
    from locale_from_config) if the instance's config is broken."""
    if args_locale:
        return args_locale, "explicit --locale"
    from_config = locale_from_config(instance_root)
    if from_config:
        return from_config, f"{instance_root / '.eif' / 'config.yaml'}"
    return "en", "default (no --locale, no .eif/config.yaml found)"


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)  # atomic on both POSIX and Windows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--framework-root", required=True, help="Framework checkout OR an instance's .eif/runtime bundle (where locales/ lives)")
    ap.add_argument("--instance-root", default=".", help="Instance root - used to read .eif/config.yaml for the default locale and to resolve the default output path. Default: current directory.")
    ap.add_argument("--locale", default=None, help="Override the locale. Default: read from --instance-root's .eif/config.yaml, falling back to 'en'.")
    ap.add_argument("artifact", choices=[*TEMPLATE_FILES.keys(), "message"], help="What to render")
    ap.add_argument("--out", default=None, help="Output file path (knowledge-delta/session-closeout only). Default: <instance-root>/<artifact-name>.md")
    ap.add_argument("--stdout", action="store_true", help="Print to stdout instead of writing the default file")
    ap.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    ap.add_argument("--draft", action="store_true", help="Accept a partial render: unresolved {placeholder} tokens are left as literal text instead of failing. Default is a 'final' render that fails on any unresolved token.")
    ap.add_argument("--key", default=None, help="Message key (only for artifact=message)")
    ap.add_argument("--set", dest="kv", action="append", default=[], metavar="key=value",
                    help="Interpolation pair, repeatable - fills {placeholder} tokens in "
                         "session-closeout, or a message's interpolation fields. "
                         "knowledge-delta has no placeholders, so --set is a no-op there.")
    args = ap.parse_args()

    framework_root = Path(args.framework_root).resolve()
    instance_root = Path(args.instance_root).resolve()
    try:
        locale, locale_source = resolve_locale(args.locale, instance_root)
    except ConfigError as e:
        print(f"eif-render: {e}", file=sys.stderr)
        return 1

    params = {}
    for pair in args.kv:
        if "=" not in pair:
            print(f"eif-render: bad key=value pair: {pair}", file=sys.stderr)
            return 1
        k, v = pair.split("=", 1)
        params[k] = v

    if args.artifact == "message":
        if not args.key:
            print("eif-render: --key is required when artifact is 'message'", file=sys.stderr)
            return 1
        rendered = msg(framework_root, locale, args.key, **params)
        if args.out:
            atomic_write(Path(args.out), rendered)
            print(f"eif-render: wrote message ({locale}, from {locale_source}) -> {args.out}", file=sys.stderr)
        else:
            print(rendered)
        return 0

    try:
        rendered, used_locale = render_template(framework_root, locale, TEMPLATE_FILES[args.artifact], draft=args.draft, **params)
    except UnresolvedPlaceholderError as e:
        print(f"eif-render: {e}", file=sys.stderr)
        return 1
    fallback_note = f" (requested '{locale}', not found - fell back to '{used_locale}')" if used_locale != locale else ""

    if args.stdout:
        print(f"# locale: {used_locale}{fallback_note}, source: {locale_source}", file=sys.stderr)
        print(rendered)
        return 0

    out_path = Path(args.out).resolve() if args.out else instance_root / TEMPLATE_FILES[args.artifact]
    if out_path.exists() and not args.force:
        print(
            f"eif-render: {out_path} already exists. Refusing to overwrite it. "
            f"Re-run with --force, or --stdout to print without writing.",
            file=sys.stderr,
        )
        return 1
    atomic_write(out_path, rendered)
    print(f"eif-render: wrote {args.artifact} ({used_locale}{fallback_note}, source: {locale_source}) -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
