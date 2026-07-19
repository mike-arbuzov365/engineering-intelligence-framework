---
type: playbook
status: validated
scope: framework
confidence: high
created: 2026-07-19
related:
  - execution-packet-execution.md
---

# Playbook: Execution Packet Review

<!-- Knowledge source: GENERALIZE of the private EI's
execution-packet-review.md. Kept essentially unchanged: the git-hygiene
preflight, the never-trust-a-local-ref rule, gh/tool-state as authority
over grep-based inference, and the existence/build/merge-is-not-
behavioral-evidence distinction - these are the actual hard-won lessons
this playbook exists to encode, and they don't shrink for a single-project
instance. Dropped: references to the specific incidents (different
projects/teams) that originally motivated each rule, replaced with the
generic failure mode each incident demonstrated. -->

Independently audit a packet claimed as executed or closed: was what's
claimed actually done, is the integration real, is the closeout truthful,
and is there any split-brain between what one part of the work assumes
and what another part actually provides. Pairs with
[`execution-packet-execution.md`](execution-packet-execution.md) - this
playbook checks the result; that one produces it.

## Step 0 - Fetch fresh state first (mandatory, first step)

Before drawing any conclusion about merge/integration state:

```text
git fetch --all --prune
```

Hard rules for this step, because violating them is the single most
common cause of a false review:

- **Never** reason about merge/closeout state from a local branch or
  `HEAD` alone - it can be many commits behind the actual integration
  branch.
- Always compare against the fetched remote integration branch, and name
  exactly which ref you audited.
- **Do not** conclude "this was never merged" from `git log | grep`
  alone - a squash or rebase merge does not preserve a literal PR-number
  string in the commit subject. A hosted-platform query (e.g. `gh pr
  view <n>`) is the authority, not a grep over local history.

Any conclusion drawn before this fetch is invalid and must be redone.

## Review steps

1. **Ground truth.** Fetch, then record the exact tip of the integration
   branch you're auditing against - name the ref explicitly.
2. **Plan vs. done.** Read the roadmap and each session's launch file.
   Build an independent matrix per exit criterion: the observable
   behavior claimed, the evidence offered, the command/test that would
   verify it, the actual result, and whether it's genuinely owner-gated.
   Existence, a passing build, or a merge on its own does not close a
   criterion that claims a specific behavior - only a test that actually
   exercises that behavior does.
3. **Evidence verification**, for every "done"/"merged" line in the
   closeout:
   ```text
   git merge-base --is-ancestor <claimed-sha> <integration-branch>
   gh pr view <n> --json number,state,mergeCommit,baseRefName
   ```
   Confirm state is the expected merged/closed state and the base branch
   matches. Anything that fails this check is a finding: false or
   unverifiable evidence.
4. **Acceptance evidence verification.** Re-run or independently check
   each exit criterion's actual command. An environment-gated test with
   no environment available should show as skipped, not passed.
   `owner-gated` is only legitimate for secrets/production/destructive/
   external-commitment steps - not for implementation logic that could
   have been verified locally.
5. **Cross-scope consistency**, if the packet spans more than one
   project/repository: confirm a contract both sides depend on (an
   endpoint and its caller, a shared schema and its consumer) is actually
   present on the fetched integration branch of *every* side, not just
   the side that was reviewed first. A mismatch here is a high-severity
   finding.
6. **Closeout truthfulness.** The closeout should separate
   implementation-done from owner-gated/pending, not blend them into one
   "done" claim, and any dashboard or status artifact should reflect
   verified state, not the planned/expected state.
7. **Code-quality pass.** Run a normal code review against the *correct*
   diff range (the merged range, or the integration branch against the
   packet's final head) - not a stranded feature branch treated as if it
   were the final state.

## Severity and output

- **Verdict**: `closed-correctly` / `gaps-found` / `false-closeout`.
- **Findings**: one issue per finding, with the actual command output as
  evidence and a confidence level. High severity: false "merged"
  evidence, cross-scope split-brain, an owner-gated step marked done
  without owner action. Medium: a stale status artifact, inconsistent
  statuses. Low: cosmetic.
- **Fix report**: a concrete, actionable list - correct integration order,
  rewrite the closeout to match reality, update any status artifact -
  referencing [`execution-packet-execution.md`](execution-packet-execution.md)
  for how to close it out correctly.

## Anti-patterns (of the reviewer)

- Auditing local branch state without fetching first - invalidates every
  conclusion that follows.
- Trusting closeout prose without independently checking each claimed
  PR/SHA.
- Concluding "this PR doesn't exist" from a commit-subject grep instead
  of a hosted-platform query.
- Reviewing a stranded feature branch as if it were the integrated state.
- Strong claims ("fabricated," "nothing was done") without the tool-query
  evidence to back them.
- Accepting a merged PR or a green build as proof of every exit
  criterion, rather than of the specific thing it actually tested.
- Accepting an environment-gated test that returned early with no
  environment as passing integration evidence.
- Accepting a final claim without verifying it yourself against
  source/tests/integration state.
