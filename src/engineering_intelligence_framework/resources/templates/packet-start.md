# Template: Execution Packet Autonomous Start

<!-- Knowledge source: GENERALIZE of the private EI's autonomous-run
entrypoint pattern (no single dedicated private template file - the
pattern was consistent across packets). Kept: the single canonical prompt
concept (one entry point, not "figure it out from the other six files"),
the explicit source-authority ordering, the explicit stop-condition list.
-->

One file per packet: `<packet-root>/06-START-HERE-<slug>.md`. The single
prompt a user pastes to hand this packet to an executing agent. Everyone
else in the packet (charter, facts, decisions, roadmap, self-review) is
read BY the agent as a result of this file, not read by the user to
figure out how to phrase the request.

```yaml
---
packet: <packet-id>
type: autonomous-entrypoint
status: prepared
---
```

## Canonical prompt

```text
Autonomously execute the prepared execution packet at:
<absolute path to packet root>

Entry point: this file.

Goal: <one sentence, from the charter>.

Order:
1. Read packet files 00 through 05 in numeric order.
2. Execute sessions in the roadmap's exact order, one accountable agent.
   A session is never delegated; bounded work inside one may be, if its
   output returns for verification and the record names it.
3. For each session, read its launch file under `sessions/` and keep a
   checkpoint per that file's own convention.
4. Do not rely on prior chat history - the packet files and current
   repository/tool state are the source of truth.

Source-of-truth hierarchy:
- current owner instruction and ratified decisions;
- fresh repository/tool state (not stale local branches or chat memory);
- validated shared knowledge;
- chat memory/inference, lowest priority.

Autonomy: apply ratified decisions and least-risk defaults instead of
asking routine questions. Record every non-trivial judgment call in the
session checkpoint and the final closeout.

Stop and ask only if:
- a real secret/private-data leak is found with no safe in-scope fix;
- an owner-only action (visibility, release, payment, external
  communication) turns out to be required;
- a resource constraint (e.g. hosted CI quota) blocks the final
  integration step;
- target files have incompatible concurrent edits with no safe
  reconciliation;
- something not covered above would cause data loss or another
  irreversible, hard-to-undo effect.

Closeout: fill `07-CLOSEOUT-<NNN>-<slug>.md` in the final session. Verify
every claim against source/tests/tool output yourself before recording it
- do not carry forward an unverified claim from an earlier session.
```
