---
type: ontology
status: validated
scope: framework
created: 2026-07-15
review_after: 2026-10-15
---

# Knowledge taxonomy

A single classification for knowledge artifacts, shared across every project
instance using this framework.

## Types

### `fact`
Verified information about system state, code behavior, or an external
system's behavior - an **empirical** claim ("this is what happens"), not a
**normative** one ("this is what should happen"). A requirement, contract,
or intended behavior belongs in `rule` or `decision`, even if it's true and
well-evidenced - putting a normative claim under `fact` is a type error the
same way putting an unvalidated hypothesis under `fact` is.
- **Example (correct - empirical):** "The webhook responds in under 10
  seconds in the current staging environment, verified by load test."
- **Example (wrong - normative, belongs in `rule`):** "The webhook must
  complete within 10 seconds." - this is a requirement, not an observation.
- **Where:** `docs/knowledge/facts/`
- **vs. `rule`:** a fact describes what *is* (empirical, axis B in the
  [authority model](authority-model.md)); a rule prescribes what *should
  be* (normative, axis A).

### `rule`
A prescriptive statement that **should** be followed. Has a concrete origin
(incident, pattern, audit) and executable actions.
- **Example:** "Never change protocol bytes based on logs alone."
- **Format:** `RULE-YYYY-MM-DD-<slug>`
- **Where:** the persistent agent-instruction file (short mandate) plus
  `docs/knowledge/rules/RULE-YYYY-MM-DD-*.md` (full context, recommended
  once a project accumulates several rules).
- **Template (not built yet):** `templates/rule-template.md`
- **vs. `fact`:** prescriptive ("do X") vs. descriptive ("X is true").
- **vs. `failure_pattern`:** a rule says "do X to prevent Y" (prescriptive);
  a failure pattern says "Y happens because of Z" (diagnostic). They're
  often paired - the pattern documents the problem, the rule documents the
  prevention.

### `decision`
A recorded decision with context, alternatives, and consequences.
- **Format:** MADR-style (explicit alternatives considered)
- **Where:** `docs/knowledge/adr/ADR-XXXX-*.md`
- **Template (not built yet):** `templates/ADR-template.md`

### `risk`
An identified risk requiring monitoring or mitigation.
- **Fields:** probability (H/M/L), impact (H/M/L), trigger, mitigation.
- **Where:** `docs/knowledge/risks/`

### `edge_case`
An atypical scenario that has occurred or could occur and needs special
handling.
- **Where:** `docs/knowledge/edge-cases/`

### `failure_pattern`
A recurring error pattern that has already happened - a generalization, not
a single incident.
- **Example:** "Blind fix cycle - fixing without diagnostics leads to 3+
  failed rounds."
- **Where:** framework-wide `core/policies/` (if broadly applicable) or
  project-local `docs/knowledge/`.

### `incident`
A specific failed round, deployment failure, or testing blocker.
- **Format:** `INC-YYYY-MM-DD-*`
- **Where:** `docs/knowledge/incidents/`
- **Template (not built yet):** `templates/incident-template.md`

### `assumption`
A working assumption not yet validated. Must be explicitly labeled and
eventually checked.
- **vs. `fact`:** an assumption requires confirmation before it can be
  relied on.
- **Important:** never mix an assumption into a fact or a rule.

### `playbook`
A step-by-step instruction for a recurring task.
- **Where:** framework-wide `playbooks/` or project-local
  `docs/knowledge/playbooks/`.
- **Template (not built yet):** `templates/playbook-template.md`

### `knowledge_operation`
An operational process for creating, checking, or maintaining knowledge
artifacts - a workflow for agents, not a fact about the system itself.
- **Example:** knowledge ingestion, knowledge linting, knowledge health
  checks.
- **Where:** `playbooks/` plus an optional matching skill under `skills/`.
- **vs. `playbook`:** a playbook can describe any recurring task; a
  knowledge operation always changes or checks the state of knowledge
  itself.

### `source_manifest`
A provenance artifact for incoming source material - documents, archives,
messages, PR comments, logs, screenshots, or local drops from a stakeholder
or developer. Records date, channel, source, privacy boundary, original
location, current processing stage, and initial routing.
- **Where:** local to the repo, alongside the originals/inventory (e.g. an
  inbox or intake directory).
- **Template (not built yet):** `templates/source-manifest-template.md`
- **vs. `fact`:** a manifest records provenance; a fact records a validated
  claim derived after analysis.

### `extraction_manifest`
An artifact recording a selective extraction from raw source material into
an agent-readable form (Markdown, text, CSV, a trace excerpt, or a
sanitized summary). Records coverage, gaps, method, quality notes, and
traceability back to the original source.
- **Where:** local, alongside extracted artifacts.
- **Template (not built yet):** `templates/extraction-manifest-template.md`
- **vs. `source_manifest`:** a source manifest says what was received; an
  extraction manifest says what was transformed and how.

### `analysis_digest`
A structured digest for source/customer intake that separates `OBSERVED`,
`INFERRED`, and `ASSUMED` claims, plus impact, risks, and open questions.
- **Where:** a local analysis folder, or a planning packet's facts document.
- **Template (not built yet):** `templates/analysis-digest-template.md`
- **vs. raw AI reasoning:** contains only the structured result and
  evidence links, never a chain-of-thought dump.

### `open_question`
An open question needing an answer - blocking or non-blocking.
- **Where:** `docs/knowledge/open-questions.md`

### `hypothesis`
A hypothesis under consideration but not yet confirmed or disproven.
- **Important:** a hypothesis never becomes a `rule` or `fact` without
  validation.
- **Lifecycle:** hypothesis -> validated -> fact/rule, OR
  hypothesis -> rejected -> recorded as a rejected hypothesis.

## Forbidden mixing

<!-- Revised 2026-07-15: the log-observation path used to force every
observation through a hypothesis AND require vendor-doc confirmation
specifically. That's wrong for empirical (axis B) claims about internal or
runtime-only behavior a vendor doc would never address - a second
reproducible observation or a test is valid confirmation on its own. -->

| Not allowed | Correct path |
|---|---|
| Hypothesis promoted directly to a rule | Hypothesis -> test -> validated fact |
| A single, uncross-verified log observation recorded directly as `confidence: high` | Log observation -> `confidence: low` fact (or hypothesis, either is defensible) -> a second independent observation, a reproducible test, **or** a vendor-doc confirmation (any one raises confidence - vendor docs are not the only valid path, especially for internal/runtime-only behavior) -> `confidence: medium`/`high` fact |
| AI inference recorded directly as a rule | AI inference -> assumption -> validation -> rule |
| Chat memory recorded directly as knowledge | Chat memory -> Knowledge Delta -> triage -> validated artifact |
| A normative requirement filed as `fact` | Requirement -> `rule` or `decision`, not `fact` - see [`fact`](#fact) |
| A `rule`/`fact` disagreement between axis A and axis B silently resolved by picking one | Record both citations and the disagreement explicitly - see [authority-model.md#when-axes-disagree](authority-model.md#when-axes-disagree) |

## Canonical example: wrong vs. right

### Wrong

```markdown
## Knowledge Delta
### New facts
- The agent decided to use PowerShell for better toolchain compatibility.
  INFERRED: PowerShell integrates better with the Windows toolchain here.
  ASSUMED: bash won't be supported in CI.
```

**What's wrong:** `INFERRED` and `ASSUMED` content is filed as "new facts" -
a type mismatch. A hypothesis never became a fact through validation. Chat
memory ("decided to") became an artifact without evidence.

### Right

```markdown
## Knowledge Delta
### New decisions
- **D-001 (implementation default):** PowerShell chosen for scripts.
  OBSERVED: platform is Windows, PowerShell is available. Python is the
  fallback if it isn't. Recorded in the session closeout for future sessions.

### New risks
- Python fallback in CI: the CI runner may lack a PowerShell-compatible
  environment -> mitigated by running that CI job in Python instead.
  probability: M | impact: L | trigger: PowerShell unavailable on the runner.
```

**Why it's right:** the decision is filed as `decision`, not `fact`;
`OBSERVED` marks a direct check; the risk is documented separately with
probability/impact/trigger fields.

## Optional local extensions

A project instance may add extra folders or metadata fields if they are
documented in that project's own persistent agent-instruction file or
knowledge index. Approved optional examples: `rules/`, `retros/`,
`registry/`, an `applies_to:` frontmatter field. Extensions do not become
mandatory framework-wide without a separate, explicit approval.

## Knowledge-artifact metadata

<!-- Revised 2026-07-15: added `rejected` to `status` (status-lifecycle.md
already required it for hypotheses; this enum had drifted out of sync with
that prose). Added `evidence` as a first-class field instead of only a
prose/comment convention, plus applicability fields (`environment`,
`source_version`, `applies_to`) so confidence can't be mistaken for
unconditional applicability - see confidence-levels.md#what-confidence-is-not.
A machine-readable version of this schema lives in
core/schemas/knowledge-frontmatter.schema.json; keep both in sync. -->

```yaml
---
type: fact | rule | decision | risk | edge_case | failure_pattern | incident | assumption | playbook | knowledge_operation | source_manifest | extraction_manifest | analysis_digest | open_question
status: draft | validated | superseded | deprecated | rejected  # rejected is hypotheses-only, see status-lifecycle.md
evidence: OBSERVED | INFERRED | ASSUMED  # epistemic label - see authority-model.md; required when status is not draft
source: chat | code_review | test_failure | deployment | customer_feedback | vendor_docs | retro  # channel this came from, distinct from `evidence`
confidence: low | medium | high  # see confidence-levels.md - not a verification bypass
scope: framework | project
created: YYYY-MM-DD
review_after: YYYY-MM-DD  # when to re-check relevance/staleness

# Optional, recommended for empirical (axis B) artifacts - narrows where
# a claim actually applies, so `confidence: high` isn't mistaken for
# "true everywhere." Omit fields that don't apply.
environment: string        # e.g. "staging", "prod-eu", "local-dev"
source_version: string     # the version of the system/library this was observed against
applies_to: string         # free-text scope narrowing, e.g. "Windows only", "API v2 only"

related:
  - path/to/related.md
---
```
