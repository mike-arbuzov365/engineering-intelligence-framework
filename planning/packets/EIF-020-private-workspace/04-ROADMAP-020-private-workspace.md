---
packet: EIF-020-private-workspace
type: roadmap
status: prepared
execution: single-agent-sequential
---

# Roadmap: EIF 0.2.0 private workspace scope

## Global execution constraints

- Use one active agent, sequential sessions and no delegation.
- Start from a clean branch with the `wm/` prefix.
- Read `core/policies/decisions.md` before every methodology-affecting
  session.
- Treat this packet and fresh source/test state as authority over chat
  memory.
- Use only sanitized synthetic repositories in public tests and docs.
- Run the privacy scan before every commit that changes examples, paths or
  project lifecycle text.
- Run `scripts/sync_package_sources.py` after every change to bundled
  source trees.
- Keep remote-run budget at 0. Do not push, tag, release or trigger GitHub
  Actions while the owner conserves hosted-runner quota.
- A local commit may close each session. Do not merge into `main` inside
  this packet.
- Apply the minimum-sufficient-change gate without removing security,
  validation, rollback or accessibility requirements.

## Session 001 - Architecture and public decision

1. Re-verify D-17, the three-layer model, site copy and current capability
   claims.
2. Add a ratified public decision defining private workspace scope inside
   L2 and superseding only D-17's path-storage rule.
3. Update the architecture contract with scope boundaries, promotion
   rules and terminology.
4. Add architecture tests that fail if public sources describe workspace
   as a fourth layer or second framework distribution.

Verification:

```text
python scripts/eif_check_links.py
python scripts/eif_privacy_scan.py
python scripts/tests/test_operating_layer.py
```

Exit: public source defines the workspace boundary without claiming an
unimplemented CLI capability or changing the three-layer count.

## Session 002 - Schemas and migrations

1. Define workspace config, registry v2, local project locations, profile
   and workspace lock schemas.
2. Keep logical registry and local-state schemas independent.
3. Implement a named, dry-run-first registry v1 to v2 migration that
   preserves project identity and writes paths only to ignored local state.
4. Add compatibility checks and fixtures for valid, invalid and future
   schema versions.
5. Prove a failed migration leaves the prior tree byte-identical.

Verification:

```text
python scripts/tests/test_validate.py
python scripts/tests/test_project_commands.py
python scripts/tests/test_workspace_schemas.py
```

Exit: every new artifact validates, v1 migration is reversible before
commit, and machine paths are absent from committed registry v2 fixtures.

## Session 003 - Workspace creation and registry lifecycle

1. Add `eifctl workspace new` and `eifctl workspace doctor`.
2. Make `workspace new` create a local Git repository, initialize it as an
   EIF instance and write the minimal private workspace structure.
3. Exclude the workspace repository from its own registry.
4. Evolve existing `eifctl projects add` and `status` to use registry v2,
   profiles and machine-local locations. Do not add duplicate
   `workspace connect` or `workspace status` routes.
5. Add a migration-ledger template without importing any private content.
6. Prove repeated creation and connection are idempotent or fail with an
   exact recovery instruction.

Verification:

```text
python scripts/tests/test_workspace_commands.py
python scripts/eif_privacy_scan.py
python scripts/tests/smoke.py
```

Exit: a synthetic workspace and two synthetic projects can be created and
listed through `workspace` plus existing `projects` commands, with no
remote side effect and no self-registration.

## Session 004 - Profiles, resolution and hashed materialization

1. Implement deterministic profile resolution across required, default
   and optional workspace artifacts.
2. Validate explicit overrides and fail undeclared same-name collisions.
3. Stage a selected bundle, compute and verify its manifest and combined
   digest, then atomically replace `.eif/workspace-runtime/`.
4. Write `.eif/workspace.lock.yaml` with opaque workspace identity,
   revision, selected profile and hashes, but no path or credential.
5. Extend doctor to detect missing runtime, unexpected files, hash drift,
   dirty source, incompatible versions and invalid policy resolution.
6. Add fault injection for staging and replacement failure windows.

Verification:

```text
python scripts/tests/test_workspace_resolution.py
python scripts/tests/test_workspace_transaction.py
python scripts/tests/test_workspace_commands.py
```

Exit: repeated materialization is deterministic, every tested failure
restores the prior project tree, and doctor distinguishes each failure
class.

## Session 005 - Fleet plan, apply and detach

1. Extend plan output to compare framework version, workspace revision,
   profile, overrides, conflicts and migration requirements per project.
2. Preflight all selected projects before the first write.
3. Apply public framework and private workspace changes as coordinated but
   independently proven per-project transactions.
4. Stop on first failure and report completed, failed and untouched
   project sets.
5. Implement detach of workspace-managed artifacts without touching
   project-owned content.
6. Add synthetic multi-project tests for dirty targets, unresolved
   locations, partial fleet completion and detach preservation.

Verification:

```text
python scripts/tests/test_workspace_fleet.py
python scripts/tests/test_project_commands.py
python scripts/tests/test_journey.py
```

Exit: every fleet failure mode has an observable result and detach leaves
project-owned files byte-identical.

## Session 006 - Documentation, site and package surface

1. Update lifecycle, instance contract, quickstart, terminology and
   capability evidence to match tested behavior.
2. Update the site after the capability becomes available: keep three
   layers and add workspace as an optional L2 scope.
3. Document the separate public framework and private workspace update
   axes, migration ledger and private dogfood gate.
4. Synchronize bundled sources and add installed-wheel coverage for the
   workspace and extended project commands plus workspace artifacts.
5. Keep all examples synthetic and all real target identities private.

Verification:

```text
python scripts/sync_package_sources.py
python scripts/eif_check_links.py
python scripts/eif_privacy_scan.py
python scripts/tests/test_package_build.py
npm --prefix site run gate
```

Exit: public docs, site, package and tested CLI behavior agree, with no
fourth-layer language or private identifiers.

## Session 007 - Local release-candidate verification

1. Re-run the complete local suite from a clean tree.
2. Build sdist and wheel, install the wheel into a clean environment and
   run the synthetic workspace journey from installed artifacts.
3. Run a local cross-platform canary if an already available local
   container can do so without hosted CI.
4. Fill packet closeout with exact commands and residual risks.
5. Prepare a private follow-on dogfood packet with generic role labels in
   public notes; store real target mapping only in the private workspace.
6. Stop before push, tag, release, remote creation or private-repository
   mutation.

Verification:

```text
python scripts/tests/run_all.py
python scripts/eif_privacy_scan.py
python scripts/eif_release.py --require-final-version
git diff --check
git status --short
```

Exit: the local 0.2.0 candidate passes all available local gates, the
closeout states that private canary and owner release approval remain, and
no remote action occurred.

## Definition-of-done cross-check

| Definition-of-done item | Session |
|---|---|
| Three layers with workspace inside L2 | 001, 006 |
| Local workspace creation with no remote side effect | 003 |
| Registry v2 and machine-local locations | 002, 003 |
| Named registry v1 migration | 002 |
| Separate framework and workspace provenance | 002, 004 |
| Deterministic staged and verified materialization | 004 |
| Preserve project-owned content | 003, 004, 005 |
| Explicit conflict and override validation | 004 |
| Fleet preflight and sequential apply | 005 |
| Doctor failure detection | 003, 004 |
| Synthetic complete lifecycle tests | 003, 004, 005, 007 |
| Synchronized package and full local suite | 006, 007 |
| No release before private dogfood and approval | 007 |
