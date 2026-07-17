---
type: ontology
status: validated
scope: framework
created: 2026-07-15
review_after: 2026-10-15
---

# Confidence levels

<!-- Revised 2026-07-15: confidence used to be described as license to skip
further verification. It isn't - see "What confidence is not" below. -->

## Levels

### `high`
**Confirmed by two or more independent sources, or passed a test in a real
environment (staging/production).**

- Vendor documentation *and* observed in logs.
- An automated test passes.
- Stakeholder-confirmed across 2+ rounds/sessions.
- Code audit with cross-verification against another source.

Artifacts marked `confidence: high` can be cited as a decision basis
without *re-deriving the original evidence* - you don't need to redo the
cross-verification that already happened. You still need to check
applicability (see below) before applying it to a new situation.

### `medium`
**Confirmed by exactly one source, or reasonably inferred with adequate
supporting evidence.**

- Observed in logs, but not cross-verified.
- Inferred from vendor docs but not confirmed by a test.
- Inferred from an analogous pattern in another project.

Artifacts marked `confidence: medium` need caution before being used as a
decision basis - don't treat them as settled.

### `low`
**An assumption, or an unverified inference - needs confirmation.**

- Inferred with no vendor-doc or test backing.
- Only chat memory or raw AI inference.
- Observed exactly once, never reproduced.

Artifacts marked `confidence: low` must be explicitly labeled as an
assumption everywhere they are used, not just where they were first recorded.

## Marking convention

When citing a knowledge artifact in documentation or code:

```markdown
<!-- confidence: high -->
Vendor docs section 3.2.1 confirms this behavior.

<!-- confidence: medium -->
Observed in session N; needs independent cross-verification.

<!-- confidence: low - ASSUMPTION -->
Assumed a 30s timeout; not yet confirmed.
```

## Raising confidence

| From -> To | What's needed |
|---|---|
| low -> medium | One confirming source (log + vendor doc, or a test) |
| medium -> high | Two independent sources, or an automated test |
| any -> rejected | Counter-evidence or a failed test |

## What confidence is not

`confidence` measures how strong the evidence was **at the time this
artifact was validated**. It is not:

- **Not permission to skip applicability checks.** A `confidence: high`
  fact about one environment, version, or time window does not
  automatically transfer to a different one. Use `environment`,
  `source_version`, and `applies_to` frontmatter fields (see
  [`knowledge-types.md`](knowledge-types.md#knowledge-artifact-metadata))
  to scope a claim, and check them before relying on it somewhere else.
- **Not a freshness signal.** `confidence: high` from a year ago can still
  be stale. Use `review_after` for that - see
  [`status-lifecycle.md`](status-lifecycle.md#checking-staleness).
- **Not authority.** Confidence is one axis (D) of the
  [authority model](authority-model.md#axis-d---knowledge-lifecycle-authority);
  it doesn't override axis A/B/C on its own. A `confidence: high` empirical
  fact and a `confidence: high` normative doc can still legitimately
  disagree - see
  [authority-model.md#when-axes-disagree](authority-model.md#when-axes-disagree).
