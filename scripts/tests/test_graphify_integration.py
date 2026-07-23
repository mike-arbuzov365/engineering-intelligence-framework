#!/usr/bin/env python3
"""Deterministic Graphify lifecycle, adapter and optional real-host tests."""
from __future__ import annotations

import argparse
import gzip
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from subprocess import CompletedProcess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eif_graphify as lifecycle  # noqa: E402
import eif_integrations as integrations  # noqa: E402


FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_GRAPH = (
    FRAMEWORK_ROOT
    / "integrations"
    / "graphify"
    / "fixtures"
    / "structural-canary"
    / "graphify-out"
    / "graph.json"
)
TIMESTAMP = "2026-07-21T00:00:00Z"
GENERATED_AT = "2026-07-21T00:00:00Z"


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


def graph_entry(**overrides: object) -> dict:
    entry = {
        "artifact_path": "graphify-out/graph.json",
        "metadata_path": "graphify-out/eif-graph-metadata.json",
        "scope_manifest_path": ".eif/graphify-scope.json",
    }
    entry.update(overrides)
    return entry


def scope_manifest(*, suppressed: bool = False) -> dict:
    result = {
        "schema_version": 1,
        "repo_id": "portable-canary",
        "source_paths": ["source.py", "docs"],
        "semantic_paths": ["docs"],
        "exclude_paths": ["docs/generated"],
        "suppressed": suppressed,
    }
    if suppressed:
        result["suppression_reason"] = "synthetic policy fixture"
    return result


def write_scope(repo: Path, scope: dict) -> None:
    target = repo / ".eif" / "graphify-scope.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(scope, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def capture(repo: Path) -> dict:
    return lifecycle.capture_metadata(
        repo,
        graph_entry(),
        "0.9.12",
        generated_at=GENERATED_AT,
        root=FRAMEWORK_ROOT,
    )


def make_repo(parent: Path) -> tuple[Path, str]:
    repo = parent / "worktree-name-must-not-be-identity"
    repo.mkdir()
    run_git(repo, "init", "-q")
    run_git(repo, "config", "user.email", "eif-canary@example.invalid")
    run_git(repo, "config", "user.name", "EIF Canary")
    graph_dir = repo / "graphify-out"
    graph_dir.mkdir()
    shutil.copy2(FIXTURE_GRAPH, graph_dir / "graph.json")
    (repo / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
    docs = repo / "docs"
    docs.mkdir()
    (docs / "meaning.md").write_text("# Stable meaning\n", encoding="utf-8")
    write_scope(repo, scope_manifest())
    run_git(repo, "add", "source.py", "docs/meaning.md", ".eif/graphify-scope.json")
    run_git(repo, "commit", "-q", "-m", "baseline")
    baseline = run_git(repo, "rev-parse", "HEAD")
    capture(repo)
    return repo, baseline


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
    metadata_path: str = "graphify-out/eif-graph-metadata.json",
    scope_manifest_path: str = ".eif/graphify-scope.json",
    executable_path: str | None = None,
    policy: str = "degrade",
) -> dict:
    entry = {
        "enabled": enabled,
        "provider": "graphify" if enabled else None,
        "mode": mode,
        "artifact_path": artifact_path,
        "metadata_path": metadata_path,
        "scope_manifest_path": scope_manifest_path,
        "baseline_commit": baseline,
        "processing": processing,
        "data_boundary": boundary,
        "cost_cap_usd": cost_cap,
        "failure_policy": policy,
    }
    if semantic_provider is not None:
        entry["semantic_provider"] = semantic_provider
    if executable_path is not None:
        entry["executable_path"] = executable_path
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
        metadata_path = instance / "graphify-out" / "eif-graph-metadata.json"
        graph_path = instance / "graphify-out" / "graph.json"
        scope_path = instance / ".eif" / "graphify-scope.json"

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        results.append(check(
            "artifact metadata contains every D-08 field and validates",
            {
                "source_commit", "graphify_version", "manifest_hash",
                "scope_hash", "generated_at"
            }.issubset(metadata)
            and not lifecycle._validate(
                metadata, "graphify-artifact-metadata.schema.json", FRAMEWORK_ROOT
            ),
        ))

        disabled_runner = FakeRunner()
        disabled = evaluate(instance, config(baseline, enabled=False), disabled_runner)
        results.append(check(
            "disabled Graphify executes no provider probe",
            disabled["state"] == "disabled" and not disabled_runner.calls,
        ))

        healthy = evaluate(instance, config(baseline))
        results.append(check(
            "compatible Graphify plus fresh lifecycle and canaries is healthy",
            healthy["state"] == "healthy",
            healthy["state"],
        ))
        results.append(check(
            "healthy Graphify result conforms to public health schema",
            not integrations.validate_health_results([healthy], FRAMEWORK_ROOT),
        ))
        results.append(check(
            "freshness uses explicit repo identity rather than worktree folder name",
            lifecycle.evaluate_status(instance, graph_entry(), root=FRAMEWORK_ROOT)["repo_id"]
            == "portable-canary"
            and instance.name != "portable-canary",
        ))
        results.append(check(
            "fresh status records hashes, source commit and mandatory source verification",
            healthy["freshness"]["state"] == "fresh"
            and healthy["freshness"]["baseline_commit"] == baseline
            and healthy["freshness"]["manifest_hash"].startswith("sha256:")
            and healthy["freshness"]["scope_hash"].startswith("sha256:")
            and healthy["freshness"]["source_verification_required"] is True,
        ))

        (instance / "source.py").write_text("VALUE = 2\n", encoding="utf-8")
        run_git(instance, "add", "source.py")
        run_git(instance, "commit", "-q", "-m", "source change")
        code_update = evaluate(instance, config(baseline))
        results.append(check(
            "structural source drift is code-update-required and maps to stale",
            code_update["state"] == "stale"
            and code_update["freshness"]["state"] == "code-update-required"
            and code_update["freshness"]["changed_source_files"] == 1,
        ))

        (instance / "docs" / "meaning.md").write_text("# Changed meaning\n", encoding="utf-8")
        run_git(instance, "add", "docs/meaning.md")
        run_git(instance, "commit", "-q", "-m", "semantic change")
        semantic_update = evaluate(instance, config(baseline))
        results.append(check(
            "semantic source drift is semantic-update-required and core-safe",
            semantic_update["state"] == "stale"
            and semantic_update["freshness"]["state"] == "semantic-update-required",
        ))

        capture(instance)
        refreshed_commit = run_git(instance, "rev-parse", "HEAD")
        results.append(check(
            "capturing structural metadata at current HEAD restores fresh",
            evaluate(instance, config(refreshed_commit))["state"] == "healthy",
        ))

        original_scope = scope_path.read_bytes()
        drifted_scope = scope_manifest()
        drifted_scope["source_paths"].append("new-area")
        write_scope(instance, drifted_scope)
        scope_drift = evaluate(instance, config(refreshed_commit))
        results.append(check(
            "manifest or scope hash drift requires semantic update",
            scope_drift["freshness"]["state"] == "semantic-update-required",
        ))
        scope_path.write_bytes(original_scope)

        write_scope(instance, scope_manifest(suppressed=True))
        suppressed = evaluate(instance, config(refreshed_commit))
        results.append(check(
            "explicit suppression is fail-loud and skips provider calls",
            suppressed["state"] == "degraded"
            and suppressed["freshness"]["state"] == "suppressed",
        ))
        scope_path.write_bytes(original_scope)

        original_metadata = metadata_path.read_bytes()
        metadata_path.unlink()
        missing_metadata = evaluate(instance, config(refreshed_commit))
        results.append(check(
            "missing metadata is blocked and never healthy",
            missing_metadata["state"] == "degraded"
            and missing_metadata["freshness"]["state"] == "blocked",
        ))
        metadata_path.write_bytes(original_metadata)

        metadata_path.write_text("{}\n", encoding="utf-8")
        invalid_metadata = evaluate(instance, config(refreshed_commit))
        results.append(check(
            "invalid metadata is blocked and never silently replaced by a report",
            invalid_metadata["freshness"]["state"] == "blocked",
        ))
        metadata_path.write_bytes(original_metadata)

        original_graph = graph_path.read_bytes()
        graph_path.unlink()
        missing_graph = evaluate(instance, config(refreshed_commit))
        results.append(check(
            "missing raw graph is blocked and core-safe",
            missing_graph["state"] == "degraded"
            and missing_graph["freshness"]["state"] == "blocked",
        ))
        graph_path.write_bytes(original_graph)

        unrelated_tree = run_git(instance, "write-tree")
        unrelated = run_git(instance, "commit-tree", unrelated_tree, "-m", "unrelated graph baseline")
        diverged_metadata = json.loads(original_metadata)
        diverged_metadata["source_commit"] = unrelated
        metadata_path.write_text(json.dumps(diverged_metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        diverged = evaluate(instance, config(unrelated))
        results.append(check(
            "non-ancestor source commit requires a full rebuild",
            diverged["state"] == "misconfigured"
            and diverged["freshness"]["state"] == "full-rebuild-required",
        ))
        metadata_path.write_bytes(original_metadata)

        escaped = evaluate(instance, config(refreshed_commit, artifact_path="../graph.json"))
        results.append(check("artifact path escape is misconfigured", escaped["state"] == "misconfigured"))

        mismatch = evaluate(instance, config("1" * 40))
        results.append(check(
            "config baseline conflict with metadata fails closed",
            mismatch["state"] == "misconfigured",
        ))

        gated = evaluate(instance, config(
            refreshed_commit,
            mode="semantic",
            processing="external",
            boundary="external-api",
            cost_cap=0,
        ))
        results.append(check(
            "semantic mode without provider and positive cap fails closed",
            gated["state"] == "misconfigured",
        ))

        semantic_runner = FakeRunner()
        semantic = evaluate(instance, config(
            refreshed_commit,
            mode="semantic",
            processing="external",
            boundary="external-api",
            cost_cap=1,
            semantic_provider="explicit-test-provider",
        ), semantic_runner)
        results.append(check(
            "complete semantic gate stays degraded and doctor initiates no provider scan",
            semantic["state"] == "degraded"
            and all(call[1] in {"--version", "query", "path", "explain"} for call in semantic_runner.calls),
        ))

        unavailable = evaluate(instance, config(refreshed_commit), available=False)
        results.append(check("missing Graphify executable is unavailable, not healthy", unavailable["state"] == "unavailable"))
        results.append(check(
            "unavailable plus degrade does not fail core doctor",
            integrations.integration_problems(config(refreshed_commit), [unavailable]) == [],
        ))
        results.append(check(
            "unavailable plus fail-closed becomes a doctor failure",
            bool(integrations.integration_problems(config(refreshed_commit, policy="fail-closed"), [unavailable])),
        ))

        incompatible = evaluate(instance, config(refreshed_commit), FakeRunner(version="9.9.9"))
        results.append(check("incompatible Graphify version is misconfigured", incompatible["state"] == "misconfigured"))

        canary_failure = evaluate(instance, config(refreshed_commit), FakeRunner(fail_command="path"))
        failed = {item["id"] for item in canary_failure["capabilities"] if item["status"] == "fail"}
        results.append(check(
            "failed path canary produces explicit degraded state",
            canary_failure["state"] == "degraded" and "path-canary" in failed,
            str(failed),
        ))

        manifest, manifest_errors = integrations._manifest(FRAMEWORK_ROOT, "graphify")
        results.append(check(
            "Graphify provider manifest conforms to strict public schema",
            manifest is not None and not manifest_errors,
            str(manifest_errors),
        ))

        archive = Path(raw_tmp) / "portable-graph.json.gz"
        with gzip.open(archive, "wb") as handle:
            handle.write(original_graph)
        metadata_source = Path(raw_tmp) / "metadata.json"
        metadata_source.write_bytes(original_metadata)
        graph_path.unlink()
        metadata_path.unlink()
        restored = lifecycle.restore_artifact(
            instance,
            graph_entry(),
            archive,
            metadata_source,
            root=FRAMEWORK_ROOT,
        )
        results.append(check(
            "portable restore validates identity, hashes and returns fresh without folder-derived ID",
            restored["state"] == "fresh"
            and restored["repo_id"] == "portable-canary"
            and graph_path.read_bytes() == original_graph,
        ))
    return results


def real_host_result() -> bool:
    with tempfile.TemporaryDirectory(prefix="eif-graphify-real-") as raw_tmp:
        instance, baseline = make_repo(Path(raw_tmp))
        actual = integrations.evaluate_integrations(
            config(baseline), FRAMEWORK_ROOT, instance
        )[0]
    print(json.dumps(actual, indent=2, sort_keys=True))
    return check(
        "real host Graphify passes bounded structural canaries with fresh schema-valid evidence",
        actual["state"] == "healthy"
        and not integrations.validate_health_results([actual], FRAMEWORK_ROOT),
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
