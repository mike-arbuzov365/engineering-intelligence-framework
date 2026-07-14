---
type: ontology
status: validated
scope: framework
created: 2026-07-15
review_after: 2026-10-15
---

# Status lifecycle for knowledge artifacts

<!-- Revised 2026-07-15 (review round 2): the diagram below used to chain
validated -> superseded -> deprecated as if deprecation only happens after
superseding. The transition-rules table already showed both as independent
transitions from validated; the diagram now matches the table. -->

## States

```text
draft
  |
  +--> validated ---+--> superseded
  |                  |
  |                  +--> deprecated
  |
  +--> rejected   (type: hypothesis only - see "rejected" below)
```

`validated -> superseded` and `validated -> deprecated` are independent
transitions - an artifact can be superseded without ever being formally
deprecated, and vice versa. Do not treat one as a prerequisite for the
other.

### `draft`
- Just created, not yet confirmed.
- Do not use as a basis for decisions without an explicit caveat.
- Typical sources: a session's Knowledge Delta, an unreviewed retro item.

### `validated`
- Confirmed by a test, a runtime trace, an official specification, or a
  stakeholder/owner confirmation - see
  [`knowledge-types.md#source`](knowledge-types.md#knowledge-artifact-metadata)
  for the channel and
  [`authority-model.md`](authority-model.md) for which axis that channel
  sits on.
- Can be used as an authoritative source.
- Must carry `evidence` (see
  [`confidence-levels.md`](confidence-levels.md)) for artifact types where
  evidence applies - see
  [`knowledge-types.md#evidence-is-not-always-one-label-per-artifact`](knowledge-types.md#evidence-is-not-always-one-label-per-artifact)
  for the types where it doesn't (`analysis_digest`, provenance types).

### `superseded`
- Replaced by a newer artifact.
- Kept for traceability - do not delete.
- Must carry `superseded_by: path/to/new.md`.

### `deprecated`
- No longer relevant; out of current scope.
- Reason: technology changed, project ended, etc.
- Kept for historical context.

For accepted rules or playbook guidance that should stop guiding future
agents, `deprecated` is the append-only retraction path. Never delete an
artifact or rewrite history as if guidance was never accepted. Instead
record:

- `deprecated_reason`
- Evidence, or a session/change reference that justifies the change.
- The deprecation date.
- `replaced_by`, if there is a replacement artifact.

Do not use `rejected` for guidance that was already accepted or validated.
`rejected` is reserved for `type: hypothesis` candidates that never became
validated knowledge - see below.

### `rejected` (`type: hypothesis` only)
- A hypothesis disproven by evidence or testing.
- **Only valid when the artifact's `type` is `hypothesis`.** Every other
  type transitions through `deprecated` if it needs to be retracted, not
  `rejected` - a rejected `fact` or `rule` never existed as validated
  knowledge in the first place, so there's nothing to "reject"; if a
  `validated` artifact turns out to be wrong, that's a `deprecated`
  correction with a `deprecated_reason`, not a `rejected` one.
- Kept in the record as a "rejected hypothesis" - valuable so future
  sessions don't re-attempt the same disproven path.

## Transition rules

| Transition | Who initiates | What's required |
|---|---|---|
| draft -> validated | Planner / owner | Evidence or a test |
| validated -> superseded | Planner | A new decision record or fact |
| validated -> deprecated | Planner | Justification, date, evidence/reference |
| draft -> rejected (`type: hypothesis` only) | Planner | Counter-evidence |

## Example frontmatter

```yaml
---
type: rule
status: validated
confidence: high
evidence: OBSERVED
source: official_specification
created: 2026-05-16
related:
  - path/to/the/specification/reference.md
---
```

See [`knowledge-types.md#knowledge-artifact-metadata`](knowledge-types.md#knowledge-artifact-metadata)
for the full field list, including `environment`/`source_version`/
`applies_to` for scoping empirical claims - `status`, `confidence`,
`evidence`, and applicability/freshness (`review_after`,
`environment`/`source_version`/`applies_to`) are four distinct concepts
that frequently get conflated; see
[`knowledge-types.md#status-confidence-evidence-and-applicability-are-not-the-same-thing`](knowledge-types.md#knowledge-artifact-metadata)
if you're tempted to merge any two of them.

## Checking staleness

A `review_after` frontmatter field sets a re-check date. During a
retrospective, review every artifact whose `review_after` date has passed.
