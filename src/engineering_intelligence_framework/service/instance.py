"""An explicitly bound instance and its contained, named sources."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path, PureWindowsPath
from typing import Any, NotRequired, TypedDict

import yaml

from ..commands import session


class Result(TypedDict):
    status: str
    data: dict[str, Any]
    truncated: NotRequired[bool]
    next_cursor: NotRequired[str]
    next_action: NotRequired[str]


class ServiceError(ValueError):
    def __init__(self, code: str, message: str, *, status: str = "unavailable", retryable: bool = False):
        super().__init__(message)
        self.code, self.status, self.retryable = code, status, retryable


def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) or ".." in value:
        raise ServiceError("validation_failed", "Use a bounded identifier, not a path.")
    return value


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class Instance:
    """Never discovers another root or follows a source outside this root."""

    def __init__(self, root: Path, packets_root: str = "planning/packets"):
        self.root = root.expanduser().resolve()
        if not self.root.is_dir():
            raise ServiceError("validation_failed", "An existing EIF instance is required.")
        self.packets_root = packets_root
        self.safe(packets_root)
        self.cursors: dict[str, dict[str, Any]] = {}
        self.refresh()

    def safe(self, relative: str | Path) -> Path:
        raw = str(relative).replace("\\", "/")
        parts = raw.split("/")
        if not raw or Path(raw).is_absolute() or PureWindowsPath(raw).drive or any(part in {"..", ".git", *session.SECRET_SOURCE_NAMES} or part.casefold().startswith(".env") or ":" in part for part in (p.casefold() for p in parts)):
            raise ServiceError("validation_failed", "Source is outside the permitted instance boundary.")
        candidate = self.root / raw
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.root):
            raise ServiceError("source_unavailable", "Source resolves outside the instance boundary.")
        if any(p.casefold() in {".git", *session.SECRET_SOURCE_NAMES} or p.casefold().startswith(".env") for p in resolved.relative_to(self.root).parts):
            raise ServiceError("source_unavailable", "Source resolves to a prohibited file.")
        return candidate

    def read(self, relative: str | Path, limit: int = 2_097_152) -> bytes:
        path = self.safe(relative)
        if not path.is_file():
            raise ServiceError("source_unavailable", "A required regular source file is unavailable.")
        try:
            with path.open("rb") as stream:
                content = stream.read(limit + 1)
        except OSError:
            raise ServiceError("source_unavailable", "A required instance source is unavailable.") from None
        if len(content) > limit:
            raise ServiceError("source_unavailable", "Source exceeds the bounded reader limit.")
        return content

    def mapping(self, relative: str) -> dict[str, Any]:
        try:
            data = yaml.safe_load(self.read(relative))
        except (yaml.YAMLError, UnicodeError):
            raise ServiceError("validation_failed", "Instance metadata is invalid.") from None
        if not isinstance(data, dict):
            raise ServiceError("validation_failed", "Instance metadata must be a mapping.")
        return data

    def refresh(self) -> None:
        self.read(".eif/config.yaml", 262_144)
        self.read(".eif/framework.lock.yaml", 2_097_152)
        try:
            self.project = session._load_project(self.root)
        except (ValueError, OSError, yaml.YAMLError):
            raise ServiceError("validation_failed", "Config and framework lock must pass the EIF schemas.") from None
        self.config = self.mapping(".eif/config.yaml")
        self.lock = self.mapping(".eif/framework.lock.yaml")
        self.workspace = self.mapping(".eif/workspace.lock.yaml") if self.safe(".eif/workspace.lock.yaml").exists() else {}
        if self.workspace:
            from ..workspace_contract import validate_data
            try:
                validate_data(self.workspace, "workspace-lock.schema.json", "workspace lock")
            except ValueError:
                raise ServiceError("validation_failed", "Workspace lock must pass its EIF schema.") from None

    def guard_tree(self, relative: str, *, max_files: int = 5000) -> list[Path]:
        """Preflight existing legacy tree readers without following unsafe links."""
        root = self.safe(relative)
        found: list[Path] = []
        pending = [root]
        seen: set[Path] = set()
        total = 0
        while pending:
            directory = pending.pop()
            resolved = directory.resolve()
            if resolved in seen:
                raise ServiceError("source_unavailable", "Source tree contains a directory cycle.")
            seen.add(resolved)
            try:
                entries = list(os.scandir(directory))
            except OSError:
                raise ServiceError("source_unavailable", "Source tree is unavailable.") from None
            for entry in entries:
                path = self.safe(Path(entry.path).relative_to(self.root))
                if path.is_dir():
                    pending.append(path)
                elif path.is_file():
                    total += path.stat().st_size
                    found.append(path)
                    if len(found) > max_files or total > 20_971_520:
                        raise ServiceError("source_unavailable", "Source tree exceeds reader limits.")
        return found

    def manifest(self) -> list[dict[str, Any]]:
        from .._impl.eif_verify_runtime import check_manifest_digest
        from .._impl.eif_init import combined_digest
        if check_manifest_digest(self.lock):
            raise ServiceError("version_conflict", "Framework manifest digest is inconsistent.", status="stale")
        if self.workspace and combined_digest((self.workspace.get("bundle") or {}).get("manifest", [])) != (self.workspace.get("bundle") or {}).get("digest"):
            raise ServiceError("version_conflict", "Workspace manifest digest is inconsistent.", status="stale")
        entries: list[dict[str, Any]] = []
        if (self.lock.get("bundle") or {}).get("path") != ".eif/runtime":
            raise ServiceError("source_unavailable", "The framework runtime must use its canonical instance path.")
        for prefix, lock in ((".eif/runtime", self.lock), (".eif/workspace-runtime", self.workspace)):
            for item in (lock.get("bundle") or {}).get("manifest", []):
                if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                    raise ServiceError("validation_failed", "Invalid runtime manifest entry.")
                self.safe(f"{prefix}/{item['path']}")
                entries.append({**item, "relative": f"{prefix}/{item['path']}"})
        return entries

    def artifacts(self) -> list[dict[str, Any]]:
        result = []
        for item in self.manifest():
            parts = item["path"].split("/")
            kind = {"skills": "skill", "playbooks": "playbook", "templates": "template", "rules": "rule"}.get(parts[0])
            if kind == "skill" and len(parts) == 3 and parts[-1] == "SKILL.md":
                name = parts[1]
            elif kind != "skill" and kind and len(parts) == 2 and parts[1].endswith(".md"):
                name = parts[1][:-3]
            else:
                continue
            result.append({**item, "kind": kind, "name": name})
        return result

    def artifact(self, kind: str, name: str) -> tuple[dict[str, Any], str]:
        identifier(name)
        matches = [item for item in self.artifacts() if item["kind"] == kind and item["name"] == name]
        if not matches:
            raise ServiceError("not_found", "The named artifact is not in the pinned manifests.")
        if len(matches) != 1:
            raise ServiceError("source_unavailable", "The named artifact is ambiguous across pinned sources.")
        item = matches[0]
        raw = self.read(item["relative"])
        if digest(raw) != item.get("sha256"):
            raise ServiceError("version_conflict", "Pinned artifact hash differs from its manifest.", status="stale")
        try:
            return item, raw.decode("utf-8")
        except UnicodeError:
            raise ServiceError("source_unavailable", "Pinned artifact is not UTF-8.") from None
