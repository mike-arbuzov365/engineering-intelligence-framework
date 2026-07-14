---
type: ontology
status: validated
scope: framework
created: 2026-07-15
review_after: 2026-10-15
---

# Authority model

<!-- Revised 2026-07-15: replaced a single linear "who wins" hierarchy with
independent axes. The linear version conflated normative claims ("what
should happen") with empirical claims ("what actually happens"), which
produces a wrong answer whenever a normative source is stale, aspirational,
or simply wrong about implemented behavior. See "Why not one hierarchy"
below. -->

A source of truth is only authoritative *for the kind of question it can
actually answer*. This model has four independent axes instead of one
ranked list; use the axis that matches the question you're asking, not the
one that happens to rank highest overall.

## Why not one linear hierarchy

"Vendor docs always outrank logs" is true when the question is *"what is
this API contractually supposed to do?"* and false when the question is
*"what does this specific deployment actually do right now?"* - a
reproducible test or an audited runtime trace answers the second question
better than a doc ever can, including a doc that is simply out of date, or
describes a feature that was never actually implemented as specified.

Collapsing both questions into one ranked list forces a wrong default: it
either discards real, reproducible evidence because a doc theoretically
outranks it, or discards the documented contract because someone saw
different behavior once. Neither is correct. The fix is to ask which axis
applies, and to record - not silently discard - any case where two axes
disagree about the same claim.

## Axis A - Normative authority

*Answers: "what is this supposed to do / what was agreed?"*

```text
1. Vendor / official documentation, for the exact version in use
      |  outranks
2. An accepted specification or contract (protocol spec, OpenAPI, schema)
      |  outranks
3. A recorded decision (status: validated)
      |  outranks
4. An agreed scope document (charter, acceptance scope)
      |  outranks
5. Team convention / style guide
      |  outranks
6. An explicitly labeled assumption
```

## Axis B - Empirical authority

*Answers: "what actually happens, right now, in this environment?"*

```text
1. A reproducible automated test result
      |  outranks
2. An audited runtime trace / verified code path, cross-verified by a second source
      |  outranks
3. A single production/staging log observation, not yet cross-verified
      |  outranks
4. A secondhand, unverified chat-reported behavior claim
```

A vendor doc does not appear on this axis. It cannot be empirical evidence
of what a specific deployment does - only of what it is supposed to do.

## Axis C - Agent-execution authority

*Answers: "which instruction actually controls what the agent does right
now?"* - orthogonal to whether either instruction is factually correct.

```text
1. A persistent, versioned agent-instruction file (survives across sessions)
      |  outranks
2. An explicit session-scoped instruction or user override for this session
      |  outranks
3. An ad-hoc chat-turn instruction with no persistence
```

Hook-based enforcement is *not* on this axis by default: hook rewrite
support is not uniformly reliable across agents (see
[`adapters/README.md`](../../adapters/README.md)), so a hook cannot be
assumed to control agent behavior until verified end-to-end for the
specific agent and version in use. Until verified, treat the persistent
instruction file as the actual authority and the hook as a best-effort
assist.

## Axis D - Knowledge-lifecycle authority

*Answers: "is this artifact even trustworthy to cite right now?"* - governed
by `status` and `confidence`, not by source type. See
[`status-lifecycle.md`](status-lifecycle.md) and
[`confidence-levels.md`](confidence-levels.md). A `status: superseded`
artifact from axis A's top tier is *less* authoritative than a
`status: validated` artifact lower on the same axis.

## When axes disagree

Two sources on the **same axis** disagreeing (e.g. two vendor docs) resolve
normally: prefer the more specific/recent/version-matched one, and record
which you chose and why.

Two sources on **different axes** disagreeing about the same claim (e.g. a
vendor doc says X, a reproducible test shows not-X) do **not** resolve by
picking a winner. Record it as a discrepancy: what the normative source
says, what the empirical source shows, and which one governs *the specific
decision at hand* (a bug ticket wants the empirical truth; a compliance
question wants the normative one - both can be true statements about
different questions). Use the `fact` knowledge type with both citations
and an explicit `discrepancy: true`-style note in the body; do not silently
overwrite one side. See
[`knowledge-types.md`](knowledge-types.md#forbidden-mixing).

## Common cases, resolved

### "The docs say X, the logs show Y - which is right?"
Neither "wins" outright. Normative axis says X is the contract; empirical
axis says Y is what happens. Record both as a discrepancy. If Y reflects a
bug, the fix target is normative-compliance; if the docs are stale, the fix
target is updating axis A's top source.

### "A planning brief says one name, an audited fact says another"
Empirical/verified-code claims outrank an informal planning brief on axis
B - the brief may use logical/informal names, a facts artifact carries
wire names from an actual audit.

### "Persistent instructions vs. an ad-hoc chat instruction"
Axis C: the persistent file wins by default. A chat-scoped override is
legitimate for the current session only and does not change the persistent
contract.

### "An older decision record vs. new evidence"
Axis D: new evidence wins *if validated*. Mark the old record
`status: superseded`, create a new one - never silently overwrite.

### "Code and docs disagree"
This is axis A vs. axis B by another name: code is empirical (what
actually runs), docs are normative (what's supposed to run). Code wins if
the disagreement reflects real behavior a user depends on; docs win if the
code has a bug the docs correctly describe as *not* intended. Either way,
record the discrepancy - don't just pick a side and move on.

## Confidence and status are not authority

`confidence: high` records how strong the *evidence was when this artifact
was validated* - it is not a license to skip checking whether the artifact
still applies to your current situation (different environment, different
version, time elapsed since `review_after`). See
[`confidence-levels.md`](confidence-levels.md) for the explicit rule
against treating confidence as a verification bypass.
