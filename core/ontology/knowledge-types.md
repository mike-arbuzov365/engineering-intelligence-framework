---
type: ontology
status: validated
scope: framework
---

# Knowledge taxonomy

A single classification for knowledge artifacts, shared across every project
instance using this framework.

## Types

### `fact`
Verified information about system state, code behavior, or an external
system's behavior.
- **Example:** "The webhook response must complete within 10 seconds."
- **Where:** `docs/knowledge/facts/`
- **vs. `rule`:** a fact describes what *is*; a rule prescribes what
  *should be*.

### `rule`
A prescriptive statement that **should** be followed. Has a concrete origin
(incident, pattern, audit) and executable actions.
- **Example:** "Never change protocol bytes based on logs alone."
- **Format:** `RULE-YYYY-MM-DD-<slug>`
- **Where:** the persistent agent-instruction file (short mandate) plus
  `docs/knowledge/rules/RULE-YYYY-MM-DD-*.md` (full context, recommended
  once a project accumulates several rules).
- **Template:** [`templates/rule-template.md`](../../templates/rule-template.md)
- **vs. `fact`:** prescriptive ("do X") vs. descriptive ("X is true").
- **vs. `failure_pattern`:** a rule says "do X to prevent Y" (prescriptive);
  a failure pattern says "Y happens because of Z" (diagnostic). They're
  often paired - the pattern documents the problem, the rule documents the
  prevention.

### `decision`
A recorded decision with context, alternatives, and consequences.
- **Format:** MADR-style (explicit alternatives considered)
- **Where:** `docs/knowledge/adr/ADR-XXXX-*.md`
- **Template:** [`templates/ADR-template.md`](../../templates/ADR-template.md)

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
- **Template:** [`templates/incident-template.md`](../../templates/incident-template.md)

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
- **Template:** [`templates/playbook-template.md`](../../templates/playbook-template.md)

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
- **Template:** [`templates/source-manifest-template.md`](../../templates/source-manifest-template.md)
- **vs. `fact`:** a manifest records provenance; a fact records a validated
  claim derived after analysis.

### `extraction_manifest`
An artifact recording a selective extraction from raw source material into
an agent-readable form (Markdown, text, CSV, a trace excerpt, or a
sanitized summary). Records coverage, gaps, method, quality notes, and
traceability back to the original source.
- **Where:** local, alongside extracted artifacts.
- **Template:** [`templates/extraction-manifest-template.md`](../../templates/extraction-manifest-template.md)
- **vs. `source_manifest`:** a source manifest says what was received; an
  extraction manifest says what was transformed and how.

### `analysis_digest`
A structured digest for source/customer intake that separates `OBSERVED`,
`INFERRED`, and `ASSUMED` claims, plus impact, risks, and open questions.
- **Where:** a local analysis folder, or a planning packet's facts document.
- **Template:** [`templates/analysis-digest-template.md`](../../templates/analysis-digest-template.md)
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

| Not allowed | Correct path |
|---|---|
| Hypothesis promoted directly to a rule | Hypothesis -> test -> validated fact |
| A log observation recorded directly as a fact | Log observation -> hypothesis -> vendor-doc confirmation -> fact |
| AI inference recorded directly as a rule | AI inference -> assumption -> validation -> rule |
| Chat memory recorded directly as knowledge | Chat memory -> Knowledge Delta -> triage -> validated artifact |

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

```yaml
---
type: fact | rule | decision | risk | edge_case | failure_pattern | incident | assumption | playbook | knowledge_operation | source_manifest | extraction_manifest | analysis_digest | open_question
status: draft | validated | superseded | deprecated
source: chat | code_review | test_failure | deployment | customer_feedback | vendor_docs | retro
confidence: low | medium | high
scope: framework | project
created: YYYY-MM-DD
review_after: YYYY-MM-DD  # when to re-check relevance
related:
  - path/to/related.md
---
```
