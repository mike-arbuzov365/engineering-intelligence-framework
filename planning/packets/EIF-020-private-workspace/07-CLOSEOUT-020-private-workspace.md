---
packet: EIF-020-private-workspace
type: closeout
status: not-started
created: 2026-07-28
completed:
---

# Closeout: EIF 0.2.0 private workspace scope

## Final status

`not-started`

- Final branch/SHA:
- PR/merge URL:

## Plan vs. done

| Session | Planned result | Actual result | Evidence | Residual |
|---|---|---|---|---|
| 001 | Architecture and public decision | not started | | |
| 002 | Schemas and migration | not started | | |
| 003 | Workspace lifecycle commands | not started | | |
| 004 | Resolution and materialization | not started | | |
| 005 | Fleet plan/apply/detach | not started | | |
| 006 | Docs, site and package | not started | | |
| 007 | Local release verification | not started | | |

## Verification

| Command | Result | Evidence |
|---|---|---|
| `python scripts/tests/run_all.py` | not run | |
| `python scripts/eif_privacy_scan.py` | not run | |
| `python scripts/eif_release.py --check` | not run | |
| `git diff --check` | not run | |

## Not done / deferred

- Private real-project dogfood.
- Legacy private-instance migration.
- Push, tag, release and hosted CI.
- Community skill research workflow.

## Knowledge Delta

To be completed after Session 007.

## Next action

After local closeout, create a private dogfood packet using the workspace
registry as the target map. Run the lower-risk canary first, then the
second project type. Release only after both have evidence and the owner
approves.
