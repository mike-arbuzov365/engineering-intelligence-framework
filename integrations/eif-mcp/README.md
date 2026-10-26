# Optional EIF MCP reader

`eifctl mcp serve` exposes nine instance-bound, read-only operations over stdio.
Install the optional extra, select a root explicitly and review the generated
client template. Core EIF and its adapters work without the SDK.

The [guide](../../docs/guides/eif-mcp.md) covers setup, boundaries, self-test,
backup and rollback. [manifest.json](manifest.json) declares the transport and
current availability. [generated/](generated/) contains four reviewable wrapper
documents with native reader snippets. They are not installed configuration.
Writer entries are explicitly `deferred-to-EIF-022b` with no executable entry.

[constraints.txt](constraints.txt) records the clean Windows/Python 3.11
dependency resolution used for the optional runtime. Use it with `pip install
-c`; it is separate from base requirements. The root
[sbom-mcp.cdx.json](../../sbom-mcp.cdx.json) and its checker cover the same 41
runtime components. Linux and Python 3.12 environment checks remain unrun.

Hermes v0.21.3 uses YAML at `~/.hermes/config.yaml`, under `mcp_servers`.
This was checked through CLI help and the installed command's source; it is
format evidence, not a connected-client canary. The other three formats follow
their existing documented JSON/TOML contracts. All four canaries remain
`configured-not-verified` because the authorized model-turn budget is zero.
