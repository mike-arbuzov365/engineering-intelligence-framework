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
anticipate).

Shell-safety (independent-review finding): these configured values are
interpolated into commands the generated CLAUDE.md tells an agent to run
in a real shell, so the path text itself must be shell-safe, not just
schema-valid. The policy is a strict ALLOWLIST - letters, digits, and
`/ \ . _ -` plus spaces - and nothing else. Spaces are allowed (a
legitimate directory name can contain them), but ONLY because generated
commands quote every interpolated path; a space with an unquoted command
would split into two arguments, so the two changes ship together. Every
other character - quotes, backticks, `$`, `%`, `;`, `&`, `|`, `<`, `>`,
`(` `)`, `{` `}`, glob metacharacters, control characters, newlines - is
rejected before anything is written, because there is no safe way to
interpolate it into a cross-platform shell command. This is defense in
depth even with quoting: a value containing a literal `"` or backtick or
`$(...)` could break out of the quotes on at least one supported shell.
"""
from __future__ import annotations

import re
from pathlib import Path

_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_UNC_RE = re.compile(r"^[\\/]{2}")
# Strict allowlist: alnum, forward/back slash, dot, underscore, hyphen,
# space. Everything else is a potential shell metacharacter and is
# rejected. Checked against the RAW value (before slash-normalization) so
# a stray backslash is treated as a Windows separator, nothing more.
# Deliberately anchored with fullmatch (below), NOT `$` - `$` in Python
# regex also matches just before a TRAILING newline, so `^...$` would let
# a path ending in "\n" through; fullmatch has no such hole.
_SAFE_PATH_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ._/\\-")


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
    # Shell-safety allowlist (independent-review finding): reject any
    # character that could act as a shell metacharacter when this path is
    # interpolated into a generated command. Runs AFTER the more specific
    # checks above so an absolute/drive/UNC path gets its own clearer
    # message, not this generic one.
    bad = sorted({c for c in raw if c not in _SAFE_PATH_CHARS})
    if bad:
        bad_display = [repr(c) if c.isprintable() else f"U+{ord(c):04X}" for c in bad]
        raise PathPolicyError(
            f"{label}: contains character(s) not allowed in a configured path "
            f"({', '.join(bad_display)}) - only letters, digits, and '/ \\ . _ -' plus "
            f"spaces are allowed, so the value is safe to quote into a shell command "
            f"({raw!r})"
        )

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
