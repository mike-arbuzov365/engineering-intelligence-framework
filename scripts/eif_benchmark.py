#!/usr/bin/env python3
"""Executable foundation for quality-per-token та bounded skill eval.

Task benchmark subcommands:

    eif_benchmark.py validate-manifest <fixture_dir>
    eif_benchmark.py materialize <fixture_dir> <work_dir> --mode <A|B|C|D>
    eif_benchmark.py run <fixture_dir> <work_dir> --mode {...} --agent-runner python runner.py --out results.jsonl [--attempt-kind ...] [--parent-attempt-id ID]
    eif_benchmark.py validate-result <result_record.json>
    eif_benchmark.py aggregate <results_dir> --out <summary.json>

Bounded skill-eval subcommands:

    eif_benchmark.py skill-eval-dry-run <manifest.yaml> --out <result.json>
    eif_benchmark.py validate-skill-eval <result.json>

Modes C and D are executable only through an explicit, privacy-safe
integration interface. C requires a schema-valid healthy/fresh Graphify report,
a real graph artifact digest and runner-returned consumption proof. D requires
the same plus healthy RTK and content-free telemetry attributed to the exact
attempt. Missing or fabricated evidence fails loud.

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
INTEGRATION_MODES = {"C_structural_navigation", "D_full_stack"}
EXECUTABLE_MODES = {"A_baseline", "B_eif_governance", *INTEGRATION_MODES}
HARNESS_VERSION = "0.3.0"

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


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _schema_errors(data: dict, schema_name: str) -> list[str]:
    validator = _validator(_load_schema(schema_name))
    return [
        error.message
        for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path))
    ]


def _passed_capabilities(result: dict) -> set[str]:
    return {
        item.get("id")
        for item in result.get("capabilities", [])
        if item.get("status") == "pass"
    }


def _prepare_integration_input(
    mode: str,
    report_path: str | None,
    graph_artifact_path: str | None,
    graph_metadata_path: str | None,
    source_dir: Path,
) -> tuple[dict | None, str | None]:
    if not report_path or not graph_artifact_path or not graph_metadata_path:
        return None, "mode C/D requires --integration-report, --graph-artifact and --graph-metadata"
    report_file = Path(report_path).resolve()
    graph_file = Path(graph_artifact_path).resolve()
    metadata_file = Path(graph_metadata_path).resolve()
    try:
        report = json.loads(report_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "integration report is missing, unreadable or invalid JSON"
    results = report.get("results") if isinstance(report, dict) else None
    if not isinstance(results, list):
        return None, "integration report must contain a results array"
    health_schema = _load_schema("integration-health-result.schema.json")
    health_validator = _validator(health_schema)
    for item in results:
        if not isinstance(item, dict) or list(health_validator.iter_errors(item)):
            return None, "integration report contains a result that fails the public health schema"
    integration_names = [item.get("integration") for item in results]
    if len(integration_names) != len(set(integration_names)):
        return None, "integration report contains duplicate integration results"
    by_name = {item.get("integration"): item for item in results}
    graphify = by_name.get("structural_graph")
    if not graphify:
        return None, "integration report does not contain structural_graph evidence"
    graph_caps = _passed_capabilities(graphify)
    required_graph_caps = {"query-canary", "path-canary", "explain-canary"}
    if (
        graphify.get("provider") != "graphify"
        or graphify.get("state") != "healthy"
        or (graphify.get("freshness") or {}).get("state") != "fresh"
        or not required_graph_caps.issubset(graph_caps)
    ):
        return None, "mode C/D requires healthy, fresh Graphify with query/path/explain canaries"
    try:
        graph = json.loads(graph_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "graph artifact is missing, unreadable or invalid JSON"
    links = graph.get("links", graph.get("edges"))
    if not isinstance(graph.get("nodes"), list) or not isinstance(links, list):
        return None, "graph artifact lacks nodes and links/edges arrays"
    source_files = [
        path.relative_to(source_dir).as_posix()
        for path in source_dir.rglob("*")
        if path.is_file()
        and not any(part in _DIGEST_SKIP_DIR_NAMES for part in path.relative_to(source_dir).parts[:-1])
        and path.suffix not in _DIGEST_SKIP_SUFFIXES
    ]
    graph_text = json.dumps(graph, ensure_ascii=False, sort_keys=True)
    if not source_files or not any(relative in graph_text for relative in source_files):
        return None, "graph artifact has no structural reference to the benchmark target source"
    version = (graphify.get("version") or {}).get("detected")
    if not isinstance(version, str) or not version:
        return None, "Graphify health evidence lacks a detected version"
    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "Graphify metadata is missing, unreadable or invalid JSON"
    metadata_errors = _schema_errors(metadata, "graphify-artifact-metadata.schema.json")
    if metadata_errors:
        return None, f"Graphify metadata failed schema validation: {metadata_errors[0]}"
    freshness = graphify["freshness"]
    artifact_digest = _sha256_file(graph_file)
    if (
        metadata["graph_sha256"] != artifact_digest
        or metadata["graphify_version"] != version
        or metadata["source_commit"] != freshness["baseline_commit"]
        or metadata["manifest_hash"] != freshness["manifest_hash"]
        or metadata["scope_hash"] != freshness["scope_hash"]
    ):
        return None, "Graphify health, metadata and graph artifact are not one integrity-bound evidence set"
    integration_input: dict = {
        "schema_version": 1,
        "mode": mode,
        "graphify": {
            "provider": "graphify",
            "health_state": "healthy",
            "freshness_state": "fresh",
            "version": version,
            "artifact_digest": artifact_digest,
            "target_source_digest": compute_source_digest(source_dir),
            "available_capabilities": ["query", "path", "explain"],
        },
    }
    if mode == "D_full_stack":
        rtk = by_name.get("shell_output_compression")
        if not rtk or rtk.get("provider") != "rtk" or rtk.get("state") != "healthy":
            return None, "mode D requires a healthy RTK behavioral report"
        required = {
            item.get("id")
            for item in rtk.get("capabilities", [])
            if item.get("required") is True
        }
        if not required or not required.issubset(_passed_capabilities(rtk)):
            return None, "mode D requires every required RTK capability to pass"
        rtk_version = (rtk.get("version") or {}).get("detected")
        if not isinstance(rtk_version, str) or not rtk_version:
            return None, "RTK health evidence lacks a detected version"
        registry = json.loads(
            (FRAMEWORK_ROOT / "integrations" / "rtk" / "command-registry.json").read_text(encoding="utf-8")
        )
        integration_input["rtk"] = {
            "provider": "rtk",
            "health_state": "healthy",
            "version": rtk_version,
            "registry_version": registry["registry_version"],
        }
    errors = _schema_errors(integration_input, "benchmark-integration-input.schema.json")
    return (None, f"integration input failed schema validation: {errors[0]}") if errors else (integration_input, None)


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

    if args.mode not in manifest["supported_modes"]:
        print(f"materialize: FAIL - {manifest['task_id']} does not declare support for mode {args.mode}")
        return 1

    source_dir = fixture_dir / manifest["source_dir"]
    integration_input = None
    graph_artifact_source = None
    if args.mode in INTEGRATION_MODES:
        integration_input, integration_error = _prepare_integration_input(
            args.mode,
            args.integration_report,
            args.graph_artifact,
            args.graph_metadata,
            source_dir,
        )
        if integration_error:
            print(
                f"materialize: BLOCKED - mode {args.mode}: {integration_error}. "
                "No workspace or result record was created."
            )
            return 3
        graph_artifact_source = Path(args.graph_artifact).resolve()

    if work_dir.exists():
        shutil.rmtree(work_dir)
    shutil.copytree(source_dir, work_dir)
    print(f"materialize: copied {source_dir} -> {work_dir}")

    setup_cost_seconds = 0.0
    eifctl_provenance = None
    adapter_name = None
    if args.mode != "A_baseline":
        import time
        adapter_name = args.adapter
        eifctl = args.eifctl_path or shutil.which("eifctl")
        if not eifctl:
            print("materialize: FAIL - modes B/C/D require the 'eifctl' console command on PATH", file=sys.stderr)
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
        print(f"materialize: eifctl init succeeded in {setup_cost_seconds}s ({args.mode} governance installed)")

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
                f"materialize: FAIL - mode {args.mode}'s eifctl init did not record "
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

    graph_artifact_rel = None
    if integration_input is not None and graph_artifact_source is not None:
        integration_dir = work_dir / ".benchmark-integrations"
        integration_dir.mkdir(parents=True, exist_ok=True)
        graph_target = integration_dir / "graph.json"
        shutil.copyfile(graph_artifact_source, graph_target)
        if _sha256_file(graph_target) != integration_input["graphify"]["artifact_digest"]:
            print("materialize: FAIL - copied graph artifact digest changed", file=sys.stderr)
            return 1
        graph_artifact_rel = ".benchmark-integrations/graph.json"
        (integration_dir / "input.json").write_text(
            json.dumps(integration_input, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    (work_dir / ".benchmark-materialize.json").write_text(
        json.dumps({
            "task_id": manifest["task_id"],
            "mode": args.mode,
            "source_digest": compute_source_digest(source_dir),
            "setup_cost_seconds": setup_cost_seconds,
            "adapter": adapter_name,
            "eifctl": eifctl_provenance,
            "integration_input": integration_input,
            "graph_artifact_rel": graph_artifact_rel,
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


def _initial_integration_evidence(integration_input: dict) -> dict:
    graphify = integration_input["graphify"]
    evidence: dict = {
        "graphify": {
            "provider": "graphify",
            "health_state": graphify["health_state"],
            "freshness_state": graphify["freshness_state"],
            "version": graphify["version"],
            "artifact_digest": graphify["artifact_digest"],
            "target_source_digest": graphify["target_source_digest"],
            "capabilities_consumed": [],
            "consumption_verified": False,
        }
    }
    if "rtk" in integration_input:
        rtk = integration_input["rtk"]
        evidence["rtk"] = {
            "provider": "rtk",
            "health_state": rtk["health_state"],
            "version": rtk["version"],
            "telemetry_attempt_attributed": False,
            "telemetry_events": 0,
            "savings_eligible_events": 0,
            "estimated_saved_tokens": 0,
        }
    return evidence


def _verify_graph_consumption(
    integration_input: dict,
    agent_report: dict,
    attempt_id: str,
) -> tuple[list[str], bool, str | None]:
    consumption = agent_report.get("integration_consumption")
    if not isinstance(consumption, dict) or consumption.get("attempt_id") != attempt_id:
        return [], False, "runner did not return integration consumption for this attempt"
    graph = consumption.get("graphify")
    if not isinstance(graph, dict):
        return [], False, "runner did not return Graphify consumption evidence"
    used = graph.get("capabilities_used")
    available = set(integration_input["graphify"]["available_capabilities"])
    valid_used = (
        isinstance(used, list)
        and bool(used)
        and len(used) == len(set(used))
        and all(isinstance(item, str) and item in available for item in used)
    )
    digest_ok = graph.get("artifact_digest") == integration_input["graphify"]["artifact_digest"]
    source_ok = graph.get("target_source_digest") == integration_input["graphify"]["target_source_digest"]
    if not valid_used or not digest_ok or not source_ok:
        return used if isinstance(used, list) else [], False, "runner consumption proof is missing, fabricated or incompatible"
    return sorted(used), True, None


def _rtk_attempt_evidence(work_dir: Path, attempt_id: str) -> tuple[dict, str | None]:
    evidence = {
        "telemetry_attempt_attributed": False,
        "telemetry_events": 0,
        "savings_eligible_events": 0,
        "estimated_saved_tokens": 0,
    }
    telemetry_path = work_dir / ".eif" / "local-state" / "rtk-telemetry.jsonl"
    if not telemetry_path.is_file():
        return evidence, "mode D runner produced no local RTK telemetry"
    validator = _validator(_load_schema("rtk-telemetry-event.schema.json"))
    matching = []
    try:
        lines = telemetry_path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if not line.strip():
                continue
            event = json.loads(line)
            if list(validator.iter_errors(event)):
                return evidence, "mode D telemetry failed the content-free RTK schema"
            if event.get("attempt_id") == attempt_id:
                matching.append(event)
    except (OSError, json.JSONDecodeError):
        return evidence, "mode D telemetry is unreadable or invalid JSONL"
    if not matching:
        return evidence, "mode D telemetry is not attributed to this attempt"
    evidence.update({
        "telemetry_attempt_attributed": True,
        "telemetry_events": len(matching),
        "savings_eligible_events": sum(1 for item in matching if item["savings_eligible"]),
        "estimated_saved_tokens": sum(item["estimated_saved_tokens"] for item in matching),
    })
    return evidence, None


def cmd_run(args: argparse.Namespace) -> int:
    import platform

    fixture_dir = Path(args.fixture_dir).resolve()
    work_dir = Path(args.work_dir).resolve()
    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))

    # materialize must have already run against this exact work_dir - its
    # record of adapter/eifctl provenance is authoritative (this command
    # never re-derives it via a fresh `eifctl version` call or a PATH
    # lookup, either of which could silently resolve to a different
    # install than the one that actually materialized the instance).
    materialize_path = work_dir / ".benchmark-materialize.json"
    if not materialize_path.is_file():
        if args.mode in INTEGRATION_MODES:
            print("run: BLOCKED - mode C/D requires a validated materialization. No result record was created.")
            return 3
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

    integration_input = materialize_data.get("integration_input")
    graph_artifact_path = None
    if args.mode in INTEGRATION_MODES:
        if not isinstance(integration_input, dict):
            print("run: BLOCKED - mode C/D materialization has no integration input.", file=sys.stderr)
            return 3
        input_errors = _schema_errors(integration_input, "benchmark-integration-input.schema.json")
        graph_artifact_rel = materialize_data.get("graph_artifact_rel")
        if input_errors or not isinstance(graph_artifact_rel, str):
            print("run: BLOCKED - mode C/D materialization integration evidence is invalid.", file=sys.stderr)
            return 3
        graph_artifact_path = (work_dir / graph_artifact_rel).resolve()
        try:
            graph_artifact_path.relative_to(work_dir)
        except ValueError:
            print("run: BLOCKED - materialized graph path escapes the workspace.", file=sys.stderr)
            return 3
        if (
            not graph_artifact_path.is_file()
            or _sha256_file(graph_artifact_path) != integration_input["graphify"]["artifact_digest"]
        ):
            print("run: BLOCKED - materialized graph artifact is absent or has drifted.", file=sys.stderr)
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
        "tool_versions": {
            "eifctl": materialize_data.get("eifctl"),
            "graphify": (integration_input or {}).get("graphify", {}).get("version"),
            "rtk": (integration_input or {}).get("rtk", {}).get("version"),
        },
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
    if integration_input is not None:
        record["integration_evidence"] = _initial_integration_evidence(integration_input)

    import time
    wall_start = time.monotonic()
    runner_argv = [*args.agent_runner, str(work_dir), str(fixture_dir / manifest["task_prompt_path"])]
    if integration_input is not None and graph_artifact_path is not None:
        attempt_input = dict(integration_input)
        attempt_input["attempt_id"] = attempt_id
        attempt_input_path = work_dir / ".benchmark-integrations" / "attempt-input.json"
        attempt_input_path.write_text(
            json.dumps(attempt_input, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        runner_argv.extend([str(attempt_input_path), str(graph_artifact_path), attempt_id])
    try:
        agent_proc = subprocess.run(
            runner_argv,
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

    if integration_input is not None:
        consumed, graph_verified, graph_error = _verify_graph_consumption(
            integration_input,
            agent_report,
            attempt_id,
        )
        graph_evidence = record["integration_evidence"]["graphify"]
        graph_evidence["capabilities_consumed"] = consumed
        graph_evidence["consumption_verified"] = graph_verified
        integration_errors = [graph_error] if graph_error else []
        if args.mode == "D_full_stack":
            rtk_evidence, rtk_error = _rtk_attempt_evidence(work_dir, attempt_id)
            record["integration_evidence"]["rtk"].update(rtk_evidence)
            if rtk_error:
                integration_errors.append(rtk_error)
        if integration_errors:
            record["outcome"] = {
                "status": "harness_error",
                "notes": "; ".join(item for item in integration_errors if item),
            }
            _write_record(args.out, record)
            print(f"run: HARNESS_ERROR (integration evidence) - {record['record_id']}")
            return EXIT_HARNESS_ERROR

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
        mode = record.get("mode")
        integration = record.get("integration_evidence") or {}
        terminal_status = record.get("outcome", {}).get("status")
        if mode in INTEGRATION_MODES and terminal_status in {"success", "partial", "failure"}:
            graph = integration.get("graphify") or {}
            if graph.get("consumption_verified") is not True or not graph.get("capabilities_consumed"):
                problems.append(f"record {i}: mode C/D terminal agent outcome requires verified Graphify consumption")
            target_digest = ((record.get("inputs") or {}).get("provenance") or {}).get("source_digest")
            if graph.get("target_source_digest") != target_digest:
                problems.append(f"record {i}: Graphify evidence is not bound to the benchmark target source digest")
        if mode == "D_full_stack" and terminal_status in {"success", "partial", "failure"}:
            rtk = integration.get("rtk") or {}
            if rtk.get("telemetry_attempt_attributed") is not True or rtk.get("telemetry_events", 0) < 1:
                problems.append(f"record {i}: mode D terminal agent outcome requires attempt-attributed RTK telemetry")

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
# Bounded skill eval: deterministic dry-run
# --------------------------------------------------------------------------

REQUIRED_SKILL_GRADERS = {
    "contract-schema",
    "matched-prompt-digest",
    "trigger-route",
    "forbidden-behavior",
    "metric-provenance",
}


def _contained_eval_path(relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"eval source path escapes framework root: {relative}")
    candidate = (FRAMEWORK_ROOT / path).resolve()
    if not candidate.is_relative_to(FRAMEWORK_ROOT.resolve()):
        raise ValueError(f"eval source path escapes framework root: {relative}")
    return candidate


def _skill_eval_manifest(path: Path) -> tuple[dict | None, list[str]]:
    problems: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        return None, [f"cannot parse skill eval manifest: {error}"]
    if not isinstance(data, dict):
        return None, ["skill eval manifest must be a mapping"]
    problems.extend(_schema_errors(data, "skill-eval-manifest.schema.json"))
    grader_ids = {
        item.get("id")
        for item in data.get("graders", [])
        if isinstance(item, dict)
    }
    missing = sorted(REQUIRED_SKILL_GRADERS - grader_ids)
    if missing:
        problems.append(f"skill eval manifest lacks required graders: {missing}")
    names = [
        item.get("name")
        for item in data.get("skills", [])
        if isinstance(item, dict)
    ]
    if len(names) != len(set(names)):
        problems.append("skill eval manifest contains duplicate skill names")
    return data, problems


def _skill_scenarios(contract_data: dict) -> dict[str, tuple[bool, str]]:
    scenarios: dict[str, tuple[bool, str]] = {}
    for category, expected in (("positive", True), ("negative", False)):
        for item in contract_data["triggers"][category]:
            scenario_id = item["id"]
            if scenario_id in scenarios:
                raise ValueError(f"duplicate skill scenario id: {scenario_id}")
            scenarios[scenario_id] = (expected, item["prompt"])
    return scenarios


def _integrity_entries(paths: set[Path]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    root = FRAMEWORK_ROOT.resolve()
    for path in sorted(path.resolve() for path in paths):
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"integrity source is missing or outside framework root: {path}")
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256_file(path),
            }
        )
    return entries


def _combined_integrity_digest(entries: list[dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for item in sorted(entries, key=lambda entry: entry["path"]):
        digest.update(f"{item['path']}:{item['sha256']}\n".encode("utf-8"))
    return f"sha256:{digest.hexdigest()}"


def _atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f".{path.name}.tmp")
    staging.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    staging.replace(path)


def cmd_skill_eval_dry_run(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.is_relative_to(FRAMEWORK_ROOT.resolve()):
        print("skill-eval-dry-run: FAIL - manifest must stay inside framework root")
        return 1
    manifest, problems = _skill_eval_manifest(manifest_path)
    if manifest is None:
        for problem in problems:
            print(f"skill-eval-dry-run: FAIL - {problem}")
        return 1
    owner_gate = manifest.get("owner_gate") or {}
    if (
        owner_gate.get("behavioral_status") != "deferred"
        or owner_gate.get("hard_zero_cost_confirmed") is not False
    ):
        problems.append(
            "dry-run requires behavioral_status=deferred and "
            "hard_zero_cost_confirmed=false; this command never calls a provider"
        )

    contract_sources: set[Path] = set()
    scenario_plan: list[dict] = []
    for skill in manifest.get("skills", []):
        try:
            contract_path = _contained_eval_path(skill["contract_path"])
        except ValueError as error:
            problems.append(str(error))
            continue
        if not contract_path.is_file():
            problems.append(f"skill contract is missing: {skill['contract_path']}")
            continue
        try:
            contract_data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as error:
            problems.append(f"cannot parse {skill['contract_path']}: {error}")
            continue
        if not isinstance(contract_data, dict):
            problems.append(f"skill contract must be a mapping: {skill['contract_path']}")
            continue
        contract_errors = _schema_errors(contract_data, "skill-contract.schema.json")
        problems.extend(
            f"{skill['contract_path']}: {error}" for error in contract_errors
        )
        if contract_errors:
            continue
        if contract_data["skill"]["name"] != skill["name"]:
            problems.append(
                f"skill name differs between manifest and contract: {skill['name']}"
            )
            continue
        try:
            available = _skill_scenarios(contract_data)
        except ValueError as error:
            problems.append(f"{skill['contract_path']}: {error}")
            continue
        for scenario_id in skill["scenario_ids"]:
            if scenario_id not in available:
                problems.append(
                    f"unknown scenario {scenario_id!r} for skill {skill['name']}"
                )
                continue
            expected_trigger, prompt = available[scenario_id]
            scenario_plan.append(
                {
                    "skill": skill["name"],
                    "scenario_id": scenario_id,
                    "expected_trigger": expected_trigger,
                    "prompt": prompt,
                    "contract_path": contract_path,
                    "contract_relative": skill["contract_path"],
                    "manifest_path": contract_path.parent.parent / "SKILL.md",
                }
            )
        contract_sources.add(contract_path)

    planned_attempts = len(scenario_plan) * len(manifest.get("modes", []))
    if planned_attempts > manifest.get("max_model_runs", 0):
        problems.append(
            f"planned attempts {planned_attempts} exceed max_model_runs "
            f"{manifest.get('max_model_runs')}"
        )
    if planned_attempts > 12:
        problems.append("planned attempts exceed packet maximum 12")
    if problems:
        print(f"skill-eval-dry-run: FAIL - {len(problems)} problem(s)")
        for problem in problems:
            print(f"  {problem}")
        return 1

    source_paths = {
        manifest_path,
        *contract_sources,
        Path(__file__).resolve(),
        SCHEMAS_DIR / "skill-contract.schema.json",
        SCHEMAS_DIR / "skill-eval-manifest.schema.json",
        SCHEMAS_DIR / "skill-eval-dry-run.schema.json",
    }
    integrity_entries = _integrity_entries(source_paths)
    grader_ids = [item["id"] for item in manifest["graders"]]
    attempts: list[dict] = []
    sequence = 0
    for scenario in scenario_plan:
        prompt_digest = f"sha256:{hashlib.sha256(scenario['prompt'].encode('utf-8')).hexdigest()}"
        contract_digest = _sha256_file(scenario["contract_path"])
        manifest_relative = scenario["manifest_path"].relative_to(
            FRAMEWORK_ROOT
        ).as_posix()
        for mode in manifest["modes"]:
            sequence += 1
            attempts.append(
                {
                    "sequence": sequence,
                    "skill": scenario["skill"],
                    "scenario_id": scenario["scenario_id"],
                    "mode": mode,
                    "expected_trigger": scenario["expected_trigger"],
                    "prompt_sha256": prompt_digest,
                    "contract_sha256": contract_digest,
                    "context": {
                        "skill_available": mode == "treatment",
                        "manifest_path": manifest_relative
                        if mode == "treatment"
                        else None,
                    },
                    "grader_ids": grader_ids,
                    "outcome": {
                        "status": "planned_deferred",
                        "reason": "hard_zero_cost_boundary_not_confirmed",
                    },
                    "metrics": {
                        "input_tokens": None,
                        "output_tokens": None,
                        "tool_calls": None,
                        "wall_time_seconds": None,
                        "measurement": "not_run",
                    },
                    "artifacts": [scenario["contract_relative"]],
                }
            )

    generated_at = args.generated_at or datetime.now(timezone.utc).isoformat()
    try:
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError:
        print("skill-eval-dry-run: FAIL - --generated-at must be ISO 8601")
        return 1
    result = {
        "schema_version": 1,
        "eval_id": manifest["eval_id"],
        "harness_version": HARNESS_VERSION,
        "generated_at": generated_at,
        "execution_status": "DEFERRED",
        "behavioral_model_runs": 0,
        "planned_attempts": len(attempts),
        "execution_order": "sequential",
        "owner_gate": owner_gate,
        "model": manifest["model"],
        "integrity": {
            "combined_sha256": _combined_integrity_digest(integrity_entries),
            "source_files": integrity_entries,
        },
        "graders": [
            {
                "id": item["id"],
                "kind": "deterministic",
                "status": "pass",
                "evidence": item["assertion"],
            }
            for item in manifest["graders"]
        ],
        "attempts": attempts,
        "claims": {
            "allowed": [
                "Dry-run harness, fixtures, deterministic graders і sequential plan на 12 attempts complete.",
                "Behavioral model evidence має status DEFERRED, model runs дорівнюють 0.",
            ],
            "forbidden": [
                "Skill quality покращилася.",
                "Trigger precision або recall виміряно.",
                "Token або time efficiency покращилася.",
            ],
        },
    }
    result_errors = _schema_errors(result, "skill-eval-dry-run.schema.json")
    if result_errors:
        print(f"skill-eval-dry-run: FAIL - generated result has {len(result_errors)} error(s)")
        for error in result_errors:
            print(f"  {error}")
        return 1
    out = Path(args.out).resolve()
    _atomic_json(out, result)
    print(
        "skill-eval-dry-run: DEFERRED - "
        f"planned_attempts={len(attempts)} model_runs=0 out={out}"
    )
    return 0


def cmd_validate_skill_eval(args: argparse.Namespace) -> int:
    result_path = Path(args.result_file).resolve()
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"validate-skill-eval: FAIL - cannot parse result: {error}")
        return 1
    problems = _schema_errors(result, "skill-eval-dry-run.schema.json")
    attempts = result.get("attempts", []) if isinstance(result, dict) else []
    if [item.get("sequence") for item in attempts if isinstance(item, dict)] != list(
        range(1, len(attempts) + 1)
    ):
        problems.append("attempt sequence is not contiguous and sequential")
    if result.get("planned_attempts") != len(attempts):
        problems.append("planned_attempts differs from attempts length")
    grouped: dict[tuple[str, str], list[dict]] = {}
    for attempt in attempts:
        if isinstance(attempt, dict):
            grouped.setdefault(
                (attempt.get("skill"), attempt.get("scenario_id")), []
            ).append(attempt)
    for key, pair in grouped.items():
        if {item.get("mode") for item in pair} != {"baseline", "treatment"}:
            problems.append(f"{key}: missing matched baseline/treatment pair")
        if len({item.get("prompt_sha256") for item in pair}) != 1:
            problems.append(f"{key}: baseline/treatment prompt digests differ")
        if len({item.get("expected_trigger") for item in pair}) != 1:
            problems.append(f"{key}: expected trigger differs across modes")

    entries = ((result.get("integrity") or {}).get("source_files") or [])
    rebuilt_entries: list[dict[str, str]] = []
    for item in entries:
        try:
            path = _contained_eval_path(item["path"])
        except (KeyError, TypeError, ValueError) as error:
            problems.append(f"invalid integrity source: {error}")
            continue
        if not path.is_file():
            problems.append(f"integrity source is missing: {item.get('path')}")
            continue
        actual = _sha256_file(path)
        if actual != item.get("sha256"):
            problems.append(f"integrity digest drift: {item.get('path')}")
        rebuilt_entries.append({"path": item["path"], "sha256": actual})
    actual_combined = _combined_integrity_digest(rebuilt_entries)
    if actual_combined != ((result.get("integrity") or {}).get("combined_sha256")):
        problems.append("combined integrity digest drift")

    if problems:
        print(f"validate-skill-eval: FAIL - {len(problems)} problem(s)")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(
        "validate-skill-eval: OK - "
        f"DEFERRED model_runs=0 planned_attempts={len(attempts)}"
    )
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
    p.add_argument("--mode", required=True, choices=sorted(EXECUTABLE_MODES))
    p.add_argument("--adapter", default="claude-code", help="Adapter to configure for modes B/C/D; ignored for mode A.")
    p.add_argument("--eifctl-path", default=None, help="Exact eifctl executable to use for modes B/C/D - overrides PATH lookup.")
    p.add_argument("--integration-report", default=None, help="Schema-valid eifctl doctor integration report required for modes C/D.")
    p.add_argument("--graph-artifact", default=None, help="Structural graph JSON whose digest and consumption are recorded for modes C/D.")
    p.add_argument("--graph-metadata", default=None, help="D08 Graphify metadata sidecar that integrity-binds the health report and graph artifact for modes C/D.")
    p.set_defaults(func=cmd_materialize)

    p = sub.add_parser("run")
    p.add_argument("fixture_dir")
    p.add_argument("work_dir")
    p.add_argument("--mode", required=True, choices=sorted(EXECUTABLE_MODES))
    p.add_argument("--agent-runner", required=True, nargs="+", help="Command (e.g. 'python runner.py'); work_dir and task_prompt_path are appended. C/D additionally receive integration_input_path, graph_artifact_path and attempt_id.")
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

    p = sub.add_parser("skill-eval-dry-run")
    p.add_argument("manifest")
    p.add_argument("--out", required=True)
    p.add_argument(
        "--generated-at",
        default=None,
        help="Optional fixed ISO-8601 timestamp for a reproducible fixture.",
    )
    p.set_defaults(func=cmd_skill_eval_dry_run)

    p = sub.add_parser("validate-skill-eval")
    p.add_argument("result_file")
    p.set_defaults(func=cmd_validate_skill_eval)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
