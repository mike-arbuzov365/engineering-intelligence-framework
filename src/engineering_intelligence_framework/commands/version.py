"""`eifctl version` - no underlying script to wrap, just package metadata."""
from __future__ import annotations

import sys

from .. import __version__


def run(argv: list[str]) -> int:
    del argv  # no arguments accepted
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"eifctl {__version__} (engineering-intelligence-framework), Python {python_version}")
    return 0
