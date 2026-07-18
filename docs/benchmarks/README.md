# Benchmarks

## Status: harness executable, no runs published yet

The quality-per-token benchmark harness (`scripts/eif_benchmark.py`) is
real and executable for modes A and B, with a 10-fixture corpus. Mode B is
proven end-to-end against a real installed `eifctl` wheel, not just
theoretically executable - see `scripts/tests/test_benchmark_mode_b.py`.
**No real-agent run has been executed or published** - only harness
self-tests against a fake, deterministic agent
(`scripts/tests/test_benchmark.py`, 41/41 checks;
`scripts/tests/test_benchmark_mode_b.py`, 29/29 checks). Any claim of "N%
token savings" without a real, published run should be treated as
unverified.

## Executable modes

| Mode | Governance | Structural graph | Shell compression | Status |
|---|---:|---:|---:|---|
| A - baseline | no | no | no | **Executable** |
| B - EIF governance | yes (`eifctl init`) | no | no | **Executable** |
| C - + structural navigation | yes | yes | no | **Schema-declared, operationally BLOCKED** |
| D - full stack | yes | yes | yes | **Schema-declared, operationally BLOCKED** |

Modes C and D are declared in
[`core/schemas/benchmark-result.schema.json`](../../core/schemas/benchmark-result.schema.json)'s
`mode` enum so the schema doesn't need to change when they become real,
but `eif_benchmark.py materialize`/`run` refuse to execute them - there is
no reproducible Graphify/RTK install-version-config contract yet to run
them against, and a faked C/D result would actively mislead rather than
just be absent. They stay blocked until that contract exists.

## Harness commands

```bash
python scripts/eif_benchmark.py validate-manifest <fixture_dir>
python scripts/eif_benchmark.py materialize <fixture_dir> <work_dir> --mode A_baseline
python scripts/eif_benchmark.py run <fixture_dir> <work_dir> --mode A_baseline \
    --agent-runner <your-agent-runner-command> --out results.jsonl
python scripts/eif_benchmark.py validate-result results.jsonl
python scripts/eif_benchmark.py aggregate <results_dir> --out summary.json
```

`--agent-runner` is a pluggable command (argv: `[work_dir,
task_prompt_path]`, stdout: JSON `{input_tokens, output_tokens,
tool_calls}`) - this round provides only a fake, deterministic one for
testing (`scripts/tests/fixtures/benchmark/fake_agent_runner.py`); wiring
a real agent adapter is separate, future work, not run this round (no
expensive real-agent matrix, per explicit instruction).

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

Not open yet - a real-agent run is out of scope this round by explicit
instruction. Tracked as part of the v0.1 public-readiness backlog.
