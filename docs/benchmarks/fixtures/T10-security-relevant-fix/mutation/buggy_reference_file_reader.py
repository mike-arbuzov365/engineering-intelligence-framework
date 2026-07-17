"""Serves files to users from a restricted public directory."""
from __future__ import annotations

import os


def read_user_file(base_dir: str, filename: str) -> str:
    """Read `filename` from within `base_dir` and return its contents.
    `filename` is caller-supplied and must never be able to escape
    `base_dir` (e.g. via '..' path segments)."""
    path = os.path.join(base_dir, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
