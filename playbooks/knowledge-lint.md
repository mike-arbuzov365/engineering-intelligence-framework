---
type: knowledge_operation
status: validated
scope: framework
confidence: high
created: 2026-07-19
related:
  - knowledge-ingest.md
  - ../core/ontology/knowledge-types.md
---

# Playbook: Knowledge Lint

<!-- Knowledge source: GENERALIZE of the private EI's knowledge-lint.md.
Kept: the severity model, the type-discipline and location/duplication
checks, the schema-exceptions note (not every tracked file is a
full-frontmatter knowledge artifact). Dropped: the
Ukrainian-language-with-exceptions check (a private-instance convention;
this framework's own public-facing language rule is
core/ontology/language-rules.md, which callers should check instead) and
references to private-only indexes. -->

Manual review of knowledge-artifact quality, before it's proposed for
promotion beyond this project instance or before a significant
packet/session closeout.

## When to run this

- Before proposing a knowledge artifact for the shared knowledge base.
- After a significant packet closeout.
- Whenever docs or knowledge artifacts seem to have drifted or
  contradict each other.

## Severity

| Severity | Meaning |
|---|---|
| `BLOCKER` | Safety, source-hierarchy, secrets, or raw-reasoning violation |
| `MAJOR` | Wrong type/status, drift, broken authority chain, missing index entry |
| `MINOR` | Wording, formatting, weak links |

## Checklist

### 1. Source and evidence

- [ ] Every fact/rule/decision has a source.
- [ ] `OBSERVED`/`INFERRED`/`ASSUMED` are not blended.
- [ ] Vendor docs or verified code outrank chat memory (see
      [`core/ontology/authority-model.md`](../core/ontology/authority-model.md)).
- [ ] No rule exists that's backed only by AI inference with nothing
      verified.

### 2. Type discipline

Per [`core/ontology/knowledge-types.md`](../core/ontology/knowledge-types.md):

- [ ] `fact` describes state; `rule` prescribes behavior - not swapped.
- [ ] A `hypothesis` isn't recorded as if it were a `fact`/`rule`.
- [ ] An `incident` isn't reduced to a generic bug note.
- [ ] A `failure_pattern` is genuinely repeated, or explicitly marked a
      candidate, not asserted from one occurrence.

### 3. Status and confidence

- [ ] The artifact has a `status` (see
      [`core/ontology/status-lifecycle.md`](../core/ontology/status-lifecycle.md))
      and, where applicable, a `confidence` (see
      [`confidence-levels.md`](../core/ontology/confidence-levels.md)).
- [ ] Draft artifacts aren't presented as validated.
- [ ] Deprecated/superseded artifacts point to their replacement, if any.

**Schema exceptions:** not every tracked file under `knowledge/` is a
full-frontmatter knowledge artifact. Skills (`SKILL.md`) use their own
manifest shape (`name`, `description`) and shouldn't be flagged for
missing `type`/`status`. A copyable template under `templates/` may
contain a target document's own body/frontmatter rather than the
template's own - check whether it's genuinely a template before flagging
it as a knowledge artifact with missing metadata.

### 4. Location and duplication

- [ ] Project-specific knowledge stays in this project instance's
      `knowledge/`.
- [ ] Something proposed as shared knowledge is actually applicable
      beyond this one project instance, or has explicit owner approval.
- [ ] No duplication between this project instance and the shared
      knowledge base without a cross-reference.

### 5. Links and indexes

- [ ] The relevant index/README is updated.
- [ ] The knowledge index is regenerated if artifacts changed
      (`scripts/eif_generate_index.py`).
- [ ] No broken links or stale paths (`scripts/eif_check_links.py`).

### 6. Privacy

- [ ] No secrets, tokens, or private/customer data
      (`scripts/eif_privacy_scan.py`).
- [ ] No raw AI reasoning or chain-of-thought - structured conclusions
      only.

### 7. Session and packet closeout

- [ ] Verification commands were actually run, or explicitly deferred
      with a reason.
- [ ] The Knowledge Delta is filled, or carries the explicit
      `<!-- no-knowledge-delta: mechanical task -->` marker.
- [ ] Deferred items are explicit, not implied.
- [ ] Ephemeral session-context files are not committed.

## Output format

```markdown
## Knowledge Lint Result

Status: PASS | PASS_WITH_NOTES | FAIL

Findings:
- [BLOCKER] <file>: <issue> -> <recommended fix>
- [MAJOR] <file>: <issue> -> <recommended fix>
- [MINOR] <file>: <issue> -> <recommended fix>

Verified:
- <commands or files actually checked>

Deferred:
- <what wasn't checked and why>
```

## Automation boundary

This is a manual review. Do not wire it into required CI until the
checklist above has proven stable across several real reviews - see
[`core/policies/decisions.md`](../core/policies/decisions.md) for this
framework's general CI-cost discipline.
