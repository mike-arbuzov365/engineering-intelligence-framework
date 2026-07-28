#!/usr/bin/env python3
"""Profile resolution, policy mode and override checks."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engineering_intelligence_framework import cli  # noqa: E402
from engineering_intelligence_framework.commands import init_cmd  # noqa: E402
from engineering_intelligence_framework.workspace_materialization import (  # noqa: E402
    WorkspaceMaterializationError,
    materialize_workspace,
    resolve_workspace,
    verify_workspace_materialization,
)
from workspace_test_support import commit_all, git, write_profile  # noqa: E402


def check(name: str, condition: bool, detail: str = "") -> tuple[bool, str]:
    return (
        condition,
        f"{'PASS' if condition else 'FAIL'} {name}"
        + (f": {detail}" if detail and not condition else ""),
    )


def expect_resolution_failure(
    workspace: Path,
    project: Path,
    *,
    required_exceptions: list[dict] | None = None,
    version: str = "0.2.0",
) -> str:
    try:
        resolve_workspace(
            workspace,
            project,
            profile_name="default",
            required_exceptions=required_exceptions,
            framework_version=version,
        )
    except WorkspaceMaterializationError as exc:
        return str(exc)
    return ""


def main() -> int:
    results: list[tuple[bool, str]] = []
    real_init_run = init_cmd.run
    init_cmd.run = lambda argv: real_init_run(  # type: ignore[assignment]
        [*argv, "--allow-dirty"]
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workspace = root / "workspace"
        project = root / "project"
        results.append(
            check(
                "workspace fixture creation succeeds",
                cli.main(["workspace", "new", str(workspace)]) == 0,
            )
        )
        results.append(
            check(
                "project fixture creation succeeds",
                cli.main(
                    [
                        "new",
                        str(project),
                        "--project-name",
                        "project",
                        "--adapter",
                        "codex",
                    ]
                )
                == 0,
            )
        )

        (workspace / "workspace" / "rules").mkdir(parents=True)
        (workspace / "workspace" / "rules" / "safety.md").write_text(
            "# Safety\n\nRequire evidence.\n",
            encoding="utf-8",
        )
        skill = workspace / "workspace" / "skills" / "planning"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# Planning skill\n", encoding="utf-8")
        (skill / "reference.md").write_text("# Reference\n", encoding="utf-8")
        (workspace / "workspace" / "templates").mkdir(parents=True)
        (workspace / "workspace" / "templates" / "brief.md").write_text(
            "# Brief\n",
            encoding="utf-8",
        )
        artifacts = [
            {
                "kind": "rule",
                "name": "safety",
                "path": "rules/safety.md",
                "mode": "required",
            },
            {
                "kind": "skill",
                "name": "planning",
                "path": "skills/planning",
                "mode": "default",
            },
            {
                "kind": "template",
                "name": "brief",
                "path": "templates/brief.md",
                "mode": "optional",
            },
        ]
        write_profile(workspace, artifacts)
        commit_all(workspace, "workspace policy")
        commit_all(project, "project bootstrap")

        plan = resolve_workspace(
            workspace,
            project,
            profile_name="default",
            framework_version="0.2.0",
        )
        manifest_paths = [entry["path"] for _, entry in plan["files"]]
        results.append(
            check(
                "selected profile resolves all three policy modes",
                {item["mode"] for item in plan["artifacts"]}
                == {"required", "default", "optional"},
            )
        )
        results.append(
            check(
                "directory artifact resolves deterministic per-file entries",
                manifest_paths
                == sorted(
                    [
                        "rules/safety.md",
                        "skills/planning/SKILL.md",
                        "skills/planning/reference.md",
                        "templates/brief.md",
                    ]
                ),
                str(manifest_paths),
            )
        )
        incompatible = expect_resolution_failure(
            workspace,
            project,
            version="0.1.9",
        )
        results.append(
            check(
                "incompatible EIF version fails before a write",
                "requires EIF" in incompatible,
                incompatible,
            )
        )

        source_rule = workspace / "workspace" / "rules" / "safety.md"
        source_before = source_rule.read_bytes()
        source_rule.write_text("# Dirty workspace policy\n", encoding="utf-8")
        dirty = expect_resolution_failure(workspace, project)
        results.append(
            check(
                "dirty workspace source is refused",
                "workspace working tree is dirty" in dirty,
                dirty,
            )
        )
        source_rule.write_bytes(source_before)
        git(workspace, "restore", "workspace/rules/safety.md")

        local_skill = project / "skills" / "planning"
        local_skill.mkdir(parents=True)
        local_skill_file = local_skill / "SKILL.md"
        local_skill_file.write_text("# Project planning\n", encoding="utf-8")
        undeclared = expect_resolution_failure(workspace, project)
        results.append(
            check(
                "undeclared same-name collision fails",
                "undeclared same-name collision: skill/planning" in undeclared,
                undeclared,
            )
        )

        overrides_path = project / ".eif" / "workspace-overrides.yaml"
        bad_overrides = {
            "schema_version": 1,
            "overrides": [
                {
                    "kind": "skill",
                    "name": "planning",
                    "override_of": "workspace://skill/other",
                    "reason": "Project specialization.",
                    "approved_by": "project-owner",
                }
            ],
        }
        overrides_path.write_text(
            yaml.safe_dump(bad_overrides, sort_keys=False),
            encoding="utf-8",
        )
        malformed = expect_resolution_failure(workspace, project)
        results.append(
            check(
                "mismatched override_of fails",
                "override_of must be" in malformed,
                malformed,
            )
        )

        overrides = bad_overrides
        overrides["overrides"][0]["override_of"] = (
            "workspace://skill/planning"
        )
        overrides_path.write_text(
            yaml.safe_dump(overrides, sort_keys=False),
            encoding="utf-8",
        )
        results.append(
            check(
                "valid default override resolves",
                not expect_resolution_failure(workspace, project),
            )
        )

        local_rules = project / "rules"
        local_rules.mkdir()
        local_rule = local_rules / "safety.md"
        local_rule.write_text("# Stricter project safety\n", encoding="utf-8")
        overrides["overrides"].append(
            {
                "kind": "rule",
                "name": "safety",
                "override_of": "workspace://rule/safety",
                "reason": "Project safeguard is stricter.",
                "approved_by": "project-owner",
            }
        )
        overrides_path.write_text(
            yaml.safe_dump(overrides, sort_keys=False),
            encoding="utf-8",
        )
        missing_exception = expect_resolution_failure(workspace, project)
        results.append(
            check(
                "required override also needs registry exception",
                "approved registry exception" in missing_exception,
                missing_exception,
            )
        )
        exceptions = [
            {
                "artifact": "rule/safety",
                "reason": "Project safeguard is stricter.",
                "approved_by": "workspace-owner",
            }
        ]
        results.append(
            check(
                "required override resolves with explicit exception",
                not expect_resolution_failure(
                    workspace,
                    project,
                    required_exceptions=exceptions,
                ),
            )
        )

        commit_all(project, "project overrides")
        project_owned_before = {
            "skill": local_skill_file.read_bytes(),
            "rule": local_rule.read_bytes(),
        }
        materialize_workspace(
            workspace,
            project,
            profile_name="default",
            required_exceptions=exceptions,
            framework_version="0.2.0",
        )
        results.append(
            check(
                "materialization preserves project-owned artifacts byte-for-byte",
                local_skill_file.read_bytes() == project_owned_before["skill"]
                and local_rule.read_bytes() == project_owned_before["rule"],
            )
        )
        lock_path = project / ".eif" / "workspace.lock.yaml"
        lock_text = lock_path.read_text(encoding="utf-8")
        results.append(
            check(
                "workspace lock contains no machine path or credential",
                str(workspace) not in lock_text
                and str(project) not in lock_text
                and "credential" not in lock_text.casefold(),
            )
        )
        results.append(
            check(
                "fresh materialization verifies and project doctor passes",
                verify_workspace_materialization(project) == []
                and cli.main(
                    ["doctor", "--instance-path", str(project)]
                )
                == 0,
            )
        )

        runtime_rule = (
            project / ".eif" / "workspace-runtime" / "rules" / "safety.md"
        )
        snapshot_before = runtime_rule.read_bytes()
        source_rule.write_text("# Uncommitted live change\n", encoding="utf-8")
        results.append(
            check(
                "project reads pinned snapshot rather than dirty live workspace",
                runtime_rule.read_bytes() == snapshot_before
                and verify_workspace_materialization(project) == [],
            )
        )
        refused_live = expect_resolution_failure(
            workspace,
            project,
            required_exceptions=exceptions,
        )
        results.append(
            check(
                "dirty live workspace cannot refresh the snapshot",
                "workspace working tree is dirty" in refused_live,
                refused_live,
            )
        )
        source_rule.write_bytes(source_before)
        git(workspace, "restore", "workspace/rules/safety.md")

        local_skill_file.unlink()
        local_skill.rmdir()
        stale = verify_workspace_materialization(project)
        results.append(
            check(
                "doctor detects an override whose project artifact disappeared",
                any("stale override" in problem for problem in stale),
                str(stale),
            )
        )

    passed = sum(1 for ok, _ in results if ok)
    for _, line in results:
        print(line)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_workspace_resolution: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
