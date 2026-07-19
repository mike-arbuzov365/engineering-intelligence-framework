# Template: Execution Packet Facts

<!-- Knowledge source: GENERALIZE of the private EI's facts-template.md.
Kept: the evidence-boundary statement, the OBSERVED/INFERRED distinction,
the carry-over ledger pattern for reconciling this packet against prior
unfinished work. Dropped: nothing structural - this template's whole
point (verified state over assumed state) doesn't shrink for a
single-project instance. -->

One file per packet: `<packet-root>/02-FACTS-<NNN>-<slug>.md`. This file,
not the charter or chat memory, is the source of truth the roadmap and
every session read from - see the framework's authority model
([`core/ontology/authority-model.md`](../core/ontology/authority-model.md)):
a normative source (what the charter says should happen) and an empirical
source (what this file verified actually happened) can disagree, and that
disagreement is itself worth recording, not silently resolved by picking
one.

```yaml
---
packet: <packet-id>
type: facts
status: validated
evidence_cutoff: YYYY-MM-DD
---
```

## Evidence boundary

<What was actually checked (which files, which fresh `git fetch`/`gh`
state, which test run) and when. A fact dated before this cutoff that
hasn't been re-verified should be treated as potentially stale, not
current.>

## Current state

<Verified, per relevant area/repo. Mark each row `OBSERVED` (you checked
it directly), `INFERRED` (a reasonable conclusion from observed facts), or
`ASSUMED` (not verified - name what verification is missing).>

| Area | State | Evidence |
|---|---|---|
| | | |

## Gaps

<What the goal requires that current state does not yet provide. This is
the actual work list the roadmap turns into sessions.>

## Carry-over ledger

<Every relevant unresolved item from prior planning (a previous packet's
deferred item, an open finding, a prior decision that touches this scope)
gets an explicit disposition here - closed / in-scope / re-deferred -
with where it's addressed. An item silently dropped from a carry-over
ledger is the most common way "we already decided this" work quietly
resurfaces two packets later.>

| Prior item | Disposition | Destination |
|---|---|---|
| | | |
