---
type: playbook
status: validated
scope: framework
confidence: high
created: 2026-07-19
related:
  - execution-packet-execution.md
  - session-preparation.md
  - ../templates/packet-charter.md
---

# Playbook: Execution Packet Planning

<!-- Knowledge source: GENERALIZE of the private EI's
execution-packet-planning.md (45K words covering multi-repo, multi-team
planning conventions). This version keeps the anatomy, the carry-over
gate, and the autonomy-by-ratified-decisions pattern that make autonomous
sequential execution safe - the actual point of a packet. Dropped:
multi-repo registry coordination, customer-engagement-specific packet
types, and cross-team review routing that a single-project-instance v0.1
adopter has no equivalent for. If a project instance's work genuinely
spans multiple repositories, the packet anatomy below still applies -
each in-scope repository just gets its own "in scope" section in the
charter and its own sessions in the roadmap. -->

Turn a piece of work too large for one session into a planned, evidence-
based set of files an agent can execute autonomously, without stopping
for routine questions mid-execution.

## When a packet is needed

Per [`session-preparation.md`](session-preparation.md) Step 1: 2+
sessions, an architectural decision worth an ADR, factual conflicts
between current state and existing docs, or a request for unattended
autonomous execution. Otherwise use
[`templates/task-scope.md`](../templates/task-scope.md) directly instead.

## Anatomy

```text
<packet-root>/
  00-README.md                  (optional - overview + session table for
                                  packets with enough sessions that an
                                  index is worth it)
  01-CHARTER-<NNN>-<slug>.md
  02-FACTS-<NNN>-<slug>.md
  03-DECISIONS-<NNN>-<slug>.md
  04-ROADMAP-<NNN>-<slug>.md
  05-SELF-REVIEW-<NNN>-<slug>.md
  06-START-HERE-<slug>.md
  07-CLOSEOUT-<NNN>-<slug>.md    (template only; filled in the final session)
  sessions/
    SESSION-001-<slug>.md
    SESSION-002-<slug>.md
    ...
```

Templates for every file above: `templates/packet-*.md` and
`templates/session-launch.md`.

## Workflow

1. **Charter** - problem, goal, explicit in/out of scope, boolean
   definition of done. Write this first; it bounds everything after it.
2. **Facts** - verify current state against fresh source/tool state, not
   memory or stale docs. Distinguish `OBSERVED` from `INFERRED`/`ASSUMED`.
   Build the carry-over ledger: every relevant unresolved item from prior
   planning gets an explicit disposition.
3. **Decisions** - for every point in the roadmap-to-be where an
   executing agent would otherwise have to stop and ask "how should this
   work," make the call now and record why. A packet with unresolved
   routine questions in its roadmap is not ready for autonomous
   execution.
4. **Roadmap** - turn the Facts file's gaps into an ordered list of
   sessions, each with concrete steps, runnable verification commands,
   and a boolean exit. Cross-check every Definition of Done item maps to
   a session.
5. **Self-review** - run the checklist in
   [`templates/packet-self-review.md`](../templates/packet-self-review.md)
   before writing the start file. Catch planning gaps now, not in
   session 3.
6. **Start file** - the single canonical prompt an owner hands to an
   executing agent. Everything above is read BY the agent as a result of
   this file, not restated in it.
7. **Session launch files** - one per roadmap session, using
   [`templates/session-launch.md`](../templates/session-launch.md).

## The carry-over gate

Before ratifying the roadmap, confirm every item that should carry
forward from prior planning (a previous packet's deferred work, an open
finding, a decision made elsewhere that touches this scope) has an
explicit disposition in the Facts file's carry-over ledger. An item with
no disposition is the most common way "we already decided this" work
quietly resurfaces two packets later, or gets silently redone.

## Autonomy, not scope-narrowing

The point of the Decisions file is to let an agent execute without
routine stops - not to narrow what the packet actually does. If a
roadmap step turns out to need a judgment call the Decisions file didn't
anticipate, the least-risk default (smallest reversible change) applies,
and the call gets recorded in that session's checkpoint - it should not
silently shrink the session's actual scope.

## Anti-patterns

- A charter whose "in scope" section quietly includes an owner-only
  action (visibility change, release, payment, external communication)
  without naming it.
- A Facts file built from memory/prior chat instead of a fresh check of
  actual source/tool state.
- A roadmap step with no corresponding Definition of Done item, or vice
  versa.
- Treating "packet passed self-review" as permission to stop verifying
  claims during execution - self-review checks the plan, not the result.
