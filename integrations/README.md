# integrations/

Optional capabilities. EIF's governance model (authority, knowledge
lifecycle, execution packets) works without any of these; each adds a
specific capability with a documented degraded mode when absent.

| Integration | Adds | Degraded mode without it |
|---|---|---|
| `graphify/` | Structural code-graph navigation, impact analysis, "what calls this" queries | Agent falls back to grep/manual source browsing - slower, more token-hungry, no cross-file impact analysis |
| `rtk/` | Shell-output compression, tracked token savings, bare/broken-command auto-rewrite | Agent's shell commands run unfiltered; still functionally correct, just more expensive per session |
| `vendor-docs/` | Current, versioned library/API documentation instead of stale training data | Agent relies on training-data knowledge of libraries, which may be outdated |

None of these is a hard dependency of the governance model. Marking them
"required" anywhere is a bug - see
[`docs/architecture/HOW-EIF-WORKS.md`](../docs/architecture/HOW-EIF-WORKS.md#extension-model).

Ported content is not populated yet.
