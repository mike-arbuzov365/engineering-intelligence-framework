#!/usr/bin/env python3
"""Tests for fail-closed merged PR CI evidence reuse."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eif_pr_ci_evidence import decide_reuse  # noqa: E402


SHA = "a" * 40
REQUIRED = ["Policy checks", "Package build required", "License required"]


def pull_request(*, sha: str = SHA, base: str = "main", merged: bool = True) -> dict:
    return {
        "number": 81,
        "merged_at": "2026-07-18T12:00:00Z" if merged else None,
        "merge_commit_sha": sha,
        "base": {"ref": base},
        "head": {"sha": "c" * 40},
    }


def successful_checks() -> list[dict]:
    return [
        {
            "name": name,
            "conclusion": "success",
            "app": {"slug": "github-actions"},
        }
        for name in REQUIRED
    ]


def main() -> int:
    cases = 0

    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    evidence_job = workflow.split("  ci-evidence:", 1)[1].split("\n  policy-gate:", 1)[0]
    assert "checks: read" in evidence_job
    cases += 1

    success = decide_reuse(
        [pull_request()],
        successful_checks(),
        commit_sha=SHA,
        base_branch="main",
        required_contexts=REQUIRED,
    )
    assert success["reuse_pr_ci"] is True
    cases += 1

    for prs, checks in [
        ([pull_request(sha="b" * 40)], successful_checks()),
        ([pull_request(base="dev")], successful_checks()),
        ([pull_request(merged=False)], successful_checks()),
        ([pull_request(), pull_request()], successful_checks()),
        ([pull_request()], successful_checks()[:-1]),
        (
            [pull_request()],
            [
                *successful_checks()[:-1],
                {
                    "name": REQUIRED[-1],
                    "conclusion": "failure",
                    "app": {"slug": "github-actions"},
                },
            ],
        ),
    ]:
        decision = decide_reuse(
            prs,
            checks,
            commit_sha=SHA,
            base_branch="main",
            required_contexts=REQUIRED,
        )
        assert decision["reuse_pr_ci"] is False
        cases += 1

    print(f"test_pr_ci_evidence: {cases}/{cases} checks passed")
    print(f"EIF-RESULT: passed={cases} total={cases}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
