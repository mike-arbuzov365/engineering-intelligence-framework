# Optional MCP reader

**Experimental.** `eifctl mcp serve` is a local stdio adapter over structured
EIF operations. One process serves one explicitly selected EIF instance.
The SDK harness and installed-wheel checks do not establish that a particular
agent client loads or uses these tools correctly. All four real-client canaries
remain `configured-not-verified`; no model-assisted evaluation was run.

## Install and select an instance

Use a local environment containing the intended EIF package version:

```text
python -m pip install "engineering-intelligence-framework[mcp]"
eifctl mcp --help
eifctl mcp serve --instance-path <explicit-instance-root>
eifctl mcp serve --instance-path <explicit-instance-root> --self-test
```

This repository's optional dependency constraints record the tested SDK,
`mcp==2.1.1`; use `pip install -c integrations/eif-mcp/constraints.txt` with the
wheel or package extra for the reproduced resolution. The extra admits
`>=2.1.1,<3`, while other SDK versions require separate verification. Core EIF,
normal CLI help, bootstrap and adapters do not require the SDK. Without it,
`mcp serve` exits 2 with an installation hint.

`--instance-path` overrides `EIF_INSTANCE_PATH`. There is no current-directory
fallback. Config and framework lock must exist and pass their schemas; failure
exits 3. `--packets-root` may select another contained relative packet directory.
The server reports package/runtime drift and never repairs it. Reinstall the
pinned package or explicitly upgrade the instance through the normal CLI.

## Configure a client

Back up the client's configuration before editing it yourself. Review the
appropriate [generated wrapper](../../integrations/eif-mcp/generated/) and use
its native reader snippet, replacing the instance-root placeholder. Verify that
`eifctl` resolves to the intended environment. To roll back, remove that server
entry and restart/reload the client as its own documentation requires.

| Client | Configuration | Key | Canary |
|---|---|---|---|
| Claude Code | `~/.claude.json` | `mcpServers` | configured-not-verified |
| Codex | `~/.codex/config.toml` | `mcp_servers` | configured-not-verified |
| Cursor | `~/.cursor/mcp.json` | `mcpServers` | configured-not-verified |
| Hermes v0.21.3 | `~/.hermes/config.yaml` | `mcp_servers` | configured-not-verified |

EIF generates templates only; no live client configuration is installed or
changed. `--self-test` launches a synthetic SDK client against a child server;
it does not call a model or prove any row in this canary table.

## Reader tools

| Tool | Purpose |
|---|---|
| `eif_capabilities` | Identity, versions, drift, mode, catalog and limits |
| `eif_brief` | Metadata route for an explicit task kind, read-list and state |
| `eif_artifact_get` | Heading list or paged section of a pinned named artifact |
| `eif_knowledge_search` | Lifecycle-aware search with explicit coverage |
| `eif_packet_status` | Explicit progress, dependencies and next ready session |
| `eif_doctor` | Bounded core checks with omitted checks disclosed |
| `eif_session_validate` | Named checkpoint validation |
| `eif_session_resume_audit` | Identity, source and read-only Git comparison |
| `eif_delivery_check` | Existing machine guard for design package/delivery |

Names are identifiers, never arbitrary paths. `artifact_get` accepts `skill`,
`playbook`, `template` or `rule`; omit `section` to obtain heading slugs. A page
has at most `max_chars` characters (default 4,000, maximum 12,000), with a
second escaped-byte limit to keep duplicated protocol content bounded. Continue
with `next_cursor`; cursors are opaque, section-bound and expire after 600 s.
The server reads policy only from the instance's pinned runtime manifests and
checks both manifest consistency and file hashes.

`brief` uses the installed package's ten explicit task-kind routes and pinned
skill metadata. It does not classify tasks. `light` has no skill read-list.
`packet_status` reads launch statuses (`prepared`, `in_progress`, `completed`,
`blocked`, `deferred`); legacy/missing status, incomplete roadmap coverage or a
dependency cycle means `partial` and no inferred next session. Only `completed`
satisfies a dependency. Every observed session remains visible in the report.

## Coverage, limits and errors

Every response carries `status`, `request_id` and `data`, with the same compact
JSON in text content and structured content. `partial`, `unavailable`, `stale`,
`unknown` and `truncated` are not success or proof of absence. Search coverage
counts indexed, malformed, schema-invalid and status-skipped artifacts. A
non-design profile reports the delivery guard as unavailable.

The bounded doctor omits ancestor size budgets, active source resolution,
skill-discovery consumption and optional integration probes. These can inspect
outside the instance or execute provider commands, so its result is `partial`.
Use direct `eifctl doctor --instance-path .` for full local coverage. Local
marker checks read the fixed adapter entrypoint, `.gitignore` and
`.gitattributes` as well as pinned manifests. These omissions do not alter CLI
doctor output.

Responses are limited to 24,576 UTF-8 bytes of serialized `CallToolResult`,
including both copies of the data, with framing headroom; briefs have a 4,096
byte hard limit and a 1,536 byte target. Search defaults to five results,
maximum twenty, with excerpts capped at 240 characters. Reader `tools/list`
is measured at 4,167 bytes against a 6,144 byte budget. Measurements use compact
SDK serialization, not Python object sizes. No token or quality improvement
claim follows from these byte counts.

Reads have a 15 s deadline and one physical worker. A timed-out synchronous
read may finish in that worker; later work remains serialized. Errors carry
typed codes, retryability and next actions, with no traceback or rejected
argument values. Logs go only to stderr and contain time, request ID, tool,
status, duration and response bytes. They do not contain argument values or
document text. No network listener, arbitrary command, SQL, generic file read
or file write is exposed. Resume audit uses only fixed Git commands with
optional locks and fsmonitor disabled, and refuses inherited/worktree Git roots.

## Deferred writes and evaluation

Human host elicitation has not passed G2: `O-6 = 0`. All five writer operations,
including render, are `deferred-to-EIF-022b`. No file-based approval substitute
or self-approval flag exists. Do not auto-allow future `eif_commit` or enable
automatic elicitation acceptance. The current server has no writer entry.

The [static byte measurement](https://github.com/mike-arbuzov365/engineering-intelligence-framework/blob/main/docs/benchmarks/context-footprint/README.md) and
[ten evaluation questions](https://github.com/mike-arbuzov365/engineering-intelligence-framework/blob/main/docs/benchmarks/mcp-eval/README.md) are separate from
client canaries. Expected answers are checked by an SDK script without a
model; model evaluation is `NOT RUN` and behavioral comparison is `DEFERRED`.
