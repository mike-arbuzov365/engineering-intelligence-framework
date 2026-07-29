"""Resolve and materialize a pinned private-workspace snapshot."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from . import __version__
from ._impl.eif_init import (
    FAULT_INJECT_ENV,
    _Stage,
    combined_digest,
    commit_transaction,
    hash_file,
    verify_staged_bundle,
)
from .workspace_contract import (
    WorkspaceContractError,
    dump_yaml,
    read_yaml,
    validate_data,
)

PROFILE_SCHEMA = "workspace-profile.schema.json"
OVERRIDES_SCHEMA = "workspace-overrides.schema.json"
LOCK_SCHEMA = "workspace-lock.schema.json"
WORKSPACE_CONFIG_SCHEMA = "workspace-config.schema.json"
FAULT_ENV = "EIF_WORKSPACE_TEST_FAIL_AFTER"


class WorkspaceMaterializationError(WorkspaceContractError):
    pass


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _clean_revision(workspace: Path) -> tuple[str, str]:
    status = _git(workspace, "status", "--porcelain", "--untracked-files=all")
    if status.returncode != 0:
        raise WorkspaceMaterializationError(
            f"cannot inspect workspace git state: {status.stderr.strip()}"
        )
    if status.stdout.strip():
        dirty_files = ", ".join(
            line[3:].strip() for line in status.stdout.strip().splitlines()[:5]
        )
        raise WorkspaceMaterializationError(
            f"workspace working tree is dirty at {workspace}; a snapshot can "
            "only be pinned to a commit. Review and commit the workspace "
            f"first (uncommitted: {dirty_files}). Registering a project with "
            "`eifctl projects add` edits the committed registry, so that "
            "change needs its own commit before the next fleet run"
        )
    revision = _git(workspace, "rev-parse", "HEAD")
    generated_at = _git(workspace, "show", "-s", "--format=%cI", "HEAD")
    if revision.returncode != 0 or not re.fullmatch(
        r"[0-9a-f]{40}", revision.stdout.strip()
    ):
        raise WorkspaceMaterializationError(
            "workspace has no verifiable git commit; commit the workspace first"
        )
    if generated_at.returncode != 0 or not generated_at.stdout.strip():
        raise WorkspaceMaterializationError(
            "cannot read the workspace commit timestamp"
        )
    return revision.stdout.strip(), generated_at.stdout.strip()


def _materialization_is_current(project: Path, lock_data: dict[str, Any]) -> bool:
    """True when this project already carries exactly the snapshot that would
    be written now: same workspace identity, profile, resolution and bundle
    digest, and a runtime whose files still hash to the recorded manifest."""
    lock_path = project / ".eif" / "workspace.lock.yaml"
    if not lock_path.exists():
        return False
    try:
        existing = read_yaml(lock_path, LOCK_SCHEMA, "workspace lock")
    except WorkspaceContractError:
        return False
    existing_workspace = existing.get("workspace") or {}
    if existing_workspace.get("id") != lock_data["workspace"]["id"]:
        return False
    if existing_workspace.get("profile") != lock_data["workspace"]["profile"]:
        return False
    if existing.get("resolution") != lock_data["resolution"]:
        return False
    if (existing.get("bundle") or {}).get("digest") != lock_data["bundle"]["digest"]:
        return False
    return not verify_workspace_materialization(project)


def _project_is_clean(project: Path) -> bool:
    status = _git(project, "status", "--porcelain", "--untracked-files=all")
    if status.returncode != 0:
        raise WorkspaceMaterializationError(
            f"cannot inspect project git state: {status.stderr.strip()}"
        )
    return not status.stdout.strip()


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise WorkspaceMaterializationError(
            f"cannot evaluate framework version {value!r}"
        )
    return tuple(int(part) for part in match.groups())


def _version_satisfies(version: str, requirement: str) -> bool:
    current = _version_tuple(version)
    for raw_clause in requirement.split(","):
        clause = raw_clause.strip()
        match = re.fullmatch(r"(>=|<=|==|>|<)(\d+\.\d+\.\d+)", clause)
        if not match:
            raise WorkspaceMaterializationError(
                f"unsupported framework requirement clause: {clause!r}"
            )
        operator, target_text = match.groups()
        target = _version_tuple(target_text)
        comparisons = {
            ">=": current >= target,
            "<=": current <= target,
            "==": current == target,
            ">": current > target,
            "<": current < target,
        }
        if not comparisons[operator]:
            return False
    return True


def _load_overrides(project: Path) -> list[dict[str, Any]]:
    path = project / ".eif" / "workspace-overrides.yaml"
    if not path.exists():
        return []
    return read_yaml(path, OVERRIDES_SCHEMA, "workspace overrides")["overrides"]


def _collision_candidates(
    project: Path,
    artifact: dict[str, Any],
) -> list[Path]:
    category = {
        "rule": "rules",
        "skill": "skills",
        "playbook": "playbooks",
        "template": "templates",
        "knowledge": "knowledge",
    }[artifact["kind"]]
    base = project / category / artifact["name"]
    return [base, base.with_suffix(".md")]


def _artifact_collision(project: Path, artifact: dict[str, Any]) -> bool:
    return any(
        candidate.exists()
        for candidate in _collision_candidates(project, artifact)
    )


def _validate_resolution(
    project: Path,
    artifacts: list[dict[str, Any]],
    overrides: list[dict[str, Any]],
    required_exceptions: list[dict[str, Any]],
) -> None:
    artifact_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for artifact in artifacts:
        key = (artifact["kind"], artifact["name"])
        if key in artifact_by_key:
            raise WorkspaceMaterializationError(
                f"duplicate workspace artifact identity: {key[0]}/{key[1]}"
            )
        artifact_by_key[key] = artifact

    override_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for override in overrides:
        key = (override["kind"], override["name"])
        if key in override_by_key:
            raise WorkspaceMaterializationError(
                f"duplicate workspace override: {key[0]}/{key[1]}"
            )
        artifact = artifact_by_key.get(key)
        expected = f"workspace://{key[0]}/{key[1]}"
        if artifact is None:
            raise WorkspaceMaterializationError(
                "override references no selected workspace artifact: "
                f"{key[0]}/{key[1]}"
            )
        if override["override_of"] != expected:
            raise WorkspaceMaterializationError(
                f"override_of must be {expected!r} for {key[0]}/{key[1]}"
            )
        override_by_key[key] = override

    exception_by_artifact = {
        item["artifact"]: item for item in required_exceptions
    }
    if len(exception_by_artifact) != len(required_exceptions):
        raise WorkspaceMaterializationError(
            "duplicate required-artifact exception in project registry"
        )

    for key, artifact in artifact_by_key.items():
        collision = _artifact_collision(project, artifact)
        override = override_by_key.get(key)
        if collision and override is None:
            raise WorkspaceMaterializationError(
                f"undeclared same-name collision: {key[0]}/{key[1]}"
            )
        if not collision and override is not None:
            raise WorkspaceMaterializationError(
                f"stale override has no project-owned artifact: {key[0]}/{key[1]}"
            )
        if (
            collision
            and artifact["mode"] == "required"
            and f"{key[0]}/{key[1]}" not in exception_by_artifact
        ):
            raise WorkspaceMaterializationError(
                "required artifact override lacks an approved registry "
                f"exception: {key[0]}/{key[1]}"
            )


def _resolve_files(
    content_root: Path,
    artifacts: list[dict[str, Any]],
) -> list[tuple[Path, dict[str, Any]]]:
    resolved: list[tuple[Path, dict[str, Any]]] = []
    seen_paths: set[str] = set()
    content_root = content_root.resolve()
    for artifact in sorted(
        artifacts,
        key=lambda item: (
            item["kind"],
            item["name"].casefold(),
            item["path"],
        ),
    ):
        relative = Path(artifact["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise WorkspaceMaterializationError(
                f"workspace artifact path escapes content root: {artifact['path']}"
            )
        source = (content_root / relative).resolve()
        if not source.is_relative_to(content_root):
            raise WorkspaceMaterializationError(
                f"workspace artifact path escapes content root: {artifact['path']}"
            )
        if source.is_file():
            source_files = [(source, relative.as_posix())]
        elif source.is_dir():
            source_files = [
                (file, (relative / file.relative_to(source)).as_posix())
                for file in sorted(source.rglob("*"))
                if file.is_file()
            ]
            if not source_files:
                raise WorkspaceMaterializationError(
                    f"workspace artifact directory is empty: {artifact['path']}"
                )
        else:
            raise WorkspaceMaterializationError(
                f"workspace artifact does not exist: {artifact['path']}"
            )
        for source_file, target_path in source_files:
            if target_path in seen_paths:
                raise WorkspaceMaterializationError(
                    "two workspace artifacts resolve to the same file: "
                    f"{target_path}"
                )
            seen_paths.add(target_path)
            resolved.append(
                (
                    source_file,
                    {
                        "path": target_path,
                        "sha256": hash_file(source_file),
                        "kind": artifact["kind"],
                        "name": artifact["name"],
                        "mode": artifact["mode"],
                    },
                )
            )
    return sorted(resolved, key=lambda item: item[1]["path"])


def resolve_workspace(
    workspace: Path,
    project: Path,
    *,
    profile_name: str,
    required_exceptions: list[dict[str, Any]] | None = None,
    framework_version: str = __version__,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    project = project.resolve()
    config = read_yaml(
        workspace / ".eif" / "workspace.yaml",
        WORKSPACE_CONFIG_SCHEMA,
        "workspace config",
    )
    profile = read_yaml(
        workspace / config["profiles"]["root"] / f"{profile_name}.yaml",
        PROFILE_SCHEMA,
        f"workspace profile {profile_name}",
    )
    if profile["name"] != profile_name:
        raise WorkspaceMaterializationError(
            "workspace profile filename and name do not match"
        )
    requirement = profile["framework"]["requires"]
    if not _version_satisfies(framework_version, requirement):
        raise WorkspaceMaterializationError(
            f"workspace profile {profile_name!r} requires EIF {requirement}; "
            f"running target is {framework_version}"
        )
    revision, generated_at = _clean_revision(workspace)
    overrides = _load_overrides(project)
    exceptions = list(required_exceptions or [])
    artifacts = list(profile["artifacts"])
    _validate_resolution(project, artifacts, overrides, exceptions)
    files = _resolve_files(
        workspace / config["content"]["root"],
        artifacts,
    )
    return {
        "workspace_id": config["workspace"]["id"],
        "revision": revision,
        "generated_at": generated_at,
        "profile": profile_name,
        "framework_requirement": requirement,
        "artifacts": artifacts,
        "files": files,
        "overrides": overrides,
        "required_exceptions": exceptions,
    }


def materialize_workspace(
    workspace: Path,
    project: Path,
    *,
    profile_name: str,
    required_exceptions: list[dict[str, Any]] | None = None,
    framework_version: str = __version__,
    dry_run: bool = False,
    allow_dirty_project: bool = False,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    project = project.resolve()
    plan = resolve_workspace(
        workspace,
        project,
        profile_name=profile_name,
        required_exceptions=required_exceptions,
        framework_version=framework_version,
    )

    eif_dir = project / ".eif"
    runtime = eif_dir / "workspace-runtime"
    runtime_next = eif_dir / "workspace-runtime.next"
    lock = eif_dir / "workspace.lock.yaml"
    lock_next = eif_dir / "workspace.lock.yaml.next"
    manifest = [entry for _, entry in plan["files"]]
    lock_data = {
        "lock_schema_version": 1,
        "workspace": {
            "id": plan["workspace_id"],
            "revision": plan["revision"],
            "profile": plan["profile"],
        },
        "resolution": {
            "overrides": plan["overrides"],
            "required_exceptions": plan["required_exceptions"],
        },
        "bundle": {
            "path": ".eif/workspace-runtime",
            "manifest": manifest,
            "digest": combined_digest(manifest),
        },
        "generated_at": plan["generated_at"],
    }
    validate_data(lock_data, LOCK_SCHEMA, "workspace lock")
    plan["digest"] = lock_data["bundle"]["digest"]
    plan["changed"] = not _materialization_is_current(project, lock_data)

    # Freshness is a question about resolved CONTENT, not about how many
    # commits the workspace has taken since. Comparing git HEAD instead meant
    # that registering project N+1 - a commit touching only the registry -
    # marked all N already-connected projects stale and forced a
    # re-materialization plus a commit in each, for a byte-identical bundle.
    if not plan["changed"]:
        return plan

    if not allow_dirty_project and not _project_is_clean(project):
        raise WorkspaceMaterializationError(
            "project working tree is dirty; commit or stash project changes "
            "before materializing workspace policy"
        )
    if dry_run:
        return plan

    shutil.rmtree(runtime_next, ignore_errors=True)
    lock_next.unlink(missing_ok=True)

    try:
        runtime_next.mkdir(parents=True)
        for index, (source, entry) in enumerate(plan["files"]):
            destination = runtime_next / entry["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            if (
                index == 0
                and os.environ.get(FAULT_ENV) == "workspace-runtime-stage"
            ):
                raise RuntimeError(
                    "fault injection during workspace runtime staging"
                )
        problems = verify_staged_bundle(runtime_next, manifest)
        if problems:
            raise WorkspaceMaterializationError("; ".join(problems))
        lock_next.write_bytes(
            dump_yaml(
                lock_data,
                "EIF-managed pinned private workspace snapshot.",
            )
        )
        read_yaml(lock_next, LOCK_SCHEMA, "staged workspace lock")
        if os.environ.get(FAULT_ENV) == "workspace-lock-stage":
            raise RuntimeError("fault injection during workspace lock staging")

        stages = [
            _Stage("workspace-runtime", runtime_next, runtime, is_dir=True),
            _Stage("workspace-lock", lock_next, lock, is_dir=False),
        ]
        old_init_fault = os.environ.get(FAULT_INJECT_ENV)
        workspace_fault = os.environ.get(FAULT_ENV)
        if workspace_fault in {"workspace-runtime", "workspace-lock"}:
            os.environ[FAULT_INJECT_ENV] = workspace_fault
        try:
            commit_transaction(stages)
        finally:
            if old_init_fault is None:
                os.environ.pop(FAULT_INJECT_ENV, None)
            else:
                os.environ[FAULT_INJECT_ENV] = old_init_fault
    except Exception:
        shutil.rmtree(runtime_next, ignore_errors=True)
        lock_next.unlink(missing_ok=True)
        raise
    return plan


def _manifest_artifacts(
    manifest: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in manifest:
        key = (entry["kind"], entry["name"])
        artifact = {
            "kind": entry["kind"],
            "name": entry["name"],
            "mode": entry["mode"],
        }
        previous = by_key.get(key)
        if previous is not None and previous != artifact:
            raise WorkspaceMaterializationError(
                f"inconsistent manifest metadata for {key[0]}/{key[1]}"
            )
        by_key[key] = artifact
    return list(by_key.values())


def verify_workspace_materialization(project: Path) -> list[str]:
    project = project.resolve()
    runtime = project / ".eif" / "workspace-runtime"
    lock_path = project / ".eif" / "workspace.lock.yaml"
    if not runtime.exists() and not lock_path.exists():
        return []
    if not lock_path.exists():
        return ["workspace lock is missing while workspace runtime exists"]
    if not runtime.exists():
        return [
            "workspace runtime is missing while workspace lock exists. "
            ".eif/workspace-runtime/ is deliberately gitignored, so a fresh "
            "clone never carries it; re-materialize it from the private "
            "workspace with `eifctl projects upgrade --registry "
            "<workspace>/.eif/projects.yaml --apply`"
        ]
    try:
        lock = read_yaml(lock_path, LOCK_SCHEMA, "workspace lock")
    except WorkspaceContractError as exc:
        return [str(exc)]

    problems: list[str] = []
    manifest = lock["bundle"]["manifest"]
    expected = {entry["path"] for entry in manifest}
    actual = {
        path.relative_to(runtime).as_posix()
        for path in runtime.rglob("*")
        if path.is_file()
    }
    for path in sorted(expected - actual):
        problems.append(f"workspace runtime file is missing: {path}")
    for path in sorted(actual - expected):
        problems.append(f"unexpected workspace runtime file: {path}")
    for entry in manifest:
        target = runtime / entry["path"]
        if target.is_file() and hash_file(target) != entry["sha256"]:
            problems.append(f"workspace runtime hash drift: {entry['path']}")
    if combined_digest(manifest) != lock["bundle"]["digest"]:
        problems.append("workspace lock combined digest is inconsistent")
    try:
        _validate_resolution(
            project,
            _manifest_artifacts(manifest),
            lock["resolution"]["overrides"],
            lock["resolution"]["required_exceptions"],
        )
    except WorkspaceMaterializationError as exc:
        problems.append(str(exc))
    return problems
