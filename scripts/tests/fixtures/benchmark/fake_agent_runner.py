#!/usr/bin/env python3
"""Deterministic fake agent runner for testing eif_benchmark.py's `run`
command without a real agent (out of scope this round). Behavior is
selected via the EIF_FAKE_AGENT_BEHAVIOR env var:

    correct_fix   - applies each fixture's correct fix (T02, T07, T10 - whichever source file is present), reports fixed metrics
    wrong_fix     - applies T07's specific documented known-failed fix
    no_fix        - leaves the source untouched (task failure)
    crash         - exits non-zero (harness_error)
    hang          - sleeps long enough to trigger the fixture's timeout

argv for A/B: [work_dir, task_prompt_path]
argv for C/D:
[work_dir, task_prompt_path, integration_input_path, graph_artifact_path,
attempt_id]

Reports measurement provenance (adoption-hardening round) alongside the
token/tool counts: source: fake-runner, exact: true (the reported numbers
ARE exactly what this script decided to report - "exact" describes the
reporting, not whether it reflects real agent cost, which it never does).
eif_benchmark.py's aggregate refuses to blend fake-runner measurements
with real-agent ones, and refuses to derive a quality-per-token claim
from fake-runner records at all.
"""
from __future__ import annotations

import json
import hashlib
import os
import sys
import time
from pathlib import Path

FAKE_RUNNER_VERSION = "0.1.0"

work_dir = Path(sys.argv[1])
behavior = os.environ.get("EIF_FAKE_AGENT_BEHAVIOR", "correct_fix")
integration_input_path = Path(sys.argv[3]) if len(sys.argv) >= 6 else None
graph_artifact_path = Path(sys.argv[4]) if len(sys.argv) >= 6 else None
attempt_id = sys.argv[5] if len(sys.argv) >= 6 else None


def _measurement() -> dict:
    return {"source": "fake-runner", "exact": True, "collector_version": FAKE_RUNNER_VERSION}


def _integration_report() -> dict:
    if integration_input_path is None or graph_artifact_path is None or attempt_id is None:
        return {}
    integration_input = json.loads(integration_input_path.read_text(encoding="utf-8"))
    graph = json.loads(graph_artifact_path.read_text(encoding="utf-8"))
    if not isinstance(graph.get("nodes"), list):
        raise ValueError("graph artifact has no nodes")
    graph_labels = {
        str(node.get("label", node.get("id", "")))
        for node in graph["nodes"]
        if isinstance(node, dict)
    }
    if not graph_labels:
        raise ValueError("graph query returned no labels")

    if integration_input["mode"] == "D_full_stack" and behavior != "missing_telemetry":
        telemetry_path = work_dir / ".eif" / "local-state" / "rtk-telemetry.jsonl"
        telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "schema_version": 1,
            "event_id": hashlib.sha256(attempt_id.encode("utf-8")).hexdigest()[:32],
            "recorded_at": "2026-07-23T00:00:00Z",
            "integration": "rtk",
            "registry_version": integration_input["rtk"]["registry_version"],
            "attempt_id": attempt_id,
            "command_class": "grep-alternation",
            "route": "native-guarded",
            "outcome": "success",
            "raw_bytes": 100,
            "emitted_bytes": 40,
            "estimated_raw_tokens": 25,
            "estimated_emitted_tokens": 10,
            "estimated_saved_tokens": 15,
            "savings_eligible": True,
        }
        with telemetry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")

    if behavior == "presence_only":
        return {}
    reported_attempt = "wrong-attempt" if behavior == "wrong_attempt" else attempt_id
    reported_digest = (
        "sha256:" + "0" * 64
        if behavior == "fabricated_graph"
        else integration_input["graphify"]["artifact_digest"]
    )
    reported_source_digest = (
        "sha256:" + "0" * 64
        if behavior == "fabricated_source"
        else integration_input["graphify"]["target_source_digest"]
    )
    return {
        "integration_consumption": {
            "attempt_id": reported_attempt,
            "graphify": {
                "artifact_digest": reported_digest,
                "target_source_digest": reported_source_digest,
                "capabilities_used": ["query"],
            },
        }
    }


def _emit(input_tokens: int, output_tokens: int, tool_calls: int) -> None:
    report = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "tool_calls": tool_calls,
        "measurement": _measurement(),
        **_integration_report(),
    }
    print(json.dumps(report))


if behavior == "crash":
    print("fake_agent_runner: simulated crash", file=sys.stderr)
    sys.exit(1)

if behavior == "hang":
    time.sleep(3600)
    sys.exit(0)

if behavior == "no_fix":
    _emit(100, 50, 1)
    sys.exit(0)

pricing = work_dir / "src" / "pricing.py"
username = work_dir / "src" / "username.py"
file_reader = work_dir / "src" / "file_reader.py"

if behavior == "correct_fix":
    if pricing.exists():
        text = pricing.read_text(encoding="utf-8")
        pricing.write_text(text.replace("elif quantity > 50:", "elif quantity >= 50:"), encoding="utf-8")
    if username.exists():
        text = username.read_text(encoding="utf-8")
        username.write_text(text.replace("return raw.lstrip().lower()", "return raw.strip().lower()"), encoding="utf-8")
    if file_reader.exists():
        file_reader.write_text(
            '"""Serves files to users from a restricted public directory."""\n'
            "from __future__ import annotations\n"
            "\n"
            "import os\n"
            "\n"
            "\n"
            "def read_user_file(base_dir: str, filename: str) -> str:\n"
            "    \"\"\"Read `filename` from within `base_dir` and return its contents.\n"
            "    `filename` is caller-supplied and must never be able to escape\n"
            "    `base_dir` (e.g. via '..' path segments).\"\"\"\n"
            "    base = os.path.realpath(base_dir)\n"
            "    path = os.path.realpath(os.path.join(base_dir, filename))\n"
            "    if path != base and not path.startswith(base + os.sep):\n"
            "        raise ValueError(f\"path escapes base_dir: {filename!r}\")\n"
            "    with open(path, \"r\", encoding=\"utf-8\") as f:\n"
            "        return f.read()\n",
            encoding="utf-8",
        )
elif behavior == "wrong_fix":
    if username.exists():
        text = username.read_text(encoding="utf-8")
        username.write_text(text.replace("return raw.lstrip().lower()", "return raw.replace(' ', '').lower()"), encoding="utf-8")

_emit(500, 200, 2)
