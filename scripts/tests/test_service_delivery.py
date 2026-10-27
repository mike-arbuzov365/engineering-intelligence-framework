#!/usr/bin/env python3
"""Exercise structured delivery checks on a real materialized design profile."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/tests")]
from test_service_golden import cases
from test_delivery_guard import approval
from engineering_intelligence_framework.service import Instance
from engineering_intelligence_framework.service.operations import delivery_check


def main() -> int:
    results = []
    with tempfile.TemporaryDirectory(prefix="eif-service-delivery-") as tmp:
        base = Path(tmp).resolve()
        # Reuse the already characterized synthetic workspace/profile/project
        # setup; no private profile or machine configuration is loaded.
        cases(base)
        project = base / "design"
        instance = Instance(project)
        allowed = delivery_check(instance, "package", "campaign-q3-final")
        results.append(allowed["status"] == "ok" and allowed["data"]["verdict"] == "pass")
        approval(project, allowed=False)
        blocked = delivery_check(instance, "package", "campaign-q3-final")
        results.append(blocked["status"] == "partial" and blocked["data"]["verdict"] == "blocked")
        results.append(blocked["data"]["enforcement"] == "machine" and blocked["data"]["external_shell_enforcement"] == "instruction_only")
        results.append(str(project) not in blocked["data"]["reason"])
    for number, value in enumerate(results, 1):
        print(f"{'PASS' if value else 'FAIL'} structured design guard {number}")
    print(f"EIF-RESULT: passed={sum(results)} total={len(results)}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
