#!/usr/bin/env python3
"""Tests for eif_benchmark.py against a fake, deterministic agent runner
(scripts/tests/fixtures/benchmark/fake_agent_runner.py) - no real agent,
no network, no cost. Proves the properties this round's owner instruction
named explicitly: seeded mode-order reproducibility, invalid-manifest
rejection, retained failed/crashed attempts, append-only raw records,
aggregation derived from records (not hand-summarized), tests_passed <=
tests_total enforcement, mixed tool-version detection, variance/CI
calculation, pre-publication privacy scanning, and that a token-count
figure is never reported without an accompanying quality figure.

Usage:
    python scripts/tests/test_benchmark.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
FRAMEWORK_ROOT = SCRIPTS_DIR.parent
BENCHMARK_SCRIPT = SCRIPTS_DIR / "eif_benchmark.py"
FAKE_AGENT = SCRIPTS_DIR / "tests" / "fixtures" / "benchmark" / "fake_agent_runner.py"
FAKE_EIFCTL = SCRIPTS_DIR / "tests" / "fixtures" / "benchmark" / "fake_eifctl.py"
FIXTURES_DIR = FRAMEWORK_ROOT / "docs" / "benchmarks" / "fixtures"
T02 = FIXTURES_DIR / "T02-fix-a-bug"
T07 = FIXTURES_DIR / "T07-avoid-repeating-a-known-failed-fix"

sys.path.insert(0, str(SCRIPTS_DIR))
from eif_benchmark import (  # noqa: E402
    _confidence_interval_95,
    cmd_aggregate,
    randomize_mode_order,
)


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def run_benchmark(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(
        [sys.executable, str(BENCHMARK_SCRIPT), *args],
        capture_output=True, text=True, env=full_env,
    )


def materialize_and_run(fixture: Path, work_dir: Path, behavior: str, **run_kwargs) -> tuple[subprocess.CompletedProcess, Path]:
    run_benchmark("materialize", str(fixture), str(work_dir), "--mode", "A_baseline")
    out_path = work_dir.parent / f"{work_dir.name}-results.jsonl"
    args = ["run", str(fixture), str(work_dir), "--mode", "A_baseline",
            "--agent-runner", sys.executable, str(FAKE_AGENT), "--out", str(out_path)]
    for key, value in run_kwargs.items():
        args += [f"--{key.replace('_', '-')}", str(value)]
    proc = run_benchmark(*args, env={"EIF_FAKE_AGENT_BEHAVIOR": behavior})
    return proc, out_path


def make_eifctl_shim(root: Path) -> Path:
    if os.name == "nt":
        shim = root / "fake-eifctl.cmd"
        shim.write_text(f'@"{sys.executable}" "{FAKE_EIFCTL}" %*\n', encoding="utf-8")
    else:
        shim = root / "fake-eifctl"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_EIFCTL}" "$@"\n', encoding="utf-8")
        shim.chmod(0o755)
    return shim


def write_integration_contract(
    root: Path,
    *,
    rtk_state: str = "healthy",
) -> tuple[Path, Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    graph_path = root / "structural-graph.json"
    graph_path.write_text(json.dumps({
        "directed": True,
        "multigraph": False,
        "nodes": [
            {"id": "src/pricing.py::calculate_price", "label": "calculate_price"},
            {"id": "tests/test_pricing.py::boundary", "label": "boundary"},
        ],
        "links": [
            {
                "source": "tests/test_pricing.py::boundary",
                "target": "src/pricing.py::calculate_price",
                "relation": "CALLS",
            }
        ],
    }), encoding="utf-8")
    graph_metadata_path = root / "graph-metadata.json"
    graph_metadata_path.write_text(json.dumps({
        "schema_version": 1,
        "repo_id": "benchmark-fixture",
        "source_commit": "a" * 40,
        "graphify_version": "0.9.12",
        "manifest_hash": "sha256:" + "b" * 64,
        "scope_hash": "sha256:" + "c" * 64,
        "graph_sha256": "sha256:" + hashlib.sha256(graph_path.read_bytes()).hexdigest(),
        "generated_at": "2026-07-23T00:00:00Z",
    }), encoding="utf-8")

    def capability(capability_id: str) -> dict:
        return {
            "id": capability_id,
            "required": True,
            "status": "pass",
            "evidence": {
                "kind": "canary",
                "summary": "deterministic contract fixture passed",
                "content_free": True,
            },
        }

    graphify = {
        "schema_version": 1,
        "integration": "structural_graph",
        "provider": "graphify",
        "state": "healthy",
        "checked_at": "2026-07-23T00:00:00Z",
        "data_boundary": "local-only",
        "version": {
            "detected": "0.9.12",
            "compatible": True,
            "constraint": ">=0.9.0,<1.0.0",
        },
        "capabilities": [
            capability("artifact-policy"),
            capability("semantic-gate"),
            capability("git-freshness"),
            capability("query-canary"),
            capability("path-canary"),
            capability("explain-canary"),
        ],
        "freshness": {
            "state": "fresh",
            "baseline_commit": "a" * 40,
            "current_commit": "a" * 40,
            "merge_base": "a" * 40,
            "manifest_hash": "sha256:" + "b" * 64,
            "scope_hash": "sha256:" + "c" * 64,
            "changed_source_files": 0,
            "source_verification_required": True,
        },
        "remediation": [
            "Verify every graph-derived claim against source files before editing."
        ],
    }
    rtk_capability_ids = [
        "version-probe",
        "cli-surface",
        "proxy-argv",
        "grep-alternation",
        "git-diff",
        "content-free-telemetry",
    ]
    rtk = {
        "schema_version": 1,
        "integration": "shell_output_compression",
        "provider": "rtk",
        "state": rtk_state,
        "checked_at": "2026-07-23T00:00:00Z",
        "data_boundary": "local-only",
        "version": {
            "detected": "0.43.0",
            "compatible": True,
            "constraint": ">=0.42.0,<0.44.0",
        },
        "capabilities": [capability(item) for item in rtk_capability_ids],
        "freshness": {
            "state": "not-applicable",
            "baseline_commit": None,
            "current_commit": None,
            "merge_base": None,
            "manifest_hash": None,
            "scope_hash": None,
            "changed_source_files": 0,
            "source_verification_required": False,
        },
        "remediation": [] if rtk_state == "healthy" else ["Use a core-safe fallback."],
    }
    if rtk_state != "healthy":
        rtk["capabilities"][3]["status"] = "fail"
    report_path = root / "integration-health.json"
    report_path.write_text(
        json.dumps({"schema_version": 1, "results": [graphify, rtk]}, indent=2),
        encoding="utf-8",
    )
    return report_path, graph_path, graph_metadata_path


def real_host_mode_d_contract(root: Path) -> tuple[bool, str]:
    """One local, zero-cost mode D contract using real provider canaries."""
    from eif_graphify import capture_metadata
    from eif_integrations import evaluate_integrations, validate_health_results

    source_repo = root / "real-host-graph-source"
    shutil.copytree(
        T02 / "source",
        source_repo,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    git_commands = [
        ["git", "init", "-q"],
        ["git", "config", "user.email", "eif-canary@example.invalid"],
        ["git", "config", "user.name", "EIF Canary"],
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", "source baseline"],
    ]
    for command in git_commands:
        proc = subprocess.run(command, cwd=source_repo, capture_output=True, text=True)
        if proc.returncode != 0:
            return False, f"Git setup failed: {proc.stdout}{proc.stderr}"

    graph_dir = source_repo / "graphify-out"
    graph_dir.mkdir()
    graph_path = graph_dir / "graph.json"
    graph_path.write_text(json.dumps({
        "directed": True,
        "multigraph": False,
        "nodes": [
            {"id": "src/pricing.py::calculate_price", "label": "calculate_price"},
            {"id": "tests/test_pricing.py::boundary", "label": "boundary"},
        ],
        "links": [
            {
                "source": "tests/test_pricing.py::boundary",
                "target": "src/pricing.py::calculate_price",
                "relation": "CALLS",
            }
        ],
    }), encoding="utf-8")
    scope_path = source_repo / ".eif" / "graphify-scope.json"
    scope_path.parent.mkdir()
    scope_path.write_text(json.dumps({
        "schema_version": 1,
        "repo_id": "benchmark-real-host",
        "source_paths": ["src", "tests"],
        "semantic_paths": [],
        "exclude_paths": [".eif", "graphify-out"],
        "suppressed": False,
    }), encoding="utf-8")
    graph_entry = {
        "enabled": True,
        "provider": "graphify",
        "mode": "structural",
        "artifact_path": "graphify-out/graph.json",
        "metadata_path": "graphify-out/eif-graph-metadata.json",
        "scope_manifest_path": ".eif/graphify-scope.json",
        "baseline_commit": None,
        "processing": "local",
        "data_boundary": "local-only",
        "cost_cap_usd": 0,
        "failure_policy": "degrade",
    }
    capture_metadata(
        source_repo,
        graph_entry,
        "0.9.12",
        generated_at="2026-07-23T00:00:00+00:00",
        root=FRAMEWORK_ROOT,
    )
    config = {
        "integrations": {
            "shell_output_compression": {
                "enabled": True,
                "provider": "rtk",
                "processing": "local",
                "data_boundary": "local-only",
                "telemetry_enabled": False,
                "failure_policy": "degrade",
            },
            "structural_graph": graph_entry,
        }
    }
    health_results = evaluate_integrations(config, FRAMEWORK_ROOT, source_repo)
    schema_problems = validate_health_results(health_results, FRAMEWORK_ROOT)
    by_name = {item["integration"]: item for item in health_results}
    if schema_problems or any(
        by_name.get(name, {}).get("state") != "healthy"
        for name in ("shell_output_compression", "structural_graph")
    ):
        return False, json.dumps({
            "schema_problems": schema_problems,
            "states": {name: item.get("state") for name, item in by_name.items()},
        })
    report_path = root / "real-host-integration-health.json"
    report_path.write_text(
        json.dumps({"schema_version": 1, "results": health_results}, indent=2),
        encoding="utf-8",
    )
    work = root / "real-host-mode-d-work"
    out = root / "real-host-mode-d.jsonl"
    fake_eifctl = make_eifctl_shim(root)
    materialize = run_benchmark(
        "materialize", str(T02), str(work), "--mode", "D_full_stack",
        "--eifctl-path", str(fake_eifctl),
        "--integration-report", str(report_path),
        "--graph-artifact", str(graph_path),
        "--graph-metadata", str(source_repo / "graphify-out" / "eif-graph-metadata.json"),
    )
    run = run_benchmark(
        "run", str(T02), str(work), "--mode", "D_full_stack",
        "--agent-runner", sys.executable, str(FAKE_AGENT),
        "--out", str(out),
        env={"EIF_FAKE_AGENT_BEHAVIOR": "correct_fix"},
    )
    if not out.is_file():
        return False, materialize.stdout + materialize.stderr + run.stdout + run.stderr
    record = json.loads(out.read_text(encoding="utf-8").strip())
    valid = run_benchmark("validate-result", str(out))
    return (
        materialize.returncode == 0
        and run.returncode == 0
        and valid.returncode == 0
        and record["integration_evidence"]["graphify"]["consumption_verified"] is True
        and record["integration_evidence"]["rtk"]["telemetry_attempt_attributed"] is True,
        materialize.stdout + materialize.stderr + run.stdout + run.stderr + valid.stdout + valid.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real",
        action="store_true",
        help="Also run one zero-cost mode D contract with installed RTK and Graphify canaries.",
    )
    args = parser.parse_args(argv)
    results: list[bool] = []

    # --- seeded mode order reproducible ---
    # Adoption-hardening round fix: the prior version of this check
    # ("order1 != order3 or True") could never fail - two arbitrary seeds
    # (42, 99) might coincidentally land on the same permutation of only
    # 4 items (24 possible orders total), and "or True" papered over that
    # instead of picking seeds known not to collide. Fixed two ways: (1)
    # exact, hardcoded expected orders for two specific seeds, computed
    # directly from randomize_mode_order itself and pinned here as a
    # regression check (a change to the shuffle algorithm/seed handling
    # would be caught, not silently accepted); (2) a real distinctness
    # assertion across a deterministic seed set that CAN fail.
    modes = ["A_baseline", "B_eif_governance", "C_structural_navigation", "D_full_stack"]
    order1 = randomize_mode_order(modes, seed=42)
    order2 = randomize_mode_order(modes, seed=42)
    results.append(check("same seed produces the same mode order", order1 == order2, f"{order1} vs {order2}"))
    results.append(check("randomize_mode_order is an actual permutation, not a copy-through", sorted(order1) == sorted(modes)))

    seed0_order = randomize_mode_order(modes, seed=0)
    seed5_order = randomize_mode_order(modes, seed=5)
    expected_seed0 = ["C_structural_navigation", "A_baseline", "B_eif_governance", "D_full_stack"]
    expected_seed5 = ["A_baseline", "B_eif_governance", "D_full_stack", "C_structural_navigation"]
    results.append(check("seed=0 produces its exact expected order (regression pin, not just 'a' permutation)", seed0_order == expected_seed0, str(seed0_order)))
    results.append(check("seed=5 produces its exact expected order (regression pin, not just 'a' permutation)", seed5_order == expected_seed5, str(seed5_order)))
    results.append(check("different seeds (0 vs 5) actually produce different orders - this assertion CAN fail", seed0_order != seed5_order, f"{seed0_order} vs {seed5_order}"))

    distinct_orders = {tuple(randomize_mode_order(modes, seed=s)) for s in range(10)}
    results.append(check(
        "at least 5 distinct permutations across 10 deterministic seeds (0-9) - proves seeding actually varies the order, not a coincidence of 2 cherry-picked seeds",
        len(distinct_orders) >= 5, f"{len(distinct_orders)} distinct order(s) across 10 seeds",
    ))

    with tempfile.TemporaryDirectory(prefix="eif-benchmark-test-") as tmp:
        tmp_root = Path(tmp)

        # --- C/D fail loud without their explicit integration boundary. ---
        for blocked_mode in ("C_structural_navigation", "D_full_stack"):
            blocked_work = tmp_root / blocked_mode
            blocked_materialize = run_benchmark(
                "materialize", str(T02), str(blocked_work), "--mode", blocked_mode,
            )
            results.append(check(
                f"{blocked_mode} materialization is BLOCKED without an integration report and graph artifact",
                blocked_materialize.returncode == 3
                and "BLOCKED" in blocked_materialize.stdout
                and not blocked_work.exists(),
                blocked_materialize.stdout + blocked_materialize.stderr,
            ))
            blocked_out = tmp_root / f"{blocked_mode}.jsonl"
            blocked_run = run_benchmark(
                "run", str(T02), str(blocked_work), "--mode", blocked_mode,
                "--agent-runner", sys.executable, str(FAKE_AGENT), "--out", str(blocked_out),
            )
            results.append(check(
                f"{blocked_mode} run without materialization writes no result record",
                blocked_run.returncode == 3
                and not blocked_out.exists(),
                blocked_run.stdout + blocked_run.stderr,
            ))

        integration_report, graph_artifact, graph_metadata = write_integration_contract(tmp_root)
        fake_eifctl = make_eifctl_shim(tmp_root)

        presence_report_data = json.loads(integration_report.read_text(encoding="utf-8"))
        presence_report_data["results"][0]["capabilities"] = [
            item
            for item in presence_report_data["results"][0]["capabilities"]
            if item["id"] not in {"query-canary", "path-canary", "explain-canary"}
        ]
        presence_report = tmp_root / "provider-presence-only.json"
        presence_report.write_text(json.dumps(presence_report_data), encoding="utf-8")
        presence_work = tmp_root / "mode-c-provider-presence-only"
        presence_materialize = run_benchmark(
            "materialize", str(T02), str(presence_work),
            "--mode", "C_structural_navigation",
            "--eifctl-path", str(fake_eifctl),
            "--integration-report", str(presence_report),
            "--graph-artifact", str(graph_artifact),
            "--graph-metadata", str(graph_metadata),
        )
        results.append(check(
            "mode C rejects provider presence plus an artifact when behavioral canaries are absent",
            presence_materialize.returncode == 3 and not presence_work.exists(),
            presence_materialize.stdout + presence_materialize.stderr,
        ))
        substituted_metadata_data = json.loads(graph_metadata.read_text(encoding="utf-8"))
        substituted_metadata_data["graph_sha256"] = "sha256:" + "0" * 64
        substituted_metadata = tmp_root / "substituted-graph-metadata.json"
        substituted_metadata.write_text(json.dumps(substituted_metadata_data), encoding="utf-8")
        substituted_work = tmp_root / "mode-c-substituted-artifact"
        substituted_materialize = run_benchmark(
            "materialize", str(T02), str(substituted_work),
            "--mode", "C_structural_navigation",
            "--eifctl-path", str(fake_eifctl),
            "--integration-report", str(integration_report),
            "--graph-artifact", str(graph_artifact),
            "--graph-metadata", str(substituted_metadata),
        )
        results.append(check(
            "mode C rejects a graph artifact that is not integrity-bound to its D08 metadata",
            substituted_materialize.returncode == 3 and not substituted_work.exists(),
            substituted_materialize.stdout + substituted_materialize.stderr,
        ))

        def materialize_integration(mode: str, work: Path, report: Path = integration_report) -> subprocess.CompletedProcess:
            return run_benchmark(
                "materialize", str(T02), str(work), "--mode", mode,
                "--eifctl-path", str(fake_eifctl),
                "--integration-report", str(report),
                "--graph-artifact", str(graph_artifact),
                "--graph-metadata", str(graph_metadata),
            )

        def run_integration(mode: str, work: Path, behavior: str) -> tuple[subprocess.CompletedProcess, Path]:
            out = work.parent / f"{work.name}.jsonl"
            proc = run_benchmark(
                "run", str(T02), str(work), "--mode", mode,
                "--agent-runner", sys.executable, str(FAKE_AGENT),
                "--out", str(out),
                env={"EIF_FAKE_AGENT_BEHAVIOR": behavior},
            )
            return proc, out

        mode_c_work = tmp_root / "mode-c-happy"
        mode_c_materialize = materialize_integration("C_structural_navigation", mode_c_work)
        mode_c_run, mode_c_out = run_integration("C_structural_navigation", mode_c_work, "correct_fix")
        mode_c_record = json.loads(mode_c_out.read_text(encoding="utf-8").strip())
        mode_c_graph = mode_c_record["integration_evidence"]["graphify"]
        results.append(check(
            "mode C executes only with healthy/fresh Graphify and records verified consumption",
            mode_c_materialize.returncode == 0
            and mode_c_run.returncode == 0
            and mode_c_record["outcome"]["status"] == "success"
            and mode_c_graph["consumption_verified"] is True
            and mode_c_graph["capabilities_consumed"] == ["query"],
            mode_c_materialize.stdout + mode_c_materialize.stderr + mode_c_run.stdout + mode_c_run.stderr,
        ))
        results.append(check(
            "mode C result validates against the public result contract",
            run_benchmark("validate-result", str(mode_c_out)).returncode == 0,
        ))

        for behavior in ("presence_only", "fabricated_graph", "fabricated_source", "wrong_attempt"):
            work = tmp_root / f"mode-c-{behavior}"
            materialize_integration("C_structural_navigation", work)
            failed_run, failed_out = run_integration("C_structural_navigation", work, behavior)
            failed_record = json.loads(failed_out.read_text(encoding="utf-8").strip())
            results.append(check(
                f"mode C rejects {behavior} evidence and retains one harness_error record",
                failed_run.returncode == 21
                and failed_record["outcome"]["status"] == "harness_error"
                and failed_record["integration_evidence"]["graphify"]["consumption_verified"] is False,
                failed_run.stdout + failed_run.stderr,
            ))

        degraded_report, _, _ = write_integration_contract(tmp_root / "degraded-contract", rtk_state="degraded")
        mode_d_blocked_work = tmp_root / "mode-d-degraded"
        mode_d_blocked = materialize_integration(
            "D_full_stack",
            mode_d_blocked_work,
            degraded_report,
        )
        results.append(check(
            "mode D remains BLOCKED for a degraded RTK report and creates no workspace",
            mode_d_blocked.returncode == 3 and not mode_d_blocked_work.exists(),
            mode_d_blocked.stdout + mode_d_blocked.stderr,
        ))

        mode_d_work = tmp_root / "mode-d-happy"
        mode_d_materialize = materialize_integration("D_full_stack", mode_d_work)
        mode_d_run, mode_d_out = run_integration("D_full_stack", mode_d_work, "correct_fix")
        mode_d_record = json.loads(mode_d_out.read_text(encoding="utf-8").strip())
        mode_d_rtk = mode_d_record["integration_evidence"]["rtk"]
        results.append(check(
            "mode D records healthy RTK plus attempt-attributed content-free telemetry",
            mode_d_materialize.returncode == 0
            and mode_d_run.returncode == 0
            and mode_d_rtk["telemetry_attempt_attributed"] is True
            and mode_d_rtk["telemetry_events"] == 1
            and mode_d_rtk["savings_eligible_events"] == 1,
            mode_d_materialize.stdout + mode_d_materialize.stderr + mode_d_run.stdout + mode_d_run.stderr,
        ))
        results.append(check(
            "mode D result validates against the public result contract",
            run_benchmark("validate-result", str(mode_d_out)).returncode == 0,
        ))

        mode_d_missing_work = tmp_root / "mode-d-missing-telemetry"
        materialize_integration("D_full_stack", mode_d_missing_work)
        missing_run, missing_out = run_integration("D_full_stack", mode_d_missing_work, "missing_telemetry")
        missing_record = json.loads(missing_out.read_text(encoding="utf-8").strip())
        results.append(check(
            "mode D rejects missing attempt telemetry and retains one harness_error record",
            missing_run.returncode == 21
            and missing_record["outcome"]["status"] == "harness_error"
            and missing_record["integration_evidence"]["rtk"]["telemetry_attempt_attributed"] is False,
            missing_run.stdout + missing_run.stderr,
        ))

        forbidden_integration_keys = {"path", "prompt", "command", "argv", "output", "cwd"}

        def nested_keys(value) -> set[str]:
            if isinstance(value, dict):
                found = set(value)
                for item in value.values():
                    found.update(nested_keys(item))
                return found
            if isinstance(value, list):
                found = set()
                for item in value:
                    found.update(nested_keys(item))
                return found
            return set()

        results.append(check(
            "C/D result integration evidence contains no path, prompt, command, argv, output or cwd fields",
            not (nested_keys(mode_c_record["integration_evidence"]) | nested_keys(mode_d_record["integration_evidence"]))
            & forbidden_integration_keys,
        ))

        # --- invalid manifest rejected ---
        bad_fixture = tmp_root / "bad-fixture"
        bad_fixture.mkdir()
        (bad_fixture / "manifest.json").write_text(json.dumps({"task_id": "T99"}), encoding="utf-8")
        proc = run_benchmark("validate-manifest", str(bad_fixture))
        results.append(check(
            "validate-manifest rejects a manifest missing required fields",
            proc.returncode != 0,
            proc.stdout + proc.stderr,
        ))

        no_confirm_fixture = tmp_root / "no-confirm-fixture"
        no_confirm_fixture.mkdir()
        (no_confirm_fixture / "source").mkdir()
        (no_confirm_fixture / "task.md").write_text("x", encoding="utf-8")
        (no_confirm_fixture / "manifest.json").write_text(json.dumps({
            "manifest_schema_version": 1, "task_id": "T99", "title": "x",
            "supported_modes": ["A_baseline"], "task_prompt_path": "task.md",
            "source_dir": "source",
            "test_command": ["python", "x.py"],
            "expected_output_contract": {"tests_total": 1},
            "mutation_check": {"description": "x", "mutation_command": ["python", "x.py"]},
            "budget": {"max_wall_time_seconds": 10, "max_tool_calls": 1},
            "license": "Apache-2.0", "provenance": "test",
            "no_private_content_confirmed": False,
        }), encoding="utf-8")
        proc = run_benchmark("validate-manifest", str(no_confirm_fixture))
        results.append(check(
            "validate-manifest rejects no_private_content_confirmed: false",
            proc.returncode != 0,
        ))

        results.append(check(
            "validate-manifest accepts the real T02 fixture",
            run_benchmark("validate-manifest", str(T02)).returncode == 0,
        ))
        results.append(check(
            "validate-manifest accepts the real T07 fixture",
            run_benchmark("validate-manifest", str(T07)).returncode == 0,
        ))
        results.append(check(
            "validate-manifest accepts the real T10 fixture",
            run_benchmark("validate-manifest", str(FIXTURES_DIR / "T10-security-relevant-fix")).returncode == 0,
        ))
        corpus_fixtures = sorted(
            path for path in FIXTURES_DIR.iterdir()
            if path.is_dir() and (path / "manifest.json").is_file()
        )
        corpus_validation = [
            run_benchmark("validate-manifest", str(path))
            for path in corpus_fixtures
        ]
        results.append(check(
            "all 10 corpus fixtures validate with executable A/B/C/D mode declarations",
            len(corpus_fixtures) == 10
            and all(proc.returncode == 0 for proc in corpus_validation),
            "\n".join(proc.stdout + proc.stderr for proc in corpus_validation if proc.returncode != 0),
        ))

        # --- failed attempt retained ---
        # T02's unfixed source already passes 5/6 (only the exact-50-units
        # boundary is wrong), so "no_fix" is correctly scored "partial", not
        # "failure" - the property under test is retention, not this exact
        # label, so accept either non-success outcome.
        work = tmp_root / "work-failed"
        proc, out_path = materialize_and_run(T02, work, "no_fix")
        records = [json.loads(l) for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        results.append(check(
            "a failed attempt (agent made no fix) still produces exactly one written record, not discarded",
            len(records) == 1 and records[0]["outcome"]["status"] in ("failure", "partial"),
            str(records),
        ))
        results.append(check(
            "a non-success attempt exits 20 (EXIT_TASK_NOT_SUCCESS) - distinct from a written record, never inferred from it",
            proc.returncode == 20, str(proc.returncode),
        ))

        # --- harness crash retained ---
        work = tmp_root / "work-crash"
        proc, out_path = materialize_and_run(T02, work, "crash")
        records = [json.loads(l) for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        results.append(check(
            "an agent-runner crash still produces a written record with status harness_error",
            len(records) == 1 and records[0]["outcome"]["status"] == "harness_error",
            str(records),
        ))
        results.append(check(
            "a harness_error attempt exits 21 (EXIT_HARNESS_ERROR)",
            proc.returncode == 21, str(proc.returncode),
        ))

        # --- a genuine success exits 0 ---
        work = tmp_root / "work-success-exit-code"
        proc, out_path = materialize_and_run(work_dir=work, fixture=T02, behavior="correct_fix")
        records = [json.loads(l) for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        results.append(check(
            "a genuine success (T02, correct_fix) exits 0",
            proc.returncode == 0 and records[0]["outcome"]["status"] == "success",
            f"rc={proc.returncode} records={records}",
        ))

        # --- timeout retained, exits 22 ---
        # A synthetic fixture with a 1-second budget (real fixtures use
        # 300s, far too long for a test to actually wait) + the "hang"
        # fake-agent behavior (sleeps 3600s) - proves the real
        # subprocess.TimeoutExpired path, not a simulated shortcut.
        timeout_fixture = tmp_root / "timeout-fixture"
        (timeout_fixture / "source" / "src").mkdir(parents=True)
        (timeout_fixture / "source" / "tests").mkdir(parents=True)
        (timeout_fixture / "source" / "src" / "x.py").write_text("VALUE = 1\n", encoding="utf-8")
        (timeout_fixture / "source" / "tests" / "test_x.py").write_text(
            "print('EIF-BENCHMARK-RESULT: passed=1 total=1')\n", encoding="utf-8",
        )
        (timeout_fixture / "task.md").write_text("unused\n", encoding="utf-8")
        (timeout_fixture / "manifest.json").write_text(json.dumps({
            "manifest_schema_version": 1, "task_id": "T98", "title": "timeout test",
            "supported_modes": ["A_baseline"], "task_prompt_path": "task.md",
            "source_dir": "source",
            "test_command": ["python", "tests/test_x.py"],
            "expected_output_contract": {"tests_total": 1},
            "budget": {"max_wall_time_seconds": 1, "max_tool_calls": 1},
            "license": "Apache-2.0", "provenance": "test",
            "no_private_content_confirmed": True,
        }), encoding="utf-8")
        work = tmp_root / "work-timeout"
        run_benchmark("materialize", str(timeout_fixture), str(work), "--mode", "A_baseline")
        timeout_out = tmp_root / "timeout-results.jsonl"
        timeout_proc = run_benchmark(
            "run", str(timeout_fixture), str(work), "--mode", "A_baseline",
            "--agent-runner", sys.executable, str(FAKE_AGENT), "--out", str(timeout_out),
            env={"EIF_FAKE_AGENT_BEHAVIOR": "hang"},
        )
        timeout_records = [json.loads(l) for l in timeout_out.read_text(encoding="utf-8").splitlines() if l.strip()] if timeout_out.exists() else []
        results.append(check(
            "a real timeout (1s budget, hanging agent) still produces exactly one written record",
            len(timeout_records) == 1 and timeout_records[0]["outcome"]["status"] == "timeout",
            str(timeout_records),
        ))
        results.append(check(
            "a timeout attempt exits 22 (EXIT_TIMEOUT)",
            timeout_proc.returncode == 22, str(timeout_proc.returncode),
        ))

        # --- raw JSONL append-only ---
        work = tmp_root / "work-append"
        proc1, out_path = materialize_and_run(T02, work, "correct_fix", run_index=0)
        run_benchmark("materialize", str(T02), str(work), "--mode", "A_baseline")
        proc2 = run_benchmark(
            "run", str(T02), str(work), "--mode", "A_baseline",
            "--agent-runner", sys.executable, str(FAKE_AGENT), "--out", str(out_path), "--run-index", "1",
            env={"EIF_FAKE_AGENT_BEHAVIOR": "correct_fix"},
        )
        records = [json.loads(l) for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        results.append(check(
            "two run invocations against the same --out file append, not overwrite (2 records present)",
            len(records) == 2,
            str(len(records)),
        ))

        # --- retry lineage: attempt_kind/parent_attempt_id ---
        first_attempt_id = records[0]["attempt_id"]
        work = tmp_root / "work-retry"
        run_benchmark("materialize", str(T02), str(work), "--mode", "A_baseline")
        retry_out = tmp_root / "retry-results.jsonl"
        proc_retry = run_benchmark(
            "run", str(T02), str(work), "--mode", "A_baseline",
            "--agent-runner", sys.executable, str(FAKE_AGENT), "--out", str(retry_out),
            "--attempt-kind", "retry_after_harness_error", "--parent-attempt-id", first_attempt_id,
            env={"EIF_FAKE_AGENT_BEHAVIOR": "correct_fix"},
        )
        retry_records = [json.loads(l) for l in retry_out.read_text(encoding="utf-8").splitlines() if l.strip()]
        results.append(check(
            "a retry run's record carries attempt_kind and parent_attempt_id correctly",
            retry_records[0]["attempt_kind"] == "retry_after_harness_error" and retry_records[0]["parent_attempt_id"] == first_attempt_id,
            str(retry_records[0]),
        ))

        # --- validate-result: tests_passed <= tests_total ---
        bad_record = dict(records[0])
        bad_record["record_id"] = "bad-record"
        bad_record["attempt_id"] = "bad-attempt"
        bad_record["metrics"] = dict(bad_record["metrics"])
        bad_record["metrics"]["tests_passed"] = 999
        bad_record["metrics"]["tests_total"] = 6
        bad_result_file = tmp_root / "bad-result.jsonl"
        bad_result_file.write_text(json.dumps(bad_record) + "\n", encoding="utf-8")
        proc = run_benchmark("validate-result", str(bad_result_file))
        results.append(check(
            "validate-result rejects tests_passed > tests_total",
            proc.returncode != 0,
            proc.stdout,
        ))

        good_result_file = tmp_root / "good-result.jsonl"
        good_result_file.write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
        proc = run_benchmark("validate-result", str(good_result_file))
        results.append(check("validate-result accepts a real, well-formed record", proc.returncode == 0, proc.stdout))

        # --- validate-result: attempt_kind/parent_attempt_id consistency ---
        inconsistent = dict(records[0])
        inconsistent["record_id"] = "inconsistent"
        inconsistent["attempt_kind"] = "retry_after_timeout"
        inconsistent["parent_attempt_id"] = None
        inconsistent_file = tmp_root / "inconsistent-result.jsonl"
        inconsistent_file.write_text(json.dumps(inconsistent) + "\n", encoding="utf-8")
        proc = run_benchmark("validate-result", str(inconsistent_file))
        results.append(check(
            "validate-result rejects a retry_* attempt_kind with parent_attempt_id: null",
            proc.returncode != 0,
        ))

        # --- known_failed_fix detection actually fires ---
        work = tmp_root / "work-t07-wrongfix"
        proc, out_path = materialize_and_run(T07, work, "wrong_fix")
        t07_records = [json.loads(l) for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        results.append(check(
            "T07's known_failed_fix detector correctly flags the documented wrong approach as failure",
            t07_records[0]["outcome"]["status"] == "failure" and "known-failed" in t07_records[0]["outcome"].get("notes", ""),
            str(t07_records[0]["outcome"]),
        ))

        # --- aggregate: derived from records, not hand-summarized ---
        agg_dir = tmp_root / "agg-in"
        agg_dir.mkdir()
        synthetic_records = [
            _make_synthetic_record("T99", "A_baseline", 0, "success", 100, 50),
            _make_synthetic_record("T99", "A_baseline", 1, "failure", 120, 40),
            _make_synthetic_record("T99", "A_baseline", 2, "success", 110, 55),
        ]
        (agg_dir / "batch1.jsonl").write_text("\n".join(json.dumps(r) for r in synthetic_records) + "\n", encoding="utf-8")
        agg_out = tmp_root / "summary.json"
        proc = run_benchmark("aggregate", str(agg_dir), "--out", str(agg_out))
        summary = json.loads(agg_out.read_text(encoding="utf-8"))
        group = summary["groups"][0]
        expected_mean_input = (100 + 120 + 110) / 3
        results.append(check(
            "aggregate's mean_input_tokens is actually computed from the 3 synthetic records (not hardcoded)",
            abs(group["mean_input_tokens"] - expected_mean_input) < 0.01,
            f"{group['mean_input_tokens']} vs {expected_mean_input}",
        ))
        results.append(check(
            "aggregate's success_rate matches 2/3 successes in the synthetic batch",
            abs(group["success_rate"] - (2 / 3)) < 0.01,
            str(group["success_rate"]),
        ))
        results.append(check(
            "aggregate's outcome_breakdown counts match the synthetic batch exactly",
            group["outcome_breakdown"] == {"success": 2, "failure": 1},
            str(group["outcome_breakdown"]),
        ))

        # --- mixed model/tool versions cannot be compared silently ---
        mixed_dir = tmp_root / "agg-mixed"
        mixed_dir.mkdir()
        rec_a = _make_synthetic_record("T99", "B_eif_governance", 0, "success", 100, 50)
        rec_a["tool_versions"] = {"eifctl": "0.1.0", "graphify": None, "rtk": None}
        rec_b = _make_synthetic_record("T99", "B_eif_governance", 1, "success", 100, 50)
        rec_b["tool_versions"] = {"eifctl": "0.2.0", "graphify": None, "rtk": None}
        (mixed_dir / "batch.jsonl").write_text(json.dumps(rec_a) + "\n" + json.dumps(rec_b) + "\n", encoding="utf-8")
        mixed_out = tmp_root / "mixed-summary.json"
        proc = run_benchmark("aggregate", str(mixed_dir), "--out", str(mixed_out))
        results.append(check(
            "aggregate flags (in stdout) a group mixing two different eifctl versions rather than silently averaging them",
            "tool_version_conflicts" in proc.stdout or "WARNING" in proc.stdout,
            proc.stdout,
        ))
        mixed_summary = json.loads(mixed_out.read_text(encoding="utf-8"))
        results.append(check(
            "the mixed-tool-version conflict is also recorded in the machine-readable summary, not just printed",
            "tool_version_conflicts" in mixed_summary and len(mixed_summary["tool_version_conflicts"]) == 1,
            str(mixed_summary.get("tool_version_conflicts")),
        ))

        # --- measurement provenance (adoption-hardening round): fake-runner
        # cannot be blended with a real agent's measurements, estimated
        # cannot be silently compared with exact, missing provenance blocks
        # publication, and no quality-per-token claim survives from a
        # fake-runner-only group. ---
        fake_measurement = {"source": "fake-runner", "exact": True, "collector_version": "0.1.0"}
        real_measurement = {"source": "provider-usage", "exact": True, "collector_version": "test"}
        estimated_measurement = {"source": "provider-usage", "exact": False, "collector_version": "test"}

        source_mixed_dir = tmp_root / "agg-measurement-source-mixed"
        source_mixed_dir.mkdir()
        rec_fake = _make_synthetic_record("T97", "A_baseline", 0, "success", 100, 50, measurement=fake_measurement)
        rec_real = _make_synthetic_record("T97", "A_baseline", 1, "success", 100, 50, measurement=real_measurement)
        (source_mixed_dir / "batch.jsonl").write_text(json.dumps(rec_fake) + "\n" + json.dumps(rec_real) + "\n", encoding="utf-8")
        source_mixed_out = tmp_root / "measurement-source-mixed-summary.json"
        run_benchmark("aggregate", str(source_mixed_dir), "--out", str(source_mixed_out))
        source_mixed_summary = json.loads(source_mixed_out.read_text(encoding="utf-8"))
        results.append(check(
            "aggregate flags a group mixing fake-runner and real-agent (provider-usage) measurements, never silently blended",
            "measurement_conflicts" in source_mixed_summary and len(source_mixed_summary["measurement_conflicts"]) == 1,
            str(source_mixed_summary.get("measurement_conflicts")),
        ))
        source_mixed_group = source_mixed_summary["groups"][0]
        results.append(check(
            "the source-mixed group's token figures are suppressed (null), not silently averaged across incompatible sources",
            source_mixed_group["mean_input_tokens"] is None and source_mixed_group["token_figures_suppressed_reason"] is not None,
            str(source_mixed_group),
        ))

        exactness_mixed_dir = tmp_root / "agg-measurement-exactness-mixed"
        exactness_mixed_dir.mkdir()
        rec_exact = _make_synthetic_record("T96", "A_baseline", 0, "success", 100, 50, measurement=real_measurement)
        rec_estimated = _make_synthetic_record("T96", "A_baseline", 1, "success", 100, 50, measurement=estimated_measurement)
        (exactness_mixed_dir / "batch.jsonl").write_text(json.dumps(rec_exact) + "\n" + json.dumps(rec_estimated) + "\n", encoding="utf-8")
        exactness_mixed_out = tmp_root / "measurement-exactness-mixed-summary.json"
        run_benchmark("aggregate", str(exactness_mixed_dir), "--out", str(exactness_mixed_out))
        exactness_mixed_summary = json.loads(exactness_mixed_out.read_text(encoding="utf-8"))
        exactness_mixed_group = exactness_mixed_summary["groups"][0]
        results.append(check(
            "an estimated measurement is never silently compared/averaged with an exact one - token figures suppressed",
            exactness_mixed_group["mean_input_tokens"] is None and "estimated vs exact" in (exactness_mixed_group["token_figures_suppressed_reason"] or ""),
            str(exactness_mixed_group),
        ))

        missing_dir = tmp_root / "agg-measurement-missing"
        missing_dir.mkdir()
        rec_missing = _make_synthetic_record("T95", "A_baseline", 0, "success", 100, 50, measurement=real_measurement)
        del rec_missing["measurement"]
        (missing_dir / "batch.jsonl").write_text(json.dumps(rec_missing) + "\n", encoding="utf-8")
        missing_out = tmp_root / "measurement-missing-summary.json"
        run_benchmark("aggregate", str(missing_dir), "--out", str(missing_out))
        missing_summary = json.loads(missing_out.read_text(encoding="utf-8"))
        results.append(check(
            "a record entirely missing measurement provenance blocks publication of that group's token figures",
            "measurement_conflicts" in missing_summary and missing_summary["groups"][0]["mean_input_tokens"] is None,
            str(missing_summary),
        ))

        fake_only_dir = tmp_root / "agg-fake-only"
        fake_only_dir.mkdir()
        rec_fake_only = _make_synthetic_record("T94", "A_baseline", 0, "success", 100, 50, measurement=fake_measurement)
        (fake_only_dir / "batch.jsonl").write_text(json.dumps(rec_fake_only) + "\n", encoding="utf-8")
        fake_only_out = tmp_root / "fake-only-summary.json"
        run_benchmark("aggregate", str(fake_only_dir), "--out", str(fake_only_out))
        fake_only_summary = json.loads(fake_only_out.read_text(encoding="utf-8"))
        fake_only_group = fake_only_summary["groups"][0]
        results.append(check(
            "no quality-per-token claim (mean_input_tokens) is emitted for an all-fake-runner group, even with no conflict",
            fake_only_group["mean_input_tokens"] is None and "fake-runner" in (fake_only_group["token_figures_suppressed_reason"] or ""),
            str(fake_only_group),
        ))
        results.append(check(
            "an all-fake-runner group's success_rate/outcome_breakdown are still reported (retention, just not a token-cost claim)",
            fake_only_group["success_rate"] == 1.0 and fake_only_group["outcome_breakdown"] == {"success": 1},
            str(fake_only_group),
        ))

        # --- variance / confidence interval ---
        ci = _confidence_interval_95([100.0, 110.0, 90.0, 105.0, 95.0])
        results.append(check(
            "a 95% CI is computed for a real sample and brackets the sample mean",
            ci is not None and ci[0] < 100.0 < ci[1],
            str(ci),
        ))
        results.append(check(
            "no CI is fabricated from a single data point",
            _confidence_interval_95([100.0]) is None,
        ))

        # --- token-count figure never reported without an accompanying quality figure ---
        for g in summary["groups"] + mixed_summary["groups"]:
            has_token_figure = g.get("mean_input_tokens") is not None
            has_quality_figure = g.get("success_rate") is not None
            results.append(check(
                f"group {g['task_id']}/{g['mode']}: a token-count figure is never present without a success_rate alongside it",
                (not has_token_figure) or has_quality_figure,
                str(g),
            ))

    # --- privacy scan before transcript publication ---
    with tempfile.TemporaryDirectory(prefix="eif-benchmark-privacy-") as tmp:
        clean_log = Path(tmp) / "clean.log"
        clean_log.write_text("agent read src/pricing.py and applied the fix\n", encoding="utf-8")
        sys.path.insert(0, str(SCRIPTS_DIR))
        from eif_benchmark import scan_transcript_for_privacy
        results.append(check("a clean transcript scans with zero findings", scan_transcript_for_privacy(clean_log) == []))

        # Split-literal construction (same technique as test_adoption.py's
        # KEYCHAIN_PW_FIELD/_LEGACY_KEY_FIELD): the runtime value must be a
        # real, contiguous Windows-absolute-path-shaped string for this
        # fixture to mean anything, but that exact contiguous text must
        # never appear in THIS file's own source, or the repo-wide privacy
        # scan flags this line as a leak. Assembling it from fragments joined
        # at runtime keeps the fixture honest without self-triggering.
        dirty_log = Path(tmp) / "dirty.log"
        dirty_log.write_text("working in " + r"C:\Users" + "\\" + "Test User\\project" + "\n", encoding="utf-8")
        dirty_findings = scan_transcript_for_privacy(dirty_log)
        results.append(check(
            "a transcript containing an absolute path is flagged before it could be published",
            len(dirty_findings) > 0 and "absolute_path_leak" in dirty_findings[0],
            str(dirty_findings),
        ))

    if args.real:
        with tempfile.TemporaryDirectory(prefix="eif-benchmark-real-host-") as tmp:
            passed_real, detail = real_host_mode_d_contract(Path(tmp))
            results.append(check(
                "real host completes one zero-cost mode D contract with healthy Graphify/RTK evidence",
                passed_real,
                detail,
            ))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_benchmark: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


def _make_synthetic_record(task_id: str, mode: str, run_index: int, status: str, input_tokens: int, output_tokens: int, measurement: dict | None = None) -> dict:
    return {
        "schema_version": 1,
        "record_id": f"{task_id}__{mode}__run{run_index}__synthetic",
        "attempt_id": f"synthetic-{task_id}-{mode}-{run_index}",
        "parent_attempt_id": None,
        "attempt_kind": "initial",
        "task_id": task_id,
        "mode": mode,
        "run_index": run_index,
        "randomized_order_seed": None,
        "model": {"name": "fake", "version_or_snapshot": "1"},
        "started_at": "2026-07-16T00:00:00+00:00",
        "finished_at": "2026-07-16T00:00:01+00:00",
        "inputs": {"target_kind": "synthetic_fixture", "target_ref": task_id},
        "metrics": {
            "input_tokens": input_tokens, "output_tokens": output_tokens, "tool_calls": 1,
            "wall_time_seconds": 1.0, "completion_success": True,
            "tests_passed": 6 if status == "success" else 3, "tests_total": 6,
        },
        "measurement": measurement if measurement is not None else {"source": "provider-usage", "exact": True, "collector_version": "test"},
        "outcome": {"status": status},
        "harness_version": "0.1.0",
    }


if __name__ == "__main__":
    raise SystemExit(main())
