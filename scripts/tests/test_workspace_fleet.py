#!/usr/bin/env python3
"""Multi-project workspace plan, apply, partial failure and detach checks."""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engineering_intelligence_framework import cli  # noqa: E402
from engineering_intelligence_framework.commands import init_cmd  # noqa: E402
from engineering_intelligence_framework.commands import projects as projects_cmd  # noqa: E402
from workspace_test_support import (  # noqa: E402
    commit_all,
    git,
    tree_bytes,
    write_profile,
)


def check(name: str, condition: bool, detail: str = "") -> tuple[bool, str]:
    return (
        condition,
        f"{'PASS' if condition else 'FAIL'} {name}"
        + (f": {detail}" if detail and not condition else ""),
    )


def capture_cli(argv: list[str]) -> tuple[int, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        rc = cli.main(argv)
    return rc, stdout.getvalue() + stderr.getvalue()


def commit_if_dirty(project: Path, message: str) -> bool:
    """A partial fleet result is only committable when an axis actually wrote
    something. Since 0.2.1 an axis that resolves to identical state writes
    nothing, so "review and commit the partial result" can legitimately find
    an already-clean tree."""
    if not git(project, "status", "--porcelain").stdout.strip():
        return False
    commit_all(project, message)
    return True


def workspace_revision(project: Path) -> str | None:
    lock_path = project / ".eif" / "workspace.lock.yaml"
    if not lock_path.exists():
        return None
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    return lock["workspace"]["revision"]


def main() -> int:
    results: list[tuple[bool, str]] = []
    real_init_run = init_cmd.run
    init_cmd.run = lambda argv: real_init_run(  # type: ignore[assignment]
        [*argv, "--allow-dirty"]
    )
    original_projects_version = projects_cmd.__version__
    projects_cmd.__version__ = "0.2.0"

    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            registry = workspace / ".eif" / "projects.yaml"
            locations = (
                workspace
                / ".eif"
                / "local-state"
                / "project-locations.yaml"
            )
            cli.main(["workspace", "new", str(workspace)])
            rules = workspace / "workspace" / "rules"
            rules.mkdir(parents=True)
            shared_rule = rules / "shared.md"
            shared_rule.write_text("# Shared v1\n", encoding="utf-8")
            write_profile(
                workspace,
                [
                    {
                        "kind": "rule",
                        "name": "shared",
                        "path": "rules/shared.md",
                        "mode": "default",
                    }
                ],
            )

            projects = [root / name for name in ("alpha", "beta", "gamma")]
            for project in projects:
                rc = cli.main(
                    [
                        "new",
                        str(project),
                        "--project-name",
                        project.name,
                        "--adapter",
                        "codex",
                        "--registry",
                        str(registry),
                    ]
                )
                results.append(
                    check(f"fixture connects {project.name}", rc == 0)
                )
                commit_all(project, f"bootstrap {project.name}")
            commit_all(workspace, "workspace fleet v1")

            before_plan = {project.name: tree_bytes(project) for project in projects}
            rc, plan_output = capture_cli(
                ["projects", "upgrade", "--registry", str(registry)]
            )
            results.append(
                check(
                    "fleet plan compares framework and workspace axes",
                    rc == 0
                    and "framework: current=" in plan_output
                    and "workspace: pinned=" in plan_output
                    and "target=" in plan_output
                    and "profile=default" in plan_output
                    # Each axis states whether it would change anything, so a
                    # plan is readable without diffing versions by eye.
                    and "change=yes" in plan_output,
                    plan_output,
                )
            )
            results.append(
                check(
                    "fleet plan writes no project",
                    all(
                        tree_bytes(project) == before_plan[project.name]
                        for project in projects
                    ),
                )
            )

            dirty_file = projects[1] / "OWNER-WORK.md"
            dirty_file.write_text("uncommitted owner work\n", encoding="utf-8")
            before_dirty_preflight = {
                project.name: tree_bytes(project) for project in projects
            }
            rc, output = capture_cli(
                [
                    "projects",
                    "upgrade",
                    "--registry",
                    str(registry),
                    "--apply",
                ]
            )
            results.append(
                check(
                    "dirty target blocks fleet before the first write",
                    rc != 0
                    and all(
                        tree_bytes(project)
                        == before_dirty_preflight[project.name]
                        for project in projects
                    ),
                    output,
                )
            )
            commit_all(projects[1], "owner work")

            rc, output = capture_cli(
                [
                    "projects",
                    "upgrade",
                    "--registry",
                    str(registry),
                    "--apply",
                ]
            )
            first_revision = git(workspace, "rev-parse", "HEAD").stdout.strip()
            results.append(
                check(
                    "fleet apply updates both axes after all preflights pass",
                    rc == 0
                    and all(
                        workspace_revision(project) == first_revision
                        for project in projects
                    ),
                    output,
                )
            )
            for project in projects:
                commit_all(project, "fleet workspace v1")

            shared_rule.write_text("# Shared v2\n", encoding="utf-8")
            commit_all(workspace, "workspace fleet v2")
            second_revision = git(workspace, "rev-parse", "HEAD").stdout.strip()
            old_revisions = {
                project.name: workspace_revision(project) for project in projects
            }

            real_materialize = projects_cmd.materialize_workspace

            def fail_beta(workspace_path, project_path, **kwargs):
                if (
                    Path(project_path).name == "beta"
                    and not kwargs.get("dry_run", False)
                ):
                    raise RuntimeError("synthetic beta workspace failure")
                return real_materialize(workspace_path, project_path, **kwargs)

            projects_cmd.materialize_workspace = fail_beta
            try:
                rc, output = capture_cli(
                    [
                        "projects",
                        "upgrade",
                        "--registry",
                        str(registry),
                        "--apply",
                    ]
                )
            finally:
                projects_cmd.materialize_workspace = real_materialize
            results.append(
                check(
                    "partial apply reports completed, failed axis and untouched set",
                    rc != 0
                    and "failed=beta axis=workspace after framework axis succeeded"
                    in output
                    and "completed=alpha" in output
                    and "untouched=gamma" in output,
                    output,
                )
            )
            results.append(
                check(
                    "partial apply updates alpha, leaves beta workspace old and gamma untouched",
                    workspace_revision(projects[0]) == second_revision
                    and workspace_revision(projects[1])
                    == old_revisions["beta"]
                    and workspace_revision(projects[2])
                    == old_revisions["gamma"],
                )
            )

            # Alpha has both axes updated and beta has its framework axis
            # updated. Commit those explicit partial results before retrying.
            commit_if_dirty(projects[0], "partial alpha")
            commit_if_dirty(projects[1], "partial beta framework")
            rc, output = capture_cli(
                [
                    "projects",
                    "upgrade",
                    "--registry",
                    str(registry),
                    "--apply",
                ]
            )
            results.append(
                check(
                    "retry after reviewing partial commits converges the fleet",
                    rc == 0
                    and all(
                        workspace_revision(project) == second_revision
                        for project in projects
                    ),
                    output,
                )
            )
            for project in projects:
                commit_if_dirty(project, "fleet workspace v2")

            beta = projects[1]
            owned_files = {
                beta / "knowledge" / "fact.md": "# Project fact\n",
                beta / "rules" / "local.md": "# Project rule\n",
                beta / "skills" / "local" / "SKILL.md": "# Project skill\n",
                beta / "src" / "product.txt": "product content\n",
            }
            for path, content in owned_files.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            commit_all(beta, "project-owned content")
            owned_before = {
                path: path.read_bytes() for path in owned_files
            }
            beta_head = git(beta, "rev-parse", "HEAD").stdout.strip()
            beta_before_plan = tree_bytes(beta)
            rc, output = capture_cli(
                ["projects", "detach", "beta", "--registry", str(registry)]
            )
            results.append(
                check(
                    "detach defaults to a no-write plan",
                    rc == 0
                    and tree_bytes(beta) == beta_before_plan
                    and "plan only" in output,
                    output,
                )
            )

            os.environ["EIF_INIT_TEST_FAIL_AFTER"] = "workspace-runtime"
            before_fault = tree_bytes(beta)
            registry_before_fault = registry.read_bytes()
            try:
                rc, output = capture_cli(
                    [
                        "projects",
                        "detach",
                        "beta",
                        "--registry",
                        str(registry),
                        "--apply",
                    ]
                )
            finally:
                os.environ.pop("EIF_INIT_TEST_FAIL_AFTER", None)
            results.append(
                check(
                    "faulted detach restores managed state and registry",
                    rc != 0
                    and tree_bytes(beta) == before_fault
                    and registry.read_bytes() == registry_before_fault,
                    output,
                )
            )

            rc, output = capture_cli(
                [
                    "projects",
                    "detach",
                    "beta",
                    "--registry",
                    str(registry),
                    "--apply",
                ]
            )
            registry_data = yaml.safe_load(registry.read_text(encoding="utf-8"))
            beta_entry = next(
                item
                for item in registry_data["projects"]
                if item["name"] == "beta"
            )
            results.append(
                check(
                    "detach removes only managed runtime and lock",
                    rc == 0
                    and not (beta / ".eif" / "workspace-runtime").exists()
                    and not (beta / ".eif" / "workspace.lock.yaml").exists()
                    and beta_entry["status"] == "detached"
                    and all(
                        path.read_bytes() == owned_before[path]
                        for path in owned_files
                    )
                    and git(beta, "rev-parse", "HEAD").stdout.strip()
                    == beta_head,
                    output,
                )
            )

            commit_all(beta, "detach workspace snapshot")
            commit_all(workspace, "mark beta detached")
            rc, output = capture_cli(
                [
                    "projects",
                    "detach",
                    "beta",
                    "--registry",
                    str(registry),
                    "--apply",
                ]
            )
            results.append(
                check(
                    "repeated detach is idempotent after explicit commit",
                    rc == 0
                    and all(
                        path.read_bytes() == owned_before[path]
                        for path in owned_files
                    ),
                    output,
                )
            )

            rc, output = capture_cli(
                [
                    "projects",
                    "add",
                    str(beta),
                    "--registry",
                    str(registry),
                ]
            )
            registry_data = yaml.safe_load(registry.read_text(encoding="utf-8"))
            beta_entry = next(
                item
                for item in registry_data["projects"]
                if item["name"] == "beta"
            )
            results.append(
                check(
                    "projects add explicitly reactivates a detached project",
                    rc == 0 and beta_entry["status"] == "active",
                    output,
                )
            )
            commit_all(workspace, "reactivate beta")

            rc, output = capture_cli(
                [
                    "projects",
                    "detach",
                    "beta",
                    "--registry",
                    str(registry),
                    "--apply",
                    "--remove-registration",
                ]
            )
            registry_data = yaml.safe_load(registry.read_text(encoding="utf-8"))
            locations_data = yaml.safe_load(
                locations.read_text(encoding="utf-8")
            )
            results.append(
                check(
                    "registration is removed only with the explicit flag",
                    rc == 0
                    and "beta"
                    not in [item["name"] for item in registry_data["projects"]]
                    and len(locations_data["locations"]) == 2
                    and all(
                        path.read_bytes() == owned_before[path]
                        for path in owned_files
                    ),
                    output,
                )
            )
    finally:
        projects_cmd.__version__ = original_projects_version

    passed = sum(1 for ok, _ in results if ok)
    for _, line in results:
        print(line)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_workspace_fleet: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
