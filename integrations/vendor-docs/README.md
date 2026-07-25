# integrations/vendor-docs/

Current, versioned library/API documentation in the agent's context instead
of training-data recall about a dependency's surface. Optional, like every
other integration here: core EIF works with it absent, and the documented
fallback is local documentation or the source itself.

Declared provider: **Context7**, a hosted documentation service, reached
over MCP. See [`manifest.json`](manifest.json) for the provider class, data
boundary and capability contract.

## What EIF does and does not do here

**Does:** generate project-local routing guidance (when a vendor-docs
lookup outranks recall, and when it does not apply), declare the provider's
data boundary and cost cap in `.eif/config.yaml`, and emit a reviewable MCP
configuration template per adapter.

**Does not:** install the MCP server, write your agent's user-level config,
or hold your credentials.

That boundary is deliberate and is the same one that applies to agent hooks
(see [`integrations/rtk/`](../rtk/README.md)): an MCP server is configured
in the agent's own config file in your home directory, outside the project
instance EIF was pointed at. A framework that silently edits files outside
that boundary is not auditable by the person adopting it. Every generated
artifact under [`generated/mcp/`](generated/mcp/) therefore carries
`installed: false` and `user_config_mutated_by_generator: false` so the
claim is machine-checkable, not just prose.

Practical consequence: **you install the MCP server yourself, once, at the
user level.** EIF then makes sure the agent knows when to reach for it.

## Setup

1. Install the provider's MCP server following that provider's own
   documentation, into your agent's config:

   | Adapter | Config file | Key |
   |---|---|---|
   | Claude Code | `~/.claude.json` | `mcpServers` |
   | Codex | `~/.codex/config.toml` | `mcp_servers` |
   | Cursor | `~/.cursor/mcp.json` | `mcpServers` |
   | Hermes | `~/.hermes/config.json` | `mcpServers` |

   [`generated/mcp/<adapter>.json`](generated/mcp/) gives the shape and a
   review checklist. The provider command itself is owner-supplied on
   purpose: this framework has not verified any specific provider's
   invocation against that provider's primary source, and asserting one
   from recall is precisely the failure mode this integration exists to
   prevent.

2. Enable the integration in `.eif/config.yaml`:

   ```yaml
   integrations:
     vendor_docs:
       enabled: true
       provider: context7
       processing: external
       data_boundary: external-api
       cost_cap_usd: 0        # raise before enabling a quota-bearing plan
       failure_policy: degrade
   ```

3. Regenerate guidance if you change the policy source:

   ```text
   python scripts/eif_generate_vendor_docs_guidance.py
   ```

## Routing guidance

[`generated/vendor-docs-instructions.md`](generated/vendor-docs-instructions.md)
is generated from [`usage-policy.json`](usage-policy.json). Summary of the
contract it encodes:

- **Use it for** a dependency's real surface: signatures, options, config
  keys, migration steps, version-specific behavior.
- **Do not use it for** this project's own logic, general programming
  concepts, or questions about EIF's own methodology - none of those have a
  vendor that documents them.
- **Never put** private repository names, customer names, credentials or
  proprietary code into a query. The query text leaves the machine.

## Authority position

Vendor documentation is a **normative** source: it says what is supposed to
happen. It does not outrank an **empirical** observation of what the code
actually does. When the docs and a reproducible test disagree, that is a
discrepancy to record, not a tie to break by rank - see
[`core/ontology/authority-model.md`](../../core/ontology/authority-model.md).

This matters here specifically because a fresh, authoritative-looking doc
page is unusually persuasive, and it is still not evidence about the
version you have installed.

## Verification status

Honest current state, per this repository's own evidence discipline:

- **Verified:** the declaration layer, the generated routing guidance, the
  per-adapter template shape, and drift detection between
  `usage-policy.json` and the generated artifacts
  (`scripts/tests/test_vendor_docs_integration.py`).
- **Not verified:** live provider behavior. EIF generates configuration for
  an agent to load; it does not itself speak MCP, so `transport-reachable`
  is reported by the agent, not probed by `eifctl doctor`. No provider
  version has been pinned or behaviorally canaried the way RTK and Graphify
  have been.

That gap is why `manifest.json` marks `transport-reachable` with
`"verified": false` rather than claiming a health check this framework does
not perform.
