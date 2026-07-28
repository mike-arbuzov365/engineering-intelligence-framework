---
id: SESSION-002
type: session-launch
status: prepared
source_artifact: ../04-ROADMAP-020-private-workspace.md
session_context: .session-context/eif-020-session-002.md
depends_on: [SESSION-001]
---

# Session 002: Schemas and migrations

## Goal

Define the public data contracts and a safe registry v1 migration before
building commands on top of them.

## Required reading order

1. Packet files 00 through 04.
2. Session 001 checkpoint.
3. Existing schemas, validation code, registry command and instance
   transaction tests.

## Experience retrieval preflight

Search for prior schema migration, lock, path and rollback decisions.

## Scope

Schemas, migration code, synthetic fixtures and focused tests.

## Out of scope / do not touch

Do not add final control CLI UX or website availability claims.

## Verification

```text
python scripts/tests/test_validate.py
python scripts/tests/test_project_commands.py
python scripts/tests/test_workspace_schemas.py
```

## Bounded loop contract

- `success_evidence`: valid fixtures pass, invalid/future fixtures fail,
  and a forced migration failure restores the exact prior tree.
- `evaluator`: focused tests above.
- `max_iterations`: 5.
- `remote_run_budget`: 0.
- Stop if migration cannot preserve registry identity and path data.

## Exit criteria

- [ ] Every schema has an independent version.
- [ ] Registry v1 has a named dry-run-first migration.
- [ ] Committed registry fixtures contain no machine paths.

## Closeout / Knowledge Delta

Record compatibility boundaries and migration failure signatures.
