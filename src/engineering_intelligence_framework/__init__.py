"""Engineering Intelligence Framework - installable package.

A quality-first control plane for governed AI-agent software development.
See https://github.com/mike-arbuzov365/engineering-intelligence-framework
"""
from __future__ import annotations

from importlib import metadata

try:
    __version__ = metadata.version("engineering-intelligence-framework")
except metadata.PackageNotFoundError:
    # Running from a source checkout without an installed distribution
    # (e.g. `python -m engineering_intelligence_framework` against src/
    # directly during development, before `pip install -e .`).
    __version__ = "0.0.0+unknown"
