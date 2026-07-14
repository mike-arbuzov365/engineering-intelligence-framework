---
type: ontology
status: validated
scope: framework
---

# Status lifecycle for knowledge artifacts

## States

```text
draft
  |
  +--> validated --> superseded --> deprecated
  |
  +--> rejected (hypotheses only)
```

### `draft`
- Just created, not yet confirmed.
- Do not use as a basis for decisions without an explicit caveat.
- Typical sources: a session's Knowledge Delta, an unreviewed retro item.

### `validated`
- Confirmed by a test, vendor doc, or stakeholder confirmation.
- Can be used as an authoritative source.
- Must carry evidence (what specifically confirms it).

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
`rejected` is reserved for candidates/hypotheses that never became validated
knowledge.

### `rejected` (hypotheses only)
- A hypothesis disproven by evidence or testing.
- Kept in the record as a "rejected hypothesis" - valuable so future
  sessions don't re-attempt the same disproven path.

## Transition rules

| Transition | Who initiates | What's required |
|---|---|---|
| draft -> validated | Planner / owner | Evidence or a test |
| validated -> superseded | Planner | A new decision record or fact |
| validated -> deprecated | Planner | Justification, date, evidence/reference |
| draft -> rejected | Planner | Counter-evidence |

## Example frontmatter

```yaml
---
type: rule
status: validated
confidence: high
source: vendor_docs
created: 2026-05-16
evidence: "Vendor doc section 3.2.1 confirms this behavior"
---
```

## Checking staleness

A `review_after` frontmatter field sets a re-check date. During a
retrospective, review every artifact whose `review_after` date has passed.
