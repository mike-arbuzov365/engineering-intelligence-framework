"""`eifctl render` - thin wrapper over _impl.eif_render.main()."""
from __future__ import annotations

from .._impl import eif_render
from ..resources import framework_root


def run(argv: list[str]) -> int:
    with framework_root() as root:
        full_argv = ["--framework-root", str(root), *argv]
        return eif_render.main(full_argv)
