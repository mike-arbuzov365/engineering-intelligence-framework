---
type: playbook
status: validated
scope: framework
confidence: medium
created: 2026-07-25
related:
  - session-closeout.md
  - knowledge-ingest.md
  - knowledge-lint.md
  - execution-packet-review.md
---

# Playbook: Run Retro

<!-- Knowledge source: GENERALIZE of the private EI's run-retro.md playbook
and retro SKILL.md. Kept: the trigger set, the git-derived data-gathering
step, the recurring-pattern analysis, the Evolve Loop promotion routing, and
the retro artifact shape. Dropped: that instance's private paths
(`docs/60-retro/`, `planning/60-findings/`), its "visual hub drift" step
(specific to one private HTML artifact that does not exist here), its
Ukrainian-language convention, and the "PR into the private methodology
repository" routing, which is replaced with the generic promotion decision
this framework's own templates/knowledge-delta.md already asks. -->

Session closeout asks what *this* session learned. Retro asks a question a
single closeout cannot: **which patterns repeat across sessions?** A lesson
that shows up once is a note; the same lesson showing up three times is a
rule the framework is missing.

This is the outer of the two loops. The inner loop (solve) runs inside a
session and ends at [`session-closeout.md`](session-closeout.md). This one
runs across many of them.

## When to run this

- After an execution packet closes out, if it produced decisions,
  incidents, delivery friction or reusable lessons.
- After a significant incident.
- On a regular cadence for an active project instance (every 2-4 weeks is
  the interval the source instance settled on) when no event-based retro
  has happened.

Do not run it after every session. A retro over a single session has no
repetition to find and degrades into a second closeout.

## Step 1 - Gather, before concluding

Derive the period's activity from the repository rather than from memory:

```text
git log --oneline --since="<period>" --all
git shortlog --since="<period>" -s -n
git diff --stat <base>..HEAD
```

Then read, without drawing conclusions yet:

- Knowledge Delta sections from the period's merged pull requests.
- Session and packet closeouts from the period.
- Artifacts under the configured `knowledge.root` created or updated in the
  period, especially `incident` and `failure_pattern` types.
- Any artifact whose `review_after` date has passed (see
  [`core/ontology/status-lifecycle.md`](../core/ontology/status-lifecycle.md#checking-staleness)).

## Step 2 - Look for repetition, not events

The unit of analysis is the recurring pattern, not the individual failure:

- **Repeated failure signatures.** Did the same failure signature appear in
  more than one bounded evidence loop? See
  [`bounded-evidence-loop.md`](bounded-evidence-loop.md).
- **Blind-fix cycles.** Changes made without a diagnostic step first.
- **Evidence skipped.** A merged change treated as proof of behavior with no
  behavioral evidence recorded.
- **Retrieval skipped.** Work that repeated a lesson already sitting in
  `knowledge/`, meaning the preflight in
  [`knowledge-search.md`](knowledge-search.md) did not happen or did not
  surface it.
- **Policy-induced failure.** The agent followed the rules and the outcome
  was still bad. That is a defect in the rule, not in the agent.
- **Hotspots.** Files changed disproportionately often in the period.

## Step 3 - The Evolve Loop

For each pattern that genuinely repeats, route it once:

1. Is it already covered by an existing rule, playbook or knowledge
   artifact? If yes, the gap is discoverability, not content - fix the
   index or the retrieval path, do not write a second copy.
2. If not, it becomes a candidate artifact via
   [`knowledge-ingest.md`](knowledge-ingest.md), typed per
   [`core/ontology/knowledge-types.md`](../core/ontology/knowledge-types.md).
   A failure seen once is a `risk` or an `incident`; only a genuinely
   repeated one is a `failure_pattern`.
3. Does it apply beyond this project instance? Only then is it a promotion
   candidate. Run [`knowledge-lint.md`](knowledge-lint.md) before proposing
   it, and record the promotion decision explicitly - including a decision
   to keep it local, which is the common and correct outcome.

Promotion out of a project is an owner decision, not an automatic
consequence of passing a lint.

## Step 4 - Record the retro

A retro that produces no artifact did not happen. Write one to the project
instance's own documented retro location, using
[`templates/retro.md`](../templates/retro.md).

Its Knowledge Delta follows the same rules as any other
([`templates/knowledge-delta.md`](../templates/knowledge-delta.md)),
including the explicit "nothing to promote" case.

## Step 5 - Close the loop on the rules themselves

If the retro produced a new or changed rule, update the persistent
agent-instruction file for the affected scope in the same retro, not "next
time". A rule that exists only in a retro document is not in force: agents
read the entrypoint file, not the retro archive.

## Anti-patterns

- Running a retro over one session, where nothing can repeat yet.
- Recording a single occurrence as a `failure_pattern` because it felt
  significant. One occurrence is an `incident`.
- Promoting every validated lesson upward. Most project knowledge is
  supposed to stay in its project.
- Deriving the period's activity from recollection instead of from the
  repository, which is the same defect this framework's own closeout
  discipline exists to prevent.
- Writing the retro and leaving the entrypoint rules unchanged, so the
  lesson never reaches the next session.
