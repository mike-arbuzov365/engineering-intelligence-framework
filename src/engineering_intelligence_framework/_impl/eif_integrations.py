#!/usr/bin/env python3
"""Behavioral health adapters for EIF optional external integrations.

The core framework never installs providers and never mutates user hooks. This
module reads public provider manifests, runs bounded local canaries and returns
content-safe records conforming to integration-health-result.schema.json.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


CommandRunner = Callable[[list[str], Path | None, float], subprocess.CompletedProcess]


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(data: dict, schema_path: Path) -> list[str]:
    schema = _read_json(schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [error.message for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path))]


def _run(argv: list[str], cwd: Path | None = None, timeout: float = 15.0) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(argv, 127, "", type(exc).__name__)


def _version_tuple(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError(f"not a three-part version: {value!r}")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _constraint(manifest: dict) -> str:
    compatibility = manifest["compatibility"]
    return f">={compatibility['min_inclusive']},<{compatibility['max_exclusive']}"


def _compatible(version: str, manifest: dict) -> bool:
    compatibility = manifest["compatibility"]
    current = _version_tuple(version)
    return _version_tuple(compatibility["min_inclusive"]) <= current < _version_tuple(compatibility["max_exclusive"])


def _evidence(kind: str, summary: str) -> dict:
    return {"kind": kind, "summary": summary, "content_free": True}


def _capability(capability_id: str, required: bool, status: str, kind: str, summary: str) -> dict:
    return {
        "id": capability_id,
        "required": required,
        "status": status,
        "evidence": _evidence(kind, summary),
    }


def _freshness_not_applicable() -> dict:
    return {
        "state": "not-applicable",
        "baseline_commit": None,
        "current_commit": None,
        "merge_base": None,
    }


def _base_result(
    integration: str,
    provider: str | None,
    state: str,
    data_boundary: str,
    checked_at: str,
    *,
    version: dict | None = None,
    capabilities: list[dict] | None = None,
    remediation: list[str] | None = None,
) -> dict:
    return {
        "schema_version": 1,
        "integration": integration,
        "provider": provider,
        "state": state,
        "checked_at": checked_at,
        "data_boundary": data_boundary,
        "version": version or {"detected": None, "compatible": None, "constraint": None},
        "capabilities": capabilities or [],
        "freshness": _freshness_not_applicable(),
        "remediation": remediation or [],
    }


def _manifest(framework_root: Path, provider: str) -> tuple[dict | None, list[str]]:
    manifest_path = framework_root / "integrations" / provider / "manifest.json"
    if not manifest_path.is_file():
        return None, ["provider manifest is missing"]
    try:
        data = _read_json(manifest_path)
    except (OSError, json.JSONDecodeError):
        return None, ["provider manifest is unreadable or invalid JSON"]
    schema = framework_root / "core" / "schemas" / "integration-provider-manifest.schema.json"
    errors = _validate(data, schema)
    return data, errors


def _rtk_static_contract(framework_root: Path) -> tuple[bool, str]:
    registry_path = framework_root / "integrations" / "rtk" / "command-registry.json"
    try:
        registry = _read_json(registry_path)
        registry_errors = _validate(
            registry,
            framework_root / "core" / "schemas" / "rtk-command-registry.schema.json",
        )
        sample_event = {
            "schema_version": 1,
            "event_id": "0" * 32,
            "recorded_at": "2026-07-21T00:00:00Z",
            "integration": "rtk",
            "registry_version": registry["registry_version"],
            "command_class": "proxy-explicit",
            "route": "raw-proxy",
            "outcome": "success",
            "raw_bytes": 100,
            "emitted_bytes": 100,
            "estimated_raw_tokens": 25,
            "estimated_emitted_tokens": 25,
            "estimated_saved_tokens": 0,
            "savings_eligible": False,
        }
        telemetry_errors = _validate(
            sample_event,
            framework_root / "core" / "schemas" / "rtk-telemetry-event.schema.json",
        )
    except (KeyError, OSError, json.JSONDecodeError, ValueError):
        return False, "RTK registry or telemetry contract is unreadable"
    if registry_errors or telemetry_errors:
        return False, "RTK registry or telemetry contract failed schema validation"
    return True, "registry and content-free telemetry contracts validated"


def _rtk_canaries(
    executable: str,
    framework_root: Path,
    manifest: dict,
    runner: CommandRunner,
) -> dict[str, tuple[bool, str]]:
    results: dict[str, tuple[bool, str]] = {}

    help_result = runner([executable, "--help"], None, 10.0)
    required_routes = ("git", "grep", "read", "summary", "proxy")
    help_ok = help_result.returncode == 0 and all(
        re.search(rf"(?m)^\s*{re.escape(route)}\s", help_result.stdout)
        for route in required_routes
    )
    results["cli-surface"] = (
        help_ok,
        "required filtered, summary and proxy routes detected" if help_ok else "required RTK CLI routes were not all detected",
    )

    with tempfile.TemporaryDirectory(prefix="eif rtk argv ") as raw_tmp:
        tmp = Path(raw_tmp)
        probe = tmp / "argv probe.py"
        probe.write_text(
            "import json, sys\nprint(json.dumps(sys.argv[1:], ensure_ascii=False))\n",
            encoding="utf-8",
        )
        expected = ["value with spaces", "pipe|literal", 'quote"literal']
        proxy_result = runner([executable, "proxy", sys.executable, str(probe), *expected], None, 15.0)
        try:
            actual = json.loads(proxy_result.stdout.strip())
        except json.JSONDecodeError:
            actual = None
        proxy_ok = proxy_result.returncode == 0 and actual == expected
        results["proxy-argv"] = (
            proxy_ok,
            "explicit raw proxy preserved tested argv boundaries" if proxy_ok else "explicit raw proxy did not preserve tested argv boundaries",
        )

    with tempfile.TemporaryDirectory(prefix="eif-rtk-grep-") as raw_tmp:
        marker_file = Path(raw_tmp) / "markers.txt"
        marker_file.write_text("EIF_RTK_ALPHA\nEIF_RTK_BETA\n", encoding="utf-8")
        grep_result = runner(
            [executable, "grep", "-e", "EIF_RTK_ALPHA", "-e", "EIF_RTK_BETA", str(marker_file)],
            None,
            15.0,
        )
        grep_ok = (
            grep_result.returncode == 0
            and "EIF_RTK_ALPHA" in grep_result.stdout
            and "EIF_RTK_BETA" in grep_result.stdout
        )
        results["grep-alternation"] = (
            grep_ok,
            "split alternation returned both markers" if grep_ok else f"split alternation canary failed with exit {grep_result.returncode}",
        )

    with tempfile.TemporaryDirectory(prefix="eif-rtk-diff-") as raw_tmp:
        repo = Path(raw_tmp)
        setup = [
            _run(["git", "init", "-q"], repo),
            _run(["git", "config", "user.email", "eif-canary@example.invalid"], repo),
            _run(["git", "config", "user.name", "EIF Canary"], repo),
        ]
        sample = repo / "sample.txt"
        sample.write_text("before\n", encoding="utf-8")
        setup.extend([
            _run(["git", "add", "sample.txt"], repo),
            _run(["git", "commit", "-q", "-m", "baseline"], repo),
        ])
        sample.write_text("after\n", encoding="utf-8")
        diff_result = runner([executable, "git", "diff", "--stat"], repo, 15.0)
        diff_ok = all(item.returncode == 0 for item in setup) and diff_result.returncode == 0 and "sample.txt" in diff_result.stdout
        results["git-diff"] = (
            diff_ok,
            "native git diff preserved the changed-file signal" if diff_ok else "native git diff canary did not preserve the changed-file signal",
        )

    results["content-free-telemetry"] = _rtk_static_contract(framework_root)
    return results


def evaluate_rtk(
    integration: str,
    entry: dict,
    framework_root: Path,
    *,
    checked_at: str,
    which: Callable[[str], str | None] = shutil.which,
    runner: CommandRunner = _run,
) -> dict:
    provider = entry.get("provider")
    boundary = entry.get("data_boundary", "local-only")
    if provider != "rtk":
        return _base_result(
            integration,
            provider,
            "misconfigured",
            boundary,
            checked_at,
            remediation=["Set provider to 'rtk' or disable this integration."],
        )

    manifest, manifest_errors = _manifest(framework_root, "rtk")
    if manifest is None or manifest_errors:
        return _base_result(
            integration,
            provider,
            "misconfigured",
            boundary,
            checked_at,
            remediation=["Restore and validate integrations/rtk/manifest.json."],
        )
    if boundary not in manifest["data_boundaries"]:
        return _base_result(
            integration,
            provider,
            "misconfigured",
            boundary,
            checked_at,
            remediation=["Use the local-only data boundary for RTK."],
        )

    executable = entry.get("executable_path") or which(manifest["executable"])
    if not executable:
        return _base_result(
            integration,
            provider,
            "unavailable",
            boundary,
            checked_at,
            version={"detected": None, "compatible": None, "constraint": _constraint(manifest)},
            remediation=["Install a compatible Rust Token Killer binary or disable the integration."],
        )

    version_argv = [executable, *manifest["compatibility"]["version_command"][1:]]
    version_result = runner(version_argv, None, 10.0)
    match = re.search(manifest["compatibility"]["version_pattern"], version_result.stdout.strip())
    detected = match.group(1) if version_result.returncode == 0 and match else None
    version_ok = bool(detected and _compatible(detected, manifest))
    capabilities = [
        _capability(
            "version-probe",
            True,
            "pass" if version_ok else "fail",
            "probe",
            f"compatible version detected: {detected}" if version_ok else "version was absent, unparseable or outside the compatible range",
        )
    ]
    version = {"detected": detected, "compatible": version_ok, "constraint": _constraint(manifest)}
    if not version_ok:
        for capability in manifest["capabilities"]:
            if capability["id"] == "version-probe":
                continue
            capabilities.append(
                _capability(capability["id"], capability["required_for_healthy"], "skipped", "fallback", "skipped because version compatibility failed")
            )
        return _base_result(
            integration,
            provider,
            "misconfigured",
            boundary,
            checked_at,
            version=version,
            capabilities=capabilities,
            remediation=["Install an RTK version in the declared compatible range, then rerun doctor."],
        )

    canaries = _rtk_canaries(executable, framework_root, manifest, runner)
    for capability in manifest["capabilities"]:
        capability_id = capability["id"]
        if capability_id == "version-probe":
            continue
        passed, summary = canaries.get(capability_id, (False, "required canary was not implemented"))
        capabilities.append(
            _capability(capability_id, capability["required_for_healthy"], "pass" if passed else "fail", "canary", summary)
        )

    failed_required = [item for item in capabilities if item["required"] and item["status"] != "pass"]
    state = "degraded" if failed_required else "healthy"
    remediation = [] if state == "healthy" else [
        "Use unfiltered core-safe commands for failed command classes and inspect the failing canary before counting savings."
    ]
    return _base_result(
        integration,
        provider,
        state,
        boundary,
        checked_at,
        version=version,
        capabilities=capabilities,
        remediation=remediation,
    )


def evaluate_integrations(
    config: dict | None,
    framework_root: Path,
    instance_path: Path,
    *,
    checked_at: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
    runner: CommandRunner = _run,
) -> list[dict]:
    del instance_path  # reserved for Graphify freshness and project-local artifact checks
    timestamp = checked_at or _utc_now()
    integrations = (config or {}).get("integrations") or {}
    if not isinstance(integrations, dict):
        return []
    results = []
    for integration, entry in sorted(integrations.items()):
        if not isinstance(entry, dict):
            results.append(_base_result(integration, None, "misconfigured", "local-only", timestamp, remediation=["Replace the integration entry with an object."]))
            continue
        boundary = entry.get("data_boundary", "local-only")
        if not entry.get("enabled"):
            results.append(_base_result(integration, entry.get("provider"), "disabled", boundary, timestamp))
            continue
        provider = entry.get("provider")
        if provider == "rtk" or integration == "shell_output_compression":
            results.append(evaluate_rtk(integration, entry, framework_root, checked_at=timestamp, which=which, runner=runner))
        else:
            results.append(_base_result(integration, provider, "misconfigured", boundary, timestamp, remediation=["No behavioral adapter exists for the configured provider."]))
    return results


def validate_health_results(results: list[dict], framework_root: Path) -> list[str]:
    schema_path = framework_root / "core" / "schemas" / "integration-health-result.schema.json"
    problems = []
    for index, result in enumerate(results):
        for error in _validate(result, schema_path):
            problems.append(f"integration result {index}: {error}")
    return problems


def integration_problems(config: dict | None, results: list[dict]) -> list[str]:
    configured = (config or {}).get("integrations") or {}
    problems = []
    for result in results:
        state = result["state"]
        if state == "disabled" or state == "healthy":
            continue
        entry = configured.get(result["integration"], {}) if isinstance(configured, dict) else {}
        policy = entry.get("failure_policy", "degrade") if isinstance(entry, dict) else "degrade"
        base = f"integrations.{result['integration']}: provider {result['provider']!r} is {state}"
        if state == "misconfigured":
            problems.append(f"{base} - fix the configuration or disable the integration")
        elif policy == "fail-closed":
            problems.append(f"{base} - failure_policy is fail-closed")
    return problems
