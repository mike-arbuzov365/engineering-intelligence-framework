---
type: playbook
status: validated
scope: framework
confidence: high
created: 2026-07-19
related:
  - idea-planning.md
  - product-requirements-planning.md
  - session-preparation.md
  - execution-packet-planning.md
  - knowledge-search.md
---

# Playbook: Engineering Intelligence Operating Protocol

<!-- Knowledge source: GENERALIZE of the private EI's
engineering-intelligence-operating-protocol.md. This version is
deliberately an index/entry-point, not a restatement - the three-layer
model, authority model, and experience retrieval it used to explain
inline now have their own canonical explanation in
docs/architecture/HOW-EIF-WORKS.md, so this playbook links to that
instead of duplicating it (D-007: one canonical source per concept).
Dropped: the private WikiLM/project-graph-specific activation gate and
routing detail - the equivalent optional integration contract (Graphify)
is a separate, explicit, removable contract, not a mandatory protocol
step; see the optional-integrations section of
docs/architecture/HOW-EIF-WORKS.md once that contract lands. -->

The entry point for agent-assisted work under this framework: first choose the
smallest safe path, then read only the process and knowledge that path needs.

## When this applies

Any task where an agent will change project artifacts, decisions or durable
documentation under a project instance that has adopted this framework. A
light task still uses the active profile, relevant project memory and a real
result check, but it does not need a planning or closeout file.

## Read this first

[`docs/architecture/HOW-EIF-WORKS.md`](../docs/architecture/HOW-EIF-WORKS.md)
for the concepts this protocol assumes: the three-layer context model,
the authority model, experience retrieval, and Knowledge Delta. This
playbook is the procedural index over those concepts, not a second copy
of them.

## Routing checkpoint

Classify the work before acting; the classification itself does not need a file:

- **Idea** - the problem, user, value or minimum useful scope is not yet a
  durable approved artifact.
- **PRD** - the idea is approved, but required behavior, quality
  constraints or acceptance evidence still need definition.
- **Light task** - one bounded action with clear requirements and approval,
  low risk and an obvious result check.
- **Structured single task** - one session, but scope, decisions or
  verification need to be recorded in a task-scope file.
- **Execution packet** - 2+ sessions, an architectural decision, factual
  conflicts to resolve first, or a request for unattended autonomous
  execution.

Record the classification before implementation starts, not after.

## Skill routing

| Situation | Use |
|---|---|
| Raw request or opportunity needs definition | [`idea-planning.md`](idea-planning.md) |
| Approved idea needs requirements | [`product-requirements-planning.md`](product-requirements-planning.md) |
| Choosing light, structured or packet work | [`session-preparation.md`](session-preparation.md) |
| Iterative test/fix/refine work | [`bounded-evidence-loop.md`](bounded-evidence-loop.md) |
| Work needs a packet | [`execution-packet-planning.md`](execution-packet-planning.md) |
| Executing a prepared task | [`session-execution.md`](session-execution.md) |
| Executing a prepared packet | [`execution-packet-execution.md`](execution-packet-execution.md) |
| Ending any session | [`session-closeout.md`](session-closeout.md) |
| Auditing a packet claimed done | [`execution-packet-review.md`](execution-packet-review.md) |
| Finding what repeats across many sessions | [`run-retro.md`](run-retro.md) |
| Finding what in the knowledge base needs maintenance | [`knowledge-curator.md`](knowledge-curator.md) |
| Before acting on a project task | [`knowledge-search.md`](knowledge-search.md) |
| New durable knowledge surfaced | [`knowledge-ingest.md`](knowledge-ingest.md) |
| Before proposing shared-knowledge promotion | [`knowledge-lint.md`](knowledge-lint.md) |

Corresponding invokable skills live under `skills/` (see
[`skills/README.md`](../skills/README.md)) for agent adapters that support
skill invocation directly.

## Agent workflow, in order

1. Routing checkpoint (above). For a light task, use the relevant profile
   skill, retrieve only relevant project knowledge, verify the result and run
   a learning check; then stop.
2. Read the framework layer (this repository, only what's relevant), then
   the project layer (this project instance's persistent
   agent-instruction file and relevant `knowledge/`).
3. Experience retrieval preflight
   ([`knowledge-search.md`](knowledge-search.md)).
4. For structured work, execute against the task-scope or session-launch file's declared
   scope and stop conditions. If the work iterates, use a
   [Bounded Evidence Loop](bounded-evidence-loop.md): observable success,
   a real evaluator, explicit iteration and remote-run budgets, and evidence-
   based stop conditions.
5. Close out structured work ([`session-closeout.md`](session-closeout.md)), including
   Knowledge Delta.

## Optional integrations

Structural-graph search, shell-output compression, and vendor-doc lookup
tooling are optional, removable integrations with their own
version/health/degraded-mode contract - their absence must never block
core workflow above, and a misconfigured one must fail loudly rather than
silently degrade. See `docs/architecture/HOW-EIF-WORKS.md`'s optional
integrations section for the current contract of each.

## Stop conditions

Stop and get an explicit decision, rather than guessing past the
boundary, if:

- the source of truth for a requirement is genuinely ambiguous or
  contradictory;
- a change would require a rule with framework-wide effect (belongs in a
  packet's Decisions file, not an ad-hoc call);
- the only source for a claim is unverified chat memory with no way to
  check it;
- an owner-only action (visibility, release, payment, external
  communication, a destructive/irreversible operation) turns out to be
  necessary.

## Closeout

Every structured task or packet session ends with
[`session-closeout.md`](session-closeout.md). A light task performs the result
check and learning check without creating a closeout file. Every packet's final
session additionally fills
[`templates/packet-closeout.md`](../templates/packet-closeout.md).
