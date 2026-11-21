# Optional MCP reader

**Experimental.** `eifctl mcp serve` is a local stdio adapter over structured
EIF operations. One process serves one explicitly selected EIF instance.
The SDK harness and installed-wheel checks do not establish that a particular
agent client loads or uses these tools correctly. All four real-client canaries
remain `configured-not-verified`. EIF-023 records a synthetic model-assisted
pilot in its [packet closeout](https://github.com/mike-arbuzov365/engineering-intelligence-framework/blob/4c006bf78552d1cf9b84ed9becee9ff464550c69/planning/packets/EIF-023-solo-agent-delivery/07-CLOSEOUT-023-solo-agent-delivery.md).
The matched model evaluation remains deferred.

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
| `eif_packet_status` | Packet progress, optional sequential admission and a named session handoff |
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

`brief` uses ten caller-selected task kinds and pinned artifacts. `light`
has an empty read-list. `structured` points to the session-preparation
playbook and task-scope template. Use the bounded evidence loop when the
task calls for iterative feedback.
`packet_status` reads launch statuses (`prepared`, `in_progress`, `completed`,
`blocked`, `deferred`); legacy/missing status, incomplete roadmap coverage or a
dependency cycle means `partial` and no inferred next session. Only `completed`
satisfies a dependency. Every observed session remains visible in the report.

## Orchestrated session admission

For sequential execution with a separate reviewer, set
`orchestration_mode: orchestrated_sequential` in the roadmap's YAML
frontmatter. Each session keeps its progress and an `orchestration` mapping
in the launch frontmatter. Use the [launch and review schema](../../core/schemas/packet-orchestration.schema.json).

```yaml
orchestration:
  goal: Restore retry after a failed request
  scope: [src/retry]
  no_touch: [service-contract]
  criteria:
    AC-04: The keyboard retry reaches the success view after a failure
```

The orchestrator records the assigned model and reason when relevant. At
assignment record `attempt` and `base_revision`. At submission update
`current_revision` and set progress `completed` for the completed work.
Revisions are full Git SHA-1 commit IDs or `sha256:` digests of a specified
work artifact. The local reviewer verifies the actual version and evidence,
then records the submitted version. Point the launch at a new revision
whenever the submitted work changes. Admission compares the declared version
with the durable review. A new branch HEAD alone does not supersede a prior
session's recorded submission.

Read progress and admission with `eif_packet_status(packet)` or
`eifctl packet status <packet> --instance-path .`. Add `session` to the MCP
call or `--session <session>` to the CLI to receive the goal, scope, criteria,
submitted revision, review and recent return reasons. `data.next_session`
still reports dependency progress. For starting work in this mode, use
`data.admission.next_session` with its `reason` and `next_action`. A returned,
blocked, stale or unreviewed earlier session prevents starting a later one.

To append a review through the local CLI, prepare a JSON record at a
project-relative path, then run:

```text
eifctl packet record-review <packet> --instance-path . --record .session-context/review.json
```

Provide `instance`, `packet`, `session`, `attempt`, `base_revision`,
`reviewed_revision`, `decision` (`accepted` or `changes_requested`), `reason`
and `criteria`. Copy the named handoff's `contract_revision` into
`reviewed_contract` when reviewing the submission. It covers the goal,
scope, excluded scope and criterion definitions. A changed definition under
the same criterion ID invalidates the acceptance even for the same work revision.
An older acceptance without this field reports `stale_contract`. Submit a new
attempt and review its handoff to resume. Prior return decisions still block.
Map each criterion ID to a `result` and an `evidence` reference.
Acceptance requires a passing result and evidence for every declared criterion.
The CLI creates the versioned JSON in the packet's `reviews/` directory.
Commit the launch and review records with the packet. An exact retry
reports `already_recorded`; a conflicting decision for that version requires
reconciliation. After `changes_requested`, submit a new attempt and retain
the earlier review.

Admission is machine-calculated from the packet files. Only the designated
orchestrator should record reviews. That role and the verification of cited
evidence are process rules. CLI filesystem permissions control local writes.
MCP reads the same records and provides no review-writing tool.

## Coverage, limits and errors

Every response carries `status`, `request_id` and `data`, with the same compact
JSON in text content and structured content. `partial`, `unavailable`, `stale`,
`unknown` and `truncated` are not success or proof of absence. Search coverage
counts indexed, malformed, schema-invalid and status-skipped artifacts for
EIF-managed sources. A project-owned source returns `unavailable` with the
configured root and any contained existing index path. Its `coverage` is
`null` because EIF did not search it. Follow the project's retrieval policy.
A non-design profile reports the delivery guard as unavailable.

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
optional locks, fsmonitor, hooks, paging and lazy object fetching disabled.
Before its first Git command it walks at most 20,000 Git metadata entries
without following links, refusing linked or shared metadata, worktree/common
directories and alternate object stores. It then queries local configuration
without expanding includes and refuses includes, clean/smudge/process filters,
partial-clone settings and configured worktree/attribute/exclusion paths.
Unsupported repositories return `source_unavailable` with a direct
`eifctl session resume-audit` fallback; the direct CLI keeps its full local
behavior. Ordinary self-contained repositories remain supported.

## Deferred writes and evaluation

Human host elicitation has not passed G2: `O-6 = 0`. All five writer operations,
including render, are `deferred-to-EIF-022b`. No file-based approval substitute
or self-approval flag exists. Do not auto-allow future `eif_commit` or enable
automatic elicitation acceptance. The current server has no writer entry.

The [static byte measurement](https://github.com/mike-arbuzov365/engineering-intelligence-framework/blob/main/docs/benchmarks/context-footprint/README.md) and
[ten evaluation questions](https://github.com/mike-arbuzov365/engineering-intelligence-framework/blob/main/docs/benchmarks/mcp-eval/README.md) are separate from
client canaries. Expected answers are checked by an SDK script without a
model; model evaluation is `NOT RUN` and behavioral comparison is `DEFERRED`.

## Optional compact instructions

The default remains the legacy instruction block. To opt in, edit the project's
own `.eif/config.yaml`, preserving other integration settings:

```yaml
integrations:
  eif_mcp:
    enabled: true
```

Commit that desired configuration through the project's normal workflow, then
run `eifctl upgrade --instance-path .`. The same transactional generator updates
the block, while preserving user-owned configuration and content outside the
markers. `eifctl doctor` reports `configured` for this declaration; that state
never means a client connection was verified. The generator and doctor do not
import the optional SDK. With `enabled: false` (or the slot absent), the legacy
block remains byte-for-byte unchanged. To roll back, set `enabled: false`,
commit that config and run the same upgrade command.

The compact block asks for `eif_brief(task_kind)` and named policy sections.
If tools are absent in a chat, its fallback is direct `eifctl doctor`, direct
`eifctl search` using the configured knowledge root, and the pinned
`.eif/runtime/playbooks/engineering-intelligence-operating-protocol.md`. Both greenfield authority and
coexisting project authority remain explicit. Missing routes or a config/block
mode mismatch fail doctor. The four adapters and English/Ukrainian project
locales are exercised through actual enable/disable upgrades and rollback;
the governance block itself remains English-invariant.

This is a startup-byte experiment. The matched behavioral comparison is still
DEFERRED and client canaries are still unverified. It establishes no claim that
instructions improve task quality, reduce model tokens or lower usage cost.
