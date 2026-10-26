#!/usr/bin/env python3
"""Exercise real synthetic measurements, repeatability and changed-baseline detection."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/eif_context_footprint.py"


def main() -> int:
    checks = []
    with tempfile.TemporaryDirectory(prefix="eif-footprint-test-") as tmp:
        baseline = Path(tmp) / "baseline.json"
        cmd = [sys.executable, str(SCRIPT), "--no-latency"]
        first = subprocess.run(cmd, capture_output=True, timeout=180)
        second = subprocess.run(cmd, capture_output=True, timeout=180)
        checks.append(first.returncode == second.returncode == 0 and first.stdout == second.stdout)
        data = json.loads(first.stdout)
        checks.append(len(data["adapters"]) == 4 and all(a["tier_b_first_task"]["doctor_stdout"]["exit_code"] == 0 for a in data["adapters"]))
        checks.append(str(Path(tmp)).encode() not in first.stdout and b"latency_seconds" not in first.stdout)
        baseline.write_bytes(first.stdout)
        match = subprocess.run([*cmd, "--check", str(baseline)], capture_output=True, timeout=180)
        checks.append(match.returncode == 0)
        data["adapters"][0]["scenarios"]["light"]["bytes"] += 1
        baseline.write_text(json.dumps(data), encoding="utf-8")
        mismatch = subprocess.run([*cmd, "--check", str(baseline)], capture_output=True, timeout=180)
        checks.append(mismatch.returncode == 1)
        spec = importlib.util.spec_from_file_location("footprint", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        runtime = Path(tmp) / "runtime"
        skill = runtime / "skills/example/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("[escape](../../../../outside.md)\n[missing](missing.md)", encoding="utf-8")
        (Path(tmp) / "outside.md").write_text("outside", encoding="utf-8")
        checks.append(module.one_hop_reads(runtime, "example") == [skill])
    for i, passed in enumerate(checks, 1):
        print(f"{'PASS' if passed else 'FAIL'} footprint {i}")
    print(f"EIF-RESULT: passed={sum(checks)} total={len(checks)}")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
