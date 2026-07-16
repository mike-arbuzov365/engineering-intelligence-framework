# Benchmarks

## Status: packet and schema ready, no runs executed

No quality-per-token benchmark has been executed or published for this
framework. Any claim of "N% token savings" without this benchmark should be
treated as unverified and specific to shell-output compression alone, not
the framework as a whole. The corpus, modes, metrics, and methodology below
are now a concrete, owner-ready plan (private planning packet
`PACKET-EIF-QUALITY-PER-TOKEN-BENCHMARK` carries the full corpus table and
task specs); this document carries the technical, public-facing parts -
the result-record schema and harness architecture - so a run can be
executed and its output validated without re-deriving either from scratch.
Expensive runs are deliberately **not** part of this deliverable.

## Planned methodology

10-20 representative tasks (find a feature, fix a bug, impact analysis, add
an endpoint, diagnose a failing test, resume after a new session, avoid
repeating a known-failed fix, cross-repo change), run under four modes:

| Mode | Governance | Structural graph | Shell compression |
|---|---:|---:|---:|
| Baseline | no | no | no |
| Knowledge governance | yes | no | no |
| + structural navigation | yes | yes | no |
| Full stack | yes | yes | yes |

Metrics: total input tokens, total output/reasoning tokens, tool calls,
wall time, task completion, tests passed, factual errors, review findings,
rework loops, context compactions, raw re-runs after over-compression, cost
of index/graph refresh, setup/maintenance overhead.

A benchmark that only measures "tokens saved" without task success and
rework rate is misleading - the private production instance this framework
was extracted from measured raw shell-output savings of 52-98% across
different weeks, driven almost entirely by whether a single high-volume
command class happened to be filtered correctly that week, not by anything
resembling task quality. Token metrics alone do not tell you whether the
system is actually good. **No "N% tokens saved" claim will be published
from this benchmark without an accompanying quality result** (task success
rate, rework rate) reported in the same breath - a savings number alone is
not the claim this framework makes.

## Result-record schema

Every run of every (task, mode) pair emits one JSON record validated against
[`core/schemas/benchmark-result.schema.json`](../../core/schemas/benchmark-result.schema.json)
(Draft 2020-12, same validator - `eif_validate_frontmatter.py` /
`jsonschema.Draft202012Validator` - as every other EIF schema). Fields cover
identity (`task_id`, `mode`, `run_index`, `randomized_order_seed`), the
model and its settings, the input (synthetic fixture or `owner/name` +
frozen commit SHA), every metric from the list above, and an `outcome`
block (`success` / `partial` / `failure` / `harness_error` - a failed run is
a valid record, not an omission). `raw_log_ref` points at the full
transcript rather than embedding it, keeping records compact enough to
aggregate in bulk.

## Harness architecture (design, not yet built)

A harness run is `run(task_id, mode, run_index, model_config) -> result_record`:

1. **Materialize the input** - for a synthetic fixture, unpack the pinned
   fixture bundle; for a public repository, clone and checkout the frozen
   commit SHA. Recorded in `inputs.provenance`.
2. **Provision the mode** - mode A: nothing. Mode B: install/init EIF
   against the input. Mode C: also build/refresh the Graphify structural
   graph. Mode D: also enable RTK. Provisioning cost is itself a metric
   (`setup_cost_seconds`, `index_or_graph_refresh_cost_seconds`), not
   discarded overhead.
3. **Execute the task** under a fixed model/settings (recorded in
   `model.settings` so a later reader can tell what was actually fixed vs.
   what varied), capturing tokens/tool-calls/wall-time as they happen, not
   reconstructed after the fact.
4. **Score the result** against the task's own deterministic test(s) (see
   the corpus in the private planning packet) - `tests_passed`/
   `tests_total` come from actually running those tests, not from a
   judgment call.
5. **Emit one result record** conforming to the schema above, plus a
   pointer to the raw transcript. A harness crash still emits a record
   (`outcome.status: harness_error`) - it is never silently dropped from
   the aggregate, the same principle `run_all.py`'s exact-inventory mode
   already enforces for this repository's own test suites.

## Methodology

- **Repeated runs.** Each (task, mode) pair runs multiple times
  (`run_index` increments) - a single run per cell is not a benchmark, it's
  an anecdote.
- **Randomized mode order.** The order in which A/B/C/D run for a given
  task is randomized per batch (`randomized_order_seed`) so mode order
  itself isn't a confound (e.g. model warm-up, rate-limit backoff patterns).
- **Fixed model/settings where possible.** Recorded explicitly per record,
  not assumed constant.
- **No cherry-picking.** Every record produced by a batch is retained and
  reported, including failed runs and harness errors - the schema has no
  field for "discard this one."
- **Raw result schema, not pre-aggregated prose.** Aggregation (means,
  success rates) is computed FROM the raw records, the same "derived, not
  hand-summed" principle `scripts/tests/run_all.py`'s `aggregate()` already
  applies to this repository's own test inventory.
- **Confidence intervals or, at minimum, variance** are reported alongside
  any mean - a single number per mode without a spread is not sufficient
  evidence of a real difference.
- **Limitations are stated, not buried** - corpus size (10-20 tasks) is
  too small to generalize confidently across all codebases/languages;
  synthetic fixtures may not capture every real-world messiness a public
  repository would.

## Contributing a benchmark run

Not open yet - tracked as part of the v0.1 public-readiness backlog. The
schema and harness design above exist so a future run doesn't have to
re-derive either; the corpus itself lives in the private planning packet
(not duplicated here, since the private packet's fixture provenance details
are execution-planning detail, not public methodology).
