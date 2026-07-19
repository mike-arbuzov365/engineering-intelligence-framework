---
type: playbook
status: validated
scope: framework
confidence: high
created: 2026-07-19
related:
  - session-execution.md
  - execution-packet-planning.md
  - ../templates/task-scope.md
---

# Playbook: Session Preparation

<!-- Knowledge source: GENERALIZE of the private EI's
session-preparation.md. Kept: the task-vs-packet routing checkpoint, the
scope questions, the handoff-prompt pattern. Dropped: worktree/parallel-
session bookkeeping (see templates/task-scope.md and
templates/session-launch.md for what's kept vs. dropped and why at the
template level). -->

Decide how much planning a piece of work actually needs, and produce the
artifact that lets execution start from that artifact instead of from
chat history.

## When to use this

- A small, clearly-bounded task (one fix, one question, one small
  change): skip preparation, start directly with
  [`session-execution.md`](session-execution.md) and a
  [`templates/task-scope.md`](../templates/task-scope.md) filled in as you go.
- Work that spans multiple sessions, has real architectural decisions to
  make first, has unresolved factual conflicts, or should run
  autonomously without routine questions: this playbook, producing an
  execution packet.

## Step 1 - Classify the work

Answer before writing anything:

- **Scope**: a single task, or does it need a packet (2+ sessions, an
  ADR-worthy decision, cross-project-instance scope, or a request for
  unattended autonomous execution)?
- **Goal**: 1-3 sentences.

If it's a single task, stop here and fill
[`templates/task-scope.md`](../templates/task-scope.md) directly - that
template is this playbook's entire preparation step for small work.

## Step 2 - If it needs a packet, build the packet anatomy

See [`execution-packet-planning.md`](execution-packet-planning.md) for the
full workflow. Summary: charter, facts, decisions, roadmap, self-review,
then a start file, using the templates under `templates/packet-*.md`.

## Step 3 - Determine session order

If the packet has more than one session, decide their exact dependency
order before writing launch files - a later session's `depends_on` should
name the earlier one explicitly, not rely on "obviously B comes after A."

## Step 4 - Self-review before handoff

Checklist (also in [`templates/packet-self-review.md`](../templates/packet-self-review.md)
for packets; for a single task, re-read the task-scope file's own
sections once before starting):

- [ ] Goal and scope are unambiguous.
- [ ] No-touch zone is explicit.
- [ ] Verification commands are concrete, not "run the tests."
- [ ] Exit criteria are boolean.
- [ ] Sequential dependencies (if any) are explicit.

## Step 5 - Hand off

End preparation with a short prompt pointing at the artifact, not a
restatement of it in the prompt itself:

```text
Run the prepared task/session at:
<path to the task-scope file, or the packet's start file>

Use that file as the source of truth - do not rely on this chat as
hidden context. Work until its exit criteria are met.
```

## Anti-patterns

- The whole plan lives only in a chat prompt, never becomes a file - an
  execution session (possibly in a fresh context) can't see it.
- A worktree/branch convention left as "figure it out" - state it
  explicitly if the project instance uses one.
- Verification stated as "tests pass" instead of the actual command.
