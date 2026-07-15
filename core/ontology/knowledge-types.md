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

### `decision_register`
<!-- Added 2026-07-16 (review round 3, NEW-CORRECTION): fixes a real
inconsistency (core/policies/decisions.md had type: decision + status:
draft while containing ratified decisions - a register isn't one decision,
and wasn't a draft). Not a private-EI capability being ported - the
private instance uses a flat findings-ledger without this distinction. -->
A maintained index of multiple `decision` entries (or other single-claim
artifacts), where **each entry carries its own status** and the register
document's own `status` describes whether the *register itself* is
current and accurate - not the status of any individual entry.
- **Example:** [`core/policies/decisions.md`](../policies/decisions.md) -
  `status: validated` there means "this register accurately reflects
  current decision statuses," while individual entries are separately
  labeled Ratified/Provisional/Open in the document body.
- **vs. `decision`:** a `decision` artifact is one claim; a
  `decision_register` is a maintained list of many, each independently
  statused - see
  [Evidence is not always one label per artifact](#evidence-is-not-always-one-label-per-artifact),
  the same shape problem `analysis_digest` has, for a different reason
  (multiple decisions instead of multiple observations).
- **Important:** do not silently change an entry already marked ratified
  in a register - add a new entry noting supersession (see
  [`status-lifecycle.md#superseded`](status-lifecycle.md)), the same rule
  that applies to any other artifact.

### `claim_register`
<!-- Added 2026-07-15 (takeover review, NEW-CORRECTION): the public claims
ledger (docs/product/claims-evidence.md) was mistyped as decision_register.
Claims are not decisions: a decision register tracks what was decided
(Ratified/Provisional/Open); a claim register tracks public-facing claims
and how strongly evidence supports each (OBSERVED/UNVERIFIED/NOT TESTED).
Reusing decision_register would have been choosing a type because it passed
the schema, not because it modeled the artifact honestly. -->
A maintained index of public-facing **claims** (for README, website,
article, portfolio, talk), where **each claim carries its own evidence
status** (OBSERVED / UNVERIFIED / NOT TESTED) and the register document's own
`status` describes whether the register accurately reflects reality - not
whether every claim is proven.
- **Example:** [`../../docs/product/claims-evidence.md`](../../docs/product/claims-evidence.md)
  - `status: validated` means "this table accurately reflects each claim's
  evidence status," not "every claim is OBSERVED."
- **vs. `decision_register`:** same "many independently-statused entries in
  one document" shape, but the axis is *evidence strength of a claim*, not
  *ratification state of a decision*. A claim only becomes OBSERVED when the
  register names reproducible evidence for it.
- Like `decision_register` and `analysis_digest`, it holds multiple entries,
  so it takes no single frontmatter `evidence` label - see
  [Evidence is not always one label per artifact](#evidence-is-not-always-one-label-per-artifact).

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
A background premise you're operating on that hasn't been checked -
usually embedded as a stated caveat within other work (a plan, a fact, a
decision), not something you're actively running an experiment to
resolve.
- **Example:** "ASSUMED: the upstream API returns JSON, not checked yet."
- **vs. `fact`:** an assumption requires confirmation before it can be
  relied on.
- **vs. `hypothesis`:** an assumption is a passive caveat you flag and
  eventually check "when it becomes relevant"; a hypothesis (below) is an
  active claim with a specific, planned validation step. If you're about
  to design a test or seek specific evidence to confirm or disprove a
  claim, it's a hypothesis, not an assumption.
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
- **Evidence labeling is per-claim, inside the document, not one
  frontmatter field** - see
  [Evidence is not always one label per artifact](#evidence-is-not-always-one-label-per-artifact)
  below; this type is the reason that section exists.

### `open_question`
An open question needing an answer - blocking or non-blocking.
- **Where:** `docs/knowledge/open-questions.md`

### `hypothesis`
An active claim under investigation, with a specific planned validation
step (a test to run, evidence to seek) - not yet confirmed or disproven.
<!-- Revised 2026-07-15 (review round 2): `hypothesis` was described in
prose but missing from the machine-readable `type` enum below and from
core/schemas/knowledge-frontmatter.schema.json - status-lifecycle.md's
`rejected` state referenced "hypotheses" as if the type existed in the
schema when it didn't. Both are fixed now; this is the type `rejected`
is scoped to. -->
- **Important:** a hypothesis never becomes a `rule` or `fact` without
  validation.
- **vs. `assumption`:** see [`assumption`](#assumption) above - a
  hypothesis has an active validation plan, an assumption is a passive
  caveat.
- **Lifecycle:** `status: draft` (hypothesis proposed), then one of two
  outcomes - **confirmed:** create a *new* `fact`/`rule`/`decision`
  artifact with `status: validated` capturing the confirmed claim, and set
  the original hypothesis artifact's own `status` to `superseded` with
  `superseded_by` pointing at that new artifact (the hypothesis artifact
  keeps `type: hypothesis` - it never mutates into a fact/rule/decision in
  place, a new artifact is created); **or disproven:** set `status:
  rejected` directly on the hypothesis artifact itself, `type` stays
  `hypothesis`, recorded as a rejected hypothesis - see
  [`status-lifecycle.md#rejected-type-hypothesis-only`](status-lifecycle.md#rejected-type-hypothesis-only).

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

## Evidence is not always one label per artifact

<!-- Revised 2026-07-15 (review round 2): the frontmatter `evidence` field
is a single OBSERVED/INFERRED/ASSUMED value, which is correct for a
single-claim artifact (a fact, a rule, a hypothesis) but wrong for
`analysis_digest`, whose entire purpose is to hold multiple claims with
*different* evidence labels in the same document. A single frontmatter
`evidence` value on that type would misrepresent every claim that doesn't
match it. -->

The frontmatter `evidence` field makes sense for **single-claim types**:
`fact`, `rule`, `decision`, `risk`, `edge_case`, `failure_pattern`,
`incident`, `assumption`, `hypothesis`. Each of these is, by definition,
one claim - one epistemic label is correct.

It does **not** make sense the same way for:

- `analysis_digest` - explicitly holds multiple claims, each with its own
  label, inline in the document body (see the canonical example below).
  Leave the frontmatter `evidence` field absent, or use it only to
  characterize the digest's own top-level conclusion if it has one - never
  as a claim that every line in the digest shares that label.
- `source_manifest`, `extraction_manifest` - these record provenance
  (what was received, what was transformed), not an epistemic claim about
  system behavior. `evidence` doesn't apply; omit it.
- `playbook`, `knowledge_operation`, `open_question`, `ontology` -
  procedural or meta content, not itself a claim. `evidence` doesn't
  apply; omit it.
- `decision_register` - holds multiple `decision` entries, each with its
  own status (see [`decision_register`](#decision_register) above);
  `evidence` doesn't apply to the register as a whole, omit it.
- `claim_register` - holds multiple public claims, each with its own
  evidence status (see [`claim_register`](#claim_register) above); the
  register as a whole takes no single `evidence` label, omit it.

See [`core/schemas/knowledge-frontmatter.schema.json`](../schemas/knowledge-frontmatter.schema.json)
for the machine-enforced version of this rule: `evidence` is required only
for single-claim types once `status` is not `draft`.

## Status, confidence, evidence, and applicability are not the same thing

Four different questions, easy to conflate into one "how much do I trust
this" feeling:

| Field | Question it answers |
|---|---|
| `status` | Is this artifact even current (not superseded/deprecated)? |
| `confidence` | How strong was the evidence *when this was validated*? |
| `evidence` | What kind of evidence is this (OBSERVED/INFERRED/ASSUMED)? |
| `environment` / `source_version` / `applies_to` | Where does this claim actually apply? |
| `review_after` | Is this claim stale, independent of how strong it was originally? |

A `status: validated`, `confidence: high`, `evidence: OBSERVED` fact about
one `environment`/`source_version` can still be the wrong thing to cite for
a different environment or version, and can still be stale if
`review_after` has passed. None of these fields substitutes for the
others - see
[`confidence-levels.md#what-confidence-is-not`](confidence-levels.md#what-confidence-is-not).

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

<!-- Revised 2026-07-15 (review round 2): applies_to was listed here as a
project-local extension example, then separately promoted to a standard
optional framework field above - fixed to not contradict itself. -->

A project instance may add extra folders or metadata fields if they are
documented in that project's own persistent agent-instruction file or
knowledge index. Approved optional examples: `rules/`, `retros/`,
`registry/`. Extensions do not become mandatory framework-wide without a
separate, explicit approval. (`environment`, `source_version`, and
`applies_to` are standard optional framework fields, not local extensions
- see [Knowledge-artifact metadata](#knowledge-artifact-metadata) above.)

## Knowledge-artifact metadata

<!-- Revised 2026-07-15 (review round 2): added `hypothesis` to `type`
(was prose-only, see the `hypothesis` section above); tightened `rejected`
to require `type: hypothesis` (was described as "hypotheses-only" without
a machine-checkable condition); replaced the private-instance-shaped
`source` channel list (`code_review`, `test_failure`, `deployment`,
`vendor_docs`) with framework-generic evidence channels aligned to the
authority-model axes; made `evidence` conditionally required only for
single-claim types (see "Evidence is not always one label per artifact"
above) instead of unconditionally on any non-draft artifact.
A machine-readable version of this schema lives in
core/schemas/knowledge-frontmatter.schema.json - it is the enforced
source; this block is the explained one. Keep both in sync. -->

```yaml
---
type: fact | rule | decision | risk | edge_case | failure_pattern | incident | assumption | hypothesis | playbook | knowledge_operation | source_manifest | extraction_manifest | analysis_digest | open_question | ontology | decision_register | claim_register
status: draft | validated | superseded | deprecated | rejected  # rejected requires type: hypothesis, see status-lifecycle.md
evidence: OBSERVED | INFERRED | ASSUMED  # epistemic label - see authority-model.md. Required once status is not draft, for single-claim types only (fact, rule, decision, risk, edge_case, failure_pattern, incident, assumption, hypothesis). Not applicable to analysis_digest, source_manifest, extraction_manifest, playbook, knowledge_operation, open_question, ontology, decision_register, claim_register - omit there.
source: chat | code | test | runtime_trace | official_specification | owner_decision | ci_evidence | customer_feedback | retro  # evidence channel, distinct from `evidence` (the epistemic label)
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

# Required when status is superseded/deprecated - see status-lifecycle.md.
superseded_by: path/to/new.md
deprecated_reason: string
replaced_by: path/to/replacement.md

related:
  - path/to/related.md
---
```

### `source` channel meanings

| Channel | Maps to (authority-model axis) |
|---|---|
| `code` | Verified/audited code - axis B |
| `test` | Reproducible automated test result - axis B |
| `runtime_trace` | Production/staging observation - axis B |
| `official_specification` | Vendor docs, accepted spec/contract - axis A |
| `owner_decision` | A ratified decision record - axis A |
| `ci_evidence` | CI check output (this framework's own gates) - axis B |
| `customer_feedback` | Stakeholder-confirmed behavior - axis A |
| `chat` | Chat-reported, unverified until cross-checked - axis B, weakest tier |
| `retro` | Retrospective synthesis - usually references other channels |
