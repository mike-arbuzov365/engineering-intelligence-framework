#!/usr/bin/env python3
"""Deterministic fake agent runner for testing eif_benchmark.py's `run`
command without a real agent (out of scope this round). Behavior is
selected via the EIF_FAKE_AGENT_BEHAVIOR env var:

    correct_fix   - applies each fixture's correct fix (T02, T07, T10 - whichever source file is present), reports fixed metrics
    wrong_fix     - applies T07's specific documented known-failed fix
    no_fix        - leaves the source untouched (task failure)
    crash         - exits non-zero (harness_error)
    hang          - sleeps long enough to trigger the fixture's timeout

argv: [work_dir, task_prompt_path]

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
import os
import sys
import time
from pathlib import Path

FAKE_RUNNER_VERSION = "0.1.0"

work_dir = Path(sys.argv[1])
behavior = os.environ.get("EIF_FAKE_AGENT_BEHAVIOR", "correct_fix")


def _measurement() -> dict:
    return {"source": "fake-runner", "exact": True, "collector_version": FAKE_RUNNER_VERSION}


if behavior == "crash":
    print("fake_agent_runner: simulated crash", file=sys.stderr)
    sys.exit(1)

if behavior == "hang":
    time.sleep(3600)
    sys.exit(0)

if behavior == "no_fix":
    print(json.dumps({"input_tokens": 100, "output_tokens": 50, "tool_calls": 1, "measurement": _measurement()}))
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

print(json.dumps({"input_tokens": 500, "output_tokens": 200, "tool_calls": 2, "measurement": _measurement()}))
