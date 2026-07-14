---
type: ontology
status: validated
scope: framework
---

# Confidence levels

## Levels

### `high`
**Confirmed by two or more independent sources, or passed a test in a real
environment (staging/production).**

- Vendor documentation *and* observed in logs.
- An automated test passes.
- Stakeholder-confirmed across 2+ rounds/sessions.
- Code audit with cross-verification against another source.

Artifacts marked `confidence: high` can be used as a basis for decisions
without further verification.

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
