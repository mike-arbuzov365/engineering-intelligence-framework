# Template: Execution Packet Self-Review

<!-- Knowledge source: GENERALIZE of the private EI's pre-execution
self-review gate used across its execution packets (no single dedicated
private template file - the pattern was consistent across packets, this
is its first standalone template). Kept: the pre-execution gate concept
itself (a packet should pass its own review before an agent starts
autonomous execution against it) and the "what would make this packet
stop for a routine question" check. -->

One file per packet: `<packet-root>/05-SELF-REVIEW-<NNN>-<slug>.md`.
Written after `01-CHARTER` through `04-ROADMAP`, before `06-START-HERE`.
The point is to catch planning gaps - missing decisions, silently dropped
carry-over items, an ambiguous scope boundary - before an agent starts
executing sessions, not partway through session 3.

```yaml
---
packet: <packet-id>
type: self-review
status: passed
created: YYYY-MM-DD
---
```

## Anatomy

- [ ] Charter states problem, goal, in/out of scope, and boolean DoD.
- [ ] Facts distinguish `OBSERVED` from `INFERRED`/`ASSUMED` and give an
      evidence cutoff.
- [ ] Every DoD item maps to at least one roadmap session.
- [ ] Nothing that changes public visibility, external commitments, or
      paid/irreversible actions is hidden inside "in scope" without being
      named explicitly.

## Decisions

- [ ] Every roadmap step that could otherwise require a routine
      mid-session question has a corresponding ratified decision or a
      stated least-risk default.
- [ ] No decision both claims `ratified` status and lacks evidence for
      why that option was chosen over an alternative.

## Carry-over gate

- [ ] Every item in the Facts file's carry-over ledger has an explicit
      disposition (closed / in-scope / re-deferred) - none silently
      dropped.

## Safety and scope

- [ ] Owner-only actions (visibility changes, releases, payments,
      external communication, destructive/irreversible operations) are
      named as explicitly out of scope, not implicitly excluded.
- [ ] User-owned uncommitted work or existing branches this packet
      touches are named, with an explicit "read-only evidence, not a
      base to reset" instruction if applicable.

## Verdict

**`PASS` / `PASS WITH NOTES` / `FAIL`.** `<One sentence on what would
still make this packet legitimately stop mid-execution - safety/data-loss
risk, an owner-only action becoming necessary, a resource constraint
(e.g. hosted CI quota) not clearing, or a genuinely unresolvable
ambiguity. Everything else should already be resolved above.>`
