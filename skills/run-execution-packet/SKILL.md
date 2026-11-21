---
name: run-execution-packet
description: >
  Execute an already-planned packet's sessions in strict sequential order
  from its start file through closeout, including an explicit orchestrated mode.
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
   - For iterative work, run the session's bounded evidence loop. Do not exceed
     its iteration or remote-run budget, and do not treat a completion phrase
     as proof.
3. Respect any resource/budget guard from the packet's decisions file
   (e.g. avoiding hosted/paid CI) for every session, not just the one
   that states it.
4. One accountable agent, sessions sequential. In orchestrated mode, use
   the launch and revision-bound review before acting on admission. Bounded
   delegates return their output and evidence to the accountable agent.
   Never start a later session while an earlier one awaits acceptance.
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

Maintain session-launch progress using `prepared`, `in_progress`, `completed`,
`blocked`, or `deferred`; only `completed` satisfies `depends_on`. Historical
status values are `legacy` to progress readers.
