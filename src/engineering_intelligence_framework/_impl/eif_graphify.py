#!/usr/bin/env python3
"""Portable, structural-only Graphify artifact lifecycle for EIF.

This module validates and restores local graph artifacts. It never invokes
Graphify generation, a semantic provider, or a paid/deep scan. Repository
identity comes from an explicit scope manifest, never a worktree folder name.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
FRESHNESS_STATES = {
    "fresh",
    "code-update-required",
    "semantic-update-required",
    "full-rebuild-required",
    "blocked",
    "suppressed",
}
MAX_GRAPH_ARTIFACT_BYTES = 256 * 1024 * 1024
_ARCHIVE_READ_CHUNK_BYTES = 1024 * 1024


def framework_root() -> Path:
    module_dir = Path(__file__).resolve().parent
    if (module_dir / "core" / "schemas").is_dir():
        return module_dir
    return module_dir.parent


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema(name: str, root: Path) -> dict:
    return _read_json(root / "core" / "schemas" / name)


def _validate(data: dict, schema_name: str, root: Path) -> list[str]:
    validator = Draft202012Validator(
        _schema(schema_name, root),
        format_checker=FormatChecker(),
    )
    return [
        error.message
        for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path))
    ]


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_graph_archive(path: Path) -> bytes:
    """Read a raw or gzip graph artifact without allowing unbounded expansion."""
    if path.suffix.lower() != ".gz":
        if path.stat().st_size > MAX_GRAPH_ARTIFACT_BYTES:
            raise ValueError(
                f"archive graph exceeds the {MAX_GRAPH_ARTIFACT_BYTES}-byte safety limit"
            )
        data = path.read_bytes()
        if len(data) > MAX_GRAPH_ARTIFACT_BYTES:
            raise ValueError(
                f"archive graph exceeds the {MAX_GRAPH_ARTIFACT_BYTES}-byte safety limit"
            )
        return data

    chunks: list[bytes] = []
    total = 0
    with gzip.open(path, "rb") as handle:
        while True:
            chunk = handle.read(_ARCHIVE_READ_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_GRAPH_ARTIFACT_BYTES:
                raise ValueError(
                    f"expanded archive graph exceeds the {MAX_GRAPH_ARTIFACT_BYTES}-byte safety limit"
                )
            chunks.append(chunk)
    return b"".join(chunks)


def _reserved_backup_path(parent: Path, prefix: str) -> Path:
    """Reserve a unique same-directory path for an atomic rollback backup."""
    with tempfile.NamedTemporaryFile(delete=False, dir=parent, prefix=prefix) as handle:
        candidate = Path(handle.name)
    candidate.unlink()
    return candidate


def _replace_pair_transactionally(
    staged_graph: Path,
    artifact: Path,
    staged_metadata: Path,
    metadata_target: Path,
) -> None:
    """Replace graph and metadata as one recoverable filesystem transaction."""
    graph_backup: Path | None = None
    metadata_backup: Path | None = None
    graph_installed = False
    metadata_installed = False
    completed = False
    try:
        if artifact.exists():
            graph_backup = _reserved_backup_path(
                artifact.parent, ".eif-restore-graph-backup-"
            )
            artifact.replace(graph_backup)
        if metadata_target.exists():
            metadata_backup = _reserved_backup_path(
                metadata_target.parent, ".eif-restore-metadata-backup-"
            )
            metadata_target.replace(metadata_backup)

        staged_graph.replace(artifact)
        graph_installed = True
        staged_metadata.replace(metadata_target)
        metadata_installed = True
        completed = True
    except OSError as exc:
        rollback_errors: list[str] = []
        try:
            if graph_installed:
                artifact.unlink(missing_ok=True)
            if graph_backup is not None and graph_backup.exists():
                graph_backup.replace(artifact)
        except OSError as rollback_exc:
            rollback_errors.append(f"graph rollback failed: {rollback_exc}")
        try:
            if metadata_installed:
                metadata_target.unlink(missing_ok=True)
            if metadata_backup is not None and metadata_backup.exists():
                metadata_backup.replace(metadata_target)
        except OSError as rollback_exc:
            rollback_errors.append(f"metadata rollback failed: {rollback_exc}")
        if rollback_errors:
            raise RuntimeError(
                "Graphify restore failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
            ) from exc
        raise
    finally:
        if completed:
            if graph_backup is not None:
                graph_backup.unlink(missing_ok=True)
            if metadata_backup is not None:
                metadata_backup.unlink(missing_ok=True)


def _scope_hash(scope: dict) -> str:
    content = {
        "repo_id": scope["repo_id"],
        "source_paths": scope["source_paths"],
        "semantic_paths": scope["semantic_paths"],
        "exclude_paths": scope["exclude_paths"],
    }
    return _sha256_bytes(
        json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _safe_relative(root: Path, configured: str, *, required_root: str | None = None) -> Path:
    relative = Path(configured)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("path must be a non-empty instance-relative path without '..'")
    if required_root and relative.parts[0] != required_root:
        raise ValueError(f"path must stay below {required_root}/")
    resolved = (root / relative).resolve()
    resolved.relative_to(root.resolve())
    return resolved


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, 127, "", type(exc).__name__)


def _git_value(repo: Path, *args: str) -> str | None:
    result = _git(repo, *args)
    value = result.stdout.strip().lower()
    return value if result.returncode == 0 else None


def _normalize_prefix(value: str) -> str:
    normalized = value.replace("\\", "/").strip("/")
    if not normalized or normalized == "." or normalized.startswith("../") or "/../" in normalized:
        raise ValueError("scope paths must be safe repository-relative prefixes")
    return normalized


def _matches_prefix(path: str, prefixes: list[str]) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)


def _load_scope(path: Path, root: Path) -> tuple[dict | None, list[str]]:
    try:
        scope = _read_json(path)
    except (OSError, json.JSONDecodeError):
        return None, ["scope manifest is missing, unreadable or invalid JSON"]
    errors = _validate(scope, "graphify-scope-manifest.schema.json", root)
    try:
        for key in ("source_paths", "semantic_paths", "exclude_paths"):
            scope[key] = [_normalize_prefix(value) for value in scope[key]]
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return scope, errors


def _load_metadata(path: Path, root: Path) -> tuple[dict | None, list[str]]:
    try:
        metadata = _read_json(path)
    except (OSError, json.JSONDecodeError):
        return None, ["artifact metadata is missing, unreadable or invalid JSON"]
    return metadata, _validate(metadata, "graphify-artifact-metadata.schema.json", root)


def _validate_graph(path: Path) -> tuple[dict | None, list[str]]:
    try:
        graph = _read_json(path)
    except (OSError, json.JSONDecodeError):
        return None, ["raw graph artifact is missing, unreadable or invalid JSON"]
    links = graph.get("links", graph.get("edges"))
    if not isinstance(graph.get("nodes"), list) or not isinstance(links, list):
        return None, ["raw graph artifact lacks nodes and links/edges arrays"]
    return graph, []


def _base_status() -> dict[str, Any]:
    return {
        "state": "blocked",
        "repo_id": None,
        "source_commit": None,
        "current_commit": None,
        "merge_base": None,
        "manifest_hash": None,
        "scope_hash": None,
        "changed_source_files": 0,
        "artifact_valid": False,
        "metadata_valid": False,
        "source_verification_required": True,
        "issue_kind": "invalid",
        "summary": "graph lifecycle validation has not completed",
    }


def evaluate_status(instance_root: Path, entry: dict, *, root: Path | None = None) -> dict:
    """Return a content-safe structural lifecycle status."""
    framework = (root or framework_root()).resolve()
    instance = instance_root.resolve()
    result = _base_status()
    try:
        artifact = _safe_relative(
            instance,
            entry.get("artifact_path", "graphify-out/graph.json"),
            required_root="graphify-out",
        )
        metadata_path = _safe_relative(
            instance,
            entry.get("metadata_path", "graphify-out/eif-graph-metadata.json"),
            required_root="graphify-out",
        )
        scope_path = _safe_relative(
            instance,
            entry.get("scope_manifest_path", ".eif/graphify-scope.json"),
        )
    except (TypeError, ValueError) as exc:
        result.update(issue_kind="config", summary=str(exc))
        return result

    scope, scope_errors = _load_scope(scope_path, framework)
    if scope_errors or scope is None:
        result.update(issue_kind="missing", summary=scope_errors[0])
        return result
    result["repo_id"] = scope["repo_id"]
    if scope["suppressed"]:
        result.update(
            state="suppressed",
            issue_kind="suppressed",
            summary="structural graph is explicitly suppressed; use source navigation",
        )
        return result

    metadata, metadata_errors = _load_metadata(metadata_path, framework)
    if metadata_errors or metadata is None:
        result.update(issue_kind="missing", summary=metadata_errors[0])
        return result
    result["metadata_valid"] = True
    result["source_commit"] = metadata["source_commit"]
    result["manifest_hash"] = metadata["manifest_hash"]
    result["scope_hash"] = metadata["scope_hash"]

    graph, graph_errors = _validate_graph(artifact)
    if graph_errors or graph is None:
        result.update(issue_kind="missing", summary=graph_errors[0])
        return result
    if _sha256_file(artifact) != metadata["graph_sha256"]:
        result.update(summary="raw graph digest does not match artifact metadata")
        return result
    result["artifact_valid"] = True

    current_manifest_hash = _sha256_file(scope_path)
    current_scope_hash = _scope_hash(scope)
    if metadata["repo_id"] != scope["repo_id"]:
        result.update(issue_kind="config", summary="metadata repo_id does not match the explicit scope manifest")
        return result
    override = entry.get("baseline_commit")
    if override is not None and override != metadata["source_commit"]:
        result.update(issue_kind="config", summary="baseline_commit conflicts with artifact metadata source_commit")
        return result

    current = _git_value(instance, "rev-parse", "HEAD")
    result["current_commit"] = current if current and FULL_SHA.fullmatch(current) else None
    if result["current_commit"] is None:
        result.update(summary="current Git commit is unavailable")
        return result

    source_commit = metadata["source_commit"]
    exists = _git(instance, "cat-file", "-e", f"{source_commit}^{{commit}}")
    if exists.returncode != 0:
        result.update(
            state="full-rebuild-required",
            issue_kind="history",
            summary="artifact source commit is not reachable in current history",
        )
        return result
    merge_base = _git_value(instance, "merge-base", source_commit, result["current_commit"])
    result["merge_base"] = merge_base if merge_base and FULL_SHA.fullmatch(merge_base) else None
    if result["merge_base"] != source_commit:
        result.update(
            state="full-rebuild-required",
            issue_kind="history",
            summary="artifact source commit is not an ancestor of current history",
        )
        return result

    if metadata["manifest_hash"] != current_manifest_hash or metadata["scope_hash"] != current_scope_hash:
        result.update(
            state="semantic-update-required",
            issue_kind="scope-drift",
            summary="scope manifest or semantic scope changed since graph capture",
        )
        return result

    changed = _git(instance, "diff", "--name-only", f"{source_commit}..{result['current_commit']}")
    if changed.returncode != 0:
        result.update(summary="Git could not enumerate source changes")
        return result
    changed_paths = [line.replace("\\", "/").strip("/") for line in changed.stdout.splitlines() if line.strip()]
    relevant = [
        path
        for path in changed_paths
        if _matches_prefix(path, scope["source_paths"])
        and not _matches_prefix(path, scope["exclude_paths"])
    ]
    result["changed_source_files"] = len(relevant)
    if not relevant:
        result.update(state="fresh", issue_kind="ok", summary="graph is fresh for its declared source scope")
    elif any(_matches_prefix(path, scope["semantic_paths"]) for path in relevant):
        result.update(
            state="semantic-update-required",
            issue_kind="source-drift",
            summary="semantic-scope source changed after graph capture",
        )
    else:
        result.update(
            state="code-update-required",
            issue_kind="source-drift",
            summary="structural source changed after graph capture",
        )
    return result


def capture_metadata(
    instance_root: Path,
    entry: dict,
    graphify_version: str,
    *,
    generated_at: str | None = None,
    root: Path | None = None,
) -> dict:
    framework = (root or framework_root()).resolve()
    instance = instance_root.resolve()
    artifact = _safe_relative(
        instance,
        entry.get("artifact_path", "graphify-out/graph.json"),
        required_root="graphify-out",
    )
    metadata_path = _safe_relative(
        instance,
        entry.get("metadata_path", "graphify-out/eif-graph-metadata.json"),
        required_root="graphify-out",
    )
    scope_path = _safe_relative(
        instance,
        entry.get("scope_manifest_path", ".eif/graphify-scope.json"),
    )
    scope, scope_errors = _load_scope(scope_path, framework)
    graph, graph_errors = _validate_graph(artifact)
    if scope_errors or scope is None:
        raise ValueError(scope_errors[0])
    if graph_errors or graph is None:
        raise ValueError(graph_errors[0])
    source_commit = _git_value(instance, "rev-parse", "HEAD")
    if source_commit is None or not FULL_SHA.fullmatch(source_commit):
        raise ValueError("current Git commit is unavailable")
    metadata = {
        "schema_version": 1,
        "repo_id": scope["repo_id"],
        "source_commit": source_commit,
        "graphify_version": graphify_version,
        "manifest_hash": _sha256_file(scope_path),
        "scope_hash": _scope_hash(scope),
        "graph_sha256": _sha256_file(artifact),
        "generated_at": generated_at or dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    errors = _validate(metadata, "graphify-artifact-metadata.schema.json", framework)
    if errors:
        raise ValueError(errors[0])
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    staged_metadata: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=metadata_path.parent,
            prefix=".eif-metadata-",
        ) as handle:
            handle.write(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
            staged_metadata = Path(handle.name)
        staged_metadata.replace(metadata_path)
    finally:
        if staged_metadata is not None:
            staged_metadata.unlink(missing_ok=True)
    return metadata


def restore_artifact(
    instance_root: Path,
    entry: dict,
    archive_path: Path,
    metadata_source: Path,
    *,
    root: Path | None = None,
) -> dict:
    """Validate an archive plus metadata, then replace each target from staging."""
    framework = (root or framework_root()).resolve()
    instance = instance_root.resolve()
    artifact = _safe_relative(
        instance,
        entry.get("artifact_path", "graphify-out/graph.json"),
        required_root="graphify-out",
    )
    metadata_target = _safe_relative(
        instance,
        entry.get("metadata_path", "graphify-out/eif-graph-metadata.json"),
        required_root="graphify-out",
    )
    scope_path = _safe_relative(
        instance,
        entry.get("scope_manifest_path", ".eif/graphify-scope.json"),
    )
    scope, scope_errors = _load_scope(scope_path, framework)
    metadata, metadata_errors = _load_metadata(metadata_source.resolve(), framework)
    if scope_errors or scope is None:
        raise ValueError(scope_errors[0])
    if metadata_errors or metadata is None:
        raise ValueError(metadata_errors[0])
    if metadata["repo_id"] != scope["repo_id"]:
        raise ValueError("metadata repo_id does not match the explicit scope manifest")
    if metadata["manifest_hash"] != _sha256_file(scope_path) or metadata["scope_hash"] != _scope_hash(scope):
        raise ValueError("metadata hashes do not match the current scope manifest")
    graph_bytes = _read_graph_archive(archive_path)
    if _sha256_bytes(graph_bytes) != metadata["graph_sha256"]:
        raise ValueError("archive graph digest does not match artifact metadata")
    try:
        graph = json.loads(graph_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("archive graph is not valid UTF-8 JSON") from exc
    links = graph.get("links", graph.get("edges"))
    if not isinstance(graph.get("nodes"), list) or not isinstance(links, list):
        raise ValueError("archive graph lacks nodes and links/edges arrays")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    metadata_target.parent.mkdir(parents=True, exist_ok=True)
    staged_graph: Path | None = None
    staged_metadata: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            delete=False,
            dir=artifact.parent,
            prefix=".eif-restore-graph-",
        ) as handle:
            handle.write(graph_bytes)
            staged_graph = Path(handle.name)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=metadata_target.parent,
            prefix=".eif-restore-metadata-",
        ) as handle:
            handle.write(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
            staged_metadata = Path(handle.name)
        _replace_pair_transactionally(
            staged_graph,
            artifact,
            staged_metadata,
            metadata_target,
        )
    finally:
        if staged_graph is not None:
            staged_graph.unlink(missing_ok=True)
        if staged_metadata is not None:
            staged_metadata.unlink(missing_ok=True)
    return evaluate_status(instance, entry, root=framework)


def _entry(args: argparse.Namespace) -> dict:
    return {
        "artifact_path": args.artifact_path,
        "metadata_path": args.metadata_path,
        "scope_manifest_path": args.scope_manifest_path,
    }


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--framework-root")
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("status", "capture-metadata", "restore"):
        command = sub.add_parser(name)
        command.add_argument("--instance-root", default=".")
        command.add_argument("--artifact-path", default="graphify-out/graph.json")
        command.add_argument("--metadata-path", default="graphify-out/eif-graph-metadata.json")
        command.add_argument("--scope-manifest-path", default=".eif/graphify-scope.json")
    capture = sub.choices["capture-metadata"]
    capture.add_argument("--graphify-version", required=True)
    capture.add_argument("--generated-at")
    restore = sub.choices["restore"]
    restore.add_argument("--archive", required=True)
    restore.add_argument("--metadata-source", required=True)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.framework_root).resolve() if args.framework_root else framework_root()
    entry = _entry(args)
    try:
        if args.command == "capture-metadata":
            result = capture_metadata(
                Path(args.instance_root),
                entry,
                args.graphify_version,
                generated_at=args.generated_at,
                root=root,
            )
        elif args.command == "restore":
            result = restore_artifact(
                Path(args.instance_root),
                entry,
                Path(args.archive),
                Path(args.metadata_source),
                root=root,
            )
        else:
            result = evaluate_status(Path(args.instance_root), entry, root=root)
    except (OSError, ValueError) as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.command == "capture-metadata":
        return 0
    return 0 if result.get("state") in {"fresh", "code-update-required", "semantic-update-required", "suppressed"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
