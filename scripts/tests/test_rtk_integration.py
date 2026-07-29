#!/usr/bin/env python3
"""Deterministic RTK adapter, registry, telemetry and optional real-host tests."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from argparse import Namespace
from pathlib import Path
from subprocess import CompletedProcess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eif_generate_rtk_guidance as guidance  # noqa: E402
import eif_integrations as integrations  # noqa: E402
import eif_rtk_telemetry as telemetry  # noqa: E402


FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return bool(condition)


def config(*, enabled: bool = True, boundary: str = "local-only", policy: str = "degrade", executable_path: str | None = None) -> dict:
    entry = {
        "enabled": enabled,
        "provider": "rtk" if enabled else None,
        "processing": "local",
        "data_boundary": boundary,
        "failure_policy": policy,
    }
    if executable_path is not None:
        entry["executable_path"] = executable_path
    return {
        "integrations": {
            "shell_output_compression": entry
        }
    }


class FakeRunner:
    def __init__(
        self,
        *,
        version: str = "0.43.0",
        search_passes: bool = True,
        version_exit: int = 0,
    ):
        self.version = version
        self.search_passes = search_passes
        # An executable that is present but cannot run. 127 is what
        # integrations._run records for FileNotFoundError; a wrapper script
        # that cannot reach its interpreter exits 9009 through cmd.exe on
        # Windows, and a failed spawn exits 1. All three produce no version
        # and mean the same thing.
        self.version_exit = version_exit
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], cwd: Path | None, timeout: float) -> CompletedProcess:
        del cwd, timeout
        self.calls.append(argv)
        if argv[1:] == ["--version"]:
            if self.version_exit != 0:
                return CompletedProcess(argv, self.version_exit, "", "")
            return CompletedProcess(argv, 0, f"rtk {self.version}\n", "")
        if argv[1:] == ["--help"]:
            return CompletedProcess(argv, 0, "  git x\n  rg x\n  read x\n  summary x\n  proxy x\n", "")
        if len(argv) > 1 and argv[1] == "proxy":
            return CompletedProcess(argv, 0, json.dumps(argv[-3:]), "")
        if len(argv) > 1 and argv[1] == "rg":
            if self.search_passes:
                return CompletedProcess(argv, 0, "EIF_RTK_ALPHA\nEIF_RTK_BETA\n", "")
            return CompletedProcess(argv, 2, "", "search failed")
        if len(argv) > 2 and argv[1:3] == ["git", "diff"]:
            return CompletedProcess(argv, 0, "sample.txt | 2 +-\n", "")
        return CompletedProcess(argv, 1, "", "unexpected fake command")


def unit_results() -> list[bool]:
    results: list[bool] = []
    timestamp = "2026-07-21T00:00:00Z"

    disabled_runner = FakeRunner()
    disabled = integrations.evaluate_integrations(
        config(enabled=False), FRAMEWORK_ROOT, FRAMEWORK_ROOT,
        checked_at=timestamp, which=lambda _name: "fake-rtk", runner=disabled_runner,
    )[0]
    results.append(check("disabled RTK is core-safe and executes no provider probe", disabled["state"] == "disabled" and not disabled_runner.calls))

    unavailable = integrations.evaluate_integrations(
        config(), FRAMEWORK_ROOT, FRAMEWORK_ROOT,
        checked_at=timestamp, which=lambda _name: None, runner=FakeRunner(),
    )[0]
    results.append(check("missing RTK is unavailable, not healthy", unavailable["state"] == "unavailable"))
    missing_explicit = integrations.evaluate_integrations(
        config(executable_path=str(FRAMEWORK_ROOT / "does-not-exist")), FRAMEWORK_ROOT, FRAMEWORK_ROOT,
        checked_at=timestamp, runner=integrations._run,
    )[0]
    results.append(check("missing explicit RTK executable is unavailable with actionable evidence", missing_explicit["state"] == "unavailable"))
    results.append(check("unavailable + degrade does not fail core doctor", integrations.integration_problems(config(), [unavailable]) == []))
    results.append(check(
        "unavailable + fail-closed becomes a doctor failure",
        bool(integrations.integration_problems(config(policy="fail-closed"), [unavailable])),
    ))

    boundary = integrations.evaluate_integrations(
        config(boundary="external-api"), FRAMEWORK_ROOT, FRAMEWORK_ROOT,
        checked_at=timestamp, which=lambda _name: "fake-rtk", runner=FakeRunner(),
    )[0]
    results.append(check("RTK external-api boundary is misconfigured", boundary["state"] == "misconfigured"))

    incompatible = integrations.evaluate_integrations(
        config(), FRAMEWORK_ROOT, FRAMEWORK_ROOT,
        checked_at=timestamp, which=lambda _name: "fake-rtk", runner=FakeRunner(version="9.9.9"),
    )[0]
    results.append(check("incompatible RTK version is misconfigured", incompatible["state"] == "misconfigured"))

    # 0.2.4: only exit 127 counted as "could not be started", so a wrapper
    # that failed to launch was reported as a configuration error and sent
    # the operator to edit a value that was already correct. Every non-zero
    # exit with nothing on stdout means the same thing and now says so.
    for exit_code in (1, 9009):
        dead = integrations.evaluate_integrations(
            config(), FRAMEWORK_ROOT, FRAMEWORK_ROOT,
            checked_at=timestamp, which=lambda _name: "fake-rtk",
            runner=FakeRunner(version_exit=exit_code),
        )[0]
        probe = [item for item in dead["capabilities"] if item["id"] == "version-probe"]
        results.append(check(
            f"RTK probe exiting {exit_code} with no output is unavailable, not misconfigured",
            dead["state"] == "unavailable"
            and len(probe) == 1
            and "could not be started" in probe[0]["evidence"]["summary"],
            f"{dead['state']} {probe}",
        ))
    results.append(check(
        "an RTK probe that exits 0 with an unusable version is still misconfigured",
        integrations.evaluate_integrations(
            config(), FRAMEWORK_ROOT, FRAMEWORK_ROOT,
            checked_at=timestamp, which=lambda _name: "fake-rtk",
            runner=FakeRunner(version="not-a-version"),
        )[0]["state"] == "misconfigured",
    ))

    healthy = integrations.evaluate_integrations(
        config(), FRAMEWORK_ROOT, FRAMEWORK_ROOT,
        checked_at=timestamp, which=lambda _name: "fake-rtk", runner=FakeRunner(),
    )[0]
    results.append(check("compatible RTK plus all required canaries is healthy", healthy["state"] == "healthy"))
    results.append(check("healthy RTK result conforms to the public health schema", not integrations.validate_health_results([healthy], FRAMEWORK_ROOT)))

    degraded = integrations.evaluate_integrations(
        config(), FRAMEWORK_ROOT, FRAMEWORK_ROOT,
        checked_at=timestamp, which=lambda _name: "fake-rtk", runner=FakeRunner(search_passes=False),
    )[0]
    failed = {item["id"] for item in degraded["capabilities"] if item["status"] == "fail"}
    results.append(check("failed grep canary produces explicit degraded state", degraded["state"] == "degraded" and failed == {"grep-alternation"}, str(failed)))

    raw_args = Namespace(
        command_class="proxy-explicit", route="raw-proxy", outcome="success",
        raw_bytes=400, emitted_bytes=40,
    )
    raw_event = telemetry.build_event(raw_args, FRAMEWORK_ROOT)
    results.append(check(
        "raw proxy is structurally zero-savings and ineligible",
        raw_event["estimated_saved_tokens"] == 0 and raw_event["savings_eligible"] is False,
    ))
    forbidden = {"command", "argv", "cwd", "path", "output"}
    results.append(check("telemetry event contains no content-bearing field", not forbidden.intersection(raw_event)))
    results.append(check("telemetry event validates against its strict schema", not telemetry.validate_event(raw_event, FRAMEWORK_ROOT)))
    for route in ("raw-proxy", "parse-failure", "unsupported"):
        event = telemetry.build_event(Namespace(
            command_class="route-canary", route=route, outcome="success",
            raw_bytes=400, emitted_bytes=40, attempt_id="attempt-zero-savings",
        ), FRAMEWORK_ROOT)
        results.append(check(
            f"{route} telemetry is always zero-savings",
            event["estimated_saved_tokens"] == 0 and event["savings_eligible"] is False,
        ))
    failed_filtered = telemetry.build_event(Namespace(
        command_class="grep-simple", route="native-guarded", outcome="degraded",
        raw_bytes=400, emitted_bytes=40, attempt_id="attempt-failed-canary",
    ), FRAMEWORK_ROOT)
    results.append(check(
        "failed or degraded filtered route cannot report savings",
        failed_filtered["estimated_saved_tokens"] == 0
        and failed_filtered["savings_eligible"] is False
        and not telemetry.validate_event(failed_filtered, FRAMEWORK_ROOT),
    ))

    with tempfile.TemporaryDirectory(prefix="eif-rtk-telemetry-") as raw_tmp:
        instance = Path(raw_tmp)
        record_rc = telemetry.main([
            "record", "--instance-root", str(instance), "--framework-root", str(FRAMEWORK_ROOT),
            "--command-class", "git-native", "--route", "native-filtered", "--outcome", "success",
            "--raw-bytes", "400", "--emitted-bytes", "40", "--attempt-id", "benchmark-attempt-001",
        ])
        store = instance / ".eif" / "local-state" / "rtk-telemetry.jsonl"
        stored = json.loads(store.read_text(encoding="utf-8")) if store.exists() else {}
        results.append(check(
            "content-free event is written only to local-state and attributed to one attempt",
            record_rc == 0
            and stored.get("command_class") == "git-native"
            and stored.get("attempt_id") == "benchmark-attempt-001",
        ))

    registry = json.loads((FRAMEWORK_ROOT / "integrations" / "rtk" / "command-registry.json").read_text(encoding="utf-8"))
    proxy_routes = [route for route in registry["routes"] if route["route"] == "raw-proxy"]
    results.append(check("every raw proxy registry route is zero-savings", all(not route["savings_eligible"] and not route["filtering_expected"] for route in proxy_routes)))
    capabilities_path = FRAMEWORK_ROOT / "integrations" / "rtk" / "adapter-capabilities.json"
    capabilities = json.loads(capabilities_path.read_text(encoding="utf-8"))
    capability_errors = integrations._validate(
        capabilities,
        FRAMEWORK_ROOT / "core" / "schemas" / "rtk-adapter-capabilities.schema.json",
    )
    results.append(check(
        "provider/version capability matrix conforms to its strict schema",
        not capability_errors,
        str(capability_errors),
    ))
    results.append(check(
        "RTK capability matrix covers exactly the four registered adapter names",
        set(capabilities["adapters"]) == {"claude-code", "cursor", "codex", "hermes"},
    ))
    generated = guidance.generated_outputs(registry, capabilities)
    stale = [
        path.relative_to(FRAMEWORK_ROOT).as_posix()
        for path, expected in generated.items()
        if not path.exists() or path.read_text(encoding="utf-8") != expected
    ]
    results.append(check(
        "one registry deterministically generates universal guidance and all adapter consumers",
        not stale,
        str(stale),
    ))
    hook_contracts = [
        json.loads(content)
        for path, content in generated.items()
        if path.parent.name == "hooks"
    ]
    results.append(check(
        "every generated hook contract is optional, non-installing and provider-mode explicit",
        len(hook_contracts) == 4
        and all(
            contract["template_only"] is True
            and contract["installed"] is False
            and contract["behavior"] in {"rewrite-capable", "block-only"}
            and contract["safety"]["user_config_mutated_by_generator"] is False
            for contract in hook_contracts
        ),
    ))
    return results


def real_host_result() -> bool:
    actual = integrations.evaluate_integrations(config(), FRAMEWORK_ROOT, FRAMEWORK_ROOT)[0]
    print(json.dumps(actual, indent=2, sort_keys=True))
    failed = [item["id"] for item in actual["capabilities"] if item["status"] == "fail"]
    return check(
        "real host resolves RTK as healthy or explicit degraded with schema-valid evidence",
        actual["state"] in {"healthy", "degraded"} and not integrations.validate_health_results([actual], FRAMEWORK_ROOT),
        f"state={actual['state']} failed={failed}",
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--real", action="store_true", help="Also run the installed RTK behavioral canary once.")
    args = ap.parse_args(argv)
    results = unit_results()
    if args.real:
        results.append(real_host_result())
    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_rtk_integration: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
