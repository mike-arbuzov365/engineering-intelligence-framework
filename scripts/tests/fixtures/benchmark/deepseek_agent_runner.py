#!/usr/bin/env python3
"""Minimal real-agent runner for eif_benchmark.py's --agent-runner contract
(XREPO-01 Session 006, D-010's first bounded real-agent pilot).

Deliberately single-shot, not a multi-tool agentic loop: reads the task
prompt and every *.py file under src/ and tests/ in work_dir (plus
CLAUDE.md, if the mode-B materialize step generated one), sends ONE
chat-completion request to DeepSeek's API (model: deepseek-v4-flash,
non-thinking mode - these are small, fully-specified bug fixes, not tasks
that benefit from extended reasoning), and writes back only the file(s)
the model returned that already existed in work_dir (never creates a new
file from model output - a corrected/rewritten existing file is in scope,
an invented extra file is not).

argv: [work_dir, task_prompt_path]
stdout: JSON {input_tokens, output_tokens, tool_calls, measurement}

measurement.source is "provider-usage" (DeepSeek's own `usage` field on
the response, not a self-report or an estimate) - the harness's aggregate
step trusts this token count for a quality-per-token claim in a way it
explicitly does not trust "estimated" or a bare self-report.

API key: DEEPSEEK_API_KEY environment variable only - never hardcoded,
never logged, never written into the benchmark result record.

No retry: a request/parse failure is one failed attempt (harness_error or
failure), not silently retried - D-010's "no automatic retry" applies
inside this runner too, not just at the harness's attempt-count level.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

RUNNER_VERSION = "0.1.0"
MODEL = "deepseek-v4-flash"
API_URL = "https://api.deepseek.com/chat/completions"
REQUEST_TIMEOUT_SECONDS = 120

FILE_BLOCK_RE = re.compile(r"# FILE: (\S+)\n(.*?)(?=\n# FILE: |\Z)", re.DOTALL)


def _read_glob(root: Path, patterns: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for pattern in patterns:
        for f in sorted(root.glob(pattern)):
            if f.is_file():
                rel = str(f.relative_to(root)).replace("\\", "/")
                out[rel] = f.read_text(encoding="utf-8")
    return out


def _measurement(usage: dict) -> dict:
    # "exact" describes the reporting itself: these numbers are DeepSeek's
    # own accounting for this exact call, not a client-side estimate.
    return {"source": "provider-usage", "exact": True, "collector_version": RUNNER_VERSION}


def _fail(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def main() -> int:
    work_dir = Path(sys.argv[1])
    task_prompt_path = Path(sys.argv[2])

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        _fail("deepseek_agent_runner: DEEPSEEK_API_KEY is not set")

    task_prompt = task_prompt_path.read_text(encoding="utf-8")

    governance_text = ""
    claude_md = work_dir / "CLAUDE.md"
    if claude_md.is_file():
        governance_text = claude_md.read_text(encoding="utf-8")

    sources = _read_glob(work_dir, ["src/*.py"])
    tests = _read_glob(work_dir, ["tests/*.py"])
    if not sources:
        _fail(f"deepseek_agent_runner: no src/*.py found under {work_dir}")

    source_block = "\n\n".join(f"# FILE: {name}\n{content}" for name, content in sources.items())
    test_block = "\n\n".join(f"# FILE: {name}\n{content}" for name, content in tests.items())

    system_prompt = (
        "You are a coding agent fixing a small, fully-specified Python bug. "
        "Read the task instructions and the source/test files below, then "
        "output ONLY the corrected content of whichever source file(s) need "
        "to change. Do not modify test files. Format your entire response as "
        "one or more blocks of exactly this shape, with no other text:\n"
        "# FILE: <relative/path.py>\n<the file's full corrected content>\n"
    )
    if governance_text:
        system_prompt += (
            "\nThis project has its own governance instructions - follow "
            f"them where relevant:\n{governance_text}\n"
        )

    user_prompt = (
        f"## Task\n{task_prompt}\n\n"
        f"## Source files\n{source_block}\n\n"
        f"## Tests (read-only - do not modify, shown for context only)\n{test_block}\n"
    )

    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        _fail(f"deepseek_agent_runner: HTTP {e.code} from DeepSeek API: {detail}")
        return 1
    except urllib.error.URLError as e:
        _fail(f"deepseek_agent_runner: request failed: {e.reason}")
        return 1
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        _fail(f"deepseek_agent_runner: could not parse DeepSeek response: {e}")
        return 1

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        _fail(f"deepseek_agent_runner: unexpected response shape: {json.dumps(body)[:500]}")
        return 1

    usage = body.get("usage", {})

    applied = 0
    for rel_path, new_content in FILE_BLOCK_RE.findall(content):
        target = work_dir / rel_path
        # Only overwrite a file that already exists in the fixture - never
        # create a new file from model output.
        if target.is_file():
            target.write_text(new_content.rstrip("\n") + "\n", encoding="utf-8")
            applied += 1

    print(json.dumps({
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "tool_calls": applied,
        "measurement": _measurement(usage),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
