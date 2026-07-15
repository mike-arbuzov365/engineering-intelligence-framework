#!/usr/bin/env python3
"""Shared instance-relative path policy for user-configured paths
(knowledge.root, knowledge.index_path) - independent-review finding: a
JSON Schema `pattern` on these fields is not enough, since a schema can
only reject shapes it can express in a regex, and cannot check the
resolved filesystem result at all. This module is the runtime check that
actually matters: does this configured path, once resolved, stay inside
the instance it was configured for?

Rejected outright, regardless of schema: absolute POSIX paths, Windows
drive paths, UNC paths, `..` traversal, and - the check none of the
others can substitute for - a resolved path that lands outside
instance_path even without any of the above (e.g. a deep symlink, or a
technically-relative path this module's own string checks didn't
anticipate). Spaces are explicitly ALLOWED (a legitimate directory name
can contain them) - the policy is that generated commands must quote
them, not that the path itself is rejected; see templates/agent-
instructions.md's use of these values.
"""
from __future__ import annotations

import re
from pathlib import Path

_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_UNC_RE = re.compile(r"^[\\/]{2}")


class PathPolicyError(ValueError):
    """A configured instance-relative path violates the path policy -
    the caller must refuse to write anything, not fall back to a
    sanitized or truncated version of the path."""


def validate_instance_relative_path(raw: str, instance_path: Path, label: str) -> Path:
    """Returns the resolved absolute Path if `raw` is a safe instance-
    relative path. Raises PathPolicyError otherwise. `instance_path` must
    already exist (callers resolve it from --instance-path before this
    is ever called)."""
    if raw is None or not str(raw).strip():
        raise PathPolicyError(f"{label}: must not be empty")
    raw = str(raw)
    normalized = raw.replace("\\", "/")

    if normalized.startswith("/"):
        raise PathPolicyError(f"{label}: absolute paths are not allowed ({raw!r})")
    if _WINDOWS_DRIVE_RE.match(raw):
        raise PathPolicyError(f"{label}: Windows drive paths are not allowed ({raw!r})")
    if _UNC_RE.match(raw):
        raise PathPolicyError(f"{label}: UNC paths are not allowed ({raw!r})")
    if any(part == ".." for part in normalized.split("/")):
        raise PathPolicyError(f"{label}: '..' path traversal is not allowed ({raw!r})")

    instance_resolved = instance_path.resolve()
    candidate = (instance_path / raw).resolve()
    try:
        candidate.relative_to(instance_resolved)
    except ValueError:
        raise PathPolicyError(
            f"{label}: resolves outside the instance root ({raw!r} -> {candidate}, "
            f"instance root is {instance_resolved})"
        )
    return candidate


def validate_index_inside_root(knowledge_index_path: str, knowledge_root: str, label: str = "knowledge.index_path") -> None:
    """knowledge.index_path must live inside knowledge.root - independent-
    review requirement. Compares the normalized relative strings, not
    resolved absolute paths, so this check works even before
    instance_path exists (e.g. for pure config-value validation)."""
    root_norm = knowledge_root.replace("\\", "/").rstrip("/")
    index_norm = knowledge_index_path.replace("\\", "/")
    if not (index_norm == root_norm or index_norm.startswith(root_norm + "/")):
        raise PathPolicyError(
            f"{label} ({knowledge_index_path!r}) must be inside knowledge.root ({knowledge_root!r})"
        )
