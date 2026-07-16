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
merge path. Immediately before merging it re-verifies (see the gate in
`eif_merge_pr.evaluate_gate`, unit-tested in
`scripts/tests/test_merge_gate.py`):

- the PR is OPEN, not a draft, and its review decision is not
  `CHANGES_REQUESTED`;
- the base branch equals `merge-policy.json`'s `base_branch` (`main`);
- (optionally) the live head equals a caller-supplied `--expected-head`
  (evidence-freeze pin);
- **every** required check context in `core/policies/merge-policy.json` is
  present and `SUCCESS` - a required context that is missing, pending, failed,
  cancelled, or skipped **blocks** the merge;
- no non-required check has failed;
- the Knowledge Delta section is present in the **live** PR body (fetched at
  merge time, not the frozen event payload);
- there are **zero unresolved review threads**.

The merge itself is pinned to the verified head
(`gh pr merge --match-head-commit <sha>`), and the head is re-read one last
time right before the merge, so a late push aborts instead of merging
unreviewed code.

The required check contexts live in **one** machine-readable source,
`core/policies/merge-policy.json`, and are read from there - never hardcoded
in the gate or the tests.

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
lines - not hand-summed anywhere. A suite that does not emit the line is
reported as `unknown`, never a silent `0`. CI runs `run_all.py --json` and its
output is stored in the job log; `scripts/tests/test_run_all_json.py` verifies
the aggregation.

## Proof matrix

`scripts/tests/test_merge_gate.py` drives the pure gate with synthetic PRs
(no live product PRs) and proves: a missing / failed / pending /
cancelled / skipped required context blocks; a moved head blocks; a wrong base
blocks; a draft blocks; an unresolved thread blocks; a missing Knowledge Delta
blocks; and a clean PR passes.

The private planning packet
`planning/80-execution-packets/PACKET-EIF-REPOSITORY-MERGE-ENFORCEMENT/`
carries the read-only settings-audit snapshot, the applied-diff record (none:
branch protection unavailable), the proof-matrix result, and the residual-risk
statement.
