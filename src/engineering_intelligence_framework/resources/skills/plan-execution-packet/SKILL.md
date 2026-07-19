---
name: plan-execution-packet
description: >
  Plan an execution packet for work too large for one session - an idea,
  a PRD, an epic, a large refactor, review findings, or cross-project
  alignment. Produces charter/facts/decisions/roadmap/self-review/start
  files ready for autonomous execution. Does not implement product code.
---

# Skill: Plan Execution Packet

<!-- Knowledge source: GENERALIZE of the private EI's
plan-execution-packet SKILL.md. Kept as a thin pointer to
playbooks/execution-packet-planning.md (the canonical, detailed source)
plus the skill-specific stop conditions - per this framework's D-007,
one canonical source per workflow, generated adapter loaders only. -->

Use when work can't be handed to an execution agent as one ad-hoc
session: an idea/PRD/epic, a large piece of work, findings from review or
testing, or cross-project-instance scope.

Full workflow: [`playbooks/execution-packet-planning.md`](../../playbooks/execution-packet-planning.md).
Templates: `templates/packet-*.md` and `templates/session-launch.md`.

## Process

1. Classify the work and confirm it actually needs a packet (see
   [`playbooks/session-preparation.md`](../../playbooks/session-preparation.md)
   Step 1) - otherwise use
   [`templates/task-scope.md`](../../templates/task-scope.md) instead.
2. Search `knowledge/` for prior related work, incidents, or rejected
   approaches (`scripts/eif_search_knowledge.py`). Record what was found.
3. Write the charter (problem, goal, explicit in/out of scope, boolean
   DoD) before anything else.
4. Write the facts file: verify current state against fresh source/tool
   state, not memory. Build the carry-over ledger - every relevant item
   from prior planning gets an explicit disposition.
5. Write the decisions file: resolve every point where an executing
   agent would otherwise stop for a routine question.
6. Write the roadmap: one session per roadmap entry, concrete steps,
   runnable verification, boolean exit. Cross-check every DoD item maps
   to a session.
7. Run the self-review checklist
   (`templates/packet-self-review.md`) before writing the start file.
8. Write the start file (the single canonical autonomous-execution
   prompt) and one launch file per session.
9. Give the user a short prompt pointing at the start file.

## Stop conditions for planning

Stop and ask only if:

- there's no access to the repository or critical source material;
- the request asks for implementation but the actual situation is
  decision-readiness (unratified architectural choices) - in that case,
  plan the decisions, keep product code read-only, and say so;
- a decision would change scope or an external commitment without
  ratification;
- there's a data-loss, security, or auth risk;
- the current branch/worktree has unexplained unrelated changes that
  affect planning.

Do not stop planning over naming, folder layout, a missing non-critical
tool, or incomplete non-critical detail - apply the least-risk default,
record it in the decisions file, and continue.

## Output

- A complete packet under `planning/` (or this project instance's
  equivalent execution-packet location).
- A short summary: packet scope, sessions, decisions made, and any
  genuine stop conditions found.
- A short prompt for the execution agent, referencing the start file.
