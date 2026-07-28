---
type: playbook
status: validated
scope: framework
confidence: high
created: 2026-07-28
related:
  - idea-planning.md
  - execution-packet-planning.md
  - ../templates/prd.md
---

# Playbook: Product Requirements Planning

<!-- Knowledge source: GENERALIZE of the private production instance's
plan-prd workflow and the first public-project dogfood adoption. Kept:
approved-idea gate, evidence and assumption separation, observable
acceptance criteria, non-functional requirements, traceability and
rollout/rollback. Dropped: private product taxonomy, customer identities
and legacy epic/story/task hierarchy. -->

Turn an approved idea into a reviewable Product Requirements Document
(PRD). A PRD defines required outcomes and constraints. It is not an
implementation task list, architecture decision or evidence that the
product decision has been approved.

## Inputs

- The idea artifact and its durable approval source.
- Current product behavior and constraints verified from source or tools.
- Relevant project knowledge, decisions, incidents and policies.
- The project instance's local PRD template, if it intentionally
  specializes the framework template.

Use [`templates/prd.md`](../templates/prd.md) when the project has no
approved local equivalent. The default location is
`planning/20-prds/PRD-NNN-<slug>.md`.

## Approval boundary

Verify that the source idea is approved before treating the PRD as ready
for implementation planning. If approval is absent or ambiguous, a draft
PRD may organize known requirements, but it must keep `status: draft`,
record the missing approval, and must not route to execution.

## Workflow

1. **Verify provenance.** Link the idea, its approval source and every
   important product or policy source. Separate verified facts,
   assumptions and open questions.
2. **Define goal and non-goals.** State the user or business outcome and
   the explicit exclusions that protect it from scope drift.
3. **Describe users and flows.** Cover the primary path plus relevant
   failure, recovery, permission and empty-state behavior.
4. **Write functional requirements.** Give each requirement a stable ID,
   a user-observable behavior and one or more acceptance checks. Avoid
   encoding an implementation unless the implementation itself is an
   approved constraint.
5. **Write non-functional requirements.** Consider security, privacy,
   reliability, performance, observability, accessibility and
   compatibility. Mark a category `not applicable` with a reason instead
   of silently omitting it.
6. **Define success evidence.** Name outcomes and evaluators that can
   distinguish success from an artifact merely existing.
7. **Cover data and evaluation where relevant.** State sources, allowed
   use, quality gates, evaluation set, failure criteria and prohibited
   use. Explicitly mark the section not applicable otherwise.
8. **Plan operability.** Record dependencies, rollout, migration,
   monitoring, support ownership and rollback.
9. **Build traceability.** Map every requirement to its source, acceptance
   check and owner. Unmapped requirements remain draft.
10. **Record approval and route.** Keep `status: draft` until the decision
    owner and approval source are durable. After approval, route
    non-trivial implementation to
    [`execution-packet-planning.md`](execution-packet-planning.md); use a
    task scope for one small session.

## Quality gate

A PRD is ready for implementation planning only when:

- its idea and idea approval are verifiable;
- goals, non-goals, users and flows agree;
- every functional requirement has observable acceptance checks;
- applicable quality and trust boundaries are explicit;
- assumptions and open questions cannot silently change scope;
- rollout, rollback and ownership are named where relevant;
- traceability has no unexplained requirement;
- PRD approval and the next route are recorded.

This gate validates requirements completeness and traceability. It does not
select architecture or prove delivery feasibility.
