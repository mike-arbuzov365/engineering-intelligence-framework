---
id: SESSION-003
type: session-launch
status: prepared
source_artifact: ../04-ROADMAP-020-private-workspace.md
session_context: .session-context/eif-020-session-003.md
depends_on: [SESSION-002]
---

# Session 003: Workspace creation and registry lifecycle

## Goal

Create and connect a local private workspace through explicit,
non-destructive commands with no remote side effects.

## Required reading order

1. Packet files 00 through 04.
2. Sessions 001 and 002 checkpoints.
3. Current `new`, `init`, `projects` and `doctor` command implementations.

## Experience retrieval preflight

Search for project creation, adoption, self-registration and registry
failure lessons.

## Scope

`workspace new`, `workspace doctor`, registry-v2 extensions to existing
`projects add/status`, migration ledger template and synthetic lifecycle
tests.

## Out of scope / do not touch

No duplicate `workspace connect/status`, remote creation, push,
publication, profile materialization or fleet apply.

## Verification

```text
python scripts/tests/test_workspace_commands.py
python scripts/eif_privacy_scan.py
python scripts/tests/smoke.py
```

## Bounded loop contract

- `success_evidence`: synthetic workspace plus two projects can be
  created, connected and inspected repeatedly without remote state.
- `evaluator`: focused control-command tests.
- `max_iterations`: 5.
- `remote_run_budget`: 0.
- Stop on any destructive adoption or self-registration behavior.

## Exit criteria

- [ ] Package install remains side-effect free.
- [ ] Workspace repository is an EIF instance but not its own fleet member.
- [ ] Repeated commands are idempotent or fail with recovery guidance.

## Closeout / Knowledge Delta

Record command contracts, side-effect boundaries and any lifecycle gaps.
