#!/usr/bin/env python3
"""Executable foundation for the quality-per-token benchmark
(docs/benchmarks/README.md). Five subcommands:

    eif_benchmark.py validate-manifest <fixture_dir>
    eif_benchmark.py materialize <fixture_dir> <work_dir> --mode {A_baseline,B_eif_governance}
    eif_benchmark.py run <fixture_dir> <work_dir> --mode {...} --agent-runner python runner.py --out results.jsonl [--attempt-kind ...] [--parent-attempt-id ID]
    eif_benchmark.py validate-result <result_record.json>
    eif_benchmark.py aggregate <results_dir> --out <summary.json>

Modes A (no EIF) and B (installed eifctl governance) are the only
executable modes this round. C (+ Graphify) and D (+ Graphify + RTK) are
schema-declared in core/schemas/benchmark-result.schema.json's mode enum,
but `run` refuses to execute them - there is no reproducible Graphify/RTK
install-version-config contract yet to run them against, and faking a C/D
result would be worse than not having one. See docs/benchmarks/README.md.

Every attempt - success, task failure, harness error, timeout, or abort -
produces exactly one result record; none is ever discarded or silently
folded into a counter. A restarted attempt is a NEW record whose
parent_attempt_id links back to the attempt it restarts (see
core/schemas/benchmark-result.schema.json) - the raw record stream is the
source of truth, never hand-summarized.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import statistics
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = FRAMEWORK_ROOT / "core" / "schemas"
BLOCKED_MODES = {"C_structural_navigation", "D_full_stack"}
EXECUTABLE_MODES = {"A_baseline", "B_eif_governance"}
HARNESS_VERSION = "0.1.0"


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))


def _validator(schema: dict):
    from jsonschema import Draft202012Validator
    return Draft202012Validator(schema)


def randomize_mode_order(modes: list[str], seed: int) -> list[str]:
    """Deterministic shuffle: the same (modes, seed) pair always produces
    the same order, so mode order itself is a controlled variable, not a
    silent confound - see randomized_order_seed in the result schema."""
    import random
    rng = random.Random(seed)
    shuffled = list(modes)
    rng.shuffle(shuffled)
    return shuffled


def scan_transcript_for_privacy(transcript_path: Path) -> list[str]:
    """Reuses eif_privacy_scan.py's own detection patterns (not a forked
    copy) against a single transcript file - required before any raw log
    is published (D-12). Returns a list of human-readable finding
    descriptions (rule + line number only, never the matched text, same
    redaction invariant as eif_privacy_scan.py itself); empty means clean."""
    sys.path.insert(0, str(FRAMEWORK_ROOT / "scripts"))
    from eif_privacy_scan import ABSOLUTE_PATH_PATTERNS, SECRET_PATTERNS

    findings = []
    text = transcript_path.read_text(encoding="utf-8", errors="replace")
    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern in ABSOLUTE_PATH_PATTERNS:
            if pattern.search(line):
                findings.append(f"absolute_path_leak:{line_no}")
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(f"secret_shaped:{name}:{line_no}")
    return findings


def compute_source_digest(source_dir: Path) -> str:
    """sha256 combined digest over every file's (relative path, sha256),
    sorted - same pattern as eif_init.py's combined_digest(), so a fixture
    drifting since its manifest was written is always detectable."""
    entries = []
    for f in sorted(p for p in source_dir.rglob("*") if p.is_file()):
        rel = f.relative_to(source_dir).as_posix()
        file_hash = hashlib.sha256(f.read_bytes()).hexdigest()
        entries.append((rel, file_hash))
    h = hashlib.sha256()
    for rel, file_hash in entries:
        h.update(f"{rel}:{file_hash}\n".encode("utf-8"))
    return f"sha256:{h.hexdigest()}"


# --------------------------------------------------------------------------
# validate-manifest
# --------------------------------------------------------------------------

def cmd_validate_manifest(args: argparse.Namespace) -> int:
    fixture_dir = Path(args.fixture_dir).resolve()
    manifest_path = fixture_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"validate-manifest: FAIL - {manifest_path} does not exist")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = _load_schema("benchmark-fixture-manifest.schema.json")
    validator = _validator(schema)
    errors = sorted(validator.iter_errors(manifest), key=lambda e: e.path)
    if errors:
        print(f"validate-manifest: FAIL - {len(errors)} schema error(s)")
        for e in errors:
            print(f"  {'/'.join(str(p) for p in e.path)}: {e.message}")
        return 1

    problems = []

    task_prompt_path = fixture_dir / manifest["task_prompt_path"]
    if not task_prompt_path.is_file():
        problems.append(f"task_prompt_path does not exist: {task_prompt_path}")

    source_dir = fixture_dir / manifest["source_dir"]
    if not source_dir.is_dir():
        problems.append(f"source_dir does not exist: {source_dir}")
    else:
        actual_digest = compute_source_digest(source_dir)
        recorded_digest = manifest.get("source_digest")
        if recorded_digest and recorded_digest != actual_digest:
            problems.append(
                f"source_digest mismatch: manifest says {recorded_digest}, "
                f"actual is {actual_digest} - fixture source changed since the manifest was written"
            )
        elif not recorded_digest:
            problems.append(f"source_digest missing from manifest - actual is {actual_digest}")

    mutation_script = manifest.get("mutation_check", {}).get("mutation_command", [None])
    if mutation_script and mutation_script[0] == "python":
        script_path = fixture_dir / mutation_script[1]
        if not script_path.is_file():
            problems.append(f"mutation_command script does not exist: {script_path}")

    known_failed_fix = manifest.get("known_failed_fix")
    if known_failed_fix:
        detect_cmd = known_failed_fix.get("detection_command", [None])
        if detect_cmd and detect_cmd[0] == "python":
            script_path = fixture_dir / detect_cmd[1]
            if not script_path.is_file():
                problems.append(f"known_failed_fix.detection_command script does not exist: {script_path}")

    if problems:
        print(f"validate-manifest: FAIL - {len(problems)} problem(s)")
        for p in problems:
            print(f"  {p}")
        return 1

    print(f"validate-manifest: OK - {manifest['task_id']} ({manifest['title']})")
    return 0


# --------------------------------------------------------------------------
# materialize
# --------------------------------------------------------------------------

def cmd_materialize(args: argparse.Namespace) -> int:
    fixture_dir = Path(args.fixture_dir).resolve()
    work_dir = Path(args.work_dir).resolve()
    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))

    if args.mode in BLOCKED_MODES:
        print(
            f"materialize: BLOCKED - mode {args.mode} is schema-declared but not "
            f"operationally executable this round (no reproducible Graphify/RTK "
            f"install-version-config contract yet). See docs/benchmarks/README.md."
        )
        return 3

    if args.mode not in manifest["supported_modes"]:
        print(f"materialize: FAIL - {manifest['task_id']} does not declare support for mode {args.mode}")
        return 1

    source_dir = fixture_dir / manifest["source_dir"]
    if work_dir.exists():
        shutil.rmtree(work_dir)
    shutil.copytree(source_dir, work_dir)
    print(f"materialize: copied {source_dir} -> {work_dir}")

    setup_cost_seconds = 0.0
    if args.mode == "B_eif_governance":
        import time
        start = time.monotonic()
        eifctl = shutil.which("eifctl")
        if not eifctl:
            print("materialize: FAIL - mode B requires the 'eifctl' console command on PATH", file=sys.stderr)
            return 1
        proc = subprocess.run(
            [eifctl, "init", "--project-name", manifest["task_id"], "--adapter", "claude-code",
             "--instance-path", str(work_dir)],
            capture_output=True, text=True,
        )
        setup_cost_seconds = round(time.monotonic() - start, 3)
        if proc.returncode != 0:
            print(f"materialize: FAIL - eifctl init failed:\n{proc.stdout}\n{proc.stderr}", file=sys.stderr)
            return 1
        print(f"materialize: eifctl init succeeded in {setup_cost_seconds}s (mode B governance installed)")

    (work_dir / ".benchmark-materialize.json").write_text(
        json.dumps({
            "task_id": manifest["task_id"],
            "mode": args.mode,
            "source_digest": compute_source_digest(source_dir),
            "setup_cost_seconds": setup_cost_seconds,
        }, indent=2),
        encoding="utf-8",
    )
    return 0


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------

def _run_test_command(test_command: list[str], cwd: Path) -> tuple[int, int, str]:
    """Runs the fixture's test_command, returns (passed, total, raw_output).
    (None, None, output) if the standardized result line is absent/malformed -
    never guessed at."""
    proc = subprocess.run(test_command, cwd=str(cwd), capture_output=True, text=True)
    output = proc.stdout + proc.stderr
    import re
    m = re.search(r"EIF-BENCHMARK-RESULT:\s*passed=(\d+)\s+total=(\d+)", output)
    if not m:
        return None, None, output
    return int(m.group(1)), int(m.group(2)), output


def cmd_run(args: argparse.Namespace) -> int:
    fixture_dir = Path(args.fixture_dir).resolve()
    work_dir = Path(args.work_dir).resolve()
    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))

    if args.mode in BLOCKED_MODES:
        print(f"run: BLOCKED - mode {args.mode} is not operationally executable this round.")
        return 3

    attempt_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    record: dict = {
        "schema_version": 1,
        "record_id": f"{manifest['task_id']}__{args.mode}__run{args.run_index}__{attempt_id}",
        "attempt_id": attempt_id,
        "parent_attempt_id": args.parent_attempt_id,
        "attempt_kind": args.attempt_kind,
        "task_id": manifest["task_id"],
        "mode": args.mode,
        "run_index": args.run_index,
        "randomized_order_seed": args.order_seed,
        "model": {"name": args.model_name, "version_or_snapshot": args.model_version},
        "started_at": started_at,
        "finished_at": None,
        "inputs": {
            "target_kind": "synthetic_fixture",
            "target_ref": manifest["task_id"],
            "provenance": {"source_digest": compute_source_digest(fixture_dir / manifest["source_dir"])},
        },
        "metrics": {
            "input_tokens": 0, "output_tokens": 0, "tool_calls": 0,
            "wall_time_seconds": 0.0, "completion_success": False,
            "tests_passed": 0, "tests_total": 0,
        },
        "outcome": {"status": "harness_error", "notes": "run did not complete"},
        "harness_version": HARNESS_VERSION,
    }

    import time
    wall_start = time.monotonic()
    try:
        agent_proc = subprocess.run(
            [*args.agent_runner, str(work_dir), str(fixture_dir / manifest["task_prompt_path"])],
            capture_output=True, text=True, timeout=manifest["budget"]["max_wall_time_seconds"],
        )
    except subprocess.TimeoutExpired:
        record["metrics"]["wall_time_seconds"] = round(time.monotonic() - wall_start, 3)
        record["outcome"] = {"status": "timeout", "notes": f"exceeded {manifest['budget']['max_wall_time_seconds']}s budget"}
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_record(args.out, record)
        print(f"run: TIMEOUT - {record['record_id']}")
        return 0

    wall_time = round(time.monotonic() - wall_start, 3)
    record["metrics"]["wall_time_seconds"] = wall_time
    record["finished_at"] = datetime.now(timezone.utc).isoformat()

    if agent_proc.returncode != 0:
        record["outcome"] = {"status": "harness_error", "notes": f"agent runner exited {agent_proc.returncode}: {agent_proc.stderr[:500]}"}
        _write_record(args.out, record)
        print(f"run: HARNESS_ERROR - {record['record_id']}")
        return 0

    try:
        agent_report = json.loads(agent_proc.stdout)
    except json.JSONDecodeError:
        agent_report = {}
    record["metrics"]["input_tokens"] = agent_report.get("input_tokens", 0)
    record["metrics"]["output_tokens"] = agent_report.get("output_tokens", 0)
    record["metrics"]["tool_calls"] = agent_report.get("tool_calls", 0)

    passed, total, _ = _run_test_command(manifest["test_command"], cwd=work_dir)
    if passed is None:
        record["outcome"] = {"status": "harness_error", "notes": "test_command produced no parseable EIF-BENCHMARK-RESULT line"}
        _write_record(args.out, record)
        print(f"run: HARNESS_ERROR (bad test output) - {record['record_id']}")
        return 0

    record["metrics"]["tests_passed"] = passed
    record["metrics"]["tests_total"] = total
    record["metrics"]["completion_success"] = True

    mutation = manifest.get("mutation_check")
    if mutation and passed == total:
        # Only meaningful once the solution looks correct - copy the work
        # dir aside first so the mutation (which overwrites files in place)
        # never destroys the actual solution being scored.
        import tempfile
        with tempfile.TemporaryDirectory(prefix="eif-benchmark-mutation-") as mutation_dir:
            mutation_work = Path(mutation_dir) / "work"
            shutil.copytree(work_dir, mutation_work)
            mutation_cmd = [mutation["mutation_command"][0], str(fixture_dir / mutation["mutation_command"][1]), str(mutation_work)]
            mutate_proc = subprocess.run(mutation_cmd, capture_output=True, text=True)
            if mutate_proc.returncode != 0:
                record["metrics"]["mutation_check_passed"] = None
            else:
                mutated_passed, mutated_total, _ = _run_test_command(manifest["test_command"], cwd=mutation_work)
                expected_after = mutation.get("expected_tests_passed_after_mutation")
                record["metrics"]["mutation_check_passed"] = (
                    mutated_passed is not None and expected_after is not None and mutated_passed == expected_after
                )

    known_failed_fix = manifest.get("known_failed_fix")
    repeated_known_fail = False
    if known_failed_fix:
        # The detector script itself lives under the fixture dir (resolved
        # here, same pattern as mutation_command); it runs with cwd=work_dir
        # so its own relative file reads (e.g. "src/username.py") target the
        # actual produced solution, not the fixture's own source copy.
        raw_cmd = known_failed_fix["detection_command"]
        resolved_cmd = [raw_cmd[0], str(fixture_dir / raw_cmd[1]), *raw_cmd[2:]]
        detect_proc = subprocess.run(resolved_cmd, cwd=str(work_dir), capture_output=True, text=True)
        repeated_known_fail = detect_proc.returncode != 0

    if repeated_known_fail:
        record["outcome"] = {"status": "failure", "notes": "solution repeats the documented known-failed approach"}
    elif passed == total:
        record["outcome"] = {"status": "success"}
    elif passed > 0:
        record["outcome"] = {"status": "partial"}
    else:
        record["outcome"] = {"status": "failure"}

    _write_record(args.out, record)
    print(f"run: {record['outcome']['status'].upper()} - {record['record_id']} ({passed}/{total} tests)")
    return 0


def _write_record(out_path: str, record: dict) -> None:
    """Append-only JSONL - never truncates, never overwrites a prior record."""
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# --------------------------------------------------------------------------
# validate-result
# --------------------------------------------------------------------------

def cmd_validate_result(args: argparse.Namespace) -> int:
    schema = _load_schema("benchmark-result.schema.json")
    validator = _validator(schema)

    records = [json.loads(line) for line in Path(args.result_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    problems = []
    for i, record in enumerate(records):
        errors = list(validator.iter_errors(record))
        for e in errors:
            problems.append(f"record {i} ({record.get('record_id', '?')}): {e.message}")
        if record.get("attempt_kind") != "initial" and not record.get("parent_attempt_id"):
            problems.append(f"record {i}: attempt_kind={record.get('attempt_kind')!r} requires a non-null parent_attempt_id")
        if record.get("attempt_kind") == "initial" and record.get("parent_attempt_id") is not None:
            problems.append(f"record {i}: attempt_kind='initial' must have parent_attempt_id: null")
        m = record.get("metrics", {})
        if m.get("tests_passed", 0) > m.get("tests_total", 0):
            problems.append(f"record {i}: tests_passed ({m.get('tests_passed')}) > tests_total ({m.get('tests_total')})")

    if problems:
        print(f"validate-result: FAIL - {len(problems)} problem(s)")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"validate-result: OK - {len(records)} record(s) valid")
    return 0


# --------------------------------------------------------------------------
# aggregate
# --------------------------------------------------------------------------

def _confidence_interval_95(values: list[float]) -> tuple[float, float] | None:
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    margin = 1.96 * stdev / math.sqrt(len(values))
    return (round(mean - margin, 3), round(mean + margin, 3))


def cmd_aggregate(args: argparse.Namespace) -> int:
    results_dir = Path(args.results_dir)
    records = []
    for f in sorted(results_dir.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))

    by_task_mode: dict[tuple[str, str], list[dict]] = {}
    for r in records:
        key = (r["task_id"], r["mode"])
        by_task_mode.setdefault(key, []).append(r)

    summary = {"harness_version": HARNESS_VERSION, "total_records": len(records), "groups": []}
    tool_version_conflicts = []

    for (task_id, mode), group in sorted(by_task_mode.items()):
        tool_versions_seen = {json.dumps(r.get("tool_versions"), sort_keys=True) for r in group}
        if len(tool_versions_seen) > 1:
            tool_version_conflicts.append(f"{task_id}/{mode}: {len(tool_versions_seen)} distinct tool_versions in this group")

        # Only the terminal attempt per run_index counts toward outcome
        # stats (a retry chain's earlier attempts are diagnostic, not
        # double-counted as separate runs) - selected as the attempt no
        # other record in the group names as its parent.
        parent_ids = {r["attempt_id"] for r in group if any(o.get("parent_attempt_id") == r["attempt_id"] for o in group)}
        terminal = [r for r in group if r["attempt_id"] not in parent_ids]

        input_tokens = [r["metrics"]["input_tokens"] for r in terminal]
        output_tokens = [r["metrics"]["output_tokens"] for r in terminal]
        successes = sum(1 for r in terminal if r["outcome"]["status"] == "success")

        group_summary = {
            "task_id": task_id,
            "mode": mode,
            "total_attempts_including_retries": len(group),
            "terminal_runs": len(terminal),
            "successes": successes,
            "success_rate": round(successes / len(terminal), 3) if terminal else None,
            "mean_input_tokens": round(statistics.mean(input_tokens), 1) if input_tokens else None,
            "mean_output_tokens": round(statistics.mean(output_tokens), 1) if output_tokens else None,
            "input_tokens_95ci": _confidence_interval_95([float(x) for x in input_tokens]),
            "outcome_breakdown": {
                status: sum(1 for r in terminal if r["outcome"]["status"] == status)
                for status in ("success", "partial", "failure", "harness_error", "timeout", "aborted")
                if any(r["outcome"]["status"] == status for r in terminal)
            },
        }
        summary["groups"].append(group_summary)

    if tool_version_conflicts:
        summary["tool_version_conflicts"] = tool_version_conflicts
        print(f"aggregate: WARNING - {len(tool_version_conflicts)} group(s) mix tool versions, excluded from a single comparable figure:")
        for c in tool_version_conflicts:
            print(f"  {c}")

    Path(args.out).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"aggregate: wrote {args.out} ({len(records)} records, {len(summary['groups'])} task/mode group(s))")
    return 0


# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate-manifest")
    p.add_argument("fixture_dir")
    p.set_defaults(func=cmd_validate_manifest)

    p = sub.add_parser("materialize")
    p.add_argument("fixture_dir")
    p.add_argument("work_dir")
    p.add_argument("--mode", required=True, choices=sorted(EXECUTABLE_MODES | BLOCKED_MODES))
    p.set_defaults(func=cmd_materialize)

    p = sub.add_parser("run")
    p.add_argument("fixture_dir")
    p.add_argument("work_dir")
    p.add_argument("--mode", required=True, choices=sorted(EXECUTABLE_MODES | BLOCKED_MODES))
    p.add_argument("--agent-runner", required=True, nargs="+", help="Command (e.g. 'python runner.py'); work_dir and task_prompt_path are appended; stdout must be JSON {input_tokens, output_tokens, tool_calls}")
    p.add_argument("--out", required=True, help="JSONL file to append the result record to")
    p.add_argument("--run-index", type=int, default=0)
    p.add_argument("--order-seed", type=int, default=None)
    p.add_argument("--attempt-kind", default="initial", choices=["initial", "retry_after_harness_error", "retry_after_timeout", "retry_after_task_failure"])
    p.add_argument("--parent-attempt-id", default=None)
    p.add_argument("--model-name", default="unknown")
    p.add_argument("--model-version", default="unknown")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("validate-result")
    p.add_argument("result_file")
    p.set_defaults(func=cmd_validate_result)

    p = sub.add_parser("aggregate")
    p.add_argument("results_dir")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_aggregate)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
