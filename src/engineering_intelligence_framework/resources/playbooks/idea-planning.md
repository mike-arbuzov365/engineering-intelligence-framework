---
type: playbook
status: validated
scope: framework
confidence: high
created: 2026-07-28
related:
  - product-requirements-planning.md
  - execution-packet-planning.md
  - ../templates/idea.md
---

# Playbook: Idea Planning

<!-- Knowledge source: GENERALIZE of the private production instance's
plan-idea workflow and the first public-project dogfood adoption. Kept:
evidence labels, source of record, problem/value/minimum-scope framing,
explicit approval and routing. Dropped: private folder names, project
profiles and customer-specific approval mechanics. -->

Turn a raw request, observation or opportunity into a reviewable idea
artifact. This step makes the problem and value clear without pretending
the implementation or detailed requirements are already decided.

## Inputs

- The raw idea and its source of record.
- Current repository and product state that can be checked directly.
- Relevant retrieved knowledge, earlier decisions and rejected approaches.
- The project instance's local idea template, if it intentionally
  specializes the framework template.

Use [`templates/idea.md`](../templates/idea.md) when the project has no
approved local equivalent. The default location is
`planning/10-ideas/IDEA-NNN-<slug>.md`; a project may configure another
durable planning path.

## Workflow

1. **Record provenance.** Name the source of record and separate
   `OBSERVED`, `INFERRED`, `ASSUMED` and `PROPOSED` statements. A chat
   summary is not a verified product fact.
2. **Search before reframing.** Retrieve related knowledge, decisions,
   incidents and rejected approaches. Record what was found or that the
   search returned no eligible result.
3. **State the problem.** Identify the affected user, current behavior,
   concrete friction and the consequence of leaving it unchanged.
4. **State the desired outcome.** Describe what becomes observably better.
   Keep this independent from a preferred technical implementation.
5. **Bound the idea.** Define the smallest useful scope, explicit
   exclusions, dependencies, risks and the assumption most likely to
   invalidate the idea.
6. **Plan validation.** Name the evidence that would support, revise or
   reject the idea. Avoid success criteria that only say an artifact was
   written or code was merged.
7. **Resolve open questions proportionally.** Continue with marked
   assumptions when they are safe and reversible. Ask before writing only
   when different answers materially change the problem, external
   commitment, privacy boundary or owner decision.
8. **Record approval.** Keep `status: draft` until the decision owner and
   approval source are explicit. An agent may recommend a route but may not
   invent approval.
9. **Choose one route.**
   - `plan-prd`: the idea is approved but user, behavior or acceptance
     requirements still need definition.
   - `plan-execution-packet`: the approved work is already sufficiently
     bounded and needs two or more sessions.
   - `task-scope`: the approved work is one small, bounded session.
   - `deferred` or `rejected`: preserve the reason and evidence.

## Quality gate

An idea is ready to leave draft only when:

- the problem is stated without relying on the proposed solution;
- the user and current state are explicit;
- facts and assumptions are distinguishable;
- minimum useful scope and out-of-scope items are both present;
- validation evidence and the decision owner are named;
- the approval source and next route are durable and reviewable.

This gate validates planning completeness. It does not prove market value,
technical feasibility or delivery success.
