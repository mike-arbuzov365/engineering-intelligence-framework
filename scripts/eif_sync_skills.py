#!/usr/bin/env python3
"""Generate agent-visible skill loaders from the pinned runtime skill set.

The gap this closes
-------------------
EIF ships eleven skills. `adapters/claude-code/README.md` records, as
OBSERVED evidence, that Claude Code discovers skills at
`.claude/skills/<name>/SKILL.md`. `eif_init.py` copies the framework's
`skills/` directory into `.eif/runtime/skills/` and stops there.

Nothing connected the two. A project instance therefore adopted eleven
skills and could invoke none of them, unless someone noticed and hand-wrote
a loader per skill. Found in a real adoption (preo-web, 2026-08-02) where
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
Loaders are generated, never authored. Each one is a pointer to the pinned
runtime skill, so there is still one canonical source per workflow (D-007).
A project that wants different behaviour overrides the skill in its own
canonical directory; this script refuses to overwrite anything it did not
generate, which is what makes an override survive the next upgrade.
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
file on every sync. To change how this skill behaves in this project,
create `{canonical_dir}/{name}/SKILL.md` - the sync then treats this skill
as project-owned and stops generating over it.

Read and follow, in order:

1. `{runtime_dir}/skills/{name}/SKILL.md`
2. The playbook that skill points to, under `{runtime_dir}/playbooks/`.

Both are pinned to this project's EIF version. Read them rather than
recalling them: the pinned copy is authoritative, chat memory is not.
"""


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
        manifest = entry / "SKILL.md"
        if not entry.is_dir() or not manifest.is_file():
            continue

        text = manifest.read_text(encoding="utf-8")
        name = _frontmatter_field(text, "name") or entry.name
        description = _frontmatter_field(text, "description") or (
            f"EIF skill {entry.name}."
        )
        found.append((name, description))

    return found


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
    canonical_subdir: str = "docs/skills",
    check_only: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    """Generate loaders. Returns (written, skipped_project_owned, removed)."""
    target_rel = ADAPTER_SKILL_DIRS.get(adapter)
    if target_rel is None:
        raise ValueError(
            f"Unknown adapter '{adapter}'. Known: {', '.join(sorted(ADAPTER_SKILL_DIRS))}"
        )

    runtime_dir = instance_path / ".eif" / "runtime"
    target_dir = instance_path / target_rel
    canonical_dir = instance_path / canonical_subdir

    written: list[str] = []
    skipped: list[str] = []
    removed: list[str] = []

    for name, description in discover_runtime_skills(runtime_dir):
        # A project-owned skill of the same name always wins. This is the
        # override path, and it has to be checked before anything is written.
        if (canonical_dir / name / "SKILL.md").is_file():
            skipped.append(name)
            continue

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
            runtime_dir=".eif/runtime",
            canonical_dir=canonical_subdir,
        )

        if destination.is_file() and destination.read_text(encoding="utf-8") == content:
            continue

        if check_only:
            written.append(name)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")
        written.append(name)

    return written, skipped, removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate agent-visible loaders for pinned EIF skills."
    )
    parser.add_argument("--instance-path", default=".", type=Path)
    parser.add_argument("--adapter", default="claude-code")
    parser.add_argument("--canonical-subdir", default="docs/skills")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report what would change and exit non-zero if anything would.",
    )
    args = parser.parse_args(argv)

    try:
        written, skipped, _ = sync(
            args.instance_path.resolve(),
            args.adapter,
            args.canonical_subdir,
            check_only=args.check,
        )
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    for name in written:
        print(f"{'would generate' if args.check else 'generated'}: {name}")
    for name in skipped:
        print(f"project-owned, left alone: {name}")

    if args.check and written:
        print(
            "\nSkill loaders are out of date. Run without --check to regenerate.",
            file=sys.stderr,
        )
        return 1

    if not written and not skipped:
        print("no skills found in .eif/runtime/skills")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
