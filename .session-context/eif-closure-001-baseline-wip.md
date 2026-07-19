---
session_id: eif-closure-001-baseline-wip
status: in-progress
date: 2026-07-19
---

# SESSION-001 checkpoint: baseline, PR #24, dirty-WIP reconciliation

## SHA verification

- `origin/main` (framework): `6fcb3439fba90efc0e43a2f83bf88dd19dce5f7e` — matches FACTS.
- Clean worktree: `D:/Repos/04-work/.eif-clean-worktrees/framework-closure`.
- Branch: `wm/eif-technical-preview-closure-2026-07-19`, based at `origin/main`.
- Dirty root worktree (`D:/Repos/04-work/engineering-intelligence-framework`) and dirty hotfix worktree (`.eif-clean-worktrees/cursor-adapter`) untouched, read-only evidence per D-002.
- Private repo (`wm-engineering-intelligence`) local `main` fast-forwarded `cefcac4..2d6e8b8` (zero unique local commits, safe) before this session started; the untracked XREPO-01 packet directory was then committed on top (`5b60142`, pure new documentation, no code). Seven files `git status` flagged "modified" (AGENTS.md, CLAUDE.md, RTK.md, HOW-TO-USE-SESSIONS.md, three planning docs) were confirmed via raw `git diff` to be pure pending CRLF normalization (zero real content) before being normalized with `checkout --`.

## PR #24 disposition

- `feat/benchmark-corpus-expansion-2026-07-18`, commit `ab3f281`, single commit, `MERGEABLE`.
- Checks: policy + 4×package-build + 2×license all `SUCCESS`; "Package build required" and "Dependency license check (required by policy)" aggregate gates `FAILED` in ~2s (`runner_id: 0` pattern) = quota allocation failure, not a product failure. Matches D-012.
- Integration method: cherry-picked `ab3f281` → `804ae70` onto `wm/eif-technical-preview-closure-2026-07-19`. No push. Per D-011 this commit becomes part of the single final framework PR; original PR #24 is superseded at final integration (fewer remote runs than reopening/updating it separately).

## Dirty hotfix WIP disposition ledger

`hotfix/radical-ci-and-test-simplification` @ `6fcb343`, worktree `.eif-clean-worktrees/cursor-adapter`.

| File | Change | Disposition | Rationale |
|---|---|---|---|
| `.github/workflows/ci.yml` | staged delete (208 lines) | reject-as-is / rebuild | Old 8-job topology is the quota problem D-004 targets, but deleting it leaves PRs with zero automatic checks, contradicting D-004's "one hosted Ubuntu job" steady state. Session 002 writes a new slim one-job workflow; does not restore the old file. |
| `.github/workflows/release-check.yml` (untracked) | new, workflow_dispatch-only | reuse | Matches D-004's manual release gate requirement directly. |
| `scripts/tests/smoke.py` (untracked) | new, ~21s parallel smoke suite | reuse-with-amend | Strong structure/coverage (schemas, privacy scan, demo, doctor-corruption, per-adapter init/doctor/idempotency/content-survival, one switch cycle). Docstring/comments call all four adapters "required" — contradicts ratified D-09 (only Claude Code + Cursor required; Codex/Hermes experimental). Session 002 must correct the required/experimental framing and keep the suite structure and timing. |
| `core/policies/merge-policy.json` | `required_check_contexts`: 3 names → `[]`; `allow_no_checks`: false → true | reject (as steady state) | D-004 explicitly: "Removing all PR checks is allowed only as a temporary quota-emergency local state and is not the committed steady-state design." Session 002 must define the new slim job's context name(s) and keep `allow_no_checks: false`. |
| `scripts/tests/test_merge_gate.py` | +26/-16 lines, adds `SYNTHETIC_POLICY` fixture | reuse | Decouples generic gate-logic tests (missing/failed/pending/duplicate-context handling) from the *current* policy's specific required-context list — a good pattern independent of what Session 002's real policy ends up declaring. The handful of assertions that assert today's *emergency* shape (zero required contexts) will need matching updates once Session 002 lands the real steady-state policy. |
| `scripts/tests/run_all.py` | -2 lines (drops `test_adapter_switch_matrix.py`, `test_pr_ci_evidence.py` from `SUITES`) | rebuild | Both files should come back as release-tier suites (see below), so they need a release-cadence runner list/flag, not full removal from the repo's test inventory. |
| `scripts/tests/test_adapter_switch_matrix.py` | staged delete (256 lines, full 12-directed-pair matrix) | keep-release-only | `smoke.py`'s one-cycle check covers routine PR needs; ROADMAP Session 002 explicitly: "restore/retain distinct... switch-pair... regressions outside routine PR cadence" and "do not inflate [parity matrix] into 12 independent proofs." Restore as a release-tier suite, not routine PR, not deleted outright. |
| `scripts/eif_pr_ci_evidence.py` | staged delete (141 lines) | reject-pending-topology | Existed to reuse PR evidence across the old push+PR double-run topology ("Reuse verified PR CI" shows as a `SKIPPED` check on PR #24). If Session 002's one-job/no-push-duplication topology removes the double-run problem this existed to solve, deletion becomes correct (D-005 "delete" class: no distinct failure mode survives). Session 002 must confirm before deleting. |
| `scripts/tests/test_pr_ci_evidence.py` | staged delete (94 lines) | reject-pending-topology | Tied 1:1 to `eif_pr_ci_evidence.py`'s fate above. |
| `scripts/tests/test_codex_adapter.py` | -919 lines net (unstaged) | keep-release-only, pending Session 002 line-level pass | Net shape matches "cut exhaustive/Unicode/permutation depth, keep core path" pattern `smoke.py`'s docstring describes; the release-tier suite must carry the cut depth forward, not silently lose it. Detailed per-case reconciliation is Session 002's explicit scope. |
| `scripts/tests/test_cursor_adapter.py` | -433 lines net (unstaged) | keep-release-only, pending Session 002 line-level pass | Same pattern as above. |
| `scripts/tests/test_hermes_adapter.py` | -685 lines net (unstaged) | keep-release-only, pending Session 002 line-level pass | Same pattern as above. |
| `scripts/tests/test_package_build.py` | -489 lines net (unstaged) | keep-release-only, pending Session 002 line-level pass | Same pattern as above; must stay in the cross-platform/Python-version release suite per D-005 "release" class (platform/packaging coverage). |

Overall WIP verdict (matches FACTS' own INFERRED note): direction is right (routine-PR cost must drop), but specific artifacts are not reusable verbatim. Session 002 rebuilds the CI workflow and merge policy to D-004's actual steady state (one required job, `allow_no_checks: false`), keeps `smoke.py`'s structure with the D-09 adapter-tier correction, and restores switch-matrix/PR-CI-evidence/adapter/package-build depth as release-tier suites rather than deleting them outright.

## Baseline local commands (recorded, not executed — full suite deferred to Session 007)

```text
rtk summary python scripts/tests/smoke.py
rtk summary python scripts/tests/run_all.py --json
rtk summary python scripts/tests/test_package_build.py
rtk summary python scripts/eif_privacy_scan.py --repo .
rtk summary python scripts/eif_check_links.py --repo .
rtk git diff --check
```

## No remote run triggered

Only `git fetch --prune` (both repos, read-only) and one `gh pr view 24` (read-only metadata) ran. No push, no PR open/update, no rerun, no `workflow_dispatch`.

## Exit criteria status

- [x] Clean framework branch/worktree starts at fresh `origin/main`.
- [x] User-owned dirty worktrees unchanged (root repo and `cursor-adapter` worktree untouched).
- [x] PR #24 has one non-duplicating integration path (cherry-picked into the closure branch; original PR superseded at final integration per D-011).
- [x] Every dirty hotfix file has a reuse/rebuild/keep-release-only/reject disposition with rationale (table above).
- [x] No remote workflow was triggered.
- [x] Checkpoint complete (this file).

## Knowledge Delta

- Reusable lesson: `rtk git diff` / `rtk git diff --stat` returned empty output for real diffs in this session — both a CRLF-only phantom-diff case and genuine multi-hundred-line diffs in a worktree. `rtk proxy git diff` (raw, with `# rtk-raw-ok`) was needed to see actual content both times. Worth a curator look at the rtk diff wrapper itself; until fixed, treat its empty output as inconclusive, not as "no diff," and confirm via raw proxy before acting.
- Private-repo local `main` carried seven files flagged "modified" by `git status` that were pure CRLF-normalization phantoms (zero real content) — confirmed via raw diff before any checkout/normalize action, not assumed from the status output alone.
