"""`eifctl workspace` - create and verify an optional private workspace."""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from .._impl import eif_init
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
PROFESSIONAL_PROFILE_ROOT = "professional-profiles"
PROFILE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class WorkspaceError(WorkspaceContractError):
    pass


def _contained(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise WorkspaceError(f"{label} escapes its allowed root: {relative}") from exc
    return candidate


def professional_profile_catalog() -> list[dict[str, str]]:
    """Return the validated public starter catalog bundled with eifctl."""
    catalog: list[dict[str, str]] = []
    with framework_root() as root:
        catalog_root = root / PROFESSIONAL_PROFILE_ROOT
        if not catalog_root.is_dir():
            raise WorkspaceError("installed package has no professional profile catalog")
        for pack in sorted(catalog_root.iterdir()):
            manifest = pack / "profile.yaml"
            if not pack.is_dir() or not manifest.is_file():
                continue
            profile = read_yaml(
                manifest,
                WORKSPACE_PROFILE_SCHEMA,
                f"professional profile {pack.name}",
            )
            if profile["name"] != pack.name:
                raise WorkspaceError(
                    f"professional profile directory and name differ: {pack.name}"
                )
            catalog.append(
                {
                    "name": profile["name"],
                    "description": profile.get("description", ""),
                }
            )
    return catalog


def install_professional_profile(
    workspace: Path,
    name: str,
) -> tuple[list[str], list[str]]:
    """Install one public starter without overwriting workspace-owned content."""
    workspace = workspace.resolve()
    if not PROFILE_NAME.fullmatch(name):
        raise WorkspaceError(f"invalid professional profile name: {name!r}")
    config, _, _ = _load_workspace_files(workspace)
    profile_root = _contained(
        workspace,
        config["profiles"]["root"],
        "workspace profiles root",
    )
    content_root = _contained(
        workspace,
        config["content"]["root"],
        "workspace content root",
    )

    desired: dict[Path, bytes] = {}
    with framework_root() as root:
        pack = root / PROFESSIONAL_PROFILE_ROOT / name
        manifest = pack / "profile.yaml"
        if not manifest.is_file():
            available = ", ".join(item["name"] for item in professional_profile_catalog())
            raise WorkspaceError(
                f"unknown professional profile {name!r}; available: {available or 'none'}"
            )
        profile = read_yaml(
            manifest,
            WORKSPACE_PROFILE_SCHEMA,
            f"professional profile {name}",
        )
        if profile["name"] != name:
            raise WorkspaceError("professional profile directory and name do not match")
        desired[profile_root / f"{name}.yaml"] = manifest.read_bytes()

        for artifact in profile["artifacts"]:
            source = _contained(pack, artifact["path"], "profile artifact")
            target = _contained(content_root, artifact["path"], "workspace artifact")
            if source.is_file():
                files = [(source, target)]
            elif source.is_dir():
                files = [
                    (item, target / item.relative_to(source))
                    for item in sorted(source.rglob("*"))
                    if eif_init.is_portable_resource_file(item)
                ]
                if not files:
                    raise WorkspaceError(
                        f"professional profile artifact is empty: {artifact['path']}"
                    )
            else:
                raise WorkspaceError(
                    f"professional profile artifact is missing: {artifact['path']}"
                )
            for source_file, destination in files:
                content = source_file.read_bytes()
                prior = desired.get(destination)
                if prior is not None and prior != content:
                    raise WorkspaceError(
                        f"professional profile maps conflicting content to {destination}"
                    )
                desired[destination] = content

    conflicts: list[Path] = []
    preserved: list[str] = []
    missing: list[tuple[Path, bytes]] = []
    for destination, content in sorted(desired.items(), key=lambda item: str(item[0])):
        shown = destination.relative_to(workspace).as_posix()
        if destination.is_file():
            if destination.read_bytes() == content:
                preserved.append(shown)
            else:
                conflicts.append(destination)
        elif destination.exists():
            conflicts.append(destination)
        else:
            missing.append((destination, content))
    if conflicts:
        shown = ", ".join(
            path.relative_to(workspace).as_posix() for path in conflicts[:5]
        )
        raise WorkspaceError(
            "professional profile would overwrite workspace-owned content: "
            f"{shown}. Keep the local version or install under a new profile name"
        )

    stages: list[eif_init._Stage] = []
    written: list[str] = []
    try:
        for destination, content in missing:
            destination.parent.mkdir(parents=True, exist_ok=True)
            staged = destination.with_name(destination.name + ".eif-profile-next")
            if staged.exists():
                raise WorkspaceError(f"stale profile staging path exists: {staged}")
            staged.write_bytes(content)
            shown = destination.relative_to(workspace).as_posix()
            stages.append(eif_init._Stage(f"professional-profile:{shown}", staged, destination, False))
            written.append(shown)
        if stages:
            eif_init.commit_transaction(stages)
    except Exception:
        for stage in stages:
            stage.next_path.unlink(missing_ok=True)
        raise
    return written, preserved


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

    # The base project was initialized before .eif/workspace.yaml existed, so
    # its managed .gitattributes block could not yet know this instance is a
    # workspace. Re-render it here rather than waiting for the first upgrade,
    # and through the same helper so there is one definition of the block.
    lock = read_yaml(
        workspace / ".eif" / "framework.lock.yaml",
        "framework-lock.schema.json",
        "framework lock",
    )
    gitattributes = workspace / ".gitattributes"
    merged, _action = eif_init.render_merged_content(
        gitattributes.read_text(encoding="utf-8") if gitattributes.exists() else None,
        eif_init.render_gitattributes_block(
            lock["adapter"]["entrypoint"],
            (lock.get("knowledge_index") or {}).get("path"),
            eif_init.workspace_content_root(workspace),
        ),
        eif_init.GITATTRIBUTES_MARKER,
        eif_init.GITATTRIBUTES_END,
    )
    gitattributes.write_bytes(merged.encode("utf-8"))

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


def _profile_inventory(
    workspace: Path,
    config: dict[str, Any],
) -> tuple[set[str], list[str]]:
    """Validate every profile and the workspace-owned sources it selects."""
    problems: list[str] = []
    try:
        profile_root = _contained(
            workspace,
            config["profiles"]["root"],
            "workspace profiles root",
        )
        content_root = _contained(
            workspace,
            config["content"]["root"],
            "workspace content root",
        )
    except (KeyError, WorkspaceError) as exc:
        return set(), [str(exc)]
    if not profile_root.is_dir():
        return set(), [f"workspace profiles root is missing: {profile_root}"]

    names: set[str] = set()
    for profile_path in sorted(profile_root.glob("*.yaml")):
        try:
            profile = read_yaml(
                profile_path,
                WORKSPACE_PROFILE_SCHEMA,
                f"workspace profile {profile_path.stem}",
            )
        except WorkspaceContractError as exc:
            problems.append(str(exc))
            continue
        name = profile["name"]
        if name != profile_path.stem:
            problems.append(
                f"workspace profile filename and name differ: {profile_path.name}"
            )
        if name in names:
            problems.append(f"duplicate workspace profile name: {name}")
        names.add(name)
        seen_artifacts: set[tuple[str, str]] = set()
        for artifact in profile["artifacts"]:
            key = (artifact["kind"], artifact["name"])
            if key in seen_artifacts:
                problems.append(
                    f"workspace profile {name} repeats artifact {key[0]}:{key[1]}"
                )
            seen_artifacts.add(key)
            try:
                source = _contained(
                    content_root,
                    artifact["path"],
                    f"workspace profile {name} artifact",
                )
            except WorkspaceError as exc:
                problems.append(str(exc))
                continue
            if not source.exists():
                problems.append(
                    f"workspace profile {name} artifact is missing: {artifact['path']}"
                )
            if artifact["kind"] == "skill" and not (
                source.is_dir() and (source / "SKILL.md").is_file()
            ):
                problems.append(
                    f"workspace profile {name} skill lacks SKILL.md: {artifact['path']}"
                )
    return names, problems


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

    profile_names, profile_problems = _profile_inventory(workspace, config)
    problems.extend(profile_problems)
    profile_name = config["profiles"]["default"]
    if profile_name not in profile_names:
        problems.append(f"default workspace profile is missing: {profile_name}")

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
        if project["profile"] not in profile_names:
            problems.append(
                f"{project['name']}: selected workspace profile is missing: "
                f"{project['profile']}"
            )
        location = location_by_id.get(project["id"])
        if location == workspace:
            problems.append("workspace must not register itself as a project")
        if project["status"] == "active" and location is None:
            problems.append(
                f"active project has no machine-local location: {project['name']}"
            )
        if project["status"] == "active" and location is not None:
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


def _mapping_report(workspace: Path) -> list[str]:
    """`workspace doctor` verifies machine-local project mappings, as its own
    help promises, but used to print nothing about them - a clean run looked
    identical whether the registry held zero projects or ten."""
    try:
        _, registry, locations = _load_workspace_files(workspace.resolve())
    except WorkspaceContractError:
        return []
    location_by_id = {item["project_id"]: item["path"] for item in locations["locations"]}
    lines = [
        f"eifctl workspace doctor: {len(registry['projects'])} registered project(s)"
    ]
    for project in registry["projects"]:
        mapped = location_by_id.get(project["id"], "unmapped on this machine")
        lines.append(
            f"  {project['name']}\tstatus={project['status']}\t"
            f"profile={project['profile']}\t{mapped}"
        )
    return lines


def run(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="eifctl workspace", description=__doc__)
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

    profile = sub.add_parser(
        "profile",
        help="List or install public professional profile starters.",
    )
    profile_sub = profile.add_subparsers(dest="profile_command", required=True)
    profile_sub.add_parser("list", help="List bundled professional profiles.")
    install = profile_sub.add_parser(
        "install",
        help="Copy one starter into a private workspace without overwriting files.",
    )
    install.add_argument("name")
    install.add_argument("--workspace-path", default=".")

    args = ap.parse_args(argv)
    try:
        if args.command == "new":
            target = Path(args.path).resolve()
            print(
                f"eifctl workspace new: building in a temporary sibling "
                f"directory, then moving the finished tree to {target}"
            )
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

        if args.command == "profile":
            if args.profile_command == "list":
                catalog = professional_profile_catalog()
                for item in catalog:
                    print(f"{item['name']}\t{item['description']}")
                print(f"eifctl workspace profile: {len(catalog)} available")
                return 0
            workspace_path = Path(args.workspace_path).resolve()
            written, preserved = install_professional_profile(
                workspace_path,
                args.name,
            )
            print(
                f"eifctl workspace profile install: {args.name} "
                f"written={len(written)} preserved={len(preserved)}"
            )
            print(
                "eifctl workspace profile install: review and commit the "
                "workspace before assigning the profile to projects"
            )
            return 0

        workspace_path = Path(args.workspace_path).resolve()
        problems = workspace_problems(workspace_path)
        for line in _mapping_report(workspace_path):
            print(line)
        if problems:
            for problem in problems:
                print(f"eifctl workspace doctor: FAIL {problem}", file=sys.stderr)
            print(
                f"eifctl workspace doctor: FAILED {workspace_path} - "
                f"{len(problems)} problem(s) above"
            )
            return 1
        print(f"eifctl workspace doctor: PASS {workspace_path}")
        return 0
    except (WorkspaceError, WorkspaceContractError, RuntimeError) as exc:
        print(f"eifctl workspace: {exc}", file=sys.stderr)
        return 1
