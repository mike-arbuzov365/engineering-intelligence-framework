---
session_id: eif-closure-002-cost-safe-ci
status: in-progress
date: 2026-07-19
depends_on: eif-closure-001-baseline-wip
---

# SESSION-002 checkpoint: cost-safe CI and test pyramid

## Topology change (D-14, supersedes D-13)

- `.github/workflows/ci.yml`: rewritten to exactly one hosted job, `PR smoke checks (required by policy)`, trigger `pull_request` only (no `push`). Runs `scripts/tests/smoke.py` + privacy scan + frontmatter/config validation + YAML/JSON-Schema validation + link check + Knowledge Delta classification.
- `.github/workflows/release-check.yml`: rebuilt (the dirty WIP's version only ran `smoke.py` + `test_package_build.py` on one OS/Python combo + privacy/license/demo/benchmark-manifest checks - it never called `run_all.py` at all, so the full 23-suite inventory, the cross-platform package-build matrix, and the license-check matrix would have run in *no* automated context, anywhere, ever, if adopted as-is). Now three jobs, `workflow_dispatch`-only: `full-suite` (`run_all.py --json` + `test_run_all_json.py` + privacy/link/demo/benchmark-manifest checks), `package-build` (Ubuntu/Windows x Python 3.11/3.12 matrix, same as the old routine job), `license-check` (Ubuntu/Windows matrix, same as the old routine job).
- `core/policies/merge-policy.json`: `required_check_contexts` is now `["PR smoke checks (required by policy)"]` (was 3 names), `allow_no_checks` stays `false`, `policy_version` 5 -> 6.
- `core/policies/decisions.md`: added **D-14** (ratified), marked **D-13 superseded by D-14** with rationale (D-13's push-side evidence-reuse still produced a workflow run on every push - part of the 76-runs/5-day evidence - and every PR still allocated nine hosted jobs; D-14 removes the push trigger entirely and cuts PR jobs from nine to one).
- Deleted `scripts/eif_pr_ci_evidence.py` and `scripts/tests/test_pr_ci_evidence.py` (dead code once push triggers nothing - confirmed via repo-wide grep that nothing else referenced them before deleting).
- `scripts/tests/run_all.py`: dropped `test_pr_ci_evidence.py` from `SUITES`; every other suite (including the full, un-cut `test_codex_adapter.py`, `test_cursor_adapter.py`, `test_hermes_adapter.py`, `test_adapter_switch_matrix.py`, `test_package_build.py`-adjacent) is untouched and now runs only via `release-check.yml`'s `full-suite`/`package-build` jobs, not routinely. These files were never adopted from the dirty WIP's cut-down versions - this worktree branched from `origin/main`, so they were at full depth the whole time; the topology change alone moves them off the routine path.
- `scripts/tests/smoke.py`: added (this worktree's version, not a copy of the dirty WIP's). Corrected the WIP's "four v0.1-required adapters" language - D-09 ratifies only Claude Code and Cursor as required; Codex and Hermes are experimental-supported. The suite still exercises all four (defense-in-depth, catching a regression here is cheaper than at release) but no longer claims required status for Codex/Hermes, and the switch-cycle docstring now says the same.
- `docs/architecture/merge-enforcement.md`: fixed a **pre-existing stale count** unrelated to this session's own change (it said "the EIF policy has seven required contexts" when the policy actually had three, even before D-14) and updated both the required-context count and the `run_all.py`/`smoke.py` routing description to match D-14.

## Verification (run locally, not via a hosted runner)

| Command | Result |
|---|---|
| `python scripts/tests/smoke.py` | 44/44 passed, ~30s (one real failure found and fixed mid-session - see Knowledge Delta) |
| `python scripts/tests/test_merge_gate.py` | 37/37 passed |
| `python scripts/eif_privacy_scan.py --repo .` | 0 unsuppressed findings |
| `python scripts/eif_check_links.py --repo .` | all relative links resolve |
| `git diff --check` | clean |
| YAML parse of both rewritten workflow files | both valid |

## Out of scope, left for later sessions (not silently dropped)

- Broader `README.md`/`docs/architecture/HOW-EIF-WORKS.md`/`docs/product/claims-evidence.md` reconciliation against the new topology is explicitly Session 006's scope ("Reconcile README, HOW-EIF-WORKS, claims ledger... including corrected CI topology"). Flagging exactly what Session 006 must touch: `HOW-EIF-WORKS.md`'s "CI and quality gates" section (~line 290) and "Definition of Public-Ready" checklist rows describing the old job set/counts (~lines 609-646); `claims-evidence.md` rows about CI/package/adapter check counts.
- Codex/Hermes non-default adapter-option-plus-switch combinations remain undocumented/unproven, unchanged from before this session - no blanket parity claim was added (exit criterion respected).

## Exit criteria status

- [x] Routine PR workflow allocates no more than one hosted runner (one job, `pr-smoke`).
- [x] Main push does not duplicate full PR validation (push triggers no workflow at all now).
- [x] Required merge context exists and no-check merge stays denied (`allow_no_checks: false`, verified by test 14).
- [x] Release/platform/exhaustive suites remain runnable and indexed (`release-check.yml`'s three jobs; local-equivalent commands documented in its header).
- [x] Removed tests have evidence-backed replacement or duplicate rationale (`eif_pr_ci_evidence.py`/`test_pr_ci_evidence.py` deletion justified by D-14's topology change; grepped repo-wide first to confirm no other references).
- [x] D-09 wording remains two required plus two experimental adapters (`smoke.py` corrected).
- [x] Non-default adapter-option-plus-switch combinations stay documented as unproven; no blanket parity claim added.
- [x] No remote run occurred (all verification was local; no push, PR, rerun, or `workflow_dispatch`).

## Knowledge Delta

- Real catch, not hypothetical: this session's first `smoke.py` run found a genuine privacy-scan failure - Session 001's own checkpoint file (`.session-context/eif-closure-001-baseline-wip.md`) contained two absolute Windows paths (`D:/Repos/04-work/...`), flagged as `absolute_path_leak`. Fixed by rewording to relative/generic references and re-verified clean. Lesson: session checkpoint files are repo content too and are subject to the same privacy scan as everything else - write them with the same care as any other committed file, and run the smoke/privacy check after writing one, not just after product-code changes.
- Confirmed dirty-WIP risk from Session 001's ledger: the dirty hotfix's `release-check.yml` would have silently dropped the entire `run_all.py` suite inventory (23 suites) and the cross-platform package-build/license-check matrices from every automated context if adopted as a copy rather than rebuilt - exactly the "wholesale loss of distinct regression tests" FACTS warned about. Rebuilt rather than copied.
- Found and fixed a pre-existing stale count in `docs/architecture/merge-enforcement.md` ("seven required contexts", actually three even before this session) while touching that file for an unrelated reason - this repo has a documented history of this exact bug class (stale check-count claims), consistent with what this session's own D-005 test-classification work is meant to prevent going forward.
