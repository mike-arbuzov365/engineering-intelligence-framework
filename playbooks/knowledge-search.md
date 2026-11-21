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

Resolve `knowledge.root`, `knowledge.index_path` and `knowledge.managed` from the
selected project's `.eif/config.yaml`. A missing `managed` flag is treated as
managed for older instances.

- For EIF-managed knowledge, use `eif_knowledge_search` or
  `eifctl search "<query>" --knowledge-root "<configured root>"`. From a
  framework checkout the equivalent command is
  `python scripts/eif_search_knowledge.py --framework-root . --knowledge-root "<configured root>" "<query>"`.
  The tool scans the configured directory and applies eligible statuses.
  Read the source of a relevant result, including the reason for a rejected
  or superseded approach if it could recur.
- For project-owned knowledge (`knowledge.managed: false`), follow the
  project's existing retrieval policy and use its index or search if
  available. EIF's reader may identify a contained index, and leaves the
  search to the project's tool. Record when that tool or source is unavailable.

Distinguish a query with zero eligible matches from unavailable or partial
coverage. Check malformed, schema-invalid and skipped-status counts before
claiming what was searched. The managed index helps navigation, while keyword
search reads the files directly.

## Recording the result

Record the query, route and coverage in the task-scope or session-launch file
before editing. Include the source path or identifier, its revision or date
when available, and the effect on the plan. For a light task the learning
check can stay in the conversation.

On resume, compare the recorded source with the current version or repeat
the scoped lookup if the earlier version was unrecorded. Read the source again
if it changed and update the impact. Record if you can no longer reach it.

## Anti-patterns

- Skipping the search because the task "looks simple" - simple-looking
  tasks are exactly where a past lesson is most likely to apply.
- Treating an empty result as proof nothing relevant exists without
  checking coverage and eligible statuses.
- Searching, finding a relevant `rejected` or `superseded` artifact, and
  not reading why before repeating the same approach.
