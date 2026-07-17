#!/usr/bin/env python3
"""Deterministic fake agent runner for testing eif_benchmark.py's `run`
command without a real agent (out of scope this round). Behavior is
selected via the EIF_FAKE_AGENT_BEHAVIOR env var:

    correct_fix   - applies the fixture's correct fix (T02 or T07), reports fixed metrics
    wrong_fix     - applies T07's specific documented known-failed fix
    no_fix        - leaves the source untouched (task failure)
    crash         - exits non-zero (harness_error)
    hang          - sleeps long enough to trigger the fixture's timeout

argv: [work_dir, task_prompt_path]
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

work_dir = Path(sys.argv[1])
behavior = os.environ.get("EIF_FAKE_AGENT_BEHAVIOR", "correct_fix")

if behavior == "crash":
    print("fake_agent_runner: simulated crash", file=sys.stderr)
    sys.exit(1)

if behavior == "hang":
    time.sleep(3600)
    sys.exit(0)

if behavior == "no_fix":
    print(json.dumps({"input_tokens": 100, "output_tokens": 50, "tool_calls": 1}))
    sys.exit(0)

pricing = work_dir / "src" / "pricing.py"
username = work_dir / "src" / "username.py"

if behavior == "correct_fix":
    if pricing.exists():
        text = pricing.read_text(encoding="utf-8")
        pricing.write_text(text.replace("elif quantity > 50:", "elif quantity >= 50:"), encoding="utf-8")
    if username.exists():
        text = username.read_text(encoding="utf-8")
        username.write_text(text.replace("return raw.lstrip().lower()", "return raw.strip().lower()"), encoding="utf-8")
elif behavior == "wrong_fix":
    if username.exists():
        text = username.read_text(encoding="utf-8")
        username.write_text(text.replace("return raw.lstrip().lower()", "return raw.replace(' ', '').lower()"), encoding="utf-8")

print(json.dumps({"input_tokens": 500, "output_tokens": 200, "tool_calls": 2}))
