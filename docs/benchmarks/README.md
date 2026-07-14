# Benchmarks

## Status: not run yet

No quality-per-token benchmark has been executed or published for this
framework. Any claim of "N% token savings" without this benchmark should be
treated as unverified and specific to shell-output compression alone, not
the framework as a whole.

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
system is actually good.

## Contributing a benchmark run

Not open yet - tracked as part of the v0.1 public-readiness backlog.
