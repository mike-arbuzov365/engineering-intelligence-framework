#!/usr/bin/env python3
"""Controlled merge entrypoint - genericized port of the pattern the
private production instance this framework was extracted from uses (a
PowerShell script there; rewritten here in Python for this repo's
tool-agnostic, cross-platform scripts/ directory - see
core/policies/decisions.md for why this counts as a direct genericization,
not a new proposal).

Why this exists: CI checks that run and report pass/fail do not, by
themselves, prevent a merge - GitHub repository settings (required status
checks / branch protection) do that, and are not configured for this
repository yet (see docs/architecture/HOW-EIF-WORKS.md#quality). Until
they are, this script is the technical enforcement: it re-verifies check
status, Knowledge Delta completeness, and review state immediately before
merging, and merges pinned to the verified head commit SHA so a late push
during the check can't slip in unreviewed.

This does not, by itself, stop someone from running `gh pr merge` directly
instead of this script - that requires an agent-side guard (a hook
denying the direct command) or repository branch protection, neither of
which this script can enforce on its own. Document/enforce that
separately per adapter, the same way the private instance does.

Requires the `gh` CLI, authenticated.

Usage:
    python scripts/eif_merge_pr.py --pr 12 [--repo owner/name] [--merge-method merge|squash|rebase] [--delete-branch] [--dry-run] [--allow-missing-checks] [--skip-knowledge-delta]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def fail(message: str) -> int:
    print(f"MERGE-GATE BLOCK: {message}")
    return 1


def run_gh(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or proc.stderr or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--repo", default=None, help="owner/name - defaults to the current directory's git remote")
    ap.add_argument("--merge-method", choices=["merge", "squash", "rebase"], default="merge")
    ap.add_argument("--delete-branch", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-missing-checks", action="store_true", help="Only for repos without CI configured")
    ap.add_argument("--skip-knowledge-delta", action="store_true")
    args = ap.parse_args()

    repo_args = ["--repo", args.repo] if args.repo else []

    fields = "state,isDraft,headRefOid,baseRefName,headRefName,body,reviewDecision,statusCheckRollup,url"
    code, out = run_gh(["pr", "view", str(args.pr), *repo_args, "--json", fields])
    if code != 0:
        return fail(f"cannot read PR #{args.pr}: {out}")
    pr = json.loads(out)

    if pr["state"] != "OPEN":
        return fail(f"PR #{args.pr} is {pr['state']}, not OPEN.")
    if pr["isDraft"]:
        return fail(f"PR #{args.pr} is a draft.")
    if pr.get("reviewDecision") == "CHANGES_REQUESTED":
        return fail("review decision is CHANGES_REQUESTED; resolve the review first.")

    checks = pr.get("statusCheckRollup") or []
    if not checks and not args.allow_missing_checks:
        return fail("no status checks reported; pass --allow-missing-checks only for repos without CI.")

    pending = []
    failed_checks = []
    for check in checks:
        name = check.get("name", "")
        status = check.get("status", "")
        conclusion = check.get("conclusion", "")
        if status != "COMPLETED":
            pending.append(name)
            continue
        if conclusion not in ("SUCCESS", "NEUTRAL", "SKIPPED"):
            failed_checks.append(f"{name} -> {conclusion}")

    if pending:
        return fail("checks still running: " + "; ".join(pending))
    if failed_checks:
        return fail("checks failed: " + "; ".join(failed_checks))

    if not args.skip_knowledge_delta:
        classifier = SCRIPT_DIR / "eif_check_knowledge_delta.py"
        proc = subprocess.run(
            [sys.executable, str(classifier), "--body-stdin"],
            input=pr.get("body") or "",
            capture_output=True, text=True, encoding="utf-8",
        )
        if proc.returncode != 0:
            return fail(f"Knowledge Delta check failed: {proc.stdout.strip()}")

    head_sha = pr["headRefOid"]
    print(f"MERGE-GATE OK: PR #{args.pr} ({pr['headRefName']} -> {pr['baseRefName']}) at {head_sha}")

    if args.dry_run:
        print("DRY-RUN: all gates passed; merge not executed.")
        return 0

    merge_args = ["pr", "merge", str(args.pr), *repo_args, f"--{args.merge_method}", "--match-head-commit", head_sha]
    if args.delete_branch:
        merge_args.append("--delete-branch")
    code, out = run_gh(merge_args)
    if code != 0:
        return fail(f"gh pr merge failed (possibly a race with a new push): {out}")

    code, out = run_gh(["pr", "view", str(args.pr), *repo_args, "--json", "state,mergedAt"])
    print(f"MERGED: {out}")
    print(pr["url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
