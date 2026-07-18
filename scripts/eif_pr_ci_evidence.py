#!/usr/bin/env python3
"""Decide whether an exact merged PR lets a push reuse successful CI evidence.

The decision is fail-closed. Any API error, ambiguous PR association, missing
required context, or non-success result keeps the full push CI enabled.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def decide_reuse(
    pull_requests: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    *,
    commit_sha: str,
    base_branch: str,
    workflow_name: str,
    required_contexts: list[str],
) -> dict[str, Any]:
    matching = [
        pr
        for pr in pull_requests
        if pr.get("merged_at")
        and pr.get("merge_commit_sha") == commit_sha
        and (pr.get("base") or {}).get("ref") == base_branch
    ]
    if len(matching) != 1:
        return {
            "reuse_pr_ci": False,
            "reason": f"expected one exact merged PR, found {len(matching)}",
            "pull_request_number": None,
        }

    pull_request_number = matching[0].get("number")
    successful = {
        check.get("name")
        for check in checks
        if check.get("workflow") == workflow_name
        and check.get("state") == "SUCCESS"
    }
    missing = [context for context in required_contexts if context not in successful]
    if missing:
        return {
            "reuse_pr_ci": False,
            "reason": "required PR checks missing or not successful: " + ", ".join(missing),
            "pull_request_number": pull_request_number,
        }

    return {
        "reuse_pr_ci": True,
        "reason": "exact merged PR has all required successful CI checks",
        "pull_request_number": pull_request_number,
    }


def run_json(arguments: list[str]) -> Any:
    completed = subprocess.run(
        arguments,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def write_github_output(path: str | None, decision: dict[str, Any]) -> None:
    if not path:
        return
    reason = " ".join(str(decision["reason"]).splitlines())
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(f"reuse-pr-ci={str(decision['reuse_pr_ci']).lower()}\n")
        stream.write(f"reason={reason}\n")
        stream.write(f"pr-number={decision.get('pull_request_number') or ''}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--base-branch", required=True)
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT"))
    args = parser.parse_args(argv)

    decision: dict[str, Any] = {
        "reuse_pr_ci": False,
        "reason": "full CI is required",
        "pull_request_number": None,
    }
    try:
        policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
        required_contexts = policy["required_check_contexts"]
        pull_requests = run_json(
            ["gh", "api", f"repos/{args.repository}/commits/{args.commit_sha}/pulls"]
        )
        candidates = [
            pr
            for pr in pull_requests
            if pr.get("merged_at")
            and pr.get("merge_commit_sha") == args.commit_sha
            and (pr.get("base") or {}).get("ref") == args.base_branch
        ]
        if len(candidates) == 1:
            checks = run_json(
                [
                    "gh",
                    "pr",
                    "checks",
                    str(candidates[0]["number"]),
                    "--repo",
                    args.repository,
                    "--json",
                    "name,state,workflow",
                ]
            )
        else:
            checks = []
        decision = decide_reuse(
            pull_requests,
            checks,
            commit_sha=args.commit_sha,
            base_branch=args.base_branch,
            workflow_name=args.workflow_name,
            required_contexts=required_contexts,
        )
    except Exception as exc:  # noqa: BLE001 - every failure must fall back to full CI
        decision["reason"] = f"evidence lookup failed closed: {exc}"

    write_github_output(args.github_output, decision)
    print(json.dumps(decision, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
