#!/usr/bin/env python3
"""Render a localized, project-facing EIF artifact (Knowledge Delta, session
closeout, or a status message) - config-driven, and writes a real file by
default.

This is the real, user-facing rendering path the locale layer needs: run
from an instance root with no flags beyond --framework-root, it reads the
locale from .eif/config.yaml and writes knowledge-delta.md / session-closeout.md
into the instance - it does not just print a template to stdout and leave the
caller to redirect it (a generated CLAUDE.md command that only prints creates
nothing; this command creates the file it names).

Framework identifiers, schema field names, commands and code stay English;
only the generated prose/headings are localized, per
docs/architecture/HOW-EIF-WORKS.md#language-configuration.

Locale resolution order: --locale flag, then .eif/config.yaml
localization.documentation_locale under --instance-root, then "en". Falls
back to the `en` template/message for anything missing in the resolved
locale, so a partially-translated locale degrades gracefully.

Usage:
    python scripts/eif_render.py --framework-root PATH knowledge-delta
    python scripts/eif_render.py --framework-root PATH session-closeout --force
    python scripts/eif_render.py --framework-root PATH --locale uk --stdout knowledge-delta
    python scripts/eif_render.py --framework-root PATH message --key init_complete --set path=/some/dir
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eif_locale import msg, render_template  # noqa: E402

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


def locale_from_config(instance_root: Path) -> str | None:
    config_path = instance_root / ".eif" / "config.yaml"
    if not config_path.exists():
        return None
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None
    return (data.get("localization") or {}).get("documentation_locale")


def resolve_locale(args_locale: str | None, instance_root: Path) -> tuple[str, str]:
    """Return (locale, source_description)."""
    if args_locale:
        return args_locale, "explicit --locale"
    from_config = locale_from_config(instance_root)
    if from_config:
        return from_config, f"{instance_root / '.eif' / 'config.yaml'}"
    return "en", "default (no --locale, no .eif/config.yaml found)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--framework-root", required=True, help="Framework checkout OR an instance's .eif/runtime bundle (where locales/ lives)")
    ap.add_argument("--instance-root", default=".", help="Instance root - used to read .eif/config.yaml for the default locale and to resolve the default output path. Default: current directory.")
    ap.add_argument("--locale", default=None, help="Override the locale. Default: read from --instance-root's .eif/config.yaml, falling back to 'en'.")
    ap.add_argument("artifact", choices=[*TEMPLATE_FILES.keys(), "message"], help="What to render")
    ap.add_argument("--out", default=None, help="Output file path (knowledge-delta/session-closeout only). Default: <instance-root>/<artifact-name>.md")
    ap.add_argument("--stdout", action="store_true", help="Print to stdout instead of writing the default file")
    ap.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    ap.add_argument("--key", default=None, help="Message key (only for artifact=message)")
    ap.add_argument("--set", dest="kv", action="append", default=[], metavar="key=value",
                    help="Interpolation pair, repeatable - fills {placeholder} tokens in "
                         "session-closeout, or a message's interpolation fields. "
                         "knowledge-delta has no placeholders, so --set is a no-op there.")
    args = ap.parse_args()

    framework_root = Path(args.framework_root).resolve()
    instance_root = Path(args.instance_root).resolve()
    locale, locale_source = resolve_locale(args.locale, instance_root)

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
            Path(args.out).write_text(rendered, encoding="utf-8")
            print(f"eif-render: wrote message ({locale}, from {locale_source}) -> {args.out}", file=sys.stderr)
        else:
            print(rendered)
        return 0

    rendered, used_locale = render_template(framework_root, locale, TEMPLATE_FILES[args.artifact], **params)
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
    out_path.write_text(rendered, encoding="utf-8")
    print(f"eif-render: wrote {args.artifact} ({used_locale}{fallback_note}, source: {locale_source}) -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
