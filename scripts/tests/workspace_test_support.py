"""Shared synthetic setup helpers for private-workspace tests."""
from __future__ import annotations

import subprocess
from pathlib import Path

import yaml


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def commit_all(root: Path, message: str) -> None:
    added = git(root, "add", "-A")
    if added.returncode != 0:
        raise RuntimeError(added.stdout + added.stderr)
    committed = git(
        root,
        "-c",
        "user.name=EIF Test",
        "-c",
        "user.email=eif-test@example.invalid",
        "commit",
        "-m",
        message,
    )
    if committed.returncode != 0:
        raise RuntimeError(committed.stdout + committed.stderr)


def write_profile(workspace: Path, artifacts: list[dict]) -> None:
    profile = {
        "schema_version": 1,
        "name": "default",
        "description": "Synthetic workspace profile.",
        "framework": {"requires": ">=0.2.0,<0.3.0"},
        "artifacts": artifacts,
    }
    (workspace / "workspace" / "profiles" / "default.yaml").write_text(
        yaml.safe_dump(profile, sort_keys=False),
        encoding="utf-8",
    )


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): (
            path.read_bytes() if path.is_file() else b"<DIR>"
        )
        for path in sorted(root.rglob("*"))
        if ".git" not in path.relative_to(root).parts
    }
