"""Resolves the packaged resources/ tree (core/schemas, core/ontology,
locales, templates - see scripts/sync_package_sources.py) to a real
filesystem path, the form every _impl script's `--framework-root` expects.

Uses `importlib.resources.as_file()`, which returns the real installed
path directly (no copying) for a normal wheel install - the common case -
and only falls back to extracting to a temporary directory for an
exotic distribution form (e.g. a zipimport/zipapp) where package data
isn't a real file on disk. Either way the caller gets a real `Path` valid
for the lifetime of the `with` block; this module's own
`framework_root()` context manager is that block.
"""
from __future__ import annotations

import contextlib
from collections.abc import Iterator
from importlib import resources
from pathlib import Path


@contextlib.contextmanager
def framework_root() -> Iterator[Path]:
    """Yields a real filesystem Path to the packaged framework resources
    (equivalent to a framework git checkout's own root, for the subset of
    it - core/schemas, core/ontology, locales, templates - the packaged
    CLI actually needs)."""
    traversable = resources.files("engineering_intelligence_framework") / "resources"
    with resources.as_file(traversable) as path:
        yield path
