---
type: playbook
status: validated
scope: framework
confidence: high
created: 2026-07-19
related:
  - session-execution.md
  - ../templates/session-closeout.md
  - ../templates/packet-closeout.md
---

# Playbook: Session Closeout

<!-- Knowledge source: GENERALIZE of the private EI's session-closeout.md
(11 steps). The step-by-step checklist itself already lives in
templates/session-closeout.md (built in Session 002 of this ported set's
predecessor work) - this playbook is deliberately thin and adds only the
surrounding context that template doesn't cover, so the checklist has one
canonical source (D-007) instead of drifting between a playbook copy and
a template copy. -->

Run at the end of any session (task or packet session) that changed
code, decisions, or documentation. The actual checklist is
[`templates/session-closeout.md`](../templates/session-closeout.md); this
playbook covers when to run it and how it connects to what comes before
and after.

## When to run this

- At the end of every task-scope-based session that touched code,
  decisions, or docs.
- At the end of every packet session - in addition to (not instead of)
  that packet's own `07-CLOSEOUT` file, which is filled once, in the
  final session, from the accumulated per-session results.

## How it connects

- **Before this**: [`session-execution.md`](session-execution.md) - do
  not start closeout with an exit criterion still failing; go back to
  execution instead.
- **The checklist**: [`templates/session-closeout.md`](../templates/session-closeout.md).
- **If this is a packet's final session**: also fill
  [`templates/packet-closeout.md`](../templates/packet-closeout.md) using
  this and every prior session's recorded results - not re-derived from
  memory.
- **After this**: if new durable knowledge surfaced, apply
  [`knowledge-ingest.md`](knowledge-ingest.md); before proposing anything
  for promotion beyond this project instance, apply
  [`knowledge-lint.md`](knowledge-lint.md).

## Anti-patterns beyond the template's own list

- Treating a packet's final session as "just another session closeout"
  and skipping `07-CLOSEOUT` entirely.
- Filling `07-CLOSEOUT` from memory of what earlier sessions did instead
  of from their actual recorded checkpoints/results.
- Marking a packet `completed` when an owner-gated action (visibility,
  release, external communication) is still outstanding - use
  `implementation-complete-integration-deferred` or `blocked` instead,
  per [`templates/packet-closeout.md`](../templates/packet-closeout.md).
