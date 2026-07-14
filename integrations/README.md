# integrations/

Optional capabilities. EIF's governance model (authority, knowledge
lifecycle, execution packets) works without any of these; each adds a
specific capability with a documented degraded mode when absent.

| Integration | Adds | Data boundary | Degraded mode without it |
|---|---|---|---|
| `graphify/` | Structural code-graph navigation, impact analysis, "what calls this" queries | `local-only` for AST-based extraction; `external-api` if semantic community labeling via an LLM backend is enabled - verify which mode a given provider is actually running in | Agent falls back to grep/manual source browsing - slower, more token-hungry, no cross-file impact analysis |
| `rtk/` | Shell-output compression, tracked token savings, bare/broken-command auto-rewrite | `local-only` | Agent's shell commands run unfiltered; still functionally correct, just more expensive per session |
| `vendor-docs/` | Current, versioned library/API documentation instead of stale training data | `external-api` - queries a hosted documentation service | Agent relies on training-data knowledge of libraries, which may be outdated |

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

Ported content is not populated yet.
