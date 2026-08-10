# Benchmarks

## The question

For the same task, model, settings, evaluator and budget, does the agent
produce a better verified outcome with an EIF instruction than without it?
Modes A and B are the matched comparison for that question. "Better" means
correctness first, then fewer false claims, review findings and rework, with
cost reported beside quality. Merely following an instruction more literally
is not an improvement if the result is no better.

A comparison must keep the source input identical, record both attempts and
randomize mode order for a real batch. One attempt per cell is an existence
proof only; it cannot support a general improvement claim.

## Status: one bounded real-agent pilot published (D-010)

The quality-per-token benchmark harness (`scripts/eif_benchmark.py`) is
real and executable for modes A and B, with a 10-fixture corpus. Mode B is
proven end-to-end against a real installed `eifctl` wheel, not just
theoretically executable - see `scripts/tests/test_benchmark_mode_b.py`.

**First real-agent result (2026-07-20), per D-010's ratified bounds:**
model `deepseek-v4-flash`, 3 representative fixtures (T02, T07, T10), one
attempt per mode, 6 attempts total, no retries. All 6 succeeded (task
completion 6/6 tests for T02/T07, 5/5 for T10, in both modes; the
anti-cheating mutation check passed on every attempt). Real, raw records:
[`../../benchmark-results.jsonl`](../../benchmark-results.jsonl); mechanical
aggregate: [`../../benchmark-summary.json`](../../benchmark-summary.json).
Every record's `measurement.source` is `provider-usage` (DeepSeek's own
`usage` field on the API response, `exact: true`), not an estimate.

| Task | Mode A input/output tokens | Mode B input/output tokens |
|---|---|---|
| T02 | 732 / 384 | 1743 / 188 |
| T07 | 727 / 256 | 1738 / 120 |
| T10 | 948 / 1538 | 1959 / 876 |

**What this does and does not support:** this is one attempt per
(task, mode) cell - a bounded existence proof that the harness, mode B's
governance materialization, and a real agent-runner all work correctly
together end to end, not a statistically powered comparison. Mode B used
more input tokens than mode A in every case (it reads the generated
governance block); mode B's output was shorter than mode A's in every
case here, but n=1 per cell cannot support a general "governance makes
model output shorter/more efficient" claim - that would need repeated
trials, which this round deliberately does not run (D-010 caps this pilot
at six attempts). Report the numbers above as exactly what they are: one
real, reproducible, honestly-measured run, not a trend.

The agent-runner used is
[`scripts/tests/fixtures/benchmark/deepseek_agent_runner.py`](../../scripts/tests/fixtures/benchmark/deepseek_agent_runner.py) -
deliberately single-shot (one API call per attempt, not a multi-tool
agentic loop), reading the task prompt, `CLAUDE.md` (mode B only), and
`src/*.py`/`tests/*.py`, and reporting DeepSeek's own token usage. A prior
round's harness self-tests against a fake, deterministic agent remain in
place and unaffected (`scripts/tests/test_benchmark.py`, 59/59 checks;
`scripts/tests/test_benchmark_mode_b.py`, 29/29 checks) - those prove the
harness mechanics; this real run proves the end-to-end pilot.

## EIF-021 bounded skill eval: deterministic dry-run

Version 0.2.8 extends the same `eif_benchmark.py` harness with a model-free
skill-evaluation surface. Manifest
[`skill-eval/eif-021-manifest.yaml`](skill-eval/eif-021-manifest.yaml) selects
`run-execution-packet` and `knowledge-search`, three local trigger scenarios
per skill, and matched `baseline`/`treatment` modes. This is 12 planned
attempts in strict sequential order, not 12 executed model runs.

Owner gate зафіксовано так:

- additional paid budget: `$0`;
- hard zero-cost boundary: not confirmed;
- provider/model/version: `not_approved`;
- rubric judge: `not_approved`;
- usage telemetry: required, stop if unavailable;
- behavioral status: `DEFERRED`;
- executed model runs: `0`.

Dry-run і integrity validation:

```bash
python scripts/eif_benchmark.py skill-eval-dry-run \
  docs/benchmarks/skill-eval/eif-021-manifest.yaml \
  --out docs/benchmarks/skill-eval/eif-021-dry-run.json
python scripts/eif_benchmark.py validate-skill-eval \
  docs/benchmarks/skill-eval/eif-021-dry-run.json
```

Result artifact
[`skill-eval/eif-021-dry-run.json`](skill-eval/eif-021-dry-run.json) містить
лише prompt digests, contract digests, paired context flags, deterministic
graders, null metrics, explicit defer reason та combined source integrity.
Raw prompts не дублюються в result. `test_skill_eval.py` доводить matched
prompt digests, deterministic output, containment, source-digest drift
detection, budget overflow failure і refusal to impersonate an approved
provider runner.

Цей dry-run дозволяє сказати лише, що harness, fixtures, graders та bounded
plan complete. Він не вимірює trigger precision/recall, task quality, token
cost, latency або benefit. Model-versus-script boundary для всіх 15 current
skills зафіксовано в
[`skill-eval/model-vs-script-audit.md`](skill-eval/model-vs-script-audit.md).

## Executable modes

| Mode | Governance | Structural graph | Shell compression | Status |
|---|---:|---:|---:|---|
| A - baseline | no | no | no | **Executable** |
| B - EIF governance | yes (`eifctl init`) | no | no | **Executable** |
| C - + structural navigation | yes | yes | no | **Executable contract; no real-agent result yet** |
| D - full stack | yes | yes | yes | **Executable contract; no real-agent result yet** |

Modes C and D now have an executable attempt boundary, not a performance
result. `materialize` accepts a schema-valid integration health report, a
structural graph artifact and its D08 metadata sidecar. It requires Graphify
`healthy`, freshness `fresh`, passing `query`/`path`/`explain` canaries and a
parseable graph. The sidecar must bind the exact artifact digest, Graphify
version, source commit, manifest hash and scope hash to the health report. The
graph must also reference at least one file in the fixture source tree, and the
integration record is bound to that tree's existing source digest. Mode D
additionally requires RTK `healthy` with every required capability passing.

For C/D, `run` passes three extra arguments to the agent runner:
`integration_input_path`, `graph_artifact_path`, and `attempt_id`. A runner
must return the exact attempt ID, graph digest and non-empty set of consumed
capabilities. Mode D must also write content-free RTK telemetry attributed to
that attempt under the materialized instance's local state. Missing,
presence-only, wrong-attempt or substituted-digest evidence produces one
append-only `harness_error` record and exit `21`; it can never become a
successful C/D result. Missing health/artifact preconditions return exit `3`
and create no workspace or result.

The deterministic C/D runs in the test suite are contract tests only. Their
`measurement.source` is `fake-runner`, so aggregation suppresses token figures
and no quality, productivity or savings claim follows from them. A real-agent
C/D run remains future evidence.

## Harness commands

```bash
python scripts/eif_benchmark.py validate-manifest <fixture_dir>
python scripts/eif_benchmark.py materialize <fixture_dir> <work_dir> --mode A_baseline
python scripts/eif_benchmark.py run <fixture_dir> <work_dir> --mode A_baseline \
    --agent-runner <your-agent-runner-command> --out results.jsonl
python scripts/eif_benchmark.py validate-result results.jsonl
python scripts/eif_benchmark.py aggregate <results_dir> --out summary.json
```

Modes C/D add explicit materialization inputs:

```bash
python scripts/eif_benchmark.py materialize <fixture_dir> <work_dir> \
  --mode C_structural_navigation --eifctl-path <exact-eifctl> \
  --integration-report <doctor-report.json> \
  --graph-artifact <graph.json> \
  --graph-metadata <eif-graph-metadata.json>
```

`--agent-runner` is a pluggable command. A/B argv is `[work_dir,
task_prompt_path]`; C/D append `[integration_input_path,
graph_artifact_path, attempt_id]`. Stdout is JSON `{input_tokens,
output_tokens, tool_calls}`, optionally `measurement`, and for C/D the
required `integration_consumption` proof. This repo provides two:
`scripts/tests/fixtures/benchmark/fake_agent_runner.py` (deterministic,
for harness self-tests, `measurement.source: fake-runner`) and
`scripts/tests/fixtures/benchmark/deepseek_agent_runner.py` (real, single-
shot, `measurement.source: provider-usage`, requires `DEEPSEEK_API_KEY`).
Wiring further real agents (a different model/provider, a true multi-tool
agentic loop) remains future work - this round's pilot is intentionally
minimal, not a claim that this is the only or best way to wire one.

Every attempt - success, task failure, harness error, timeout, or a
deliberate abort - produces exactly one append-only result record
conforming to
[`core/schemas/benchmark-result.schema.json`](../../core/schemas/benchmark-result.schema.json).
A restarted attempt is a NEW record whose `parent_attempt_id` links back
to the attempt it restarts (`attempt_kind`:
`retry_after_harness_error`/`retry_after_timeout`/`retry_after_task_failure`)
- there is no bare "reruns" counter that could silently lose the retry
history; the raw record stream is the source of truth `aggregate` reads
from, never a hand-summarized figure.

`run`'s exit code is distinct from whether a record was written (which
happens on every attempt, regardless): `0` a genuine success; `20` the
task failed or partially succeeded; `21` a harness error (e.g. the agent
runner crashed or produced unparseable output); `22` a timeout; `23` a
deliberate abort. A batch orchestrator may continue past any non-zero
code, but a CI/shell caller must not mistake 20-23 for success.

Mode B's `materialize` accepts `--eifctl-path` to pin the exact eifctl
executable to invoke (bypassing PATH lookup entirely) - the property this
exists to prove is that mode B runs a SPECIFIC installed package, never
whichever `eifctl` happens to resolve first on PATH.

## Fixture corpus (10, expanded from the original 3-fixture pilot)

Each fixture under
[`docs/benchmarks/fixtures/`](fixtures/) has a `manifest.json`
conforming to
[`core/schemas/benchmark-fixture-manifest.schema.json`](../../core/schemas/benchmark-fixture-manifest.schema.json):
an immutable source-tree digest, the exact task prompt, a deterministic
test command, an expected-output contract, an anti-cheating mutation
check (overwrites the solution with a known-bad reference regardless of
how the agent structured its fix, to prove the test suite actually
distinguishes correct from broken), a wall-time/tool-call budget, and
license/provenance/no-private-content confirmation. Every fixture below
was verified directly against `scripts/eif_benchmark.py validate-manifest`
and its own `test_command`/mutation pair (both the unfixed starting state's
real pass count and, separately, a correct fix's 6/6) before being
committed - none of the pass counts named here are estimated.

Ten task categories, deliberately spanning different bug/change shapes so
the corpus doesn't just repeat the same kind of fix ten times:

- **T01 - implement a function from a written spec**: a compact
  duration-string parser (`1d2h30m15s` -> total seconds), unimplemented
  (raises `NotImplementedError`) rather than buggy - a from-scratch
  implementation task, not a fix. 6 tests; unfixed source passes 0/6;
  mutation check (a plausible reference that treats a day as 1 hour, not
  24) expects 4/6.
- **T02 - fix a bug**: an off-by-one boundary bug in a bulk-discount
  calculation (`pricing.py`). 6 tests; mutation check expects 5/6 after
  reverting to the known-buggy reference.
- **T03 - refactor without changing behavior**: two functions duplicate
  the same validate-and-compute logic; requires extracting a shared
  helper without changing either function's observable behavior. 6 tests;
  unfixed (already-correct, pre-refactor) source passes 6/6; mutation
  check (a plausible "refactor" that silently drops the validation)
  expects 4/6.
- **T04 - add input validation**: a function's docstring promises a
  `ValueError` for invalid input that the implementation doesn't actually
  raise yet (crashes with an undocumented exception instead). 6 tests;
  unfixed source passes 4/6; mutation check (a partial fix that only
  handles the crash it happened to notice) expects 5/6.
- **T05 - fix a boundary bug**: a pagination function's off-by-one is in
  slice-index arithmetic, not a comparison operator - a different
  boundary-bug shape than T02. 6 tests; unfixed source passes 2/6;
  mutation check expects 2/6.
- **T06 - fix a data-driven bug**: a shipping-rate lookup table has one
  wrong constant; the calculation logic itself is correct - tests whether
  the fix targets the data, not the algorithm. 6 tests; unfixed source
  passes 4/6; mutation check expects 4/6.
- **T07 - avoid repeating a known failed fix**: a whitespace-trimming bug
  whose task prompt explicitly documents a previously-tried, wrong fix
  (stripping all spaces, which breaks multi-word names) and instructs not
  to repeat it. A dedicated detector
  (`checks/detect_known_fail.py`) flags a solution that reintroduces the
  documented wrong pattern as a failure, independent of raw test-pass
  count. 6 tests; mutation check expects 3/6.
- **T08 - fix an inconsistency across two functions**: a member-discount
  rate is correctly defined once in a shared module but re-hardcoded,
  differently, in a second function - a multi-file/multi-function
  coordination bug, not a single isolated line. 6 tests; unfixed source
  passes 4/6; mutation check expects 4/6.
- **T09 - add an optional parameter without breaking existing callers**:
  a name-formatting function needs an optional middle-name parameter
  added without breaking any existing 2-argument call - a backward-
  compatibility/API-evolution task. 6 tests; unfixed source passes 2/6;
  mutation check (a plausible fix that checks `is not None` instead of
  truthiness, mishandling an explicit empty string) expects 5/6.
- **T10 - security-relevant fix**: an unvalidated path-traversal
  vulnerability in a file-serving function - both relative `..` escapes
  and absolute-path escapes must be rejected with the correct error type,
  without misclassifying a legitimately-missing in-sandbox file as an
  attack. 5 tests; mutation check expects 2/5.

All ten are originally-authored, synthetic, Apache-2.0-licensed, and
contain no private repository content, per D-12.

## Metrics and methodology

Total input/output/reasoning tokens, tool calls, wall time, task
completion, tests passed/total, factual errors, review findings, rework
loops, context compactions, setup cost, index/graph refresh cost,
maintenance overhead - see the result schema for the full, precise list.
`aggregate` derives success rate and a 95% confidence interval on token
counts per (task, mode) group directly from the raw records - never
hand-computed - and explicitly refuses to silently average a group that
mixes different tool versions (e.g. two different `eifctl` releases),
surfacing it as a named conflict instead. A token-count figure is never
reported without an accompanying quality figure (success rate) in the
same group.

Every record also carries `measurement` (`source`: `fake-runner` |
`provider-usage` | `client-telemetry` | `estimated`; `exact`: bool) -
provenance for the token/tool-call numbers themselves, since an
agent-runner's self-reported JSON is not trusted as measured truth
without labeling where it came from. `aggregate` refuses to blend a
group whose records disagree on `source` or on `exact`, refuses to
publish token figures for a group with any record missing `measurement`
entirely, and suppresses token figures for a group that is entirely
`fake-runner`-sourced (this round's only agent-runner, never real
quality-per-token evidence) - success_rate/outcome_breakdown are still
reported either way, since retention doesn't depend on measurement
trustworthiness.

A benchmark that only measures "tokens saved" without task success and
rework rate is misleading - the private production instance this
framework was extracted from measured raw shell-output savings of 52-98%
across different weeks, driven almost entirely by whether a single
high-volume command class happened to be filtered correctly that week,
not by anything resembling task quality. Token metrics alone do not tell
you whether the system is actually good.

## Privacy before publication

Any raw transcript referenced by a result record's `raw_log_ref` must
pass a privacy scan before publication (D-12) -
`scripts/eif_benchmark.py`'s `scan_transcript_for_privacy()` reuses
`eif_privacy_scan.py`'s own detection patterns (absolute paths,
secret-shaped strings) against the transcript file, rather than
duplicating that logic. A finding blocks publication of that transcript,
not the result record itself (the compact record has no raw content to
leak).

## Contributing a benchmark run

The remaining seven fixtures (T01, T03-T06, T08-T09) have not been run
against a real agent yet - D-010 deliberately bounded this pilot to three.
Running them, running additional models/providers, or running repeated
trials per cell (needed for a real confidence interval) are all open,
tracked as part of the v0.1 public-readiness backlog - not done here to
avoid an unbounded real-agent matrix in one round.
