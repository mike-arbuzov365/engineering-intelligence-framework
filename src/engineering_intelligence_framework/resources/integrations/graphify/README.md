# integrations/graphify/

Structural code-graph navigation and impact analysis.

## Current status: behavioral adapter (experimental)

EIF has a bounded, optional Graphify adapter. It probes a compatible CLI,
runs `query`, `path`, and `explain` against a three-node synthetic structural
fixture, validates the project-local raw artifact, and derives freshness from
the graph baseline, current Git commit, and merge base. PATH reachability alone
never produces `healthy`.

The tested compatibility contract is in [`manifest.json`](manifest.json):
Graphify `>=0.9.12,<0.10.0`, with `0.9.12` behaviorally tested. The range is a
candidate compatibility range, not proof that every version in it behaves the
same; doctor reruns the canaries on the installed version. Install the
`graphifyy` package separately following the
[upstream project](https://github.com/safishamsi/graphify). EIF does not install
it or mutate user configuration.

## Structural configuration

```yaml
integrations:
  structural_graph:
    enabled: true
    provider: graphify
    mode: structural
    artifact_path: graphify-out/graph.json
    baseline_commit: null
    processing: local
    data_boundary: local-only
    cost_cap_usd: 0
    failure_policy: degrade
```

Build or restore the raw graph separately, place it below `graphify-out/`, and
record the exact commit used to build it as the artifact's `built_at_commit`.
`baseline_commit` is an explicit override for artifacts without that metadata;
keeping it in the ignored artifact avoids making a new config commit stale by
definition. Generated EIF instances ignore the whole `graphify-out/`
directory. The committed synthetic canary under
`fixtures/` contains invented code only; it is not a project graph.

Freshness states are commit-derived:

- `fresh`: baseline equals the current commit;
- `stale`: baseline is an ancestor of the current commit;
- `diverged`: baseline is not an ancestor of the current history;
- `unknown`: a valid reachable baseline or Git state is unavailable.

Only `fresh` can be `healthy`. `stale` is reported directly, `diverged` is
`misconfigured`, and `unknown` is `degraded`.

## Semantic and deep safety gate

Structural mode is the default and must remain `local`/`local-only` with a
zero cost cap. `semantic` or `deep` requires all of:

- `processing: external`;
- `data_boundary: external-api`;
- a non-empty `semantic_provider`;
- a positive `cost_cap_usd`.

Missing any field fails closed as `misconfigured`. Even with a complete gate,
doctor only runs the local structural canary and reports `degraded` until a
separately approved semantic run supplies evidence. Doctor never initiates a
paid/provider scan.

## Authority and fallback

Graph output is navigation evidence, not source authority. Verify graph-derived
claims against source files before editing or deciding. If Graphify is disabled,
unavailable, stale, or degraded, use source search and manual navigation; core
EIF remains functional. See [`integrations/README.md`](../README.md) for the
shared failure-policy contract.
