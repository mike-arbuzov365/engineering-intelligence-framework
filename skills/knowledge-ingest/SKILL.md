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
3. Place it: this project instance's `knowledge/` if local, or flag as a
   candidate for the shared knowledge base if validated beyond this one
   project instance.
4. Create or update the artifact with correct `type`/`status`/
   `confidence`. If it contradicts previously accepted guidance, mark
   that guidance `deprecated`/`superseded` rather than deleting it.
5. Regenerate the knowledge index (`scripts/eif_generate_index.py`).
6. Close the Knowledge Delta - state what was added, or that nothing was.

## Output

- The created/updated knowledge artifact.
- Updated index.
- The Knowledge Delta entry.
