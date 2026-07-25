---
name: run-retro
description: >
  Run a retrospective across many sessions to find patterns that repeat,
  after a packet closeout, a significant incident, or on a 2-4 week cadence
  for an active project. Routes each recurring pattern to a knowledge
  artifact and an explicit promotion decision. Not a second session
  closeout.
---

# Skill: Run Retro

<!-- Knowledge source: GENERALIZE of the private EI's retro SKILL.md. Thin
pointer to playbooks/run-retro.md - one canonical source per D-007. -->

Full workflow: [`playbooks/run-retro.md`](../../playbooks/run-retro.md).

## When this applies

After an execution packet closeout, after a significant incident, or on a
2-4 week cadence for an active project instance. **Not** after every
session: a retro over one session has no repetition to find.

## Process

1. Derive the period's activity from the repository (`git log`,
   `git shortlog`, merged Knowledge Deltas, session and packet closeouts) -
   not from recollection.
2. Look for repetition: repeated failure signatures, blind-fix cycles,
   skipped evidence, skipped retrieval, policy-induced failures, hotspots.
3. Route each genuinely recurring pattern through
   [`knowledge-ingest.md`](../../playbooks/knowledge-ingest.md), then
   [`knowledge-lint.md`](../../playbooks/knowledge-lint.md) if it is a
   promotion candidate.
4. Write the artifact from
   [`templates/retro.md`](../../templates/retro.md).
5. Apply any new or changed rule to the persistent agent-instruction file
   in this same retro.

## Output

```markdown
Retro: <packet | incident | period>  Period: <start> - <end>

Recurring patterns: <N> (each with occurrence count and where observed)
New artifacts: <paths, or "none">
Promotion decisions: <promoted / stays local, per artifact>
Entrypoint updates applied: <yes, what | none>
```

## Boundaries

- A single occurrence is an `incident` or a `risk`, never a
  `failure_pattern`.
- Most validated project knowledge is meant to stay local. Promotion is the
  exception and is an owner decision.
- A rule recorded only in the retro artifact is not in force. Either it
  reaches the entrypoint file in this retro, or it is explicitly deferred.
