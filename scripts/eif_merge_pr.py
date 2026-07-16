#!/usr/bin/env python3
"""Controlled merge entrypoint - the supported merge path for this repo.

Platform note: GitHub branch protection / rulesets are UNAVAILABLE on this
repository's plan (private repo, free tier -> the branch-protection and
rulesets APIs return HTTP 403 "Upgrade to GitHub Pro or make this repository
public"). This script is therefore the technical enforcement (a "wrapper-only"
gate), not a substitute for platform enforcement - see
docs/architecture/merge-enforcement.md and core/policies/merge-policy.json.
Agents must merge only through this script; direct `gh pr merge` from agent
shells is denied by the RTK PreToolUse hook. It does NOT stop a human with
push access from bypassing it - that residual risk is documented, not
eliminated (only branch protection or public visibility + required checks
would eliminate it).

The gate is a pure function (`evaluate_gate`, unit-tested in
scripts/tests/test_merge_gate.py without gh). It re-verifies, immediately
before merging:
  - PR OPEN, not draft, reviewDecision != CHANGES_REQUESTED;
  - base branch == policy.base_branch;
  - (optional) live head == --expected-head;
  - every policy.required_check_contexts is PRESENT and SUCCESS - a required
    context that is missing / pending / failed / cancelled / skipped BLOCKS;
  - no non-required check has failed;
  - Knowledge Delta present in the LIVE PR body (fetched now, not frozen);
  - zero UNRESOLVED review threads.
The merge is pinned to the verified head (`gh pr merge --match-head-commit`),
and the head is re-read one last time right before the merge so a late push
aborts instead of merging unreviewed code. The required check contexts are
read from a single source (core/policies/merge-policy.json), never hardcoded
here.

Requires the `gh` CLI, authenticated.

Usage:
    python scripts/eif_merge_pr.py --pr 12 [--repo owner/name] [--expected-head SHA] \\
        [--merge-method merge|squash|rebase] [--delete-branch] [--dry-run] \\
        [--allow-missing-checks] [--skip-knowledge-delta]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
POLICY_PATH = SCRIPT_DIR.parent / "core" / "policies" / "merge-policy.json"

PR_FIELDS = "state,isDraft,headRefOid,baseRefName,headRefName,body,reviewDecision,statusCheckRollup,url"
FAILED_CONCLUSIONS = {"FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}


def load_policy(path: Path = POLICY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_gate(
    pr: dict,
    policy: dict,
    *,
    unresolved_threads: int,
    knowledge_delta_ok: bool,
    expected_head: str | None = None,
    allow_missing_checks: bool = False,
) -> list[str]:
    """Return a list of block reasons (empty list == all gates pass).

    Pure: takes already-fetched PR data + review-thread count + a
    Knowledge-Delta boolean, so the whole policy is unit-testable without gh.
    """
    blocks: list[str] = []

    if pr.get("state") != "OPEN":
        blocks.append(f"PR is {pr.get('state')}, not OPEN")
    if pr.get("isDraft"):
        blocks.append("PR is a draft")
    if pr.get("reviewDecision") == "CHANGES_REQUESTED":
        blocks.append("review decision is CHANGES_REQUESTED")

    base = pr.get("baseRefName")
    if base != policy["base_branch"]:
        blocks.append(f"base branch is {base!r}, policy requires {policy['base_branch']!r}")

    head = pr.get("headRefOid")
    if expected_head and head != expected_head:
        blocks.append(f"live head {head} != expected head {expected_head} (moved after evidence collection)")

    checks = pr.get("statusCheckRollup") or []
    by_name = {c.get("name", ""): c for c in checks}
    required = policy["required_check_contexts"]
    acceptable = set(policy.get("acceptable_conclusions", ["SUCCESS"]))

    # --allow-missing-checks is only for a repo genuinely without CI: it
    # skips BOTH the "no checks reported" block and the required-context
    # enforcement (there are no contexts to require). It never weakens a
    # repo that does report checks - a failed check below still blocks.
    if not allow_missing_checks:
        if not checks:
            blocks.append("no status checks reported (pass --allow-missing-checks only for a repo without CI)")
        for name in required:
            c = by_name.get(name)
            if c is None:
                blocks.append(f"required check missing: {name!r}")
                continue
            if c.get("status") != "COMPLETED":
                blocks.append(f"required check not completed ({c.get('status')}): {name!r}")
                continue
            if c.get("conclusion") not in acceptable:
                blocks.append(f"required check conclusion {c.get('conclusion')!r} not in {sorted(acceptable)}: {name!r}")

    for c in checks:
        if c.get("name") in required:
            continue
        if c.get("status") == "COMPLETED" and c.get("conclusion") in FAILED_CONCLUSIONS:
            blocks.append(f"a non-required check failed: {c.get('name')!r} -> {c.get('conclusion')}")

    if policy.get("block_unresolved_review_threads", True) and unresolved_threads > 0:
        blocks.append(f"{unresolved_threads} unresolved review thread(s)")

    if not knowledge_delta_ok:
        blocks.append("Knowledge Delta section missing/empty in the live PR body")

    return blocks


# -------------------------------------------------------------------------- gh
def run_gh(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or proc.stderr or "").strip()


def fetch_pr(pr_number: int, repo_args: list[str]) -> dict:
    code, out = run_gh(["pr", "view", str(pr_number), *repo_args, "--json", PR_FIELDS])
    if code != 0:
        raise RuntimeError(f"cannot read PR #{pr_number}: {out}")
    return json.loads(out)


def fetch_unresolved_threads(pr_number: int, repo: str | None) -> int:
    """Count UNRESOLVED review threads via GraphQL. Returns 0 if none. Repo
    is 'owner/name'; if None, derive owner/name from the PR's url is not
    available here, so require --repo for the thread check (callers pass it)."""
    if not repo:
        return 0  # cannot query without owner/name; main() warns
    owner, name = repo.split("/", 1)
    query = (
        "query($o:String!,$n:String!,$p:Int!){repository(owner:$o,name:$n){"
        "pullRequest(number:$p){reviewThreads(first:100){nodes{isResolved}}}}}"
    )
    code, out = run_gh([
        "api", "graphql", "-f", f"query={query}",
        "-F", f"o={owner}", "-F", f"n={name}", "-F", f"p={pr_number}",
    ])
    if code != 0:
        raise RuntimeError(f"cannot read review threads: {out}")
    data = json.loads(out)
    nodes = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    return sum(1 for t in nodes if not t.get("isResolved"))


def knowledge_delta_ok(body: str) -> bool:
    classifier = SCRIPT_DIR / "eif_check_knowledge_delta.py"
    proc = subprocess.run(
        [sys.executable, str(classifier), "--body-stdin"],
        input=body or "", capture_output=True, text=True, encoding="utf-8",
    )
    return proc.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--repo", default=None, help="owner/name - defaults to the current directory's git remote (required for the review-thread check)")
    ap.add_argument("--expected-head", default=None, help="Abort unless the live PR head equals this SHA (evidence-freeze pin)")
    ap.add_argument("--merge-method", default=None, choices=["merge", "squash", "rebase"], help="Defaults to policy.merge_method; if given, must equal it")
    ap.add_argument("--delete-branch", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-missing-checks", action="store_true", help="Only for repos without CI configured")
    ap.add_argument("--skip-knowledge-delta", action="store_true")
    args = ap.parse_args()

    policy = load_policy()
    repo_args = ["--repo", args.repo] if args.repo else []

    merge_method = args.merge_method or policy.get("merge_method", "merge")
    if args.merge_method and args.merge_method != policy.get("merge_method", "merge"):
        print(f"MERGE-GATE BLOCK: --merge-method {args.merge_method!r} != policy merge_method {policy.get('merge_method')!r}")
        return 1

    if not args.repo:
        print("MERGE-GATE NOTE: --repo not given; the unresolved-review-thread check is skipped (cannot run GraphQL without owner/name). Pass --repo to enforce it.", file=sys.stderr)

    try:
        pr = fetch_pr(args.pr, repo_args)
        threads = fetch_unresolved_threads(args.pr, args.repo) if args.repo else 0
    except RuntimeError as e:
        print(f"MERGE-GATE BLOCK: {e}")
        return 1

    kd_ok = True if args.skip_knowledge_delta else knowledge_delta_ok(pr.get("body") or "")

    blocks = evaluate_gate(
        pr, policy,
        unresolved_threads=threads,
        knowledge_delta_ok=kd_ok,
        expected_head=args.expected_head,
        allow_missing_checks=args.allow_missing_checks,
    )
    if blocks:
        for b in blocks:
            print(f"MERGE-GATE BLOCK: {b}")
        return 1

    head = pr["headRefOid"]
    print(f"MERGE-GATE OK: PR #{args.pr} ({pr['headRefName']} -> {pr['baseRefName']}) at {head}")

    if args.dry_run:
        print("DRY-RUN: all gates passed; merge not executed.")
        return 0

    # Evidence-freeze: re-read the head one last time; abort if it moved since
    # the gate evaluation above (a race with a late push).
    try:
        fresh = fetch_pr(args.pr, repo_args)
    except RuntimeError as e:
        print(f"MERGE-GATE BLOCK: {e}")
        return 1
    if fresh.get("headRefOid") != head:
        print(f"MERGE-GATE BLOCK: head moved from {head} to {fresh.get('headRefOid')} during gate evaluation - aborting")
        return 1

    merge_args = ["pr", "merge", str(args.pr), *repo_args, f"--{merge_method}", "--match-head-commit", head]
    if args.delete_branch:
        merge_args.append("--delete-branch")
    code, out = run_gh(merge_args)
    if code != 0:
        print(f"MERGE-GATE BLOCK: gh pr merge failed (possibly a race with a new push): {out}")
        return 1

    code, out = run_gh(["pr", "view", str(args.pr), *repo_args, "--json", "state,mergedAt,mergeCommit"])
    print(f"MERGED: {out}")
    print(pr["url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
