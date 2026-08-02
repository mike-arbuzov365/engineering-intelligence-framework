#!/usr/bin/env python3
"""Tests for scripts/eif_sync_skills.py: the bridge from the pinned runtime
skill set to where each agent actually looks for skills.

The bug being guarded against is silent. A skill that never reaches the
agent raises nothing; the agent simply never learns the workflow exists.
So every check here asserts on a file that must or must not be there, and
on who owns it.

Usage:
    python scripts/tests/test_sync_skills.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eif_sync_skills import (  # noqa: E402
    GENERATED_MARKER,
    discover_runtime_skills,
    discover_selected_skills,
    remove_generated_loaders,
    sync,
)


def check(name: str, cond: bool, detail: str = "") -> bool:
    status = "PASS" if cond else "FAIL"
    print(f"{status} {name}" + (f": {detail}" if detail and not cond else ""))
    return cond


def runtime_skill(instance: Path, name: str, description: str = "Does a thing.") -> None:
    skill_dir = instance / ".eif" / "runtime" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: >\n  {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )


def main() -> int:  # noqa: PLR0915
    results: list[bool] = []

    # --- Every runtime skill becomes invocable. This is the actual bug:
    # eleven skills shipped, none reachable. ---
    with tempfile.TemporaryDirectory() as td:
        instance = Path(td)
        for name in ("plan-idea", "run-execution-packet", "run-retro"):
            runtime_skill(instance, name)

        written, skipped, _ = sync(instance, "claude-code")
        results.append(
            check(
                "every runtime skill becomes invocable",
                sorted(written) == ["plan-idea", "run-execution-packet", "run-retro"]
                and skipped == []
                and all(
                    (instance / ".claude" / "skills" / n / "SKILL.md").is_file()
                    for n in written
                ),
                f"written={written} skipped={skipped}",
            )
        )

    # --- A project-owned skill becomes the selected source. The adapter still
    # needs a loader: merely skipping the framework loader leaves a canonical
    # project skill just as invisible as the original runtime-only bug. ---
    with tempfile.TemporaryDirectory() as td:
        instance = Path(td)
        runtime_skill(instance, "plan-execution-packet")
        canonical = instance / "skills" / "plan-execution-packet"
        canonical.mkdir(parents=True)
        (canonical / "SKILL.md").write_text(
            "---\nname: plan-execution-packet\ndescription: Project planning.\n---\n",
            encoding="utf-8",
        )

        written, skipped, _ = sync(instance, "claude-code")
        loader = instance / ".claude" / "skills" / "plan-execution-packet" / "SKILL.md"
        results.append(
            check(
                "project-owned skill wins and remains agent-visible through a loader",
                written == ["plan-execution-packet"]
                and skipped == []
                and "skills/plan-execution-packet/SKILL.md" in loader.read_text(encoding="utf-8"),
                f"written={written} skipped={skipped} loader={loader.read_text(encoding='utf-8')}",
            )
        )

    # --- A workspace profile may specialize the public skill set without
    # copying it into each project. Project scope still wins over workspace. ---
    with tempfile.TemporaryDirectory() as td:
        instance = Path(td)
        runtime_skill(instance, "design-review", "Framework review.")
        workspace = instance / ".eif" / "workspace-runtime" / "skills" / "design-review"
        workspace.mkdir(parents=True)
        (workspace / "SKILL.md").write_text(
            "---\nname: design-review\ndescription: Workspace design review.\n---\n",
            encoding="utf-8",
        )
        selected = discover_selected_skills(instance)
        sync(instance, "codex")
        loader = instance / ".agents" / "skills" / "design-review" / "SKILL.md"
        results.append(
            check(
                "pinned workspace skill replaces the public skill and is discoverable",
                selected == [
                    (
                        "design-review",
                        "Workspace design review.",
                        ".eif/workspace-runtime/skills/design-review/SKILL.md",
                    )
                ]
                and ".eif/workspace-runtime/skills/design-review/SKILL.md"
                in loader.read_text(encoding="utf-8"),
                f"selected={selected}",
            )
        )

    # --- A hand-written loader predating this script is left alone. ---
    with tempfile.TemporaryDirectory() as td:
        instance = Path(td)
        runtime_skill(instance, "knowledge-search")
        loader_dir = instance / ".claude" / "skills" / "knowledge-search"
        loader_dir.mkdir(parents=True)
        (loader_dir / "SKILL.md").write_text("hand written", encoding="utf-8")

        written, skipped, _ = sync(instance, "claude-code")
        results.append(
            check(
                "hand-written loader is not replaced",
                written == []
                and skipped == ["knowledge-search"]
                and (loader_dir / "SKILL.md").read_text(encoding="utf-8") == "hand written",
                f"written={written} skipped={skipped}",
            )
        )

    # --- But our own generated loader may be refreshed, or loaders rot
    # against the runtime they point at. ---
    with tempfile.TemporaryDirectory() as td:
        instance = Path(td)
        runtime_skill(instance, "run-retro")
        sync(instance, "claude-code")
        loader = instance / ".claude" / "skills" / "run-retro" / "SKILL.md"
        had_marker = GENERATED_MARKER in loader.read_text(encoding="utf-8")

        loader.write_text(
            f"---\nname: run-retro\ndescription: stale\n---\n{GENERATED_MARKER}\nold",
            encoding="utf-8",
        )
        written, _, _ = sync(instance, "claude-code")
        results.append(
            check(
                "generated loader is refreshed on upgrade",
                had_marker
                and written == ["run-retro"]
                and "stale" not in loader.read_text(encoding="utf-8"),
                f"written={written}",
            )
        )

    # --- Idempotent: a second sync must not churn files. ---
    with tempfile.TemporaryDirectory() as td:
        instance = Path(td)
        runtime_skill(instance, "plan-prd")
        sync(instance, "claude-code")
        written, _, _ = sync(instance, "claude-code")
        results.append(
            check("sync is idempotent", written == [], f"written={written}")
        )

    # --- Check mode reports without writing. ---
    with tempfile.TemporaryDirectory() as td:
        instance = Path(td)
        runtime_skill(instance, "knowledge-lint")
        written, _, _ = sync(instance, "claude-code", check_only=True)
        results.append(
            check(
                "check mode reports without writing",
                written == ["knowledge-lint"]
                and not (instance / ".claude" / "skills" / "knowledge-lint").exists(),
                f"written={written}",
            )
        )

    # --- A deselected generated loader must not stay callable forever. ---
    with tempfile.TemporaryDirectory() as td:
        instance = Path(td)
        runtime_skill(instance, "obsolete")
        sync(instance, "claude-code")
        runtime_manifest = instance / ".eif" / "runtime" / "skills" / "obsolete" / "SKILL.md"
        runtime_manifest.unlink()
        runtime_manifest.parent.rmdir()
        written, skipped, removed = sync(instance, "claude-code")
        results.append(
            check(
                "generated loader is removed when its selected source disappears",
                written == []
                and skipped == []
                and removed == ["obsolete"]
                and not (instance / ".claude" / "skills" / "obsolete").exists(),
                f"written={written} skipped={skipped} removed={removed}",
            )
        )

    # --- Manual uninstall removes only files carrying EIF's marker. ---
    with tempfile.TemporaryDirectory() as td:
        instance = Path(td)
        runtime_skill(instance, "run-retro")
        sync(instance, "claude-code")
        custom = instance / ".claude" / "skills" / "custom" / "SKILL.md"
        custom.parent.mkdir(parents=True)
        custom.write_text("hand written", encoding="utf-8")
        removed = remove_generated_loaders(instance, "claude-code")
        results.append(
            check(
                "manual uninstall removes generated loaders only",
                removed == ["run-retro"]
                and not (
                    instance / ".claude" / "skills" / "run-retro"
                ).exists()
                and custom.read_text(encoding="utf-8") == "hand written",
                f"removed={removed}",
            )
        )

    # --- Each adapter writes where its own README says its agent looks.
    # Getting one wrong reproduces the original bug for that agent alone,
    # which is harder to notice than reproducing it for all of them. ---
    with tempfile.TemporaryDirectory() as td:
        instance = Path(td)
        runtime_skill(instance, "plan-idea")
        ok = True
        for adapter, expected in (
            ("claude-code", ".claude/skills"),
            ("codex", ".agents/skills"),
            ("cursor", ".cursor/skills"),
            ("hermes", ".hermes/skills"),
        ):
            sync(instance, adapter)
            ok = ok and (instance / expected / "plan-idea" / "SKILL.md").is_file()
        results.append(check("each adapter writes where its agent looks", ok))

    # --- An unknown adapter fails loudly rather than doing nothing. ---
    with tempfile.TemporaryDirectory() as td:
        raised = False
        try:
            sync(Path(td), "not-an-adapter")
        except ValueError as error:
            raised = "not-an-adapter" in str(error)
        results.append(check("unknown adapter raises", raised))

    # --- The folded description survives. Losing it leaves the agent a name
    # with no idea when to use it, which is most of the value. ---
    with tempfile.TemporaryDirectory() as td:
        instance = Path(td)
        runtime_skill(
            instance, "run-execution-packet", "Execute a planned packet end to end."
        )
        discovered = dict(discover_runtime_skills(instance / ".eif" / "runtime"))
        sync(instance, "claude-code")
        loader_text = (
            instance / ".claude" / "skills" / "run-execution-packet" / "SKILL.md"
        ).read_text(encoding="utf-8")

        results.append(
            check(
                "folded description reaches the manifest",
                discovered.get("run-execution-packet")
                == "Execute a planned packet end to end."
                and "Execute a planned packet end to end." in loader_text,
                f"discovered={discovered}",
            )
        )

    # --- A project that has not run init yet must not crash here. ---
    with tempfile.TemporaryDirectory() as td:
        written, skipped, _ = sync(Path(td), "claude-code")
        results.append(
            check("missing runtime is a no-op", written == [] and skipped == [])
        )

    passed = sum(1 for r in results if r)
    print(f"\n{passed}/{len(results)} checks passed")
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
