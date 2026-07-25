# integrations/

Optional capabilities. EIF's governance model (authority, knowledge
lifecycle, execution packets) works without any of these; each adds a
specific capability with a documented degraded mode when absent.

| Integration | Adds | Data boundary | Degraded mode without it |
|---|---|---|---|
| `graphify/` | Structural code-graph navigation, impact analysis, "what calls this" queries | `local-only` for AST-based extraction; `external-api` if semantic labeling is explicitly enabled | Agent falls back to source search/manual browsing; no graph-level path or impact hints |
| `rtk/` | Shell-output compression and tracked output reduction | `local-only` | Agent's shell commands run unfiltered and no RTK reduction is recorded |
| `vendor-docs/` | Current, versioned library/API documentation instead of stale training data | `external-api` - queries a hosted documentation service | Agent relies on local docs or training-data knowledge, which may be outdated |

Implementation status:

- RTK has a versioned behavioral adapter, command registry, canaries and
  content-free local telemetry. A failed required canary produces `degraded`.
- Graphify has a versioned structural adapter, synthetic query/path/explain
  canaries, validated artifact metadata, explicit repository/scope identity,
  portable restore/status commands, a Git-and-hash-derived artifact lifecycle,
  local raw-artifact policy and an explicit semantic provider/boundary/cost gate.
  Any non-fresh state preserves the source-navigation fallback.
- Vendor-docs now names a declared provider (Context7, reached over MCP),
  ships generated routing guidance and a reviewable per-adapter MCP
  configuration template, and states its authority position: vendor
  documentation is a normative source and does not outrank an empirical
  observation. It is still not behaviorally canaried the way RTK and
  Graphify are - EIF generates configuration for the agent to load and does
  not itself speak MCP, so `transport-reachable` is reported by the agent
  and is marked `"verified": false` in its manifest rather than claiming a
  probe that does not happen.

None of the three is installed by EIF. RTK and Graphify are executables you
install; a vendor-docs MCP server is configured at the **user level**, in
your agent's own config file outside the project instance. EIF generates
project-local guidance and reviewable templates and never mutates
user-level configuration - the same boundary that applies to agent hooks.
Every generated artifact records `installed: false` and
`user_config_mutated_by_generator: false` so that claim is
machine-checkable.

The `data_boundary` values here are the declared, expected boundary for a
typical provider in that integration slot - see
[`.eif/config.yaml.example`](../.eif/config.yaml.example) for the field
each project instance sets per integration, and
[`SECURITY.md`](../SECURITY.md#threat-model) for why a boundary mismatch
between what's declared and what a provider actually does is a security
issue, not a documentation nitpick.

None of these is a hard dependency of the governance model. Marking them
"required" anywhere is a bug - see
[`docs/architecture/HOW-EIF-WORKS.md`](../docs/architecture/HOW-EIF-WORKS.md#extension-model).

## Shared implementation boundary

The generic `.eif/config.yaml` and `eifctl doctor` contract is implemented:

- integrations can be enabled/disabled with a named provider;
- the declared data boundary is checked against the known provider class;
- an executable's PATH reachability is checked when enabled;
- `failure_policy: fail-closed` reports a missing provider;
- `failure_policy: degrade` permits the documented core-only fallback.

The shared declaration layer is not itself health. RTK and Graphify extend it
with real version probes and provider-specific behavioral canaries; vendor-docs
does not yet.
`eifctl doctor` reports each configured provider independently, and a provider
must not be marketed as integrated until its capability-specific checks pass.
Core EIF remains functional with every optional provider disabled or absent.
