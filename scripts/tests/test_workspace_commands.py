#!/usr/bin/env python3
"""Synthetic lifecycle checks for `eifctl workspace` and registry v2."""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from engineering_intelligence_framework import cli  # noqa: E402
from engineering_intelligence_framework.commands.workspace import (  # noqa: E402
    FAULT_ENV,
    professional_profile_catalog,
)


def check(name: str, condition: bool, detail: str = "") -> tuple[bool, str]:
    return (
        condition,
        f"{'PASS' if condition else 'FAIL'} {name}"
        + (f": {detail}" if detail and not condition else ""),
    )


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): (
            path.read_bytes() if path.is_file() else b"<DIR>"
        )
        for path in sorted(root.rglob("*"))
    }


def main() -> int:
    results: list[tuple[bool, str]] = []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        empty_target = root / "existing-empty-workspace"
        empty_target.mkdir()
        empty_before = tree(root)
        empty_error = io.StringIO()
        with contextlib.redirect_stderr(empty_error):
            empty_rc = cli.main(["workspace", "new", str(empty_target)])
        empty_message = empty_error.getvalue()
        results.append(
            check(
                "workspace new explains how to recover from an existing empty target",
                empty_rc != 0
                and tree(root) == empty_before
                and "requires a path that does not exist" in empty_message
                and "re-run the command from the parent directory" in empty_message,
                empty_message,
            )
        )
        empty_target.rmdir()

        import_probe = root / "import-probe"
        import_probe.mkdir()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        imported = subprocess.run(
            [
                sys.executable,
                "-c",
                "import engineering_intelligence_framework.cli",
            ],
            cwd=import_probe,
            env=env,
            capture_output=True,
            text=True,
        )
        results.append(
            check(
                "package import is side-effect free",
                imported.returncode == 0 and not any(import_probe.iterdir()),
                imported.stdout + imported.stderr,
            )
        )

        workspace = root / "workspace-control"
        rc = cli.main(
            [
                "workspace",
                "new",
                str(workspace),
                "--workspace-name",
                "Workspace control",
                "--adapter",
                "codex",
                "--locale",
                "uk",
            ]
        )
        results.append(check("workspace new succeeds", rc == 0))
        results.append(
            check(
                "workspace is an EIF project instance",
                (workspace / ".eif" / "config.yaml").is_file()
                and (workspace / ".eif" / "framework.lock.yaml").is_file()
                and (workspace / "AGENTS.md").is_file(),
            )
        )
        results.append(
            check(
                "workspace is a local git repository with no remote",
                (workspace / ".git").is_dir()
                and git(workspace, "remote").stdout.strip() == "",
            )
        )
        registry_path = workspace / ".eif" / "projects.yaml"
        locations_path = (
            workspace / ".eif" / "local-state" / "project-locations.yaml"
        )
        workspace_config = yaml.safe_load(
            (workspace / ".eif" / "workspace.yaml").read_text(encoding="utf-8")
        )
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        locations = yaml.safe_load(locations_path.read_text(encoding="utf-8"))
        results.append(
            check(
                "workspace starts outside its own fleet",
                registry["projects"] == []
                and locations["locations"] == []
                and registry["workspace_id"]
                == workspace_config["workspace"]["id"],
            )
        )
        results.append(
            check(
                "workspace local state and runtime are gitignored",
                git(
                    workspace,
                    "check-ignore",
                    "-q",
                    ".eif/local-state/project-locations.yaml",
                ).returncode
                == 0
                and git(
                    workspace,
                    "check-ignore",
                    "-q",
                    ".eif/workspace-runtime/probe",
                ).returncode
                == 0,
            )
        )
        results.append(
            check(
                "workspace ships a classification-first migration ledger",
                (workspace / "planning" / "migration-ledger.md").is_file()
                and "Do not copy a directory wholesale"
                in (
                    workspace / "planning" / "migration-ledger.md"
                ).read_text(encoding="utf-8"),
            )
        )
        catalog_names = {item["name"] for item in professional_profile_catalog()}
        results.append(
            check(
                "public professional profile catalog contains two focused starters",
                catalog_names == {"graphic-design", "software-development"},
                str(sorted(catalog_names)),
            )
        )
        install_argv = [
            "workspace",
            "profile",
            "install",
            "graphic-design",
            "--workspace-path",
            str(workspace),
        ]
        results.append(
            check(
                "graphic-design starter installs into the private workspace",
                cli.main(install_argv) == 0
                and (
                    workspace / "workspace" / "profiles" / "graphic-design.yaml"
                ).is_file()
                and (
                    workspace
                    / "workspace"
                    / "skills"
                    / "run-graphic-design-project"
                    / "SKILL.md"
                ).is_file(),
            )
        )
        installed_tree = tree(workspace)
        results.append(
            check(
                "professional profile install is idempotent",
                cli.main(install_argv) == 0 and tree(workspace) == installed_tree,
            )
        )
        delivery = workspace / "workspace" / "templates" / "design-delivery.md"
        delivery_before = delivery.read_bytes()
        delivery.write_text("# Workspace-owned customization\n", encoding="utf-8")
        customized_tree = tree(workspace)
        results.append(
            check(
                "professional profile install refuses to overwrite customization",
                cli.main(install_argv) != 0 and tree(workspace) == customized_tree,
            )
        )
        delivery.write_bytes(delivery_before)
        results.append(
            check(
                "workspace doctor validates every installed profile",
                cli.main(
                    [
                        "workspace",
                        "doctor",
                        "--workspace-path",
                        str(workspace),
                    ]
                )
                == 0,
            )
        )
        delivery.unlink()
        results.append(
            check(
                "workspace doctor catches a missing artifact in a non-default profile",
                cli.main(
                    [
                        "workspace",
                        "doctor",
                        "--workspace-path",
                        str(workspace),
                    ]
                )
                != 0,
            )
        )
        delivery.write_bytes(delivery_before)

        rejected_target = root / "unknown-profile-project"
        registry_before_rejection = registry_path.read_bytes()
        results.append(
            check(
                "new rejects an unknown professional profile before creating files",
                cli.main(
                    [
                        "new",
                        str(rejected_target),
                        "--registry",
                        str(registry_path),
                        "--profile",
                        "unknown-profile",
                    ]
                )
                != 0
                and not rejected_target.exists()
                and registry_path.read_bytes() == registry_before_rejection,
            )
        )

        before_repeat = tree(workspace)
        rc = cli.main(["workspace", "new", str(workspace)])
        results.append(
            check(
                "repeated workspace new fails without changing the target",
                rc != 0 and tree(workspace) == before_repeat,
            )
        )

        alpha = root / "alpha"
        beta = root / "beta"
        for project, adapter in ((alpha, "claude-code"), (beta, "hermes")):
            rc = cli.main(
                [
                    "new",
                    str(project),
                    "--project-name",
                    project.name,
                    "--adapter",
                    adapter,
                    "--registry",
                    str(registry_path),
                    *(
                        ["--profile", "graphic-design"]
                        if project == beta
                        else []
                    ),
                ]
            )
            results.append(
                check(f"connects independent project {project.name}", rc == 0)
            )

        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        locations = yaml.safe_load(locations_path.read_text(encoding="utf-8"))
        results.append(
            check(
                "two projects share logical registry and local mappings",
                len(registry["projects"]) == 2
                and len(locations["locations"]) == 2
                and all("path" not in project for project in registry["projects"]),
            )
        )
        results.append(
            check(
                "new records the selected professional profile",
                next(
                    item for item in registry["projects"] if item["name"] == "beta"
                )["profile"]
                == "graphic-design",
            )
        )
        results.append(
            check(
                "projects status is repeatable",
                cli.main(
                    ["projects", "status", "--registry", str(registry_path)]
                )
                == 0
                and cli.main(
                    ["projects", "status", "--registry", str(registry_path)]
                )
                == 0,
            )
        )
        results.append(
            check(
                "workspace doctor passes with two resolved projects",
                cli.main(
                    [
                        "workspace",
                        "doctor",
                        "--workspace-path",
                        str(workspace),
                    ]
                )
                == 0,
            )
        )

        registry_before_self = registry_path.read_bytes()
        locations_before_self = locations_path.read_bytes()
        rc = cli.main(
            [
                "projects",
                "add",
                str(workspace),
                "--registry",
                str(registry_path),
            ]
        )
        results.append(
            check(
                "workspace self-registration is refused without a write",
                rc != 0
                and registry_path.read_bytes() == registry_before_self
                and locations_path.read_bytes() == locations_before_self,
            )
        )

        broken_locations = yaml.safe_load(
            locations_path.read_text(encoding="utf-8")
        )
        broken_locations["locations"] = broken_locations["locations"][:1]
        locations_path.write_text(
            yaml.safe_dump(broken_locations, sort_keys=False),
            encoding="utf-8",
        )
        results.append(
            check(
                "workspace doctor fails an unresolved active project",
                cli.main(
                    [
                        "workspace",
                        "doctor",
                        "--workspace-path",
                        str(workspace),
                    ]
                )
                != 0,
            )
        )
        locations_path.write_bytes(locations_before_self)
        results.append(
            check(
                "workspace doctor recovers after the local mapping is restored",
                cli.main(
                    [
                        "workspace",
                        "doctor",
                        "--workspace-path",
                        str(workspace),
                    ]
                )
                == 0,
            )
        )

        failed_target = root / "faulted-workspace"
        before_fault = tree(root)
        os.environ[FAULT_ENV] = "workspace-scaffold"
        try:
            rc = cli.main(["workspace", "new", str(failed_target)])
        finally:
            os.environ.pop(FAULT_ENV, None)
        results.append(
            check(
                "faulted workspace creation leaves no target or staging tree",
                rc != 0
                and not failed_target.exists()
                and tree(root) == before_fault,
            )
        )

    passed = sum(1 for ok, _ in results if ok)
    for _, line in results:
        print(line)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_workspace_commands: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
