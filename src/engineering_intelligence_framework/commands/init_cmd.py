"""`eifctl init` - thin wrapper over _impl.eif_init.main(). Its one real job
beyond dispatch: compute this installed package's own provenance (real
digests, never a fabricated stand-in for a git commit) and pass it to
eif_init as CLI args, so eif_init writes it into the SAME transaction as
config/runtime/lock/entrypoint/gitignore/index - never a second, unprotected
read-modify-write of the lock file after the fact. See
core/schemas/framework-lock.schema.json's discriminated `framework.source_type`
contract.
"""
from __future__ import annotations

import hashlib
import json
import sys
from importlib import metadata
from pathlib import Path

from .. import __version__
from .._impl import eif_init  # noqa: E402  (import triggers _impl/__init__.py's sys.path bootstrap)
from ..resources import framework_root

DISTRIBUTION_NAME = "engineering-intelligence-framework"


def _installed_wheel_sha256(distribution_name: str) -> str | None:
    """The real sha256 of the actual wheel/archive file this distribution was
    installed from, read from PEP 610's direct_url.json - present when pip
    installed from a local wheel path (the only way this project is
    installed pre-PyPI). Returns None - never a fabricated value - when
    direct_url.json is absent or lacks hash info (e.g. an editable/
    local-directory install, which has no discrete archive file to hash)."""
    try:
        dist = metadata.distribution(distribution_name)
        raw = dist.read_text("direct_url.json")
    except (metadata.PackageNotFoundError, FileNotFoundError):
        return None
    if raw is None:
        return None
    try:
        direct_url = json.loads(raw)
    except json.JSONDecodeError:
        return None
    archive_info = direct_url.get("archive_info")
    if not isinstance(archive_info, dict):
        return None
    hashes = archive_info.get("hashes")
    if isinstance(hashes, dict) and "sha256" in hashes:
        return hashes["sha256"]
    hash_field = archive_info.get("hash")
    if isinstance(hash_field, str) and hash_field.startswith("sha256="):
        return hash_field.split("=", 1)[1]
    return None


def _resource_manifest_digest(resources_root: Path) -> str:
    """Combined sha256 over every file actually present in the installed
    package's bundled resources/ tree right now, sorted (relative path,
    sha256) pairs - same combined-digest pattern as eif_init.py's own
    bundle.digest. Always computable (unlike wheel_sha256): this is a
    live filesystem read, not install-metadata that may be absent."""
    entries = []
    for f in sorted(
        p for p in resources_root.rglob("*")
        if eif_init.is_portable_resource_file(p)
    ):
        rel = f.relative_to(resources_root).as_posix()
        entries.append((rel, hashlib.sha256(f.read_bytes()).hexdigest()))
    h = hashlib.sha256()
    for rel, file_hash in entries:
        h.update(f"{rel}:{file_hash}\n".encode("utf-8"))
    return f"sha256:{h.hexdigest()}"


HELP = """\
`eifctl init` - initialize or adopt one EIF project instance in place.

Usage:
    eifctl init [PATH] [--project-name NAME] [--adapter ADAPTER]
                [--locale {en,uk}] [--adoption-mode {greenfield,coexist}]
                [--knowledge-root PATH] [--dry-run] [--force]

PATH is the project to initialize, and may also be given as
--instance-path PATH. It defaults to the current directory. --project-name
defaults to that directory's name on a first-ever init and is derived from
the existing config on every later run.

--framework-root is not accepted here: the installed package IS the
framework source, and eifctl passes its own provenance through. The
standalone `python scripts/eif_init.py --framework-root ... ` form still
takes it, and still works unchanged.

Re-running against an existing instance is a routine upgrade: it preserves
.eif/config.yaml byte for byte and refreshes only the lock, the pinned
runtime and the managed entrypoint/.gitignore/.gitattributes blocks. Pass
--force only for a deliberate reconfiguration.

Every other flag is passed through to the shared implementation; see
`python -m engineering_intelligence_framework._impl.eif_init --help` for the
full list.
"""


def _normalize_target(argv: list[str]) -> tuple[list[str], Path]:
    """Accept `eifctl init PATH` alongside `--instance-path PATH`.

    Every other path-taking eifctl command (`new`, `projects add`,
    `projects detach`, `workspace new`) takes its target positionally, the
    documented quickstart used the positional form, and the underlying
    eif_init parser rejected it outright with `unrecognized arguments`. The
    two forms are equivalent here; passing both with different targets is an
    error rather than a silent winner."""
    positional: str | None = None
    rest = list(argv)
    if rest and not rest[0].startswith("-"):
        positional = rest.pop(0)
    if "--instance-path" in rest:
        flag_value = rest[rest.index("--instance-path") + 1]
        if positional is not None and Path(positional).resolve() != Path(flag_value).resolve():
            raise ValueError(
                f"target given twice and they differ: {positional!r} and "
                f"--instance-path {flag_value!r}"
            )
        return rest, Path(flag_value).resolve()
    if positional is not None:
        return [*rest, "--instance-path", positional], Path(positional).resolve()
    return [*rest, "--instance-path", "."], Path(".").resolve()


def run(argv: list[str]) -> int:
    if "-h" in argv or "--help" in argv:
        print(HELP)
        return 0
    try:
        argv, target = _normalize_target(argv)
    except (ValueError, IndexError) as exc:
        print(f"eifctl init: {exc}", file=sys.stderr)
        return 2

    # `eifctl new` already defaults the project name to the directory name;
    # requiring it here only for `init` made the documented one-liner fail on
    # its second run at the user. Only a first-ever init consumes it: a
    # routine upgrade derives the name from the existing config and prints a
    # note for any flag it ignores.
    if not (target / ".eif" / "config.yaml").exists() and "--project-name" not in argv:
        argv = [*argv, "--project-name", target.name]

    with framework_root() as root:
        package_args = [
            "--package-distribution", DISTRIBUTION_NAME,
            "--package-version", __version__,
            "--package-python-version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "--package-resource-manifest-digest", _resource_manifest_digest(root),
        ]
        wheel_sha256 = _installed_wheel_sha256(DISTRIBUTION_NAME)
        if wheel_sha256 is not None:
            package_args += ["--package-wheel-sha256", wheel_sha256]

        return eif_init.main(["--framework-root", str(root), *package_args, *argv])
