#!/usr/bin/env python3
"""Check the EIF dependency closure's licenses against
core/policies/license-policy.json - blocks on GPL/AGPL-family licenses
(unless an explicit policy exception exists), unknown/undeclared licenses,
unpinned entries in requirements.txt, and a stale SBOM.

Default scope: the CycloneDX SBOM (sbom.cdx.json) at the framework root -
the declared/resolved dependency closure recorded there, cross-checked
against requirements.txt's own pins (a version mismatch, or a pinned
package missing from the SBOM entirely, fails the run as a stale SBOM).
This is deterministic regardless of the interpreter, OS, or ambient
environment invoking this script, since it reads one committed JSON file
rather than introspecting whatever happens to be installed right now.

Pass --environment to instead scan every package importlib.metadata
reports as installed in the CURRENT interpreter (minus a small, fixed
bootstrap-tooling exclusion list: pip, setuptools, wheel). This is only
trustworthy in a clean virtualenv where `pip install -r requirements.txt`
was the sole install step - an ambient local Python environment that also
has unrelated packages installed for other projects (a real, observed
case on at least one dev machine this was built on) will produce false
denied/unknown findings. Skips the SBOM-freshness check: no SBOM is
consulted in this mode.

Usage:
    python scripts/eif_check_licenses.py [--framework-root PATH] [--environment]

Exit code 1 if any checked package has a denied-family license, an
undeclared/unknown license, requirements.txt has an unpinned entry, or (in
the default mode only) sbom.cdx.json disagrees with requirements.txt.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from importlib import metadata
from pathlib import Path

BOOTSTRAP_EXCLUDE = {"pip", "setuptools", "wheel"}

_REQ_NAME_VERSION_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([A-Za-z0-9.!+_-]+)$")


def load_policy(framework_root: Path) -> dict:
    path = framework_root / "core" / "policies" / "license-policy.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_sbom(framework_root: Path) -> dict:
    path = framework_root / "sbom.cdx.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found - default mode certifies the SBOM-declared dependency "
            "closure and requires it to exist. Regenerate it (cyclonedx-py environment "
            "in a clean venv with only requirements.txt installed) or pass --environment "
            "to scan the current interpreter's installed packages instead."
        )
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


def sbom_component_license_identifiers(component: dict) -> list[str]:
    """Every license-shaped string a CycloneDX SBOM component declares -
    licenses[].license.id (SPDX) and licenses[].license.name (free-text or
    trove classifier), the two fields cyclonedx-py records. Mirrors
    license_identifiers()'s Distribution-based extraction; the source is
    the committed sbom.cdx.json instead of a live importlib.metadata scan."""
    ids: list[str] = []
    for entry in component.get("licenses", []) or []:
        lic = entry.get("license", {})
        if lic.get("id"):
            ids.append(lic["id"])
        if lic.get("name"):
            ids.append(lic["name"])
    return ids


def matches_any(identifiers: list[str], names: list[str]) -> bool:
    return any(
        name.lower() in ident.lower()
        for ident in identifiers
        for name in names
    )


def classify_licenses(
    policy: dict, named_identifiers: list[tuple[str, list[str]]],
) -> tuple[list[str], list[str], list[str]]:
    """Returns (denied, unknown, ok) package-name lists. The one
    policy-matching decision, shared by both check_package_licenses (live
    --environment scan) and check_sbom_licenses (default, committed SBOM) -
    each just supplies (name, license_identifiers) pairs from its own
    source, so a policy semantics change never needs updating twice."""
    denied, unknown, ok = [], [], []
    for name, ids in named_identifiers:
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


def check_package_licenses(
    policy: dict, distributions: list[metadata.Distribution] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """Returns (denied, unknown, ok) package-name lists, scanning live
    interpreter distributions - the --environment opt-in path.

    `distributions` defaults to the real current interpreter's installed
    packages (`importlib.metadata.distributions()`). Tests pass an explicit,
    controlled list instead, so a developer's ambient Python environment
    (which may have unrelated packages installed for unrelated projects - a
    real, observed case on at least one dev machine this was built on) can
    never make this function's own test suite flaky or wrongly fail."""
    named_identifiers: list[tuple[str, list[str]]] = []
    seen = set()
    for dist in (distributions if distributions is not None else metadata.distributions()):
        name = dist.metadata.get("Name") or dist.name
        if not name or name in seen or name.lower() in BOOTSTRAP_EXCLUDE:
            continue
        seen.add(name)
        named_identifiers.append((name, license_identifiers(dist)))
    return classify_licenses(policy, named_identifiers)


def check_sbom_licenses(policy: dict, components: list[dict]) -> tuple[list[str], list[str], list[str]]:
    """Returns (denied, unknown, ok) package-name lists, sourced from a
    CycloneDX SBOM's component list - the default path. This is what makes
    the result deterministic across machines/OSes/ambient installs:
    sbom.cdx.json is a single committed file, not a live scan of whatever
    happens to be installed in the invoking interpreter."""
    named_identifiers: list[tuple[str, list[str]]] = []
    seen = set()
    for component in components:
        name = component.get("name")
        if not name or name in seen or name.lower() in BOOTSTRAP_EXCLUDE:
            continue
        seen.add(name)
        named_identifiers.append((name, sbom_component_license_identifiers(component)))
    return classify_licenses(policy, named_identifiers)


def _requirement_lines(framework_root: Path) -> list[str]:
    req_path = framework_root / "scripts" / "requirements.txt"
    lines = []
    for raw in req_path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def check_pinned_requirements(framework_root: Path, policy: dict) -> list[str]:
    if not policy.get("require_pinned_versions"):
        return []
    return [line for line in _requirement_lines(framework_root) if "==" not in line]


def parse_pinned_requirements(framework_root: Path) -> list[tuple[str, str]]:
    """(name, version) pairs for every exact-pinned entry in
    requirements.txt - any [extras] marker is stripped from the name, since
    the SBOM records the bare package cyclonedx-py resolved, not the extras
    syntax used to request it (e.g. jsonschema[format-nongpl]==4.23.0 ->
    ("jsonschema", "4.23.0"))."""
    pins = []
    for line in _requirement_lines(framework_root):
        m = _REQ_NAME_VERSION_RE.match(line)
        if m:
            pins.append((m.group(1), m.group(2)))
    return pins


def _normalize_pkg_name(name: str) -> str:
    """PEP 503 normalization - PyPI treats runs of -/_/. and case as
    equivalent, so comparing requirements.txt names against SBOM component
    names must normalize both sides first, or a purely cosmetic naming
    difference would misreport as a stale/missing SBOM entry."""
    return re.sub(r"[-_.]+", "-", name).lower()


def check_sbom_freshness(framework_root: Path, sbom: dict) -> list[str]:
    """Human-readable problems if sbom.cdx.json's component versions
    disagree with requirements.txt's pinned versions, or a pinned
    dependency has no corresponding SBOM component at all. Either means the
    SBOM was not regenerated after a dependency bump and no longer reflects
    the closure eif_check_licenses.py's default mode actually certifies - a
    stale SBOM is a silent gap in the license gate, not a cosmetic issue,
    so this fails the run rather than warning."""
    pins = parse_pinned_requirements(framework_root)
    sbom_versions: dict[str, str] = {}
    for component in sbom.get("components", []):
        name = component.get("name")
        version = component.get("version")
        if name and version:
            sbom_versions[_normalize_pkg_name(name)] = version

    problems = []
    for name, version in pins:
        sbom_version = sbom_versions.get(_normalize_pkg_name(name))
        if sbom_version is None:
            problems.append(
                f"{name}=={version} is pinned in requirements.txt but sbom.cdx.json has "
                "no matching component - regenerate the SBOM"
            )
        elif sbom_version != version:
            problems.append(
                f"{name}: requirements.txt pins {version}, sbom.cdx.json has {sbom_version} "
                "- regenerate the SBOM"
            )
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--framework-root", default=".", help="Repository root (where core/policies/ and sbom.cdx.json live)")
    ap.add_argument(
        "--environment", action="store_true",
        help="Scan every package installed in the CURRENT Python interpreter instead of "
             "the committed sbom.cdx.json. Opt-in only, and only trustworthy in a clean "
             "virtualenv with exactly `pip install -r requirements.txt` installed - an "
             "ambient dev machine with unrelated packages will produce false denied/unknown "
             "findings. Skips the SBOM-freshness check (no SBOM is consulted in this mode).",
    )
    args = ap.parse_args()
    framework_root = Path(args.framework_root).resolve()

    policy = load_policy(framework_root)
    unpinned = check_pinned_requirements(framework_root, policy)

    if args.environment:
        stale: list[str] = []
        denied, unknown, ok = check_package_licenses(policy)
        scope_label = "every package installed in the current interpreter (--environment)"
    else:
        try:
            sbom = load_sbom(framework_root)
        except FileNotFoundError as e:
            print(f"eif-check-licenses: FAILED - {e}")
            return 1
        stale = check_sbom_freshness(framework_root, sbom)
        denied, unknown, ok = check_sbom_licenses(policy, sbom.get("components", []))
        scope_label = "the declared/resolved dependency closure recorded in sbom.cdx.json"

    print(f"eif-check-licenses: checking {scope_label}")
    print(f"eif-check-licenses: {len(ok)} package(s) OK")
    for name in ok:
        print(f"  OK      {name}")

    failed = bool(denied or unknown or unpinned or stale)

    for name in denied:
        print(f"  DENIED  {name} - matches a denied license family with no recorded exception")
    for name in unknown:
        print(f"  UNKNOWN {name} - no declared license found, or not in the allowed_licenses list")
    for line in unpinned:
        print(f"  UNPINNED requirements.txt entry has no exact '==' pin: {line}")
    for problem in stale:
        print(f"  STALE   {problem}")

    if failed:
        print(
            f"\neif-check-licenses: FAILED - {len(denied)} denied, {len(unknown)} unknown, "
            f"{len(unpinned)} unpinned, {len(stale)} stale-SBOM"
        )
        return 1

    tail = "" if args.environment else "; sbom.cdx.json matches requirements.txt"
    print(f"\neif-check-licenses: all checked packages have an allowed, declared license; requirements.txt fully pinned{tail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
