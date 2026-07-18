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
scripts/tests/test_merge_gate.py without gh). There is no CLI flag that can
weaken it: no `--allow-missing-checks`, no `--skip-knowledge-delta`. What a
policy requires is a property of `core/policies/merge-policy.json`, not of
how this script is invoked. A repo genuinely without CI expresses that in its
own policy file (`required_check_contexts: []` + `allow_no_checks: true`);
the EIF policy has explicit required contexts and `allow_no_checks: false`,
so every context declared there is unconditionally enforced.

`evaluate_live_gate()` is the single live-evaluation entrypoint: it resolves
the repo, fetches the live PR, paginates every review thread, reads the live
Knowledge Delta, and calls the pure `evaluate_gate()`. It is called twice:
  1. once up front, for dry-run/evidence;
  2. once again immediately before the real merge, pinned to the head
     confirmed in step 1 - re-deriving checks/threads/Knowledge Delta fresh,
     not just re-reading the head SHA. A late change to any of those between
     the two calls blocks the merge even though the commit itself hasn't
     moved.

`--repo` auto-resolves via `gh repo view --json nameWithOwner` when omitted.
If it cannot be resolved, the script fails closed (blocks) rather than
skipping the review-thread check - there is no code path that silently
treats an unresolvable repo as "0 unresolved threads".

Requires the `gh` CLI, authenticated.

Usage:
    python scripts/eif_merge_pr.py --pr 12 [--repo owner/name] [--expected-head SHA] \\
        [--merge-method merge|squash|rebase] [--delete-branch] [--dry-run]
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
MAX_THREAD_PAGES = 1000  # sanity bound so a malformed GraphQL response can't spin forever


def load_policy(path: Path = POLICY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_gate(
    pr: dict,
    policy: dict,
    *,
    unresolved_threads: int,
    knowledge_delta_ok: bool,
    expected_head: str | None = None,
) -> list[str]:
    """Return a list of block reasons (empty list == all gates pass).

    Pure: takes already-fetched PR data + review-thread count + a
    Knowledge-Delta boolean, so the whole policy is unit-testable without gh.
    No parameter here can disable the required-context or Knowledge-Delta
    checks - what's required comes only from `policy`.
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
    required = policy["required_check_contexts"]
    acceptable = set(policy.get("acceptable_conclusions", ["SUCCESS"]))
    allow_no_checks = bool(policy.get("allow_no_checks", False))

    if not required:
        # A policy may legitimately declare no required contexts (a repo with
        # no CI) - but only as an explicit, documented property of the policy
        # file. No CLI flag can produce this state from a policy that *does*
        # declare required contexts.
        if not allow_no_checks:
            blocks.append(
                "policy has an empty required_check_contexts but allow_no_checks "
                "is not true - refusing to treat this as a no-CI repo"
            )
    else:
        if not checks:
            blocks.append(f"no status checks reported but policy requires {len(required)} context(s)")

        # Group by name rather than a last-write-wins dict: if a required
        # context appears more than once in the rollup, every occurrence must
        # be checked - a duplicate must never let one bad occurrence hide
        # behind a good one (or vice versa masking a failure).
        occurrences_by_name: dict[str, list[dict]] = {}
        for c in checks:
            occurrences_by_name.setdefault(c.get("name", ""), []).append(c)

        for name in required:
            occurrences = occurrences_by_name.get(name)
            if not occurrences:
                blocks.append(f"required check missing: {name!r}")
                continue
            for c in occurrences:
                if c.get("status") != "COMPLETED":
                    blocks.append(f"required check not completed ({c.get('status')}): {name!r}")
                elif c.get("conclusion") not in acceptable:
                    blocks.append(
                        f"required check conclusion {c.get('conclusion')!r} not in {sorted(acceptable)}: {name!r}"
                    )

    for c in checks:
        if c.get("name") in required:
            continue
        if c.get("status") == "COMPLETED" and c.get("conclusion") in FAILED_CONCLUSIONS:
            blocks.append(f"a non-required check failed: {c.get('name')!r} -> {c.get('conclusion')}")

    if policy.get("block_unresolved_review_threads", True) and unresolved_threads > 0:
        blocks.append(f"{unresolved_threads} unresolved review thread(s)")

    if policy.get("knowledge_delta_required", True) and not knowledge_delta_ok:
        blocks.append("Knowledge Delta section missing/empty in the live PR body")

    return blocks


# -------------------------------------------------------------------------- gh
def run_gh(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or proc.stderr or "").strip()


def resolve_repo(explicit: str | None) -> str:
    """Return 'owner/name'. Uses --repo if given, otherwise resolves the
    current directory's git remote via `gh repo view`. Fails closed (raises
    RuntimeError) if resolution is not possible - there is no fallback that
    proceeds with the review-thread check skipped."""
    if explicit:
        return explicit
    code, out = run_gh(["repo", "view", "--json", "nameWithOwner"])
    if code != 0:
        raise RuntimeError(f"cannot resolve --repo automatically (gh repo view failed): {out}")
    try:
        name = json.loads(out)["nameWithOwner"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise RuntimeError(f"cannot resolve --repo automatically (unexpected gh repo view output {out!r}): {e}") from e
    if not name or "/" not in name:
        raise RuntimeError(f"cannot resolve --repo automatically (malformed nameWithOwner: {name!r})")
    return name


def fetch_pr(pr_number: int, repo: str) -> dict:
    code, out = run_gh(["pr", "view", str(pr_number), "--repo", repo, "--json", PR_FIELDS])
    if code != 0:
        raise RuntimeError(f"cannot read PR #{pr_number}: {out}")
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"cannot parse PR #{pr_number} JSON: {e}") from e


def fetch_unresolved_threads(pr_number: int, repo: str) -> int:
    """Count UNRESOLVED review threads via paginated GraphQL. `repo` is
    required ('owner/name') - callers must resolve it first; there is no
    skip-if-absent path. Any gh failure or unexpected/malformed JSON raises
    RuntimeError, which callers must treat as a block, never as zero."""
    owner, name = repo.split("/", 1)
    query = (
        "query($o:String!,$n:String!,$p:Int!,$c:String){repository(owner:$o,name:$n){"
        "pullRequest(number:$p){reviewThreads(first:100, after:$c){"
        "nodes{isResolved} pageInfo{hasNextPage endCursor}}}}}"
    )
    unresolved = 0
    cursor: str | None = None
    for page in range(1, MAX_THREAD_PAGES + 1):
        gh_args = [
            "api", "graphql", "-f", f"query={query}",
            "-F", f"o={owner}", "-F", f"n={name}", "-F", f"p={pr_number}",
        ]
        if cursor:
            gh_args += ["-F", f"c={cursor}"]
        code, out = run_gh(gh_args)
        if code != 0:
            raise RuntimeError(f"cannot read review threads (page {page}): {out}")
        try:
            thread_conn = json.loads(out)["data"]["repository"]["pullRequest"]["reviewThreads"]
            nodes = thread_conn["nodes"]
            page_info = thread_conn["pageInfo"]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise RuntimeError(f"cannot read review threads (unexpected GraphQL response on page {page}): {e}") from e
        unresolved += sum(1 for t in nodes if not t.get("isResolved"))
        if not page_info.get("hasNextPage"):
            return unresolved
        cursor = page_info.get("endCursor")
        if not cursor:
            raise RuntimeError("GraphQL reported hasNextPage=true but no endCursor - aborting rather than looping forever")
    raise RuntimeError(f"review thread pagination exceeded {MAX_THREAD_PAGES} pages - aborting rather than looping forever")


def knowledge_delta_ok(body: str) -> bool:
    classifier = SCRIPT_DIR / "eif_check_knowledge_delta.py"
    proc = subprocess.run(
        [sys.executable, str(classifier), "--body-stdin"],
        input=body or "", capture_output=True, text=True, encoding="utf-8",
    )
    return proc.returncode == 0


def evaluate_live_gate(
    pr_number: int, repo: str, policy: dict, *, expected_head: str | None
) -> tuple[list[str], dict]:
    """The single live-evaluation entrypoint. Fetches the live PR, paginates
    every review thread, reads the live Knowledge Delta, and calls the pure
    evaluate_gate(). Called once for dry-run/evidence and once more,
    immediately before the real merge, pinned to the head confirmed by the
    first call - the second call re-derives every live signal, not just the
    head SHA, so a late change to checks/threads/body is caught even when the
    commit itself has not moved."""
    pr = fetch_pr(pr_number, repo)
    threads = fetch_unresolved_threads(pr_number, repo)
    kd_ok = knowledge_delta_ok(pr.get("body") or "")
    blocks = evaluate_gate(
        pr, policy,
        unresolved_threads=threads,
        knowledge_delta_ok=kd_ok,
        expected_head=expected_head,
    )
    return blocks, pr


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--repo", default=None, help="owner/name - auto-resolved via `gh repo view` when omitted; resolution failure blocks (fail closed)")
    ap.add_argument("--expected-head", default=None, help="Abort unless the live PR head equals this SHA (evidence-freeze pin)")
    ap.add_argument("--merge-method", default=None, choices=["merge", "squash", "rebase"], help="Defaults to policy.merge_method; if given, must equal it")
    ap.add_argument("--delete-branch", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    policy = load_policy()

    merge_method = args.merge_method or policy.get("merge_method", "merge")
    if args.merge_method and args.merge_method != policy.get("merge_method", "merge"):
        print(f"MERGE-GATE BLOCK: --merge-method {args.merge_method!r} != policy merge_method {policy.get('merge_method')!r}")
        return 1

    try:
        repo = resolve_repo(args.repo)
    except RuntimeError as e:
        print(f"MERGE-GATE BLOCK: {e}")
        return 1

    try:
        blocks, pr = evaluate_live_gate(args.pr, repo, policy, expected_head=args.expected_head)
    except RuntimeError as e:
        print(f"MERGE-GATE BLOCK: {e}")
        return 1

    if blocks:
        for b in blocks:
            print(f"MERGE-GATE BLOCK: {b}")
        return 1

    head = pr["headRefOid"]
    print(f"MERGE-GATE OK: PR #{args.pr} ({pr['headRefName']} -> {pr['baseRefName']}) at {head}")

    if args.dry_run:
        print("DRY-RUN: all gates passed; merge not executed.")
        return 0

    # Full re-verification immediately before merging, pinned to the head just
    # confirmed above. This re-derives checks/threads/Knowledge Delta fresh -
    # it is not a bare SHA re-read - so a late change to any of them between
    # the two evaluate_live_gate() calls blocks the merge.
    try:
        blocks2, pr2 = evaluate_live_gate(args.pr, repo, policy, expected_head=head)
    except RuntimeError as e:
        print(f"MERGE-GATE BLOCK (final pre-merge check): {e}")
        return 1
    if blocks2:
        for b in blocks2:
            print(f"MERGE-GATE BLOCK (final pre-merge check): {b}")
        return 1

    merge_args = ["pr", "merge", str(args.pr), "--repo", repo, f"--{merge_method}", "--match-head-commit", head]
    if args.delete_branch:
        merge_args.append("--delete-branch")
    code, out = run_gh(merge_args)
    if code != 0:
        print(f"MERGE-GATE BLOCK: gh pr merge failed (possibly a race with a new push): {out}")
        return 1

    code, out = run_gh(["pr", "view", str(args.pr), "--repo", repo, "--json", "state,mergedAt,mergeCommit"])
    print(f"MERGED: {out}")
    print(pr["url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
