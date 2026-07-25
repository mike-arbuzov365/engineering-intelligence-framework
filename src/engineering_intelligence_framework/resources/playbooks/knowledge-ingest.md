---
type: knowledge_operation
status: validated
scope: framework
confidence: high
created: 2026-07-19
related:
  - knowledge-search.md
  - knowledge-lint.md
  - ../core/ontology/knowledge-types.md
---

# Playbook: Knowledge Ingest

<!-- Knowledge source: GENERALIZE of the private EI's knowledge-ingest.md.
Kept: the source-hierarchy check, the artifact-type classification step,
the deprecate-don't-delete rule for superseded guidance. Dropped: the
framework-layer-PR-to-a-separate-methodology-repository routing (replaced with the
generic "propose for the shared knowledge base" question this framework's
own templates/knowledge-delta.md already asks) and the
Ukrainian-language requirement (a private-instance convention, not part
of this framework's own language rules). -->

Turn raw evidence from work, review, an incident, or a docs audit into a
durable knowledge artifact - not a chat summary, and not raw reasoning.

## When to run this

- After a Knowledge Delta records new facts, rules, or edge cases.
- After an incident or a failed attempt with prevention value.
- After a review surfaces a reusable rule.
- After evidence that previously accepted guidance should be deprecated
  or superseded.

## Source hierarchy

Before creating an artifact, check authority per the framework's
[authority model](../core/ontology/authority-model.md): vendor docs and
verified code outrank validated knowledge assets, which outrank chat
memory and raw inference. If the only source is chat memory, record an
`assumption` or `open_question`, not a `fact`/`rule`.

## Workflow

1. **Gather evidence.** Record the source (file path, PR/comment
   reference, or command output). Mark it `OBSERVED`, `INFERRED`, or
   `ASSUMED`. Discard raw reasoning; keep the structured result.
2. **Classify the artifact type.** Use the types defined in
   [`core/ontology/knowledge-types.md`](../core/ontology/knowledge-types.md)
   (`fact`, `rule`, `decision`, `risk`, `edge_case`, `failure_pattern`,
   `incident`, `assumption`, `open_question`, ...) - do not invent a new
   type or blend two.
3. **Place it.** Project-instance-specific knowledge goes under this
   project instance's `knowledge/`. Knowledge validated as useful beyond
   this one project instance is a candidate for the shared knowledge base
   - see the "Promote to shared knowledge base?" question in
   [`templates/knowledge-delta.md`](../templates/knowledge-delta.md).
4. **Create or update the artifact.** Use an existing artifact's
   frontmatter shape (`type`, `status`, `confidence` per
   [`core/ontology/confidence-levels.md`](../core/ontology/confidence-levels.md)
   and [`status-lifecycle.md`](../core/ontology/status-lifecycle.md)).
   If evidence contradicts previously accepted guidance, do not delete
   the old artifact - mark it `deprecated`/`superseded` with the reason,
   date, source, and a replacement link if one exists. A hypothesis that
   didn't hold up gets recorded as `rejected`, not quietly removed.
5. **Update indexes.** Rebuild the knowledge index
   (`scripts/eif_generate_index.py`) so the new/updated artifact is
   findable via [`knowledge-search.md`](knowledge-search.md).
6. **Close the Knowledge Delta.** Record what was added. If ingest added
   nothing, say so explicitly rather than leaving the section blank.

## Decision matrix

| Evidence | Artifact type | Scope |
|---|---|---|
| One-time task note | Not ingested | Session checkpoint / closeout only |
| Verified behavior in code/docs | `fact` | Local or shared, per scope |
| Prevention behavior after an incident | `rule` | Local first; shared after validation |
| A failure repeated across projects | `failure_pattern` | Shared |
| An architectural choice | `decision` | Local (ADR) |
| Unresolved uncertainty with no evidence | `assumption` / `open_question` | Local planning |
| Guidance that should stop applying | `deprecated`/`superseded` update | The existing artifact's own location |
| A hypothesis evidence rejected | `rejected` note | Knowledge Delta or closeout |

## Quality gate

An artifact is ready when it: has a clear source; has the correct type;
doesn't duplicate an existing artifact without linking to it; doesn't mix
fact/rule/hypothesis; has `status` and `confidence`; is indexed; and
contains no secrets, private data, or raw chain-of-thought. Run
[`knowledge-lint.md`](knowledge-lint.md) before proposing anything for
promotion beyond this project instance.
