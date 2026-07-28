---
packet: EIF-020-private-workspace
type: charter
status: prepared
created: 2026-07-28
---

# Charter: EIF 0.2.0 private workspace scope

## Problem statement

EIF can create or adopt independent project instances and can keep a
private registry that plans and applies compatible framework updates
across them. That registry currently stores only a name and a local path.
It cannot hold reusable private rules, skills, playbooks, templates,
profiles or cross-project knowledge, and it cannot pin or verify such
artifacts inside a connected project.

Users therefore face an unsafe choice: duplicate private operating
artifacts into every project, keep using an older private framework fork,
or let projects read live files from an unpinned private checkout. None is
an adequate update and provenance model.

## Goal

Add one optional private workspace vertical slice to EIF 0.2.0. A local,
private workspace repository can govern a registry of independent EIF
projects, define reusable workspace artifacts, and materialize a
profile-selected, hashed snapshot into each connected project without
copying or forking the public framework.

Keep the public three-layer model intact by treating workspace and project
as two durable scopes inside L2.

## In scope

- Clarify the framework, workspace, project and session relationships.
- Add a ratified decision that supersedes only the path-storage part of
  D-17.
- Define versioned schemas for workspace configuration, logical project
  registry, machine-local locations, workspace profiles and workspace
  locks.
- Provide a named migration from registry schema v1 to v2.
- Add explicit local commands to create, inspect and connect a private
  workspace.
- Resolve one selected profile into a deterministic, hashed workspace
  bundle.
- Materialize that bundle into a project-owned ignored runtime directory
  while keeping its lock reviewable and committed.
- Detect drift, missing runtime, invalid overrides and incompatible
  framework/workspace versions.
- Plan and apply updates with fleet-wide preflight followed by
  per-project transactions.
- Detach a project without deleting project-owned knowledge, rules or
  skills.
- Update public architecture, lifecycle, capability and website copy
  without describing the workspace as a fourth layer.
- Cover the complete slice with synthetic local repositories on Windows
  and platform-neutral tests suitable for later release verification.

## Out of scope

- A second public or private EIF distribution.
- Git submodules, live reads from another working tree, a database, a
  daemon, a web dashboard or a GitHub App.
- Automatic remote-repository creation, visibility changes, pushes,
  releases or hosted CI runs.
- Fleet-wide atomic Git rollback. Each repository remains a separate
  transaction and review unit.
- Team RBAC beyond the Git host and filesystem permissions already in
  use.
- Automatic installation or execution of third-party skills.
- Automatic promotion from project to workspace or from workspace to the
  public framework.
- A community skill discovery service. A later read-only curator workflow
  may propose candidates with provenance, but it is not part of this
  vertical slice.
- Bulk copying of a legacy private framework. Migration classifies each
  artifact before it is moved.
- Real private-project identities, paths, customer materials or
  owner-identifying data in this public repository.
- Publishing `0.2.0`. Private canary evidence and an explicit owner release
  decision are required after this packet.

## Definition of done

- [ ] Public architecture and the website still expose three layers, with
      workspace described as an optional durable scope inside L2.
- [ ] A local command creates a private workspace repository without a
      remote, push or visibility side effect.
- [ ] Registry v2 commits logical project identity and profile selection
      while machine locations remain in a gitignored local-state file.
- [ ] Registry v1 has a named, tested, non-destructive migration.
- [ ] A connected project records public framework provenance separately
      from private workspace provenance.
- [ ] Workspace materialization is deterministic, hashed, staged and
      verified before replacement.
- [ ] Project-owned config, knowledge, rules and skills are preserved by
      connect, update and detach.
- [ ] Same-name skill or rule conflicts fail unless an explicit valid
      override declaration resolves them.
- [ ] Fleet apply preflights every selected project before its first write,
      updates one project at a time, and reports partial completion
      honestly.
- [ ] Doctor detects missing runtime, hash drift, incompatible versions,
      unresolved locations and invalid policy resolution.
- [ ] Synthetic lifecycle tests cover creation, connect, update, failure,
      rollback and detach with no private fixtures.
- [ ] Package resources are synchronized and the full local verification
      suite passes.
- [ ] Release remains local and unpublished until separate private dogfood
      and owner approval.

## Does this change something visible?

Yes. Session 006 updates the public architecture, project lifecycle,
capability matrix and site copy. The visible model remains three layers.
The change adds an optional workspace scope to the explanation of L2 and
must not imply that the capability is available before its implementation
and tests pass.
