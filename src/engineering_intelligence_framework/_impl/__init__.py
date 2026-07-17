"""Byte-for-byte synced copies of the framework's own scripts/eif_*.py
modules - see scripts/sync_package_sources.py, the single mechanism that
keeps them identical to their source of truth (verified by
scripts/tests/test_package_build.py, not just assumed).

These modules import each other with flat `from eif_xxx import yyy`
statements, unchanged from how they're written in scripts/ - inserting
this package's own directory onto sys.path here reproduces exactly what
Python already does automatically for `python scripts/eif_init.py`,
without needing to rewrite a single import in the synced copies.
"""
from __future__ import annotations

import sys
from pathlib import Path

_impl_dir = str(Path(__file__).resolve().parent)
if _impl_dir not in sys.path:
    sys.path.insert(0, _impl_dir)
