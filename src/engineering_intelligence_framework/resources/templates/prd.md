# Template: Product Requirements Document

Use with
[`playbooks/product-requirements-planning.md`](../playbooks/product-requirements-planning.md).
Default project path: `planning/20-prds/PRD-NNN-<slug>.md`.

```yaml
---
id: PRD-NNN
type: prd
status: draft
idea: IDEA-NNN
title: "<short title>"
created: YYYY-MM-DD
decision_owner: "<role or person>"
approval_source:
---
```

# PRD-NNN: `<short title>`

## Goal

<The user or business outcome this PRD must produce.>

## Provenance and evidence

- Approved idea:
- Idea approval source:
- Source of record:
- Verified facts:
- Assumptions:
- Related decisions and knowledge:

## Users

- Primary user:
- Other affected users:

## User flow

<Describe the primary path and relevant failure, recovery, permission and
empty states.>

## Scope

### In scope

-

### Out of scope

-

## Functional requirements

### FR-001: `<requirement name>`

- Required behavior:
- Source:
- Acceptance criteria:
  - [ ]
  - [ ]

## Non-functional requirements

- Security:
- Privacy:
- Reliability:
- Performance:
- Observability:
- Accessibility:
- Compatibility:

Use `not applicable - <reason>` for a category that does not apply.

## Success evidence

- Outcome:
- Evaluator:
- Failure criteria:

## Data and evaluation

<For data or AI behavior, state data sources, allowed use, quality gates,
evaluation set, failure criteria and prohibited use. Otherwise write
`not applicable - <reason>`.>

## Dependencies

-

## Risks

-

## Rollout, migration and operability

- Rollout:
- Migration and backward compatibility:
- Monitoring:
- Rollback:
- Support owner:

## Traceability

| Requirement | Source | Acceptance check | Owner |
|---|---|---|---|
| FR-001 | | | |

## Open questions

- [ ]

## Decision and next route

- Decision: `approve | revise | defer | reject | pending`
- Decision owner:
- Approval source:
- Next route: `plan-execution-packet | task-scope | deferred | rejected`
- Rationale:
