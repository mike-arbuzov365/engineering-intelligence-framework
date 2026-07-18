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
- An installable `eifctl` package (not yet published to a package index).

## In progress

- Public documentation closure: this page, the quickstart, the config
  reference, and a documentation-accuracy pass across the existing docs
  set (adapter counts, roadmap staleness, and similar drift, corrected as
  found rather than assumed absent).
- An executable synthetic demo proven from the installed package (not
  just a framework checkout) on both Windows and Ubuntu.

## Not started

- Real merge-gate/CI enforcement wired into repository settings (required
  status checks, branch protection), not just present as workflow files
  re-verified by a wrapper script.
- A reproducible quality-per-token benchmark, run against the vertical
  slice, comparing baseline / EIF / EIF+Graphify / EIF+Graphify+RTK
  strategies - schema and harness exist; no run has happened yet, and the
  approval packet for a first real run (models, cost, stopping rules) is
  prepared separately from actually running it.
- Broader playbook/template/skill porting - deliberately sequenced after
  the items above, and only as much as their own lessons say is actually
  needed.
- `v0.1.0` release, package-index publication, and launch content
  (website, article, announcement).

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
