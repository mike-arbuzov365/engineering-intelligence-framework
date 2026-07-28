---
packet: EIF-020-private-workspace
type: closeout
status: complete-local
created: 2026-07-28
completed: 2026-07-28
---

# Closeout: EIF 0.2.0 private workspace scope

## Final status

`complete-local`

- Final branch/SHA: `wm/v0.2.0-private-workspace` /
  `89650da5a88e4dfa4b4d10a8f858f5359704c9a2` before this closeout commit.
- PR/merge URL: not created inside the packet. Remote publication is a
  separately authorized follow-on action.

## Plan vs. done

| Session | Planned result | Actual result | Evidence | Residual |
|---|---|---|---|---|
| 001 | Architecture and public decision | Complete | Ratified D-18; workspace is optional L2 scope, not a fourth layer or private framework fork | None |
| 002 | Schemas and migration | Complete | Registry v2, workspace schemas, deterministic v1 migration and schema tests | Real legacy migration remains follow-on |
| 003 | Workspace lifecycle commands | Complete | `workspace new` and `workspace doctor`; CLI now exposes 11 commands | Remote repository creation is not claimed |
| 004 | Resolution and materialization | Complete | Profile resolution, content-addressed workspace snapshot and lock verification | Live workspace consumption is intentionally rejected |
| 005 | Fleet plan/apply/detach | Complete | Two-axis plan/apply/status/detach; fleet 16/16, project commands 29/29, journey 273/273 | Fleet-wide atomicity is not claimed |
| 006 | Docs, site and package | Complete | Installed-wheel workspace lifecycle 75/75; site gate, 83 E2E, 3 accessibility checks, Lighthouse 100/100/100/100 | Real private dogfood not performed |
| 007 | Local release verification | Complete | Full local suite 30/30 and 1534/1534; final package build/install PASS | Optional Docker canary unavailable locally |

## Verification

| Command | Result | Evidence |
|---|---|---|
| `python scripts/tests/run_all.py` | pass | 30/30 suites, 1534/1534 checks |
| `python scripts/eif_privacy_scan.py` | pass | 0 findings |
| `python scripts/eif_check_links.py` | pass | All relative links resolve |
| `python scripts/eif_check_licenses.py --framework-root .` | pass | 19 packages OK |
| `python scripts/sync_package_sources.py --check` | pass | 145 bundled copies match |
| `python scripts/eif_release.py --require-final-version` | pass | 0.2.0 wheel and sdist built, metadata-checked and clean-installed |
| `git diff --check` | pass | No whitespace errors |
| `git status --short` | pass | Clean candidate tree |

## Not done / deferred

- Legacy private-instance migration.
- Real private-repository dogfood.
- Optional already-local container canary, because the Docker daemon was not
  available. No image was pulled.
- Push, tag, release and hosted CI did not occur inside the packet. The owner
  authorized them as the next action after closeout.
- Exhaustive hosted `release-check` is deferred until 2026-08-01. It remains
  manual-only, so push, PR and tag cannot start it implicitly.
- Community skill research workflow.

## Knowledge Delta

- A private workspace belongs inside L2 as a user-owned control scope. It does
  not create a fourth EIF layer and does not copy or fork the public
  framework.
- A project pins two independent inputs: the public framework runtime and a
  selected private workspace runtime. Both are materialized and hash-verified.
- The logical registry stores portable repository identity and policy, while
  machine-specific checkout paths stay in local state.
- Fleet changes are explicit `plan` then `apply` operations. A detached project
  keeps its public EIF runtime and removes only workspace-managed state.
- A workspace source must be committed before materialization. This prevents a
  project from pinning unreviewed local edits.
- Dry-run and plan paths must not create bytecode or other state.

## Next action

Publish through the protected PR path authorized by the owner. Allow only the
normal lightweight PR and Pages workflows; do not dispatch the exhaustive
manual `release-check` before 2026-08-01. Then create a private dogfood packet
using generic target labels in this public repository. Run the lower-risk
communication canary first and the product-site canary second. Record any
legacy private-instance migration as a separate bounded packet.
