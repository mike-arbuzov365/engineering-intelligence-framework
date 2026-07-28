# Template: Idea

Use with [`playbooks/idea-planning.md`](../playbooks/idea-planning.md).
Default project path:
`planning/10-ideas/IDEA-NNN-<slug>.md`.

```yaml
---
id: IDEA-NNN
type: idea
status: draft
title: "<short title>"
created: YYYY-MM-DD
source: "<source type>"
decision_owner: "<role or person>"
approval_source:
route: undecided
---
```

# IDEA-NNN: `<short title>`

## Problem

<What real problem exists, for whom, and what evidence shows it?>

## Source and evidence

- Source of record:
- `OBSERVED`:
- `INFERRED`:
- `ASSUMED`:
- `PROPOSED`:
- Related knowledge and rejected approaches:

## Target user

<Who experiences the problem or receives the value?>

## Current state

<What happens today without this idea?>

## Desired outcome

<What should become observably better, independent from implementation?>

## Proposed direction

<The smallest direction worth validating. Keep unapproved implementation
choices out of this section.>

## Value and why now

<Why this matters and why the timing is justified?>

## Minimum useful scope

<The smallest coherent slice that produces real value or learning.>

## Out of scope

<Adjacent work explicitly excluded from this idea.>

## Risks and dependencies

- Product:
- Technical:
- Scope:
- Privacy and security:
- Dependencies:

## Validation plan

- Critical assumption:
- Evidence that supports the idea:
- Evidence that revises or rejects it:
- Evaluator or decision method:

## Open questions

- [ ]

## Decision and route

- Decision: `approve | revise | defer | reject | pending`
- Decision owner:
- Approval source:
- Next route: `plan-prd | plan-execution-packet | task-scope | deferred | rejected`
- Rationale:
