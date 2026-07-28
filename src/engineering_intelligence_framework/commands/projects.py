"""`eifctl projects` - manage a private registry of EIF project instances.

The default registry is `.eif/projects.yaml` in the current directory. It
belongs in the user's private control repository. Paths are stored relative
to the registry, and nothing is sent to the public EIF repository.

Commands:
    eifctl projects add PATH [--registry PATH]
    eifctl projects remove NAME [--registry PATH]
    eifctl projects status [--registry PATH]
    eifctl projects upgrade [--registry PATH] [--apply] [--migrate-source]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from .. import __version__
from ..resources import framework_root
from . import upgrade as upgrade_cmd

DEFAULT_REGISTRY = Path(".eif") / "projects.yaml"


class RegistryError(ValueError):
    pass


def _registry_path(value: str | None) -> Path:
    return Path(value).resolve() if value else DEFAULT_REGISTRY.resolve()


def _validate_registry(data: dict) -> None:
    with framework_root() as root:
        schema = yaml.safe_load((root / "core" / "schemas" / "project-registry.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(f"{'.'.join(str(p) for p in e.path) or '(root)'}: {e.message}" for e in errors)
        raise RegistryError(f"registry schema validation failed: {detail}")


def load_registry(path: Path, *, allow_missing: bool = False) -> dict:
    if not path.exists():
        if allow_missing:
            return {"schema_version": 1, "projects": []}
        raise RegistryError(f"registry not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RegistryError(f"cannot read registry {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise RegistryError(f"registry must contain a YAML mapping: {path}")
    _validate_registry(raw)
    return raw


def _write_registry(path: Path, data: dict) -> None:
    _validate_registry(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    next_path = path.with_name(path.name + ".next")
    text = (
        "# User-owned private EIF project registry. Paths are relative to this file.\n"
        + yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    )
    try:
        next_path.write_text(text, encoding="utf-8")
        next_path.replace(path)
    finally:
        if next_path.exists():
            next_path.unlink()


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
    name = ((config or {}).get("project") or {}).get("name") if isinstance(config, dict) else None
    if not isinstance(name, str) or not name.strip():
        raise RegistryError(f"project.name is missing from {config_path}")
    return name.strip()


def register_project(registry_path: Path, project_path: Path) -> tuple[str, str]:
    registry_path = registry_path.resolve()
    project_path = project_path.resolve()
    name = _project_identity(project_path)
    data = load_registry(registry_path, allow_missing=True)
    try:
        stored_path = Path(os.path.relpath(project_path, registry_path.parent)).as_posix()
    except ValueError:
        # Windows cannot express a relative path across drive letters.
        # Keep the exact absolute path rather than inventing portability.
        stored_path = project_path.as_posix()

    for entry in data["projects"]:
        existing = (registry_path.parent / entry["path"]).resolve()
        if existing == project_path:
            return name, "already-registered"
        if entry["name"] == name:
            raise RegistryError(
                f"registry already contains project name {name!r} at {entry['path']!r}; "
                "project names must be unique"
            )

    data["projects"].append({"name": name, "path": stored_path})
    data["projects"].sort(key=lambda item: item["name"].casefold())
    _write_registry(registry_path, data)
    return name, "registered"


def _resolved_projects(registry_path: Path, data: dict) -> list[tuple[dict, Path]]:
    return [(entry, (registry_path.parent / entry["path"]).resolve()) for entry in data["projects"]]


def _lock_status(project_path: Path) -> tuple[str, str, str]:
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
        version = (lock.get("source_bundle") or {}).get("asserted_ref", "unknown")
    health = "ready" if runtime.exists() else "runtime-missing"
    return str(source_type), str(version), health


def run(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="Register an existing EIF project.")
    add.add_argument("project_path")
    add.add_argument("--registry", default=None)

    remove = sub.add_parser("remove", help="Remove a project from the registry without touching the project.")
    remove.add_argument("name")
    remove.add_argument("--registry", default=None)

    status = sub.add_parser("status", help="Show registered project provenance and local runtime state.")
    status.add_argument("--registry", default=None)

    upgrade = sub.add_parser("upgrade", help="Plan or apply the current EIF package to every registered project.")
    upgrade.add_argument("--registry", default=None)
    upgrade.add_argument("--apply", action="store_true", help="Apply after every project passes a dry-run preflight.")
    upgrade.add_argument("--migrate-source", action="store_true")
    upgrade.add_argument("--allow-dirty-project", action="store_true")

    args = ap.parse_args(argv)
    registry_path = _registry_path(args.registry)

    try:
        if args.command == "add":
            name, action = register_project(registry_path, Path(args.project_path))
            print(f"eifctl projects: {action} {name} in {registry_path}")
            return 0

        data = load_registry(registry_path)
        projects = _resolved_projects(registry_path, data)

        if args.command == "remove":
            kept = [entry for entry in data["projects"] if entry["name"] != args.name]
            if len(kept) == len(data["projects"]):
                raise RegistryError(f"project not found in registry: {args.name}")
            data["projects"] = kept
            _write_registry(registry_path, data)
            print(f"eifctl projects: removed {args.name} from registry; project files were not touched")
            return 0

        if args.command == "status":
            print(f"EIF project registry: {registry_path}")
            print("NAME\tSOURCE\tCURRENT\tRUNTIME\tPATH")
            for entry, path in projects:
                source, version, health = _lock_status(path)
                print(f"{entry['name']}\t{source}\t{version}\t{health}\t{path}")
            print(f"eifctl projects: {len(projects)} project(s); running package target={__version__}")
            return 0

        if not projects:
            print("eifctl projects: registry contains no projects")
            return 0

        common = []
        if args.migrate_source:
            common.append("--migrate-source")
        if args.allow_dirty_project:
            common.append("--allow-dirty-project")

        # Cross-repository updates are intentionally not atomic. Preflight
        # every target before the first write, then stop on the first apply
        # failure and report which earlier projects succeeded.
        print(f"eifctl projects: preflighting {len(projects)} project(s) for EIF {__version__}")
        for entry, path in projects:
            print(f"\n== dry-run: {entry['name']} ({path}) ==")
            rc = upgrade_cmd.run(["--instance-path", str(path), "--dry-run", *common])
            if rc != 0:
                print(f"eifctl projects: preflight failed for {entry['name']}; no project was updated", file=sys.stderr)
                return rc

        if not args.apply:
            print("\neifctl projects: plan complete; no files were written. Re-run with --apply to update.")
            return 0

        completed: list[str] = []
        for entry, path in projects:
            print(f"\n== apply: {entry['name']} ({path}) ==")
            rc = upgrade_cmd.run(["--instance-path", str(path), *common])
            if rc != 0:
                done = ", ".join(completed) if completed else "none"
                print(
                    f"eifctl projects: stopped at {entry['name']}; already updated: {done}. "
                    "No later project was touched.",
                    file=sys.stderr,
                )
                return rc
            completed.append(entry["name"])
        print(f"\neifctl projects: SUCCESS updated {len(completed)} project(s) to EIF {__version__}")
        return 0
    except RegistryError as exc:
        print(f"eifctl projects: {exc}", file=sys.stderr)
        return 1
