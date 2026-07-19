# Template: Execution Packet Decisions

<!-- Knowledge source: GENERALIZE of the private EI's
decisions-rules-template.md and the D-NNN pattern used across its
execution packets. Kept: ratified-vs-open status, the "why this and not
the alternative" evidence requirement, the never-silently-change-a-
ratified-entry rule. Dropped: nothing - this is what lets a packet run
without stopping for routine questions, which matters just as much for a
single-project instance as a multi-repo one. -->

One file per packet: `<packet-root>/03-DECISIONS-<NNN>-<slug>.md`. Each
entry resolves one uncertainty the roadmap would otherwise have to stop
and ask about mid-session. A packet with no unresolved "how should this
work" questions left in its roadmap is what makes autonomous, sequential
session execution safe.

```yaml
---
packet: <packet-id>
type: decisions
status: ratified
created: YYYY-MM-DD
---
```

## D-001: `<short name>`

**Status: ratified.** `<The decision itself, stated as an instruction an
executing session can follow without further interpretation.>`

**Evidence:** `<Why this option and not an alternative - what was
checked, what it showed.>`

<Repeat one `## D-NNN` entry per decision. Number sequentially; never
reuse a number.>

## Amending a ratified decision

Do not edit a decision already marked `ratified` in place. Add a new
entry that supersedes it, state which decision it replaces and why, and
mark the old entry `superseded by D-NNN` instead of deleting it - the
history of what changed and why is itself worth keeping.

## Open (not yet decided)

<Anything still genuinely undecided when this file is written. A packet
should not enter execution with unresolved items here that its own
roadmap depends on - resolve them first, or scope the dependent session
out.>

*(none currently, or list open items)*

## Least-risk defaults

<For incomplete non-safety details the roadmap doesn't explicitly cover:
state the default an executing session should apply (smallest reversible
change, ask only if a safety/data-loss/external-commitment condition is
actually met) so "what do I do about this small ambiguous thing" doesn't
become a routine stop either.>
