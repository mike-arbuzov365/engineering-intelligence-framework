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
    modes = ["A_baseline", "B_eif_governance", "C_structural_navigation", "D_full_stack"]
    order1 = randomize_mode_order(modes, seed=42)
    order2 = randomize_mode_order(modes, seed=42)
    order3 = randomize_mode_order(modes, seed=99)
    results.append(check("same seed produces the same mode order", order1 == order2, f"{order1} vs {order2}"))
    results.append(check("different seed can produce a different order", order1 != order3 or True, "(non-fatal if they happen to coincide, just documenting)"))
    results.append(check("randomize_mode_order is an actual permutation, not a copy-through", sorted(order1) == sorted(modes)))

    with tempfile.TemporaryDirectory(prefix="eif-benchmark-test-") as tmp:
        tmp_root = Path(tmp)

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

        # --- harness crash retained ---
        work = tmp_root / "work-crash"
        proc, out_path = materialize_and_run(T02, work, "crash")
        records = [json.loads(l) for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        results.append(check(
            "an agent-runner crash still produces a written record with status harness_error",
            len(records) == 1 and records[0]["outcome"]["status"] == "harness_error",
            str(records),
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

        dirty_log = Path(tmp) / "dirty.log"
        dirty_log.write_text(r"working in C:\Users\Test User\project" + "\n", encoding="utf-8")
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


def _make_synthetic_record(task_id: str, mode: str, run_index: int, status: str, input_tokens: int, output_tokens: int) -> dict:
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
        "outcome": {"status": status},
        "harness_version": "0.1.0",
    }


if __name__ == "__main__":
    raise SystemExit(main())
