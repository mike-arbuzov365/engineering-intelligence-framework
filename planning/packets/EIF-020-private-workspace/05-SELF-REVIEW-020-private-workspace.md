---
packet: EIF-020-private-workspace
type: self-review
status: passed
created: 2026-07-28
---

# Self-review: EIF 0.2.0 private workspace scope

## Anatomy

- [x] Charter states problem, goal, in/out of scope and boolean DoD.
- [x] Facts distinguish `OBSERVED`, `INFERRED` and `ASSUMED` and give an
      evidence cutoff.
- [x] Every DoD item maps to at least one roadmap session.
- [x] Visibility changes, external commitments and paid or irreversible
      actions are explicitly out of scope.

## Decisions

- [x] Every roadmap step that could otherwise require a routine question
      has a ratified decision or least-risk default.
- [x] Every ratified decision states evidence and rejects a concrete
      alternative where relevant.
- [x] D-17 is not silently contradicted. Session 001 must add an explicit
      partial supersession for registry path storage.

## Carry-over gate

- [x] Every item from the user-provided prior plan has a disposition.
- [x] Real private canaries are retained as a required release gate rather
      than silently dropped.
- [x] Legacy private-instance migration is classified, not treated as a
      bulk copy.
- [x] Periodic community skill research is explicitly re-deferred.

## Safety and scope

- [x] The public packet contains no real private repository name, path,
      customer material or owner-specific profile.
- [x] Remote repository creation, push, tag, release and hosted CI are out
      of scope.
- [x] Existing user branches and uncommitted work are read-only evidence,
      never a reset target.
- [x] Materialized agent instructions are treated as a trust boundary:
      provenance, hashes, conflict checks and rollback are not simplified
      away.
- [x] Detach preserves all project-owned durable content.

## Minimum-sufficient-change review

- [x] Reuses current package, registry, lock, runtime and transaction
      primitives.
- [x] Does not add a database, daemon, dashboard, GitHub App, submodule or
      private package index.
- [x] Uses `eifctl workspace` only for workspace creation and verification,
      while extending existing `eifctl projects` lifecycle commands.
- [x] Removes a workspace publication command from 0.2.0 because existing
      Git host tooling covers the external action.
- [x] Ships schemas and a minimal example, not user-specific profiles.
- [x] Keeps community skill discovery outside the vertical slice.

## Website consistency review

- [x] The site remains a three-layer explanation.
- [x] Workspace is represented as a scope or bracket across projects, not
      as another ring between framework and project.
- [x] Public copy changes only after runtime behavior is available and
      tested.

## Verdict

**PASS WITH NOTES.** The packet is ready for a future explicit execution
request. It must stop after local release-candidate verification. Real
private dogfood, remote operations and release require a separate owner
instruction and private target mapping.
