---
id: SESSION-001
type: session-launch
status: prepared
source_artifact: ../04-ROADMAP-020-private-workspace.md
session_context: .session-context/eif-020-session-001.md
depends_on: []
---

# Session 001: Architecture and public decision

## Goal

Define private workspace scope inside L2, record the decision and prevent
the public model from drifting to four layers.

## Required reading order

1. Packet files 00 through 04.
2. `AGENTS.md`, `core/policies/decisions.md`,
   `docs/architecture/HOW-EIF-WORKS.md` and site layer copy.
3. Current capability claims and tests that bind them.

## Experience retrieval preflight

Search knowledge and decision sources for registry, workspace, layer and
promotion. Record exact matches or that none exist.

## Scope

Architecture, decision register, terminology and structural tests only.

## Out of scope / do not touch

Do not add CLI behavior, schemas, runtime files or available capability
claims.

## Verification

```text
python scripts/eif_check_links.py
python scripts/eif_privacy_scan.py
python scripts/tests/test_operating_layer.py
```

## Bounded loop contract

- `success_evidence`: public sources consistently define three layers and
  workspace as L2 scope.
- `evaluator`: commands above plus exact source search.
- `max_iterations`: 3.
- `remote_run_budget`: 0.
- Stop on ratified-decision conflict or privacy risk.

## Exit criteria

- [ ] D-17 is superseded only where required.
- [ ] No public source describes a fourth layer.
- [ ] Capability status remains honest.

## Closeout / Knowledge Delta

Record the final scope terminology and any rejected hierarchy.
