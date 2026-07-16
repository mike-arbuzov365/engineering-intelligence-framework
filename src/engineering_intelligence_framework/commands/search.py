"""`eifctl search` - thin wrapper over _impl.eif_search_knowledge.main().

--knowledge-root is required by the underlying script but optional here -
defaults to "knowledge" (the same default eif_init.py uses for a new
greenfield instance) so `eifctl search "query"` works out of the box in a
project that never overrode it.
"""
from __future__ import annotations

from .._impl import eif_search_knowledge
from ..resources import framework_root


def run(argv: list[str]) -> int:
    with framework_root() as root:
        full_argv = ["--framework-root", str(root), *argv]
        if "--knowledge-root" not in full_argv:
            full_argv = ["--knowledge-root", "knowledge", *full_argv]
        return eif_search_knowledge.main(full_argv)
