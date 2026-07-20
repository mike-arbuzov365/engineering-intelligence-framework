---
session_id: eif-closure-006-benchmark-evidence
status: completed
date: 2026-07-20
depends_on: eif-closure-005-private-coexistence
---

# SESSION-006 checkpoint: bounded benchmark and public evidence

## Cost-boundary gate (D-010)

D-010 and this session's own launch file both require aborting before any
paid call without an enforceable cost boundary. No such boundary existed
in chat at the point this session reached the real-agent step - stopped
and asked the owner explicitly rather than guessing or silently
substituting a fake/estimated run. Owner provided a `DEEPSEEK_API_KEY` and
pinned `deepseek-v4-flash` after a grounded token estimate (based on the
actual fixture file sizes, not a guess) showed the real cost would be
negligible for a minimal single-shot runner. Verified `deepseek-v4-flash`
is a real, current model (not stale training-data knowledge) via Context7
+ web search before writing any code against it - old `deepseek-chat`/
`deepseek-reasoner` names are being deprecated 2026-07-24, four days from
this session.

## Fixture validation

All 10 fixture manifests validated locally (`validate-manifest`) before
any paid call - zero cost, matches this session's own scope item 1.

## Real-agent runner

Built `scripts/tests/fixtures/benchmark/deepseek_agent_runner.py`:
deliberately single-shot (one API call per attempt, not a multi-tool
loop) - reads the task prompt, `CLAUDE.md` if present (mode B), and every
`src/*.py`/`tests/*.py` under `work_dir`; sends one non-streaming chat
completion to `deepseek-v4-flash`; writes back only files that already
existed in `work_dir` (never invents a new file from model output);
reports DeepSeek's own `usage` field as `measurement: {source:
provider-usage, exact: true}` - not an estimate, not a self-report.

Ran a trivial, un-counted connectivity smoke test first (one word request,
33 tokens total) to confirm the key/model/endpoint actually work before
spending any of the six real, counted attempts on a preventable
configuration mistake.

## The six real attempts (D-010 bound: exactly six, no retries)

| # | Task | Mode | Input/output tokens | Outcome |
|---|---|---|---|---|
| 1 | T02 | A_baseline | 732 / 384 | success, 6/6 tests, mutation check passed |
| 2 | T02 | B_eif_governance | 1743 / 188 | success, 6/6 tests, mutation check passed |
| 3 | T07 | A_baseline | 727 / 256 | success, 6/6 tests, mutation check passed |
| 4 | T07 | B_eif_governance | 1738 / 120 | success, 6/6 tests, mutation check passed |
| 5 | T10 | A_baseline | 948 / 1538 | success, 5/5 tests, mutation check passed |
| 6 | T10 | B_eif_governance | 1959 / 876 | success, 5/5 tests, mutation check passed |

Total: 11,209 tokens across all 6 attempts - well under the pre-run
estimate (30-60K for a minimal runner), confirming the minimal single-
shot design achieved the owner's stated minimize-usage goal. Real dollar
cost at DeepSeek's published rates ($0.14/M input, $0.28/M output): a
small fraction of a cent.

Mode B materialize initially failed for lack of an installed `eifctl` on
PATH (this environment runs the framework from a source checkout, not an
installed package) - fixed by installing the package into a throwaway
venv and passing `--eifctl-path` (exists specifically to pin an exact
install without relying on PATH), not by mutating any real PATH/
environment. Attempt 1 (T02/A) had already succeeded before this was
discovered; per D-010's no-retry rule, it was not re-run - only the
remaining 5 attempts used `--eifctl-path`.

`validate-result` confirmed all 6 records schema-valid.
`aggregate` produced `benchmark-summary.json`: 6/6 groups, 100%
success_rate each, `input_tokens_95ci: null` for every group (correctly -
a single sample cannot support a confidence interval; the harness does
not fabricate one).

## What is and is not claimed

Every doc update (see below) states explicitly: this is one attempt per
(task, mode) cell, not a statistically powered comparison. Mode B used
more input tokens than mode A in every case (reads the generated
governance block) and had shorter output in every case here - reported as
observed numbers, NOT as a general "governance reduces tokens" claim,
since n=1 per cell cannot support that. D-010's "never publish token
numbers without task-success quality beside them" is satisfied throughout
- every token figure in the updated docs sits next to the success rate.

## Privacy and secret handling

`DEEPSEEK_API_KEY` was written to exactly one scratchpad file (outside any
git repo, session-isolated), read by the runner via `os.environ` only,
never hardcoded, never printed in full, never included in any result
record. Confirmed by direct search after the run: the literal key string
does not appear anywhere in the framework repo (tracked or untracked).
`eif_privacy_scan.py` also ran clean (0 findings) across the whole repo
including the new files. Scratchpad key file, throwaway venv, and
disposable work directories were deleted after the run.

## Docs/claims reconciliation (this session's other scope item)

- `docs/benchmarks/README.md`: replaced the "no runs published" status
  with the real result, the per-task token table, and an explicit "what
  this does/does not support" paragraph.
- `docs/product/claims-evidence.md`: updated the "EIF saves tokens" row
  (UNVERIFIED -> "first bounded pilot exists, not sufficient for a
  general claim", with the real evidence and forbidden-wording list
  updated to explicitly forbid generalizing beyond this pilot). Also
  updated the "CI validates EIF artifacts" row, which had gone stale
  independent of this session's own benchmark work - it still described
  the pre-D-14 topology (13 suites/620 checks quoted as CI's own routine
  output) from Session 002's CI consolidation two sessions ago; corrected
  to the real current shape (one routine job; full 24-suite/990-check
  inventory on the manual release gate).
- `docs/architecture/HOW-EIF-WORKS.md`: updated the "CI and quality gates"
  section, the "Metrics and benchmark methodology" section, the
  "Definition of Public-Ready" Quality checklist item and Roadmap item 6
  (struck through as partially done), and one FAQ answer - all for the
  same two reasons (stale D-14 CI description, stale "no benchmark"
  claim).

## Verification

| Command | Result |
|---|---|
| `validate-manifest` (all 10 fixtures) | 10/10 OK |
| `validate-result benchmark-results.jsonl` | 6/6 valid |
| `aggregate` | wrote `benchmark-summary.json`, 6 groups |
| `eif_privacy_scan.py --repo .` | 0 unsuppressed findings |
| `eif_check_links.py --repo .` | all relative links resolve |
| `scripts/tests/smoke.py` | 44/44 passed |
| Direct search for the literal API key string | 0 matches anywhere in the repo |

## Exit criteria status

- [x] All fixture manifests validate.
- [x] At most six real attempts exist and no retry is hidden (exactly 6,
      `attempt_kind: initial` for all, no `parent_attempt_id`).
- [x] Measurement provenance/exactness is explicit
      (`measurement.source: provider-usage`, `exact: true` on all 6).
- [x] Token result is always paired with task quality (success rate) in
      every doc update - never suppressed since none are fake-runner-
      sourced.
- [x] Raw transcript publication: none published - only the compact
      result records (no `raw_log_ref` populated), which have no raw
      content to leak; privacy scan clean regardless.
- [x] README/HOW/claims/ROADMAP/checklist agree with verified reality.
- [x] Human quickstart timing remains open, untouched by this session -
      not substituted with any mechanical figure.
- [x] No remote CI run occurred (all local; DeepSeek API calls are not
      GitHub Actions runs).

## Knowledge Delta

- **New fact**: `deepseek-v4-flash` is DeepSeek's current default model
  as of 2026-07-20 (verified via Context7 + web search, not assumed from
  training data); `deepseek-chat`/`deepseek-reasoner` deprecate
  2026-07-24. Worth re-checking if this benchmark is extended later.
- **New operational lesson**: mode B's `materialize` needs a real
  installed `eifctl` - a source-checkout-only dev environment (like this
  one) does not have it on PATH by default. `--eifctl-path` plus a
  throwaway venv is the correct fix, not a global install or a PATH
  mutation, and this is a real, recurring need for anyone running mode-B
  benchmark attempts from a framework source checkout rather than an
  installed package.
- **Confirmed working end to end**: a real, minimal (single-shot, no
  agentic tool-calling loop) agent-runner is sufficient to produce a
  schema-valid, provider-measured, 100%-success benchmark result - the
  harness's `--agent-runner` pluggability contract works exactly as
  documented for a genuinely new, real implementation, not just the
  fake one it shipped with.
- **Promotion candidate for public docs (already applied, not deferred)**:
  the "first bounded pilot, not a statistical claim" framing pattern used
  throughout the doc updates above is worth keeping as the template for
  any FUTURE benchmark expansion (more fixtures, more models, repeated
  trials) - state exactly what n supports and forbid generalizing beyond
  it, every time.
