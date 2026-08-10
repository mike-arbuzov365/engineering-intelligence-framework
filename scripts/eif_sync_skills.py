#!/usr/bin/env python3
"""Generate agent-visible skill loaders from the pinned runtime skill set.

The gap this closes
-------------------
На момент виявлення gap EIF постачав одинадцять skills.
`adapters/claude-code/README.md` records, as
OBSERVED evidence, that Claude Code discovers skills at
`.claude/skills/<name>/SKILL.md`. `eif_init.py` copies the framework's
`skills/` directory into `.eif/runtime/skills/` and stops there.

Nothing connected the two. A project instance therefore adopted eleven
skills and could invoke none of them, unless someone noticed and hand-wrote
a loader per skill. Found in a real private adoption (2026-08-02) where
exactly one of eleven had been written by hand, and the missing
`run-execution-packet` meant packets were executed without the playbook that
forbids stopping between sessions. Two other symptoms in the same instance -
no retro ever run, the knowledge base never fed - trace to the same cause:
`run-retro`, `knowledge-ingest` and `knowledge-curator` were equally
invisible.

The failure mode is quiet by construction. A missing skill produces no
error; the agent simply never learns the workflow exists, and the project
looks like it chose not to use it.

Design
------
Loaders are generated, never authored. Each one points to the selected
canonical skill source, so there is still one source per workflow (D-007).
Selection is deliberately narrow and deterministic:

1. a project-owned skill;
2. a skill selected by the pinned private-workspace profile;
3. the public EIF runtime skill.

A hand-authored file in the adapter's own skill directory still wins over a
generated loader. That file is already agent-visible and may encode an
adapter-specific override this script must not replace.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Marker that identifies a file this script owns. A loader without it is
# treated as hand-authored and left alone: silently replacing a project's own
# override would be a worse bug than the one this script fixes.
GENERATED_MARKER = "<!-- eif:generated-skill-loader -->"

# Where each adapter's agent looks for skills, per adapters/<name>/README.md.
ADAPTER_SKILL_DIRS: dict[str, str] = {
    "claude-code": ".claude/skills",
    "codex": ".agents/skills",
    "cursor": ".cursor/skills",
    "hermes": ".hermes/skills",
}

LOADER_TEMPLATE = """---
name: {name}
description: >
{description}
---

{marker}

# Skill: {name}

Generated loader. Do not edit: `scripts/eif_sync_skills.py` rewrites this
file on every sync. The selected source for this project is:

`{source_manifest}`

Read and follow that file. Then read only the playbooks, references or assets
it explicitly points to. The selected source is pinned or project-owned;
chat memory is not authoritative.

To override it for this project, create `{canonical_dir}/{name}/SKILL.md`
and run the sync again. The generated loader will then point to that file.
"""


def _skill_manifest(path: Path) -> tuple[str, str] | None:
    """Return (name, description) for one skill directory."""
    manifest = path / "SKILL.md"
    if not path.is_dir() or not manifest.is_file():
        return None
    text = manifest.read_text(encoding="utf-8")
    name = _frontmatter_field(text, "name") or path.name
    description = _frontmatter_field(text, "description") or f"EIF skill {path.name}."
    return name, description


def _frontmatter_field(text: str, field: str) -> str | None:
    """Read one scalar or folded field from a SKILL.md frontmatter block."""
    if not text.startswith("---"):
        return None

    end = text.find("\n---", 3)
    if end == -1:
        return None

    block = text[3:end]
    lines = block.splitlines()

    for index, line in enumerate(lines):
        if not line.startswith(f"{field}:"):
            continue

        value = line[len(field) + 1 :].strip()
        if value and value not in {">", "|", ">-", "|-"}:
            return value

        # Folded scalar: take the indented continuation lines.
        collected: list[str] = []
        for continuation in lines[index + 1 :]:
            if continuation.strip() and not continuation.startswith((" ", "\t")):
                break
            if continuation.strip():
                collected.append(continuation.strip())
        return " ".join(collected) if collected else None

    return None


def discover_runtime_skills(runtime_dir: Path) -> list[tuple[str, str]]:
    """Return (name, description) for every skill in the pinned runtime."""
    skills_dir = runtime_dir / "skills"
    if not skills_dir.is_dir():
        return []

    found: list[tuple[str, str]] = []
    for entry in sorted(skills_dir.iterdir()):
        discovered = _skill_manifest(entry)
        if discovered is None:
            continue
        found.append(discovered)

    return found


def discover_selected_skills(
    instance_path: Path,
    canonical_subdir: str = "skills",
) -> list[tuple[str, str, str]]:
    """Resolve the agent-visible skill set and its selected source paths.

    Later sources replace earlier ones. This makes the precedence public EIF
    < pinned workspace < project explicit without copying any skill body.
    `docs/skills` remains a compatibility source for instances that used the
    first, pre-workspace convention; the canonical project path is `skills`.
    """
    selected: dict[str, tuple[str, str]] = {}

    def add_from(root: Path) -> None:
        if not root.is_dir():
            return
        for entry in sorted(root.iterdir()):
            discovered = _skill_manifest(entry)
            if discovered is None:
                continue
            name, description = discovered
            source_manifest = (entry / "SKILL.md").relative_to(instance_path).as_posix()
            selected[name] = (description, source_manifest)

    add_from(instance_path / ".eif" / "runtime" / "skills")
    add_from(instance_path / ".eif" / "workspace-runtime" / "skills")

    project_roots = ["docs/skills", canonical_subdir]
    seen_roots: set[str] = set()
    for rel in project_roots:
        normalized = Path(rel).as_posix().strip("/")
        if not normalized or normalized in seen_roots:
            continue
        seen_roots.add(normalized)
        add_from(instance_path / normalized)

    return [
        (name, description, source_manifest)
        for name, (description, source_manifest) in sorted(selected.items())
    ]


def _wrap(description: str, indent: str = "  ", width: int = 72) -> str:
    """Fold a description into the frontmatter block."""
    words = description.split()
    lines: list[str] = []
    current = indent

    for word in words:
        if len(current) + len(word) + 1 > width and current.strip():
            lines.append(current.rstrip())
            current = indent
        current += word + " "

    if current.strip():
        lines.append(current.rstrip())

    return "\n".join(lines)


def sync(
    instance_path: Path,
    adapter: str,
    canonical_subdir: str = "skills",
    check_only: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    """Generate loaders. Returns (written, preserved_hand_authored, removed)."""
    target_rel = ADAPTER_SKILL_DIRS.get(adapter)
    if target_rel is None:
        raise ValueError(
            f"Unknown adapter '{adapter}'. Known: {', '.join(sorted(ADAPTER_SKILL_DIRS))}"
        )

    target_dir = instance_path / target_rel

    written: list[str] = []
    skipped: list[str] = []
    removed: list[str] = []
    selected = discover_selected_skills(instance_path, canonical_subdir)
    desired_names = {name for name, _, _ in selected}

    for name, description, source_manifest in selected:
        destination = target_dir / name / "SKILL.md"

        if destination.is_file():
            existing = destination.read_text(encoding="utf-8")
            if GENERATED_MARKER not in existing:
                # Hand-authored. Leave it: whoever wrote it knew something
                # this script does not.
                skipped.append(name)
                continue

        content = LOADER_TEMPLATE.format(
            name=name,
            description=_wrap(description),
            marker=GENERATED_MARKER,
            canonical_dir=canonical_subdir,
            source_manifest=source_manifest,
        )

        if destination.is_file() and destination.read_text(encoding="utf-8") == content:
            continue

        if check_only:
            written.append(name)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")
        written.append(name)

    # Remove only stale files that carry our ownership marker. A removed or
    # deselected skill must not remain discoverable forever, while a
    # hand-authored skill in the same adapter directory is never ours to
    # delete.
    if target_dir.is_dir():
        for manifest in sorted(target_dir.glob("*/SKILL.md")):
            name = manifest.parent.name
            if name in desired_names:
                continue
            existing = manifest.read_text(encoding="utf-8")
            if GENERATED_MARKER not in existing:
                continue
            removed.append(name)
            if check_only:
                continue
            manifest.unlink()
            try:
                manifest.parent.rmdir()
            except OSError:
                pass

    return written, skipped, removed


def remove_generated_loaders(
    instance_path: Path,
    adapter: str,
    *,
    check_only: bool = False,
) -> list[str]:
    """Remove only EIF-owned loaders before a manual EIF uninstall."""
    target_rel = ADAPTER_SKILL_DIRS.get(adapter)
    if target_rel is None:
        raise ValueError(
            f"Unknown adapter '{adapter}'. Known: {', '.join(sorted(ADAPTER_SKILL_DIRS))}"
        )
    target_dir = instance_path / target_rel
    removed: list[str] = []
    if not target_dir.is_dir():
        return removed
    for manifest in sorted(target_dir.glob("*/SKILL.md")):
        if GENERATED_MARKER not in manifest.read_text(encoding="utf-8"):
            continue
        removed.append(manifest.parent.name)
        if check_only:
            continue
        manifest.unlink()
        try:
            manifest.parent.rmdir()
        except OSError:
            pass
    return removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate agent-visible loaders for pinned EIF skills."
    )
    parser.add_argument("--instance-path", default=".", type=Path)
    parser.add_argument("--adapter", default="claude-code")
    parser.add_argument("--canonical-subdir", default="skills")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report what would change and exit non-zero if anything would.",
    )
    parser.add_argument(
        "--remove-generated",
        action="store_true",
        help=(
            "Remove only EIF-generated loaders from the active adapter "
            "directory before manually deleting .eif/."
        ),
    )
    args = parser.parse_args(argv)

    try:
        if args.remove_generated:
            written, skipped = [], []
            removed = remove_generated_loaders(
                args.instance_path.resolve(),
                args.adapter,
                check_only=args.check,
            )
        else:
            written, skipped, removed = sync(
                args.instance_path.resolve(),
                args.adapter,
                args.canonical_subdir,
                check_only=args.check,
            )
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    for name in written:
        print(f"{'would generate' if args.check else 'generated'}: {name}")
    for name in skipped:
        print(f"project-owned, left alone: {name}")
    for name in removed:
        print(f"{'would remove' if args.check else 'removed'} stale loader: {name}")

    if args.check and (written or removed):
        print(
            "\nSkill loaders are out of date. Run without --check to regenerate.",
            file=sys.stderr,
        )
        return 1

    if not written and not skipped and not removed:
        print("no selected skills found")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
