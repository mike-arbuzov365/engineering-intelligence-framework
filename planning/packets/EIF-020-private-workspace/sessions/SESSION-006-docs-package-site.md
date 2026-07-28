---
id: SESSION-006
type: session-launch
status: prepared
source_artifact: ../04-ROADMAP-020-private-workspace.md
session_context: .session-context/eif-020-session-006.md
depends_on: [SESSION-005]
---

# Session 006: Documentation, package and site

## Goal

Expose only the behavior now proven by source and tests, while keeping the
three-layer public explanation simple.

## Required reading order

1. Packet files 00 through 04.
2. Sessions 001 through 005 checkpoints.
3. Capability claims, lifecycle docs, package sync contract and site
   claim verifier.

## Experience retrieval preflight

Search for prior capability overclaim, package sync and site terminology
findings.

## Scope

Public docs, site copy, package resources, installed-wheel tests and
privacy checks.

## Out of scope / do not touch

No site deployment, public release, private profiles or real fleet names.

## Verification

```text
python scripts/sync_package_sources.py
python scripts/eif_check_links.py
python scripts/eif_privacy_scan.py
python scripts/tests/test_package_build.py
npm --prefix site run gate
```

## Bounded loop contract

- `success_evidence`: package and site gates pass and exact search finds
  no fourth-layer or second-framework wording.
- `evaluator`: commands above.
- `max_iterations`: 4.
- `remote_run_budget`: 0.
- Stop if public copy would have to disclose private target information.

## Exit criteria

- [ ] Capability matrix status matches actual tests.
- [ ] Site still says three layers and explains workspace inside L2.
- [ ] Synced resources match canonical trees.

## Closeout / Knowledge Delta

Record terminology choices, claim boundaries and package evidence.
