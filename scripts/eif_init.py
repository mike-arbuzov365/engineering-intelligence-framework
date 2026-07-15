#!/usr/bin/env python3
"""EXPERIMENTAL bootstrap for a new (or existing) EIF project instance.

This is the smallest credible entrypoint that makes the v0.1 vertical slice
reproducible from a *separate* project instance - not a preview of a final
`eifctl` CLI, and it does NOT ratify a CLI name, packaging strategy, or
distribution mechanism (D-05 CLI name, D-08 dependency model in
core/policies/decisions.md both remain open).

Design decisions this script embodies (all reversible, none ratified):

1. Self-contained instance. eif_init writes a pinned `.eif/runtime/` bundle
   (the scripts, schemas, ontology, templates and locales the instance's
   own generated commands need) into the instance. The generated CLAUDE.md's
   commands reference `.eif/runtime/...`, so they run from the instance root
   even when the framework itself is not checked out. This is one distribution
   option ("local runtime bundle"), chosen for v0.1 because it makes a
   separate instance genuinely runnable and makes upgrade a re-run; it is not
   a ratification of D-08.

2. Real provenance. `.eif/config.yaml` records the *actual* framework git
   commit the bundle was generated from (resolved via `git rev-parse`), not a
   placeholder. Upgrade = re-run eif_init from a newer framework checkout;
   the recorded ref changes, the bundle refreshes.

3. Non-destructive by default. eif_init refuses to overwrite an existing
   `.eif/config.yaml` unless `--force` (which backs it up first). CLAUDE.md is
   updated by *merging* an EIF-managed marker block, never clobbering
   project-authored content. This is required for the later, safe migration of
   an existing repository (e.g. wm-engineering-intelligence) that already has
   its own CLAUDE.md and rules. `--dry-run` writes nothing and prints the plan.

4. Correct adapter entrypoint. The generated persistent-instruction file is
   CLAUDE.md, which Claude Code loads at session start (verified against the
   official docs and CLI 2.1.169) - not AGENTS.md.

Usage:
    python scripts/eif_init.py --framework-root PATH --instance-path PATH \\
        --project-name NAME [--locale en|uk] [--adapter claude-code] \\
        [--dry-run] [--force]
"""
from __future__ import annotations

import argparse
import datetime
import shutil
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    # Windows consoles default stdout to the active codepage (e.g. cp1252),
    # which cannot encode Cyrillic - and this script prints locale-aware
    # messages that may not be ASCII. Without this, a non-English locale
    # crashes on the first print() with UnicodeEncodeError.
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eif_locale import msg  # noqa: E402
from eif_validate_frontmatter import validate_config_mode  # noqa: E402
from eif_generate_index import build_index, render as render_index  # noqa: E402

EIF_BEGIN = "<!-- EIF:BEGIN"
EIF_END = "<!-- EIF:END -->"

# What goes into the pinned per-instance runtime bundle. Paths are relative to
# the framework root. Scripts the generated CLAUDE.md invokes, plus everything
# those scripts read (schemas, locales, templates) and the ontology the
# generated instructions link to.
BUNDLE_SCRIPTS = [
    "eif_locale.py",
    "eif_generate_index.py",
    "eif_search_knowledge.py",
    "eif_validate_frontmatter.py",
    "eif_render.py",
    "requirements.txt",
]
BUNDLE_TREES = [
    "core/schemas",
    "core/ontology",
    "locales",
    "templates",
]

CONFIG_TEMPLATE = """\
schema_version: 1

framework:
  version: {framework_version}
  # Real framework commit this instance was generated from - not a placeholder.
  # Upgrade = re-run eif_init from a newer framework checkout.
  ref: {framework_ref}
  ref_short: {framework_ref_short}
  bundle: .eif/runtime

instance:
  eif_instance_version: 0.1.0
  migration_status: {migration_status}

adapter:
  name: {adapter}
  entrypoint: CLAUDE.md

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


def resolve_framework_ref(framework_root: Path) -> tuple[str | None, str | None]:
    """Return (full_sha, short_sha) of the framework checkout, or (None, None)
    if it is not a git repo (caller then requires --framework-ref)."""
    try:
        full = subprocess.run(
            ["git", "-C", str(framework_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        short = subprocess.run(
            ["git", "-C", str(framework_root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return full, short
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None


def _backup(path: Path) -> Path:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = path.with_suffix(path.suffix + f".bak-{stamp}")
    shutil.copyfile(path, dest)
    return dest


def build_runtime_bundle(framework_root: Path, instance_path: Path, dry_run: bool) -> Path:
    """(Re)generate the self-contained .eif/runtime/ bundle. Always a full
    refresh - this is managed framework code, and refreshing it is exactly
    what 'upgrade' means."""
    runtime = instance_path / ".eif" / "runtime"
    if dry_run:
        return runtime
    if runtime.exists():
        shutil.rmtree(runtime)
    runtime.mkdir(parents=True, exist_ok=True)
    for script in BUNDLE_SCRIPTS:
        src = framework_root / "scripts" / script
        if src.exists():
            shutil.copyfile(src, runtime / src.name)
    for tree in BUNDLE_TREES:
        src = framework_root / tree
        if src.exists():
            shutil.copytree(src, runtime / tree, dirs_exist_ok=True)
    (runtime / "README.md").write_text(
        "# .eif/runtime (managed bundle)\n\n"
        "Pinned copy of the framework runtime this instance was generated "
        "from. Do not edit by hand - it is fully regenerated by `eif_init` on "
        "upgrade. The framework commit it corresponds to is recorded in "
        "`../config.yaml` `framework.ref`.\n",
        encoding="utf-8",
    )
    return runtime


def render_config(framework_ref: str, framework_ref_short: str, project_name: str,
                  locale: str, adapter: str, migration_status: str, framework_version: str) -> str:
    return CONFIG_TEMPLATE.format(
        framework_version=framework_version,
        framework_ref=framework_ref,
        framework_ref_short=framework_ref_short,
        project_name=project_name,
        locale=locale,
        adapter=adapter,
        migration_status=migration_status,
    )


def write_config(instance_path: Path, content: str, dry_run: bool, force: bool) -> tuple[str, Path]:
    """Return (action, path). action in {create, overwrite, conflict, dry-run}."""
    eif_dir = instance_path / ".eif"
    config_path = eif_dir / "config.yaml"
    if config_path.exists():
        if not force:
            return "conflict", config_path
        if not dry_run:
            _backup(config_path)
        action = "overwrite"
    else:
        action = "create"
    if not dry_run:
        eif_dir.mkdir(parents=True, exist_ok=True)
        config_path.write_text(content, encoding="utf-8")
    return action, config_path


def _managed_block(framework_root: Path) -> str:
    template = (framework_root / "templates" / "agent-instructions.md").read_text(encoding="utf-8")
    begin = template.index(EIF_BEGIN)
    end = template.index(EIF_END) + len(EIF_END)
    return template[begin:end]


def merge_entrypoint(framework_root: Path, instance_path: Path, dry_run: bool) -> tuple[str, Path]:
    """Insert/replace the EIF-managed marker block in CLAUDE.md without ever
    destroying project-authored content. Return (action, path)."""
    block = _managed_block(framework_root)
    target = instance_path / "CLAUDE.md"
    if not target.exists():
        action = "create"
        new_text = block + "\n\n# Project-specific rules\n\n<Add this project instance's own rules here.>\n"
    else:
        existing = target.read_text(encoding="utf-8")
        if EIF_BEGIN in existing and EIF_END in existing:
            action = "update-block"
            head = existing[: existing.index(EIF_BEGIN)]
            tail = existing[existing.index(EIF_END) + len(EIF_END):]
            new_text = head + block + tail
        else:
            action = "append-block"
            new_text = existing.rstrip() + "\n\n" + block + "\n"
    if not dry_run:
        target.write_text(new_text, encoding="utf-8")
    return action, target


def generate_index(instance_path: Path, dry_run: bool) -> tuple[Path, int]:
    knowledge_root = instance_path / "knowledge"
    if not knowledge_root.is_dir():
        return knowledge_root, 0
    rows, malformed = build_index(knowledge_root)
    if not dry_run:
        (knowledge_root / "index.md").write_text(render_index(rows, malformed, knowledge_root), encoding="utf-8")
    return knowledge_root / "index.md", len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--framework-root", required=True, help="This framework's checkout (source of the runtime bundle)")
    ap.add_argument("--instance-path", required=True, help="Where to create/adopt the project instance")
    ap.add_argument("--project-name", required=True)
    ap.add_argument("--locale", default="en")
    ap.add_argument("--adapter", default="claude-code", help="Adapter whose entrypoint to generate (default: claude-code -> CLAUDE.md)")
    ap.add_argument("--framework-version", default="0.1.0-dev")
    ap.add_argument("--framework-ref", default=None, help="Override the resolved framework commit (used when framework-root is not a git checkout)")
    ap.add_argument("--migration-status", default="greenfield", choices=["greenfield", "adopted"], help="greenfield = new repo; adopted = pre-existing repo being brought under EIF")
    ap.add_argument("--dry-run", action="store_true", help="Print the plan and write nothing")
    ap.add_argument("--force", action="store_true", help="Overwrite an existing .eif/config.yaml (backed up first)")
    args = ap.parse_args()

    framework_root = Path(args.framework_root).resolve()
    instance_path = Path(args.instance_path).resolve()

    ref, ref_short = resolve_framework_ref(framework_root)
    if args.framework_ref:
        ref, ref_short = args.framework_ref, args.framework_ref[:12]
    if not ref:
        print(
            "eif-init: could not resolve the framework commit (framework-root is "
            "not a git checkout). Pass --framework-ref <sha> explicitly - a real "
            "instance must record a real framework ref, not a placeholder.",
            file=sys.stderr,
        )
        return 1

    prefix = "[dry-run] would " if args.dry_run else ""
    print(msg(framework_root, args.locale, "init_start", path=instance_path))

    if not args.dry_run:
        instance_path.mkdir(parents=True, exist_ok=True)

    content = render_config(ref, ref_short, args.project_name, args.locale, args.adapter, args.migration_status, args.framework_version)
    action, config_path = write_config(instance_path, content, args.dry_run, args.force)
    if action == "conflict":
        print(
            f"eif-init: {config_path} already exists. Refusing to overwrite it. "
            f"Re-run with --force to back it up and replace it, or --dry-run to "
            f"preview. (This guard exists so adopting an existing repo never "
            f"silently discards its config.)",
            file=sys.stderr,
        )
        return 1
    print(f"{prefix}{action} .eif/config.yaml (framework.ref {ref_short})")

    # Validate the config we just rendered (skip file read on dry-run - validate
    # the in-memory content by writing to a temp path is overkill; instead
    # validate the real file when not dry-run).
    if not args.dry_run:
        rc = validate_config_mode(framework_root, config_path)
        if rc != 0:
            print(f"eif-init: generated config failed validation: {config_path}", file=sys.stderr)
            return rc
    if not args.dry_run:
        print(msg(framework_root, args.locale, "config_created", locale=args.locale))

    runtime = build_runtime_bundle(framework_root, instance_path, args.dry_run)
    print(f"{prefix}refresh {runtime.relative_to(instance_path) if not args.dry_run else '.eif/runtime'} (pinned bundle)")

    entry_action, entry_path = merge_entrypoint(framework_root, instance_path, args.dry_run)
    print(f"{prefix}{entry_action} CLAUDE.md (EIF-managed block)")
    if not args.dry_run:
        print(msg(framework_root, args.locale, "instructions_generated", path=entry_path))

    index_path, count = generate_index(instance_path, args.dry_run)
    if (instance_path / "knowledge").is_dir() and not args.dry_run:
        print(msg(framework_root, args.locale, "index_generated", count=count))

    print(msg(framework_root, args.locale, "init_complete", path=instance_path))
    if args.dry_run:
        print("[dry-run] no files were written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
