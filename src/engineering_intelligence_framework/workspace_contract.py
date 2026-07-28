"""Versioned data contracts and transactions for EIF private workspaces."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from .resources import framework_root

REGISTRY_SCHEMA = "project-registry.schema.json"
LEGACY_REGISTRY_SCHEMA = "project-registry-v1.schema.json"
LOCATIONS_SCHEMA = "project-locations.schema.json"
DEFAULT_REGISTRY = Path(".eif") / "projects.yaml"
DEFAULT_LOCATIONS = Path(".eif") / "local-state" / "project-locations.yaml"


class WorkspaceContractError(ValueError):
    """A workspace file is invalid or cannot be changed safely."""


def schema_data(name: str) -> dict[str, Any]:
    with framework_root() as root:
        path = root / "core" / "schemas" / name
        return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_data(data: Any, schema_name: str, label: str) -> None:
    errors = sorted(
        Draft202012Validator(schema_data(schema_name)).iter_errors(data),
        key=lambda error: list(error.path),
    )
    if errors:
        detail = "; ".join(
            f"{'.'.join(str(part) for part in error.path) or '(root)'}: {error.message}"
            for error in errors
        )
        raise WorkspaceContractError(f"{label} schema validation failed: {detail}")


def read_yaml(path: Path, schema_name: str, label: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkspaceContractError(f"{label} not found: {path}") from exc
    except (OSError, yaml.YAMLError) as exc:
        raise WorkspaceContractError(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise WorkspaceContractError(f"{label} must contain a YAML mapping: {path}")
    validate_data(data, schema_name, label)
    return data


def dump_yaml(data: dict[str, Any], header: str) -> bytes:
    return (
        f"# {header}\n"
        + yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    ).encode("utf-8")


def default_locations_path(registry_path: Path) -> Path:
    if registry_path.name == "projects.yaml" and registry_path.parent.name == ".eif":
        return registry_path.parent / "local-state" / "project-locations.yaml"
    return registry_path.parent / "local-state" / "project-locations.yaml"


def stable_project_id(name: str) -> str:
    normalized = name.strip().casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "project"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]
    return f"{slug[:53].rstrip('-')}-{digest}"


def ensure_unique_registry(data: dict[str, Any]) -> None:
    ids: set[str] = set()
    names: set[str] = set()
    for project in data.get("projects", []):
        project_id = project["id"]
        name_key = project["name"].casefold()
        if project_id in ids:
            raise WorkspaceContractError(f"duplicate project id in registry: {project_id}")
        if name_key in names:
            raise WorkspaceContractError(
                f"duplicate project name in registry: {project['name']}"
            )
        ids.add(project_id)
        names.add(name_key)


def ensure_unique_locations(data: dict[str, Any]) -> None:
    project_ids: set[str] = set()
    for location in data.get("locations", []):
        project_id = location["project_id"]
        if project_id in project_ids:
            raise WorkspaceContractError(
                f"duplicate project id in local locations: {project_id}"
            )
        project_ids.add(project_id)


def _restore(path: Path, previous: bytes | None) -> None:
    if previous is None:
        if path.exists():
            path.unlink()
        return
    restore_path = path.with_name(path.name + ".restore")
    restore_path.write_bytes(previous)
    restore_path.replace(path)


def commit_yaml_pair(
    registry_path: Path,
    registry_data: dict[str, Any],
    locations_path: Path,
    locations_data: dict[str, Any],
    *,
    fault_after: str | None = None,
) -> None:
    """Validate and replace registry plus local locations as one transaction."""
    validate_data(registry_data, REGISTRY_SCHEMA, "project registry")
    validate_data(locations_data, LOCATIONS_SCHEMA, "project locations")
    ensure_unique_registry(registry_data)
    ensure_unique_locations(locations_data)

    created_dirs: list[Path] = []
    for parent in (registry_path.parent, locations_path.parent):
        missing: list[Path] = []
        current = parent
        while not current.exists():
            missing.append(current)
            current = current.parent
        parent.mkdir(parents=True, exist_ok=True)
        created_dirs.extend(reversed(missing))
    registry_next = registry_path.with_name(registry_path.name + ".next")
    locations_next = locations_path.with_name(locations_path.name + ".next")
    registry_before = registry_path.read_bytes() if registry_path.exists() else None
    locations_before = locations_path.read_bytes() if locations_path.exists() else None
    registry_next.write_bytes(
        dump_yaml(
            registry_data,
            "Committed logical EIF project registry. Machine paths are forbidden here.",
        )
    )
    locations_next.write_bytes(
        dump_yaml(
            locations_data,
            "Machine-local EIF project paths. Keep this file gitignored.",
        )
    )

    failed = False
    try:
        read_yaml(registry_next, REGISTRY_SCHEMA, "staged project registry")
        read_yaml(locations_next, LOCATIONS_SCHEMA, "staged project locations")
        registry_next.replace(registry_path)
        if fault_after == "registry":
            raise RuntimeError("fault injection after registry replacement")
        locations_next.replace(locations_path)
        if fault_after == "locations":
            raise RuntimeError("fault injection after locations replacement")
    except Exception:
        failed = True
        _restore(registry_path, registry_before)
        _restore(locations_path, locations_before)
        raise
    finally:
        for transient in (
            registry_next,
            locations_next,
            registry_path.with_name(registry_path.name + ".restore"),
            locations_path.with_name(locations_path.name + ".restore"),
        ):
            if transient.exists():
                transient.unlink()
        if failed:
            for created_dir in sorted(
                set(created_dirs),
                key=lambda item: len(item.parts),
                reverse=True,
            ):
                try:
                    created_dir.rmdir()
                except OSError:
                    pass


def registry_v1_migration_plan(
    registry_path: Path,
    *,
    locations_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    registry_path = registry_path.resolve()
    locations_path = (
        locations_path.resolve()
        if locations_path is not None
        else default_locations_path(registry_path).resolve()
    )
    legacy = read_yaml(
        registry_path,
        LEGACY_REGISTRY_SCHEMA,
        "legacy project registry v1",
    )
    if locations_path.exists():
        raise WorkspaceContractError(
            f"migration refuses to overwrite existing local locations: {locations_path}"
        )

    projects: list[dict[str, Any]] = []
    locations: list[dict[str, str]] = []
    seen_names: set[str] = set()
    seen_ids: set[str] = set()
    for entry in legacy["projects"]:
        name = entry["name"].strip()
        name_key = name.casefold()
        if name_key in seen_names:
            raise WorkspaceContractError(f"legacy registry has duplicate name: {name}")
        project_id = stable_project_id(name)
        if project_id in seen_ids:
            raise WorkspaceContractError(
                f"legacy registry identity collision for project: {name}"
            )
        source_path = Path(entry["path"])
        resolved_path = (
            source_path.resolve()
            if source_path.is_absolute()
            else (registry_path.parent / source_path).resolve()
        )
        projects.append(
            {
                "id": project_id,
                "name": name,
                "profile": "default",
                "status": "active",
            }
        )
        locations.append(
            {
                "project_id": project_id,
                "path": resolved_path.as_posix(),
            }
        )
        seen_names.add(name_key)
        seen_ids.add(project_id)

    registry_v2 = {"schema_version": 2, "projects": projects}
    locations_v1 = {"schema_version": 1, "locations": locations}
    validate_data(registry_v2, REGISTRY_SCHEMA, "migrated project registry")
    validate_data(locations_v1, LOCATIONS_SCHEMA, "migrated project locations")
    ensure_unique_registry(registry_v2)
    ensure_unique_locations(locations_v1)
    return registry_v2, locations_v1, locations_path


def migrate_registry_v1_to_v2(
    registry_path: Path,
    *,
    locations_path: Path | None = None,
    apply: bool = False,
    fault_after: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    registry_v2, locations_v1, resolved_locations = registry_v1_migration_plan(
        registry_path,
        locations_path=locations_path,
    )
    if apply:
        commit_yaml_pair(
            registry_path.resolve(),
            registry_v2,
            resolved_locations,
            locations_v1,
            fault_after=fault_after,
        )
    return registry_v2, locations_v1, resolved_locations
