"""`eifctl doctor` - thin wrapper over _impl.eif_verify_runtime.main()."""
from __future__ import annotations

from .._impl import eif_verify_runtime
from ..resources import framework_root


def run(argv: list[str]) -> int:
    with framework_root() as root:
        full_argv = ["--framework-root", str(root), *argv]
        return eif_verify_runtime.main(full_argv)
