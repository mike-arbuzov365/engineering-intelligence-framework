---
id: SESSION-007
type: session-launch
status: prepared
source_artifact: ../04-ROADMAP-020-private-workspace.md
session_context: .session-context/eif-020-session-007.md
depends_on: [SESSION-006]
---

# Session 007: Local release-candidate verification

## Goal

Verify the complete public vertical slice locally and hand off a private
dogfood gate without publishing anything.

## Required reading order

1. Packet files 00 through 06.
2. All prior session checkpoints.
3. Release workflow comments and local equivalent commands.

## Experience retrieval preflight

Search for release failures, hosted-runner budget decisions, packaging
drift and private dogfood requirements.

## Scope

Full local tests, clean package build/install, optional already-local
container canary, packet closeout and private follow-on handoff.

## Out of scope / do not touch

No push, tag, GitHub Actions, remote creation, site deployment, private
project mutation or release.

## Verification

```text
python scripts/tests/run_all.py
python scripts/eif_privacy_scan.py
python scripts/eif_release.py --require-final-version
git diff --check
git status --short
```

## Bounded loop contract

- `success_evidence`: every local gate passes from the candidate tree and
  the installed-wheel synthetic workspace journey succeeds.
- `evaluator`: commands above.
- `max_iterations`: 3.
- `remote_run_budget`: 0.
- Stop on an unavailable required local evaluator, a privacy finding or
  any request for remote execution.

## Exit criteria

- [ ] Closeout records exact local evidence and residual risks.
- [ ] Private dogfood remains an explicit release gate.
- [ ] No external action occurred.

## Closeout / Knowledge Delta

Fill `../07-CLOSEOUT-020-private-workspace.md` and name the next private
packet without recording real targets in this public repository.
