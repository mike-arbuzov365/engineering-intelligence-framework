---
name: review-execution-packet
description: >
  Independently audit a packet claimed as executed or closed - verify
  the claimed integration, evidence, and closeout against fresh
  repository/tool state rather than trusting the closeout narrative.
  Use for a post-hoc audit, not while executing the packet yourself.
---

# Skill: Review Execution Packet

<!-- Knowledge source: GENERALIZE of the private EI's
review-execution-packet SKILL.md. Thin pointer to
playbooks/execution-packet-review.md - one canonical source per D-007. -->

Full workflow: [`playbooks/execution-packet-review.md`](../../playbooks/execution-packet-review.md).

## Process

1. **Fetch fresh state first, always** (`git fetch --all --prune`).
   Never reason about merge/integration state from a local ref alone.
2. Build an independent plan-vs-done matrix from the roadmap and session
   launch files - one row per exit criterion, with the actual evidence
   and result, not the closeout's own claim.
3. Verify every "merged"/"done" line against fetched state and the
   relevant hosted-platform query (e.g. `gh pr view`) - not a
   commit-subject grep (squash/rebase merges don't preserve it).
4. If the packet spans more than one project/repository, confirm a
   shared contract is present on the fetched state of *every* side.
5. Check that the closeout separates implementation-done from
   owner-gated/pending, and that any status artifact reflects verified
   state.
6. Run a normal code-quality review against the correct diff range.

## Output

```markdown
Verdict: closed-correctly | gaps-found | false-closeout

Findings (one per issue, with evidence and severity):
- [HIGH|MEDIUM|LOW] <finding> - <evidence>

Fix report: <concrete next steps, referencing
playbooks/execution-packet-execution.md for how to close correctly>
```
