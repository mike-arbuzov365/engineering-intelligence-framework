#!/usr/bin/env python3
"""EXPERIMENTAL bootstrap for a new EIF project instance.

This is the smallest credible entrypoint that makes the v0.1 vertical
slice reproducible - not a preview of a final `eifctl` CLI. Running this
script does not ratify a CLI name, packaging strategy, or distribution
mechanism (see core/policies/decisions.md D-05 CLI name, D-08 public/
private dependency model - both remain open). If/when those are ratified,
this script is expected to be replaced, not grown into the final tool.

What it does, in order:
  1. Write <instance>/.eif/config.yaml from the framework's
     .eif/config.yaml.example, with schema_version/framework.version/
     project.name/localization filled in from CLI args.
  2. Validate that config against core/schemas/eif-config.schema.json
     (fails loudly if invalid - never writes an unvalidated config and
     calls it done).
  3. Copy templates/agent-instructions.md into <instance>/AGENTS.md
     verbatim (English-canonical - see templates/agent-instructions.md's
     own "Language" section for why this file itself is not localized
     even when the project's documentation locale is not English).
  4. Generate <instance>/knowledge/index.md via eif_generate_index, if
     <instance>/knowledge/ exists.

Framework-root / instance-root separation (from PR #1) is used throughout:
the framework's schemas/templates come from --framework-root, the new
project instance is created at --instance-path, which is never required to
be inside or vendor the framework checkout.

Usage:
    python scripts/eif_init.py --framework-root PATH --instance-path PATH \\
        --project-name NAME [--locale en|uk]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    # Windows consoles default stdout to the active codepage (e.g. cp1252),
    # which cannot encode Cyrillic - and this script's whole point is to
    # print locale-aware messages that may not be ASCII. Without this, a
    # non-English locale crashes on the first print() with UnicodeEncodeError
    # instead of producing the localized output it exists to produce.
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eif_locale import msg  # noqa: E402
from eif_validate_frontmatter import validate_config_mode  # noqa: E402
from eif_generate_index import build_index, render as render_index  # noqa: E402

try:
    import yaml
except ImportError:
    print(
        "eif-init: PyYAML is required. Install with: "
        "pip install -r scripts/requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(1)

CONFIG_TEMPLATE = """\
schema_version: 1

framework:
  version: {framework_version}
  ref: "<commit-sha-you-checked-out>"

project:
  name: {project_name}

localization:
  documentation_locale: {locale}
  agent_response_locale: {locale}
  fallback_locale: en
  preserve_technical_terms: true
  code_comments_locale: en
  commit_messages_locale: en

governance:
  knowledge_delta_required: true
  evidence_labels_required: true
"""


def write_config(instance_path: Path, project_name: str, locale: str, framework_version: str) -> Path:
    eif_dir = instance_path / ".eif"
    eif_dir.mkdir(parents=True, exist_ok=True)
    config_path = eif_dir / "config.yaml"
    config_path.write_text(
        CONFIG_TEMPLATE.format(
            framework_version=framework_version,
            project_name=project_name,
            locale=locale,
        ),
        encoding="utf-8",
    )
    return config_path


def generate_instructions(framework_root: Path, instance_path: Path) -> Path:
    src = framework_root / "templates" / "agent-instructions.md"
    dest = instance_path / "AGENTS.md"
    shutil.copyfile(src, dest)
    return dest


def generate_index(instance_path: Path) -> tuple[Path, int]:
    knowledge_root = instance_path / "knowledge"
    if not knowledge_root.is_dir():
        return knowledge_root, 0
    rows, malformed = build_index(knowledge_root)
    out_path = knowledge_root / "index.md"
    out_path.write_text(render_index(rows, malformed, knowledge_root), encoding="utf-8")
    return out_path, len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--framework-root", required=True, help="This framework's checkout (where templates/ and core/schemas/ live)")
    ap.add_argument("--instance-path", required=True, help="Where to create the new project instance")
    ap.add_argument("--project-name", required=True)
    ap.add_argument("--locale", default="en", help="Documentation locale for this instance (default: en)")
    ap.add_argument("--framework-version", default="0.1.0-dev")
    args = ap.parse_args()

    framework_root = Path(args.framework_root).resolve()
    instance_path = Path(args.instance_path).resolve()
    instance_path.mkdir(parents=True, exist_ok=True)

    print(msg(framework_root, args.locale, "init_start", path=instance_path))

    config_path = write_config(instance_path, args.project_name, args.locale, args.framework_version)
    validate_rc = validate_config_mode(framework_root, config_path)
    if validate_rc != 0:
        print(f"eif-init: generated config failed validation: {config_path}", file=sys.stderr)
        return validate_rc
    print(msg(framework_root, args.locale, "config_created", locale=args.locale))

    instructions_path = generate_instructions(framework_root, instance_path)
    print(msg(framework_root, args.locale, "instructions_generated", path=instructions_path))

    index_path, count = generate_index(instance_path)
    if count or (instance_path / "knowledge").is_dir():
        print(msg(framework_root, args.locale, "index_generated", count=count))

    print(msg(framework_root, args.locale, "init_complete", path=instance_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
