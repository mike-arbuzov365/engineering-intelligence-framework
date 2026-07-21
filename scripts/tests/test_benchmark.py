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

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
FRAMEWORK_ROOT = SCRIPTS_DIR.parent
BENCHMARK_SCRIPT = SCRIPTS_DIR / "eif_benchmark.py"
FAKE_AGENT = SCRIPTS_DIR / "tests" / "fixtures" / "benchmark" / "fake_agent_runner.py"
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


def main() -> int:
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

        # --- C/D are explicitly blocked at the real missing boundary. A
        # deterministic fake agent must never make either mode look real. ---
        for blocked_mode, expected_signal in (
            ("C_structural_navigation", "records and consumes Graphify query/path/explain evidence"),
            ("D_full_stack", "healthy RTK behavioral report"),
        ):
            blocked_work = tmp_root / blocked_mode
            blocked_materialize = run_benchmark(
                "materialize", str(T02), str(blocked_work), "--mode", blocked_mode,
            )
            results.append(check(
                f"{blocked_mode} materialization is explicitly BLOCKED without fake workspace evidence",
                blocked_materialize.returncode == 3
                and "BLOCKED" in blocked_materialize.stdout
                and expected_signal in blocked_materialize.stdout
                and not blocked_work.exists(),
                blocked_materialize.stdout + blocked_materialize.stderr,
            ))
            blocked_out = tmp_root / f"{blocked_mode}.jsonl"
            blocked_run = run_benchmark(
                "run", str(T02), str(blocked_work), "--mode", blocked_mode,
                "--agent-runner", sys.executable, str(FAKE_AGENT), "--out", str(blocked_out),
            )
            results.append(check(
                f"{blocked_mode} run is explicitly BLOCKED and writes no result record",
                blocked_run.returncode == 3
                and "BLOCKED" in blocked_run.stdout
                and not blocked_out.exists(),
                blocked_run.stdout + blocked_run.stderr,
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
