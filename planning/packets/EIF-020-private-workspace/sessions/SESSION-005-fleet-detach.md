---
id: SESSION-005
type: session-launch
status: prepared
source_artifact: ../04-ROADMAP-020-private-workspace.md
session_context: .session-context/eif-020-session-005.md
depends_on: [SESSION-004]
---

# Session 005: Fleet plan, apply and detach

## Goal

Coordinate both provenance axes across registered projects without
claiming fleet-wide atomicity or taking ownership of project content.

## Required reading order

1. Packet files 00 through 04.
2. Sessions 001 through 004 checkpoints.
3. D-17, current fleet update code and project transaction tests.

## Experience retrieval preflight

Search for fleet preflight, partial completion, dirty-target and uninstall
lessons.

## Scope

Plan, apply, status output, detach and multi-project synthetic tests.

## Out of scope / do not touch

No Git operations across project histories, real private projects or
remote actions.

## Verification

```text
python scripts/tests/test_workspace_fleet.py
python scripts/tests/test_project_commands.py
python scripts/tests/test_journey.py
```

## Bounded loop contract

- `success_evidence`: no project changes when preflight fails, partial
  apply reports exact sets, and detach preserves project-owned files
  byte-for-byte.
- `evaluator`: focused tests above.
- `max_iterations`: 5.
- `remote_run_budget`: 0.
- Stop if an update would require rewriting project history.

## Exit criteria

- [ ] Plan compares framework and workspace targets independently.
- [ ] Apply stops on first failure and reports completed/untouched sets.
- [ ] Detach removes only managed workspace artifacts.

## Closeout / Knowledge Delta

Record failure semantics, recovery path and detach guarantees.
