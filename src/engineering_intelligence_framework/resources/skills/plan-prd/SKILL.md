---
name: plan-prd
description: >
  Turn an approved idea into an evidence-based Product Requirements
  Document with users, flows, scope, observable functional acceptance
  criteria, non-functional requirements, traceability, rollout and
  approval. Use after idea approval and before non-trivial implementation
  planning.
---

# Skill: Plan PRD

Follow the canonical workflow in
[`playbooks/product-requirements-planning.md`](../../playbooks/product-requirements-planning.md).
Use [`templates/prd.md`](../../templates/prd.md) unless the project has an
approved local template.

## Process

1. Verify the source idea and its approval.
2. Read current source and retrieve relevant project knowledge.
3. Create or update one durable PRD artifact.
4. Give every functional requirement observable acceptance criteria.
5. Keep requirements separate from unapproved implementation decisions.
6. Keep the PRD in draft until its own approval is explicit.
7. Route approved non-trivial work to an execution packet and a small
   bounded change to a task scope.

If idea approval is absent, organize known requirements only as a draft
and record the approval gap. Do not route it into execution.

## Output

A reviewable PRD artifact, normally
`planning/20-prds/PRD-NNN-<slug>.md`, plus a short statement of its
status, unresolved requirements and next route.
