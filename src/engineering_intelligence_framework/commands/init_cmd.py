"""`eifctl init` - thin wrapper over _impl.eif_init.main(), plus one
package-specific enrichment step eif_init.py itself has no reason to know
about: recording installed-package provenance (distribution, version,
source_type, python_version) into the lock file it just wrote. See
core/schemas/framework-lock.schema.json's optional `package` object.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import yaml

from .. import __version__
from .._impl import eif_init  # noqa: E402  (import triggers _impl/__init__.py's sys.path bootstrap)
from ..resources import framework_root

DISTRIBUTION_NAME = "engineering-intelligence-framework"


def _synthetic_ref(version: str) -> str:
    """A deterministic, schema-valid (40-hex, like a real git SHA-1) stand-in
    for framework.ref when the source is an installed package, not a git
    checkout - there is no real commit to report. Reproducible from the
    version string alone, so the same release always asserts the same ref."""
    return hashlib.sha1(f"eifctl-package:{version}".encode("utf-8")).hexdigest()


def _enrich_lock_with_package_provenance(instance_path: Path) -> None:
    lock_path = instance_path / ".eif" / "framework.lock.yaml"
    if not lock_path.exists():
        return  # --dry-run or a run that didn't reach the write step
    data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    data["package"] = {
        "distribution": DISTRIBUTION_NAME,
        "version": __version__,
        "source_type": "installed-package",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
    lock_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def run(argv: list[str]) -> int:
    with framework_root() as root:
        full_argv = ["--framework-root", str(root), "--framework-ref", _synthetic_ref(__version__), *argv]
        if "--instance-path" not in full_argv:
            full_argv = [*full_argv, "--instance-path", "."]
        rc = eif_init.main(full_argv)
        if rc == 0:
            instance_path_str = full_argv[full_argv.index("--instance-path") + 1]
            _enrich_lock_with_package_provenance(Path(instance_path_str).resolve())
        return rc
