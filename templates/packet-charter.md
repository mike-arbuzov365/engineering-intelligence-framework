# Template: Execution Packet Charter

<!-- Knowledge source: GENERALIZE of the private EI's charter-template.md
and the charter section of execution-packet-planning.md. Kept: problem
statement, explicit in/out of scope, boolean definition-of-done, a small
"does this change something visible" check. Dropped: the private
multi-repo registry/visual-hub update questions - re-add only if a
project instance actually maintains a cross-project registry or visual
map that a packet could make stale. -->

One file per packet: `<packet-root>/01-CHARTER-<NNN>-<slug>.md`. Written
before `02-FACTS`/`03-DECISIONS`/`04-ROADMAP`, and not edited afterward
without recording why (see the Decisions template's evidence rule).

```yaml
---
packet: <packet-id>
type: charter
status: prepared
created: YYYY-MM-DD
---
```

## Problem statement

<What's true today that makes this packet necessary. Evidence-based, not
aspirational - if a claim can't be checked against a file, a test, or a
tool's output, mark it `ASSUMED`, not stated as fact.>

## Goal

<1-3 sentences. The smallest coherent slice that's actually worth
shipping - not every adjacent improvement that comes to mind while
planning.>

## In scope

<What this packet's sessions will change. Group by project/repo if the
packet spans more than one.>

## Out of scope

<Explicitly named adjacent work this packet will NOT do, and why -
"someone reading this later" is the audience, not just the planning
agent. An item with no disposition here is the single most common way
scope silently creeps mid-execution.>

## Definition of done

<Boolean checklist. Every item must be independently verifiable against
source, tests, or tool output - not "looks complete."›

- [ ]
- [ ]

## Does this change something visible?

<If this packet changes a workflow, a public-facing document, a
registry/index another project instance reads, or anything else with
consumers beyond the sessions doing the work - name it here and say
which session updates it. If nothing like that applies, say so
explicitly instead of leaving the question unanswered.>
