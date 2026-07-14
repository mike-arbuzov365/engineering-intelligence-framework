---
type: playbook
status: draft
scope: framework
created: 2026-07-15
review_after: 2026-10-15
---

# The v0.1 vertical slice

<!-- Knowledge source: review round 2026-07-15 - explicit instruction not
to port all private playbooks/skills at once, but to design and build the
smallest complete, testable EIF workflow first. -->

## Why a slice, not a full port

The private instance has roughly 15 playbooks and a full skill catalog.
Porting all of it before anything works end to end would produce a large,
untestable surface area and repeat the exact mistake this review round
found in the v0.1 skeleton itself: content that describes target design
dressed up as current capability. One small, real, working path beats a
large skeleton of "not built yet" stubs.

## The slice

A single synthetic demo repository (`examples/demo-workspace/`, not built
yet) walks through, start to finish:

1. **Initialize a project instance.** Produce a real `.eif/config.yaml`
   from `.eif/config.yaml.example`, validated against
   `core/schemas/eif-config.schema.json`.
2. **Generate compact agent instructions.** A minimal `AGENTS.md`/
   `CLAUDE.md`-equivalent for the demo repo, in the style of this
   repository's own [`AGENTS.md`](../../AGENTS.md) - short, pointing to
   detail rather than duplicating it.
3. **Create a knowledge index.** A handful of seeded knowledge artifacts
   (2-3 facts, 1 rule, 1 decision) in the demo repo, each passing
   `eif_validate_frontmatter.py`.
4. **Retrieve one relevant prior lesson.** Before the "controlled task"
   step below, demonstrate a real search over the seeded index that
   surfaces a specific, relevant artifact - not a hardcoded example.
5. **Run one controlled task.** A small, real code change in the demo
   repo (not a no-op), scoped and executed by one of the two priority
   adapters (see [`adapters/README.md`](../../adapters/README.md#recommended-v01-priority)).
6. **Verify behavior.** A test in the demo repo actually runs and passes -
   not a claim of passing.
7. **Create a Knowledge Delta.** Following the PR template's Knowledge
   Delta section, for the change made in step 5.
8. **Validate the instance.** Run `eif_privacy_scan.py`,
   `eif_validate_frontmatter.py`, and `eif_check_links.py` against the
   demo repo - all pass.
9. **Close the session.** A short closeout note distinguishing what was
   done from what was planned - honestly, including anything that didn't
   work.

## What's deliberately excluded from the slice

- Structural-graph and shell-output-compression integrations - the slice
  must work in fully degraded mode first (see
  [`docs/architecture/HOW-EIF-WORKS.md#degraded-modes`](../architecture/HOW-EIF-WORKS.md#degraded-modes)).
  Adding either integration is a follow-up slice, not part of this one.
- A second adapter - ship the slice against the single highest-reliability
  adapter first (Claude Code, per current evidence), then repeat against
  the second (Cursor) to prove the framework/adapter boundary actually
  holds, rather than building both simultaneously.
- Any playbook or skill not directly needed for steps 1-9 above.

## Definition of done for this slice

- [ ] `examples/demo-workspace/` exists, is fully synthetic, and passes
      `eif_privacy_scan.py` with zero findings.
- [ ] Steps 1-9 above are each backed by a real, runnable command or file,
      not prose describing what they would do.
- [ ] A second person (or the same agent, in a fresh session with no
      memory of building it) can follow the demo README and reproduce the
      same result.
- [ ] The demo's Knowledge Delta and closeout are reviewed against
      [`core/ontology/knowledge-types.md`](../../core/ontology/knowledge-types.md)
      for type/status/evidence correctness - this is the first real test
      of whether the revised ontology (see
      [`core/ontology/authority-model.md`](../../core/ontology/authority-model.md))
      is actually usable in practice, not just internally consistent on
      paper.

## Sequencing

This guide's existence, and the ontology/schema/CI work in this same
review round, are prerequisites for the slice - not the slice itself. The
next session that picks this up should build the slice, not add more
scaffolding.
