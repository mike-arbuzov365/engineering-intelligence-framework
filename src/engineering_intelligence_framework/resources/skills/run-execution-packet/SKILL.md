---
name: run-execution-packet
description: >
  Execute an already-planned execution packet's sessions in strict
  sequential order, as one agent, from its start file through closeout.
  Use when handed a prepared packet to run - not for planning one.
---

# Skill: Run Execution Packet

<!-- Knowledge source: GENERALIZE of the private EI's
run-execution-packet SKILL.md. Thin pointer to
playbooks/execution-packet-execution.md - one canonical source per D-007.
-->

Full workflow: [`playbooks/execution-packet-execution.md`](../../playbooks/execution-packet-execution.md).

## Process

1. Read the packet's start file (`06-START-HERE-*.md` or equivalent) -
   not a paraphrase, not prior chat history.
2. For each session, in the roadmap's exact order:
   - Read its launch file.
   - Execute against its declared scope, no-touch zone, and verification
     commands (see
     [`playbooks/session-execution.md`](../../playbooks/session-execution.md)).
   - Confirm its exit criteria before starting the next session.
   - Keep its checkpoint - this is what makes an interrupted session
     resumable and the whole packet independently reviewable.
3. Respect any resource/budget guard from the packet's decisions file
   (e.g. avoiding hosted/paid CI) for every session, not just the one
   that states it.
4. One agent, sequential, no delegation/spawn/team tools.
5. On the final session: run
   [`playbooks/session-closeout.md`](../../playbooks/session-closeout.md),
   then fill `templates/packet-closeout.md` from the actual accumulated
   session results.

## If blocked

Record which session is in progress and why it's blocked. Use an honest
closeout status (`in-progress`,
`implementation-complete-integration-deferred`, or `blocked`) rather than
marking the packet complete with an unmet criterion.

## Output

- Each session's checkpoint, committed per the packet's convention.
- The filled packet closeout.
- A final report: what was done, what verification ran and its result,
  what's deferred and why.
