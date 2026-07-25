---
name: knowledge-curator
description: >
  Aggregate existing knowledge-base signals (links, orphans, freshness,
  schema, privacy, deferred closeout items) into one ranked maintenance
  backlog with a stable findings ledger, severity, routing and an owner
  path per finding. Read-only by default. Never merges, never edits source
  outside the instance it was pointed at.
---

# Skill: Knowledge Curator

<!-- Knowledge source: GENERALIZE of the private EI's knowledge-curator
SKILL.md. Thin pointer to playbooks/knowledge-curator.md - one canonical
source per D-007. -->

Full workflow: [`playbooks/knowledge-curator.md`](../../playbooks/knowledge-curator.md).

## When this applies

Before a promotion batch, before packet planning as a freshness gate,
after a packet closeout that changed methodology or skills, or when an
agent keeps asking something the knowledge base should already answer.

Not after every session. That is [`run-retro`](../run-retro/SKILL.md)'s
cadence, and a different question.

## Process

1. Read the previous findings ledger first, so each signal can be
   classified as new, recurring or regressed rather than reported fresh
   every time.
2. Collect only signals that already exist: link check, knowledge index
   orphans, `review_after` freshness, frontmatter validation, privacy
   scan and its suppression hygiene, deferred closeout items, integration
   health. Generating new evidence means this stopped being a curator run.
3. Classify each finding: severity, one of the six canonical routing
   tokens, fix class A/B/C, and an evidence label.
4. Escalate anything open at three or more occurrences by one severity
   level, with a prevention proposal rather than another fix.
5. Write the report from
   [`templates/curator-report.md`](../../templates/curator-report.md).
6. Only with an explicit opt-in, apply Class A fixes on their own branch
   and open a pull request.

## Output

```markdown
Curator report: <date>   Scope: <what was scanned>   Mode: read-only | fixes-proposed

Ledger diff: <new> new, <recurring> recurring, <closed> closed, <regressed> regressed
Severity: <blocker>/<major>/<minor>
Class A proposed: <n> (branch + PR, never merged)
Escalated on recurrence: <ids, or none>
```

## Boundaries

- **Never merge.** Class A fixes reach a pull request and stop there.
- **Never push to the default branch.**
- **Never edit source outside the instance** this run was pointed at.
- Class A is a closed list, and never touches `core/ontology/`,
  `core/policies/`, any `SKILL.md` or `.github/workflows/`. If a fix needs
  an argument for why it is safe, it is Class B.
- A finding is `resolved` only against evidence, and never in the same run
  that proposed the fix.
