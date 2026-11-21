#!/usr/bin/env python3
"""Independent acceptance cases for the orchestrated packet reader.

An adapter exports open_case(data), a context manager that materializes the
input once and yields a zero-argument read function. The function maps actual
reader output to the fixture's legacy and admission fields. The input uses
symbolic revisions and a roadmap ordered by the sessions list. An adapter
may translate them into native sources. It receives only inputs.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import runpy
import sys
from tempfile import TemporaryDirectory


FIXTURE = Path(__file__).parent / "fixtures/orchestrator_admission.json"


def scenarios(fixture):
    for case in fixture["cases"]:
        data = deepcopy(fixture["input"])
        data["sessions"][0].update(case.get("first", {}))
        data["sessions"][1].update(case.get("second", {}))
        data["sessions"] = data["sessions"][:case.get("session_count")]
        if case.get("review", {}) is None:
            data["reviews"].clear()
        else:
            data["reviews"][0].update(case.get("review", {}))
        expected = {"legacy": case.get("legacy", fixture["legacy"]), "admission": case["admission"]}
        yield case["id"], data, expected, case.get("reads", 1)


def check(label, expected, actual):
    if actual == expected:
        print(f"PASS {label}")
        return True
    print(f"FAIL {label}: expected {expected!r}; got {actual!r}")
    return False


def run_contract(fixture, open_case):
    failures = 0
    for case_id, data, expected, reads in scenarios(fixture):
        with open_case(data) as read:
            for read_number in range(1, reads + 1):
                if not check(f"{case_id} read {read_number}", expected, read()):
                    failures += 1
    return int(failures > 0)


def run_baseline(fixture):
    """Compare the real legacy response and expose unsafe use as admission."""
    root = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(root / "src"), str(root / "scripts/tests/fixtures/eif_mcp")]
    from engineering_intelligence_framework.service import Instance
    from engineering_intelligence_framework.service.packets import packet_status
    from seed import seed

    false_admissions = 0
    with TemporaryDirectory(prefix="eif-admission-") as tmp:
        instance = Instance(seed(Path(tmp) / "project"))
        for case_id, data, expected, reads in scenarios(fixture):
            folder = instance.root / instance.packets_root / case_id
            sessions = folder / "sessions"
            sessions.mkdir(parents=True)
            order = "\n".join(f"## Session {row['id'].split('-')[1]}" for row in data["sessions"])
            (folder / "04-ROADMAP-synthetic.md").write_text(order + "\n", encoding="utf-8")
            for row in data["sessions"]:
                launch = f"---\n{json.dumps(row)}\n---\n"
                (sessions / f"{row['id']}-synthetic.md").write_text(launch, encoding="utf-8")
            (folder / "review-fixture.json").write_text(json.dumps(data["reviews"]), encoding="utf-8")
            for _ in range(reads):
                result = packet_status(instance, case_id)
                legacy = {"status": result["status"], "next_session": result["data"]["next_session"],
                          "reason": result["data"]["reason"]}
                if legacy != expected["legacy"]:
                    print(f"ERROR {case_id}: legacy response changed: {legacy!r}")
                    return 2
            admission = expected["admission"]
            if legacy["next_session"] != admission["next_session"]:
                false_admissions += 1
                print(f"FAIL {case_id}: legacy next_session={legacy['next_session']}; "
                      f"expected admission next_session={admission['next_session']} ({admission['reason']})")
            else:
                print(f"PASS {case_id}: legacy next_session={legacy['next_session']}")
    return int(false_admissions > 0)


def revision_control(data, require_current_revision):
    """Test-only comparison for the pair whose sole change is the work revision."""
    session, following = data["sessions"]
    review, = data["reviews"]
    if require_current_revision and review["reviewed_revision"] != session["current_revision"]:
        return {"next_session": None, "blocker": session["id"], "reason": "stale_revision",
                "next_action": "review_current_revision"}
    return {"next_session": following["id"], "blocker": None, "reason": "ready",
            "next_action": "start_next_session"}


def run_controls(fixture):
    cases = {case_id: (data, expected["admission"]) for case_id, data, expected, _ in scenarios(fixture)}
    mismatches = []
    for require_current_revision in (True, False):
        for case_id in ("accepted_current", "stale_revision"):
            data, expected = cases[case_id]
            actual = revision_control(data, require_current_revision)
            if not check(f"{case_id} require_current_revision={require_current_revision}", expected, actual):
                mismatches.append((require_current_revision, case_id))
    return int(mismatches != [(False, "stale_revision")])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--baseline", action="store_true", help="Compare current legacy progress to admission")
    mode.add_argument("--controls", action="store_true", help="Check the positive and weakened revision controls")
    mode.add_argument("--fingerprint", action="store_true", help="Print the acceptance version and SHA-256")
    mode.add_argument("--adapter", type=Path, help="Run acceptance cases against a reader adapter")
    args = parser.parse_args()
    fixture_text = FIXTURE.read_text(encoding="utf-8")
    fixture = json.loads(fixture_text)
    if args.baseline:
        return run_baseline(fixture)
    if args.controls:
        return run_controls(fixture)
    if args.fingerprint:
        runner_text = Path(__file__).read_text(encoding="utf-8")
        fingerprint = sha256((runner_text + "\0" + fixture_text).encode("utf-8")).hexdigest()
        print(f"{fixture['version']} sha256:{fingerprint}")
        return 0
    return run_contract(fixture, runpy.run_path(str(args.adapter))["open_case"])


if __name__ == "__main__":
    raise SystemExit(main())
