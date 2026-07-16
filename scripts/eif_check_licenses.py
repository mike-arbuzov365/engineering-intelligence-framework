#!/usr/bin/env python3
"""Check every installed Python dependency's license against
core/policies/license-policy.json - blocks on GPL/AGPL-family licenses
(unless an explicit policy exception exists), unknown/undeclared licenses,
and unpinned entries in requirements.txt.

Scope: every package `importlib.metadata` reports as installed in the
CURRENT interpreter, minus a small, fixed bootstrap-tooling exclusion list
(pip, setuptools, wheel - never real project dependencies). This is exactly
right in CI (a fresh environment where `pip install -r requirements.txt`
was the only install step - "everything installed minus bootstrap" IS the
real dependency closure). It is NOT reliable against an ambient local
Python environment that has unrelated packages installed for other
projects - run this inside a clean virtualenv that only has
requirements.txt installed for a trustworthy local result, the same way
scripts/requirements.txt itself is meant to be installed.

Usage:
    python scripts/eif_check_licenses.py [--framework-root PATH]

Exit code 1 if any installed package has a denied-family license, an
undeclared/unknown license, or if requirements.txt has an unpinned entry.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from importlib import metadata
from pathlib import Path

BOOTSTRAP_EXCLUDE = {"pip", "setuptools", "wheel"}


def load_policy(framework_root: Path) -> dict:
    path = framework_root / "core" / "policies" / "license-policy.json"
    return json.loads(path.read_text(encoding="utf-8"))


def license_identifiers(dist: metadata.Distribution) -> list[str]:
    """Every license-shaped string this distribution's own metadata
    declares - the SPDX `License-Expression` field if present, the free-text
    `License:` field, and every `Classifier: License :: ...` trove
    classifier. Returns [] (not a placeholder string) when truly nothing is
    declared - the caller decides that means "unknown", not this function."""
    meta = dist.metadata
    ids: list[str] = []

    expr = meta.get("License-Expression")
    if expr:
        ids.append(expr)

    license_field = meta.get("License")
    if license_field and license_field.strip().upper() not in {"UNKNOWN", ""}:
        ids.append(license_field.strip())

    for classifier in meta.get_all("Classifier") or []:
        if classifier.startswith("License ::"):
            ids.append(classifier)

    return ids


def matches_any(identifiers: list[str], names: list[str]) -> bool:
    return any(
        name.lower() in ident.lower()
        for ident in identifiers
        for name in names
    )


def check_package_licenses(
    policy: dict, distributions: list[metadata.Distribution] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """Returns (denied, unknown, ok) package-name lists.

    `distributions` defaults to the real current interpreter's installed
    packages (`importlib.metadata.distributions()`) - the right default for
    `main()`/CI, where the environment is exactly `pip install -r
    requirements.txt` and nothing else. Tests pass an explicit, controlled
    list instead, so a developer's ambient Python environment (which may
    have unrelated packages installed for unrelated projects - a real,
    observed case on at least one dev machine this was built on) can never
    make this function's own test suite flaky or wrongly fail."""
    denied, unknown, ok = [], [], []
    seen = set()
    for dist in (distributions if distributions is not None else metadata.distributions()):
        name = dist.metadata.get("Name") or dist.name
        if not name or name in seen or name.lower() in BOOTSTRAP_EXCLUDE:
            continue
        seen.add(name)

        ids = license_identifiers(dist)
        if not ids:
            unknown.append(name)
            continue

        if matches_any(ids, policy["denied_license_families"]):
            exception = next((e for e in policy["exceptions"] if e.get("package") == name), None)
            if exception:
                ok.append(f"{name} (exception: {exception.get('reason', 'no reason recorded')})")
            else:
                denied.append(f"{name}: {ids}")
            continue

        if matches_any(ids, policy["allowed_licenses"]):
            ok.append(name)
        else:
            unknown.append(f"{name}: {ids} (not in allowed_licenses - add it deliberately, don't assume)")

    return denied, unknown, ok


def check_pinned_requirements(framework_root: Path, policy: dict) -> list[str]:
    if not policy.get("require_pinned_versions"):
        return []
    req_path = framework_root / "scripts" / "requirements.txt"
    unpinned = []
    for line in req_path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if "==" not in line:
            unpinned.append(line)
    return unpinned


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--framework-root", default=".", help="Repository root (where core/policies/ lives)")
    args = ap.parse_args()
    framework_root = Path(args.framework_root).resolve()

    policy = load_policy(framework_root)

    denied, unknown, ok = check_package_licenses(policy)
    unpinned = check_pinned_requirements(framework_root, policy)

    print(f"eif-check-licenses: {len(ok)} package(s) OK")
    for name in ok:
        print(f"  OK      {name}")

    failed = bool(denied or unknown or unpinned)

    for name in denied:
        print(f"  DENIED  {name} - matches a denied license family with no recorded exception")
    for name in unknown:
        print(f"  UNKNOWN {name} - no declared license found, or not in the allowed_licenses list")
    for line in unpinned:
        print(f"  UNPINNED requirements.txt entry has no exact '==' pin: {line}")

    if failed:
        print(f"\neif-check-licenses: FAILED - {len(denied)} denied, {len(unknown)} unknown, {len(unpinned)} unpinned")
        return 1

    print("\neif-check-licenses: all installed packages have an allowed, declared license; requirements.txt fully pinned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
