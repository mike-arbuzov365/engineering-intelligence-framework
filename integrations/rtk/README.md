# integrations/rtk/

Shell-output compression with correctness-first output filtering.

## Current status: contract-only

EIF can declare `rtk`, validate its `local-only` data boundary, check whether
the executable is reachable, and apply `degrade` or `fail-closed` absence
policy. It does not yet validate RTK behavior.

Not yet built:

- a pinned compatible version and version probe;
- a machine-readable canonical command registry;
- Windows argv probes for quoted whitespace and special characters;
- correctness canaries for grep alternation, diff, and fallback behavior;
- generated adapter instructions/hooks from one contract;
- telemetry that separates native filtering, proxy/raw fallback, parse
  failures, and real output reduction;
- explicit `healthy`, `degraded`, and `misconfigured` doctor status.

Until those checks exist, the degraded mode is unfiltered commands. Never infer
that empty output means "no matches" when the transport/filter itself has not
passed a correctness canary. The governing principle remains the
correctness-first discipline described in
[`docs/architecture/HOW-EIF-WORKS.md#shell-output-compression-integration`](../../docs/architecture/HOW-EIF-WORKS.md#shell-output-compression-integration) -
a filter that silently returns wrong output is worse than no filter.
