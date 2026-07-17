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

import yaml

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = FRAMEWORK_ROOT / "core" / "schemas"
BLOCKED_MODES = {"C_structural_navigation", "D_full_stack"}
EXECUTABLE_MODES = {"A_baseline", "B_eif_governance"}
HARNESS_VERSION = "0.1.0"

# `run`'s exit codes (adoption-hardening round): distinct from whether a
# result record was written, which happens on EVERY attempt regardless -
# record retention must never be inferred from the process exit code. A
# batch orchestrator may treat 20/21/22/23 as "continue to the next
# attempt", but CI/shell callers must not mistake any of them for 0.
EXIT_TASK_NOT_SUCCESS = 20  # outcome.status: failure or partial
EXIT_HARNESS_ERROR = 21     # outcome.status: harness_error
EXIT_TIMEOUT = 22           # outcome.status: timeout
EXIT_ABORTED = 23           # outcome.status: aborted


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


_DIGEST_SKIP_DIR_NAMES = {"__pycache__", ".git"}
_DIGEST_SKIP_SUFFIXES = (".pyc", ".pyo")


def compute_source_digest(source_dir: Path) -> str:
    """sha256 combined digest over every file's (relative path, sha256),
    sorted - same pattern as eif_init.py's combined_digest(), so a fixture
    drifting since its manifest was written is always detectable.

    Skips __pycache__/.pyc/.pyo: running a fixture's own test_command
    directly against source_dir (e.g. to smoke-test it, as this round did
    for all 3 pilot fixtures) generates local bytecode-cache artifacts
    that git never tracks. Without this exclusion, the digest recorded in
    manifest.json would depend on whether the fixture author happened to
    have run the tests before computing it - and would then mismatch on
    any environment (a fresh CI checkout, another contributor's machine)
    that never generated that cache, exactly as manifest.json's recorded
    digests did on this PR's first two CI runs."""
    entries = []
    for f in sorted(p for p in source_dir.rglob("*") if p.is_file()):
        if any(part in _DIGEST_SKIP_DIR_NAMES for part in f.relative_to(source_dir).parts[:-1]):
            continue
        if f.suffix in _DIGEST_SKIP_SUFFIXES:
            continue
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
    eifctl_provenance = None
    adapter_name = None
    if args.mode == "B_eif_governance":
        import time
        adapter_name = args.adapter
        eifctl = args.eifctl_path or shutil.which("eifctl")
        if not eifctl:
            print("materialize: FAIL - mode B requires the 'eifctl' console command on PATH", file=sys.stderr)
            return 1
        start = time.monotonic()
        proc = subprocess.run(
            [eifctl, "init", "--project-name", manifest["task_id"], "--adapter", adapter_name,
             "--instance-path", str(work_dir)],
            capture_output=True, text=True,
        )
        setup_cost_seconds = round(time.monotonic() - start, 3)
        if proc.returncode != 0:
            print(f"materialize: FAIL - eifctl init failed:\n{proc.stdout}\n{proc.stderr}", file=sys.stderr)
            return 1
        print(f"materialize: eifctl init succeeded in {setup_cost_seconds}s (mode B governance installed)")

        # Read the eifctl provenance eifctl ITSELF just recorded (this exact
        # venv's package/version/resource_manifest_digest/wheel_sha256) from
        # the instance's own lock file - never re-derive it via a second
        # `eifctl version` call or a fresh PATH lookup, either of which could
        # silently resolve to a DIFFERENT install than the one that actually
        # materialized this instance.
        lock_path = work_dir / ".eif" / "framework.lock.yaml"
        lock_data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
        if (lock_data.get("framework") or {}).get("source_type") != "installed-package":
            print(
                "materialize: FAIL - mode B's eifctl init did not record "
                "framework.source_type: installed-package in the instance lock "
                "- cannot attribute this attempt to a specific eifctl install.",
                file=sys.stderr,
            )
            return 1
        pkg = lock_data["package"]
        eifctl_provenance = {
            "distribution": pkg["distribution"],
            "version": pkg["version"],
            "python_version": pkg["python_version"],
            "resource_manifest_digest": pkg["resource_manifest_digest"],
        }
        if "wheel_sha256" in pkg:
            eifctl_provenance["wheel_sha256"] = pkg["wheel_sha256"]

    (work_dir / ".benchmark-materialize.json").write_text(
        json.dumps({
            "task_id": manifest["task_id"],
            "mode": args.mode,
            "source_digest": compute_source_digest(source_dir),
            "setup_cost_seconds": setup_cost_seconds,
            "adapter": adapter_name,
            "eifctl": eifctl_provenance,
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
    import platform

    fixture_dir = Path(args.fixture_dir).resolve()
    work_dir = Path(args.work_dir).resolve()
    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))

    if args.mode in BLOCKED_MODES:
        print(f"run: BLOCKED - mode {args.mode} is not operationally executable this round.")
        return 3

    # materialize must have already run against this exact work_dir - its
    # record of adapter/eifctl provenance is authoritative (this command
    # never re-derives it via a fresh `eifctl version` call or a PATH
    # lookup, either of which could silently resolve to a different
    # install than the one that actually materialized the instance).
    materialize_path = work_dir / ".benchmark-materialize.json"
    if not materialize_path.is_file():
        print(f"run: FAIL - {materialize_path} not found - run materialize first.", file=sys.stderr)
        return 1
    materialize_data = json.loads(materialize_path.read_text(encoding="utf-8"))
    if materialize_data.get("mode") != args.mode:
        print(
            f"run: FAIL - {materialize_path} was materialized for mode "
            f"{materialize_data.get('mode')!r}, but this run is for mode {args.mode!r}.",
            file=sys.stderr,
        )
        return 1

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
        "tool_versions": {"eifctl": materialize_data.get("eifctl")},
        "environment": {"os": platform.system()},
        "started_at": started_at,
        "finished_at": None,
        "inputs": {
            "target_kind": "synthetic_fixture",
            "target_ref": manifest["task_id"],
            "adapter": materialize_data.get("adapter"),
            "provenance": {"source_digest": compute_source_digest(fixture_dir / manifest["source_dir"])},
        },
        "metrics": {
            "input_tokens": 0, "output_tokens": 0, "tool_calls": 0,
            "wall_time_seconds": 0.0, "completion_success": False,
            "tests_passed": 0, "tests_total": 0,
            "setup_cost_seconds": materialize_data.get("setup_cost_seconds", 0.0),
        },
        # Default for every early-exit path (timeout/harness_error/aborted,
        # none of which ever reach the agent's own report) - overwritten
        # with the agent-runner's actual measurement block once one is
        # available. No tokens were meaningfully measured for these
        # outcomes anyway (metrics.input_tokens/output_tokens stay 0).
        "measurement": {"source": "estimated", "exact": False, "collector_version": None},
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
        return EXIT_TIMEOUT
    except KeyboardInterrupt:
        # Not exercised by an automated signal-based test: reliably
        # delivering SIGINT/CTRL_C to a subprocess.run() child mid-flight
        # is platform-fragile (Windows in particular does not support
        # send_signal(SIGINT) the same way POSIX does for an arbitrary
        # child), and a flaky test here would be worse than an honestly
        # untested edge case. The record-writing/exit-code shape matches
        # every other outcome branch, which IS covered.
        record["metrics"]["wall_time_seconds"] = round(time.monotonic() - wall_start, 3)
        record["outcome"] = {"status": "aborted", "notes": "operator-cancelled (KeyboardInterrupt)"}
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_record(args.out, record)
        print(f"run: ABORTED - {record['record_id']}")
        return EXIT_ABORTED

    wall_time = round(time.monotonic() - wall_start, 3)
    record["metrics"]["wall_time_seconds"] = wall_time
    record["finished_at"] = datetime.now(timezone.utc).isoformat()

    if agent_proc.returncode != 0:
        record["outcome"] = {"status": "harness_error", "notes": f"agent runner exited {agent_proc.returncode}: {agent_proc.stderr[:500]}"}
        _write_record(args.out, record)
        print(f"run: HARNESS_ERROR - {record['record_id']}")
        return EXIT_HARNESS_ERROR

    try:
        agent_report = json.loads(agent_proc.stdout)
    except json.JSONDecodeError:
        agent_report = {}
    record["metrics"]["input_tokens"] = agent_report.get("input_tokens", 0)
    record["metrics"]["output_tokens"] = agent_report.get("output_tokens", 0)
    record["metrics"]["tool_calls"] = agent_report.get("tool_calls", 0)
    # An agent-runner that doesn't report measurement provenance at all
    # gets an honest "estimated, not exact" placeholder here - never
    # silently assumed authoritative. This still lets the attempt be
    # retained (per this harness's retention-first design); it is
    # aggregate's job to refuse to publish a quality-per-token claim
    # built on unverified measurement, not this command's.
    record["measurement"] = agent_report.get("measurement") or {
        "source": "estimated", "exact": False, "collector_version": None,
    }

    passed, total, _ = _run_test_command(manifest["test_command"], cwd=work_dir)
    if passed is None:
        record["outcome"] = {"status": "harness_error", "notes": "test_command produced no parseable EIF-BENCHMARK-RESULT line"}
        _write_record(args.out, record)
        print(f"run: HARNESS_ERROR (bad test output) - {record['record_id']}")
        return EXIT_HARNESS_ERROR

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
    return 0 if record["outcome"]["status"] == "success" else EXIT_TASK_NOT_SUCCESS


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
    measurement_conflicts = []

    for (task_id, mode), group in sorted(by_task_mode.items()):
        tool_versions_seen = {json.dumps(r.get("tool_versions"), sort_keys=True) for r in group}
        if len(tool_versions_seen) > 1:
            tool_version_conflicts.append(f"{task_id}/{mode}: {len(tool_versions_seen)} distinct tool_versions in this group")

        # Measurement provenance (adoption-hardening round): a group must
        # never silently blend fake-runner measurements with a real
        # agent's, or an estimated figure with an exact one - either is
        # reported as a named conflict, same treatment as tool_version_
        # conflicts, never a silent average. A record missing measurement
        # entirely (should not happen given cmd_run's default, but this
        # command reads raw JSONL without re-validating against the
        # schema first) is treated the same as "missing provenance".
        measurements = [r.get("measurement") for r in group]
        missing_measurement = any(m is None for m in measurements)
        sources_seen = {m.get("source") for m in measurements if m is not None}
        exactness_seen = {m.get("exact") for m in measurements if m is not None}
        group_measurement_ok = not missing_measurement and len(sources_seen) <= 1 and len(exactness_seen) <= 1
        if missing_measurement:
            measurement_conflicts.append(f"{task_id}/{mode}: {sum(1 for m in measurements if m is None)} record(s) missing measurement provenance entirely - group excluded from publication")
        elif len(sources_seen) > 1:
            measurement_conflicts.append(f"{task_id}/{mode}: mixes measurement.source values {sorted(sources_seen)} - never silently blended")
        elif len(exactness_seen) > 1:
            measurement_conflicts.append(f"{task_id}/{mode}: mixes measurement.exact (estimated vs exact) - never silently compared")
        is_fake_runner_group = group_measurement_ok and sources_seen == {"fake-runner"}

        # Only the terminal attempt per run_index counts toward outcome
        # stats (a retry chain's earlier attempts are diagnostic, not
        # double-counted as separate runs) - selected as the attempt no
        # other record in the group names as its parent.
        parent_ids = {r["attempt_id"] for r in group if any(o.get("parent_attempt_id") == r["attempt_id"] for o in group)}
        terminal = [r for r in group if r["attempt_id"] not in parent_ids]

        input_tokens = [r["metrics"]["input_tokens"] for r in terminal]
        output_tokens = [r["metrics"]["output_tokens"] for r in terminal]
        successes = sum(1 for r in terminal if r["outcome"]["status"] == "success")

        # Token figures are never reported without a trustworthy,
        # single-provenance measurement basis: suppressed (null, with a
        # reason) rather than silently computed when measurement is
        # missing/conflicting, OR when every record in the group is
        # fake-runner-sourced (this round's only agent-runner, never real
        # quality-per-token evidence) - success_rate/outcome_breakdown are
        # still reported either way, since those don't depend on token
        # measurement provenance at all.
        suppress_reason = None
        if missing_measurement:
            suppress_reason = "measurement provenance missing on at least one record in this group"
        elif len(sources_seen) > 1:
            suppress_reason = f"mixed measurement.source values: {sorted(sources_seen)}"
        elif len(exactness_seen) > 1:
            suppress_reason = "mixed measurement.exact (estimated vs exact)"
        elif is_fake_runner_group:
            suppress_reason = "every record in this group is fake-runner-sourced - not real quality-per-token evidence"

        group_summary = {
            "task_id": task_id,
            "mode": mode,
            "total_attempts_including_retries": len(group),
            "terminal_runs": len(terminal),
            "successes": successes,
            "success_rate": round(successes / len(terminal), 3) if terminal else None,
            "mean_input_tokens": round(statistics.mean(input_tokens), 1) if input_tokens and not suppress_reason else None,
            "mean_output_tokens": round(statistics.mean(output_tokens), 1) if output_tokens and not suppress_reason else None,
            "input_tokens_95ci": _confidence_interval_95([float(x) for x in input_tokens]) if not suppress_reason else None,
            "token_figures_suppressed_reason": suppress_reason,
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

    if measurement_conflicts:
        summary["measurement_conflicts"] = measurement_conflicts
        print(f"aggregate: WARNING - {len(measurement_conflicts)} group(s) have a measurement-provenance conflict, token figures suppressed:")
        for c in measurement_conflicts:
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
    p.add_argument("--adapter", default="claude-code", help="Adapter to configure for mode B (eifctl init --adapter); ignored for mode A.")
    p.add_argument("--eifctl-path", default=None, help="Exact eifctl executable to use for mode B (e.g. a specific venv's Scripts/eifctl.exe) - overrides PATH lookup, so a test can pin exactly which install runs, not whichever eifctl happens to resolve first on PATH.")
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
