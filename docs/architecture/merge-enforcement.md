# Repository merge enforcement

This document is the honest, repository-visible statement of how merges to
`main` are controlled, and what is technically enforced versus advisory.

## Platform reality (verified, not assumed)

This repository is **private on the free GitHub plan**. GitHub's branch
protection and rulesets APIs are **not available** on that plan for a private
repository - both return:

```
HTTP 403: Upgrade to GitHub Pro or make this repository public to enable this feature.
```

So platform-level "required status checks" cannot be configured here. Making
CI "required by policy" *technically* enforceable therefore has exactly two
platform routes, **both deferred to the owner and neither done here**:

1. Upgrade the account to GitHub Pro (enables branch protection / rulesets on
   a private repo); or
2. Make the repository public (enables them on the free plan).

Changing repository **visibility is out of scope** and was not done.

## Enforcement mode: wrapper-only

Until one of the platform routes above is taken, the enforcement is a
**controlled merge wrapper**, `scripts/eif_merge_pr.py`. It is the supported
merge path, and it has **no CLI flag that can weaken it** - no
`--allow-missing-checks`, no `--skip-knowledge-delta`. What is required is a
property of `core/policies/merge-policy.json` alone.

`--repo` auto-resolves via `gh repo view --json nameWithOwner` when omitted.
If it cannot be resolved, the script **fails closed** - it blocks rather than
skipping the review-thread check (there is no code path that silently treats
an unresolvable repo as "0 unresolved threads").

`evaluate_live_gate()` is the single live-evaluation entrypoint (fetch the PR,
paginate every review thread, read the live Knowledge Delta, call the pure
`eif_merge_pr.evaluate_gate`, unit- and integration-tested in
`scripts/tests/test_merge_gate.py`). It runs **twice**: once up front for
dry-run/evidence, and once more immediately before the real merge, pinned to
the head confirmed by the first pass. The second pass re-derives every live
signal - not just the head SHA - so a check flipping to failure, a new
unresolved thread, or the Knowledge Delta body degrading between the two
passes blocks the merge even though the commit itself never moved.

Each pass verifies:

- the PR is OPEN, not a draft, and its review decision is not
  `CHANGES_REQUESTED`;
- the base branch equals `merge-policy.json`'s `base_branch` (`main`);
- (optionally) the live head equals a caller-supplied `--expected-head`
  (evidence-freeze pin);
- **every** required check context in `core/policies/merge-policy.json` is
  present and `SUCCESS` - a required context that is missing, pending, failed,
  cancelled, or skipped **blocks** the merge. If a context appears more than
  once in the rollup, **every occurrence** is checked - a duplicate can never
  let one bad occurrence hide behind a good one;
- no non-required check has failed;
- the Knowledge Delta section is present in the **live** PR body (fetched at
  merge time, not the frozen event payload) - unless the policy explicitly
  sets `knowledge_delta_required: false` (the EIF policy always requires it);
- there are **zero unresolved review threads**, paginated across the full
  review-thread list (not just the first 100) - any GraphQL/JSON error
  blocks, never silently counts as zero.

A repo genuinely without CI expresses that via the policy file alone
(`required_check_contexts: []` and `allow_no_checks: true`), never via how
the script is invoked. As of D-14 (2026-07-19), the EIF policy has exactly
one required context (`PR smoke checks (required by policy)`, the routine
PR job) and `allow_no_checks: false`.

The merge itself is pinned to the verified head
(`gh pr merge --match-head-commit <sha>`). The required check contexts live in
**one** machine-readable source, `core/policies/merge-policy.json`, and are
read from there - never hardcoded in the gate or the tests.

## Agent-side deny-direct-merge

In this workspace, agents are additionally denied direct `gh pr merge` by the
RTK PreToolUse hook, which redirects to the controlled merge script. An
adopting project should install an equivalent guard for its own agents (a hook
that denies the direct merge command), plus this document as its visible
policy.

## What is enforced vs advisory (residual risk, stated plainly)

- **Enforced** for anyone who uses the supported path (agents, and humans who
  follow it): the full gate above, pinned to the verified head.
- **Advisory / bypassable**: a human with push access can still run
  `gh pr merge` directly, or push straight to `main`, bypassing the wrapper.
  The wrapper cannot prevent that on its own - only branch protection (paid
  plan) or public visibility + required checks would. This residual bypass is
  documented here rather than hidden behind a "branch is protected" claim it
  cannot back up.

## Machine-readable test evidence

`python scripts/tests/run_all.py --json` emits a machine-readable inventory:
per-suite `passed`/`total`/`duration`, and an aggregate whose check total is
**derived** from the suites' standardized `EIF-RESULT: passed=P total=T`
lines - not hand-summed anywhere. A suite result is trusted only if it emits
exactly one such line and reports `passed <= total`; a missing, duplicated, or
internally inconsistent line is reported as `unknown`, never a silent `0` or a
guess at which line to trust. `--json` is CI's exact-inventory mode: it exits
non-zero if any suite is unknown, exited non-zero, or exited `0` while
reporting `passed != total` (a suite that claims success but disagrees with
its own count is an inventory failure, not a pass). Plain-text mode stays
diagnostic-only - it surfaces the same unknown/mismatched suites for a human
but does not fail the process on them. Under D-14, the routine PR job runs
the faster `scripts/tests/smoke.py` critical-path suite instead; the full
`run_all.py --json` inventory runs in the manual
`.github/workflows/release-check.yml` gate (or locally, at no Actions cost)
and its output is stored in that job's log; `scripts/tests/test_run_all_json.py`
verifies the aggregation and the exact-inventory verdict.

## Proof matrix

`scripts/tests/test_merge_gate.py` drives the pure gate with synthetic PRs
(no live product PRs) and proves: a missing / failed / pending /
cancelled / skipped required context blocks (including when duplicated, with
one bad occurrence among several); a moved head blocks; a wrong base blocks; a
draft blocks; an unresolved thread blocks (including beyond the first
GraphQL page); a missing Knowledge Delta blocks; a clean PR passes; an
unresolvable `--repo` blocks rather than skipping the thread check; a
review-thread query failure blocks; and the second live-gate pass (immediately
before merge) catches a check, a review thread, or the Knowledge Delta body
changing even when the head SHA has not moved. A small set of integration
scenarios drive `eif_merge_pr.main()` end-to-end against a programmable fake
`gh`, including one positive control proving a genuinely clean run reaches
`gh pr merge`.

The private planning packet
`planning/80-execution-packets/PACKET-EIF-REPOSITORY-MERGE-ENFORCEMENT/`
carries the read-only settings-audit snapshot, the applied-diff record (none:
branch protection unavailable), the proof-matrix result, and the residual-risk
statement.
