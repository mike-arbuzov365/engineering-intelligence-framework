---
type: decision
status: draft
scope: framework
created: 2026-07-15
review_after: 2026-10-15
---

# Decision ledger

<!-- Knowledge source: owner decisions, private instance, 2026-07-14/15.
Sanitized for public release - no private repository names, machine paths,
or audit specifics that would identify the private instance. -->

Public, sanitized record of decisions behind this framework's naming,
licensing, and structure. **A decision is only marked `ratified` here if it
went through an explicit owner ratification step** - a decision that was
merely *implemented* because the evidence pointed one way is marked
`provisional`, not `ratified`, even if it's already in effect. This
distinction matters: a provisional choice can be revisited without
"reversing a ratified decision"; a ratified one needs an explicit
supersession to change.

## Ratified

### D-01: Product name
**Status: ratified.** `Engineering Intelligence Framework`, short form
`EIF`.
**Evidence:** a preliminary GitHub exact-name search and a PyPI/npm web
search found no exact match for `engineering-intelligence-framework`. This
is a preliminary collision check, **not** trademark clearance - full legal
clearance is still open, tracked in the public-readiness checklist in
[`docs/architecture/HOW-EIF-WORKS.md`](../../docs/architecture/HOW-EIF-WORKS.md#definition-of-public-ready).

### D-04: License
**Status: ratified.** Apache-2.0 for v0.1, see [`LICENSE`](../../LICENSE).

## Provisional (strongly evidenced, not formally ratified)

### D-02: Descriptor
**Status: provisional.** "A quality-first control plane for governed
AI-agent software development." Adopted alongside D-01; not separately
ratified through an explicit decision step. Low risk to revisit.

### D-03: Public repository strategy
**Status: provisional, strong evidence.** Clean-room extraction into a new
repository with fresh history, rather than migrating the private
instance's history or exporting its current tree as-is.
**Evidence:** a privacy audit of the private instance's tracked files and
git history found private-repository names and owner-identifying strings
spread across more than 100 tracked files and referenced in dozens of
commits. Sanitizing that history after the fact was judged less reliable
than starting clean. This repository's own history starts from this
decision - there is nothing to migrate.
**Why still provisional:** this was a judgment call under time pressure,
not a formal ratification round with alternatives considered. It should be
explicitly ratified (or revisited) before claiming it as settled in
external-facing material (website, articles).

## Open (not yet decided)

### D-05: CLI name
**Status: open.** No CLI exists yet (`scripts/README.md`,
`docs/guides/`). A name should be chosen alongside the first working
bootstrap implementation, not before.

### D-06/D-07: Canonical language / non-English locale timing
**Status: open.** Current documents assume English-canonical framework
docs with a config-driven project locale (see
[`.eif/config.yaml.example`](../../.eif/config.yaml.example) and
[`locales/README.md`](../../locales/README.md)) as a *design default*, not
a ratified decision. Whether a Ukrainian locale pack ships in v0.1 or
later is open.

### D-08: Public/private dependency model
**Status: open.** How a project instance actually consumes the framework
(git submodule, vendored bundle, package/CLI installer, template
repository) is undecided. `docs/architecture/HOW-EIF-WORKS.md`'s current
text should not be read as having settled this.

### D-09: Required v0.1 adapters
**Status: open, recommendation exists.** See
[`adapters/README.md`](../../adapters/README.md#recommended-v01-priority)
for an evidence-based recommendation (Claude Code, then Cursor) based on
hook-reliability testing done while building this repository. Not yet
ratified.

### D-10: Are structural-graph / shell-compression integrations in the official v0.1 integration catalog?
**Status: open, design default exists.** Current documents treat them as
optional, non-core capabilities (see
[`integrations/README.md`](../../integrations/README.md)) - this is the
working assumption, not a ratified decision.

### D-11: Website timing
**Status: open.** Not started. Should follow, not precede, a working
vertical slice and a real benchmark - see
[`docs/guides/vertical-slice.md`](../../docs/guides/vertical-slice.md).

### D-12: Benchmark publication scope
**Status: open.** No benchmark has been run - see
[`docs/benchmarks/README.md`](../../docs/benchmarks/README.md). Which
repositories/tasks can safely be used (without leaking private data) is
undecided.

## How to ratify a decision

Update this file: move the entry from `Open`/`Provisional` to `Ratified`,
record the evidence, and set `status: validated` in this file's own
frontmatter once at least one decision below moves. Do not silently change
a decision already marked `ratified` here - add a new entry noting
supersession, with rationale, per
[`core/ontology/status-lifecycle.md`](../ontology/status-lifecycle.md#superseded).
