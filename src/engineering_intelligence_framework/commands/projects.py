"""`eifctl projects` - manage independent projects from a private registry.

The committed registry stores logical project identities only. Machine paths
live in a separate gitignored locations file.

Commands:
    eifctl projects add PATH [--profile NAME] [--registry PATH]
    eifctl projects remove NAME [--registry PATH]
    eifctl projects detach NAME [--registry PATH] [--apply]
    eifctl projects status [--registry PATH]
    eifctl projects upgrade [--registry PATH] [--apply] [--migrate-source]
    eifctl projects migrate-registry-v1-to-v2 [--registry PATH] [--apply]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from .. import __version__
from .._impl.eif_init import _DeleteStage, commit_transaction
from ..workspace_contract import (
    DEFAULT_REGISTRY,
    LOCATIONS_SCHEMA,
    REGISTRY_SCHEMA,
    WorkspaceContractError,
    commit_yaml_pair,
    default_locations_path,
    ensure_unique_locations,
    ensure_unique_registry,
    migrate_registry_v1_to_v2,
    read_yaml,
    stable_project_id,
)
from ..workspace_materialization import (
    PROFILE_SCHEMA,
    WORKSPACE_CONFIG_SCHEMA,
    WorkspaceMaterializationError,
    materialize_workspace,
    verify_workspace_materialization,
)
from . import upgrade as upgrade_cmd


class RegistryError(WorkspaceContractError):
    pass


def _registry_path(value: str | None) -> Path:
    return Path(value).resolve() if value else DEFAULT_REGISTRY.resolve()


def _locations_path(value: str | None, registry_path: Path) -> Path:
    return (
        Path(value).resolve()
        if value
        else default_locations_path(registry_path).resolve()
    )


def load_registry(path: Path, *, allow_missing: bool = False) -> dict[str, Any]:
    if not path.exists():
        if allow_missing:
            return {"schema_version": 2, "projects": []}
        raise RegistryError(f"registry not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RegistryError(f"cannot read registry {path}: {exc}") from exc
    if isinstance(raw, dict) and raw.get("schema_version") == 1:
        raise RegistryError(
            "legacy registry schema v1 requires the dry-run-first migration: "
            "eifctl projects migrate-registry-v1-to-v2"
        )
    try:
        data = read_yaml(path, REGISTRY_SCHEMA, "project registry")
        ensure_unique_registry(data)
        return data
    except WorkspaceContractError as exc:
        raise RegistryError(str(exc)) from exc


def load_locations(path: Path, *, allow_missing: bool = False) -> dict[str, Any]:
    if not path.exists():
        if allow_missing:
            return {"schema_version": 1, "locations": []}
        raise RegistryError(f"project locations not found: {path}")
    try:
        data = read_yaml(path, LOCATIONS_SCHEMA, "project locations")
        ensure_unique_locations(data)
        return data
    except WorkspaceContractError as exc:
        raise RegistryError(str(exc)) from exc


def _write_state(
    registry_path: Path,
    registry: dict[str, Any],
    locations_path: Path,
    locations: dict[str, Any],
) -> None:
    try:
        commit_yaml_pair(registry_path, registry, locations_path, locations)
    except WorkspaceContractError as exc:
        raise RegistryError(str(exc)) from exc


def _project_identity(project_path: Path) -> str:
    config_path = project_path / ".eif" / "config.yaml"
    lock_path = project_path / ".eif" / "framework.lock.yaml"
    if not config_path.exists() or not lock_path.exists():
        raise RegistryError(
            f"{project_path} is not a complete EIF instance "
            "(.eif/config.yaml and .eif/framework.lock.yaml are required)"
        )
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RegistryError(f"cannot read {config_path}: {exc}") from exc
    name = (
        ((config or {}).get("project") or {}).get("name")
        if isinstance(config, dict)
        else None
    )
    if not isinstance(name, str) or not name.strip():
        raise RegistryError(f"project.name is missing from {config_path}")
    return name.strip()


def register_project(
    registry_path: Path,
    project_path: Path,
    *,
    profile: str = "default",
    locations_path: Path | None = None,
) -> tuple[str, str]:
    registry_path = registry_path.resolve()
    locations_path = (
        locations_path.resolve()
        if locations_path is not None
        else default_locations_path(registry_path).resolve()
    )
    project_path = project_path.resolve()
    validate_profile_selection(registry_path, profile)
    workspace_root = registry_path.parent.parent
    if (
        (workspace_root / ".eif" / "workspace.yaml").exists()
        and project_path == workspace_root.resolve()
    ):
        raise RegistryError(
            "a private workspace cannot register itself in its own project registry"
        )
    name = _project_identity(project_path)
    project_id = stable_project_id(name)
    registry = load_registry(registry_path, allow_missing=True)
    locations = load_locations(locations_path, allow_missing=True)
    location_by_id = {
        item["project_id"]: Path(item["path"]).resolve()
        for item in locations["locations"]
    }

    for entry in registry["projects"]:
        if entry["id"] == project_id:
            existing_path = location_by_id.get(project_id)
            if entry["name"].casefold() == name.casefold():
                if existing_path is not None and existing_path != project_path:
                    raise RegistryError(
                        f"project {name!r} is mapped to a different local path"
                    )
                changed = False
                if existing_path is None:
                    locations["locations"].append(
                        {
                            "project_id": project_id,
                            "path": project_path.as_posix(),
                        }
                    )
                    changed = True
                if entry["status"] != "active" or entry["profile"] != profile:
                    entry["status"] = "active"
                    entry["profile"] = profile
                    changed = True
                if changed:
                    locations["locations"].sort(
                        key=lambda item: item["project_id"]
                    )
                    _write_state(
                        registry_path,
                        registry,
                        locations_path,
                        locations,
                    )
                    return name, "reactivated"
                return name, "already-registered"
            raise RegistryError(
                f"stable project id {project_id!r} is already assigned to "
                f"{entry['name']!r}"
            )
        if entry["name"].casefold() == name.casefold():
            raise RegistryError(
                f"registry already contains project name {name!r}; "
                "project names must be unique"
            )

    registry["projects"].append(
        {
            "id": project_id,
            "name": name,
            "profile": profile,
            "status": "active",
        }
    )
    locations["locations"].append(
        {"project_id": project_id, "path": project_path.as_posix()}
    )
    registry["projects"].sort(key=lambda item: item["name"].casefold())
    locations["locations"].sort(key=lambda item: item["project_id"])
    _write_state(registry_path, registry, locations_path, locations)
    return name, "registered"


def _resolved_projects(
    registry: dict[str, Any],
    locations: dict[str, Any],
) -> list[tuple[dict[str, Any], Path | None]]:
    location_by_id = {
        item["project_id"]: Path(item["path"]).resolve()
        for item in locations["locations"]
    }
    return [
        (entry, location_by_id.get(entry["id"]))
        for entry in registry["projects"]
    ]


def _lock_status(project_path: Path | None) -> tuple[str, str, str]:
    if project_path is None:
        return "unresolved", "-", "location-missing"
    lock_path = project_path / ".eif" / "framework.lock.yaml"
    runtime = project_path / ".eif" / "runtime"
    if not lock_path.exists():
        return "missing-lock", "-", "missing"
    try:
        lock = yaml.safe_load(lock_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return "invalid-lock", "-", "invalid"
    source_type = (lock.get("framework") or {}).get("source_type", "unknown")
    if source_type == "installed-package":
        version = (lock.get("package") or {}).get("version", "unknown")
    elif source_type == "git":
        version = (lock.get("git") or {}).get("commit_sha", "unknown")
        version = version[:12] if isinstance(version, str) else "unknown"
    else:
        version = (lock.get("source_bundle") or {}).get(
            "asserted_ref", "unknown"
        )
    health = "ready" if runtime.exists() else "runtime-missing"
    return str(source_type), str(version), health


def _workspace_root(registry_path: Path) -> Path | None:
    candidate = registry_path.parent.parent.resolve()
    return (
        candidate
        if (candidate / ".eif" / "workspace.yaml").is_file()
        else None
    )


def validate_profile_selection(registry_path: Path, profile: str) -> None:
    """Reject a profile typo before changing a workspace-owned registry."""
    workspace = _workspace_root(registry_path.resolve())
    if workspace is None:
        return
    try:
        config = read_yaml(
            workspace / ".eif" / "workspace.yaml",
            WORKSPACE_CONFIG_SCHEMA,
            "workspace config",
        )
        profile_root = (workspace / config["profiles"]["root"]).resolve()
        profile_path = (profile_root / f"{profile}.yaml").resolve()
        profile_root.relative_to(workspace)
        profile_path.relative_to(profile_root)
        selected = read_yaml(
            profile_path,
            PROFILE_SCHEMA,
            f"workspace profile {profile}",
        )
    except (KeyError, ValueError, WorkspaceContractError) as exc:
        raise RegistryError(
            f"profile {profile!r} is not available in workspace {workspace}: {exc}"
        ) from exc
    if selected["name"] != profile:
        raise RegistryError(
            f"workspace profile filename and name differ: {profile_path.name}"
        )


def _workspace_status(
    project_path: Path | None,
) -> tuple[str, str]:
    if project_path is None:
        return "-", "location-missing"
    lock_path = project_path / ".eif" / "workspace.lock.yaml"
    runtime = project_path / ".eif" / "workspace-runtime"
    if not lock_path.exists() and not runtime.exists():
        return "-", "not-materialized"
    if not lock_path.exists():
        return "-", "missing-lock"
    try:
        lock = yaml.safe_load(lock_path.read_text(encoding="utf-8")) or {}
        revision = (lock.get("workspace") or {}).get("revision", "unknown")
        shown = revision[:12] if isinstance(revision, str) else "unknown"
    except (OSError, yaml.YAMLError):
        return "unknown", "invalid-lock"
    problems = verify_workspace_materialization(project_path)
    return shown, "ready" if not problems else "invalid"


def _detach_workspace_managed(project_path: Path) -> None:
    runtime = project_path / ".eif" / "workspace-runtime"
    lock = project_path / ".eif" / "workspace.lock.yaml"
    stages = []
    if runtime.exists():
        stages.append(
            _DeleteStage("workspace-runtime", runtime, is_dir=True)
        )
    if lock.exists():
        stages.append(
            _DeleteStage("workspace-lock", lock, is_dir=False)
        )
    if stages:
        commit_transaction(stages)


def run(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="eifctl projects",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="Register an existing EIF project.")
    add.add_argument("project_path")
    add.add_argument("--profile", default="default")
    add.add_argument("--registry", default=None)
    add.add_argument("--locations", default=None)

    remove = sub.add_parser(
        "remove",
        help="Remove a logical registration without touching project files.",
    )
    remove.add_argument("name")
    remove.add_argument("--registry", default=None)
    remove.add_argument("--locations", default=None)

    detach = sub.add_parser(
        "detach",
        help="Plan or remove only workspace-managed state from one project.",
    )
    detach.add_argument("name")
    detach.add_argument("--registry", default=None)
    detach.add_argument("--locations", default=None)
    detach.add_argument("--apply", action="store_true")
    detach.add_argument(
        "--remove-registration",
        action="store_true",
        help="Also remove logical registry and local-location entries.",
    )
    detach.add_argument("--allow-dirty-project", action="store_true")

    status = sub.add_parser(
        "status",
        help="Show logical registration, provenance and local runtime state.",
    )
    status.add_argument("--registry", default=None)
    status.add_argument("--locations", default=None)

    upgrade = sub.add_parser(
        "upgrade",
        help="Plan or apply the current EIF package to active projects.",
    )
    upgrade.add_argument("--registry", default=None)
    upgrade.add_argument("--locations", default=None)
    upgrade.add_argument(
        "--apply",
        action="store_true",
        help="Apply after every active project passes a dry-run preflight.",
    )
    upgrade.add_argument("--migrate-source", action="store_true")
    upgrade.add_argument("--allow-dirty-project", action="store_true")

    migrate = sub.add_parser(
        "migrate-registry-v1-to-v2",
        help="Plan the named path-splitting registry migration.",
    )
    migrate.add_argument("--registry", default=None)
    migrate.add_argument("--locations", default=None)
    migrate.add_argument(
        "--apply",
        action="store_true",
        help="Atomically write registry v2 and the gitignored locations file.",
    )

    args = ap.parse_args(argv)
    registry_path = _registry_path(args.registry)
    locations_path = _locations_path(
        getattr(args, "locations", None),
        registry_path,
    )

    try:
        if args.command == "migrate-registry-v1-to-v2":
            registry_v2, locations_v1, resolved_locations = (
                migrate_registry_v1_to_v2(
                    registry_path,
                    locations_path=locations_path,
                    apply=args.apply,
                )
            )
            action = "APPLIED" if args.apply else "PLAN"
            print(
                "eifctl projects migration v1-to-v2: "
                f"{action} {len(registry_v2['projects'])} project(s)"
            )
            print(f"  committed registry: {registry_path}")
            print(f"  local locations: {resolved_locations}")
            if not args.apply:
                print(
                    "eifctl projects: no files were written. "
                    "Re-run with --apply after reviewing the plan."
                )
            return 0

        if args.command == "add":
            name, action = register_project(
                registry_path,
                Path(args.project_path),
                profile=args.profile,
                locations_path=locations_path,
            )
            print(f"eifctl projects: {action} {name} in {registry_path}")
            return 0

        registry = load_registry(registry_path)
        locations = load_locations(locations_path, allow_missing=True)
        projects = _resolved_projects(registry, locations)

        if args.command == "remove":
            removed_ids = {
                entry["id"]
                for entry in registry["projects"]
                if entry["name"] == args.name
            }
            if not removed_ids:
                raise RegistryError(f"project not found in registry: {args.name}")
            registry["projects"] = [
                entry
                for entry in registry["projects"]
                if entry["id"] not in removed_ids
            ]
            locations["locations"] = [
                item
                for item in locations["locations"]
                if item["project_id"] not in removed_ids
            ]
            _write_state(registry_path, registry, locations_path, locations)
            print(
                f"eifctl projects: removed {args.name} from registry; "
                "project files were not touched"
            )
            return 0

        if args.command == "detach":
            matches = [
                (entry, path)
                for entry, path in projects
                if entry["name"] == args.name
            ]
            if not matches:
                raise RegistryError(
                    f"project not found in registry: {args.name}"
                )
            entry, path = matches[0]
            if path is None:
                raise RegistryError(
                    f"project has no machine-local location: {args.name}"
                )
            dirty, detail = upgrade_cmd._git_dirty(path)
            if dirty and not args.allow_dirty_project:
                suffix = f": {detail}" if detail else ""
                raise RegistryError(
                    "project working tree is dirty; commit or stash before "
                    f"detach, or pass --allow-dirty-project to detach anyway "
                    f"(the usual case is repairing a project a failed upgrade "
                    f"left modified){suffix}"
                )
            print(
                f"eifctl projects detach: project={entry['name']} "
                f"workspace-runtime={'present' if (path / '.eif' / 'workspace-runtime').exists() else 'absent'} "
                f"workspace-lock={'present' if (path / '.eif' / 'workspace.lock.yaml').exists() else 'absent'} "
                f"registration={'remove' if args.remove_registration else 'keep-as-detached'}"
            )
            if not args.apply:
                print(
                    "eifctl projects detach: plan only; no files were written. "
                    "Re-run with --apply."
                )
                return 0

            _detach_workspace_managed(path)
            if args.remove_registration:
                registry["projects"] = [
                    project
                    for project in registry["projects"]
                    if project["id"] != entry["id"]
                ]
                locations["locations"] = [
                    location
                    for location in locations["locations"]
                    if location["project_id"] != entry["id"]
                ]
            else:
                entry["status"] = "detached"
            _write_state(registry_path, registry, locations_path, locations)
            print(
                f"eifctl projects detach: SUCCESS {entry['name']}; "
                "project-owned knowledge, rules, skills, history and product "
                "files were not touched"
            )
            return 0

        if args.command == "status":
            print(f"EIF project registry: {registry_path}")
            print(
                "ID\tNAME\tPROFILE\tSTATUS\tFRAMEWORK\tFW_CURRENT\t"
                "FW_RUNTIME\tWORKSPACE\tWS_RUNTIME\tPATH"
            )
            for entry, path in projects:
                source, version, health = _lock_status(path)
                workspace_revision, workspace_health = _workspace_status(path)
                shown_path = str(path) if path is not None else "-"
                print(
                    f"{entry['id']}\t{entry['name']}\t{entry['profile']}\t"
                    f"{entry['status']}\t{source}\t{version}\t{health}\t"
                    f"{workspace_revision}\t{workspace_health}\t{shown_path}"
                )
            print(
                f"eifctl projects: {len(projects)} project(s); "
                f"running package target={__version__}"
            )
            return 0

        active = [
            (entry, path)
            for entry, path in projects
            if entry["status"] == "active"
        ]
        unresolved = [entry["name"] for entry, path in active if path is None]
        if unresolved:
            raise RegistryError(
                "active projects have no machine-local location: "
                + ", ".join(unresolved)
                + ". The locations file is machine-local and gitignored on "
                "purpose, so a workspace cloned onto another machine starts "
                "with none. Re-run `eifctl projects add <path>` once per "
                "project to map them here"
            )
        if not active:
            print("eifctl projects: registry contains no active projects")
            return 0

        common = ["--defer-workspace-check"]
        if args.migrate_source:
            common.append("--migrate-source")
        if args.allow_dirty_project:
            common.append("--allow-dirty-project")

        workspace_root = _workspace_root(registry_path)
        workspace_plans: dict[str, dict[str, Any]] = {}
        pending: list[str] = []
        print(
            f"eifctl projects: preflighting {len(active)} project(s) "
            f"for EIF {__version__}"
            + (
                f" and workspace {workspace_root}"
                if workspace_root is not None
                else ""
            )
        )
        for entry, path in active:
            assert path is not None
            print(f"\n== dry-run: {entry['name']} ({path}) ==")
            rc = upgrade_cmd.run(
                ["--instance-path", str(path), "--dry-run", *common]
            )
            if rc != 0:
                print(
                    f"eifctl projects: preflight failed for {entry['name']}; "
                    "no project was updated",
                    file=sys.stderr,
                )
                return rc
            if workspace_root is not None:
                try:
                    workspace_plan = materialize_workspace(
                        workspace_root,
                        path,
                        profile_name=entry["profile"],
                        required_exceptions=entry.get(
                            "required_exceptions", []
                        ),
                        framework_version=__version__,
                        dry_run=True,
                        allow_dirty_project=args.allow_dirty_project,
                    )
                except WorkspaceMaterializationError as exc:
                    print(
                        f"eifctl projects: workspace preflight failed for "
                        f"{entry['name']}: {exc}; no project was updated",
                        file=sys.stderr,
                    )
                    return 1
                workspace_plans[entry["id"]] = workspace_plan
                current_workspace, current_health = _workspace_status(path)
                framework_current = _lock_status(path)[1]
                framework_changes = framework_current != __version__
                workspace_changes = bool(workspace_plan.get("changed", True))
                if framework_changes or workspace_changes:
                    pending.append(entry["name"])
                print(
                    "  framework: "
                    f"current={framework_current} target={__version__} "
                    f"change={'yes' if framework_changes else 'no'}"
                )
                workspace_line = (
                    "  workspace: "
                    f"pinned={current_workspace} "
                    f"profile={entry['profile']} "
                    f"overrides={len(workspace_plan['overrides'])} "
                    f"health={current_health} "
                    f"change={'yes' if workspace_changes else 'no'}"
                )
                if workspace_changes:
                    workspace_line += f" -> {workspace_plan['revision'][:12]}"
                print(workspace_line)

        if not args.apply:
            if workspace_root is not None and not pending:
                print(
                    "\neifctl projects: every active project is already current "
                    "on both axes; nothing to apply."
                )
                return 0
            print(
                "\neifctl projects: plan complete; no files were written. "
                "Re-run with --apply to update."
            )
            return 0

        completed: list[str] = []
        for index, (entry, path) in enumerate(active):
            assert path is not None
            print(f"\n== apply: {entry['name']} ({path}) ==")
            rc = upgrade_cmd.run(["--instance-path", str(path), *common])
            if rc != 0:
                done = ", ".join(completed) if completed else "none"
                untouched = ", ".join(
                    item[0]["name"] for item in active[index + 1 :]
                ) or "none"
                print(
                    f"eifctl projects: failed={entry['name']} axis=framework; "
                    f"completed={done}; untouched={untouched}",
                    file=sys.stderr,
                )
                return rc
            if workspace_root is not None:
                try:
                    applied = materialize_workspace(
                        workspace_root,
                        path,
                        profile_name=entry["profile"],
                        required_exceptions=entry.get(
                            "required_exceptions", []
                        ),
                        framework_version=__version__,
                        allow_dirty_project=True,
                    )
                    # The framework axis ran with the workspace check deferred,
                    # so this is where the workspace guarantee is enforced.
                    remaining = verify_workspace_materialization(path)
                    if remaining:
                        raise WorkspaceMaterializationError("; ".join(remaining))
                    skill_activation = applied.get("skill_activation", {})
                    skill_written = skill_activation.get("written", [])
                    skill_preserved = skill_activation.get("preserved", [])
                    skill_removed = skill_activation.get("removed", [])
                    print(
                        "  workspace axis: "
                        + (
                            "materialized "
                            f"{applied['revision'][:12]}"
                            if applied.get("changed", True)
                            else "already current, nothing written"
                        )
                    )
                    print(
                        "  agent skills: "
                        f"updated={len(skill_written)} "
                        f"preserved={len(skill_preserved)} "
                        f"removed={len(skill_removed)}"
                    )
                except (WorkspaceMaterializationError, RuntimeError) as exc:
                    done = ", ".join(completed) if completed else "none"
                    untouched = ", ".join(
                        item[0]["name"] for item in active[index + 1 :]
                    ) or "none"
                    print(
                        f"eifctl projects: failed={entry['name']} "
                        f"axis=workspace after framework axis succeeded; "
                        f"completed={done}; untouched={untouched}; error={exc}",
                        file=sys.stderr,
                    )
                    return 1
            completed.append(entry["name"])
        print(
            f"\neifctl projects: SUCCESS updated {len(completed)} "
            f"project(s) to EIF {__version__}"
            + (
                " and the selected workspace revisions"
                if workspace_root is not None
                else ""
            )
        )
        return 0
    except (RegistryError, WorkspaceContractError, RuntimeError) as exc:
        print(f"eifctl projects: {exc}", file=sys.stderr)
        return 1
