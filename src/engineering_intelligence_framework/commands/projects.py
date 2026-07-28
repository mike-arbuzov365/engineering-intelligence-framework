"""`eifctl projects` - manage independent projects from a private registry.

The committed registry stores logical project identities only. Machine paths
live in a separate gitignored locations file.

Commands:
    eifctl projects add PATH [--profile NAME] [--registry PATH]
    eifctl projects remove NAME [--registry PATH]
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
            if (
                entry["name"].casefold() == name.casefold()
                and existing_path == project_path
            ):
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


def run(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
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

        if args.command == "status":
            print(f"EIF project registry: {registry_path}")
            print("ID\tNAME\tPROFILE\tSTATUS\tSOURCE\tCURRENT\tRUNTIME\tPATH")
            for entry, path in projects:
                source, version, health = _lock_status(path)
                shown_path = str(path) if path is not None else "-"
                print(
                    f"{entry['id']}\t{entry['name']}\t{entry['profile']}\t"
                    f"{entry['status']}\t{source}\t{version}\t{health}\t"
                    f"{shown_path}"
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
            )
        if not active:
            print("eifctl projects: registry contains no active projects")
            return 0

        common = []
        if args.migrate_source:
            common.append("--migrate-source")
        if args.allow_dirty_project:
            common.append("--allow-dirty-project")

        print(
            f"eifctl projects: preflighting {len(active)} project(s) "
            f"for EIF {__version__}"
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

        if not args.apply:
            print(
                "\neifctl projects: plan complete; no files were written. "
                "Re-run with --apply to update."
            )
            return 0

        completed: list[str] = []
        for entry, path in active:
            assert path is not None
            print(f"\n== apply: {entry['name']} ({path}) ==")
            rc = upgrade_cmd.run(["--instance-path", str(path), *common])
            if rc != 0:
                done = ", ".join(completed) if completed else "none"
                print(
                    f"eifctl projects: stopped at {entry['name']}; "
                    f"already updated: {done}. No later project was touched.",
                    file=sys.stderr,
                )
                return rc
            completed.append(entry["name"])
        print(
            f"\neifctl projects: SUCCESS updated {len(completed)} "
            f"project(s) to EIF {__version__}"
        )
        return 0
    except (RegistryError, WorkspaceContractError) as exc:
        print(f"eifctl projects: {exc}", file=sys.stderr)
        return 1
