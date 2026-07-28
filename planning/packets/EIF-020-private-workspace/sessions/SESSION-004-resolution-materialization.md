---
id: SESSION-004
type: session-launch
status: prepared
source_artifact: ../04-ROADMAP-020-private-workspace.md
session_context: .session-context/eif-020-session-004.md
depends_on: [SESSION-003]
---

# Session 004: Resolution and materialization

## Goal

Resolve selected workspace artifacts deterministically and install a
verified snapshot without overwriting project-owned content.

## Required reading order

1. Packet files 00 through 04.
2. Sessions 001 through 003 checkpoints.
3. Current runtime manifest, transaction and doctor implementations.

## Experience retrieval preflight

Search for hash drift, transaction rollback, managed blocks and override
conflicts.

## Scope

Profile resolver, policy modes, override validation, workspace lock,
runtime materialization, doctor checks and fault-injection tests.

## Out of scope / do not touch

No multi-project apply, public site claims or third-party skill install.

## Verification

```text
python scripts/tests/test_workspace_resolution.py
python scripts/tests/test_workspace_transaction.py
python scripts/tests/test_workspace_commands.py
```

## Bounded loop contract

- `success_evidence`: deterministic hash across repeated clean runs,
  distinct doctor results for each drift class, byte-exact rollback after
  every injected failure.
- `evaluator`: focused tests above.
- `max_iterations`: 5.
- `remote_run_budget`: 0.
- Stop if project-owned files cannot be separated from managed output.

## Exit criteria

- [ ] Runtime and lock contain no path or credential.
- [ ] Same-name collisions require explicit valid override metadata.
- [ ] Failed materialization preserves the prior working project.

## Closeout / Knowledge Delta

Record resolution precedence, trust-boundary checks and transaction
evidence.
