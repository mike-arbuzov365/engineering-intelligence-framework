#!/usr/bin/env python3
"""Deterministic vendor-docs declaration, guidance-generation and safety tests.

These check the parts EIF actually owns: the manifest's honesty about what
is and is not verified, the generated routing guidance staying in sync with
its policy source, and the hard guarantee that no generated artifact claims
to have installed anything or carries a credential.

They deliberately do NOT assert live provider behavior. EIF generates
configuration for an agent to load and does not itself speak MCP, so a test
here that claimed a working provider would be asserting something this
repository cannot observe.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eif_generate_vendor_docs_guidance as guidance  # noqa: E402

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_DIR = FRAMEWORK_ROOT / "integrations" / "vendor-docs"

CREDENTIAL_HINTS = (
    "api_key",
    "apikey",
    "api-key",
    "token",
    "secret",
    "password",
    "bearer",
)


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return bool(condition)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifest_declares_provider_and_boundary(results: list[bool]) -> None:
    manifest = load(INTEGRATION_DIR / "manifest.json")

    results.append(check("manifest: integration id", manifest["integration"] == "vendor-docs"))
    results.append(check("manifest: transport is mcp", manifest["transport"] == "mcp"))

    providers = manifest["providers"]
    results.append(check("manifest: at least one declared provider", len(providers) >= 1))

    context7 = next((p for p in providers if p["id"] == "context7"), None)
    results.append(check("manifest: context7 is declared", context7 is not None))
    if context7 is not None:
        results.append(
            check(
                "manifest: context7 boundary is external-api",
                context7["data_boundary"] == "external-api",
                "a hosted service must not be declared local-only",
            )
        )
        results.append(
            check(
                "manifest: context7 is not installed by eif",
                context7["installed_by_eif"] is False,
                "EIF must never claim to install a user-level MCP server",
            )
        )

    results.append(
        check(
            "manifest: generator does not mutate user config",
            manifest["artifact_policy"]["user_config_mutated_by_generator"] is False,
        )
    )


def test_manifest_is_honest_about_unverified_capability(results: list[bool]) -> None:
    """The transport cannot be probed by eifctl, so it must not claim to be."""
    manifest = load(INTEGRATION_DIR / "manifest.json")
    caps = {c["id"]: c for c in manifest["capabilities"]}

    transport = caps.get("transport-reachable")
    results.append(check("capability: transport-reachable exists", transport is not None))
    if transport is not None:
        results.append(
            check(
                "capability: transport-reachable is marked unverified",
                transport.get("verified") is False,
                "EIF does not speak MCP; claiming a verified probe would be false",
            )
        )
        results.append(
            check(
                "capability: the verification gap is stated",
                bool(transport.get("verification_gap")),
            )
        )

    cost = caps.get("cost-cap-explicit")
    results.append(
        check(
            "capability: an explicit cost cap is required for healthy",
            cost is not None and cost["required_for_healthy"] is True,
        )
    )


def test_authority_position_does_not_outrank_empirical(results: list[bool]) -> None:
    """Vendor docs are normative. Regression guard against a rank-based claim."""
    manifest = load(INTEGRATION_DIR / "manifest.json")
    authority = manifest["authority_position"]

    results.append(check("authority: axis is normative", authority["axis"] == "normative"))
    rule = authority["rule"].lower()
    results.append(
        check(
            "authority: states it does not outrank observation",
            "does not outrank" in rule and "discrepancy" in rule,
            "a normative source must not be presented as beating empirical evidence",
        )
    )


def test_generated_artifacts_match_policy_source(results: list[bool]) -> None:
    """Committed guidance must equal a fresh generation, or it has drifted."""
    artifacts = guidance.generate()
    results.append(check("generator: produces artifacts", len(artifacts) >= 2))

    for path, expected in artifacts.items():
        rel = path.relative_to(FRAMEWORK_ROOT)
        if not path.exists():
            results.append(check(f"generated: {rel} exists", False, "missing"))
            continue
        results.append(
            check(
                f"generated: {rel} is in sync",
                path.read_text(encoding="utf-8") == expected,
                "regenerate with scripts/eif_generate_vendor_docs_guidance.py",
            )
        )


def test_generated_mcp_templates_are_inert(results: list[bool]) -> None:
    """No generated template may claim installation or carry a credential."""
    mcp_dir = INTEGRATION_DIR / "generated" / "mcp"
    templates = sorted(mcp_dir.glob("*.json"))
    results.append(check("mcp: a template exists per adapter", len(templates) == 4, str(len(templates))))

    for path in templates:
        payload = load(path)
        name = path.name

        results.append(check(f"mcp/{name}: installed is false", payload["installed"] is False))
        results.append(check(f"mcp/{name}: template_only is true", payload["template_only"] is True))
        results.append(
            check(
                f"mcp/{name}: does not mutate user config",
                payload["safety"]["user_config_mutated_by_generator"] is False,
            )
        )
        results.append(
            check(
                f"mcp/{name}: owner review required",
                payload["safety"]["active_install_requires_owner_review"] is True,
            )
        )
        results.append(
            check(
                f"mcp/{name}: command is owner-supplied, not guessed",
                payload["server_entry"]["command"].startswith("<owner-supplied"),
                "asserting an unverified provider invocation is the failure this avoids",
            )
        )
        results.append(
            check(
                f"mcp/{name}: no credentials embedded",
                payload["server_entry"]["env"] == {},
            )
        )

        raw = path.read_text(encoding="utf-8").lower()
        offending = [hint for hint in CREDENTIAL_HINTS if f'"{hint}"' in raw]
        results.append(
            check(
                f"mcp/{name}: no credential-shaped keys",
                not offending,
                f"found {offending}",
            )
        )

        results.append(
            check(
                f"mcp/{name}: config path is home-relative, not absolute",
                payload["config_path"].startswith("~/"),
                "an absolute machine path must never reach this repository",
            )
        )


def test_usage_policy_covers_both_directions(results: list[bool]) -> None:
    """Guidance that only says 'use it' spends quota on questions it cannot answer."""
    policy = load(INTEGRATION_DIR / "usage-policy.json")

    results.append(check("policy: has use_when entries", len(policy["use_when"]) >= 3))
    results.append(check("policy: has do_not_use_when entries", len(policy["do_not_use_when"]) >= 3))
    results.append(check("policy: has explicit boundaries", len(policy["boundaries"]) >= 3))

    for section in ("use_when", "do_not_use_when"):
        for entry in policy[section]:
            results.append(
                check(
                    f"policy: {section}/{entry['id']} states a rationale",
                    bool(entry.get("rationale")),
                )
            )

    boundaries = " ".join(policy["boundaries"]).lower()
    results.append(
        check(
            "policy: warns that query text leaves the machine",
            "leaves the local machine" in boundaries,
        )
    )
    results.append(
        check(
            "policy: forbids a silent fallback to recall",
            "silent fallback" in boundaries,
            "an unavailable provider must be reported, not quietly replaced by recall",
        )
    )


def main() -> int:
    results: list[bool] = []

    test_manifest_declares_provider_and_boundary(results)
    test_manifest_is_honest_about_unverified_capability(results)
    test_authority_position_does_not_outrank_empirical(results)
    test_generated_artifacts_match_policy_source(results)
    test_generated_mcp_templates_are_inert(results)
    test_usage_policy_covers_both_directions(results)

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\nvendor-docs integration: {passed}/{total}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
