---
type: knowledge_operation
status: validated
scope: framework
confidence: high
created: 2026-07-19
related:
  - knowledge-ingest.md
  - knowledge-lint.md
---

# Playbook: Knowledge Search

<!-- Knowledge source: GENERALIZE, built from the framework's own
Experience Retrieval design (docs/architecture/HOW-EIF-WORKS.md#experience-retrieval)
and scripts/eif_search_knowledge.py/eif_generate_index.py directly - the
private EI has no single dedicated "knowledge-search" playbook file (the
behavior is folded into its session-execution preflight), so this is a
first standalone version rather than a port of one file. -->

Search existing knowledge before non-trivial work, so a plausible-looking
approach doesn't repeat a mistake a prior session already found and
recorded.

## When to run this

- Before implementing anything non-trivial (the experience-retrieval
  preflight step in [`session-execution.md`](session-execution.md) and
  [`templates/task-scope.md`](../templates/task-scope.md)).
- While planning a packet, searching for prior related work, incidents,
  or rejected approaches (see
  [`execution-packet-planning.md`](execution-packet-planning.md)).
- Whenever something feels like it should already have an answer
  somewhere in `knowledge/`.

## How

```text
python scripts/eif_search_knowledge.py "<query>"
```

An offline, Unicode-aware keyword/substring search over the index built
by `scripts/eif_generate_index.py` from every artifact under
`knowledge.root`. Excludes `rejected`/`superseded` artifacts by default -
pass the relevant flag if you specifically need to see why something was
rejected. This is deliberately not semantic/embedding search; see
[`docs/architecture/HOW-EIF-WORKS.md#limitations`](../docs/architecture/HOW-EIF-WORKS.md#limitations)
for the tradeoff and when it stops holding (very large knowledge bases,
queries where the relevant term isn't in the text).

If the index is stale or missing, rebuild it first:

```text
python scripts/eif_generate_index.py
```

Malformed-YAML and schema-invalid artifacts are reported as distinct,
honest categories by the generator - never silently treated as "no
results." If your search comes back empty, check whether the generator
reported skipped/invalid artifacts before concluding nothing relevant
exists.

## Recording the result

Whatever preflight step triggered the search, record it there, not just
in scratch reasoning:

- Query used.
- What was found (artifact path), or that nothing relevant was found.
- How it changes the plan - or `n/a` if it doesn't.

A search that finds nothing relevant is still worth recording as
evidence that the check happened - it is not the same as skipping the
step.

## Anti-patterns

- Skipping the search because the task "looks simple" - simple-looking
  tasks are exactly where a past lesson is most likely to apply.
- Treating an empty result as proof nothing relevant exists without
  checking whether the index itself is current.
- Searching, finding a relevant `rejected` or `superseded` artifact, and
  not reading why before repeating the same approach.
