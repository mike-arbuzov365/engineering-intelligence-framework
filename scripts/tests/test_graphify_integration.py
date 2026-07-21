#!/usr/bin/env python3
"""Deterministic Graphify adapter, freshness and optional real-host tests."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from subprocess import CompletedProcess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eif_integrations as integrations  # noqa: E402


FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_GRAPH = FRAMEWORK_ROOT / "integrations" / "graphify" / "fixtures" / "structural-canary" / "graphify-out" / "graph.json"
TIMESTAMP = "2026-07-21T00:00:00Z"


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return bool(condition)


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout.strip()


def make_repo(parent: Path) -> tuple[Path, str]:
    repo = parent / "instance"
    repo.mkdir()
    run_git(repo, "init", "-q")
    run_git(repo, "config", "user.email", "eif-canary@example.invalid")
    run_git(repo, "config", "user.name", "EIF Canary")
    graph_dir = repo / "graphify-out"
    graph_dir.mkdir()
    shutil.copy2(FIXTURE_GRAPH, graph_dir / "graph.json")
    (repo / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
    run_git(repo, "add", "source.py")
    run_git(repo, "commit", "-q", "-m", "baseline")
    return repo, run_git(repo, "rev-parse", "HEAD")


def config(
    baseline: str | None,
    *,
    enabled: bool = True,
    mode: str = "structural",
    processing: str = "local",
    boundary: str = "local-only",
    cost_cap: float = 0,
    semantic_provider: str | None = None,
    artifact_path: str = "graphify-out/graph.json",
    policy: str = "degrade",
) -> dict:
    entry = {
        "enabled": enabled,
        "provider": "graphify" if enabled else None,
        "mode": mode,
        "artifact_path": artifact_path,
        "baseline_commit": baseline,
        "processing": processing,
        "data_boundary": boundary,
        "cost_cap_usd": cost_cap,
        "failure_policy": policy,
    }
    if semantic_provider is not None:
        entry["semantic_provider"] = semantic_provider
    return {"integrations": {"structural_graph": entry}}


class FakeRunner:
    def __init__(self, *, version: str = "0.9.12", fail_command: str | None = None):
        self.version = version
        self.fail_command = fail_command
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], cwd: Path | None, timeout: float) -> CompletedProcess:
        del cwd, timeout
        self.calls.append(argv)
        if argv[1:] == ["--version"]:
            return CompletedProcess(argv, 0, f"graphify {self.version}\n", "")
        command = argv[1] if len(argv) > 1 else ""
        if command == self.fail_command:
            return CompletedProcess(argv, 2, "", "synthetic failure")
        if command == "query":
            return CompletedProcess(argv, 0, "PaymentService InvoiceRepository CALLS\n", "")
        if command == "path":
            return CompletedProcess(argv, 0, "CheckoutController -> PaymentService -> InvoiceRepository\n", "")
        if command == "explain":
            return CompletedProcess(argv, 0, "PaymentService CALLS InvoiceRepository\n", "")
        return CompletedProcess(argv, 1, "", "unexpected fake command")


def evaluate(instance: Path, cfg: dict, runner: FakeRunner | None = None, *, available: bool = True) -> dict:
    return integrations.evaluate_integrations(
        cfg,
        FRAMEWORK_ROOT,
        instance,
        checked_at=TIMESTAMP,
        which=(lambda _name: "fake-graphify") if available else (lambda _name: None),
        runner=runner or FakeRunner(),
    )[0]


def unit_results() -> list[bool]:
    results: list[bool] = []
    with tempfile.TemporaryDirectory(prefix="eif-graphify-test-") as raw_tmp:
        instance, baseline = make_repo(Path(raw_tmp))

        disabled_runner = FakeRunner()
        disabled = evaluate(instance, config(baseline, enabled=False), disabled_runner)
        results.append(check("disabled Graphify executes no provider probe", disabled["state"] == "disabled" and not disabled_runner.calls))

        healthy = evaluate(instance, config(baseline))
        results.append(check("compatible Graphify plus fresh artifact and canaries is healthy", healthy["state"] == "healthy", healthy["state"]))
        results.append(check("healthy Graphify result conforms to public health schema", not integrations.validate_health_results([healthy], FRAMEWORK_ROOT)))
        results.append(check(
            "freshness records baseline, current and merge base",
            healthy["freshness"] == {
                "state": "fresh",
                "baseline_commit": baseline,
                "current_commit": baseline,
                "merge_base": baseline,
            },
            json.dumps(healthy["freshness"], sort_keys=True),
        ))

        (instance / "source.py").write_text("VALUE = 2\n", encoding="utf-8")
        run_git(instance, "add", "source.py")
        run_git(instance, "commit", "-q", "-m", "source change")
        stale = evaluate(instance, config(baseline))
        results.append(check("ancestor baseline is stale after a source commit", stale["state"] == "stale" and stale["freshness"]["state"] == "stale"))

        unknown = evaluate(instance, config(None))
        results.append(check("missing baseline is degraded with unknown freshness", unknown["state"] == "degraded" and unknown["freshness"]["state"] == "unknown"))
        results.append(check(
            "freshness classifier distinguishes divergence",
            integrations.classify_graph_freshness("1" * 40, "2" * 40, "3" * 40) == "diverged",
        ))
        tree = run_git(instance, "write-tree")
        diverged_baseline = run_git(instance, "commit-tree", tree, "-m", "unrelated graph baseline")
        diverged = evaluate(instance, config(diverged_baseline))
        results.append(check(
            "unrelated reachable baseline is misconfigured as diverged",
            diverged["state"] == "misconfigured" and diverged["freshness"]["state"] == "diverged",
        ))

        escaped = evaluate(instance, config(baseline, artifact_path="../graph.json"))
        results.append(check("artifact path escape is misconfigured", escaped["state"] == "misconfigured"))

        missing = evaluate(instance, config(baseline, artifact_path="graphify-out/missing.json"))
        results.append(check("missing raw graph is degraded, never healthy", missing["state"] == "degraded"))

        gated = evaluate(instance, config(
            baseline,
            mode="semantic",
            processing="external",
            boundary="external-api",
            cost_cap=0,
        ))
        results.append(check("semantic mode without provider and positive cap fails closed", gated["state"] == "misconfigured"))

        semantic_runner = FakeRunner()
        semantic = evaluate(instance, config(
            run_git(instance, "rev-parse", "HEAD"),
            mode="semantic",
            processing="external",
            boundary="external-api",
            cost_cap=1,
            semantic_provider="explicit-test-provider",
        ), semantic_runner)
        results.append(check(
            "complete semantic gate stays degraded because doctor does not execute paid scans",
            semantic["state"] == "degraded" and all(call[1] in {"--version", "query", "path", "explain"} for call in semantic_runner.calls),
        ))

        unavailable = evaluate(instance, config(run_git(instance, "rev-parse", "HEAD")), available=False)
        results.append(check("missing Graphify executable is unavailable, not healthy", unavailable["state"] == "unavailable"))
        results.append(check("unavailable + degrade does not fail core doctor", integrations.integration_problems(config(baseline), [unavailable]) == []))
        results.append(check(
            "unavailable + fail-closed becomes a doctor failure",
            bool(integrations.integration_problems(config(baseline, policy="fail-closed"), [unavailable])),
        ))

        incompatible = evaluate(instance, config(run_git(instance, "rev-parse", "HEAD")), FakeRunner(version="9.9.9"))
        results.append(check("incompatible Graphify version is misconfigured", incompatible["state"] == "misconfigured"))

        canary_failure = evaluate(instance, config(run_git(instance, "rev-parse", "HEAD")), FakeRunner(fail_command="path"))
        failed = {item["id"] for item in canary_failure["capabilities"] if item["status"] == "fail"}
        results.append(check("failed path canary produces explicit degraded state", canary_failure["state"] == "degraded" and "path-canary" in failed, str(failed)))

        manifest, manifest_errors = integrations._manifest(FRAMEWORK_ROOT, "graphify")
        results.append(check("Graphify provider manifest conforms to strict public schema", manifest is not None and not manifest_errors, str(manifest_errors)))
    return results


def real_host_result() -> bool:
    with tempfile.TemporaryDirectory(prefix="eif-graphify-real-") as raw_tmp:
        instance, baseline = make_repo(Path(raw_tmp))
        actual = integrations.evaluate_integrations(config(baseline), FRAMEWORK_ROOT, instance)[0]
    print(json.dumps(actual, indent=2, sort_keys=True))
    return check(
        "real host Graphify passes bounded structural canaries with fresh schema-valid evidence",
        actual["state"] == "healthy" and not integrations.validate_health_results([actual], FRAMEWORK_ROOT),
        f"state={actual['state']}",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real", action="store_true", help="Also run installed Graphify structural canaries once.")
    args = parser.parse_args(argv)
    results = unit_results()
    if args.real:
        results.append(real_host_result())
    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_graphify_integration: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
