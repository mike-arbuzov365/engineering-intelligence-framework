#!/usr/bin/env python3
"""Render a localized, project-facing EIF artifact (Knowledge Delta, session
closeout, or a status message) to stdout or a file.

This is the real, user-facing rendering path the locale layer needs: a
committed command a project author actually runs, not a one-off script.
Framework identifiers, schema field names, commands and code stay English;
only the generated prose/headings are localized, per
docs/architecture/HOW-EIF-WORKS.md#language-configuration.

Falls back to the `en` locale for any missing locale/template/message, so a
partially-translated locale degrades gracefully rather than failing.

Usage:
    python scripts/eif_render.py --framework-root PATH --locale uk knowledge-delta
    python scripts/eif_render.py --framework-root PATH --locale uk session-closeout [--out FILE]
    python scripts/eif_render.py --framework-root PATH --locale uk message --key init_complete --set path=/some/dir
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eif_locale import msg, render_template  # noqa: E402

TEMPLATE_FILES = {
    "knowledge-delta": "knowledge-delta.md",
    "session-closeout": "session-closeout.md",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--framework-root", required=True, help="Framework root or instance .eif/runtime bundle (where locales/ lives)")
    ap.add_argument("--locale", default="en")
    ap.add_argument("artifact", choices=[*TEMPLATE_FILES.keys(), "message"], help="What to render")
    ap.add_argument("--out", default=None, help="Write to this file instead of stdout")
    ap.add_argument("--key", default=None, help="Message key (only for artifact=message)")
    ap.add_argument("--set", dest="kv", action="append", default=[], metavar="key=value",
                    help="Interpolation pair for artifact=message; repeatable")
    args = ap.parse_args()

    framework_root = Path(args.framework_root).resolve()

    if args.artifact == "message":
        if not args.key:
            print("eif-render: --key is required when artifact is 'message'", file=sys.stderr)
            return 1
        params = {}
        for pair in args.kv:
            if "=" not in pair:
                print(f"eif-render: bad key=value pair: {pair}", file=sys.stderr)
                return 1
            k, v = pair.split("=", 1)
            params[k] = v
        rendered = msg(framework_root, args.locale, args.key, **params)
        used_locale = args.locale
    else:
        rendered, used_locale = render_template(framework_root, args.locale, TEMPLATE_FILES[args.artifact])

    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
        print(f"eif-render: wrote {args.artifact} ({used_locale}) -> {args.out}", file=sys.stderr)
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
