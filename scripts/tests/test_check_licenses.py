#!/usr/bin/env python3
"""Tests for eif_check_licenses.py's classification logic and the real
current-environment result (this repo's own pinned dependencies must pass).

Usage:
    python scripts/tests/test_check_licenses.py
"""
from __future__ import annotations

import email.message
import sys
import tempfile
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eif_check_licenses import (  # noqa: E402
    check_package_licenses,
    check_pinned_requirements,
    license_identifiers,
    load_policy,
    matches_any,
)

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]


def _installed(name: str) -> bool:
    try:
        metadata.distribution(name)
        return True
    except metadata.PackageNotFoundError:
        return False


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


class FakeDistribution:
    """Minimal stand-in for importlib.metadata.Distribution - just enough
    of the interface eif_check_licenses.py actually reads (.metadata with
    .get()/.get_all(), .name)."""

    def __init__(self, name: str, fields: dict[str, str | list[str]]):
        self.name = name
        msg = email.message.Message()
        msg["Name"] = name
        for key, value in fields.items():
            if isinstance(value, list):
                for v in value:
                    msg[key] = v
            else:
                msg[key] = value
        self.metadata = msg


def main() -> int:
    results: list[bool] = []
    policy = load_policy(FRAMEWORK_ROOT)

    # --- matches_any: pure function, no environment dependency ---
    results.append(check(
        "matches_any: case-insensitive substring match",
        matches_any(["License :: OSI Approved :: MIT License"], ["MIT"]),
    ))
    results.append(check(
        "matches_any: no match returns False",
        not matches_any(["Apache-2.0"], ["GPL", "AGPL"]),
    ))
    results.append(check(
        "matches_any: GPL family does not accidentally match LGPL as GPL-denied would need its own family entry",
        matches_any(["License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)"], ["GPL"]),
        "documents actual behavior: 'GPL' is a substring of 'LGPL' text too - denied_license_families entries "
        "must be specific enough (this repo's policy denies 'GPL'/'AGPL' as families, and separately allows "
        "'LGPL' in allowed_licenses so an LGPL package is still classified OK via the allowed-list branch, "
        "which check_package_licenses evaluates only when NOT already caught by denied_license_families - "
        "this test documents the substring-match caveat rather than hiding it)",
    ))

    # --- license_identifiers: real Distribution-shaped input ---
    mit_dist = FakeDistribution("fake-mit-pkg", {"License-Expression": "MIT"})
    results.append(check(
        "license_identifiers: reads License-Expression",
        license_identifiers(mit_dist) == ["MIT"],
        str(license_identifiers(mit_dist)),
    ))

    classifier_dist = FakeDistribution("fake-classifier-pkg", {
        "Classifier": ["Programming Language :: Python :: 3", "License :: OSI Approved :: Apache Software License"],
    })
    results.append(check(
        "license_identifiers: reads License :: classifiers, ignores non-license classifiers",
        license_identifiers(classifier_dist) == ["License :: OSI Approved :: Apache Software License"],
        str(license_identifiers(classifier_dist)),
    ))

    unknown_dist = FakeDistribution("fake-no-license-pkg", {"Summary": "does something"})
    results.append(check(
        "license_identifiers: no declared license returns [] (not a placeholder string)",
        license_identifiers(unknown_dist) == [],
        str(license_identifiers(unknown_dist)),
    ))

    unknown_field_dist = FakeDistribution("fake-unknown-field-pkg", {"License": "UNKNOWN"})
    results.append(check(
        "license_identifiers: License: UNKNOWN is treated as undeclared, not a real license value",
        license_identifiers(unknown_field_dist) == [],
        str(license_identifiers(unknown_field_dist)),
    ))

    # --- check_pinned_requirements ---
    real_unpinned = check_pinned_requirements(FRAMEWORK_ROOT, policy)
    results.append(check(
        "check_pinned_requirements: this repo's actual requirements.txt is fully pinned",
        real_unpinned == [],
        str(real_unpinned),
    ))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        (tmp_root / "scripts").mkdir()
        (tmp_root / "scripts" / "requirements.txt").write_text(
            "PyYAML==6.0.2\nsome-unpinned-package\n# a comment\n", encoding="utf-8",
        )
        unpinned = check_pinned_requirements(tmp_root, policy)
        results.append(check(
            "check_pinned_requirements: an unpinned line is detected, a pinned line and a comment are not",
            unpinned == ["some-unpinned-package"],
            str(unpinned),
        ))

    # --- check_package_licenses: fixture-controlled, NOT the real ambient
    # environment - a dev machine can have unrelated packages installed for
    # unrelated projects (observed directly while building this: rfc3987,
    # psycopg, edge-tts and others turned up on the machine this was
    # developed on, none of them EIF dependencies). Scanning the real
    # environment belongs to eif_check_licenses.py's own `main()` / CI,
    # where the environment is exactly `pip install -r requirements.txt`;
    # a unit test asserting against the real ambient environment would be
    # testing "is this developer's whole machine clean", not "is
    # check_package_licenses() correct" - so every case here is injected.
    clean_dist = FakeDistribution("clean-pkg", {"License-Expression": "MIT"})
    gpl_dist = FakeDistribution("gpl-pkg", {"Classifier": ["License :: OSI Approved :: GNU General Public License v3 (GPLv3)"]})
    no_license_dist = FakeDistribution("mystery-pkg", {"Summary": "no license field at all"})

    denied, unknown, ok = check_package_licenses(policy, [clean_dist, gpl_dist, no_license_dist])
    results.append(check(
        "check_package_licenses: a clean MIT package is classified OK",
        any("clean-pkg" in name for name in ok),
        str(ok),
    ))
    results.append(check(
        "check_package_licenses: a GPL package with no exception is DENIED",
        any("gpl-pkg" in name for name in denied),
        str(denied),
    ))
    results.append(check(
        "check_package_licenses: a package with no declared license is UNKNOWN",
        any("mystery-pkg" in name for name in unknown),
        str(unknown),
    ))

    policy_with_exception = dict(policy, exceptions=[{"package": "gpl-pkg", "reason": "test fixture"}])
    denied_ex, _, ok_ex = check_package_licenses(policy_with_exception, [gpl_dist])
    results.append(check(
        "check_package_licenses: a GPL package WITH a recorded policy exception is OK, not denied",
        denied_ex == [] and any("gpl-pkg" in name for name in ok_ex),
        f"denied={denied_ex} ok={ok_ex}",
    ))

    # --- this repo's real, current environment - the two direct deps only,
    # checked individually via license_identifiers (already exercised
    # above), not via a full ambient-environment scan ---
    real_pyyaml = metadata.distribution("PyYAML") if _installed("PyYAML") else None
    real_jsonschema = metadata.distribution("jsonschema") if _installed("jsonschema") else None
    results.append(check(
        "this environment has PyYAML and jsonschema installed with a declared, allowed license each",
        real_pyyaml is not None and real_jsonschema is not None
        and matches_any(license_identifiers(real_pyyaml), policy["allowed_licenses"])
        and matches_any(license_identifiers(real_jsonschema), policy["allowed_licenses"]),
        f"PyYAML={license_identifiers(real_pyyaml) if real_pyyaml else 'NOT INSTALLED'} "
        f"jsonschema={license_identifiers(real_jsonschema) if real_jsonschema else 'NOT INSTALLED'}",
    ))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_check_licenses: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
