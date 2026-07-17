"""`eifctl privacy-scan` - thin wrapper over _impl.eif_privacy_scan.main().

No --framework-root involved: eif_privacy_scan.py only ever scans --repo
(default ".", the user's own project), never the framework's own bundled
resources.
"""
from __future__ import annotations

from .._impl import eif_privacy_scan


def run(argv: list[str]) -> int:
    return eif_privacy_scan.main(argv)
