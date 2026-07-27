#!/usr/bin/env python3
"""Sync the canonical scripts/*.py implementation and framework resource
trees into src/engineering_intelligence_framework/ - the single mechanism
that keeps the installable package's bundled copies byte-for-byte identical
to their scripts/ source of truth, so "thin adapter, don't fork business
logic" is a checked fact, not a promise. Re-run this after any change to
one of the source files/trees listed below, then commit both the source
change and the synced copy together.

Copies verbatim (no text transformation): every _impl module keeps its own
original `from eif_xxx import yyy` flat-import statements unchanged - the
package's `_impl/__init__.py` puts `_impl/`'s own directory on `sys.path`
at import time (exactly what Python does automatically for
`python scripts/eif_init.py` today), so the copied files behave
identically without needing rewritten imports.

Usage:
    python scripts/sync_package_sources.py [--check]

--check: verify the package copies already match their sources byte-for-
byte (used by scripts/tests/test_package_build.py and CI); exits 1 and
prints exactly what's out of sync without writing anything.
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = FRAMEWORK_ROOT / "src" / "engineering_intelligence_framework"

sys.path.insert(0, str(FRAMEWORK_ROOT / "scripts"))
from eif_init import BUNDLE_SCRIPTS  # noqa: E402 - single source of truth for what eif_init.py itself bundles into a project instance's .eif/runtime/; read, not re-typed here.

# Every _impl module actually needed by the 6 non-trivial eifctl
# subcommands (init, doctor, search, render, privacy-scan, validate) -
# `version` needs none. Deliberately NOT the full BUNDLE_SCRIPTS list
# (that list is for project-instance bundling, a different concern) -
# see eif_init.py's own BUNDLE_SCRIPTS/BUNDLE_TREES for that mechanism.
IMPL_SCRIPTS = [
    "eif_init.py",
    "eif_verify_runtime.py",
    "eif_integrations.py",
    "eif_graphify.py",
    "eif_search_knowledge.py",
    "eif_render.py",
    "eif_privacy_scan.py",
    "eif_validate_frontmatter.py",
    "eif_generate_index.py",
    "eif_preflight.py",
    "eif_paths.py",
    "eif_adapters.py",
    "eif_markers.py",
    "eif_locale.py",
]

# Standalone verification tools that are part of the published framework
# contract but are not eifctl subcommands and must not be installed into every
# initialized project's .eif/runtime/. They remain executable from the
# installed package's resource tree.
PACKAGE_TOOL_SCRIPTS = [
    "eif_benchmark.py",
]

# Resource trees the _impl scripts read at runtime via --framework-root.
RESOURCE_TREES = [
    "core/schemas",
    "core/ontology",
    "docs/architecture",
    "docs/product",
    "docs/reference",
    "docs/research",
    "locales",
    "templates",
    "playbooks",
    "skills",
    "integrations",
]


def iter_resource_files(tree: str) -> list[Path]:
    src_root = FRAMEWORK_ROOT / tree
    if not src_root.is_dir():
        raise FileNotFoundError(f"mandatory resource source missing: {tree}/")
    return sorted(f for f in src_root.rglob("*") if f.is_file())


def planned_copies() -> list[tuple[Path, Path]]:
    """Every (source, destination) pair this sync manages."""
    pairs: list[tuple[Path, Path]] = []
    for name in IMPL_SCRIPTS:
        src = FRAMEWORK_ROOT / "scripts" / name
        if not src.exists():
            raise FileNotFoundError(f"mandatory _impl source missing: scripts/{name}")
        pairs.append((src, PKG_ROOT / "_impl" / name))
    for tree in RESOURCE_TREES:
        for src in iter_resource_files(tree):
            rel = src.relative_to(FRAMEWORK_ROOT)
            pairs.append((src, PKG_ROOT / "resources" / rel))
    # eif_init.py's OWN bundling mechanism (collect_bundle_sources(),
    # invoked when `eifctl init` runs) expects to find these under
    # <framework_root>/scripts/ - a real, separate need from _impl/ above,
    # which is for eifctl's own dispatch. BUNDLE_SCRIPTS is read directly
    # from eif_init.py (imported above), not re-typed as a second list
    # that could silently drift from the one eif_init.py actually uses.
    for name in BUNDLE_SCRIPTS:
        src = FRAMEWORK_ROOT / "scripts" / name
        if not src.exists():
            raise FileNotFoundError(f"mandatory bundle-source resource missing: scripts/{name}")
        pairs.append((src, PKG_ROOT / "resources" / "scripts" / name))
    for name in PACKAGE_TOOL_SCRIPTS:
        src = FRAMEWORK_ROOT / "scripts" / name
        if not src.exists():
            raise FileNotFoundError(f"mandatory package-tool resource missing: scripts/{name}")
        pairs.append((src, PKG_ROOT / "resources" / "scripts" / name))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="Verify only, write nothing")
    args = ap.parse_args()

    pairs = planned_copies()

    if args.check:
        mismatched = []
        for src, dest in pairs:
            if not dest.exists() or not filecmp.cmp(src, dest, shallow=False):
                mismatched.append((src, dest))
        if mismatched:
            print(f"sync-package-sources: {len(mismatched)} file(s) out of sync - run without --check to fix:")
            for src, dest in mismatched:
                print(f"  {src.relative_to(FRAMEWORK_ROOT)} -> {dest.relative_to(FRAMEWORK_ROOT)}")
            return 1
        print(f"sync-package-sources: all {len(pairs)} package copies match their sources")
        return 0

    for src, dest in pairs:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    print(f"sync-package-sources: synced {len(pairs)} file(s) into {PKG_ROOT.relative_to(FRAMEWORK_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
