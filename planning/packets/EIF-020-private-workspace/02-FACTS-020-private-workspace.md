---
packet: EIF-020-private-workspace
type: facts
status: validated
evidence_cutoff: 2026-07-28
---

# Facts: EIF 0.2.0 private workspace scope

## Evidence boundary

Checked on 2026-07-28:

- `core/policies/decisions.md`, especially D-05/D-08 and D-17;
- `docs/architecture/HOW-EIF-WORKS.md`;
- `docs/architecture/instance-contract.md`;
- `docs/guides/project-lifecycle.md`;
- `core/schemas/project-registry.schema.json`;
- `src/engineering_intelligence_framework/cli.py`;
- `src/engineering_intelligence_framework/commands/projects.py`;
- current site DOM at the local development URL;
- existing public EIF skills, playbooks, templates and tests;
- sanitized private-instance planning workflows as migration evidence only;
- the user-provided carry-over note dated 2026-07-28;
- primary public sources for Ponytail, Vercel Skills and Microsoft APM.

No Graphify data was used. No private repository content is a source of
public facts beyond the sanitized workflow gap already described in this
packet.

## Current state

| Area | State | Evidence |
|---|---|---|
| Public framework | `OBSERVED`: the installable public package is canonical and project instances should not fork it | D-05/D-08, D-17, `HOW-EIF-WORKS.md` |
| Three-layer model | `OBSERVED`: L1 is framework, L2 is one project or a set of related projects, L3 is session | `HOW-EIF-WORKS.md` |
| Website | `OBSERVED`: the visible site presents L1 framework, L2 project and L3 session; it does not show a private workspace | local site DOM |
| Project lifecycle | `OBSERVED`: `eifctl new` creates a local Git repository and `eifctl init` adopts an existing one | D-17, CLI source, lifecycle guide |
| Registry | `OBSERVED`: schema v1 requires `name` and `path` in the same committed entry | `project-registry.schema.json` |
| Fleet updates | `OBSERVED`: `eifctl projects upgrade` preflights all projects, then applies sequentially and stops on first failure | `commands/projects.py` |
| Framework provenance | `OBSERVED`: each project has a committed framework lock and ignored hashed runtime bundle | `instance-contract.md` |
| Workspace provenance | `OBSERVED`: no workspace config, profile, lock, bundle or verifier exists | repository source search and CLI command table |
| Compatibility | `OBSERVED`: no general automatic cross-version config migration exists; the first breaking shape change requires a named migration | `instance-contract.md` |
| CLI surface | `OBSERVED`: the CLI has ten commands and no `workspace` command group | `cli.py` |
| Package install | `OBSERVED`: installation and project creation are separate explicit operations | package and CLI source |
| Planning gap | `OBSERVED`: public EIF lacks a complete private reusable scope between the framework release and independent projects | schema, commands and documentation above |
| External design pattern | `OBSERVED`: Vercel Skills distinguishes project and global installation scopes | public repository documentation |
| External provenance pattern | `OBSERVED`: Microsoft APM uses a manifest and lockfile with resolved-source and content-hash provenance | public repository documentation |
| Minimum-change check | `OBSERVED`: Ponytail recommends understanding the actual flow, reusing existing mechanisms, and not simplifying away trust-boundary validation, data-loss protection or security | public `ponytail` skill |
| Required private dogfood | `ASSUMED`: two owner-selected private project types remain the intended canary sequence | user carry-over; exact identities must be re-verified in a private workspace before execution |

## Gaps

1. The architecture does not name workspace scope or its boundary with
   project scope.
2. The registry mixes logical fleet identity with machine-specific paths.
3. There is no workspace configuration, profile or lock schema.
4. There is no explicit local workspace creation command.
5. There is no deterministic workspace bundle resolver.
6. Projects cannot verify private workspace provenance or runtime drift.
7. There is no conflict contract for project and workspace artifacts with
   the same name.
8. Fleet planning compares only public framework provenance.
9. There is no detach workflow for workspace-managed artifacts.
10. There is no named migration from registry schema v1.
11. Public documentation and the site cannot explain a feature that does
    not yet exist.
12. No synthetic lifecycle test proves the complete workspace flow.

## Carry-over ledger

| Prior item | Disposition | Destination |
|---|---|---|
| Public EIF remains canonical | in scope | Decisions D-002; Sessions 001 and 006 |
| Private reusable rules, skills, playbooks, templates and knowledge | in scope | Decisions D-005 through D-008; Sessions 002 and 004 |
| User-wide profiles | in scope, generic schema only | Sessions 002 and 004 |
| Multi-machine location model | in scope | Decision D-004; Session 002 |
| Separate workspace lock and runtime | in scope | Decisions D-005 and D-006; Sessions 002 and 004 |
| Promotion `project -> workspace -> framework` | in scope as an explicit governance contract, not automation | Session 001 |
| Command that creates the workspace repository | in scope, local only | Decision D-003; Session 003 |
| GitHub remote creation and `control publish` | rejected for 0.2.0 | Decision D-003; existing Git tooling already covers it and the side effect is not core EIF behavior |
| Required/default/optional policy modes | in scope | Decision D-007; Sessions 002 and 004 |
| Explicit same-name overrides | in scope | Decision D-008; Session 004 |
| Public schemas cannot be silently overridden | in scope | Decision D-008; Session 004 |
| Fleet preflight and per-project transaction | in scope | Decision D-010; Session 005 |
| Canary private project A, then private project B | re-deferred as a mandatory post-packet release gate | Session 007 closeout and a private follow-on packet |
| Legacy private-instance migration ledger | in scope as a template and contract; real content remains private | Decision D-012; Sessions 003 and 006 |
| Old private instance becomes a read-only archive after accepted migration | re-deferred to private follow-on packet | Session 007 closeout |
| Ponytail minimum-sufficient-change gate | in scope as self-review, no vendoring | Decision D-015; every session |
| Periodic community skill research and improvement proposals | re-deferred | Decision D-014; later read-only curator workflow |
| Automatic third-party skill installation | rejected | Charter out of scope; Decision D-014 |
| Database, daemon, dashboard, GitHub App and submodules | rejected | Charter out of scope; Decision D-015 |
| Hosted CI conservation | in scope | Roadmap global constraints; Session 007 |
