"""`eifctl workspace` - create and verify an optional private workspace."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from ..resources import framework_root
from ..workspace_contract import (
    LOCATIONS_SCHEMA,
    REGISTRY_SCHEMA,
    WorkspaceContractError,
    dump_yaml,
    read_yaml,
    stable_project_id,
    validate_data,
)
from ..workspace_materialization import verify_workspace_materialization
from . import doctor as doctor_cmd
from . import new as new_cmd

WORKSPACE_CONFIG_SCHEMA = "workspace-config.schema.json"
WORKSPACE_PROFILE_SCHEMA = "workspace-profile.schema.json"
FAULT_ENV = "EIF_WORKSPACE_TEST_FAIL_AFTER"


class WorkspaceError(WorkspaceContractError):
    pass


def _git(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _write_workspace_scaffold(workspace: Path, name: str) -> None:
    workspace_id = stable_project_id(name)
    workspace_config = {
        "schema_version": 1,
        "workspace": {"id": workspace_id, "name": name},
        "registry": {
            "path": ".eif/projects.yaml",
            "locations_path": ".eif/local-state/project-locations.yaml",
        },
        "profiles": {"root": "workspace/profiles", "default": "default"},
        "content": {"root": "workspace"},
    }
    registry = {
        "schema_version": 2,
        "workspace_id": workspace_id,
        "projects": [],
    }
    locations = {"schema_version": 1, "locations": []}
    profile = {
        "schema_version": 1,
        "name": "default",
        "description": "Minimal user-owned workspace profile.",
        "framework": {"requires": ">=0.2.0,<0.3.0"},
        "artifacts": [],
    }
    validate_data(workspace_config, WORKSPACE_CONFIG_SCHEMA, "workspace config")
    validate_data(registry, REGISTRY_SCHEMA, "project registry")
    validate_data(locations, LOCATIONS_SCHEMA, "project locations")
    validate_data(profile, WORKSPACE_PROFILE_SCHEMA, "workspace profile")

    eif_dir = workspace / ".eif"
    local_state = eif_dir / "local-state"
    profile_dir = workspace / "workspace" / "profiles"
    planning_dir = workspace / "planning"
    local_state.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)
    planning_dir.mkdir(parents=True, exist_ok=True)
    (eif_dir / "workspace.yaml").write_bytes(
        dump_yaml(workspace_config, "User-owned EIF private workspace configuration.")
    )
    (eif_dir / "projects.yaml").write_bytes(
        dump_yaml(
            registry,
            "Committed logical EIF project registry. Machine paths are forbidden here.",
        )
    )
    (local_state / "project-locations.yaml").write_bytes(
        dump_yaml(
            locations,
            "Machine-local EIF project paths. Keep this file gitignored.",
        )
    )
    (profile_dir / "default.yaml").write_bytes(
        dump_yaml(profile, "Minimal user-owned private workspace profile.")
    )
    with framework_root() as root:
        migration_template = (
            root / "templates" / "workspace-migration-ledger.md"
        ).read_text(encoding="utf-8")
    (planning_dir / "migration-ledger.md").write_text(
        migration_template,
        encoding="utf-8",
    )

    gitignore = workspace / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    for required_ignore in (
        ".eif/local-state/",
        ".eif/workspace-runtime/",
        ".eif/workspace-runtime.next/",
        ".eif/workspace-runtime.previous/",
    ):
        if required_ignore not in existing:
            raise WorkspaceError(
                f"base EIF project did not generate required ignore: "
                f"{required_ignore}"
            )


def create_workspace(
    target: Path,
    *,
    name: str,
    adapter: str,
    locale: str,
) -> None:
    target = target.resolve()
    if target.exists():
        raise WorkspaceError(f"target already exists: {target}")
    if not target.parent.exists():
        raise WorkspaceError(f"parent directory does not exist: {target.parent}")

    container = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.eif-workspace-", dir=target.parent)
    )
    stage = container / "workspace"
    try:
        rc = new_cmd.run(
            [
                str(stage),
                "--project-name",
                name,
                "--adapter",
                adapter,
                "--locale",
                locale,
            ]
        )
        if rc != 0:
            raise WorkspaceError("base EIF project creation failed")
        if os.environ.get(FAULT_ENV) == "base-project":
            raise RuntimeError("fault injection after base project creation")
        _write_workspace_scaffold(stage, name)
        if os.environ.get(FAULT_ENV) == "workspace-scaffold":
            raise RuntimeError("fault injection after workspace scaffold")
        problems = workspace_problems(stage, include_base_doctor=False)
        if problems:
            raise WorkspaceError(
                "staged workspace verification failed: " + "; ".join(problems)
            )
        stage.replace(target)
    finally:
        if container.exists():
            shutil.rmtree(container)


def _load_workspace_files(
    workspace: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    config = read_yaml(
        workspace / ".eif" / "workspace.yaml",
        WORKSPACE_CONFIG_SCHEMA,
        "workspace config",
    )
    registry = read_yaml(
        workspace / config["registry"]["path"],
        REGISTRY_SCHEMA,
        "project registry",
    )
    locations_path = workspace / config["registry"]["locations_path"]
    if locations_path.exists():
        locations = read_yaml(
            locations_path,
            LOCATIONS_SCHEMA,
            "project locations",
        )
    else:
        locations = {"schema_version": 1, "locations": []}
    return config, registry, locations


def workspace_problems(
    workspace: Path,
    *,
    include_base_doctor: bool = True,
) -> list[str]:
    workspace = workspace.resolve()
    problems: list[str] = []
    if include_base_doctor and doctor_cmd.run(
        ["--instance-path", str(workspace)]
    ) != 0:
        problems.append("base EIF project doctor failed")
    try:
        config, registry, locations = _load_workspace_files(workspace)
    except WorkspaceContractError as exc:
        return [str(exc), *problems]

    workspace_id = config["workspace"]["id"]
    if registry.get("workspace_id") != workspace_id:
        problems.append("registry workspace_id does not match workspace config")

    profile_name = config["profiles"]["default"]
    profile_path = (
        workspace / config["profiles"]["root"] / f"{profile_name}.yaml"
    )
    try:
        profile = read_yaml(
            profile_path,
            WORKSPACE_PROFILE_SCHEMA,
            f"workspace profile {profile_name}",
        )
        if profile["name"] != profile_name:
            problems.append("default profile filename and name do not match")
    except WorkspaceContractError as exc:
        problems.append(str(exc))

    location_by_id = {
        item["project_id"]: Path(item["path"]).resolve()
        for item in locations["locations"]
    }
    registry_ids = {item["id"] for item in registry["projects"]}
    unknown_locations = set(location_by_id) - registry_ids
    if unknown_locations:
        problems.append(
            "local locations reference unknown project IDs: "
            + ", ".join(sorted(unknown_locations))
        )
    for project in registry["projects"]:
        location = location_by_id.get(project["id"])
        if location == workspace:
            problems.append("workspace must not register itself as a project")
        if project["status"] == "active" and location is None:
            problems.append(
                f"active project has no machine-local location: {project['name']}"
            )
        if location is not None:
            for problem in verify_workspace_materialization(location):
                problems.append(f"{project['name']}: {problem}")

    git_root = _git(workspace, "rev-parse", "--show-toplevel")
    if git_root.returncode != 0 or Path(git_root.stdout.strip()).resolve() != workspace:
        problems.append("workspace is not the root of a local git repository")
    for ignored_path in (
        ".eif/local-state/project-locations.yaml",
        ".eif/workspace-runtime/probe",
    ):
        ignored = _git(workspace, "check-ignore", "-q", ignored_path)
        if ignored.returncode != 0:
            problems.append(f"workspace path is not gitignored: {ignored_path}")
    return problems


def run(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="Create a local private workspace repo.")
    new.add_argument("path")
    new.add_argument("--workspace-name", default=None)
    new.add_argument(
        "--adapter",
        choices=["claude-code", "cursor", "codex", "hermes"],
        default="claude-code",
    )
    new.add_argument("--locale", choices=["en", "uk"], default="en")

    doctor = sub.add_parser(
        "doctor",
        help="Verify a workspace and its machine-local project mappings.",
    )
    doctor.add_argument("--workspace-path", default=".")

    args = ap.parse_args(argv)
    try:
        if args.command == "new":
            target = Path(args.path).resolve()
            create_workspace(
                target,
                name=args.workspace_name or target.name,
                adapter=args.adapter,
                locale=args.locale,
            )
            print(
                f"eifctl workspace new: SUCCESS created local workspace at {target}"
            )
            print(
                "eifctl workspace new: no remote, visibility choice, push or "
                "publication was performed"
            )
            return 0

        workspace_path = Path(args.workspace_path).resolve()
        problems = workspace_problems(workspace_path)
        if problems:
            for problem in problems:
                print(f"eifctl workspace doctor: FAIL {problem}", file=sys.stderr)
            return 1
        print(f"eifctl workspace doctor: PASS {workspace_path}")
        return 0
    except (WorkspaceError, WorkspaceContractError, RuntimeError) as exc:
        print(f"eifctl workspace: {exc}", file=sys.stderr)
        return 1
