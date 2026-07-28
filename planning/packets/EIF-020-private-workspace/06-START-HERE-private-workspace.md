---
packet: EIF-020-private-workspace
type: autonomous-entrypoint
status: prepared
---

# Start here: EIF 0.2.0 private workspace scope

## Canonical prompt

```text
Autonomously execute the prepared execution packet in the current EIF
repository at:
planning/packets/EIF-020-private-workspace/

Entry point: 06-START-HERE-private-workspace.md.

Goal: add the smallest safe private workspace vertical slice inside L2,
without forking public EIF or creating a fourth layer.

Order:
1. Read packet files 00 through 05 in numeric order.
2. Re-verify every OBSERVED fact against current source before editing.
3. Execute sessions in the roadmap's exact order, one agent, no
   delegation, spawn or team tools.
4. For each session, read its launch file under sessions/ and keep a
   checkpoint per that file's convention.
5. Do not rely on prior chat history. Packet files and current
   repository/tool state are the source of truth.

Source-of-truth hierarchy:
- current owner instruction and ratified decisions;
- fresh repository/tool state;
- validated shared knowledge;
- packet assumptions;
- chat memory and inference, lowest priority.

Autonomy: apply ratified decisions and least-risk defaults instead of
asking routine questions. Record every non-trivial judgment in the
session checkpoint and final closeout.

Global limits:
- no Graphify;
- no subagents;
- remote_run_budget: 0;
- no push, tag, release, remote repository creation or hosted CI;
- no private target identities or machine paths in the public repo;
- no workspace publication command;
- no automatic third-party skill installation.

Stop and ask only if:
- a real secret or private-data leak has no safe in-scope fix;
- a remote or owner-only action becomes necessary;
- target files have incompatible concurrent edits with no safe
  reconciliation;
- the existing transaction primitives cannot preserve data safely;
- the current owner instruction changes the packet's architecture or
  scope;
- something would cause data loss or another hard-to-undo effect.

Closeout: fill 07-CLOSEOUT-020-private-workspace.md in Session 007. The
packet ends with a locally verified release candidate and a private
dogfood handoff, not a release.
```
