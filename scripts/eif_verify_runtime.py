#!/usr/bin/env python3
"""Integrity and consistency check for an EIF project instance ("doctor").

Bundled into every instance (`.eif/runtime/eif_verify_runtime.py`) and
referenced from the generated CLAUDE.md, so an instance can audit its own
state without a framework checkout.

Checks, each independently reported:

  1. config schema      - .eif/config.yaml validates
  2. lock schema         - .eif/framework.lock.yaml validates
  3. manifest digest      - the lock's own combined digest matches a fresh
                            recompute over its manifest (self-consistency)
  4. bundle file hashes   - every manifested file's current sha256 matches
                            the lock (catches hand-edits or partial upgrades)
  5. missing managed files    - a manifested path that no longer exists
  6. unexpected managed files - a file under .eif/runtime/ NOT in the
                            manifest. README.md and __pycache__/ are
                            classified separately (known, by-design
                            incidental output - see stage_bundle() in
                            eif_init.py) - anything else is flagged as a
                            real integrity concern, not silently ignored.
  7. config/adapter/lock/entrypoint consistency (see check_consistency())
  8. provenance state    - dirty / asserted, surfaced, not just recorded
  9. marker integrity     - CLAUDE.md and .gitignore's managed blocks are
                            each a single well-formed BEGIN/END pair

Usage:
    python eif_verify_runtime.py --framework-root PATH [--instance-path PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eif_adapters import ADAPTERS, entrypoint_for  # noqa: E402
from eif_markers import check_marker_integrity  # noqa: E402
from eif_validate_frontmatter import load_schema, validate_one, _normalize_yaml_scalars  # noqa: E402

try:
    import yaml
except ImportError:
    print(
        "eif-verify-runtime: PyYAML is required. Install with: "
        "pip install -r scripts/requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(1)

EIF_BEGIN = "<!-- EIF:BEGIN"
EIF_END = "<!-- EIF:END -->"
GITIGNORE_BEGIN = "# EIF:BEGIN gitignore"
GITIGNORE_END = "# EIF:END gitignore"

# Files that legitimately exist under .eif/runtime/ but are NOT in the
# manifest - by design (see eif_init.py's stage_bundle()), not an oversight.
KNOWN_UNMANIFESTED_NAMES = {"README.md"}
KNOWN_UNMANIFESTED_DIR_NAMES = {"__pycache__"}


class Report:
    def __init__(self):
        self.sections: list[tuple[str, list[str]]] = []

    def add(self, title: str, problems: list[str]) -> None:
        self.sections.append((title, problems))

    def print(self) -> bool:
        ok = True
        for title, problems in self.sections:
            if problems:
                ok = False
                print(f"FAIL {title}")
                for p in problems:
                    print(f"  - {p}")
            else:
                print(f"ok   {title}")
        return ok


def _load_yaml(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return _normalize_yaml_scalars(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    except yaml.YAMLError:
        return None


def check_schema(framework_root: Path, path: Path, schema_rel: str, label: str) -> list[str]:
    if not path.exists():
        return [f"missing: {path}"]
    data = _load_yaml(path)
    if data is None:
        return [f"invalid YAML: {path}"]
    schema = load_schema(framework_root / "core" / "schemas" / schema_rel)
    errors = validate_one(data, schema, label)
    return errors


def check_manifest_digest(lock: dict) -> list[str]:
    manifest = lock.get("bundle", {}).get("manifest", [])
    stored_digest = lock.get("bundle", {}).get("digest", "")
    h = hashlib.sha256()
    for entry in sorted(manifest, key=lambda e: e["path"]):
        h.update(f"{entry['path']}:{entry['sha256']}\n".encode("utf-8"))
    recomputed = f"sha256:{h.hexdigest()}"
    if recomputed != stored_digest:
        return [f"manifest digest mismatch: lock says {stored_digest}, recomputed {recomputed} "
                f"(the manifest list itself was edited or is out of order)"]
    return []


def check_bundle_files(instance_path: Path, lock: dict) -> tuple[list[str], list[str], list[str]]:
    """Returns (hash_mismatches, missing, unexpected)."""
    bundle_path = instance_path / lock.get("bundle", {}).get("path", ".eif/runtime")
    manifest = lock.get("bundle", {}).get("manifest", [])
    manifested_paths = {e["path"] for e in manifest}

    hash_mismatches, missing = [], []
    for entry in manifest:
        f = bundle_path / entry["path"]
        if not f.exists():
            missing.append(entry["path"])
            continue
        actual = hashlib.sha256(f.read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            hash_mismatches.append(entry["path"])

    unexpected = []
    if bundle_path.is_dir():
        for f in sorted(bundle_path.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(bundle_path).as_posix()
            if rel in manifested_paths:
                continue
            if f.name in KNOWN_UNMANIFESTED_NAMES:
                continue
            if any(part in KNOWN_UNMANIFESTED_DIR_NAMES for part in f.relative_to(bundle_path).parts):
                continue
            unexpected.append(rel)

    return hash_mismatches, missing, unexpected


def check_consistency(config: dict | None, lock: dict | None) -> list[str]:
    """config <-> adapter registry <-> lock <-> entrypoint. See module
    docstring item 7 / the round-3 review's Finding D."""
    problems = []
    if config is None or lock is None:
        return ["cannot check consistency: config or lock missing/invalid"]

    cfg_adapter = (config.get("adapter") or {}).get("name")
    lock_adapter = (lock.get("adapter") or {}).get("name")
    lock_entrypoint = (lock.get("adapter") or {}).get("entrypoint")

    if cfg_adapter not in ADAPTERS:
        problems.append(f"config adapter.name {cfg_adapter!r} is not in the adapter registry (scripts/eif_adapters.py)")
    if cfg_adapter != lock_adapter:
        problems.append(f"config adapter.name ({cfg_adapter!r}) != lock adapter.name ({lock_adapter!r})")
    if lock_adapter in ADAPTERS and lock_entrypoint != entrypoint_for(lock_adapter):
        problems.append(f"lock adapter.entrypoint ({lock_entrypoint!r}) != the registered entrypoint for {lock_adapter!r} ({entrypoint_for(lock_adapter)!r})")

    migration_status = (lock.get("instance") or {}).get("migration_status")
    if migration_status not in ("greenfield", "adopted"):
        problems.append(f"lock instance.migration_status is missing or invalid: {migration_status!r}")

    return problems


def check_provenance(lock: dict | None) -> list[str]:
    if lock is None:
        return ["cannot check provenance: lock missing/invalid"]
    fw = lock.get("framework", {})
    notes = []
    if fw.get("dirty"):
        notes.append(f"framework was DIRTY when this bundle was generated (ref {fw.get('ref_short', '?')}) - "
                     f"the recorded ref does not exactly match what was materialized")
    if fw.get("ref_verification") == "asserted":
        notes.append(f"framework ref ({fw.get('ref_short', '?')}) was ASSERTED via --framework-ref, "
                     f"not git-verified - provenance is only as trustworthy as whoever passed that flag")
    return notes  # informational, not failures - reported but does not flip overall ok to False


def check_markers(instance_path: Path, entrypoint: str) -> list[str]:
    problems = []
    entry_path = instance_path / entrypoint
    if entry_path.exists():
        problems.extend(
            f"{entrypoint}: {p}" for p in check_marker_integrity(entry_path.read_text(encoding="utf-8"), EIF_BEGIN, EIF_END)
        )
    gi_path = instance_path / ".gitignore"
    if gi_path.exists():
        problems.extend(
            f".gitignore: {p}" for p in check_marker_integrity(gi_path.read_text(encoding="utf-8"), GITIGNORE_BEGIN, GITIGNORE_END)
        )
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--framework-root", required=True, help="Where core/schemas/ lives (the framework checkout, or this instance's own .eif/runtime bundle)")
    ap.add_argument("--instance-path", default=".", help="Instance root to verify. Default: current directory.")
    args = ap.parse_args()

    framework_root = Path(args.framework_root).resolve()
    instance_path = Path(args.instance_path).resolve()

    report = Report()

    config_path = instance_path / ".eif" / "config.yaml"
    lock_path = instance_path / ".eif" / "framework.lock.yaml"
    config = _load_yaml(config_path)
    lock = _load_yaml(lock_path)

    report.add("config schema (.eif/config.yaml)", check_schema(framework_root, config_path, "eif-config.schema.json", str(config_path)))
    report.add("lock schema (.eif/framework.lock.yaml)", check_schema(framework_root, lock_path, "framework-lock.schema.json", str(lock_path)))

    if lock is not None:
        report.add("manifest digest self-consistency", check_manifest_digest(lock))
        hash_mismatches, missing, unexpected = check_bundle_files(instance_path, lock)
        report.add("bundle file hashes", [f"hash mismatch (file changed since generation): {p}" for p in hash_mismatches])
        report.add("missing managed files", [f"manifested but missing on disk: {p}" for p in missing])
        report.add("unexpected managed files (outside manifest, not README.md/__pycache__)", unexpected)

    report.add("config/adapter/lock/entrypoint consistency", check_consistency(config, lock))

    provenance_notes = check_provenance(lock)
    if provenance_notes:
        print("note: provenance")
        for n in provenance_notes:
            print(f"  - {n}")

    entrypoint = (lock.get("adapter") or {}).get("entrypoint", "CLAUDE.md") if lock else "CLAUDE.md"
    report.add("marker integrity (CLAUDE.md, .gitignore)", check_markers(instance_path, entrypoint))

    ok = report.print()
    print(f"\neif-verify-runtime: {'all checks passed' if ok else 'FAILED - see above'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
