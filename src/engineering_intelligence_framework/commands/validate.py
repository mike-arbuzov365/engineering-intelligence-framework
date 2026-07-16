"""`eifctl validate` - thin wrapper over _impl.eif_validate_frontmatter.main().

--instance-root defaults to "." (the user's project) here explicitly -
the underlying script's own default is "same as --framework-root", which
would be wrong once --framework-root is auto-pointed at the packaged
resources instead of a project checkout.
"""
from __future__ import annotations

from .._impl import eif_validate_frontmatter
from ..resources import framework_root


def run(argv: list[str]) -> int:
    with framework_root() as root:
        full_argv = ["--framework-root", str(root), *argv]
        if "--instance-root" not in full_argv:
            full_argv = [*full_argv, "--instance-root", "."]
        return eif_validate_frontmatter.main(full_argv)
