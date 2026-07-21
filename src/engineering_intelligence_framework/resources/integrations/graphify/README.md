# integrations/graphify/

Structural code-graph navigation and impact analysis.

## Current status: contract-only

EIF can declare a Graphify provider, validate its allowed data boundary, check
whether its executable is reachable, and apply `degrade` or `fail-closed`
absence policy. It does not yet execute or validate Graphify behavior.

Not yet built:

- a pinned install/version compatibility contract;
- `query`/`path`/`explain` behavioral canaries;
- graph baseline commit and merge-base freshness calculation;
- structural-only default plus an explicit semantic-provider/cost gate;
- privacy review and raw-artifact placement rules in generated instances;
- status output that distinguishes `healthy`, `stale`, `degraded`, and
  `misconfigured`.

Until those checks exist, use source search/manual navigation as the honest
degraded mode and verify every graph-derived claim against source files. See
[`integrations/README.md`](../README.md) for the shared contract.
