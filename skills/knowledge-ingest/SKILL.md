---
name: knowledge-ingest
description: >
  Turn raw evidence from work, review, an incident, or a docs audit into
  a durable knowledge artifact - not a chat summary or raw reasoning.
  Use after a Knowledge Delta records something durable, or after an
  incident with prevention value.
---

# Skill: Knowledge Ingest

<!-- Knowledge source: GENERALIZE of the private EI's knowledge-ingest
SKILL.md. Thin pointer to playbooks/knowledge-ingest.md - one canonical
source per D-007. -->

Full workflow: [`playbooks/knowledge-ingest.md`](../../playbooks/knowledge-ingest.md).

## Process

1. Gather the evidence (source path, command output). Mark it
   `OBSERVED`, `INFERRED`, or `ASSUMED`.
2. Classify the artifact type against
   [`core/ontology/knowledge-types.md`](../../core/ontology/knowledge-types.md)
   (`fact`, `rule`, `decision`, `risk`, `edge_case`, `failure_pattern`,
   `incident`, `assumption`, ...).
3. Place it in the configured project source using its ownership rules.
   Flag candidates for shared scope or pending write access in the Delta.
4. Create or update the artifact with correct `type`/`status`/
   `confidence`. If it contradicts previously accepted guidance, mark
   that guidance `deprecated`/`superseded` rather than deleting it.
5. Regenerate the EIF-managed index (`scripts/eif_generate_index.py`) for
   managed knowledge. Follow the project's procedure for external knowledge.
6. Close the Knowledge Delta with the source and result or a reason to defer.

## Output

- The created/updated knowledge artifact.
- Retrieval verification or the documented access limit.
- The Knowledge Delta entry.
