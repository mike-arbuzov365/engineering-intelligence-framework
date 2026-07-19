---
type: playbook
status: validated
scope: framework
confidence: high
created: 2026-07-19
related:
  - execution-packet-planning.md
  - execution-packet-review.md
  - session-execution.md
---

# Playbook: Execution Packet Execution

<!-- Knowledge source: GENERALIZE of the private EI's
execution-packet-execution.md. Kept: strict sequential single-agent
execution, per-session checkpointing, the never-silently-narrow-scope
rule, the resource-budget-guard pattern (e.g. avoid triggering paid/hosted
CI mid-execution). Dropped: parallel-session/multi-worktree coordination -
this framework's default is one agent executing one packet's sessions in
strict order; re-add coordination machinery only if a project instance
actually needs concurrent sessions on the same packet. -->

Execute an already-planned packet's sessions in order, as one agent, from
its start file through to closeout.

## Preconditions

- The packet passed self-review
  ([`templates/packet-self-review.md`](../templates/packet-self-review.md)).
- Its start file exists
  ([`templates/packet-start.md`](../templates/packet-start.md)).

## Step 1 - Enter via the start file

Read the packet's `06-START-HERE-*.md`, not a paraphrase of it. It states
the read order, the source-of-truth hierarchy, and the stop conditions -
do not substitute chat memory for any of these.

## Step 2 - Execute sessions in roadmap order

For each session, in the exact order the roadmap states:

1. Read that session's launch file
   ([`templates/session-launch.md`](../templates/session-launch.md)).
2. Run [`session-execution.md`](session-execution.md) against it.
3. Confirm its exit criteria before moving to the next session - a
   session with an unmet exit criterion blocks every session that
   `depends_on` it.
4. Keep the session's checkpoint per its own `session_context` path. This
   is what lets execution resume correctly if the session is interrupted,
   and what closeout later verifies against.

Never run two sessions out of the roadmap's order, and never start a
later session to "make progress" while an earlier one is still failing
its exit criteria.

## Step 3 - Respect resource/budget guards

If the packet's Decisions file states a resource guard (a common one:
avoid triggering hosted/paid CI runs until some condition clears), that
guard applies to every session, not just the one that mentions it. When
in doubt about whether an action would trigger the guarded resource,
prefer the local/no-cost equivalent and record the substitution.

## Step 4 - One active agent, no delegation

Sessions execute sequentially in one agent. Do not spawn subagents,
delegate sessions to parallel workers, or use team/multi-agent tooling to
"speed up" a sequential packet - the roadmap's ordering and the
checkpoint trail are what make the result auditable
(see [`execution-packet-review.md`](execution-packet-review.md)); parallel,
undocumented execution breaks that trail.

## Step 5 - Close out

Once every session's exit criteria are met: run
[`session-closeout.md`](session-closeout.md) for the final session, then
fill [`templates/packet-closeout.md`](../templates/packet-closeout.md)
from the accumulated, actually-recorded session results - not from
memory of what should have happened.

## If execution must stop before the packet is done

Record which session is in progress, its own pause state (per
[`session-execution.md`](session-execution.md)'s pause guidance), and
which sessions remain. The packet's `status` should reflect this
honestly (`in-progress`, or
`implementation-complete-integration-deferred` if only an owner-gated or
resource-blocked final step remains) rather than being marked complete
prematurely.

## Anti-patterns

- Skipping a session's checkpoint "to save time" - it's what makes an
  independent review (or a resumed, interrupted session) possible.
- Treating a resource/budget guard as advisory once execution starts.
- Declaring the packet done while a Definition of Done item is actually
  unmet, deferred, or owner-gated - use the honest closeout status
  instead.
