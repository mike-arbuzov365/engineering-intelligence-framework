---
type: playbook
status: validated
scope: framework
created: 2026-07-18
review_after: 2026-10-18
---

# Quickstart

Ten minutes, one synthetic task, no private repositories, no Graphify, no
RTK. This page is the short "get oriented" path; for the full walkthrough
with real captured command output, see
[`examples/demo-workspace/README.md`](../../examples/demo-workspace/README.md) -
this page doesn't duplicate that content, it summarizes it and adds a real
timing measurement.

For real private repositories, install the v0.2.2 wheel and create a
user-owned workspace with `eifctl workspace new`. That workspace is optional
L2 scope, not a private copy of EIF. The
[`project lifecycle guide`](project-lifecycle.md) covers registry v2,
machine-local paths, profiles, the two update axes, and detach.

## What you need

- Python 3.11+
- A clone of this repository (framework checkout - no installable package
  or private instance required for this walkthrough)

## The five things you'll do

1. **Initialize an instance.** `scripts/eif_init.py` generates a pinned
   `.eif/runtime/` source bundle, a `.eif/config.yaml` (user-owned) and
   `.eif/framework.lock.yaml` (EIF-managed provenance), and an agent
   entrypoint (`CLAUDE.md` by default - see
   [adapter compatibility](../reference/config.md#adapter-compatibility)
   for the other three).
2. **Retrieve knowledge before implementing.** A seeded, lifecycle-aware
   search returns validated facts and failure patterns relevant to the
   task - not the whole knowledge base, and never a `rejected` hypothesis
   by default.
3. **Implement and verify.** One real, small change, checked by a real
   test - a failing-before, passing-after transition, not just "a test
   exists."
4. **Close out truthfully.** A config-driven Knowledge Delta and session
   closeout, written to real files (not printed to stdout and discarded),
   in whatever locale the instance declares.
5. **Validate the instance from its own bundle.** Schema validation,
   privacy scan, link check - all runnable with no framework checkout
   present, from the instance's pinned `.eif/runtime/` alone.

See [`examples/demo-workspace/README.md`](../../examples/demo-workspace/README.md)
for the exact command for each step and real, captured output from an
actual run.

## How long this actually takes

Two different numbers, deliberately not conflated:

- **Mechanical execution**: running the full sequence above (init,
  retrieval, the demo's test suite, both renders, and all five validation
  checks, including staging the generated files so the privacy scan's
  `git ls-files`-based check actually sees them - what a real user would
  naturally do before a commit) as a scripted, back-to-back run measured
  **6.3-7.0 seconds** wall clock across three separate runs (average
  ~6.6s), end to end, on the machine this was measured on. Commands are
  fast; nothing here is computationally heavy. Reported as a range from
  repeated runs, not a single-run figure - an earlier single measurement
  (5.7s) omitted the staging step and is superseded by this one.
- **Reading, typing, and understanding time** - the number a "10-minute
  quickstart" claim is actually about - has **not** been independently
  timed by a human working through this page for the first time. Treat
  "10 minutes" as this project's own estimate, not a verified claim - see
  [`docs/product/claims-evidence.md`](../product/claims-evidence.md) for
  what is and is not OBSERVED.

## What this quickstart does not cover

- Adopting an existing, already-governed repository (a materially
  different, harder path - see
  [Existing-repository adoption](../architecture/instance-contract.md#adoption-existing-repositories)).
- Any adapter besides the default. `--adapter cursor`/`codex`/`hermes`
  work the same way at `eif_init` time - see
  [`adapters/README.md`](../../adapters/README.md).
- Graphify, RTK, or vendor-docs integration - all optional, all off by
  default, see [`integrations/README.md`](../../integrations/README.md).
- The installable `eifctl` package's own quickstart (same steps, different
  invocation - `eifctl init` instead of `python scripts/eif_init.py`) -
  see the root [`README.md`](../../README.md#get-started). Workspace
  creation, registration, profile materialization, multi-project updates,
  and detach are covered separately in the
  [`project lifecycle guide`](project-lifecycle.md).
