# Roadmap

Public, high-level view of where EIF is headed. For the detailed,
date-stamped history of what's already landed (with evidence links per
item), see
[`docs/architecture/HOW-EIF-WORKS.md#roadmap`](docs/architecture/HOW-EIF-WORKS.md#roadmap) -
this page summarizes the same sequence for a reader who wants the shape of
the plan without the full history.

This is a **roadmap, not a commitment with dates**. Pre-v0.1: sequencing
can change based on what each step actually finds, the same discipline
this project applies to every other claim it makes about itself - see
[`docs/product/claims-evidence.md`](docs/product/claims-evidence.md).

## Done

- Public/private security audit, legal foundation, ontology consistency,
  machine-readable schemas, decision ledger, self-governance CI.
- A vertical slice (one synthetic demo, one adapter) end to end, including
  existing-repository adoption hardening driven by a real pilot.
- Four agent adapters ported: two required for v0.1 (Claude Code, Cursor),
  two experimental-supported (Codex, Hermes) - each re-verified against
  its own primary/installed source, with a full directed switching matrix
  across all 12 ordered pairs. **Adapter scope is now frozen** at these
  four.
- Reproducible dependency/license checking - default mode reads a
  committed SBOM instead of scanning the invoking environment, confirmed
  identical on Windows and Ubuntu CI.
- An installable `eifctl` package (not yet published to a package index),
  including an installed-wheel synthetic journey and behavioral integration
  states.
- A first bounded real-agent benchmark pilot: one model, three fixtures, six
  attempts, one attempt per cell. It proves the harness/pilot, not a
  quality/token advantage.
- Optional RTK and Graphify behavioral adapters with version probes, bounded
  canaries, explicit degraded modes and local/no-paid defaults.
- A bounded evidence-loop operating contract with explicit evaluator,
  iteration/remote budgets, adaptation and closeout states.
- Public documentation reconciliation across README, architecture,
  integrations, claims and roadmap.
- A bilingual presentation site, built and gated locally: every material
  claim on it cites a manifest entry that resolves to this repository's
  claims ledger, and the build fails on an unknown claim ID, forbidden
  wording, a leaked private path or any third-party runtime request. Built,
  not hosted - see below.

## In progress

- Final local release gate and a refreshed fresh-history candidate after the
  last documentation changes.
- Owner review of launch source, repository-history choice, domain/social
  strategy and the exact candidate digest.

## Not started

- Real merge-gate/CI enforcement wired into repository settings (required
  status checks, branch protection), not just present as workflow files
  re-verified by a wrapper script.
- Repeated comparative quality-per-token trials across more fixtures/models.
  Modes C/D remain blocked until a real agent runner consumes Graphify
  evidence and RTK passes the required behavioral/telemetry contract; fake
  integration results are not accepted.
- A provider-specific vendor-documentation adapter; its generic declaration
  exists, but behavioral retrieval/health is not yet implemented.
- Broader playbook/template/skill porting - deliberately sequenced after
  the items above, and only as much as their own lessons say is actually
  needed.
- `v0.1.0` tag/release, package-index publication, website hosting,
  article/LinkedIn publication and feedback intake. These are separate
  owner-gated launch packets, not side effects of technical review. The site
  itself is built and its production URLs are configured; what remains is
  the act of serving it, which nothing in this repository performs.

## Explicit non-goals for v0.1

- Hosted SaaS or a proprietary cloud memory service.
- An autonomous multi-agent runtime that merges unchecked changes.
- A mandatory code-graph or shell-compression dependency - both optional
  integrations, always.
- Universal token-savings claims - any efficiency claim is scoped to what
  was actually measured, for the specific integration and workload that
  produced the number.

## How to read "done"

A checked item above means the described work exists and has the
evidence named in
[`docs/product/claims-evidence.md`](docs/product/claims-evidence.md) - it
does not mean "production-ready" or "complete for every adapter/platform."
That distinction matters enough that this project tracks it as a
first-class ledger rather than leaving it to prose - see that document for
exactly what's OBSERVED, UNVERIFIED, or NOT TESTED, and the allowed vs.
forbidden public wording for each claim.
