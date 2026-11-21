#!/usr/bin/env python3
"""Optional browser proof for the software profile's retry example."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/tests/fixtures/eif_mcp")]

from engineering_intelligence_framework.service import Instance  # noqa: E402
from engineering_intelligence_framework.service.admission import MODE  # noqa: E402
from seed import seed  # noqa: E402
from test_service_golden import capture  # noqa: E402

PACKET = "web-retry"
FIXTURE = ROOT / "scripts/tests/fixtures/eif_web/verify.mjs"


def node_proof(mode):
    result = subprocess.run(["node", str(FIXTURE), mode], capture_output=True, text=True, timeout=80)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout)


def main():
    with tempfile.TemporaryDirectory(prefix="eif-web-profile-") as raw:
        base = Path(raw).resolve()
        workspace = base / "workspace"
        assert capture(["workspace", "new", str(workspace)], base)["rc"] == 0
        installed = capture(["workspace", "profile", "install", "software-development",
                             "--workspace-path", str(workspace)], base)
        assert installed["rc"] == 0, installed
        root = seed(base / "project")
        profile_project = base / "profile-project"
        registered = capture(["new", str(profile_project), "--project-name", "synthetic-web",
                              "--registry", str(workspace / ".eif/projects.yaml"),
                              "--profile", "software-development"], base)
        assert registered["rc"] == 0, registered
        for repo in (workspace, profile_project):
            subprocess.run(["git", "-C", str(repo), "add", "--all"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(repo), "-c", "user.name=EIF test", "-c", "user.email=eif@example.invalid",
                 "commit", "--no-gpg-sign", "-m", "Synthetic web profile baseline"],
                check=True, capture_output=True,
            )
        applied = capture(["projects", "upgrade", "--registry", str(workspace / ".eif/projects.yaml"), "--apply"], base)
        assert applied["rc"] == 0, applied
        guide = profile_project / ".eif/workspace-runtime/playbooks/web-change-acceptance.md"
        assert guide.is_file()
        assert not (root / ".eif/workspace-runtime/playbooks/web-change-acceptance.md").exists()
        print("PASS profile activation pins the optional guide")

        instance = Instance(profile_project)
        root = profile_project
        folder = root / instance.packets_root / PACKET
        sessions = folder / "sessions"
        sessions.mkdir(parents=True)
        (folder / "04-ROADMAP.md").write_text(
            f"---\norchestration_mode: {MODE}\n---\n## Session 001\n## Session 002\n", encoding="utf-8",
        )
        launch = {"id": "SESSION-001", "status": "completed", "depends_on": [],
                  "orchestration": {"goal": "Retry a failed request from the keyboard",
                                    "scope": ["retry view", "action button"],
                                    "no_touch": ["service contract"],
                                    "criteria": {"AC-04": "From failure, Tab to Retry and press Enter to reach success"}}}
        next_launch = {"id": "SESSION-002", "status": "prepared", "depends_on": ["SESSION-001"],
                       "orchestration": {"goal": "Verify the next report", "scope": ["report"],
                                         "no_touch": ["retry view"], "criteria": {"AC-05": "Report is readable"}}}

        def write_launch(row):
            path = sessions / f"{row['id']}-web.md"
            path.write_text(f"---\n{json.dumps(row)}\n---\n", encoding="utf-8")

        def cli(command, *args):
            result = capture(["packet", command, PACKET, "--instance-path", str(root), *args], root)
            assert result["rc"] == 0, result
            return json.loads(result["stdout"])["data"]

        def record(attempt, proof, decision, result, evidence):
            launch["orchestration"].update(attempt=attempt, current_revision=proof["revision"], base_revision=api["revision"])
            write_launch(launch)
            review = {"instance": instance.project["id"], "packet": PACKET, "session": launch["id"],
                      "attempt": attempt, "base_revision": api["revision"], "reviewed_revision": proof["revision"],
                      "decision": decision, "reason": evidence,
                      "criteria": {"AC-04": {"result": result, "evidence": evidence}}}
            (root / "fixture-review.json").write_text(json.dumps(review), encoding="utf-8")
            assert cli("record-review", "--record", "fixture-review.json")["record"] == "recorded"

        api = node_proof("--api")
        assert api["responses"] == [503, 200]
        write_launch(next_launch)
        record(1, api, "changes_requested", "not_run", "API returned 503 and 200; keyboard evidence missing.")
        returned = cli("status", "--session", launch["id"])
        assert returned["next_session"] == "SESSION-002" and returned["admission"]["next_session"] is None
        assert returned["admission"]["reason"] == "changes_requested"
        print("PASS API-only evidence returns AC-04 and blocks the next session")

        browser = node_proof("--browser")
        assert browser["revision"] != api["revision"] and browser["negativeControl"] and browser["check"]
        record(2, browser, "accepted", "pass", f"Chromium {browser['browser']}: {browser['check']}.")
        accepted = cli("status", "--session", launch["id"])
        assert accepted["admission"]["next_session"] == "SESSION-002"
        assert accepted["handoff"]["prior_feedback"][0]["attempt"] == 1
        print(f"PASS Chromium {browser['browser']}: mouse-only control fails; keyboard evidence accepts attempt 2")
        print("EIF-RESULT: passed=3 total=3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
