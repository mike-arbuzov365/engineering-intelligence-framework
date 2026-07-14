---
type: analysis_digest
status: validated
source: retro
scope: project
created: 2026-07-16
---

# Fixture: analysis_digest without an artifact-level evidence field

Positive case for
core/ontology/knowledge-types.md#evidence-is-not-always-one-label-per-artifact
- analysis_digest is a procedural/multi-claim type and must validate fine
with no `evidence` field even though status is not draft.
